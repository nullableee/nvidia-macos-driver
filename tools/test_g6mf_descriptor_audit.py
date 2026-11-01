#!/usr/bin/env python3
"""Test opt-in descriptor miss taxonomy and mutation controls without macOS/GPU."""
from pathlib import Path
import shutil
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]
header = ROOT / 'plugin/nvmtl_descriptor_audit.h'
clang = shutil.which('clang') or shutil.which('cc')
if not clang:
    raise SystemExit('No C compiler found')
fixture = r'''
#include "nvmtl_descriptor_audit.h"
#define CHECK(e) do { if (!(e)) return __LINE__; } while (0)
int main(void) {
 CHECK(G6MF_DA_N == 12);
 CHECK(g6mf_desc_audit_miss_reason(0,1,1,0,0,0) == G6MF_DA_BUILD_NO_LAST);
 CHECK(g6mf_desc_audit_miss_reason(1,0,1,0,0,0) == G6MF_DA_BUILD_LAYOUT);
 CHECK(g6mf_desc_audit_miss_reason(1,1,0,0,0,0) == G6MF_DA_BUILD_STALE);
 CHECK(g6mf_desc_audit_miss_reason(1,1,1,1,0,0) == G6MF_DA_BUILD_STORAGE);
 CHECK(g6mf_desc_audit_miss_reason(1,1,1,0,1,0) == G6MF_DA_BUILD_MASK);
 CHECK(g6mf_desc_audit_miss_reason(1,1,1,0,0,1) == G6MF_DA_BUILD_CHANGED);
 CHECK(g6mf_desc_audit_miss_reason(1,1,1,0,0,0) == G6MF_DA_BUILD_OTHER);
 CHECK(g6mf_desc_audit_miss_reason(1,0,1,1,1,1) == G6MF_DA_BUILD_LAYOUT);
 return 0;
}
'''
variants = {
    'production': header.read_text(),
    'missing-mask-reason': header.read_text().replace('if (mask_grew) return G6MF_DA_BUILD_MASK;', ''),
    'missing-layout-reason': header.read_text().replace('if (!same_layout) return G6MF_DA_BUILD_LAYOUT;', ''),
}
for name, src in variants.items():
    with tempfile.TemporaryDirectory() as d:
        p = Path(d)
        (p/'nvmtl_descriptor_audit.h').write_text(src)
        (p/'test.c').write_text(fixture)
        subprocess.run([clang, '-x', 'c', '-std=c11', '-Wall', '-Wextra',
                        '-I', str(p), str(p/'test.c'), '-o', str(p/'test')],
                       check=True, capture_output=True)
        result = subprocess.run([str(p/'test')], capture_output=True)
        assert (result.returncode == 0) == (name == 'production'), (name, result.returncode)
        print('PASS', name)

source = (ROOT/'plugin/nvmtl_vk.c').read_text()
assert '#include "nvmtl_descriptor_audit.h"' in source
assert 'g6mf_desc_audit_event(G6MF_DA_REUSE_EXACT)' in source
assert 'g6mf_desc_audit_event(G6MF_DA_REUSE_TABLE)' in source
assert 'g6mf_desc_audit_miss_reason(' in source
assert 'g6mf_desc_audit_event(G6MF_DA_BATCH_HIT)' in source
assert 'g6mf_desc_audit_event(G6MF_DA_BATCH_MISS)' in source
assert 'nvmtl_snapshot_set_md(c, which, hi, m, p->tbany ? tb : NULL' in source
assert 'void g6mf_descriptor_audit_stats(' in source
assert 'DESC_AUDIT events=' in (ROOT/'tools/g6mf_descriptor_render_probe.m').read_text()
print('PASS: production integration points present')
