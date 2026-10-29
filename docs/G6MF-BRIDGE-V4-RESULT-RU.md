# Результат аппаратного теста v4

Источник: macOS-20261029-231243-733, внутренний автосбор
boot-20261029-230243-319. Исходные файлы сохранены в
/home/spotlight/workspace/G6MF-Hardware-2026-10-29/.

Это загрузка с NMIntelFB, а не последующее восстановление: boot-args не
содержат -nmintelfboff. Автосбор завершён (CAPTURE-COMPLETE).

## Подтверждено

- NVRMAGDC g6mf-v1.4 активен, связан с NVIDIA PEGP и Intel NMIntelFB.
- debug.nvrmfb_agdc=1, fbmap содержит один слот 0 с ID 0x100000583,
  maxfb=1, k5_link=3, k5_caps=3, k5_why=0.
- IOPresentment в WindowServer: Valid ADGC node found for this device;
  Successfully created presentment object type: 1024;
  Capabilities conversion successful (23:02:56).
- NVAccel published/registered/piped = 16 (бит внутренней головы 4).
- debug.nvaccel_iop_ok_h4 остаётся 0 во всех шести замерах.
- С 23:02:58 повторяются IOPRESENTMENT_METHOD_FAILURE / 0x2d8 и
  Fallback GPU Display Pipe transaction submission failed.
  В IOReturn.h 0x2d8 — младшая часть kIOReturnNotReady.
- Target State показывает BGRA 1920x1200, System Gamma Unknown;
  рядом есть Attempting to get capabilities from plane with no gamma.
- До подключения WindowServer отчёт GATES показывает accel enabled,
  pipe active=0, wsaaDefer=0. В логе отсутствуют K6 plane/transaction
  из нашего performTransaction. Это указывает на более ранний отказ,
  но не доказывает, что active оставался 0 во время всех транзакций.
- Нового .ips/SIGABRT или kernel panic в сборе нет. Есть cpu_resource
  WindowServer PID 200: 90 секунд CPU за 100 секунд; стеки показывают
  также работу NVMTL/переводчика шейдеров. Это отчёт нагрузки, не падение.

## Ограничения вывода

map-probe вернул MAP NULL во всех замерах, однако WindowServer успешно
создал собственный объект IOPresentment. Поэтому MAP NULL отдельного
процесса нельзя считать доказательством, что карта отсутствует у WS.
Предыдущие Unable to acquire map в том же log show относятся к другой
загрузке 22:59 и не описывают результат v4 в 23:02.

Нельзя пока приписывать весь отказ gamma, несовпадению индексов либо
отсутствующему framebuffer resource. Нужна проверка реализации family
именно Tahoe 25G241. Подмена opaque active-флага и объявление CPU-only
Intel scanout видеопамятью NVIDIA не являются проверенными исправлениями.

## Следующий шаг

Рабочий EFI уже восстановлен, SHA256 config.plist:
cb8d0564840c5f7c0c11177352145d2368cb6eca951ae4a3ae69c152516288d5.
Скрипт collect-family.sh копирует установленный IOAcceleratorFamily2,
IOGraphicsFamily и BootKernelExtensions.kc для разбора условий NotReady
до performTransaction. Только чтение; драйверы и EFI не изменяет.
