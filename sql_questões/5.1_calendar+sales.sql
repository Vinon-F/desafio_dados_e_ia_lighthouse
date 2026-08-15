WITH parametros AS (
    SELECT
        MIN(placed_at)::date AS data_inicio,
        MAX(placed_at)::date AS data_fim
    FROM orders
),
dim_data AS (
    SELECT
        d::date AS data_ref,
        EXTRACT(DOW FROM d) AS numero_dia_semana,
        CASE EXTRACT(DOW FROM d)
            WHEN 0 THEN 'Domingo'
            WHEN 1 THEN 'Segunda-feira'
            WHEN 2 THEN 'Terça-feira'
            WHEN 3 THEN 'Quarta-feira'
            WHEN 4 THEN 'Quinta-feira'
            WHEN 5 THEN 'Sexta-feira'
            WHEN 6 THEN 'Sábado'
        END AS nome_dia_semana
    FROM parametros p
    CROSS JOIN generate_series(p.data_inicio, p.data_fim, interval '1 day') AS d
),
vendas_diarias AS (
    SELECT
        o.placed_at::date AS data_venda,
        SUM(o.total) AS valor_total_dia
    FROM orders o
    WHERE o.channel = 'pos'
      AND o.status IN ('paid', 'confirmed')
    GROUP BY o.placed_at::date
),
calendario_vendas AS (
    SELECT
        dd.data_ref,
        dd.numero_dia_semana,
        dd.nome_dia_semana,
        COALESCE(vd.valor_total_dia, 0) AS valor_vendas_dia
    FROM dim_data dd
    LEFT JOIN vendas_diarias vd
        ON dd.data_ref = vd.data_venda
)
SELECT
    numero_dia_semana,
    nome_dia_semana,
    COUNT(*)                                              AS qtd_dias_no_periodo,
    SUM(CASE WHEN valor_vendas_dia > 0 THEN 1 ELSE 0 END) AS dias_com_venda,
    ROUND(AVG(valor_vendas_dia), 2)                       AS media_vendas_por_dia,
    ROUND(SUM(valor_vendas_dia), 2)                       AS total_vendas_periodo
FROM calendario_vendas
GROUP BY numero_dia_semana, nome_dia_semana
ORDER BY media_vendas_por_dia ASC;