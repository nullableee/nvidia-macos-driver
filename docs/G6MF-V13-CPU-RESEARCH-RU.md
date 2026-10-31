# CPU-расходы до обработки muxless кадра

30 октября выполнен дополнительный разбор существующего sample v13
(1812 отсчётов ws_main_thread). Эксклюзивные листья сведены по предкам,
без сложения родителя и дочерних строк. Получено: descriptor path144,
wrapping поверхностей95, RunFullDisplayPipe219, обычное ожидание событий395,
SurfaceIn12, остальные947. Это доли отсчётов профиля, не точные миллисекунды
кадра и не независимое измерение загрузки GPU.

Обычный server_loop mach_msg (395/1812~21.8%) нельзя называть GPU wait.
Descriptor path~7.95%, wrapping~5.24%, display pipe/LUT~12.09% дают
конкретные CPU-кандидаты вне измеренного handler total4.83мс.
Нельзя просто вычесть handler4.83 из entry13.07 и приписать весь остаток
одному стеку: обработка может идти на другом потоке и перекрываться.

В отдельном пользовательском процессе выполнен Metal probe: существующий
MTLCreateSystemDefaultDevice вернул NVIDIA RTX4050; IOSurface1920x1200,
BGRA8,120 последовательных newTextureWithDescriptor:iosurface:plane:
с освобождением каждой обёртки в autoreleasepool. Три серии:
36.574/55.789/27.929мс на120, то есть0.3048/0.4649/0.2327мс на обёртку.
Нет draw/upload/submit: тест показывает накладную стоимость API/импорта,
но не её обязательное повторение ровно один раз за кадр WindowServer.
Число обёрток на кадр в реальном WS этим тестом не измерялось.
Исходник и результат вне Git: diagnostics/probes/surface-wrap.m,
surface-wrap-result.txt. Система/драйверы при тесте не заменялись.

## Связь с исходниками

NVMTLDevice.m nvmtlNewSurfaceTexture создаёт новый wrapper. Существующий
weak cache используется для backing только если !backing->_vramOn;
VRAM-backed поверхности обходят этот reuse. nvmtl_vk_surface_vram
повторно импортирует/создаёт bindings, что соответствует видимым VA/ioctl
стекам. Длительное удержание импортов потребует явной инвалидации/lifetime,
а не замены weak cache на strong без ограничения памяти.

nvmtl_snapshot_set_c уже содержит H3 reuse и buffer-only fast path,
NVMTL_ENC78_OFF по умолчанию0, то есть эти оптимизации включены в исходниках.
Нельзя заявлять, что descriptor cache вообще отсутствует. Нужно измерять
попадания и причины dirty/смены layout/table page. Большая часть пути всё
ещё попадает в snapshot_set_md → Allocate/UpdateDescriptorSets.

nvmtlSurfaceIn хранит hostPages на texture; это не то же самое, что
разделяемый bounded IOSurface cache из внешнего предложения.

## Внешние первичные источники

https://github.com/nullmoth/nvidia-macos-driver/issues/368
Автор описывает churn host import/map/free и повторные VRAM wrappers
в WindowServer на RTX5080. Сообщённый выигрыш97→136fps относится к другой
машине; один комментатор не получил заметного улучшения аналогичного
подхода. Это не доказательство выигрыша на muxless4050.

https://github.com/KhronosGroup/Vulkan-Samples/blob/main/samples/performance/descriptor_management/README.adoc
Khronos описывает CPU-стоимость Allocate/UpdateDescriptorSets и reuse,
включая необходимость lifetime правил для наборов, используемых GPU.

Вывод: два CPU-переноса~3.62мс плюс work по descriptors/wrappers/LUT —
подтверждённые точки. Для следующего исправления предпочтительно проверять
bounded reuse импортов/wrappers или причины descriptor misses отдельно,
с пиксельным тестом/инвалидацией. Готового безопасного plugin-патча пока нет.
