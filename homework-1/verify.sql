-- Выполнить в Query Tool pgAdmin в базе north после запуска main.py.
SELECT 'employees' AS table_name, COUNT(*) AS row_count FROM employees
UNION ALL
SELECT 'customers', COUNT(*) FROM customers
UNION ALL
SELECT 'orders', COUNT(*) FROM orders;

-- Пример заказа с данными клиента и сотрудника.
SELECT
    o.order_id,
    o.order_date,
    c.company_name,
    e.first_name,
    e.last_name,
    o.ship_city
FROM orders AS o
JOIN customers AS c ON c.customer_id = o.customer_id
JOIN employees AS e ON e.employee_id = o.employee_id
ORDER BY o.order_id
LIMIT 10;

-- Должно получиться 0: все заказы связаны с клиентами и сотрудниками.
SELECT COUNT(*) AS orders_without_relations
FROM orders AS o
LEFT JOIN customers AS c ON c.customer_id = o.customer_id
LEFT JOIN employees AS e ON e.employee_id = o.employee_id
WHERE c.customer_id IS NULL OR e.employee_id IS NULL;
