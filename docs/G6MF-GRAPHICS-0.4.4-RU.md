# Graphics 0.4.4: present без промежуточной CPU-копии

Подготовлен экспериментальный пакет, установка не выполнялась.
Пакет0.4.4 меняет NVAccel0.1.7→0.1.8. Metal остаётся0.4.3.
NMIntelFB0.1.4 упакован побайтно прежний; общий installer повторно публикует
его при сборкеKC. EFI, AGDC и настройки очереди не меняются.

## Новый путь

В0.4.3 измерены staging→IOSurfaceRAM1.6884мс и RAM→IntelWC1.8772мс.
Кандидат делает VRAM→staging→IntelWC: nvAccelMuxlessDirect вызывается
только дляNMIntelFB/head4 под новым opt-in sysctl. Он проверяет BGRA,
геометрию и размеры, dirtymarker, VRAMvalid, allocationwritecookie и
готовностьGPU. Ресурс/cache живут подfamilylock, staging подstage lock;
порядокfamily→stage совпадает сpageoff. Scanout запрашивается послеCE,
проверяется актуальная плоскость, копия завершаетсяsfence.

CPUbacking не обновлялся, поэтому valid[0] не выставляется и nvSVPend
не очищается. Обычныйpageoff и CPUreaders сохраняют прежний путь. CPUcurrent,
неподходящий ресурс или ошибка подготовки доCE возвращают originalpath.
После ошибкиCE/неверногоscanout предыдущийframe остаётся на экране.
При timeout/неопределённом результате вызоваCE staging исключается изreuse
безrelease подготовленных DMAстраниц. Kernel сам ставитdirect_present=0
после первого held-результата: повторныекадры не накапливаютquarantine.

Общийpageoff с игнорированиемboolnvSurfWaitReady здесь НЕ менялся;
вdirectpresent повторная проверкаbool выполняется подfamilylock.
Новаяветка не меняетGPUdirty/readynotifications и не сокращаетfences.

debug.nvaccel_direct_present всегда0послезагрузки. Новыеcounters:
direct_attempts/ok/fallback/held/timeout; direct_total_count/ns/max,
direct_ce_count/ns/max. direct_total включает все попытки после успешного
familylock, в том числе последующиеfallbacks, не только fastsuccess.
Обычныйperf_total остаётся полным обработчиком; perf_copy включает обе
разновидностиIntelcopy. perf_ready не учитывает fastpath, сравнивать его
с baseline как время всехframes нельзя. Fastpath не читает устаревшую
IOSurfaceRAM дляblank64pixelsdiagnostics, эти счётчики несопоставимы.

## Проверки до установки

- Собранx86_64MH_KEXT_BUNDLE; версияkmod_info0.1.8 совпадаетсInfo.plist,
  constructor/destructorsections есть, userspaceatexit/TLSimports нет.
- HostASan/UBSan компилирует непосредственноproduction nv_direct_present.h.
  Проверены пиксели/stride/padding, две последовательныеGPUкартинки1920x1200,
  20fault/stateсценариев, неизменностьCPUvalidity, lockorder/cleanup,
  quarantine иauto-disable. Это не тест реальногоIOAccel lifecycle.
- Существующиеcopy32/64 иstagewrite проверки проходят.
- Bridgeinstaller10сценариев: success, preflightfail, missingmodule,
  livefail, пары/AGDC сrollback, UUIDsuccess/missing. Тесты используют
  disposable filesystem иmockkmutil, не настоящуюrootKC.
- A/Bscript6модельныхсценариев: success, held, nohits, CPUprobeerror,
  ошибкаво времяCPUreadback, SIGINT. Везде флаги восстановлены.

КандидатнаяKC из user-ownedrepository не собралась: kmutilstatus31,
"only1codelesskexts". Root-ownedкандидатнаяKC доустановки не проверена.
Installer обязательно chownroot:wheelrepo, собирает temporaryKC и
проверяет новыйUUID ДОзамены. Затем строитliveKC и проверяет снова;
ошибки посленачалаизменений вызываютrollback. Workspace test.kc,
получившийся при некорректном пустомrepository, содержит СТАРЫЙ0.1.7;
он не кандидат и не упакован. Не объявлять nativeKCvalidated.

PayloadSHA25601c88a9328867697458a4493e18ab643cd8fb62886a3ccbad62114f92c424437,
UUIDE881A422-9625-3E41-9AE0-42F168277866. build-manifestkit содержит только
упакованныеNVAccel и прежнийNMIntelFB, не остальныеfullbuildtargets.

## Аппаратная проверка

Пользователь: sudo bash kits/graphics-0.4.4/install.sh → толькоREADY → reboot,
проверкаGlass/цветов,2–3минпрогрева → bash test-desktop.sh БЕЗsudo.
ПутьпакетавREADMEабсолютный. Поумолчаниюновыйкоднеактивен.

Скрипт запрашиваетsudo дляпереключателей и выполняет4автофазы анимации
OFF→ON→ON→OFF (каждая2сразгон+12сосновноеокно). ПослепервойON отдельно
проверяетpixel-probe CPU/GPUreadback собственнойIOSurface сточнымиpixels.
Это не проверкаCPUreaders всех скрытыхWSsurfaces. Счётчики проверяются
после каждойфазы иCPUprobe; held/fail/timeouts илиnohits прекращаюттест.
Kernelможетсамотключитьфлаг; это ошибкаиспытания, не успешнаяфазаON.
Выход/ошибка/Ctrl-C всегда отключаютdirect и возвращаютисходныйlatencydiag.

Snapshotwindow включаетstartupокна; отдельнаяanimationстрока измеряет
12с после2сразгона. Не смешиватьэти знаменатели. Длямежпроцессныхграниц
используетсяnativeclock-probeCLOCK_UPTIME_RAW. Python3.9 macOSmonotonic_ns
имеетprocess-localepoch (провереноразныминативнымипроцессами), поэтому
дваPythonпроцесса не годятся дляэтогоelapsed. Тест скрипта обнаружилошибку,
исправление clock-probe проверено последовательно растущимиtimestamps.

Фонживой, ABBAснижаетвлияниедрейфа, но не даётуникальныйdisplayedFPS или
input-to-photon. Экономия1.69мс —цельдляоперации, не обещание165FPS.
ЕслиCPUreadersпотребуютдополнительныйpageoff, выигрышможетисчезнуть;
именно поэтому нужныреальныеcounters/картинка/CPUreadback иdefaultoff.
После успешноготеста режимтожеостаётся0. FullbackupNVAccel/NMIntelFB/
AuxKC/cache26 иrestore-working.sh возвращают0.1.7; Metal0.4.3неизменялся.
