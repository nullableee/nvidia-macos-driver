# v14: локальный кандидат live IOSurface wrapper reuse

Эксперимент касается только Metal plugin, не установлен в систему.
NVMTL_LIVE_SURFACE_REUSE=1 разрешает существующему weak cache использовать
также VRAM-backed backing, если shader-write usage не требует отсутствующего
storage view. Геометрия/plane/format/resource options/framebufferOnly
остаются частью исходного ключа. Alias удерживает исходный root через
_parent; новая схема не удерживает root дольше последнего живого alias.
Никакого strong cache, global GPU-resource cache или pin-through-idle здесь нет.
Самая дорогая часть нового wrapper — повторный family VRAM import/map —
при попадании пропускается; создаётся typed view существующего изображения.
При miss/невозможности view исходный путь остаётся fallback.

Предложение shared host-pages pin отложено: в нашем sample SurfaceIn лишь
12/1812 main-thread отсчётов. Кроме того per-texture hostPages cache в исходниках
уже реализован с256MB cap. Этот патч решает другую часть — повторный live
VRAM-wrapper import — и не заявляет внедрение внешнего патча issue368.

Собран native release plugin на Mac, x86_64/minos15.0; только локальный файл
builds/live-reuse-v14/NVMTLDriver. Probe tools/g6mf_live_surface_probe.m
сначала загружает кандидат dlopen, затем напрямую создаёт NVMTLDevice
через текущий NVAccel. dladdr подтверждает путь именно локального кандидата;
системный NVMTL/WindowServer/kexts не заменяются.

Важная находка: release constructor очищает NVMTL_* env. Первые прогоны
поэтому шли с экспериментом0 и НЕ считаются проверкой новой ветви.
Исправленный probe задаёт NVMTL_LIVE_SURFACE_REUSE после dlopen, используя
G6MF_TEST_REUSE. Интроспекция подтвердила anchor_vram1, alias parent==anchor
в режиме1 и parent!=anchor в режиме0. В коде WindowServer такой env override
не внедрялся; будущая установка потребует штатной config-интеграции.

GPU pixel test: циклы8 размеров64..176x32, по20 CPU-обновлений IOSurface,
каждый раз новый wrapper, GPU blit в независимую texture и readback всех
пикселей. Дополнительно обратный GPU blit новой (отличной от исходной CPU)
картинки через alias и чтение через anchor. Финальная версия теста проверяет
этот отличающийся pattern. Full-panel1920x1200:3x20 кадров при mode0 иmode1,
точное совпадение каждого пикселя. Нет сообщения об ошибке GPU.

Full-panel synthetic totalms на20frames:
mode0 296.135/203.798/245.867;
mode1 (первый прогон)256.274/190.060/179.188;
финальный build mode1 234.354/151.358/186.300.
Это смешанный upload/blit/readback CPU-verification benchmark в разных
процессах, а не WindowServer FPS/A-B с контролем всех условий. Не обещать
по нему процент общего FPS. Поздний прогрев мог повлиять на результат.
Локальная копия v9 wrapper с изменённым только REAL_PLUGIN для загрузки
кандидата также прошла small pixel test. Настоящий WindowServer/LUT hook
этот прогон не квалифицирует: процесс сохранял обычное probe имя.

Перед установкой остаются: lifecycle после освобождения всех aliases,
параллельные wrapper-потоки, swizzle/usage разнообразие, проверка настоящей
WindowServer-only политики локальным probe и guarded installer с откатом.
Не предлагать слепую замену установленного g6mf-original.

## Дополнительные завершённые проверки и комплект

50 lifecycles/4000 wrappers на4потоках: PASS; последняя живая alias
удерживает root, после выхода всехpool weakRoot=nil. Разные resource
options не используют старый backing. RGBA16Float pixelcopy: PASS.
Swizzle compute read проверил2048пикселей и фактическую перестановкуR/B:
PASS. При первом запуске shader probe не нашёл translator возле локального
payload; после копирования неизменённого установленного libnvmtl_translate
в локальную buildдиректорию shader/swizzle прошёл. В установщике кандидат
создаётся копией полного текущего bundle, поэтому runtimeбиблиотеки рядом.

Комплект kits/live-reuse-v14 готов, но не установлен. Feature helper
кэширует настройку при первомиспользовании: явный NVMTL env (пробы/конфиг),
иначе только WindowServer читает g6mf-live-surface-reuse. Установщик
пишет1, не меняя nvrm610.conf. Release очищает inherited NVMTL env, поэтому
штатный WindowServer включается именно root-файлом.
Сохранениеbundle+config, root native probes до/послепубликации, rollback
на ошибках и явный recovery. Модельные installer tests используютнастоящие
Bash/cp/mv/shasum с mockDarwinподписью иnativeprobes; аппаратнаяустановка
и уникальныйFPS WindowServer пока не проверены.
