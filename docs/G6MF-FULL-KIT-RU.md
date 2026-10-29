# Полный экспериментальный комплект для G6 MF / Tahoe

База: официальный NullMoth 2.6.4 из f95f4d24a42f88f9bc71fba12c90bcfe8e060225.
SHA-256 исходного архива:
90f4c677f0e15caae69d90136990c88556bed27ba4499fd580ebdf9dcdb9244e.
NVRM, GSP 615.78.08, Metal-плагин, translator и NVK сохранены из релиза.
NMIntelFB, NVAccel Tahoe и NVRMFB заменены нашими проверенными сборками.
Весь стек на этом ноутбуке ещё не проверен; работоспособность Metal не заявляется.

Первый запуск проверяет RTX/GSP и Metal без захвата Intel-экрана:
`nmoptimus=1 -nmintelfboff`. Мост присутствует, но NMIntelFB отказывается
от устройства по флагу. Экран остаётся на firmware framebuffer Intel.
Не выполнять sysctl debug.nvaccelfb и не удалять -nmintelfboff на первом тесте.
Не запускать штатное автообновление NullMoth: оно заменит экспериментальные kext.

## 1. Linux: активировать подготовленный профиль EFI

```bash
python3 /run/media/spotlight/1401/NullMoth-G6MF-Full-v1/prepare-efi.py --activate
```

Полная текущая EFI сохраняется рядом в EFI-before-G6MF-Full-ДАТА.
Добавляются nvfb/nvaccel, nmoptimus и параметры допуска драйвера из README
upstream; csr-active-config объединяется с 0x0A43, SecureBootModel Disabled.
BAR и ACPI сохраняются. Диагностический NMIntelProbe отключается.
Драйверные kext в EFI не добавляются: они будут загружаться из Auxiliary KC.
В комплекте может уже быть staged-профиль; он сам по себе не активен.

## 2. Tahoe: установить

Загрузиться через эту флешку и выполнить в обычном Terminal:

```bash
sudo bash /Volumes/1401/NullMoth-G6MF-Full-v1/install-macos.sh
```

Интернет, Python и Xcode на Tahoe не нужны. Пакет распаковывается на macOS-диск,
проверяется по SHA-256, а затрагиваемые файлы сохраняются на APFS в
/Users/Shared/G6MF-Backups/before-full-ДАТА. На FAT32 системные файлы
не копируются. Установщик проверяет линковку тестовой Auxiliary KC до замены
драйверов и затем проверяет итоговую KC. Это первая фактическая проверка
связывания всех компонентов именно с ядром пользователя.
Драйвер Intel/NMXGPU отдельно не удаляется и его kext не заменяется.
Общие каталоги GPUBundles/nvmtl обновляются установщиком и включены в откат.

Дождаться INSTALL COMPLETE. Если macOS просит разрешить расширения, сделать это
в System Settings → Privacy & Security. Перезагрузиться через флешку 1401.
При ошибке установки не перезагружаться вслепую: сохранить last-install.log
и весь вывод Terminal. Wrapper пытается вернуть исходные файлы при отказе.

## 3. Tahoe после перезагрузки: проверить и собрать

```bash
sudo bash /Volumes/1401/NullMoth-G6MF-Full-v1/collect-full.sh
```

Скрипт ждёт публикации headless Metal, запускает готовый x86_64 metal-probe
и собирает обычную диагностику. Выбирается NVIDIA, не случайная другая GPU.
Metal test отправляет blit-команду копирования 4096 байт и проверяет readback;
есть таймаут. Это проверка очереди/буферов, не шейдеров и не вывода на экран.
Дождаться FULL COLLECTION COMPLETE, вернуться в Linux с флешкой.

## Откат

В Linux вернуть профиль EFI:

```bash
python3 /run/media/spotlight/1401/NullMoth-G6MF-Full-v1/prepare-efi.py --restore
```

В обычной Tahoe использовать точный путь backup, напечатанный установщиком:

```bash
sudo bash /Volumes/1401/NullMoth-G6MF-Full-v1/rollback-macos.sh /Users/Shared/G6MF-Backups/before-full-ДАТА /
```

В Recovery сначала разблокировать/смонтировать macOS Data volume. Передать
его абсолютную точку монтирования вторым аргументом и путь к backup на нём
первым. Например (заменить имя тома и ДАТА реальными):

```bash
bash /Volumes/1401/NullMoth-G6MF-Full-v1/rollback-macos.sh "/Volumes/Macintosh HD - Data/Users/Shared/G6MF-Backups/before-full-ДАТА" "/Volumes/Macintosh HD - Data"
```

Откат восстанавливает сохранённые файлы и Auxiliary KC той же установки,
без cmp, Python, компилятора или сборки KC в Recovery. EFI откатывается отдельно.
Восстановление старой KC после обновления macOS требует отдельной проверки;
не обновлять macOS между тестом и откатом.

## Проверяемые границы

Успешная сборка и тест Intel plane не доказывают RTX/GSP или Metal.
Даже успешный blit/readback не доказывает шейдеры, WindowServer, head-4 copy,
165 Гц, сон, переключение режимов или долговременную стабильность.
После первого отчёта решается включение NMIntelFB и реального вывода.
Результаты upstream в UPSTREAM-BASELINE-IDENTITY.json относятся к upstream,
не являются результатами этого патча или этого ноутбука.
