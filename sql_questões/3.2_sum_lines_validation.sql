SELECT
	(SELECT COUNT(*) FROM customers) +
	(SELECT COUNT(*) FROM orders) +
	(SELECT COUNT(*) FROM order_items) +
	(SELECT COUNT(*) FROM payments) AS soma_total_linhas;

SELECT
	(SELECT COUNT(*) FROM customers) AS customers_total,
	(SELECT COUNT(*) FROM orders) AS orders_total,
	(SELECT COUNT(*) FROM order_items) AS order_items_total,
	(SELECT COUNT(*) FROM payments) AS payments_total,
	(SELECT COUNT(*) FROM customers) +
	(SELECT COUNT(*) FROM orders) +
	(SELECT COUNT(*) FROM order_items) +
	(SELECT COUNT(*) FROM payments) AS sum_total;