# Graphics0.4.7 runtime result

User installed and rebooted. Currentboot16:09:24. Capture contention-20261031-161121-872: all probe/sample/animation exit0. GPU full pixels/mips/alias/presubmit PASS.

WindowServer completion_channel ready1,errors0 confirmed. Calls19209 at16:11:22.469 ->24488 at16:11:33.594:5279successful transport calls with no recorded IO error. This confirms the real WS sandbox permits the separate channel; it is not merely a native-probe result.

During capture GPU timeouts4->4, direct_present0 throughout. Prior comparable animated capture on0.4.6:34->36. Different boots:4 is NOT a reduction from36; only within-capture deltas are comparable. One short passing test does not prove all stalls eliminated. Four startup/earlier timeouts already existed before capture.

Animation12s:82.49panelcopies/s vs69.83prior capture (+18.1% approximately), handler6.7307 vs7.795ms. Different boot/configured linkduration5.9529 vs6.1256ms (168vs163 callbackcadence), so not a controlled18%driver-gain claim and not Safari FPS.

Main3311samples,ordinary dirty call ancestry345 (344Mach leaves) remains, vs419prior. It still blocks on ordinary client; dedicated channel removes the shared readiness-gate dependency, not the family lock itself. Main serverloop wait1408; counts are neither CPU%nor frame-ms. Current direct_present0 explains generic pageoff cost:ready4.3567ms plus Intelcopy1.9176ms are nested in handler6.7307ms. Do not add overlapping terms.

Next necessary manual validation: existing0.4.7/test-desktop.sh enables previously validated direct1 then collects20s moving/resizing heavy Safari. No installation needed. Maintain ordinary workloads; if timeout grows again, retain boot and per-capture deltas. No source/system changes made during result analysis.
