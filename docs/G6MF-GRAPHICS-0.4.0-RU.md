# Graphics 0.4.0

Начиная с этой сборки, пользовательская нумерация комплекта — 0.4.x.
Старые v10–v14 остаются именами исторических экспериментов/замеров.
Metal bundle получает CFBundleVersion/CFBundleShortVersionString 0.4.0;
payload экспортирует g6mf_graphics_release(). Версии не изменённых kext
NVAccel 0.1.7 и NVRMAGDC 2.6.6 сохраняются: это отдельные компоненты.

## Что изменено

В live-surface cache path убрано создание лишнего NVMTLTexture до lookup:
при cache hit этот объект не использовался. Новый root теперь создаётся
только после cache miss/невозможности сделать view. Это небольшое сокращение
CPU-работы, не обещание заметного прироста FPS.

Добавлены атомарные cumulative counters завершённых surface-wrapper calls:
private_hit, vram_hit, no_backing, disabled, capability, view_failed,
created, create_failed. WindowServer пишет одну агрегированную строку
G6MF 0.4.0 surfaces на 512 завершённых вызовов через os_log DEFAULT.
Нет логирования каждой поверхности, texture IDs или пользовательских данных.
Другие процессы не пишут эти строки. Counters не удерживают поверхности.
Экспорт g6mf_surface_stats позволяет нативному probe проверить их значения.

no_backing объединяет первый вызов нового ключа и отсутствие живого root:
он сам по себе не доказывает слишком раннее освобождение. disabled показывает,
что существующий VRAM root не использован из-за выключенного reuse;
capability — что ShaderWrite требует storage, которого у root нет.
Логи редкие, поэтому snapshot не совпадает точно с началом/концом 20с perf.
Если строк нет, нельзя объявлять hits равными нулю: нужно проверить сбор логов
и число вызовов. Атомарный snapshot разных counters не является транзакционным.

## Что найдено в пути показа

NVDisplayPipe::performTransaction для NMIntelFB синхронно вызывает
nvSurfWaitReady, nvAccelSurfCopyReady/pageoff и nvMuxlessCopy.
nvAccelIopFlip немедленно возвращает false для framebuffer другого вендора;
асинхронный NVIDIA flip worker не обслуживает внутреннюю Intel-панель.
Это реальное ограничение текущей архитектуры. Перевод копии в worker требует
сохранения IOSurface, очереди, сигнализации completion и правил teardown;
простое раннее return может дать старые/незавершённые кадры.

В v14 handler занимает около4.84мс, копии около3.61мс, VBL period6.10мс,
entry13.17мс. Это совместимо с нехваткой времени в конвейере, но не доказывает
конкретный пропуск каждого второго VBL. Нельзя автоматически сложить работу
разных потоков или объявить весь handler блокировкой main thread:
sample main содержит лишь несколько листьев в IOPTransaction Submit.
Средний fence0.36мс и отсутствие новых timeout не поддерживают гипотезу
о долгом GPU fence как единственной причине задержки.

В worker sample также видна компиляция render pipelines (например Thread15419).
Это дополнительный кандидат, не доказанная главная причина. Сборщик0.4.0
сохраняет весь sample, process snapshots и vm_stat до/после для проверки
конкурирующей нагрузки и изменения памяти. Он не закрывает приложения.

## Проверка и установка

Нативный release plugin x86_64/minOS15 собран и ad-hoc подписан.
На работающем GPU прошли:

- 50 lifecycles, 4000 concurrent wrappers, удержание root последним alias,
  освобождение root и разделение resource options;
- точные counters: calls4150, vram_hit4050, no_backing100, created100;
- 60 полноразмерных BGRA кадров с CPU/GPU patterns и readback;
- RGBA16Float и compute swizzle2048pixels.

Модельные installer tests проверили успех/restore и отказы pixel/stress/
swizzle/LUT/serial/signature, включая возврат версии bundle0.1 после restore.
Реальный WindowServer с0.4.0 ещё не запускался. Система не заменена:
sudo требует пароль пользователя. Kit kits/graphics-0.4.0 сохраняет полный
текущий v14 bundle и его featurefile. EFI и kexts не меняются.

Установка: sudo bash kits/graphics-0.4.0/install.sh из корня workspace.
Только после GRAPHICS 0.4.0 READY — обычная перезагрузка, проверка Glass,
прогрев рабочего стола 1–2мин и sudo bash kits/graphics-0.4.0/profile-perf.sh.
При проблеме sudo bash kits/graphics-0.4.0/restore.sh и перезагрузка.
