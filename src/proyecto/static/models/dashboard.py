import streamlit as st
import pandas as pd
import sqlite3
import plotly.express as px
import os
import requests
import statsmodels.api as sm

# --- Configuración de la página ---
st.set_page_config(layout="wide", page_title="Dashboard de KPIs Financieros ETH")

# --- Configuración de la base de datos y carga de datos ---

db_path = "enriched_historical.db"

script_dir = os.path.dirname(os.path.abspath(__file__))

data_dir_abs = os.path.abspath(os.path.join(script_dir, '..', 'static', 'data'))

enriched_db_path = os.path.join(data_dir_abs, db_path)

# Descargamos la base de datos desde GitHub si no existe
if not os.path.exists(enriched_db_path):
    st.write("-------Descargando la base de datos desde GitHub-------")
    try:
        url = "https://raw.githubusercontent.com/jimymora25/Tarea_2_Proyecto_Integrado_V/main/src/proyecto/static/data/enriched_historical.db"
        response = requests.get(url)
        if response.status_code == 200:
            os.makedirs(data_dir_abs, exist_ok=True)
            with open(enriched_db_path, "wb") as f:
                f.write(response.content)
            # st.write("✅ Base de datos descargada correctamente.") # Eliminado a petición del usuario
        else:
            st.error(f"❌ Error al descargar la base de datos: Código de estado {response.status_code}. Verifica la URL.")
            st.stop()
    except Exception as e:
        st.error(f"❌ Error al descargar la base de datos: {e}. Verifica la conexión a internet.")
        st.stop()

if not os.path.exists(enriched_db_path):
    st.error("❌ Error: No se pudo encontrar la base de datos después de intentar descargarla. La aplicación no puede continuar.")
    st.stop()
# else: # Eliminado a petición del usuario
#     st.write("✅ Base de datos disponible.") # Eliminado a petición del usuario

@st.cache_data
def load_data(path):
    """
    Carga los datos desde la base de datos SQLite y convierte la columna 'date' a datetime.
    """
    conn = sqlite3.connect(path)
    df = pd.read_sql_query("SELECT * FROM enriched_historical", conn)
    conn.close()
    df["date"] = pd.to_datetime(df["date"])
    return df

df = load_data(enriched_db_path)

# st.write("✅ Datos cargados correctamente") # Eliminado a petición del usuario
# st.dataframe(df.head()) # Eliminado a petición del usuario

# --- Cálculo de KPIs financieros ---

df["Price Change %"] = df["close"].pct_change() * 100
df["Moving Average 30"] = df["close"].rolling(window=30).mean()
df["Volatility"] = df["close"].rolling(window=30).std()
df["Cumulative Return"] = (1 + df["close"].pct_change().fillna(0)).cumprod()
df["Price Range"] = df["high"] - df["low"]

# st.write("✅ KPIs calculados correctamente!") # Eliminado a petición del usuario

# --- Configuración del dashboard ---
st.title("📊 Dashboard de KPIs Financieros de Ethereum (ETH)")

# Filtros de fecha en la barra lateral
st.sidebar.header("Filtros de Fecha")
start_date = st.sidebar.date_input("Fecha inicio", df["date"].min().date())
end_date = st.sidebar.date_input("Fecha fin", df["date"].max().date())

# Filtrar el DataFrame según las fechas seleccionadas
df_filtered = df[(df["date"] >= pd.to_datetime(start_date)) & (df["date"] <= pd.to_datetime(end_date))]

if df_filtered.empty:
    st.warning("No hay datos para el rango de fechas seleccionado. Por favor, ajusta las fechas.")
    st.stop()

# Asegura que las columnas 'year', 'month', 'day_of_week' existan para los gráficos
df_filtered_copy = df_filtered.copy()
df_filtered_copy['year'] = df_filtered_copy['date'].dt.year
df_filtered_copy['month'] = df_filtered_copy['date'].dt.month_name()
df_filtered_copy['day_of_week'] = df_filtered_copy['date'].dt.day_name()
df_filtered_copy['year_month_day'] = df_filtered_copy['date'].dt.to_period('D')


# --- Creación de Pestañas ---
tab_overview, tab_metrics, tab_trends, tab_individual_kpis, tab_comparative_analysis, tab_composition = st.tabs([
    "Resumen General",
    "Métricas Clave",
    "Tendencias Globales",
    "KPIs Individuales",
    "Análisis Comparativo",
    "Composición"
])

