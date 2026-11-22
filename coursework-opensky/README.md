# Самолёты в воздушном пространстве десяти стран

Программа загружает текущие наблюдения OpenSky в PostgreSQL. Она определяет страну по положению борта внутри её географической границы. В список по умолчанию входят Австрия, Бельгия, Венгрия, Германия, Люксембург, Польша, Словакия, Словения, Чехия и Швейцария.

## Запуск

Понадобятся Python 3.10 или новее и PostgreSQL. Команды ниже рассчитаны на PowerShell и запускаются из корня репозитория.

```powershell
cd coursework-opensky
py -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt

$env:PGHOST = '127.0.0.1'
$env:PGPORT = '5432'
$env:PGUSER = 'postgres'
$env:PGDATABASE = 'opensky_coursework'
$env:PGPASSWORD = [System.Net.NetworkCredential]::new('', (Read-Host 'Пароль PostgreSQL' -AsSecureString)).Password
```

При первом запуске создайте пустую базу. Для PostgreSQL 18 со стандартным путём установки команда выглядит так. Если база уже создана, переходите к загрузке.

```powershell
& 'C:\Program Files\PostgreSQL\18\bin\createdb.exe' --maintenance-db=postgres opensky_coursework
```

Загрузите наблюдения и посмотрите распределение бортов по странам.

```powershell
.\.venv\Scripts\python.exe -m airspace load
.\.venv\Scripts\python.exe -m airspace counts
```

`load` выводит время наблюдения в UTC и число записанных стран и бортов. Отчёты читают сохранённый снимок. Чтобы обновить его, снова запустите `load`. Список стран можно менять, например `python -m airspace load --countries Austria Czechia Germany Poland` в активированном окружении. Параметры подключения также можно передать одной строкой в переменной `DATABASE_URL`.

## Отчёты DBManager

После активации окружения каждую команду из таблицы можно выполнить как `python -m airspace КОМАНДА`. Все методы доступны и из Python через `from airspace.db_manager import DBManager`.

| Команда | Метод | Результат |
| --- | --- | --- |
| `counts` | `get_countries_and_aeroplanes_count()` | Страны и количество бортов в каждой. Благодаря `LEFT JOIN` в выборку входят страны с нулём наблюдений. |
| `all` | `get_all_aeroplanes()` | Полная запись каждого борта, страна наблюдения и время снимка. |
| `avg` | `get_avg_speed()` | Средняя путевая скорость в м/с. SQL-функция `AVG` учитывает только известные скорости. При отсутствии измерений метод возвращает `None`. |
| `faster` | `get_aeroplanes_with_higher_speed()` | Борта со скоростью строго выше средней по всему снимку. |
| `find ACA` | `get_aeroplanes_with_keyword("ACA")` | Борта, в позывном которых встречается `ACA`. Регистр букв произвольный, символы `%` и `_` ищутся буквально. |

## Источники и хранение

Nominatim возвращает центр страны и геометрию её границы. При первом запуске программа запрашивает страны последовательно с паузой не менее секунды, а ответы кэширует в `.cache/places.sqlite3`. При следующих запусках сохранённые границы читаются с диска. Адрес другого сервера можно задать через `NOMINATIM_URL`. Геоданные © OpenStreetMap contributors. [Документация Nominatim](https://nominatim.org/release-docs/latest/api/Search/) · [Правила публичного сервиса](https://operations.osmfoundation.org/policies/nominatim/) · [Условия использования данных OpenStreetMap](https://www.openstreetmap.org/copyright).

OpenSky получает один запрос `/states/all` на общий прямоугольник выбранных стран. Из ответа программа выбирает борта с известными координатами и `on_ground = false`, затем проверяет вхождение точки в полигон страны с учётом островов и анклавов. Для точки на общей границе выбирается первая страна в порядке кодов ISO. Поле `origin_country` хранит страну, которую OpenSky определил по адресу транспондера. Число наблюдений зависит от времени и покрытия приёмниками. Публичный режим работает без ключей. Для доступа через OAuth2 задайте обе переменные `OPENSKY_CLIENT_ID` и `OPENSKY_CLIENT_SECRET`. [Документация OpenSky](https://openskynetwork.github.io/opensky-api/rest.html).

Таблица `aviation.countries` хранит код и название страны, координаты центра, границы прямоугольника и время снимка. В `aviation.aeroplanes` ключом служит ICAO24, а внешний ключ `country_code` связывает борт со страной наблюдения. Сохраняются позывной, координаты, высоты, скорость, курс, время последнего контакта и остальные поля вектора состояния OpenSky. Обе таблицы обновляются в одной транзакции. При ошибке загрузки предыдущий снимок остаётся доступен. [Схема PostgreSQL](airspace/schema.sql).

## Проверка

При загрузке **22 ноября 2026 года в 11:12:09 UTC** в базе оказалось **735 бортов** над **10 странами**. Сумма десяти счётчиков совпала с числом уникальных ICAO24. Средняя скорость составила **171,09 м/с**, у **463** бортов скорость была выше средней.

Проверки географического отбора можно запустить без сети. Для проверки пяти методов на известных данных, повторной загрузки и отката транзакции задайте `AIRSPACE_TEST_POSTGRES=1`. Тест сам создаёт и удаляет временную базу, для этого пользователю PostgreSQL нужно право `CREATEDB`.

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
$env:AIRSPACE_TEST_POSTGRES = '1'
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```
