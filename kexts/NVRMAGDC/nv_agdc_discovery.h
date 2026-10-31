#pragma once
// Bounded only on the AGDC thread_call worker, never the graphics work loop.
template<class Wanted, class Discover, class Pause>
static bool nvAgdcAwaitTargets(Wanted wanted, Discover discover, Pause pause)
{
    for (unsigned i = 0; i < 20; ++i) {
        if (!wanted()) return false;
        if (discover()) return true;
        if (i + 1 < 20) pause();
    }
    return false;
}
