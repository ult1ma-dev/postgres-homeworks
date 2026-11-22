-- Подключиться к БД Northwind и сделать следующие изменения:
BEGIN;

-- 1. Добавить ограничение на поле unit_price таблицы products (цена должна быть больше 0)
ALTER TABLE public.products
    ADD CONSTRAINT products_unit_price_positive
    CHECK (unit_price > 0);

-- 2. Добавить ограничение, что поле discontinued таблицы products может содержать только значения 0 или 1
ALTER TABLE public.products
    ADD CONSTRAINT products_discontinued_values
    CHECK (discontinued IN (0, 1));

-- 3. Создать новую таблицу, содержащую все продукты, снятые с продажи (discontinued = 1)
CREATE TABLE public.discontinued_products AS
SELECT *
FROM public.products
WHERE discontinued = 1;

-- 4. Удалить из products товары, снятые с продажи (discontinued = 1)
-- Для 4-го пункта может потребоваться удаление ограничения, связанного с foreign_key. Подумайте, как это можно решить, чтобы связь с таблицей order_details все же осталась.
-- ON DELETE CASCADE сохраняет внешний ключ и удаляет позиции заказов,
-- которые ссылаются на удаляемые товары.
ALTER TABLE public.order_details
    DROP CONSTRAINT fk_order_details_products;

ALTER TABLE public.order_details
    ADD CONSTRAINT fk_order_details_products
    FOREIGN KEY (product_id)
    REFERENCES public.products (product_id)
    ON DELETE CASCADE;

DELETE FROM public.products
WHERE discontinued = 1;

COMMIT;
