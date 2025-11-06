import streamlit as st
import pandas as pd
import datetime as dt
import json
import plotly.express as px
import plotly.graph_objects as go

# ---------------------------
# --- Dashboard Konfiguration
# ---------------------------
st.set_page_config(page_title="⚡ aWATTar Dashboard", layout="wide")
st.title("⚡ aWATTar Strompreis Dashboard – Tarifvergleich")

DATA_FILE = "strompreise_2024_2025.json"

# ---------------------------
# --- Daten laden & vorbereiten
# ---------------------------
@st.cache_data
def load_data(path):
    with open(path, "r") as f:
        data = json.load(f)["data"]
    df = pd.DataFrame(data)
    df["start_timestamp"] = pd.to_datetime(df["start_timestamp"], unit="ms")
    df["end_timestamp"] = pd.to_datetime(df["end_timestamp"], unit="ms")
    df["price_ct_kwh"] = df["marketprice"] / 10  # €/MWh → ct/kWh
    return df

try:
    df = load_data(DATA_FILE)
except FileNotFoundError:
    st.error(f"Datei '{DATA_FILE}' nicht gefunden. Bitte zuerst mit cURL herunterladen.")
    st.stop()

# ---------------------------
# --- Sidebar: Filter & Ansicht
# ---------------------------
st.sidebar.header("🧭 Einstellungen")

min_date = df["start_timestamp"].min().date()
max_date = df["start_timestamp"].max().date()

# Datumsfilter
date_range = st.sidebar.date_input(
    "Zeitraum wählen:",
    value=[min_date, max_date],
    min_value=min_date,
    max_value=max_date,
)

# Aggregationsmodus
agg_mode = st.sidebar.radio(
    "Ansicht:",
    ["Stündlich", "Täglich", "Monatlich"],
    index=1
)

# ---------------------------
# --- Stromtarife
# ---------------------------
st.sidebar.header("💡 Stromtarife")
tarif1_price = 40.0  # ct/kWh
tarif2_price = 30.0  # ct/kWh
tarif3_price = 12.5  # ct/kWh

st.sidebar.metric("Stromtarif 1 (Bestandskunden)", f"{tarif1_price:.2f} ct/kWh")
st.sidebar.metric("Stromtarif 2 (Neukunden)", f"{tarif2_price:.2f} ct/kWh")
st.sidebar.metric("Stromtarif 3 (Zieltarif)", f"{tarif3_price:.2f} ct/kWh")

# ---------------------------
# --- Daten filtern & aggregieren
# ---------------------------
start_date, end_date = date_range
filtered_df = df[
    (df["start_timestamp"].dt.date >= start_date)
    & (df["start_timestamp"].dt.date <= end_date)
].copy()

if agg_mode == "Täglich":
    filtered_df = (
        filtered_df.resample("D", on="start_timestamp")["price_ct_kwh"].mean().reset_index()
    )
elif agg_mode == "Monatlich":
    filtered_df = (
        filtered_df.resample("M", on="start_timestamp")["price_ct_kwh"].mean().reset_index()
    )

# ---------------------------
# --- Statistiken
# ---------------------------
st.sidebar.header("📊 Statistiken")
avg_price = filtered_df["price_ct_kwh"].mean()
min_price = filtered_df["price_ct_kwh"].min()
max_price = filtered_df["price_ct_kwh"].max()

st.sidebar.metric("Durchschnittspreis (ct/kWh)", f"{avg_price:.2f}")
st.sidebar.metric("Niedrigster Preis", f"{min_price:.2f}")
st.sidebar.metric("Höchster Preis", f"{max_price:.2f}")

# ---------------------------
# --- Tabs für Struktur
# ---------------------------
tab1, tab2, tab3 = st.tabs(["📈 Diagramm", "📆 Analyse", "📋 Tabelle"])

