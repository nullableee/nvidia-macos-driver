# G6MF — Sequoia 15.8.2 (24H232), Serial LUT v9.2

**Ветка для экспериментов Sequoia; main остаётся снимком Tahoe.** Машина: GIGABYTE G6 MF, RTX 4050 (28A1), Intel iGPU (A7A0), muxless, внутренняя панель 1920×1200 ≈165 Гц. Изменения EFI и разделов Linux/Windows в этот перенос не входят.

## Работающая конфигурация (1 ноября 2026 г.)

- macOS 15.8.2 build `24H232`;
- `NMIntelFB.kext` 0.1.4, `NVAccel.kext` 0.1.8, `NVRM.kext` 2.6.4, `NVRMAGDC.kext` 2.6.6, `NVRMFB.kext` 0.1;
- изменённый NVIDIA Metal `NVMTLDriver.bundle` 0.4.7;
- `/Library/NullMoth/g6mf-lut-limit` = 1024; `/Library/NullMoth/g6mf-lut-serial` = 1;
- Serial LUT v9.2: in-process rebinding only for the precise `RunFullDisplayPipe` LUT `dispatch_apply` call, guarded by UUID and call/block identity.

## Данные для переноса hook

| Свойство | Значение |
|---|---|
| CoreDisplay UUID | `37573E08-0E1B-3981-988C-0AFBCA6C9AA7` |
| CoreDisplay __TEXT SHA-256 | `942e14ede3f404499171471997480d364fbafb74577c414beaf2fa8fd76395d6` |
| __TEXT vmaddr | `0x7ff80404c000` |
| dispatch_apply call | `0x7ff8041121ff` |
| dispatch_apply stub | `0x7ff8041411f2` |
| LUT block_invoke | `0x7ff80411293c` |

Изменённый файл `tools/g6mf_lut_serial_sequoia.c` основан на Tahoe `tools/g6mf_lut_serial.c` из коммита `e556902`. **Не использовать Tahoe-адреса с Sequoia.** Полные бинарные дампы CoreDisplay, локальные audit ZIP и частные пользовательские логи намеренно не включены.

## Аппаратная проверка

В системном журнале рабочего WindowServer были обе записи:

```text
2026-11-01 04:52:19 G6MF-LUT-SERIAL: import installed
2026-11-01 04:52:20 G6MF-LUT-SERIAL: matched real CoreDisplay LUT, entries=1024; serial execution
```

До v9.2 профиль WindowServer включал 4242 сэмпла в `RunFullDisplayPipe` из 5150 по главному потоку (82.4%), со множественными `CurrentHeadroom → __psynch_mutexwait`. После установки основной bottleneck исчез; в последующем профиле основная активность включала композитинг `QuartzCore / CompositorMetal`. Тесты не полностью сопоставимы по нагрузке, количеству сэмплов и времени.

## Счётчики передачи на панель (по 20 секунд)

| Режим | Копий/с по VBL | Среднее total | Среднее copy | copy_skip | Интервалы ≥40 мс |
|---|---:|---:|---:|---:|---:|
| Serial LUT, direct=0, copy64=0, первый замер Terminal | 95.30 | 5.2592 мс | 2.0039 мс | 94 | 6 |
| Serial LUT, direct=0, copy64=0, отдельная серия | 88.27 | 5.0941 мс | 1.9993 мс | 48 | 2 |
| Serial LUT, direct=1, copy64=0 | 89.48 | 3.3244 мс | 2.1164 мс | 4 | 4 |
| Serial LUT, direct=0, copy64=1 | 85.57 | 4.7991 мс | 1.8043 мс | 26 | 8 |

Условие `direct=1` установлено по описанию проведённого теста; файл perf не сохранял само значение переключателя. Метрики — **копирования на панель, не уникальные FPS приложения**. Отличия условий движения окон не позволяют сделать строгий A/B-вывод по FPS. Счётчики GPU timeout и IOP fail в этих тестах не росли.

## Выводы и ограничения

- Serial LUT устранил наблюдавшееся массовое ожидание `CurrentHeadroom` и резко улучшил субъективную плавность. Пользователь также заметил уменьшение шума ноутбука, но температура и мощность не измерены.
- `direct_present=1` в отдельных тестах снижал среднее total и число пропущенных копирований, но не доказал существенный прирост копий/с.
- `copy64=1` ускорял копирование, но не улучшал общий результат теста; по умолчанию не включать.
- В коде NVAccel при успешном Direct Present обычный путь копирования не вызывается; `copy64` работает только при fallback, а не поверх Direct Present.
- Экспериментальные sysctl переключатели сбрасываются при перезагрузке. Автоматическое включение не вносилось в EFI.

## Воспроизводимость

Исходный v9.2 kit (скрипты `prepare.py`, `install.sh`, `macho_validate.py`, `macho_text.py`, исходники и README) был собран локально и проверен `install.sh check`, `install.sh install`, после чего реальный WindowServer сообщил о совпадении LUT. Kit **не включён в этот первый коммит**: хранится в локальной папке `~/Downloads/G6MF-Sequoia-SerialLUT-v9.2` и должен быть добавлен отдельным коммитом после просмотра `git status`, исключения `build/`, дампов и подписанных бинарников. Не включать ZIP с Apple CoreDisplay или приватные ключи.

Базовые документы Tahoe сохранены в `docs/G6MF-SERIAL-LUT-V9-RU.md` и `docs/G6MF-SERIAL-LUT-V9-CONTROL-RU.md`.