# Pestaña 1: Resumen General
with tab_overview:
    st.header("Resumen del periodo")
    st.write("Aquí puedes encontrar un resumen general de los datos.")
    st.dataframe(df_filtered_copy.head())

# Pestaña 2: Métricas Clave (valores numéricos)
with tab_metrics:
    st.header("Métricas Clave")
    col1, col2, col3 = st.columns(3)
    col4, col5, col6 = st.columns(3)

    with col1:
        st.metric("📈 Tasa de Variación (%)", f"{df_filtered_copy['Price Change %'].mean():.2f}%")
    with col2:
        st.metric("📉 Media Móvil (30 días)", f"{df_filtered_copy['Moving Average 30'].iloc[-1]:.2f}")
    with col3:
        st.metric("⚡ Volatilidad (STD Móvil 30 días)", f"{df_filtered_copy['Volatility'].iloc[-1]:.2f}")
    with col4:
        st.metric("📊 Retorno Acumulado", f"{df_filtered_copy['Cumulative Return'].iloc[-1]:.2f}")
    with col5:
        st.metric("📏 Rango de Precio (Máximo - Mínimo)", f"{df_filtered_copy['Price Range'].mean():.2f}")
    with col6:
        st.metric("💲 Precio de Cierre Promedio", f"{df_filtered_copy['close'].mean():.2f}")


# Pestaña 3: Tendencias Globales (todos los gráficos de línea juntos)
with tab_trends:
    st.header("Tendencias Globales de KPIs")

    st.plotly_chart(px.line(df_filtered_copy, x="date", y="Price Change %", title="Tasa de Variación (%) a lo largo del tiempo"))
    st.plotly_chart(px.line(df_filtered_copy, x="date", y="Moving Average 30", title="Media Móvil (30 días) del Precio de Cierre"))
    st.plotly_chart(px.line(df_filtered_copy, x="date", y="Volatility", title="Volatilidad (Desviación Estándar Móvil)"))
    st.plotly_chart(px.line(df_filtered_copy, x="date", y="Cumulative Return", title="Retorno Acumulado del Precio de Cierre"))


# Pestaña 4: KPIs Individuales (un gráfico por KPI, seleccionable o con opciones)
with tab_individual_kpis:
    st.header("Análisis de KPIs Individuales")

    kpi_options = {
        "Tasa de Variación (%)": "Price Change %",
        "Media Móvil (30 días)": "Moving Average 30",
        "Volatilidad (STD Móvil 30 días)": "Volatility",
        "Retorno Acumulado": "Cumulative Return",
        "Rango de Precio (Máximo - Mínimo)": "Price Range",
        "Precio de Cierre": "close",
        "Volumen": "volume"
    }
    selected_kpi_display = st.selectbox("Selecciona un KPI para ver su tendencia:", list(kpi_options.keys()))
    selected_kpi_column = kpi_options[selected_kpi_display]

    fig_individual = px.line(df_filtered_copy, x="date", y=selected_kpi_column, title=f"Tendencia de {selected_kpi_display}")
    st.plotly_chart(fig_individual)

    st.write("---")
    st.subheader("Comparación de KPIs")
    kpi_compare_1 = st.selectbox("Selecciona el primer KPI a comparar:", list(kpi_options.keys()), index=0, key='kpi_comp1')
    kpi_compare_2 = st.selectbox("Selecciona el segundo KPI a comparar:", list(kpi_options.keys()), index=1, key='kpi_comp2')

    if kpi_compare_1 and kpi_compare_2:
        fig_comparison = px.line(df_filtered_copy, x="date", y=[kpi_options[kpi_compare_1], kpi_options[kpi_compare_2]],
                                 title=f"Comparación de {kpi_compare_1} y {kpi_compare_2}")
        st.plotly_chart(fig_comparison)


