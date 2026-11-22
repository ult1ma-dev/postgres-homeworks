BEGIN;

-- 1. Создать таблицу student с полями student_id serial, first_name varchar, last_name varchar, birthday date, phone varchar
CREATE TABLE public.student (
    student_id SERIAL PRIMARY KEY,
    first_name VARCHAR,
    last_name VARCHAR,
    birthday DATE,
    phone VARCHAR
);


-- 2. Добавить в таблицу student колонку middle_name varchar
ALTER TABLE public.student
    ADD COLUMN middle_name VARCHAR;

-- 3. Удалить колонку middle_name
ALTER TABLE public.student
    DROP COLUMN middle_name;

-- 4. Переименовать колонку birthday в birth_date
ALTER TABLE public.student
    RENAME COLUMN birthday TO birth_date;

-- 5. Изменить тип данных колонки phone на varchar(32)
ALTER TABLE public.student
    ALTER COLUMN phone TYPE VARCHAR(32);

-- 6. Вставить три любых записи с автогенерацией идентификатора
INSERT INTO public.student (first_name, last_name, birth_date, phone)
VALUES
    ('Иван', 'Иванов', DATE '2001-05-12', '+7-900-000-00-01'),
    ('Анна', 'Петрова', DATE '2002-08-23', '+7-900-000-00-02'),
    ('Алексей', 'Сидоров', DATE '2000-11-04', '+7-900-000-00-03')
RETURNING student_id;

-- 7. Удалить все данные из таблицы со сбросом идентификатор в исходное состояние
TRUNCATE TABLE public.student RESTART IDENTITY;

COMMIT;
