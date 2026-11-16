import streamlit as st
import pandas as pd
import plotly.express as px

# Aplicación realizada en clase

# Configuracion pagina
st.set_page_config(layout='wide', initial_sidebar_state="collapsed")
st.sidebar.header("Filtros")
st.title('KORA - clientes')

# Carga de informacion
clientes = pd.read_csv("KORA_clientes.csv", parse_dates=['fecha_registro'])
pedidos = pd.read_csv("KORA_pedidos.csv", parse_dates=['fecha_pedido'])

df_intermedio = pedidos.groupby("id_cliente", as_index=False).agg(
    n_pedidos=("id_pedido", 'count'),
    ingreso_total=("ingreso_neto_cop", 'sum'), 
    ultima_compra=('fecha_pedido', 'max'))
df_final = clientes.merge(df_intermedio, how='left', on='id_cliente', validate='one_to_one')

df_final['n_pedidos'] = df_final['n_pedidos'].fillna(0)
df_final['ingreso_total'] = df_final['ingreso_total'].fillna(0)

fecha_corte = pd.Timestamp('2026-10-31')
df_final['dias_sin_compra'] = (fecha_corte - df_final['ultima_compra']).dt.days

def segmento(f):
    if f['n_pedidos'] == 0: return 'Sin compras'
    if f['dias_sin_compra'] > 90: return 'En pausa'
    if f['n_pedidos'] >= 3 and f['dias_sin_compra'] <= 90: return 'Fieles'
    if f['n_pedidos'] == 1 and f['dias_sin_compra'] <= 90: return 'Primerizos'
    if f['n_pedidos'] == 2 and f['dias_sin_compra'] <= 90: return 'En desarrollo'
df_final['Segmento'] = df_final.apply(segmento, axis=1)    

#Filtros

ciudades = st.sidebar.multiselect('Ciudad', sorted(df_final['ciudad'].unique()), 
                                  default=sorted(df_final['ciudad'].unique()))
filtrado_ciudades = df_final['ciudad'].isin(ciudades)

canales = st.sidebar.multiselect('Canal', df_final['canal_adquisicion'].unique(), 
                                 default=df_final['canal_adquisicion'].unique())
filtrado_canales = df_final['canal_adquisicion'].isin(canales)

segmento_f = st.sidebar.multiselect('Segmento', df_final['Segmento'].unique(), 
                                  default=df_final['Segmento'].unique())

filtrado_segmento = df_final['Segmento'].isin(segmento_f)

filtrado = df_final[(filtrado_ciudades) & (filtrado_segmento) & (filtrado_canales)]

#Punto 5: Filtro por preferencia declarada

preferencia = st.sidebar.multiselect('Preferencia Declarada', df_final['preferencia_declarada'].unique(),
                                     default=df_final['preferencia_declarada'].unique())
filtrado_preferencia = df_final['preferencia_declarada'].isin(preferencia)

filtrado = df_final[(filtrado_ciudades) & (filtrado_segmento) & (filtrado_canales) & (filtrado_preferencia)]

#Crear KPIs

compradores = filtrado.query('n_pedidos > 0')
recompra = compradores['n_pedidos'].ge(2).mean() if len(compradores) > 0 else 0
ingreso = filtrado['ingreso_total'].sum()
pedidos_totales = filtrado['n_pedidos'].sum()

a, b, c, d = st.columns(4)

a.metric('Compradores', len(compradores), border=True)
b.metric('Total de pedidos', f'{pedidos_totales:.0f}', border=True)
c.metric('Ingresos totales', f'{ingreso/1e6:.1f}M', border=True)
d.metric('Recompra', f'{recompra:.1%}', border=True) 

#Punto 1:

st.subheader("""¿Por qué la tasa de recompra por sí sola no basta para elegir el canal más adecuado?
             
La tasa de recompra mide el porcentaje de compradores de un canal que han realizado dos o más pedidos, y se calcula dividiendo 
el número de clientes con dos o más pedidos entre el número total de clientes con al menos una compra, multiplicando el resultado por 100.
Sin embargo, esta tasa por sí sola no es suficiente para elegir el canal más adecuado para una campaña de segunda compra, 
porque no considera el número de clientes que podrían participar en ella. Por eso, es necesario analizar ambas métricas. 
El número de clientes con exactamente una compra representa a los compradores que todavía 
no han realizado un segundo pedido y que podrían ser el público objetivo de la campaña.""")

# Punto 2: Nueva metricas

una_compra = compradores.query('n_pedidos == 1')
porcentaje_una_compra = (len(una_compra) / len(compradores) * 100) if len(compradores) > 0 else 0

e, f = st.columns(2)
e.metric('Clientes con una compra', len(una_compra), border=True)
f.metric('Porcentaje', f'{round(porcentaje_una_compra, 2)}%', border=True) 


# Gráfica clientes por segmento
tabla = filtrado.groupby('Segmento', as_index=False).agg(total_clientes=('id_cliente', 'count'))
fig_segmentos = px.bar(data_frame=tabla, x='Segmento', y='total_clientes', text='total_clientes')
fig_segmentos.update_layout(title='Número de clientes por segmento', xaxis_title='Segmento', yaxis_title='Clientes')
fig_segmentos.update_traces(marker_color=['#66ACED', '#66E6ED', '#66ED9A', '#099976', '#C7C761'])

