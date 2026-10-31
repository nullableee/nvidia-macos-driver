# Graphics0.4.1: ограниченное удержание surface imports

Цель: сократить повторные imports/VA allocations, которые0.4.0 не устраняет
между освобождением временных обёрток. Это кандидат, ещё не проверенный
реальным WindowServer; причина no_backing в WS не установлена окончательно.

## Реализация

Режимы NVMTL_LIVE_SURFACE_REUSE либо WS-file g6mf-live-surface-reuse:
0=исходный путь;1=live-only weak cache;2=weak cache плюс ограниченный LRU.
Обычные приложения без явной настройки по-прежнему получают0.
Kit устанавливает mode2 только через существующий WS feature file.

На каждом NVMTLDevice удерживаются максимум8 VRAM-backed roots с суммой
учтённых spans не более64MiB. Span=max(IOSurfaceAllocSize,imported buffer size).
Это бюджет импортируемых поверхностей, не точный total RSS/VRAM всех
служебных объектов. Срока TTL нет: idle entries остаются до вытеснения,
явного flush или освобождения устройства. Для нескольких устройств лимит
применяется к каждому отдельно.

Ключ прежний: IOSurfaceID,plane,width,height,format,resourceoptions,FBO.
Root удерживает IOSurface, поэтому его ID не может быть переиспользован
другой поверхностью во время удержания. Private fallback не удерживается.
Проверка ShaderWrite/storage capability и pixel/seed paths сохранены.
Вытеснение удаляет только ссылку кэша: live aliases/command buffers сохраняют
собственное владение root. Lookup/touch/insert идут под существующим
@synchronized(device); worker/timer для кэша не добавлен.

Добавлен repeat_miss counter: отсутствие root при ключе, уже встречавшемся
в последних128 miss keys. Он хранит только числовые ключи, не surfaces.
В mode1 recycled ID может дать повтор: это подсказка, не identity proof.
Редкие os_log строки G6MF0.4.1 сохраняют прежние counters.

## Нативная проверка

На GPU в отдельных процессах с прямой загрузкой кандидата:

- Live-only negative control после освобождения anchor вернул ожидаемый12;
  bounded mode сохранил root и тот же parent у следующих wrappers.
- BGRA1920x1200 и RGBA16Float, включая full1920x1200:60frames с новыми
  CPU patterns и GPU-write patterns, полное побитовое readback сравнение PASS.
- Compute channel swizzle2048pixels PASS в mode2.
- 50lifecycles/4000concurrentwrappers PASS отдельно mode1 и mode2;
  flush после снятия cache ownership освобождает последние roots.
- LRU8entries, touch-before-evict, byte-budget и last-alias lifetime PASS.
  При12fullBGRA поверхностях осталось7entries/64512000bytes; oldest released.
- GPU readback после удаления caller/cache refs до submit PASS: command buffer
  сохраняет import до завершения работы.
- API-only transient-wrapper probe: mode1=120created/0hits/119repeatmiss,
  mode2=1created/119hits/0repeatmiss.76.552→3.111мс за120APIcalls.
  Нет compositor/draw/display benchmark: не переводить ускорение API в FPS.

Модельные Bash installer tests: success+restore и отказы hold/pixel/stress/
swizzle/LUT/serial/signature PASS. Дополнительно success/restore и hold/LUT
failure проверены с существующим featurefile1, как на текущей системе:
после rollback возвращается именно1. Всего11случаев. Реальный root installer
не запускался.

## Kit

kits/graphics-0.4.1 содержит signedpayload, guardedinstaller, nativeprobes,
profilecollector иrestore. Перед заменой stagingbundle проходит hold,
boundedstress, pixel-mode2 без внешнего anchor, half, swizzle и live-stress;
после публикации — LUT/shader и serial probes. Ошибка вызывает rollback.
Backup включает весь текущий0.4.0bundle иfeaturefile1. EFI/kexts не меняются.
После reboot нужны проверка Glass/цветов и реальная WS-телеметрия. Новый
GPU timeout/crash или ухудшение — основание откатить, а не отключать fence.
