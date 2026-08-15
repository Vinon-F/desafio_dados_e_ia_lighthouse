import pandas as pd


# 1. CARREGAMENTO DOS DADOS

products = pd.read_csv('./csv/products.csv')
variants = pd.read_csv('./csv/product_variants.csv')
orders   = pd.read_csv('./csv/orders.csv', parse_dates=['placed_at'])
items    = pd.read_csv('./csv/order_items.csv')

products = products.rename(columns={'id': 'product_id'})
variants = variants.rename(columns={'id': 'variant_id'})
orders   = orders.rename(columns={'id': 'order_id'})

if 'id' in items.columns:
    items = items.rename(columns={'id': 'order_item_id'})

# CRIAÇÃO DO DATASET UNIFICADO (todos os produtos)

def criar_dataset_unificado(items, orders, variants, products,
                             status_validos=('paid', 'confirmed')):

    df = items.merge(
        orders[['order_id', 'placed_at', 'status']],
        on='order_id',
        how='left',
        validate='many_to_one'
    )

    df = df.merge(
        variants[['variant_id', 'product_id', 'sku']],
        left_on='product_variant_id',
        right_on='variant_id',
        how='left',
        validate='many_to_one'
    )

    df = df.merge(
        products[['product_id', 'name']],
        on='product_id',
        how='left',
        validate='many_to_one'
    )

    # Checagem de integridade: o merge não pode ter alterado a
    assert len(df) == len(items), (
        f"Merge alterou o número de linhas: {len(items)} -> {len(df)}. "
        "Verifique duplicidade de chaves em variants/products/orders."
    )

    # Filtro de status aplicado dentro da função unificadora, mas

    df = df[df['status'].isin(status_validos)].copy()

    return df


def filtrar_por_nome_produto(df, nome_produto):
    """
    Filtra o dataset unificado por nome de produto.
    Trata o caso de nomes duplicados com product_id distintos
    (ex.: cadastro duplicado no catálogo) agregando-os juntos.
    """
    ids = df.loc[df['name'] == nome_produto, 'product_id'].unique().tolist()
    if not ids:
        raise ValueError(f"Nenhum product_id encontrado para '{nome_produto}'")
    return df[df['product_id'].isin(ids)].copy()


def agregar_mensal(df, coluna_qtd='quantity'):
    """
    Agrega quantidade vendida por mês, preenchendo meses sem venda
    com 0 para manter a continuidade da série temporal.
    """
    df = df.copy()
    df['month'] = df['placed_at'].dt.to_period('M')
    monthly = df.groupby('month')[coluna_qtd].sum().sort_index()

    full_idx = pd.period_range(monthly.index.min(), monthly.index.max(), freq='M')
    monthly = monthly.reindex(full_idx, fill_value=0)
    return monthly

# 3. APLICAÇÃO: dataset unificado -> produto alvo -> série mensal

dataset = criar_dataset_unificado(items, orders, variants, products)

produto_alvo = filtrar_por_nome_produto(dataset, 'Bússola de Bordo 702')

monthly = agregar_mensal(produto_alvo)

# 4. BASELINE: MÉDIA MÓVEL DOS ÚLTIMOS 3 MESES

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

# MÉTRICAS (MAE)
mae = df_resultado['erro_abs'].mean()
print(f'\nMAE: {mae:.2f} unidades')

print(f"Média histórica mensal (treino): {treino.mean():.2f}")
print(f"MAE como % da média histórica: {mae / treino.mean():.1%}")
print(f"Previsão do total de vendas para o primeiro trimestre: {round(df_resultado['previsto'].sum())}")