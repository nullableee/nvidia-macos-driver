# G6MF Sequoia: эксперимент descriptor miss audit

Дата: 2026-11-01. База: sequoia-15.8.2-g6mf (5da7cb1). Цель: понять, какие именно условия мешают повторному использованию VkDescriptorSet в WindowServer после исправления Serial LUT v9.2.

## Причина

В профиле после Serial LUT основной старый путь CoreDisplay CurrentHeadroom перестал доминировать; теперь в стеке видны CompositorMetal/QuartzCore и в отдельных выборках NVMTLDriver nvmtl_snapshot_set_md / NVK nvk_AllocateDescriptorSets и nvk_UpdateDescriptorSets. Наблюдения по sample не дают полного количества вызовов и не доказывают, что именно выделение descriptor sets ограничивает FPS.

Сейчас в форке уже есть NVMTL_DESC_MASK, повторное использование последнего набора, NVMTL_METADATA_REUSE и пакетное выделение максимум по 32 дескрипторных набора (dcache[32]). Не переносить эти механизмы заново из NullMoth 2.6.5/2.6.6.

## Что изменено

- Только opt-in инструментирование plugin/nvmtl_vk.c; **никакие** Vulkan-команды, пайплайны и решения о повторном использовании не изменены.
- Лёгкие атомарные счётчики классифицируют exact/table reuse, отсутствие предыдущего набора, смену layout/texel mask, неактуальный last set, рост storage_hi, рост mask, изменение используемых дескрипторов и прочие причины (например, смену страницы address table). Счётчики batch_hit и batch_miss показывают использование dcache внутри command buffer.
- По умолчанию аудит выключен. В отдельном тестовом процессе можно установить G6MF_DESC_AUDIT=1. Только WindowServer может включить через root-owned обычный файл /Library/NullMoth/g6mf-descriptor-audit с содержимым 1 или 1\n, без доступной другим пользователям записи. Проверка однократная для процесса.
- При включении вывод G6MF-DESC-AUDIT в unified log раз в 65 536 событий. Это process-local статистика; счётчики двух shader stages суммируются, события batch считаются дополнительно к результатам reuse/new.
- Новая классификация предназначена только для диагностики, а не является основанием без проверки делать skip vkUpdateDescriptorSets или повторно использовать набор после смены sampler/texture.

## Проверка (исходники без установки)

На машине с Xcode Command Line Tools:

    python3 tools/test_g6mf_descriptor_audit.py

Прежде чем собирать/устанавливать экспериментальный NVMTLDriver: отдельно убедиться, что компилируется весь исходный plugin вместе с новым заголовком; проходят имеющиеся tools/test_g6mf_descriptor_reuse.py, GPU render probe и проверки blur/скруглений. **Сейчас сборка на macOS и аппаратный тест не выполнены.** Не заменять рабочий Serial LUT v9.2 этим экспериментом.

Для профиля собранного экспериментального драйвера использовать те же 10–20 секунд движения Safari, те же параметры экрана; лог можно получить командой:

    log show --last 5m --style compact --predicate 'eventMessage CONTAINS "G6MF-DESC-AUDIT"'

Пока нет статистики miss, следующий кодовый оптимизационный патч делать преждевременно: новый алгоритм может нарушить правильность texture/sampler bindings и вернуть blocky blur (см. upstream issue #363). Итоговая цель — не просто меньше vkAllocate, а сохранение корректного изображения и реальный прирост копирований/с с меньшим количеством интервалов >20/40 мс.

Сравнения upstream: NullMoth 2.6.6 issue #356 о потолке compositor при 165–180 Гц; issue #363 о backdrop blur. Полный merge upstream запрещён в этом эксперименте.


## Следующая проверка: standalone GPU smoke

После компиляции этой ветки новой командой build_check.sh собирается отдельно проверяемый Mach-O.
Он не должен заменять исполняемый файл в текущем Serial LUT v9.2 bundle.
Прогон GPU проб запускается только явно:

    bash tools/g6mf_descriptor_smoke.sh "$HOME/Desktop/G6MF-descriptor-compile-.../NVMTLDriver"

Важен именно **новый** бинарник после коммита, в котором добавлен экспорт g6mf_descriptor_audit_stats.
Сценарий компилирует existing tools/g6mf_descriptor_render_probe.m во временную папку на Desktop,
выполняет по 2048 draw calls при обычном повторном использовании, sampler churn и pipeline-mask churn,
сверяет полученные пиксели и печатает process-local значения DESC_AUDIT после каждой пробы.
Счётчики не являются FPS и не отражают WindowServer без его собственного профилирования.
Без root, без установки плагина и без изменения ключей/EFI/запущенного WindowServer.
Невыполнение одного теста останавливает остальные, сохраняются логи и SHA-256.
Проба использует действующий NVAccel/NVK GPU и поэтому остаётся экспериментальной.
