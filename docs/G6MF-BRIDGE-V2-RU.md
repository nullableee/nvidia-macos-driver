# G6 MF: шейдеры и следующий запуск Intel-моста

Предыдущий отчёт подтвердил RTX/GSP, NVRMRenderBridge и Metal blit/readback.
Эта версия добавляет настоящий compute-тест и исправляет двойной вызов
IOFramebuffer::start в ещё не включавшемся NMIntelFB. Новый NMIntelFB 0.1.1
(patch g6mf-v1.2) вызывает superclass один раз после выделения scanout/timer
и установки dependent properties. Поведение старта/отказов проверено тестом.

## Что делать

Активная EFI при подготовке не меняется. Уже установленные NVRM, NVAccel,
NVRMFB, Metal-плагин и firmware повторно устанавливать не требуется.

В обычной Tahoe, загруженной через текущую флешку, выполнить:

```bash
sudo bash /Volumes/1401/NullMoth-G6MF-Bridge-v2/next-stage.sh
```

Скрипт выполнит blit и затем скомпилирует MSL compute kernel на NVIDIA,
создаст pipeline, дважды запустит 1024 потока, сверит все результаты с CPU
и проверит 32 защитных слова после выходного массива. Есть общий таймаут
240 секунд и таймаут каждой GPU-команды. Xcode/Python на Tahoe не нужны.
Отчёт сохраняется в next-ДАТА на флешке даже при отказе шейдера.

При SHADER TEST FAILED ничего не обновляется и EFI не переключается.
Сохранить данные и вернуться в Linux; не выполнять дальнейшее включение вручную.

Только после SHADER PASS скрипт проверит новую NMIntelFB в тестовой Auxiliary KC,
сохранит прежнюю NMIntelFB и KC на APFS в /Users/Shared/G6MF-Backups/before-bridge-*,
обновит только NMIntelFB, пересоберёт и проверит итоговую Auxiliary KC.
При ошибке замены он пытается восстановить эти два объекта автоматически.
Затем сохранит всю действующую EFI в EFI-before-G6MF-Bridge-ДАТА и активирует
предварительно подготовленную копию. В ней удалён -nmintelfboff, добавлен
-nvrmnoflip; BAR, SIP, ACPI и остальные драйверы не меняются.
До перезагрузки экран продолжает работать через старый firmware framebuffer.

При NEXT STAGE READY разрешить обновлённое расширение, если macOS просит,
и перезагрузиться через ту же флешку. Во время следующего старта NVRM сам
попытается зарегистрировать Intel head 4 и включить передачу кадров.
Не выполнять sysctl debug.nvaccelfb вручную и не перезапускать WindowServer вручную.

После появления рабочего стола выполнить:

```bash
sudo bash /Volumes/1401/NullMoth-G6MF-Bridge-v2/collect-bridge.sh
```

В первые 15 секунд двигать окна на встроенном экране. Скрипт снимет счётчики
до/после и полную диагностику. Дождаться BRIDGE COLLECTION COMPLETE,
вернуться в Linux. Нужно доказать наличие NMIntelFB, head 4 в published/
registered/piped, рост количества скопированных кадров и видимый вывод.
Одна надпись Metal или успешный compute этого не доказывает.

## Если экран не появился

Вернуться в Linux и восстановить последнюю рабочую headless EFI:

```bash
python3 /run/media/spotlight/1401/NullMoth-G6MF-Bridge-v2/prepare-bridge.py --restore
```

Эта команда возвращает -nmintelfboff. Исправленная NMIntelFB останется
на диске, но не захватит Intel. Не нужно удалять весь NVIDIA-стек.
Если требуется вернуть саму NMIntelFB и KC, использовать напечатанный backup:

```bash
sudo bash /Volumes/1401/NullMoth-G6MF-Bridge-v2/rollback-bridge-macos.sh /Users/Shared/G6MF-Backups/before-bridge-ДАТА /
```

В Recovery вместо / передать точку монтирования macOS Data volume, а backup
указать полным путём на нём. Это восстановление двух сохранённых объектов,
без cmp, Python или сборки KC. Не обновлять macOS между тестом и откатом.

## Для комплекта, скачанного из CI

На Linux сначала распаковать комплект в корень 1401 и выполнить:

```bash
python3 /run/media/spotlight/1401/NullMoth-G6MF-Bridge-v2/prepare-bridge.py
```

Это только подготовка плана и копии EFI; shader-gate активирует её на Tahoe.
Для текущей флешки этот шаг уже выполнен при подготовке комплекта.
Ожидается точно прежняя сборка NMIntelFB из Full-v1; чужую версию updater
откажется заменять. Исходные профили EFI и предыдущие отчёты сохраняются.

Сон, изменение разрешения/частоты, длительная стабильность и все приложения
этим тестом не квалифицируются. Шейдер и вывод ещё требуют фактического теста.
