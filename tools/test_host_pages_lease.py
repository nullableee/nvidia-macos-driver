#!/usr/bin/env python3
"""Shared host-page leases (NVMTL_HOST_PAGES_SHARE=1): wrappers of one surface share an import of its pages. The table
rules (reuse, stale cookie, idle expiry, eviction, busy entries) are proven by tools/test_import_cache.c; these arms prove
the wiring: off by default, keyed by surface and cookie, checked against the mapped address, and every lease given back."""
import pathlib, sys
root = pathlib.Path(sys.argv[1] if len(sys.argv) > 1 else pathlib.Path(__file__).resolve().parents[1])
vk = (root / 'plugin/nvmtl_vk.c').read_text()
ob = (root / 'plugin/NVMTLObjects.m').read_text()
fails = 0
def check(name, ok):
    global fails
    print(('ok   ' if ok else 'FAIL ') + name); fails += not ok
def func(src, head):
    i = src.find(head)
    return src[i:src.index('\n}\n', i)] if i >= 0 else ''
check('sharing is off unless NVMTL_HOST_PAGES_SHARE=1', "getenv(\"NVMTL_HOST_PAGES_SHARE\"); on = e && e[0] == '1'" in vk)
lease = func(vk, 'static int nvmtl_hp_lease(')
check('a lease is found by surface id, size and cookie', 'nvmtl_ic_acquire(&g_hp_ic, t_hp_key.sid, bytes, t_hp_key.cookie' in lease)
check('a lease is used only when the pages are mapped where the lease was made', 'tmp->map == base' in lease)
check('a moved page range hands the lease back before importing again', 'nvmtl_ic_release(' in lease)
check('a surface with no cookie never leases', 't_hp_key.set' in lease)
check('a very large surface is imported per copy as before', '64u << 20' in lease)
check('the copy uses a lease before the private cache', func(vk, 'static nvk_buffer *nvmtl_host_pages(').index('nvmtl_hp_lease') < func(vk, 'static nvk_buffer *nvmtl_host_pages(').index('cache->buf'))
done = func(vk, 'static void nvmtl_host_pages_done(')
check('a leased buffer is given back, never destroyed under its other users', 'nvmtl_ic_release(' in done and done.index('nvmtl_ic_release') < done.index('nvmtl_vk_buffer_destroy(hb)'))
def has_surface_key(body, operation):
    pos = body.find(operation)
    if pos < 0:
        return False
    key = body.rfind('nvmtl_vk_host_pages_key((uint32_t)IOSurfaceGetID', 0, pos)
    clear = body.find('nvmtl_vk_host_pages_key(0, 0);', pos)
    return key >= 0 and clear > pos

surface_in = func(ob, '- (void)nvmtlSurfaceIn {')
surface_out = func(ob, '- (BOOL)nvmtlSurfaceOutDirtied:(BOOL)dirtied {')
surface_fused = func(ob, '- (BOOL)nvmtlFuseSurfaceOutToCmd:(nvk_cmdbuf *)c {')
check('surface-in upload names its surface and clears the key after the host copy',
      has_surface_key(surface_in, 'nvmtl_vk_image_write_host('))
check('surface-out readback names its surface and clears the key after the host copy',
      has_surface_key(surface_out, 'nvmtl_vk_image_read_host('))
check('fused surface readback names its surface and clears the key after the host copy',
      has_surface_key(surface_fused, 'nvmtl_vk_cmd_image_read_host('))
check('the default path never reads or writes the surface cookie', 'return on ? nvmtl_plane_cookie(s, YES) : 0;' in ob)
sys.exit(1 if fails else 0)
