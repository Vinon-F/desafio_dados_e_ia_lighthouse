select
    COUNT(*) AS quantidade_linhas,
    MIN(created_at) AS data_minima,
    MAX(created_at) AS data_maxima,
    MIN(total) AS valor_minimo_total,
    MAX(total) AS valor_maximo_total,
    ROUND(AVG(total)::numeric, 2) AS valor_medio_total
FROM orders;