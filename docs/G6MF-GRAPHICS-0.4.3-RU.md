# Graphics 0.4.3: framebuffer input и маска ресурсов

Подготовлен kit, установка не выполнялась. Сейчас система 0.4.2.

В профиле 0.4.2 осталось 181.78 descriptor writes на новый set. Найден
дефект nvmtl_spirv_bmask: отдельные input attachments set3 bindings192..199
воспринимались как неизвестные stage bindings. Возврат0 выключал gmask_ok
для обеих стадий pipeline. Fallback писал почти весь layout, а metadata
reuse0.4.2 при такой маске сработать не мог.

Исправление запоминает set3 отдельно от set2 и пропускает только известный
framebuffer band в set3. Binding192 в stage set0 и неизвестный200 вset3
продолжают отвергаться. Парсер проверяет целое число SPIRV words и границы
инструкций; порядок Binding/DescriptorSet неважен. Отдельная привязкаset3,
shaders/renderpass/WindowServer default fetch-off не менялись.

В пользовательском SPIRV cache312модулей,23старых отказа, все из-за
framebuffer bindings192..194 вset3; новый parser принимает312. Это не
кэш WindowServer. Вклад именно в WS требует аппаратного профиля.

## GPU-проверки

Render probe рисует2048отдельных пикселей, каждый сравнивается с ожидаемым.
Texture, sampler и shader mask changes имеют разные результаты. Live fetch
читает ненулевой clear0.25; fetch-off —нулевую отдельно привязанную dummy
attachment, как текущий WindowServer.

| Сценарий | sets | writes | metadata hits |
|---|---:|---:|---:|
| Старый0.4.2, metadata ON, framebuffer input |2049|395457|0|
| Новый0.4.3, metadata OFF, framebuffer input |2049|4096|0|
| Новый0.4.3, metadata ON, framebuffer input |9|16|2040|
| Новый, смена sampler |1369|2736|680|
| Новый, смена shader mask |2049|4096|0|

Последние3случая прошли и с fetch-off, и с реальным ненулевым fetch.
Mode0→mode0 изолирует parser: число sets не меняется, writes сокращаются
395457→4096. Metadata ON добавляет уже существующий путь0.4.2. Это счётчики
работы synthetic renderer, не FPS; encode timings шумят, прогноз не делается.

Прошли compute2000outputs mode0/1, sampler/mask/outputbuffer churn;
weak/bounded stress по4000wrappers, heldcache LRU/64MiB/lifetime/inflight,
BGRA1920x1200/RGBA16Float1920x1200, swizzle и64ordered queue copies.
Логи builds/graphics-0.4.3. Тест production scanner извлекает непосредственно
C-функцию; negative controls старого отказа и пропуска всехset3bindings
отклонены. Installer16модельных сценариев, включая rollbackfetchzero/live.

## Пакет

kits/graphics-0.4.3: подписанный payload, SHA256SUMS, identity guard текущего
0.4.2, полный backup/restore, native checks перед публикацией.
UUID9BF7F116-D5F8-3047-96B6-0242252E622B, SHA256
1db934baa811186efd5b8ee4abd3d4a55d9c94d47bcb25d3819fac8a47f503db.

install.sh→GRAPHICS0.4.3READY→обычная перезагрузка→проверка стекла,
2–3мин прогрева→test-desktop.sh безsudo. Он запроситsudo для20с профиля,
затем20с inputprobe обычным пользователем. Повторить прежнее движение окон
и состав приложений. Сравнить writes/sets/hits, copy cadence, input/timeout.
EFI/kexts/queuepolicy не меняются. Результат0.4.2 —в отдельном RESULTдокументе.
