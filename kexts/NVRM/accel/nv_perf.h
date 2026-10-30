#pragma once
// Allocation-free timing. Units are nanoseconds, counters are cumulative.
struct NMPerfMetric { int64_t count, ns, max; };
static inline void nmPerfAdd(NMPerfMetric &m, uint64_t ns) {
    __atomic_fetch_add(&m.count, 1, __ATOMIC_RELAXED);
    __atomic_fetch_add(&m.ns, (int64_t)ns, __ATOMIC_RELAXED);
    int64_t previous = __atomic_load_n(&m.max, __ATOMIC_RELAXED);
    while ((int64_t)ns > previous && !__atomic_compare_exchange_n(&m.max, &previous,
            (int64_t)ns, false, __ATOMIC_RELAXED, __ATOMIC_RELAXED)) {}
}
static inline uint64_t nmPerfElapsed(uint64_t start) {
    uint64_t ns = 0;
    absolutetime_to_nanoseconds(mach_absolute_time() - start, &ns);
    return ns;
}
struct NMPerfScope {
    NMPerfMetric *metric; uint64_t start;
    explicit NMPerfScope(NMPerfMetric *m): metric(m), start(m ? mach_absolute_time() : 0) {}
    ~NMPerfScope() { if (metric) nmPerfAdd(*metric, nmPerfElapsed(start)); }
};
static inline unsigned nmPerfGapBin(uint64_t ns) {
    const uint64_t limits[] = {7000000, 12000000, 20000000, 28000000, 40000000};
    for (unsigned i = 0; i < 5; ++i) if (ns < limits[i]) return i;
    return 5;
}
