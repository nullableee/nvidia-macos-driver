# Graphics0.4.7 Safari/direct-present result

Profile161302-1092/perf161302-1107, boot16:09:24. Actual installed WS0.4.7, dedicated channel ready1. Direct1,latency diag restored by wrapper. Panel69.49copies/s over20.030579s (1392copies), entry14.3883ms, handler3.7822ms, fence.8786ms, Intelcopy2.0085ms. Generic pageoff49calls, CPUwrite1.2621ms mean, not the full-frame dominant population. Nested timings must not be added.

No new timeout during capture:4->4, live remains4; IOP/pageoff failures and copy lock misses0. completion channel calls43495at16:13:04.734 ->51127at16:13:23.347 (+7632),errors0. Startup/earlier4timeouts remain unexplained; do not claim they were eliminated by runtime fix.

Main1762observations:dirty mark22(21Mach),schedule wait94,serverloop274Mach,descriptor allocator22leaf. Old contention419dirty observations occurred in a different animated workload/direct0; cannot call this a measured95%performance gain. End CPU snapshotWS115.1%,Safari25.7%, not20saverage. Capture0.4.6 Safari66.57 vs69.49now (+4.4%) uncontrolled acrossboots/settings; ABBA0.4.6~59 is a different run, not baseline for a claimed18%gain.

Private image hits+3253/misses+1230 across same interval =>72.56%hits; many small differently shaped blur targets remain. Prior controlled ABBA showed only1%desktop gain from this cache, so do not chase entry count as the main solution. Direct copy remains~2ms; global CPU/compositor/encoder preparation still distributed. No new proven single bottleneck identified in this result. No more installation required for0.4.7.
