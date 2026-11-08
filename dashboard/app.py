import pandas as pd
import plotly.express as px
import streamlit as st
from sqlalchemy import create_engine

st.set_page_config(page_title="Uber India 2024 - Cancelaciones", layout="wide")

ORDEN_DIAS = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]
ORDEN_FRANJAS = ["Madrugada", "Mañana", "Tarde", "Noche"]
ORDEN_VTAT = ["0-5 min", "5-10 min", "10-15 min", "15-20 min", "20+ min", "Sin dato"]


@st.cache_resource
def get_engine():
    c = st.secrets["db"]
    url = f"postgresql+psycopg2://{c['user']}:{c['password']}@{c['host']}:{c['port']}/{c['dbname']}"
    return create_engine(url)


@st.cache_data(ttl=600)
def consulta(sql: str) -> pd.DataFrame:
    return pd.read_sql(sql, get_engine())


st.title("Diagnóstico de cancelaciones - Uber India 2024")

# ---------- KPIs ----------
k = consulta("SELECT * FROM vw_kpi_globales").iloc[0]
c1, c2, c3, c4, c5 = st.columns(5)
c1.metric("Reservas", f"{int(k.total_reservas):,}".replace(",", "."))
c2.metric("Éxito", f"{k.pct_exito}%")
c3.metric("Cancelación directa", f"{k.pct_canc_directa}%")
c4.metric("Cancela cliente", f"{k.pct_canc_cliente}%")
c5.metric("Cancela conductor", f"{k.pct_canc_conductor}%")

tab1, tab2, tab3 = st.tabs(["P1 Vehículo y línea", "P2 Tiempo de llegada", "P3 Horario, pago y causales"])

# ---------- P1 ----------
with tab1:
    df1 = consulta("SELECT * FROM vw_p1_cancelacion_vehiculo")
    lineas = st.multiselect("Línea de negocio", sorted(df1["business_line"].unique()),
                            default=sorted(df1["business_line"].unique()))
    df1 = df1[df1["business_line"].isin(lineas)].sort_values("tasa_cancelacion_pct", ascending=False)

    a, b = st.columns(2)
    a.plotly_chart(px.bar(df1, x="vehicle_type", y="tasa_cancelacion_pct", color="business_line",
                          title="Tasa de cancelación por tipo de vehículo (%)"),
                   use_container_width=True)
    b.plotly_chart(px.bar(df1.sort_values("perdida_estimada_inr", ascending=False),
                          x="vehicle_type", y="perdida_estimada_inr", color="business_line",
                          title="Pérdida estimada (INR)"),
                   use_container_width=True)
    st.dataframe(df1, use_container_width=True, hide_index=True)

# ---------- P2 ----------
with tab2:
    df2 = consulta("SELECT * FROM vw_p2_vtat_cancelacion")
    df2["rango_vtat"] = pd.Categorical(df2["rango_vtat"], categories=ORDEN_VTAT, ordered=True)
    df2 = df2.sort_values("rango_vtat")
    st.plotly_chart(px.bar(df2, x="rango_vtat", y="pct_canc_cliente",
                           category_orders={"rango_vtat": ORDEN_VTAT},
                           title="% de cancelación del cliente según tiempo de llegada del vehículo"),
                    use_container_width=True)
    st.dataframe(df2, use_container_width=True, hide_index=True)

# ---------- P3 ----------
with tab3:
    df3 = consulta("SELECT * FROM vw_p3_cancelacion_tiempo")
    df3["tasa_cancelacion_pct"] = (100 * df3["cancelaciones"] / df3["reservas"]).round(2)
    st.plotly_chart(px.density_heatmap(
        df3, x="dia_semana", y="franja_horaria", z="tasa_cancelacion_pct", histfunc="avg",
        category_orders={"dia_semana": ORDEN_DIAS, "franja_horaria": ORDEN_FRANJAS},
        title="Tasa de cancelación (%) por día y franja horaria"),
        use_container_width=True)

    a, b = st.columns(2)
    dfp = consulta("SELECT * FROM vw_p3_cancelacion_pago")
    dfp["tasa_cancelacion_pct"] = (100 * dfp["cancelaciones"] / dfp["reservas"]).round(2)
    a.plotly_chart(px.bar(dfp.sort_values("cancelaciones", ascending=False),
                          x="payment_method", y="cancelaciones",
                          title="Cancelaciones por método de pago"),
                   use_container_width=True)
    a.caption("Ojo: el método de pago viene vacío en los viajes cancelados del origen; "
              "se muestra tal como está en el DW.")

    dfc = consulta("SELECT * FROM vw_p3_causales").sort_values("casos", ascending=True)
    b.plotly_chart(px.bar(dfc, x="casos", y="cancellation_reason", color="cancelled_by",
                          orientation="h", title="Causales de cancelación"),
                   use_container_width=True)