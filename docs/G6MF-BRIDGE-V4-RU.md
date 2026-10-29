# G6 MF Bridge v4: AGDC-карта для Intel-панели

В v3 найден userspace crash WindowServer: SIGABRT, assert
`found != slist->end()` в `CA::OGL::Context::push_surface`.
Перед ним IOPresentment сообщает Unable to get AGDC information /
Unable to locate service dependencies / Unable to acquire map,
а CoreDisplay — System set to use IOP but no display pipes are present.
Исходный AGDC-модуль искал только NVRMNVDAFramebuffer, которого на этой
конфигурации нет. Поэтому AGDC=-1. Это подтверждённый пробел; является ли
он единственной причиной assert, покажет следующий аппаратный тест.

В v4 NVRMAGDC при nmoptimus=1 допускает отдельную Intel-панель со своим
controller index 0. AGDC slot 0 указывает на её настоящий IOFramebuffer,
а render PCI берётся у единственного NVRMRenderBridge. NVAccel продолжает
использовать внутренний head 4. Несколько render bridges считаются
неоднозначностью и отвергаются. Десктопный NVIDIA framebuffer сохраняет
приоритет. Intel публикует проверенный NVRMTiming из принятого firmware mode.
Преобразование 10-bit поверхностей и другие изменения формата не добавлялись.

Версии: NMIntelFB 0.1.3, NVRMAGDC 2.6.5 (локальная G6MF-сборка, не заявление
о новом релизе upstream). NVAccel 0.1.1 сохранена из v3. Инсталлятор проверяет
соответствие установленной v3 и сохраняет компоненты/KC до замены. Тестовая
и итоговая Auxiliary KC проверяются на самом ноутбуке перед переключением EFI.
Автообновление upstream во время испытаний не запускать.

## Запуск

В обычной Tahoe через текущую рабочую EFI выполнить:

```bash
sudo bash /Volumes/1401/NullMoth-G6MF-Bridge-v4/next-stage.sh
```

Как раньше, сначала выполняется NVIDIA shader test. При его отказе профиль
не включается. Затем ставятся согласованные компоненты и одноразовый
LaunchDaemon для следующего старта. Он не запускается в текущем сеансе,
не меняет sysctl/драйверы и не перезапускает WindowServer. Он читает AGDC,
IOPresentmentGetMap, IORegistry и счётчики head 4, сохраняет их на APFS в
`/Users/Shared/G6MF-BootReports/boot-*` и копирует на флешку, если та доступна.
После старта задания его plist удаляется, чтобы сбор не повторялся каждый раз.

При `NEXT STAGE READY` разрешить обновлённые расширения, если macOS просит,
и перезагрузиться через флешку 1401.

Если рабочий стол появился, двигать окна и выполнить:

```bash
sudo bash /Volumes/1401/NullMoth-G6MF-Bridge-v4/collect-bridge.sh
```

Если снова чёрный экран/verbose-консоль при живой системе, подождать
пять минут для автоматического сбора, штатно выключиться и вернуться
в Linux. Весь каталог `boot-reports` оставить на флешке.

## Возврат к Metal без захвата экрана

В Linux:

```bash
python3 /run/media/spotlight/1401/NullMoth-G6MF-Bridge-v4/prepare-bridge.py --restore
```

Возвращается EFI с -nmintelfboff. Новые компоненты останутся на диске,
но Intel не будет захвачен мостом. Если флешка не смонтировалась при чёрном
экране, после возврата в обычную Tahoe выполнить collect-macos.sh из этой
папки: он также заберёт внутренние G6MF-BootReports.

Для возврата самих компонентов/KC использовать напечатанный `before-bridge-*`
backup и rollback-bridge-macos.sh. В обычной Tahoe второй аргумент `/`,
в Recovery — точка монтирования macOS Data volume, backup указать путём
на этом томе. Не обновлять macOS между установкой и откатом старой KC.

## Статус

CPU-тесты проверяют настоящую логику выбора AGDC targets, slot map и ответа
0x980, проверки таймингов, старта, routing и rollback с имитацией отказа KC.
Они не подтверждают работоспособность частного протокола IOPresentment
на этом ноутбуке. Нужно увидеть непустую корректную карту, AGDC=1,
рост head-4 copy counters и видимый устойчивый вывод. MAP PRESENT отдельно
не считается успешным выводом. Сон, смена режима и полная Metal-совместимость
этим испытанием не квалифицируются.

Для архива CI на Linux сначала запустить prepare-bridge.py в распакованном
каталоге флешки. Для текущей 1401 план EFI уже подготовлен; активный профиль
при подготовке не менялся.
