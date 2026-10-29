# Probe 0.1.2: fix the first hardware boot's injection failure

Report: `macOS-20261029-182337-732`. All collection steps completed without a
timeout; the requested NVIDIA debug sysctls were absent. No NMIntelProbe kext
or service loaded, so this run did not capture Intel plane registers.

The associated OpenCore log identifies the failure before probe code ran:

```
OCAK: Symbol ___cxa_atexit has 0-value
OCAK: RIP-relative overflow in com.nullmoth.NMIntelProbe: source=0xFFFFFF8005256EB2 target=0x0 diff=0x7FFADA914A
OC: Prelinked injection NMIntelProbe.kext (...) - Invalid Parameter
```

The rejected binary's external branch relocation at 0xEB2 is to
`___cxa_atexit`, exactly matching the failing source address's in-image offset.
This is a build/runtime linkage defect, not evidence about GPU acceleration or
whether Intel's plane is linear/tiled.

With the compiler used for the local cross build, frontend flags alone did not
prevent LLVM's backend from lowering llvm.global_dtors to an atexit call.
The build now disables atexit registration in the frontend and, when accepted
by the compiler, uses `-mllvm -disable-atexit-based-global-dtor-lowering`.
Constructor and destructor sections are preserved. Global destructors are
not simply dropped.

The strengthened Mach-O validator scans every undefined symbol, rejects
atexit/TLS runtime dependencies and requires module init and term sections as
well as matching kmod_info identity/version. The actual rejected 0.1.1 binary
fails this new gate; all four rebuilt candidate kexts pass. The builder runs
the gate before recording a successful component, and CI runs it before
packaging. Regression fixtures cover cxa_atexit, atexit, TLS and missing term
sections. Existing CPU regressions still pass.

The standalone probe is now version 0.1.2, with module-entry/start diagnostics,
BAR-map failure logging and per-pipe raw/rejection logs. PCI provider status is
published so an unsuccessful match/start can be diagnosed from IORegistry.
It still contains no framebuffer subclass, display-register writes or scanout
writes. The only runtime failure confirmed by this report is corrected;
successful injection and the register snapshot need the next actual boot.

No Intel package removal, SIP changes, BAR changes or Metal enablement form
part of this fix. Full-stack RTX/GSP/Metal and the real Intel bridge remain
unvalidated on hardware. CI has not been dispatched from this session.
