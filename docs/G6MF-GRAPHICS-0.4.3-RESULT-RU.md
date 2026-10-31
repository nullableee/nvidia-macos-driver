# Аппаратный результат 0.4.3

Загрузка 30 октября 2026,21:28:05 MSK. Установлен и загружен payload
9BF7F116-D5F8-3047-96B6-0242252E622B, SHA256совпадает сkit. Safe0/AGDC1,
mapcopy0/latencydiag0 после сбора. Профиль profile-20261030-213226-1005,
perf-20261030-213226-1020, input-20261030-213249.HVUCkL.

В ручном окне90.12копии/с против80.41в0.4.2 (+12.07%). Это разные ручные
прогоны, неA/B и не точный FPS. Entry10.9731мс вместо12.3344. Handler4.7581мс,
fence0.2902,ready2.6014,Intelcopy1.8772,staging CPUwrite1.6884,
CE0.7436. Вложенные интервалы перекрываются. Timeout10→10, IOP/pageofffail0,
lockmiss+20. Начальные10timeout принадлежат новой boot session, не старой.

Участок sparse logs21:32:30.255→21:32:46.623:
44540sets,241792writes,9398metadatahits. Writes/set5.42865 против181.77844
предыдущего профиля: падение примерно97%. Metadatahits/(sets+hits)=17.42%
против1.13%; обычныйsetreuse здесь неучтён. Разбор masks теперь устраняет
лишнюю работу именно в WindowServer, что подтверждает смысл исправления.
Surface2856hits/3072calls=92.97%,216созданий,216repeatmiss. Неувеличивать
LRUбюджет без доказательства причины misses.

Queue дельты: scheduled4341/completed4341, commit→scheduled0.15236мс,
commit→completionready0.68615мс, pending приcommit1.01889CB.
Большая постоянно накопленная очередь в этом окне не наблюдается;
CBнекадры, completionнечистоеGPUtime, максимумыstartupнеусреднять.

Main1815samples: AllocateDescriptorSets18exclusive против28/1828,
UpdateDescriptorSets не вошёл вtop20 (ранее66), address_snapshot14.
Не превращать samples в точный CPU%/frame-ms. JSON diagnostics/graphics-0.4.3-*.

Input2269events: app p503.34817,p956.72864,max12.79255мс;
layercommitp503.47164,p956.81553,max12.88616мс. Invalid0.
Callback3254intervals,p506.12224,p956.55772,max39.51277мс;
panelcopies106.844/с. Eventdelivery практически прежняя, физическая
мышь→фотон не измерена, аппаратный курсор не подтверждён.

Повторили прежний owned-window animationprobe (2сразгон+12с):
client86.40copies/s при162.97callbacks/s; server91.40при163.71.
Старые0.4.1client104.07/server108.82, но фон/boot/видимыйdesktop различаются.
Эти результаты не подтверждают универсальный прирост12% или165FPS.
В обоих новых прогонах handler4.61–4.65мс, copy1.79мс. Логиbuilds/cadence-0.4.3.

Проверен VBL callback: дельта37106479ns/3279=0.0113164мс, bootmax0.074531мс.
Это короткий callback, не4.76мс обработчикаpresent. Гипотеза что самcallback
синхронно занимает весьpresent и поэтому пропускает каждый второйtick
этими данными не поддерживается. Средняя периодичность6.1115мс близка
настроенной6.1113; это таймер, не измерение физическойфазыscanout.

Следующий кандидат: убрать промежуточную CPUкопию staging→IOSurface
в специализированном muxlesspresent, сохранив обычныйpageoff дляCPUreaders.
Текущий путь CPUwrite1.6884+Intelcopy1.8772=3.5656мс (не надо ещёраз добавлять
их поверх ready/total). Аудитконтрактов — G6MF-MUXLESS-PRESENT-AUDIT-RU.md.
Новый kernelкандидат не подготовлен/не установлен: простое пропускание
writeBytes и установка valid[0] было бы неверным, stale CPUmemory.
