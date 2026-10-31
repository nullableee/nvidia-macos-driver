# Safari / открытые настройкиДисплеи,0.4.5

profile-20261030-224708-1951/perf-20261030-224708-1966.
Direct1/cache128. Copies56.81/s,VBL6.0994ms,entry17.5871ms,
handler3.8030ms,fence0.8471ms,Intelcopy2.0478ms. Nestedtimingsперекрываются;
17.6-3.8нельзяобъявлятьчистымGPUtime. Startupmax100msнемоментзамера.
НетновыхGPUtimeout:12→12,IOP/pageofffail0,directheld0/timeout0.

Кэш128в22:47:09.091→22:47:28.590:3072calls/3036hits/36creates=98.828%hits.
Политика5постоянна,установиласькпервойзаписи;30позднихсозданийпример
неустранённойдинамикиразмера/новыхповерхностей,неполныйисходныйLRUthrash.
Увеличиватьбюджетещёрадиэтойпросадкинедоказанно.

WSmain1808samples:Mach636(499serverloop),allocsets16,snapshot10,
VAmach27,allocmemoryMach22,bindmemMach17. Samplingcountsнеframe-ms/CPU%.
Крупногоновогобагаизэтогосэмпланеопределено. CPUwrite109callsпо0.5039ms,
массовоепромежуточноекопированиене вернулось.

Вконцесбораprocesssnapshot:WindowServer113.2%CPU,DisplaysExt96.2%,
VTDecoder55.7%,Safari29%,WindowManager32%. Этомоментные/psоценки,
непрофильCPUза20с. ПрипоследующейпроверкеDisplaysExt98.8%,VTDecoder121.7%,
Safari0%—другаянагрузкапродолжаласьпослеSafariсценария.
Userподтвердил:настройки«Дисплеи»былиоткрытывовремязамера.

Безrootснятысвежие4sown-userпроцессыDisplaysExtPID728/VTDecoder736,
сохраненыdiagnostics/safari-0.4.5. ВVTDecoderестьVCPHEVC/VideoToolbox,
VTMetalTransferSessionTransferImageSync,shadertranslation/pipelinecreation.
Это подтверждаетdecoder+Metalработу,ноНЕдоказываетеёполнуюпривязкук
DisplaysExtилистабильнуюстоимостькомпиляциикаждыйframe. Снятыпозже20sокна.
Вэтомчатеappне закрывали/процессынеубивали/настройкинеизменяли.

Следующийнеобходимыйконтроль:закрытьSystemSettingsобычночерезUI,
повторитьтотже20sprofileSafari. Сравнитьcadence/fence/CPUprocesses/cache.
НельзяпростообъявитьSafariилидрайвервиновным,исходныйсценарийсмешанный.
Повторнаяустановка/ребутне нужны,cache128/direct1сейчасактивны.
