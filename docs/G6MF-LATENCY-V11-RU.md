# ВНИМАНИЕ: v11 отозван после аппаратного сбоя

После установки пользователь потерял Glass/ускоренный WindowServer.
При обычной загрузке (safeboot0) был загружен NVAccel0.1.6. Два crash
reports показывают SIGABRT в CA::OGL::Context::push_surface через
FlattenNode::retain_surface. Причина assert пока не установлена; совпадение
по времени и успешный откат требуют считать v11 непригодным для установки.
Откат к сохранённому NVAccel0.1.5 вернул Glass и ускорение по подтверждению
пользователя; loaded version и stage_map_copy0 независимо проверены.
Локальный install.sh блокирует повторную установку. Предыдущие локальные
проверки не обеспечили совместимость с реальным WindowServer.

Ниже сохранено описание неудачного эксперимента для анализа.

# v11: раздельные замеры задержек

Установка: sudo bash install.sh. Только после LATENCY UPDATE READY
перезагрузиться. После входа несколько минут повторять обычные анимации,
затем sudo bash profile-perf.sh и 20 секунд двигать одно и то же окно.
Повторное сравнение с mapping=1 не требуется.

po_total — весь собственный pageoff, включая ранние выходы после входного фильтра.
po_gpu — повторное ожидание GPU внутри pageoff.
po_prepare / po_complete — wiring/unwiring IOSurface.
po_stagewait — ожидание глобального staging lock.
po_ce — wall time callPlatformFunction PAGEOFF; включает RM/CE/ожидания.
po_write — весь CPU stage write, включая mapping при его ручном включении.
dirty_lock — блокирующий nvFamLock для SURF_DIRTY без TRYLOCK-флага.
copy_hold — область после успешного lock в copyReady до выхода после unlock.

Метрики глобальные: pageoff разных ресурсов и DIRTY разных потоков, а не
только один displayed frame. Суммы вложенных времён НЕ складывать друг с
другом; dirty_lock и copy_hold могут измерять одновременные ожидание/работу.
max накоплен с загрузки. CE здесь не чистое аппаратное время GPU.
Путь данных/синхронизация не изменены, stage_map_copy default0.

Откат: sudo bash rollback-bridge-macos.sh "$(cat last-bridge-backup.txt)" /
Затем перезагрузка. Сохранять /Users/Shared/G6MF-Backups.

## Проверки до установки

Native x86_64 NVAccel 0.1.6 скомпилирован и связан, kmod/plist metadata
совпадают. Дополнительных undefined imports относительно установленного
v10 нет. Production timing tests проверяют атомарное накопление, максимум,
ранний выход и перевод времени; collector test выполняет настоящий awk
на mock snapshots, проверяет формат v11 и отказ при неполном snapshot.
Изменение не является ускорением: это раздельная диагностика подтверждённого
кандидата на contention. Эффект самих счётчиков аппаратно ещё не измерен.
Установщик повторно проверяет точные хеши живого стека, candidate и live
AuxKC; сохраняет предыдущий NVAccel, framebuffer и KC для отката.

Сетевой EFI не изменён. Не включать mapping=1 во время этого сбора.
