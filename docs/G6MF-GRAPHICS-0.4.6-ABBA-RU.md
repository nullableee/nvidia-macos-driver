# Safari private-image cache ABBA, 0.4.6

Same boot14:17:27; modes OFF/ON/ON/OFF verified by WindowServer private_images logs. Complete four-phase collection. Copies/s:59.74,60.74,57.25,56.98. OFF58.36 vsON59.00, +1.08%; phase spread exceeds gain. Not application FPS; no meaningful throughput improvement demonstrated.

Kernel handler means4.0859,4.0981,4.0715,4.4256ms. Timeouts3 throughout; direct present remains1, held/timeout0. Private cache original setting1 restored by script.

Main-thread allocation observations OFF61/64 vsON13/11. Exact totals in diagnostics/safari-ab-0.4.6/summary.json. Counts are not CPU percentages or frame milliseconds.

No basis for promising165FPS or increasing cache immediately. Next investigation: compositor CPU encoding/layer preparation; LUT and descriptor work are smaller candidates. Do not weaken GPU synchronization. Driver/EFI/configuration unchanged.
