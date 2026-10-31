# Аудит сокращения muxless readback

Это исходный аудит перед реализацией. Экспериментальный default-off кандидат
реализован в пакете0.4.4: см. G6MF-GRAPHICS-0.4.4-RU.md. Аппаратного
подтверждения пока нет.

Текущий NVDisplayPipe::performTransaction для NMIntelFB:
GPU fence → nvAccelSurfCopyReady → NVResource::pageoff → CE VRAM→staging →
nvStageWrite staging→IOSurfaceRAM → iopMapSurface → nvMuxlessCopy RAM→IntelWC.
Реальные средние в0.4.3: CPUwrite1.6884мс, Intelcopy1.8772мс.

pageoff выполняется под accelerator family lock. Staging buffer глобальный,
защищён stage lock; физически contiguous, prepare сохраняется на его lifetime.
CE status0 подтверждает завершение перед чтением CPU. При CEtimeout0x65
старый staging abandon: нельзя повторно использовать пока возможенDMA.
Системный md подготовлен доCE и complete вызывается послеCPUwrite; при
прямом SGtimeout страницы остаютсяwired. Общий pageoff обязан сохранять это.

При успешном pageoff nvSVPend(surface,0) очищает dirtymarker,
valid[0]|=1 объявляет CPUcopyактуальной. GPUdirty устанавливает valid[6],
сбрасывает valid[0], пишет allocationcookie. Поэтому НЕЛЬЗЯ просто убрать
nvStageWrite изpageoff: CPUreaders станут читать старую RAMкакновую.

Кандидат: отдельный present-only VRAM→staging→IntelWC, не использующий
обычныйpageoff для перемещения вCPUbacking. Нельзя очищать dirtymarker
или выставлятьvalid[0]: CPUbacking не обновлялся. Обычныйpageoff должен
остаться дляIOSurfaceLock/readers. Готовностьpresent и готовностьCPUbacking
теперьразныепонятия. Требуется отдельно проверить lifecycle семействаIOAccel
при успешномperformTransaction сdirtyCPUbacking, включаяповторныйpresent.

Границы будущего прототипа:
- толькоhead4/NMIntelFB, BGRA, точнаягеометрия, подтверждённыйVRAMnewest,
  pluginwritecookie соответствует текущемуallocation;
- дождатьсяnvSurfWaitReady и проверитьbool; приtimeout не копировать;
- resource/cache/VRAM handles живут подfamilylock; stageпослеfamilylock,
  порядок совпадает сpageoff, не вводить обратного захвата;
- validate Intelmapping поliveplane черезaskFramebufferForScanout;
- CEошибка/timeout сохраняет предыдущийdisplayframe; нечитатьstaging после
  неудачногоCE, не сообщатьактуальностьCPUbacking;
- stage остаётсяподlock доокончанияIntelWCcopy+sfence;
- CPUcurrent/несовпадениеконтракта/failure → исходныйпуть либо удержание
  предыдущегоframe, безкопированиянеподтверждённыхпикселей;
- отдельныесчётчики fast/fallback/fail, default-off sysctl, trap дляA/B.

До productionнужны проверкиpixelpatterns/stride/границ, CPUreadback после
present, повторнаясменаGPU→CPU→GPU, surface reuse/destruction, CEfailure и
timeoutбезuse-after-DMA. Пользовательскийmemcpybenchmark не заменяет эти
контракты и аппаратныйтест. Возможнаяэкономия1.69мс не означает +1.69мс
во всёмframe pipeline или165FPS: потоки/периоды перекрываются.

Также остаётся отдельныйexisting correctnessдефект: общийpageoff игнорирует
bool nvSurfWaitReady, хотяdisplayperformTransaction его проверяет.
Его нельзя лечить сокращением ожидания или произвольнойустановкойvalidflags.