# Pestaña 5: Análisis Comparativo
with tab_comparative_analysis:
    st.header("Análisis Comparativo")

    avg_close_by_year = df_filtered_copy.groupby('year')['close'].mean().reset_index()
    fig_bar_year = px.bar(avg_close_by_year, x='year', y='close',
                          title='Precio de Cierre Promedio por Año',
                          labels={'close': 'Precio Promedio de Cierre', 'year': 'Año'},
                          color='close', color_continuous_scale=px.colors.sequential.Viridis)
    st.plotly_chart(fig_bar_year)

    month_order = [
        'January', 'February', 'March', 'April', 'May', 'June',
        'July', 'August', 'September', 'October', 'November', 'December'
    ]
    avg_vol_by_month = df_filtered_copy.groupby('month')['Volatility'].mean().reindex(month_order).reset_index()
    fig_bar_month = px.bar(avg_vol_by_month, x='month', y='Volatility',
                           title='Volatilidad Promedio por Mes',
                           labels={'Volatility': 'Volatilidad Promedio', 'month': 'Mes'},
                           color='Volatility', color_continuous_scale=px.colors.sequential.Plasma)
    st.plotly_chart(fig_bar_month)

    avg_open_by_year = df_filtered_copy.groupby('year')['open'].mean().reset_index()
    fig_bar_open_year = px.bar(avg_open_by_year, x='year', y='open',
                               title='Precio de Apertura Promedio por Año',
                               labels={'open': 'Precio Promedio de Apertura', 'year': 'Año'},
                               color='open', color_continuous_scale=px.colors.sequential.Greens)
    st.plotly_chart(fig_bar_open_year)

    st.write("---")
    st.subheader("Gráficos de Barras Horizontales")

    top_5_vol_months = df_filtered_copy.groupby('month')['Volatility'].mean().nlargest(5).reset_index()
    fig_bar_h_vol = px.bar(top_5_vol_months, x='Volatility', y='month', orientation='h',
                           title='Top 5 Meses con Mayor Volatilidad Promedio',
                           labels={'Volatility': 'Volatilidad Promedio', 'month': 'Mes'},
                           color='Volatility', color_continuous_scale=px.colors.sequential.Burg)
    fig_bar_h_vol.update_yaxes(categoryorder='total ascending')
    st.plotly_chart(fig_bar_h_vol)

    last_return_by_year = df_filtered_copy.groupby('year')['Cumulative Return'].last().nlargest(5).reset_index()
    fig_bar_h_return = px.bar(last_return_by_year, x='Cumulative Return', y='year', orientation='h',
                              title='Top 5 Años con Mayor Retorno Acumulado',
                              labels={'Cumulative Return': 'Retorno Acumulado', 'year': 'Año'},
                              color='Cumulative Return', color_continuous_scale=px.colors.sequential.Blues)
    fig_bar_h_return.update_yaxes(categoryorder='total ascending')
    st.plotly_chart(fig_bar_h_return)

# Pestaña 6: Composición
with tab_composition:
    st.header("Composición y Proporciones")

    df_filtered_copy['Price Change Direction'] = df_filtered_copy['Price Change %'].apply(lambda x: 'Positivo' if x >= 0 else 'Negativo')
    price_change_counts = df_filtered_copy['Price Change Direction'].value_counts().reset_index()
    price_change_counts.columns = ['Direction', 'Count']
    fig_pie_direction = px.pie(price_change_counts, values='Count', names='Direction',
                               title='Proporción de Días con Cambio de Precio Positivo/Negativo',
                               color='Direction',
                               color_discrete_map={'Positivo':'lightgreen', 'Negativo':'salmon'},
                               hole=0.3)
    st.plotly_chart(fig_pie_direction)

    df_filtered_copy['Price Change Quartile'] = pd.qcut(df_filtered_copy['Price Change %'], q=4, labels=['Q1 (Muy Negativo)', 'Q2 (Negativo)', 'Q3 (Positivo)', 'Q4 (Muy Positivo)'], duplicates='drop')
    quartile_counts = df_filtered_copy['Price Change Quartile'].value_counts().reset_index()
    quartile_counts.columns = ['Quartile', 'Count']
    fig_pie_quartile = px.pie(quartile_counts, values='Count', names='Quartile',
                              title='Distribución de Días por Cuartil de Variación de Precio',
                              color='Quartile',
                              color_discrete_map={'Q1 (Muy Negativo)':'darkred', 'Q2 (Negativo)':'lightcoral',
                                                  'Q3 (Positivo)':'lightgreen', 'Q4 (Muy Positivo)':'darkgreen'},
                              hole=0.4)
    st.plotly_chart(fig_pie_quartile)