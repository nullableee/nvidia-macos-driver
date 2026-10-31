# v13: диагностика только после входа
NVAccel0.1.7. Раздельные метрики v11 управляются nvaccel_latency_diag,
по умолчанию0: без вызовов часов/накопления новых метрик при старте.
AGDC остаётся установленный проверенный2.6.6. Mapping по умолчанию0.
Это новый кандидат: его стабильность на железе ещё не подтверждена.

sudo bash install.sh → OPT-IN LATENCY READY → reboot → проверить Glass.
При сохранении Glass прогреть обычные анимации несколько минут, затем
sudo bash profile-perf.sh. На20с включатся замеры и после завершения
восстановится исходный переключатель, включая INT/TERM/ошибку.
При ухудшении: sudo bash restore-working.sh → reboot.

Метрики глобальные, вложенные/пересекающиеся и с разными популяциями.
po_ce включает весь platform call, не чистое аппаратное время CE.
Пиковые значения max накоплены с загрузки; считать дельты count/ns.

Native build/metadata/import comparison прошли; новых undefined imports
относительно рабочего0.1.5 нет. Production timing/collector tests прошли.
Shell wrapper проверен на временных mock sysctl: включение во время profile,
возврат исходного значения при успехе и ошибке child profile. Установщик
использует прежний guarded candidate/live AuxKC update и backup/rollback.
Native root installation и hardware validation ещё не выполнялись.
Отчёты по успешному сбору передаются SUDO_UID/SUDO_GID, сохраняя закрытый
режим каталога; это позволяет читать отчёт в следующем чате без root.
