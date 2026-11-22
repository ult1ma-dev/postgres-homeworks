# Data Definition Language. Домашнее задание

## Написание sql-запросов

- Напишите sql-запросы в файле `alter_student.sql`
- Напишите sql-запросы в файле  `alter_northwind.sql`

> Писать и проверять запросы можно в pgAdmin, а далее код перенести в .sql-файлы.

## Решение

- [alter_student.sql](alter_student.sql) выполняет все семь действий с таблицей
  `student`: создание, изменение колонок, вставку трёх строк и очистку со сбросом ID.
- [alter_northwind.sql](alter_northwind.sql) добавляет ограничения товаров,
  создаёт таблицу `discontinued_products` и удаляет снятые с продажи товары.

В обоих файлах явно указана схема `public`. Каждый файл содержит транзакцию
`BEGIN` / `COMMIT` и рассчитан на один последовательный запуск на исходной схеме.

### Внешний ключ и каскадное удаление

Внешний ключ `fk_order_details_products` пересоздаётся с правилом
`ON DELETE CASCADE`. Имя ограничения взято из исходного скрипта Northwind.
Связь `order_details.product_id → products.product_id` сохраняется и проверяется
PostgreSQL.

При удалении товара автоматически удаляются ссылающиеся на него позиции
в `order_details`. Данные самих снятых товаров предварительно копируются
в `discontinued_products`. На исходном наборе удаляется 10 товаров
и 310 связанных позиций заказов.

### Запуск на учебной копии базы

Для проверки создайте отдельную базу, например `northwind_hw4`, и загрузите
в неё [исходный набор Northwind](../homework-2/northwind_script.sql).
Затем выполните целиком `alter_student.sql` и `alter_northwind.sql`.
В pgAdmin эти файлы открываются в Query Tool выбранной учебной базы.

Команды PowerShell из корня репозитория:

```powershell
$psqlPath = 'C:\Program Files\PostgreSQL\18\bin\psql.exe'

& $psqlPath -X -v ON_ERROR_STOP=1 -h localhost -U postgres -d postgres -c "CREATE DATABASE northwind_hw4;"
& $psqlPath -X -v ON_ERROR_STOP=1 --single-transaction -h localhost -U postgres -d northwind_hw4 -f homework-2\northwind_script.sql
& $psqlPath -X -v ON_ERROR_STOP=1 -h localhost -U postgres -d northwind_hw4 -f homework-4\alter_student.sql
& $psqlPath -X -v ON_ERROR_STOP=1 -h localhost -U postgres -d northwind_hw4 -f homework-4\alter_northwind.sql
```

При подключении введите пароль своего пользователя PostgreSQL.
Для повторной полной проверки используйте новую учебную базу с исходными данными.

### Проверка

Оба скрипта выполнены на новой тестовой базе PostgreSQL 18.6.

| Проверка | Результат |
| --- | --- |
| Автоматические ID трёх студентов | 1, 2, 3 |
| Итоговые колонки `student` | `student_id`, `first_name`, `last_name`, `birth_date`, `phone` |
| Тип колонки `phone` | `VARCHAR(32)` |
| Очистка `student` | 0 строк, следующая вставка получает ID 1 |
| Снятые с продажи товары | Все 10 строк скопированы в `discontinued_products` |
| Оставшиеся товары | 67 активных товаров |
| Позиции заказов | 310 связанных позиций удалено, 1845 осталось |
| Внешний ключ | Существует, валиден, правило удаления `CASCADE` |
| Позиции без соответствующего товара | 0 |

Дополнительно проверено отклонение нулевой и отрицательной цены,
отклонение флагов `-1` и `2`, приём положительной цены и флагов `0` / `1`.
Отдельное пробное удаление подтвердило работу каскада; проба была отменена.
После завершения проверки тестовая база удалена.
