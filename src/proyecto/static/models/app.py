import streamlit as st
import pandas as pd
import sqlite3
import plotly.express as px
import os
import requests

# --- Configuración de la base de datos y carga de datos ---

db_path = "enriched_historical.db"

if not os.path.exists(db_path):
    st.write("-------Descargando la base de datos desde GitHub-------")
    try:
        url = "https://raw.githubusercontent.com/jimymora25/Tarea_2_Proyecto_Integrado_V/main/src/proyecto/static/data/enriched_historical.db"
        response = requests.get(url)
        if response.status_code == 200:
            with open(db_path, "wb") as f:
                f.write(response.content)
            st.write("✅ Base de datos descargada correctamente.")
        else:
            st.error(f"❌ Error al descargar la base de datos: Código de estado {response.status_code}. Verifica la URL.")
            st.stop()
    except Exception as e:
        st.error(f"❌ Error al descargar la base de datos: {e}. Verifica la conexión a internet.")
        st.stop()

if not os.path.exists(db_path):
    st.error("❌ Error: No se pudo encontrar la base de datos después de intentar descargarla.")
    st.stop()
else:
    st.write("✅ Base de datos disponible.")

@st.cache_data
def load_data(path):
    conn = sqlite3.connect(path)
    df = pd.read_sql_query("SELECT * FROM enriched_historical", conn)
    conn.close()
    df["date"] = pd.to_datetime(df["date"])
    return df

df = load_data(db_path)

st.write("✅ Datos cargados correctamente")
st.dataframe(df.head())

# --- Cálculo de KPIs financieros ---

df["Price Change %"] = df["close"].pct_change() * 100
df["Moving Average 30"] = df["close"].rolling(window=30).mean()
df["Volatility"] = df["close"].rolling(window=30).std()
df["Cumulative Return"] = (1 + df["close"].pct_change().fillna(0)).cumprod()
df["Price Range"] = df["high"] - df["low"]
std_close = df["close"].std()

# --- Configuración del dashboard ---
st.write("✅ KPIs calculados correctamente!")
st.title("📊 Dashboard de KPIs Financieros")

st.sidebar.header("Filtros de Fecha")
start_date = st.sidebar.date_input("Fecha inicio", df["date"].min().date())
end_date = st.sidebar.date_input("Fecha fin", df["date"].max().date())
df_filtered = df[(df["date"] >= pd.to_datetime(start_date)) & (df["date"] <= pd.to_datetime(end_date))]

st.header("Métricas Clave")
col1, col2, col3 = st.columns(3)
col4, col5, col6 = st.columns(3)

if not df_filtered.empty:
    with col1:
        st.metric("📈 Tasa de Variación (%)", f"{df_filtered['Price Change %'].mean():.2f}%")
    with col2:
        st.metric("📉 Media Móvil (30 días)", f"{df_filtered['Moving Average 30'].iloc[-1]:.2f}")
    with col3:
        st.metric("⚡ Volatilidad (STD Móvil 30 días)", f"{df_filtered['Volatility'].iloc[-1]:.2f}")
    with col4:
        st.metric("📊 Retorno Acumulado", f"{df_filtered['Cumulative Return'].iloc[-1]:.2f}")
    with col5:
        st.metric("📏 Rango de Precio (Máximo - Mínimo)", f"{df_filtered['Price Range'].mean():.2f}")
else:
    st.warning("No hay datos para el rango de fechas seleccionado.")

st.header("Tendencias de KPIs")

if not df_filtered.empty:
    fig_change = px.line(df_filtered, x="date", y="Price Change %", title="Tasa de Variación (%) a lo largo del tiempo")
    st.plotly_chart(fig_change)

    fig_ma = px.line(df_filtered, x="date", y="Moving Average 30", title="Media Móvil (30 días) del Precio de Cierre")
    st.plotly_chart(fig_ma)

    fig_volatility = px.line(df_filtered, x="date", y="Volatility", title="Volatilidad (Desviación Estándar Móvil)")
    st.plotly_chart(fig_volatility)

    fig_return = px.line(df_filtered, x="date", y="Cumulative Return", title="Retorno Acumulado del Precio de Cierre")
    st.plotly_chart(fig_return)
else:
    st.info("No se pueden mostrar los gráficos ya que no hay datos en el rango de fechas seleccionado.")
