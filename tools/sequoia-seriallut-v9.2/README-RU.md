# G6MF Serial LUT v9 — macOS Sequoia 15.8.2 (24H232)

Это отдельный **экспериментальный перенос** оптимизации Serial LUT v9 из форка
nullableee/nvidia-macos-driver для GIGABYTE G6 MF с RTX 4050 и Intel A7A0.
Текущий Metal 0.4.7 должен быть уже установлен и проверен; установленным
NVAccel, NMIntelFB, NVRM, NVRMFB, NVRMAGDC ничего не делается.

## Основание переноса

Аудит пользователя CoreDisplay 24H232:
- UUID `37573E08-0E1B-3981-988C-0AFBCA6C9AA7`;
- SHA-256 полного `__TEXT`: `942e14ede3f404499171471997480d364fbafb74577c414beaf2fa8fd76395d6`;
- вызов `dispatch_apply`: `0x7ff8041121ff` → `0x7ff8041411f2` (несдвинутые адреса);
- возврат после вызова: `0x7ff804112204`;
- LUT `block_invoke`: `0x7ff80411293c`, подтверждён прямым `lea` в `0x7ff804111fb5`.

Оригинальный код Tahoe из `tools/g6mf_lut_serial.c` заменяет import указатель
`dispatch_apply` **только в WindowServer и только для конкретного вызова LUT**.
Остальные вызовы передаются исходной функции. Кроме того, обёртка выставляет
WindowServer-only лимит 1D LUT 1024, как в аппаратном эксперименте Tahoe v9.

**Это не тестировалось на Sequoia в работающем WindowServer.** Совпадение
машинного кода, отдельный serial-probe и GPU-probe не гарантируют стабильность
после перезагрузки. Не запускайте старый Tahoe-инсталлятор v9.

## Исправления v9.2

В v9.1 preflight обнаружил, что подпись переименованного бинарника Metal 0.4.7
по-прежнему ссылается на исходный `Info.plist` внешнего bundle. Это привело
к `invalid Info.plist ... In subcomponent: NVMTLDriver.g6mf-original`.

Новая версия сначала выносит оригинальный Metal Mach-O **только из копии
кандидата** в отдельный временный файл, переподписывает как самостоятельный
Mach-O, проверяет `__text` после переподписания, возвращает его в кандидат,
а затем подписывает внешнюю обёртку и проверяет `codesign --deep --strict`.
Так предписывает Apple для вложенного кода. Все действия до `CHECK PASS`
происходят в одноразовом каталоге, действующая установка не меняется.

На macOS этот конкретный этап ещё не был проверен аппаратно. Не переходите
к `install`, пока не появится `CHECK PASS`.

## Исправление v9.1

Первая упаковка v9 ошибочно использовала ограничение `len(Mach-O)>10000` для
`serial-probe` и `lut-probe`. Компоновщик может выпускать корректный x86_64
`MH_EXECUTE` меньшего размера. В v9.2 вместо порога проверяются заголовок,
архитектура, filetype, таблица load commands и наличие `__TEXT`.
Используется **новый каталог**, чтобы не пересекаться с частичной сборкой v9.
Ни установка, ни замена файлов системы в предыдущей попытке не происходили.

## Подготовка и проверка

Положите уже созданный `G6MF-Sequoia-CoreDisplay-audit.zip` на рабочий стол,
по пути `~/Desktop/G6MF-Sequoia-CoreDisplay-audit.zip`.

```bash
cd ~/Downloads/G6MF-Sequoia-SerialLUT-v9.2
python3 macho_validate.py --self-test
python3 prepare.py --verify-only
python3 prepare.py
sudo bash install.sh check
```

Первый шаг **только читает** пользовательский аудит. Второй компилирует
трёхкомпонентный x86_64 Mach-O комплект с установленным Xcode CLT,
ничего не устанавливая. Последний проверяет установленный Metal 0.4.7
побайтно по `__TEXT,__text`, пакет, версии kext и подпись пробного bundle.
Ожидается `CHECK PASS`.

Только после CHECK PASS установка:

```bash
sudo bash install.sh install
```

Установщик сохраняет полный текущий `NVMTLDriver.bundle` и файлы политик,
ставит wrapper вместо бинарника Metal 0.4.7 (сам бинарник переименовывается в
`NVMTLDriver.g6mf-original` в том же bundle), подписывает пакет и запускает
**отдельные процессы** для serial probe и Metal shader probe.
При ошибке до READY предыдущий bundle и параметры восстанавливаются.
Успешный вывод: `SERIAL LUT V9 READY for Sequoia 24H232`.

Затем вручную перезагрузите macOS через прежний USB OpenCore:

```bash
sudo reboot
```

После загрузки проверьте системный журнал:

```bash
log show --last 5m --style compact --predicate 'eventMessage CONTAINS "G6MF-LUT-SERIAL"' | tail -20
```

Ищите **оба** сообщения `import installed` и `matched real CoreDisplay LUT`.
Если нет второго — ускорение не активировалось, даже если probe прошёл.
Затем повторите `sample WindowServer` под нагрузкой Safari и сравните плавность.

## Отключение и откат

После установки в терминале будет напечатана абсолютная команда `RESTORE`.
Она сохранена также в резервном каталоге вида:
`/Users/Shared/G6MF-Backups/seriallut-sequoia-.../restore.sh`.

Чтобы выключить только serial hook на следующую загрузку:

```bash
sudo bash ~/Downloads/G6MF-Sequoia-SerialLUT-v9.2/install.sh disable
sudo reboot
```

Полный откат всего wrapper и обеих LUT-политик (Metal 0.4.7 остаётся):

```bash
sudo bash ~/Downloads/G6MF-Sequoia-SerialLUT-v9.2/install.sh restore
sudo reboot
```

Если WindowServer перестал запускаться, не стирайте macOS: через Recovery
или Linux найдите Data-раздел и поменяйте **только** файл
`Library/NullMoth/g6mf-lut-serial` на `0\n` в его фактической точке монтирования.
Это выключит hook при следующем старте WindowServer; полный откат возможен
затем из macOS. Не меняйте `csr-active-config`, EFI, kext или другие диски.

## Изменяемые объекты

- `/Library/GPUBundles/NVMTLDriver.bundle` — обёртка и сохранённый Metal 0.4.7
- `/Library/NullMoth/g6mf-lut-limit` — 1024
- `/Library/NullMoth/g6mf-lut-serial` — 1 для включения
- `/Library/NullMoth/g6mf-seriallut-sequoia-backup` — путь резервной копии
- `/Users/Shared/G6MF-Backups/seriallut-sequoia-*` — полный откат

Не изменяются Apple CoreDisplay на диске, Kernel Collections, EFI, Realtek Ethernet,
BIOS и разделы SSD. Вся модификация `dispatch_apply` выполняется в памяти
процесса WindowServer, после проверок UUID и конкретной инструкции.
