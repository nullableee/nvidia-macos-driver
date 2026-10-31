# v12: успешная аппаратная загрузка

Пользователь подтвердил сохранение Glass/ускорения и собрал startup.
Root-only каталог: kits/agdc-v12/startup-20261030-162720-820. Его файлы
текущему процессу напрямую недоступны; результат дополнительно проверен
по живым sysctl, loaded kexts и отдельной доступной выгрузке unified log.

В16:26:19.096 AGDC выбрал PEGP + NMIntelFB, slot0 = Intel registryID
0x100000587, UP с1 framebuffer. В16:26:19.297 auto-go сообщил heads0x10
accel4 agdc1 k5=1 iop1. kern.safeboot0, NVRMAGDC2.6.6, NVAccel0.1.5,
stage_map_copy0. Свежих WindowServer crash reports после прошлых аварий
15:54/15:58 не обнаружено. Это один успешный boot, не доказательство
устранения всех гонок и не измерение FPS.
