# 0.4.6 WindowServer result

Installed/loaded UUID08E46473-8C65-389D-A6EB-2D20E27303E6 confirmed by sample. Boot14:17:27. Terminal run profile142121:93.11copies/s. User explicitly confirmed this was Terminal, not Safari.

Safari run profile142325/perf142325:66.57copies/s,entry15.0245ms,handler3.9480ms,fence.9869ms,Intelcopy2.0532ms. Prior Safari0.4.5:70.39copies/s; uncontrolled runs do not demonstrate an improvement. Timeout3->3,IOPfail0,pageofffail0. Main1817observations; allocation ancestry10 vs67/1809 previously, raw sample observations only. WindowServer106.5%CPU/Safari36.5% in end snapshot, not window average.

Recovered log14:23:27.219-45.435:IOSurface calls+4096,hits+4078,created18=99.56%hits. Private images hits+5508,misses+757=87.92%hits; evictions+755,held16,~1.9MiB at end. Count pressure remains a candidate but larger limits need evidence. Queue complete+3642,complete_ns delta5694524495 =>1.564ms/CB; pending delta4456/3642=1.224parts, not frames. Means cannot be added as independent frame costs.

Collector incorrectly filtered0.4.5. Fixed profile-core.sh to G6MF prefix; recovered raw logs saved diagnostics/safari-0.4.6. No driver reinstall required for collector fix. Added test-safari-ab.sh: four20second same-window Safari phasesOFF/ON/ON/OFF, keeps direct1, restores prior private-cache setting on success; disables both on error/new timeout. User manual80second workload needed for controlled comparison before next tuning.
