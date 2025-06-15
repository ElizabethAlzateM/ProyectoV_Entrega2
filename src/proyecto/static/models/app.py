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

# Obtenemos la ruta absoluta del directorio donde se encuentra este script (app.py)
script_dir = os.path.dirname(os.path.abspath(__file__))

# Si app.py está en 'src/proyecto/static/models/'
# y enriched_historical.db está en 'src/proyecto/static/data/'
# entonces para ir de 'models' a 'data', subimos un nivel (..) y luego bajamos a 'data'.
data_dir_abs = os.path.abspath(os.path.join(script_dir, '..', 'data'))

# Definimos la ruta completa para la base de datos enriquecida
enriched_db_path = os.path.join(data_dir_abs, db_path)


# Descargamos la base de datos desde GitHub si no existe
if not os.path.exists(enriched_db_path):
    st.info("🔄 Descargando la base de datos desde GitHub... Esto puede tardar unos segundos.")
    try:
        url = "https://raw.githubusercontent.com/jimymora25/Tarea_2_Proyecto_Integrado_V/main/src/proyecto/static/data/enriched_historical.db"
        response = requests.get(url, stream=True) # Usamos stream=True para descargas más eficientes
        response.raise_for_status() # Lanza un HTTPError si la respuesta no es 200 (OK)

        os.makedirs(data_dir_abs, exist_ok=True) # Crea el directorio si no existe

        with open(enriched_db_path, "wb") as f:
            for chunk in response.iter_content(chunk_size=8192): # Descarga en chunks
                f.write(chunk)
        st.success("✅ Base de datos descargada correctamente.")
    except requests.exceptions.RequestException as e:
        st.error(f"❌ Error de red al descargar la base de datos: {e}. Verifica la URL o la conexión.")
        st.stop()
    except Exception as e:
        st.error(f"❌ Error inesperado al descargar la base de datos: {e}.")
        st.stop()

if not os.path.exists(enriched_db_path):
    st.error("❌ Error: No se pudo encontrar la base de datos después de intentar descargarla. La aplicación no puede continuar.")
    st.stop()


@st.cache_data
def load_data(path, file_mod_time): # Añadimos file_mod_time como argumento para "romper" la caché
    """
    Carga los datos desde la base de datos SQLite y convierte la columna 'date' a datetime.
    El argumento file_mod_time se usa para forzar la recarga cuando el archivo cambie.
    """
    conn = sqlite3.connect(path)
    df = pd.read_sql_query("SELECT * FROM enriched_historical", conn)
    conn.close()
    df["date"] = pd.to_datetime(df["date"])
    return df

# Obtenemos la última fecha de modificación del archivo para usarla en la caché
# Esto fuerza a Streamlit a recargar los datos si el archivo .db cambia.
try:
    # Obtener el timestamp de la última modificación del archivo
    file_modification_time = os.path.getmtime(enriched_db_path)
except FileNotFoundError:
    # Si el archivo no existe (aún no ha sido descargado en la ejecución actual), usa 0
    file_modification_time = 0

df = load_data(enriched_db_path, file_modification_time)

# --- Cálculo de KPIs financieros ---

df["Price Change %"] = df["close"].pct_change() * 100
df["Moving Average 30"] = df["close"].rolling(window=30).mean()
df["Volatility"] = df["close"].rolling(window=30).std()
df["Cumulative Return"] = (1 + df["close"].pct_change().fillna(0)).cumprod()
df["Price Range"] = df["high"] - df["low"]

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
tab_overview, tab_metrics, tab_trends, tab_individual_kpis, tab_comparative_analysis, tab_distribution, tab_composition = st.tabs([
    "Resumen General",
    "Métricas Clave",
    "Tendencias Globales",
    "KPIs Individuales",
    "Análisis Comparativo",
    "Distribución y Relación",
    "Composición"
])

# Pestaña 1: Resumen General
with tab_overview:
    st.header("Resumen del Periodo Seleccionado")
    st.write("Aquí puedes encontrar un resumen de las métricas clave y una visión general de los datos.")

    st.subheader("Vista Previa de los Datos Filtrados")
    st.dataframe(df_filtered_copy.head())

    fig_close_price = px.line(df_filtered_copy, x="date", y="close", title="Precio de Cierre a lo largo del tiempo")
    st.plotly_chart(fig_close_price)


# Pestaña 2: Métricas Clave
with tab_metrics:
    st.header("Métricas Clave")
    col1, col2, col3 = st.columns(3)
    col4, col5, col6 = st.columns(3)

    with col1:
        st.metric("📈 Tasa de Variación (%)", f"{df_filtered_copy['Price Change %'].mean():.2f}%")
    with col2:
        st.metric("📉 Media Móvil (30 días)", f"{df_filtered_copy['Moving Average 30'].iloc[-1]:.2f}")
    with col3:
        st.metric("⚡ Volatilidad (STD Móvil 30 días)", f"{df_filtered_copy['Volatility'].iloc[-1]:.2f}%")
    with col4:
        st.metric("📊 Retorno Acumulado", f"{df_filtered_copy['Cumulative Return'].iloc[-1]:.2f}")
    with col5:
        st.metric("📏 Rango de Precio (Máximo - Mínimo)", f"{df_filtered_copy['Price Range'].mean():.2f}")
    with col6:
        st.metric("💲 Precio de Cierre Promedio", f"{df_filtered_copy['close'].mean():.2f}")


