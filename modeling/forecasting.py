import pandas as pd

# 1. CARREGAMENTO DOS DADOS
products = pd.read_csv('../csv/products.csv')
variants = pd.read_csv('../csv/product_variants.csv')
orders   = pd.read_csv('../csv/orders.csv', parse_dates=['placed_at'])
items    = pd.read_csv('../csv/order_items.csv')

# 2. UNIFICAÇÃO DO DATASET
# Filtra o produto pelo nome (existem 2 product_id com o mesmo nome -> tratados juntos)
target = products[products['name'] == 'Bússola de Bordo 702']
target_ids = target['id'].tolist()

variant_ids = variants[variants['product_id'].isin(target_ids)]['id'].tolist()

oi = items[items['product_variant_id'].isin(variant_ids)]

merged = (
    oi.merge(orders, left_on='order_id', right_on='id', suffixes=('_item', '_order'))
      .merge(variants[['id', 'product_id', 'sku']], left_on='product_variant_id', right_on='id',
             suffixes=('', '_variant'))
      .merge(products[['id', 'name']], left_on='product_id', right_on='id', suffixes=('', '_product'))
)

# FILTRO POR STATUS DE PEDIDO
valid = merged[merged['status'].isin(['paid', 'confirmed'])].copy()

# AGREGAÇÃO MENSAL
valid['month'] = valid['placed_at'].dt.to_period('M')
monthly = valid.groupby('month')['quantity'].sum().sort_index()

# Continuidade (meses sem venda = 0)
full_idx = pd.period_range(monthly.index.min(), monthly.index.max(), freq='M')
monthly = monthly.reindex(full_idx, fill_value=0)

# 4. BASELINE: MÉDIA MÓVEL DOS ÚLTIMOS 3 MESES (sem usar valores reais de JAN, FEV e MAR)
treino = monthly[monthly.index <= pd.Period('2025-12', freq='M')]

prev_jan = treino.tail(3).mean()
prev_fev = (treino.tail(2).sum() + prev_jan) / 3
prev_mar = (treino.tail(1).sum() + prev_jan + prev_fev) / 3

previsoes = [prev_jan, prev_fev, prev_mar]

# PREVISÕES PARA O 1º TRIMESTRE DE 2026
test_months = pd.period_range('2026-01', '2026-03', freq='M')

resultados = []
for mes, previsto in zip(test_months, previsoes):
    real = monthly[mes]
    erro_abs = abs(previsto - real)
    resultados.append({
        'mes': str(mes),
        'previsto': round(previsto, 2),
        'real': int(real),
        'erro_abs': round(erro_abs, 2)
    })

df_resultado = pd.DataFrame(resultados)
print(df_resultado)

# MÉTRICAS (MAE):
mae = df_resultado['erro_abs'].mean()
print(f'\nMAE: {mae:.2f} unidades')

# Contexto adicional
train = monthly[monthly.index <= pd.Period('2025-12', freq='M')]
print(f"Média histórica mensal (treino): {train.mean():.2f}")
print(f"MAE como % da média histórica: {mae / train.mean():.1%}")
print(f"Previsão do total de vendas para o primeiro trimestre: {round(df_resultado['previsto'].sum())}")