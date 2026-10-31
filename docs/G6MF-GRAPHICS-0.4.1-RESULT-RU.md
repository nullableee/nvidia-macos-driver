# Аппаратный результат0.4.1 и автоматическая анимация

Источники: kits/graphics-0.4.1/perf-20261030-174152-1019 и
profile-20261030-174152-1004. Metadata0.4.1 и loaded UUID
907A0E1B-18B2-3F8E-AE8F-F065A0C773B6 совпадают с kit. Feature2,
AGDC1, safeboot0, mapping0. Диагностический переключатель после теста0.

## Ручной профиль

| Метрика |0.4.0|0.4.1|
|---|---:|---:|
| Panel copies/s |78.57|86.29|
| Entry interval, ms |12.6677|11.5087|
| Fence, ms |0.6135|0.2887|
| Ready, ms |2.6915|2.4781|
| Intel copy, ms |1.8077|1.8215|
| Handler total, ms |5.1125|4.5841|
| CPU staging write, ms |1.7366|1.5352|

1728копий/20.024726с. Около+9.8% к предыдущему ручному прогону,
но не контролируемый A/B. Различаются нагрузка, время после boot и VBL
оценка (теперь6.1012мс). Это не точное число уникальных кадров приложения.
GPU timeouts в окне18→18, iop/pageofffail0, lockmiss+13.18timeouts были
до профиля; их наличие нельзя игнорировать или считать ошибками этого окна.
После дополнительных анимационных проб live timeout counter остался18.
Новых WS crash reports после прежних15:58 не найдено.

## Cache reuse подтверждён именно в WindowServer

17:41:57.637: calls4096, hits3600, created496.
17:42:12.360: calls7168, hits6671, created497.
Дельта3072calls,3071hit,1create =99.967%hits.
Более узкое окно4608→7168:2560calls/2560hits/0creates.
Это интервалы редких логов, не в точности начало/конец perf.
Во всех сводках privatehit/disabled/capability/viewfailed/createfailed0.
Ранее между512→2048 в0.4.0 было1536calls/0hits/1536creates.

Свежий main-thread sample содержит лишь2Mach leaf samples под alloc_va
и1подva_bind_mem; повторное создание импортов больше не прежний горячий
путь. Descriptor Update68, Allocate33, snapshot_set_md35 остаются среди
видимых листьев. Это sampling observations, не точные frame-ms или CPU%.
Полное сравнение diagnostics/graphics-0.4.1-main-comparison.json.

## Независимые автоматические пробы без установки

tools/g6mf_animation_probe.m создаёт собственную неактивирующую панель900x520
с движущимся оранжевым слоем.2с прогрев+12с замер, затем закрывается сама.
NSView CADisplayLink requested range30..165/preferred165; timestamps,
глобальные display counters читаются в процессе безsudo. Никакие настройки
драйвера/EFI или существующие приложения не изменяются.

Первый exploratory run:163.98callbacks/s,108.57panel copies/s.
Два последующих режима с измерением timing deltas:

| Режим | callbacks/s | copies/s | entry ms | handler ms | fence ms |
|---|---:|---:|---:|---:|---:|
| Клиент обновляет layer position каждый callback |163.98|104.07|9.4166|4.4515|0.2463|
| CABasicAnimation, callback только считает |163.99|108.82|8.9166|4.4279|0.2499|

Ready2.50–2.52ms, finalcopy1.70–1.73ms. Логи
builds/cadence-probe/{result,client-animation,server-animation}.txt.
Фон рабочего стола остаётся живым и неконтролируемым. Copies глобальные,
не уникальные кадры этого окна. Display-link callbacks не равны displayed FPS.
Тем не менее эти результаты исключают универсальный жёсткий лимит80copies/s
и показывают, что источник обновлений способен давать около164callbacks/s.
Более лёгкая нагрузка повышает cadence; остаток не объясняется только cache.

## Дальнейшая работа

0.4.1 сохраняется как текущая рабочая сборка; новой установки на этом этапе
нет. Следующая задача — разделить затраты descriptors/композитинга и
сигнализацию completion в muxless copy path. Не вычитать4.43мс из8.92мс
с автоматическим приписыванием остатка одному потоку.
В nvmtl_snapshot_set_c есть кандидат для отдельной проверки: dirty-only
descriptor copy выбирает from только при live (который требует !dirty),
а случай was с dirty slots не использует copy-mask. Это ещё не доказанная
ошибка или причина задержек; нужны GPU-проверки changed/unchanged bindings,
layout masks и стоимости copy против rewrite. Код descriptors пока не изменён.