#Grafica ingresos por categoria
pedidos_filtrado = pedidos[pedidos['id_cliente'].isin(filtrado['id_cliente'])]
categorias = pedidos_filtrado.groupby('categoria', as_index=False).agg(Total_Pedidos=('id_pedido', 'count'), 
                                              Total_ingresos=('ingreso_neto_cop', 'sum'))

fig_categoria = px.bar(data_frame=categorias, y='categoria', x='Total_ingresos', text='Total_ingresos', orientation='h')
fig_categoria.update_layout(title='Ingresos totales por categoria', xaxis_title='Ingresos netos COP', yaxis_title='Categorias')
fig_categoria.update_traces(marker_color='#2285C9')
    
#Graficas una al lado de la otra: 
gra1, gra2 = st.columns(2)

with gra1: 
    with st.container(border=True):
        st.plotly_chart(fig_segmentos, width='stretch')
with gra2: 
    with st.container(border=True):
        st.plotly_chart(fig_categoria, width='stretch')
    
#Grafica de lineas
pedidos_filtrado['mes'] = pedidos_filtrado['fecha_pedido'].dt.to_period('M').astype(str)
serie = pedidos_filtrado.groupby('mes', as_index=False).agg(Numero_pedidos=('id_pedido', 'count'))
fig_serie = px.line(data_frame=serie, x='mes', y='Numero_pedidos', markers=True)
fig_serie.update_layout(title='Número de pedidos por mes', xaxis_title='Mes', yaxis_title='Número total de pedidos')
fig_serie.update_traces(marker_color='#2285C9', line_color='#2285C9', line_width=3)

with st.container(border=True):
    st.plotly_chart(fig_serie, width='stretch')

# Punto 3: Comparación por canales clientes con 2+ pedidos

comparacion_canales = compradores.groupby('canal_adquisicion', as_index=False).agg(
    total_compradores=('id_cliente', 'count'),
    clientes_recompra=('n_pedidos', lambda x: (x >= 2).sum()))

comparacion_canales['porcentaje'] = (
    comparacion_canales['clientes_recompra']
    / comparacion_canales['total_compradores'] * 100
)

comparacion_canales = comparacion_canales.sort_values('porcentaje', ascending=False)

fig_comparacion = px.bar(
    data_frame=comparacion_canales,
    x='canal_adquisicion',
    y='porcentaje',
    text='porcentaje',
    hover_data={
        'total_compradores': True,
        'clientes_recompra': True,
        'porcentaje': ':.1f'},
    title='Tasa de recompra por canal',
    labels={
        'canal_adquisicion': 'Canal de adquisición',
        'porcentaje': 'Tasa de recompra (%)',
        'total_compradores': 'Total compradores',
        'clientes_recompra': 'Compradores con 2+ pedidos'})

fig_comparacion.update_traces(
    texttemplate='%{y:.1f}%',
    textposition='outside',
    marker_color='#2285C9'
)

fig_comparacion.update_layout(yaxis_range=[0, 110])

with st.container(border=True):
    st.plotly_chart(fig_comparacion, width='stretch')
        
st.write("""Se eligió un gráfico de barras porque permite comparar
fácilmente las tasas de recompra entre los canales de
adquisición. Además, la información interactiva muestra
cuántos compradores componen cada tasa, lo que permite
interpretar los porcentajes considerando el tamaño de
cada grupo.""")

#Punto 4: Comparacion entre canales los compradores con una sola compra

comparacion_canales_una_compra = una_compra.groupby('canal_adquisicion', as_index=False).agg(
    total_clientes=('n_pedidos', 'count')).sort_values(by='total_clientes', ascending=False)
fig_comparacion_canales_una_compra = px.bar(data_frame=comparacion_canales_una_compra, 
                                            x='canal_adquisicion',
                                            y='total_clientes', 
                                            text='total_clientes')
fig_comparacion_canales_una_compra.update_layout(title='Número de clientes con una sola compra por canal', 
                                                 xaxis_title='Canales de adquisicion',
                                                 yaxis_title='Total de clientes')
fig_comparacion_canales_una_compra.update_traces(marker_color=['#008C41', '#00FF7B', '#18A85E', '#17E379'] )

with st.container(border=True):
    st.plotly_chart(fig_comparacion_canales_una_compra, width='stretch')
    
st.subheader("""¿El canal con mayor volumen coincide necesariamente con el de menor tasa de recompra?
         
En el caso de KORA, el canal con mayor volumen de clientes con exactamente una compra coincide con 
el de menor tasa de recompra. Redes sociales tiene 147 clientes que han realizado una sola compra y presenta 
una tasa de recompra del 59,6 %, la más baja entre los cuatro canales analizados. 
Por otro lado, orgánico tiene solamente 48 clientes con una compra y presenta la tasa de recompra más alta, con un 75.9%.""")

#Punto 6: Recomendación canal

st.subheader("""Recomendación y limitaciones de los datos: 
             
Se recomendaría iniciar el piloto en Redes Sociales. Este canal 364 compradores en total, de los cuales 147 clientes 
tienen una sola compra. Además, este canal cuenta con la tasa de Recompra más baja con un 59.6%, frente al 75.9% 
del canal Orgánico, que tiene 48 clientes de 196 en total. Por este motivo, Redes Sociales representa el 
canal con mayor margen de mejora. 

Una limitación es que los datos no permiten identificar las razones por las que los clientes no
han vuelto a comprar. 
             
Una métrica recomendada para evaluar al piloto podría ser la tasa de conversión a segunda compra, 
calculando el porcentaje de clientes participantes en la campaña que realizan una segunda compra durante el periodo
de evaluación. 
             """)

