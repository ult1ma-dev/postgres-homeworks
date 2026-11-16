# Базовые SQL запросы. Домашнее задание

### Создание и наполнение БД

- Создайте новую БД `northwind`
- Откройте в pgAdmin _querytool_ и выполните там код из файл `northwind_script.sql`

### Написание sql-запросов

- Напишите sql-запросы на простые выборки в файле `simple_queries.sql`
- Напишите sql-запросы на фильтрацию и сортировки в `filter_sorting.sql`
- Напишите sql-запросы на фильтрацию по шаблону и группировки в `groupby.sql`

> **Note**
> <br>
> Писать и проверять запросы можно в pgAdmin, а далее код перенести в .sql-файлы.

> **Note**
> <br>
> В папке screenshots лежат скриншоты результатов, которые должны получиться по каждому sql-запросу.

## Решение

Выполнены все 17 заданий:

- [simple_queries.sql](simple_queries.sql) — 5 простых выборок.
- [filter_sorting.sql](filter_sorting.sql) — 5 запросов с фильтрацией, сортировкой и агрегатами.
- [groupby.sql](groupby.sql) — 7 запросов с `LIKE`, `IS NULL`, `GROUP BY`, `HAVING`, `INTERSECT` и `EXCEPT`.

Во всех запросах явно указана схема `public`. Для этого задания используется
полная база из `northwind_script.sql`, включая таблицы `products` и `suppliers`.

### Запуск в pgAdmin

1. Подключитесь к локальному серверу PostgreSQL и создайте базу `northwind`.
   Если она уже создана, используйте её.
2. Откройте Query Tool именно для базы `northwind` и выполните
   [northwind_script.sql](northwind_script.sql) в новой пустой базе.
3. Откройте SQL-файлы решения. Для проверки отдельного задания выделите его
   запрос целиком и выполните выделенный фрагмент.

### Запуск через psql на Windows

Команды PowerShell выполняются из корня репозитория. При подключении введите
пароль своего пользователя PostgreSQL.

```powershell
$psqlPath = 'C:\Program Files\PostgreSQL\18\bin\psql.exe'

# Создание базы выполняется один раз.
& $psqlPath -h localhost -U postgres -d postgres -c "CREATE DATABASE northwind;"

# Загрузка таблиц и данных в новую пустую базу.
& $psqlPath -X -v ON_ERROR_STOP=1 --single-transaction -h localhost -U postgres -d northwind -f homework-2\northwind_script.sql

# Выполнение запросов решения.
& $psqlPath -X -v ON_ERROR_STOP=1 -h localhost -U postgres -d northwind -f homework-2\simple_queries.sql
& $psqlPath -X -v ON_ERROR_STOP=1 -h localhost -U postgres -d northwind -f homework-2\filter_sorting.sql
& $psqlPath -X -v ON_ERROR_STOP=1 -h localhost -U postgres -d northwind -f homework-2\groupby.sql
```

Из скрипта загрузки убрана настройка `default_with_oids` для совместимости
с PostgreSQL 18. Поддержка табличных OID удалена в
[PostgreSQL 12](https://www.postgresql.org/docs/12/release-12.html).

### Проверка

Данные загружены через `psql`. Все 17 запросов выполнены на PostgreSQL 18.6
через `psycopg2`.
Результаты проверены по исходным строкам таблиц и эталонным скриншотам.
Для запросов без `ORDER BY` сравнивается набор результатов: порядок строк
в такой выборке не определён.

| Контрольная выборка | Результат |
| --- | --- |
| Количество заказов | 830 |
| Уникальные города клиентов | 69 |
| Уникальные страны отгрузки | 21 |
| Заказы во France, Germany, Spain | 222 |
| Уникальные пары «страна, город» отгрузки | 70 |
| Среднее число дней до отгрузки в Германию | 8.0083333333333333 |
| Минимальная и максимальная цена активных товаров | 2.5 и 263.5 |
| Те же цены при остатке не меньше 20 | 2.5 и 81 |
| Страны с клиентами, поставщиками и сотрудниками | UK, USA |
| Страны с клиентами и поставщиками, без сотрудников | 10 стран |

В запросе со средней длительностью `AVG` учитывает заказы с известной датой
отгрузки. В запросе № 5 файла `groupby.sql` сначала выбираются заказы
с известным регионом, затем применяется условие `HAVING` к сумме по стране.
