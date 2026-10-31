# Разбор задержек v10

Анализируется главный ws_main_thread отдельно от вспомогательных потоков.
Скрипт tools/g6mf_analyze_ws_sample.py выделяет эксклюзивные листья и
проверяет их сумму против числа отсчётов корня. Нельзя суммировать
вложенные строки sample как независимые CPU-затраты.

В mode0 всего 1836 отсчётов главного потока, в mode1 — 1808.
Mach trap: 569 и 801. Из них обычное ожидание событий в server_loop:
348 и 380. Их нельзя объявлять ожиданием GPU.

Ключевой изменившийся путь:
nvmtl_vk_surface_mark_newest → nvkmd_nvrm_surface_dirty → nvRmApiSurfShare
→ nvrm_xnu_ioctl → IOConnectCallMethod → mach_msg2_trap:
24 отсчёта в mode0 против 292 в mode1. Это присутствие потока внутри
синхронного вызова ядра, а не прямое измерение удерживающего mutex потока.

Код NVAccel объясняет правдоподобный механизм: nvAccelSurfCopyReady
захватывает nvFamLock и вызывает pageoff до nvFamUnlock. Pageoff включает
ожидания, prepare, staging lock, CE, CPU write и complete. Обычный SURF_DIRTY
(без TRYLOCK-флага) также входит через блокирующий nvFamLock. Поэтому
удлинение pageoff способно остановить main thread на маркировке другой
поверхности и задержать отправку следующего GPU-кадра. Для доказательства
точной доли mutex-нужны раздельные kernel timings/стек владельца lock.
Не объявлять всю длительность Mach trap временем ожидания именно mutex.

Это согласуется с ростом ready с 2.31 до 7.89мс и отсутствием timeout,
pageoff failures и fallback. Крайне редкие lock_miss6/14 учитывают только
исчерпанные попытки copy path, а не все ожидания обычного blocking dirty.
Их низкое число НЕ исключает существенного blocking contention.

Исходный режим тоже имеет расходы выше scanout: в главном потоке
679 отсчётов на одной основной ветви render_update, 116 на одной ветви
serial LUT, а также выделение GPU VA, импорт памяти и descriptor updates.
Эти вложенные значения не складываются с родителями и не являются FPS.
В mode0 есть компиляция shader translator: она делает A/B неидеальным,
но не объясняет улучшение отключённого mapping относительно включённого.

Вывод для следующего изменения: отдельно измерить blocking nvFamLock,
prepare/complete, ожидание staging lock, CE platform call и CPU write.
Сокращать область family lock можно только после проверки lifetime ресурса,
сброса validity и гонки с новой GPU-записью. Просто снять lock вокруг CE
или сделать все DIRTY try-only опасно: это может вернуть старые пиксели.
Постоянное writable mapping может убрать повторный map/unmap, но требует
отдельного решения lifetime и инвалидации. Готового безопасного патча
на основании одного userspace sample пока нет.
