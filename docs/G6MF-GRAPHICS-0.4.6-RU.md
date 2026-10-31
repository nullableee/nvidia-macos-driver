# Graphics 0.4.6 experimental

Safari profile without Displays settings: 70.39 panel copies/s, handler3.7663ms, fence.8577ms, copy2.0283ms. Not application FPS. 2048/2048 IOSurface cache hits during22:50:46.085-22:51:00.510. Main-thread allocation ancestry67/1809 observations points to private backdrop/blur textures. Sampling observations are not CPU percentages or frame times.

New exact-key private 2D render-target image cache:16 images/64MiB, max32MiB per image. Shared/IOSurface/depth/multisample/heap excluded. Command buffers and aliases retain live roots; upload barrier precedes parking. Layout is preserved; applications initialize texture contents normally. Pool memory remains in allocation accounting. No idle background trimming; disabling drains on next eligible creation. Ordinary apps default off. WindowServer polls root-owned non-writable-by-others policy file once/second. Missing, invalid or symlink policy fails closed.

Native ABBA: mean creation+release cost per fresh texture in microseconds. Synthetic operation, NOT desktop FPS gain.

| Texture | OFF us | ON us |
|---|---:|---:|
| 512x256 BGRA8 | 246.5 | 14.3 |
| 512x256 RGBA16F | 203.2 | 13.9 |
| 960x600 BGRA8 | 635.8 | 14.3 |
| 960x600 RGBA16F | 1055.0 | 12.4 |
| 1920x1200 BGRA8 | 1415.3 | 16.2 |
| 1920x1200 RGBA16F | 2171.7 | 11.9 |

PASS: production pool ASan/UBSan,20000 concurrent lifetimes, exact keys, limits, eviction, flush, policy reader with mocked uid/clock. GPU: all pixels of4mips,100alias lifetimes,100pre-submit releases,200reuse cycles,40full1920x1200BGRA8/RGBA16F frames. Installer20mock cases include private-safety failure and restoration of prior configuration. WindowServer validation pending.

Earlier boot11:47 timeout counter6->9 across a wider working interval, cause unresolved. User rebooted at14:07. Fresh isolated OFF/ON test in that boot:8->8 for each, direct held/timeout0. Never compare counts across boots. Kernel and EFI unchanged.

Install:

```bash
sudo bash /Users/spotlight1/Projects/G6MF-Mac-Handoff/kits/graphics-0.4.6/install.sh
```

Reboot manually. Verify Glass. Close System Settings and run; move/resize a heavy Safari window for20seconds:

```bash
sudo bash /Users/spotlight1/Projects/G6MF-Mac-Handoff/kits/graphics-0.4.6/test-desktop.sh
```

Test enables direct_present=1 and leaves it active on success. On failure it disables direct present and the private cache. Kernel automatic direct-present failure shutdown remains active.

Disable new cache live:

```bash
sudo bash /Users/spotlight1/Projects/G6MF-Mac-Handoff/kits/graphics-0.4.6/set-private-cache.sh 0
```

Restore saved0.4.5 bundle and configuration, then reboot manually:

```bash
sudo bash /Users/spotlight1/Projects/G6MF-Mac-Handoff/kits/graphics-0.4.6/restore.sh
```
