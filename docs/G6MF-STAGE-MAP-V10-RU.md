# v10: эксперимент mapped staging copy

Подготовлен в macOS 26.7.1 / 25G241, NVAccel 0.1.5. Native x86_64 сборка
и проверки metadata прошли. На железе v10 ещё не установлен и не измерен;
заявлять прирост частоты или 165 FPS нельзя.

После успешного CE pageoff эксперимент временно отображает подготовленный
IOSurface memory descriptor в writable kernel VA и переносит staging RAM
через bcopy. Отображение освобождается в том же вызове под staging lock.
Отказ, нулевой адрес или короткое отображение возвращают исходный writeBytes.
Изначально debug.nvaccel_stage_map_copy=0; значение 1 включает эксперимент.
Отображение каждый раз создаётся/освобождается: его стоимость может оказаться
выше выигрыша от замены writeBytes. Persistent writable mapping не вводится.
Это по-прежнему два CPU-копирования: staging → IOSurface → Intel scanout.

Не меняются ожидание fence, готовность GPU, обработка timeout и запрет
копировать устаревший muxless кадр. Добавлены счётчики stage_map_ok,
stage_map_fallback, copy_lock_miss и copy_pageoff_fail. Последние два
разделяют исчерпание try-lock и неудачную синхронизацию surface. Это счётчики
вызовов соответствующих путей, а не независимые измерения FPS панели.

Production helper проверен ASan/UBSan: копирование, release, failed/null/short
mapping, fallback, границы и short write. Native build не заменяет проверку
реальных отображений и frame pacing после установки.

Комплект установщика использует существующий guarded bridge updater с
проверкой точных хешей установленного стека, candidate/live AuxKC и откатом.
Берёт неизменённый установленный NMIntelFB; фактически меняется NVAccel.
EFI, NVRAM, LUT и Intel/Julionectar-компоненты не меняются. A/B-скрипт
переключает 0/1 и возвращает исходное значение при завершении/ошибке.
Не выгружать рабочие графические kext на лету.

Отдельная проверка сети: журнал целевого Mac за 30 октября 12:20 показывает
SAFE BOOT DETECTED и отказ загрузки IntelBluetoothFirmware/IntelBTPatcher
именно из-за безопасного режима. Причина входа в Safe Boot не установлена.
Новые сетевые kext и индивидуальный EFI остаются вне Git. Первый этап
включает только обновлённый Ethernet; Bluetooth проверяется следующим этапом.
