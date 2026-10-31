# AGDC v12: отдельный эксперимент запуска
Только NVRMAGDC2.6.6; NMIntelFB берётся побайтно из установленного стека.
NVAccel0.1.5, NVRM, LUT, EFI и сетевые компоненты не заменяются.
При nmoptimus1 приоритет строгого Intel-panel/NVIDIA-broker маршрута;
предельное ожидание targets 20 попыток с 19 паузами по100мс на thread_call.
State=-1 теперь появляется после исчерпания попыток; новый запрос1 очищает
прошлый отрицательный state в pending0. Появление ложного NVIDIA head не
разрешает обойти отсутствие или неоднозначность muxless targets.
Причина lookup failure в аварии v11 пока не доказана: это кандидат,
исправляющий найденные пробелы обнаружения, а не установленное объяснение
всех прошлых падений и не оптимизация FPS.

sudo bash install.sh → только после AGDC UPDATE READY перезагрузка.
Проверить Glass/ускорение и sudo bash collect-startup.sh.
При ухудшении sudo bash restore.sh → перезагрузка.
Оригинальный full updater сохраняет компоненты/AuxKC и проверяет candidate
и live KC. Сам установщик native/root ещё не выполнен.

Проверки: production target selection и 0x980 mapping с ASan/UBSan,
наличие ложного NVIDIA-head при muxless opt-in, отказ при отсутствующем
broker, legacy-index и ambiguous-broker отказ, сохранение desktop fallback.
Production retry helper проверен для готовности на каждой попытке1..20,
исчерпания20/19, выключения до первой попытки и отмены после ожидания.
Native x86_64 сборка NVRMAGDC и metadata прошли. Модельные сценарии
установки/отката AGDC existing updater прошли. Hardware validation pending.

NVRM auto-go пока сохраняет исходное поведение display PARTIAL после
неустранимого отказа. Этот кандидат не гарантирует корректную fallback
загрузку при постоянном отсутствии панели/broker; предел ожидания намеренно
укладывается в существующее пятисекундное окно опроса AGDC. До проверки
не сочетать его с новым NVAccel или иными графическими экспериментами.
