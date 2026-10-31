# Graphics 0.4.5: проверка cache pressure

Пользователь проверил0.4.4вобычнойработе и уточнил: desktop/Dock плавные,
тяжёлые окна вродеSafari всёещёпросаживаютплавность. Оценка~120FPS —его
ощущение, не инструментальныйdisplayedFPS. Directpresentпроверенвключённым.

ПослеAB0.4.4direct_ok3679; новаяпроверка44823/45861attempts, fallback1037,
held0/timeout0/IOPfail0/pageofffail0. Один общийGPUreadytimeout добавился
19→20 с концаAB. Это неdirectCEtimeout; pendingwait естьдоdirecthelper.
Причина/точное времясобытия неизвестны, не объявлятьдлительныйтестбезошибочным.
За последующиеnative/UIпробыcounter20→20,held0,direct_presentоставлен1.

## Основание кандидата

ЛогиWindowServer0.4.3 за3минутыпрочитаныбезsudo. В участке22:19:55.317→
22:19:56.438calls89088→89600:124hits/512calls=24.22%,388created/repeatmiss.
Это не controlledSafariтест; повторныечисловыеkeys не доказываютидентичность
послерециклингаIOSurfaceID. Но естькандидат: LRU8entries/64MiB вытесняет
рабочийнабор. Ранееcacheпопаданиябыли~93–100% влёгкихсценариях.
Rawлоги diagnostics/cache-pressure-0.4.4. СвежийsampleWS безsudoзапрещён,
поэтому не выдавать старыйпрофиль за новыйтяжёлыйслучай.

Новая Metal0.4.5 добавляет:
- прежнюю defaultpolicy8/64MiB и эксперимент16/128MiB;
- WS-only file /Library/NullMoth/g6mf-surface-cache-mb,64/128строго;
- rootfileполлинг нечаще1раза/с поCLOCK_UPTIME_RAW, остальныеappsdefault64;
  nativeoverrideNVMTL_SURFACE_CACHE_MBзадаётсяпослеdlopen;
- обрезкуcacheприуменьшении на следующемholdвdevice, включаяoversizedrequest;
- counters evictions/evictedbytes/entrypressure/bytepressure/admissions/
  touches/oversized/policychanges, heldentries/bytes иpolicy в sparseWSlog.
Entry/bytepressure могутувеличиватьсяодновременноприодномeviction.
Budgetпер-device, считаетсяspanmax(surfacealloc,importbuffer), необщаяVRAM
всехapps. Eviction снимает толькоcacheownership;aliases/CBдержатнужныеroots.
Idledeviceнеочищаетсяфоновымтаймером,каждыйbudgetвсегдаограничен128MiB/16.
Keys/usageguards, masks,descriptorcode,GPUqueue/kernel/EFIнеизменны.

## Проверки

ProductionObjC LRUтест ASan/UBSan:8/64→16/128→8/64,touch,byte/countpressure,
oversizedshrink, caller/flushlifetime. Проверяетсяименноproductionкод,
включаяfilepoll128→64/ограничениечастоты/missing/malformed/embeddedNUL.

Nativeрабочийнабор12реальныхIOSurfaces1920x1200,240transientwrappers:
| Лимит | Созданоимпортов | Hits | Удержано | Spanbytes |
|---|---:|---:|---:|---:|
|64MiB|240|0|7|64512000|
|128MiB|12|228|12|110592000|

Все12полныхкартинок провереныGPUblit→CPUreadbackпопиксельно. Доsubmit
удаленыcaller/cacheссылки иуменьшенpolicy:CBownership сохраняетpixels.
Это доказываетмеханизмнауправляемомнаборе, не егоFPSэффектвWindowServer.
ПрежниеholdLRU/64MB/inflight,weak+heldstress4000,pixelsBGRA/half,swizzle,
compute0/1,render/fetch,queueпрошли. Финальныйsignedpayload повторнопрошёл
cache64/128 иholdtests. UIpressureprobe12ownedpanels прошёлкороткийsmoke,
самзакрылся. Небылоизмененийсистемнойбиблиотеки/файлаpolicy.

ABscript6disposablemockcases(success/existingpolicy/held/probefail/SIGINT/
missinglogs)PASS;roothelperтестируетсятоже,реальныеrootwritesнеисполняются.
Installer18modelcasesPASS,втомчислеcache64/cache128prepublishfailure.
Логиbuilds/graphics-0.4.5. HardwareWindowServer0.4.5ещёНЕпроверен.

## Пакет и аппаратный замер

Kit kits/graphics-0.4.5: Metal0.4.3→0.4.5, NVAccel0.1.8 неизменён.
SHA25699b683baad7bd6791732c9ed0be1d9278c9d3e434594791cf549d2e4ee7dd8ab,
UUID16982222-7EB7-3FC1-87A3-D407B611BF10. Bundlebackup/restoreвозвращаетMetal3.

install.sh→GRAPHICS0.4.5READY→reboot→Glass/warmup→test-desktop.shБЕЗsudo.
Пятьфазпримерно50с:4сравниваемых64/128/128/64, затемотдельная128сsample8с.
Каждаяанимация2сwarmup+8сосновноеокно,12неактивирующихсяownedwindows.
SamplingнеискажаеттолькооднуABфазу. Скриптвключаетdirectpresentдляодинаковой
базы,diag1дляtimings. Kernelcountererrors/held илинетподтвержденияpolicyMB
вsparseлогах→abort, не делатьвыводы изнесработавшей128policy.

Успехвосстанавливаетпредыдущиеcache/direct/diag. Ошибка/Ctrl-Cвозвращает
cache/diag,ноdirectставит0(нельзяповторновключатьавтоотключившийсяпуть).
Manifest/hash/shellsyntax/codesignпроверены. Большийcacheпопослеуспеханеостаётся.
Скриптзапишетcache-ab-*/summary иотдельныйsample,потомсравнитьhit/evictions,
allocation/importstack,cadence/handler. Это livebackgroundABBA,неточныйFPS.
ПриSIGKILLtrapневыполнится; helperabsentвозвращаетdefault64. Rootfileне
создаётсясамойустановкой, толькотестом. Startup/default-onнеизменены.