# Pestaña 3: Tendencias Globales
with tab_trends:
    st.header("Tendencias Globales de KPIs")

    st.plotly_chart(px.line(df_filtered_copy, x="date", y="Price Change %", title="Tasa de Variación (%) a lo largo del tiempo"))
    st.plotly_chart(px.line(df_filtered_copy, x="date", y="Moving Average 30", title="Media Móvil (30 días) del Precio de Cierre"))
    st.plotly_chart(px.line(df_filtered_copy, x="date", y="Volatility", title="Volatilidad (Desviación Estándar Móvil)"))
    st.plotly_chart(px.line(df_filtered_copy, x="date", y="Cumulative Return", title="Retorno Acumulado del Precio de Cierre"))


# Pestaña 4: KPIs Individuales
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


# Pestaña 5: Análisis Comparativo (Gráficos de barras)
with tab_comparative_analysis:
    st.header("Análisis Comparativo (Gráficos de Barras)")

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


# Pestaña 6: Distribución de Datos (Histogramas y gráficos de dispersión)
with tab_distribution:
    st.header("Distribución y Relación entre Variables")

    st.subheader("Histogramas de Distribución")
    fig_hist_change = px.histogram(df_filtered_copy, x="Price Change %", nbins=50,
                                   title="Distribución del Porcentaje de Cambio de Precio Diario",
                                   labels={"Price Change %": "Cambio de Precio (%)"},
                                   marginal="box",
                                   color_discrete_sequence=['purple'])
    st.plotly_chart(fig_hist_change)

    fig_hist_volume = px.histogram(df_filtered_copy, x="volume", nbins=50,
                                   title="Distribución del Volumen de Trading Diario",
                                   labels={"volume": "Volumen"},
                                   marginal="rug",
                                   color_discrete_sequence=['teal'])
    st.plotly_chart(fig_hist_volume)

    fig_hist_range = px.histogram(df_filtered_copy, x="Price Range", nbins=50,
                                   title="Distribución del Rango de Precio Diario (Máximo - Mínimo)",
                                   labels={"Price Range": "Rango de Precio"},
                                   marginal="violin",
                                   color_discrete_sequence=['darkblue'])
    st.plotly_chart(fig_hist_range)

    fig_hist_close = px.histogram(df_filtered_copy, x="close", nbins=50,
                                  title="Distribución del Precio de Cierre",
                                  labels={"close": "Precio de Cierre"},
                                  marginal="box",
                                  color_discrete_sequence=['orange'])
    st.plotly_chart(fig_hist_close)

    fig_hist_ma = px.histogram(df_filtered_copy, x="Moving Average 30", nbins=50,
                               title="Distribución de la Media Móvil (30 días)",
                               labels={"Moving Average 30": "Media Móvil"},
                               marginal="box",
                               color_discrete_sequence=['gray'])
    st.plotly_chart(fig_hist_ma)

    st.write("---")
    st.subheader("Relación entre Variables (Gráficos de Dispersión)")
    fig_scatter_close_volume = px.scatter(df_filtered_copy, x="volume", y="close",
                                          title="Precio de Cierre vs. Volumen de Trading",
                                          labels={"volume": "Volumen", "close": "Precio de Cierre"},
                                          trendline="ols",
                                          color="Price Change %",
                                          color_continuous_scale=px.colors.sequential.Sunset)
    st.plotly_chart(fig_scatter_close_volume)

    fig_scatter_vol_range = px.scatter(df_filtered_copy, x="Volatility", y="Price Range",
                                       title="Volatilidad vs. Rango de Precio Diario",
                                       labels={"Volatility": "Volatilidad", "Price Range": "Rango de Precio"},
                                       trendline="ols",
                                       color="year",
                                       color_continuous_scale=px.colors.sequential.Rainbow)
    st.plotly_chart(fig_scatter_vol_range)

    fig_scatter_close_ma = px.scatter(df_filtered_copy, x="date", y="close",
                                      title="Precio de Cierre vs. Media Móvil (30 días)",
                                      labels={"close": "Precio de Cierre", "date": "Fecha"},
                                      color_discrete_sequence=['blue'])
    fig_scatter_close_ma.add_scatter(x=df_filtered_copy["date"], y=df_filtered_copy["Moving Average 30"],
                                     mode='lines', name='Media Móvil 30', line=dict(color='red'))
    st.plotly_chart(fig_scatter_close_ma)


# Pestaña 7: Composición (Gráficos de torta)
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