# Graphics0.4.2: descriptor reuse и измерение отклика

Кандидат подготовлен, в WindowServer ещё не установлен. Текущая система0.4.1.
Эта сборка меняет Metal bundle; kexts/EFI, очередь GPU и её лимиты не меняет.

## Найденная лишняя работа

В nvmtl_snapshot_set_c старый buffer-only fast path запрещал reuse при любом
изменении текстуры. Но переведённые шейдеры часто получают текстуру через
bindless handle в таблице адресов. Меняется таблица, а используемые самим
набором Vulkan descriptors (например, sampler и постоянный output buffer)
остаются прежними. Драйвер всё равно Allocate/Update-ил новый set на draw.

Новый путь разрешён только если:

- previous set всё ещё принадлежит этому command buffer и валиден;
- формат texel bindings и uniform layout/buffer/range совпадают;
- нет storage-image range (stex_hi=0);
- changed mask не пересекается с used-descriptor mask шейдера;
- прежний set покрывает новый used mask;
- адресная таблица использует тот же buffer page, включая проверку границы256
  snapshots на страницу.

Новая таблица и её dynamic offset всё равно записываются. Новые direct-buffer,
sampler или shader-mask bindings продолжают получать новый set. Старый путь
для buffer-only изменений сохранён. Helper nvmtl_descriptor_reuse.h проверяется
как production C-код; negative controls игнорирования changed/storage guards
должны завершиться ошибкой. В production всё прошло.

NVMTL_METADATA_REUSE=1/0 явно включает/выключает путь. Без override он включён
только в WindowServer, обычные приложения сохраняют прежнее поведение.
Release constructor очищает inherited NVMTL_*: probes задают env ПОСЛЕ dlopen.
Предварительный prototype dirty-copy (live||was) был проверен отдельно,
но в релиз НЕ включён: он не убирал сам allocation и не решал основную работу.

## Реальные GPU-проверки

Каждый mode0/1 — отдельный процесс с загрузкой локального signed payload.
Проверены все2000 outputs compute и2048pixels render, а не только отсутствие
ошибки API. Flags/счётчик fast_cases доказывают выполнение новой ветки.

| Тест | mode0 sets/writes | mode1 sets/writes | mode1 metadata hits |
|---|---:|---:|---:|
| Compute, смена одной из16textures |2001/6003|9/27|1992|
| Compute, также меняется sampler |2001/6003|1336/4008|665|
| Compute, меняется shader mask |2002/6006|2002/6006|0|
| Compute, также меняется output buffer |2001/6003|40/120|1961|
| Render, смена texture |2049/4096|9/16|2040|
| Render, меняется sampler |2049/4096|1369/2736|680|
| Render, меняется shader mask |2049/4096|2049/4096|0|

Все пиксели совпали.2000dispatches пересекают несколько256-entry table pages:
неверный reuse на границе испортил бы outputs. Sampler/filter, output buffer
и mask changes имеют разные ожидаемые результаты, поэтому stale binding не
скрывается одинаковыми данными. Также прошли прежние weak/held stress4000
wrappers, LRU/64MiB/last-alias/in-flight lifetime, BGRA1920x1200,
RGBA16Float1920x1200 и compute swizzle. Логи builds/graphics-0.4.2.

Прототип render encoding21.933→7.123ms/2048draws; финальный payload в одном
прогоне11.892→9.734ms. Другие измерения времени сильно колеблются, включая
paired phases; это не стабильный коэффициент ускорения и не прогноз FPS.
Устранение allocations/writes подтверждено независимо от этих колебаний.

## Задержка ввода и очередь

Пользователь уточнил: отклик самого курсора кажется хуже Arch; задержка была
до0.4.1. В NMIntelFB нет собственного hardware-cursor implementation.
Это ограничение, но точный путь текущего курсора и его вклад не измерены.
Наличие базового software cursor в IOFramebuffer не даёт права автоматически
считать курсор привязанным только к частоте compositor.