# ---------------------------
# --- Tab 1: Diagramm
# ---------------------------
with tab1:
    st.subheader(f"📈 Preisverlauf ({agg_mode}-Daten) mit Tarifvergleich")

    fig = go.Figure()

    # aWATTar Preislinie
    fig.add_trace(go.Scatter(
        x=filtered_df["start_timestamp"],
        y=filtered_df["price_ct_kwh"],
        mode="lines",
        name="aWATTar Preis",
        line=dict(color="#00CC96", width=2)
    ))

    # Tarif 1 – rote Linie
    fig.add_trace(go.Scatter(
        x=[filtered_df["start_timestamp"].min(), filtered_df["start_timestamp"].max()],
        y=[tarif1_price, tarif1_price],
        mode="lines",
        name=f"Stromtarif 1 ({tarif1_price:.2f} ct/kWh)",
        line=dict(color="red", width=2, dash="dash")
    ))

    # Tarif 2 – gelbe Linie
    fig.add_trace(go.Scatter(
        x=[filtered_df["start_timestamp"].min(), filtered_df["start_timestamp"].max()],
        y=[tarif2_price, tarif2_price],
        mode="lines",
        name=f"Stromtarif 2 ({tarif2_price:.2f} ct/kWh)",
        line=dict(color="gold", width=2, dash="dot")
    ))

    # Tarif 3 – blaue Linie
    fig.add_trace(go.Scatter(
        x=[filtered_df["start_timestamp"].min(), filtered_df["start_timestamp"].max()],
        y=[tarif3_price, tarif3_price],
        mode="lines",
        name=f"Stromtarif 3 ({tarif3_price:.2f} ct/kWh)",
        line=dict(color="blue", width=2, dash="dot")
    ))

    fig.update_layout(
        title="aWATTar Strompreise im Vergleich zu festen Stromtarifen",
        xaxis_title="Zeit",
        yaxis_title="Preis (ct/kWh)",
        legend=dict(yanchor="top", y=1.05, xanchor="left", x=0),
        xaxis_rangeslider_visible=True,
    )

    st.plotly_chart(fig, use_container_width=True)

# ---------------------------
# --- Tab 2: Analyse
# ---------------------------
with tab2:
    st.subheader("📆 Preis-Muster nach Tageszeit und Wochentag")

    df["hour"] = df["start_timestamp"].dt.hour
    df["weekday"] = df["start_timestamp"].dt.day_name()

    avg_by_hour = df.groupby("hour")["price_ct_kwh"].mean().reset_index()
    avg_by_day = df.groupby("weekday")["price_ct_kwh"].mean().reindex(
        ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    ).reset_index()

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("**⏰ Durchschnittlicher Preis pro Stunde (über gesamten Zeitraum)**")
        fig_hour = px.bar(
            avg_by_hour, x="hour", y="price_ct_kwh", color="price_ct_kwh",
            color_continuous_scale="Viridis", labels={"price_ct_kwh": "ct/kWh"}
        )
        st.plotly_chart(fig_hour, use_container_width=True)

    with col2:
        st.markdown("**📅 Durchschnittlicher Preis pro Wochentag**")
        fig_day = px.bar(
            avg_by_day, x="weekday", y="price_ct_kwh", color="price_ct_kwh",
            color_continuous_scale="Viridis", labels={"price_ct_kwh": "ct/kWh"}
        )
        st.plotly_chart(fig_day, use_container_width=True)

# ---------------------------
# --- Tab 3: Datentabelle
# ---------------------------
with tab3:
    st.subheader("📋 Rohdaten (gefiltert)")
    st.dataframe(
        filtered_df.rename(columns={
            "start_timestamp": "Zeitpunkt",
            "price_ct_kwh": "Preis (ct/kWh)"
        })
    )

    csv = filtered_df.to_csv(index=False).encode("utf-8")
    st.download_button(
        label="📥 Daten als CSV herunterladen",
        data=csv,
        file_name=f"awattar_{agg_mode.lower()}_{start_date}_{end_date}.csv",
        mime="text/csv"
    )
