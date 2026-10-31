# v11: установлен отказ AGDC перед падением WindowServer

Сохранённые unified logs целевого Mac за 15:57–15:58 показывают:

- 15:57:54.268: NVRMRenderBridge опубликован.
- 15:57:57.375: AGDC: no PCI device or no framebuffer yet (pci0 fb0).
- 15:57:57.576: auto-go: heads0x10 accel4 agdc-1 k5=1 iop=1.
- 15:58:04.388: IOPresentment Unable to get AGDC information,
  Unable to locate service dependencies, Unable to acquire map.
- 15:58:05.012: System set to use IOP but no display pipes are present.
- Затем SIGABRT в CA::OGL::Context::push_surface.

Повторная неудачная загрузка также имеет отсутствие display pipes.
Это устанавливает отказ AGDC до crash. Оно не доказывает, какой именно
предикат nvdaAgdcTargets отказал. Поздняя публикация render bridge сама
по себе не объясняет приведённую попытку: он опубликован раньше AGDC.
Нельзя объявлять причиной диагностические атомарные счётчики pageoff:
startup уже не имел корректной AGDC-карты.

Аудит исходников обнаружил две точки для дальнейшей проверки:
1. nvdaAgdcTargets сначала выбирает NVRMNVDAFramebuffer, даже при
nmoptimus=1; путь Intel вызывается только если NVIDIA matching не нашёл
ничего. Неподходящий ранний NVIDIA объект с неверным provider приводит
к отказу без попытки muxless fallback. Это кодовый кандидат, наличие
такого объекта в момент аварии пока не подтверждено.
2. nvdaAgdcWorkBody при отсутствии targets сразу сохраняет state=-1 и
возвращает. Auto-go прекращает ожидание при любом ag<0, затем включает
IOP и отпускает boot hold как display PARTIAL. Поэтому ошибки обнаружения
не восстанавливаются автоматически и WindowServer получает неполный стек.
Просто добавлять sleep без определения отказавшего предиката недостаточно.

В обоих бинарниках NVAccel v10/v11 дизассемблер не обнаружил SIMD-регистров.
UUID Metal wrapper, оригинального NVMTL, Vulkan и CoreDisplay в обоих
crash reports совпадают. Это исключает различия этих библиотек между
двумя авариями, но не доказывает неизменность всех условий загрузки.

Текущий установленный NVAccel0.1.5 восстановлен, agdc=1, mapping=0,
Glass/ускорение подтверждены пользователем. Системные компоненты при
этом анализе не менялись. v11 остаётся заблокированным к установке.
Следующий безопасный кандидат должен сохранять рабочий NVAccel и отдельно
проверять обнаружение AGDC targets, причины отказа и поведение auto-go.
