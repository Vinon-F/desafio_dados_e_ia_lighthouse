-- Questão 4.1 - Código SQL
WITH orders_validos AS (
    SELECT o.*
    FROM orders o
    WHERE o.status in ('paid', 'confirmed')
),
customer_metrics AS (
    SELECT
        o.customer_id,
        SUM(o.total) AS faturamento_total,
        COUNT(DISTINCT o.id) AS frequencia,
        ROUND(SUM(o.total) / COUNT(DISTINCT o.id), 2) AS ticket_medio
    FROM orders_validos o
    GROUP BY o.customer_id
),
customer_categories AS (
    SELECT
        o.customer_id,
        COUNT(DISTINCT p.category_id) AS diversidade_categorias
    FROM orders_validos o
    JOIN order_items oi      ON oi.order_id = o.id
    JOIN product_variants pv ON pv.id = oi.product_variant_id
    JOIN products p          ON p.id = pv.product_id
    GROUP BY o.customer_id
),
clientes_elite AS (
    SELECT
        cm.customer_id,
        cm.faturamento_total,
        cm.frequencia,
        cm.ticket_medio,
        cc.diversidade_categorias
    FROM customer_metrics cm
    JOIN customer_categories cc ON cc.customer_id = cm.customer_id
    WHERE cc.diversidade_categorias >= 13
    ORDER BY cm.ticket_medio DESC, cm.customer_id ASC
    LIMIT 10
)
SELECT * FROM clientes_elite;

-- Questão 4 - TAREFA 3. SUM(QUANTITY)
WITH orders_validos AS (
    SELECT o.*
    FROM orders o
    WHERE o.status in ('paid', 'confirmed')
),
customer_metrics AS (
    SELECT
        o.customer_id,
        SUM(o.total) AS faturamento_total,
        COUNT(DISTINCT o.id) AS frequencia,
        SUM(o.total) / COUNT(DISTINCT o.id) AS ticket_medio
    FROM orders_validos o
    GROUP BY o.customer_id
),
customer_categories AS (
    SELECT
        o.customer_id,
        COUNT(DISTINCT p.category_id) AS diversidade_categorias
    FROM orders_validos o
    JOIN order_items oi      ON oi.order_id = o.id
    JOIN product_variants pv ON pv.id = oi.product_variant_id
    JOIN products p          ON p.id = pv.product_id
    GROUP BY o.customer_id
),
customer_elite AS (
    SELECT cm.customer_id
    FROM customer_metrics cm
    JOIN customer_categories cc ON cc.customer_id = cm.customer_id
    WHERE cc.diversidade_categorias >= 13
    ORDER BY cm.ticket_medio DESC, cm.customer_id ASC
    LIMIT 10
)
SELECT
    cat.id   AS category_id,
    cat.name AS categoria,
    SUM(oi.quantity) AS total_itens_comprados
FROM orders_validos o
JOIN order_items oi      ON oi.order_id = o.id
JOIN product_variants pv ON pv.id = oi.product_variant_id
JOIN products p          ON p.id = pv.product_id
JOIN categories cat      ON cat.id = p.category_id
WHERE o.customer_id IN (SELECT customer_id FROM customer_elite)
GROUP BY cat.id, cat.name
ORDER BY total_itens_comprados DESC
limit 1;