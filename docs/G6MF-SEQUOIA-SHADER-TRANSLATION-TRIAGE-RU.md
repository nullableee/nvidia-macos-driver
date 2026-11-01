# Shader translation triage for Sequoia (2026-11-01)

Initial standalone GPU probe stopped before the first draw: newLibraryWithData: translation produced nothing.
This is NOT a descriptor-set or pixel validation failure.

plugin/NVMTLLibraryLoad.m loads the AIR->SPIR-V translator from next to the isolated NVMTLDriver or
from /Library/GPUBundles/nvmtl/libnvmtl_translate.dylib.
The indexing function returns nil if translator is unavailable OR the metallib contains no indexable AIR entries.
Those failures are indistinguishable from the original single-line error.

The first test bundle used NVMTL_RELEASE=1. plugin/NVMTLDevice.m suppresses ordinary nvlog() in that mode.
Run opt-in diagnostic build without installation:

    G6MF_DIAGNOSTIC=1 bash tools/g6mf_descriptor_build_check.sh

Then use the latest Desktop build:

    BIN="$(ls -t "$HOME"/Desktop/G6MF-descriptor-compile-*/NVMTLDriver | head -n 1)"
    bash tools/g6mf_descriptor_smoke.sh "$BIN"

The smoke harness sets NVMTL_LOG_PATH to a per-test file in the Desktop smoke output folder.
On failure it includes the last 70 lines of baseline.driver.log. This is process-local logging only.
Look for translate: dlopen, missing translator symbol, metallib bitcode blob count, and AIR indexing.
Do not change installed Serial LUT v9.2, replace system binaries, or merge upstream.
