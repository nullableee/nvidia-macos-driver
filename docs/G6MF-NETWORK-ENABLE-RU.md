# Bluetooth и Ethernet: обнаруженные отключённые записи EFI

В контрольном сборе Tahoe Bluetooth Intel AX211 присутствует как USB
8087:0033 в IORegistry. В Linux Ethernet определён как Realtek 10ec:8168.
На флешке уже есть IntelBluetoothFirmware 2.5.0, IntelBTPatcher 2.5.0,
BlueToolFixup 2.7.3 и RealtekRTL8111 2.4.2. Однако все четыре записи
Kernel/Add имели Enabled=false. Соответствующие сторонние драйверы в
последнем списке загруженных kexts отсутствуют. Firmware personality
совпадает с 8087:0033; IOPCIMatch Ethernet включает 0x816810ec.

Подготовлено минимальное изменение: четыре Enabled=true; три Bluetooth
записи упорядочены firmware → patcher → BlueToolFixup после Lilu/AMFIPass.
Остальные значения config.plist сохранены, что проверено сравнением
декодированных plist. Обе конфигурации проходят ocvalidate 1.0.8.
Бинарники kexts не заменялись. Это устраняет обнаруженную причину отсутствия
загрузки, но работа Bluetooth pairing и проводной передачи в Tahoe требует
проверки на ноутбуке.

Индивидуальная EFI и её точная резервная копия остаются вне Git, в
G6MF-Network-Enable-2026-10-30 на рабочей машине и флешке. Там также
change.json с хешами, restore-network.sh с проверкой текущего хеша и
collect-network.sh. Изменён активный USB EFI/OC/config.plist.
Исходный графический профиль сохранён в backup/config.plist.

Полностью выключить ноутбук и затем загрузить Tahoe с этой флешки.
Проверить Ethernet с подключённым кабелем и Bluetooth. Собрать состояние:

    sudo bash /Volumes/1401/G6MF-Network-Enable-2026-10-30/collect-network.sh

Дождаться NETWORK COLLECTION COMPLETE. Сборщик только читает состояние,
все команды ограничены по времени; сохраняются статусы и частичный вывод.
Пакеты графики, Wi-Fi и настройки USB mapping не менялись. Если контроллер
есть, но прошивка/сопряжение не работают, следующий отчёт позволит отличить
загрузку кекстов, USB-видимость и ошибку bluetoothd.

Основания для состава Bluetooth-набора и холодного запуска:
https://openintelwireless.pages.dev/IntelBluetoothFirmware/FAQ
https://openintelwireless.pages.dev/IntelBluetoothFirmware/Troubleshooting
Ethernet: https://github.com/Mieze/RTL8111_driver_for_OS_X
