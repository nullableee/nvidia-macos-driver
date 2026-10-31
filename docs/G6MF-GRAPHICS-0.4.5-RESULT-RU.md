# Аппаратный результат 0.4.5

Новаязагрузка22:38:11MSK30октября2026. PayloadSHA99b683...совпал,
Metal0.4.5. Сбор cache-ab-20261030-224358.bzXPG7 завершёнпослеcollectorfix1.
GPUtimeoutcounter12вэтойboot,несравниватьс20впрошлойзагрузке.

4фазы64/128/128/64:84.82/84.06/90.25/77.06copies/s. Среднее80.94vs87.16
(+7.68%). Фонживой,междуфазамиразброс,этонеdisplayedFPS и неуниверсальный
процентускорения. Handler3.3955/3.3428/3.1875/3.3109мс:огромногоизменения
copyhandlerнет,выигрышкэшаожидаетсявподготовкересурсоввuserspace.

ВсефазыdeltaGPUreadytimeout/IOPfail/pageofffail/directheld/directtimeout0,
directсрабатывал883/884/947/872раз. Отдельныйprofileтожеуспешензавершён.
Послеуспехавосстановленыcachedefault64/direct0/diag0.

ВкаждойABфазеоднаpolicyзапись:политику64/128подтверждает, ноотдельные
внутрифазовыеhit/evictionдельтынедоступны. Междудвумязаписями128
22:44:15.621→22:44:24.581policy_changesостаётся1,PID200:
calls51712→52224(+512),hits28879→29372(+493),creates22833→22852(+19),
evictions23103→23122(+19),96.29%hits. Этотинтервалвключаетграницудвух
анимаций,ноbudget128непереключался. Несчитатьегочистымокномоднойфазы.

64snapshotheld8/21.56MB;128snapshotheld16/66.54MBили45.45MB.
Entry_pressure22988→23102→23121→23325,byte_pressureпостоянно1.
ОграничениечислакорнейдействительноосновнаяпричинаLRUвытесненийвэтом
прогоне;самbytebudget64MiBпочтивсегданедостигнут. Общиеcumulative
countsнесравниватькакскоростизафазу.

WSsample8с,5770mainobservations:mach2328(2158server_loop),layerprepare99/88,
AllocateDescriptorSets54,VRAMVAallocationMach13,dirtymarkMach89.
Sampleнепоказываетновогокрупногодоказанногодефектавдрайвере;ожидание
server_loopнеравноGPUwait. Не переводитьobservationsвframe-ms.
Profileprobe93.85copies/s,callback164.08/s,handler3.3217ms,Intelcopy2.1325ms.
JSONdiagnostics/cache-0.4.5-result/main-sample.json.

Следующийобязательныйhumanrepro—реальноеоткрытие/resizeSafariс128+direct1
иprofile-perf.sh20с. Гипотезымассовогоимпорта/компиляции/ресурсовSafari
нужнопроверятьименнонаэтомсценарии,нетолько12простыхCAпанелях.
Новыйkitнеподготовлен,системныхизмененийвэтомразборенебыло. Пользователь
можетвключить128черезсуществующийset-cache-budget.sh128иdirect1безребута;
этоэкспериментобычнойсессии,default/startupнеизменялись.