Новый input-probe отслеживает события только внутри собственного окна,
без глобального event tap/Accessibility. Он записывает event→app, event→layer
commit и интервалы display-link. Не измеряет физическое input-to-photon.
В2-секундном UI smoke run попало86реальных pointer events:
app p50=3.1558ms,p95=6.9137,max=8.0467; layer commit p50=3.2084,
p95=6.9692. Invalid timestamps0. Это короткий неконтролируемый прогон,
не исключающий задержки при другом сценарии. Лог kits/input-latency-0.4.2/ui-smoke.json.

Добавлены наблюдения только для WindowServer: commit→scheduled и
commit→completion-ready (включая публикацию/CPU cleanup), а также pending
command-buffer count в момент commit. Частота/порядок submission и лимит
NVMTL_GSUB_INFLIGHT по-прежнему прежние. Это CB count, НЕ число кадров.
Native queue probe проверил64копирования:64scheduled/64completed,
точные данные и pendingmax6. Mean commit→completion в этом тесте0.2805ms.
Native compute probes включают диагностику явным G6MF_TEST_QUEUE_STATS=1.

Раз в512surface calls WindowServer пишет три строки os_log DEFAULT:
G6MF0.4.2 surfaces/descriptors/queue. Для очереди n/ns/max — cumulative,
max с запуска процесса; snapshots не транзакционные. Нужны дельты в окне,
а не трактовка startup maximum как задержки каждого кадра.

## Остальные проверенные направления

На новой загрузке20:33:53 kernel timeout counter был12; в интервале тяжёлых
GPU-проб и живой фоновой нагрузки вырос до26. WindowServer всё это время
использовал0.4.1. Это pending-surface readiness timeouts до100ms, не
доказательство зависшего GPU. Нельзя объявлять их отсутствующими или
приписывать новому, ещё не установленному payload. Новых WS ips после15:58
не было при проверке. Эти длинные ожидания надо отделять от среднего fence
0.29ms предыдущего ручного профиля.

В NVResource::pageoff результат nvSurfWaitReady не проверяется, в отличие
от muxless performTransaction. Это отдельный correctness-кандидат для
аудита; pageoff/kernel code этой сборкой НЕ менялся. Не сокращать/отключать
fence без сохранения запрета копировать неподтверждённые пиксели.

CPU: ProvideCurrentCpuInfo=true, CpuTopologyRebuild2.0.2 на EFI отключён,
sysctl16physical/16logical/одинStandard perf level. Автор проекта описывает
такую плоскую топологию как возможную причину потерь, но эффект неопределён:
https://github.com/b00t0x/CpuTopologyRebuild/blob/master/README.md
Наш короткий single-thread probe default/UI QoS видел только P-core type40,
поэтому не доказывает неправильное размещение именно WindowServer.
EFI/CPU topology не менять одновременно с проверкой0.4.2.

IOFBWaitCursorPeriod=33333333 относится к стандартной30fps wait-cursor
animation, не доказательство ограничения движения указателя30Hz:
https://github.com/apple-oss-distributions/IOGraphics/blob/main/IOGraphicsFamily/IOFramebuffer.cpp
Точность VBL-оценки по250msFRMCOUNT и её фаза также остаются кандидатами;
в0.4.2 этот kernel code не менялся.

## Установка и проверка

kits/graphics-0.4.2 сохраняет весь текущий0.4.1bundle/feature2. Stagingnative
probes проверяют cache, compute/render descriptors, sampler/mask/buffer и
очередь. После публикации — исходные LUT/shader/serial probes; ошибка
вызывает восстановление.14модельных installer scenarios прошли, включая
отказы descriptor/render/queue и rollback существующего feature file.

После GRAPHICS0.4.2READY нужна обычная перезагрузка и2–3мин прогрева.
test-desktop.sh выполняет20с профиля с движением окон, затем20с input-probe.
Проверяет установленную версию и отказывается работать в той же загрузке,
в которой installer заменил bundle. Loaded UUID всё равно проверяется
по sample. Реальные FPS/отклик/Glass0.4.2 пока не проверены.
