# G6 MF muxless candidate v1

Base: `f95f4d24a42f88f9bc71fba12c90bcfe8e060225` (NullMoth 2.6.4 source).
Target: Intel A7A0 + RTX 4050 Laptop 28A1, Tahoe x86_64, internal eDP on Intel.
This is a local experimental patch, not a contribution submitted upstream.

## Implemented

- A display-less NVIDIA GPU publishes `NVRMRenderBridge`, an IOService exposing
  allocation/free/RM-handle calls from the initialized NVKMS device. It is not
  an IOFramebuffer and does not invent a connected NVIDIA monitor.
- NVAccel selects its NVIDIA render backend separately from its Intel scanout;
  the backend must have the same PCI ancestor as this accelerator. Intel head 4
  can register without a NVIDIA head 0. Existing NVIDIA head 0 remains the
  preferred backend when it exists.
- `nmoptimus=1` explicitly enables the real Intel bridge and head 4. Without
  that boot argument, the patched real framebuffer declines the device.
- The firmware plane must be unique, enabled, linear XRGB8888, with supported
  rotation/channel ordering/compression/offset, adequate stride and aperture
  capacity. The complete 12-bit stride field is used. Scanout mapping and VBL
  callback allocation are checked before IOFramebuffer::start. Dependent head
  properties are set before the superclass can publish the framebuffer.
- Intel scanout returns a bounded CPU mapping with `phys=0`, never NVIDIA VRAM.
  Every scanout request revalidates the live plane. The copy writes visible
  pixels only, checks both pitches/capacities and completes WC stores with sfence.
- A muxless present retains its last frame when GPU completion/pageoff is not
  ready. A GPU timeout does not erase the pending fence. The existing NVIDIA
  display fallback is preserved when muxless mode is disabled.
- A separate `NMIntelProbe.kext` contains only IOService probe code, not
  IOFramebuffer subclasses, NVAccel, GSP or a Metal plugin. With `nmintelprobe=1`
  it reads the four firmware plane snapshots and publishes raw values/rejection
  codes in IORegistry. It never writes display registers or scanout memory.

## Next hardware evidence

The existing report proves PCI enumeration and firmware display, not GPU/GSP
initialization or an accelerated WindowServer. First collect the missing Intel
plane snapshot using the standalone probe. This does not require installing
NullMoth or touching the user's restored Intel package.

The probe is still a new kernel binary: cross-compilation and correct Mach-O
metadata do not prove loading/binding or safe behavior on a real machine.

1. On Linux run the kit's `prepare-probe.py --activate`. It preserves the entire
   original EFI directory and activates a copied EFI with only NMIntelProbe and
   nmintelprobe=1 added. It does not change SIP, BAR settings, existing drivers,
   ACPI tables or macOS files. No reset of NVRAM is required by the script;
   boot-args is added to OpenCore NVRAM/Delete so the configured value is applied.
2. Boot ordinary Tahoe and run the supplied collect-macos.sh with sudo. The new
   report includes NMIntelProbe, NMIntelFB, NVRMRenderBridge and head/copy/fence
   counters. Return to Linux with the USB still containing the report.
3. Decode it with tools/g6mf_decode.py. Check the loaded probe version, one valid
   active plane and raw values before enabling nmoptimus=1 or the full stack.

## Full candidate

The kit also contains cross-linked NMIntelFB/NVAccel/NVRMFB kexts from this
source. Those are candidate replacements for the corresponding components of
**the same NullMoth base**, not a complete driver installation. NVRM, its GSP
firmware, NVMTLDriver, translator and NVK backend are still required. Do not
inject all candidate kexts just to obtain the Intel probe snapshot. Probe and
real bridge are deliberately separate packages.

A real full-stack acceptance must show RTX initialization, a NVIDIA Metal
MTLDevice, successful offscreen GPU readback and then increasing head-4 copy
counters with a visible stable desktop. No such hardware result is claimed yet.
The final patch after the next report depends on what the firmware plane and
actual GPU bring-up report; one more patch cannot be promised in advance.

## Verification and boundaries

`tools/test_g6mf_muxless.py` compiles and runs production layout/copy functions,
actual registration methods, and the GPU-wait method under mocked kernel APIs.
ASan/UBSan checks the fixture. It proves the upstream head-0 check fails the
Intel-only scenario and the patched method passes. These tests do not emulate
Apple's complete display family, PCI DMA, GSP or WindowServer.

`tools/test_g6mf_probe_efi.py` exercises staging/activation against temporary
EFIs, byte-preserved originals, unrelated settings and invalid-binary refusal.
Existing headless, flip/pageoff gating and pending-lifetime regressions pass.

All four kexts compile to x86_64 Mach-O objects and link as MH_KEXT_BUNDLE,
including _kmod_info. They are not signed by Apple; native kmutil linking/loading
has not been checked. Build manifest records source base, commands and hashes.

Rebuild on Linux with:

```sh
python3 tools/build_g6mf.py --sdk /path/to/MacKernelSDK \
  --ogkm /path/to/open-gpu-kernel-modules-615.78.08 \
  --ld /path/to/cctools-ld64 --out /path/to/output
```

macOS can use the same script with Python 3, Xcode CLT and MacKernelSDK; omit
--ld. --probe-only does not need NVIDIA sources. The shipped probe is already
built and needs no compiler on the user's Tahoe installation.

Not implemented/validated: Intel modesetting/link training, tiled/compressed
planes, arbitrary modes, guaranteed 165 Hz, suspend/resume, GPU reset recovery,
repeated hotplug, full app/Metal conformance, full power-state handling or
long-duration stress. The real bridge adopts firmware mode and rejects a plane
that no longer matches. The firmware snapshot cannot prove those features.

## Probe 0.1.2 build hotfix

The first boot rejected probe 0.1.1 before its start method because the binary
imported atexit. See G6MF-PROBE-0.1.2.md. The build now preserves native module
constructor/destructor sections without an atexit dependency, and validates
this before producing a successful component. Next diagnostics require 0.1.2.
