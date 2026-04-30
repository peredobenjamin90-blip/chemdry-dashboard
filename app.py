import pandas as pd
import streamlit as st
from datetime import datetime, timedelta
import gspread
from google.oauth2.service_account import Credentials
from config import USUARIOS
import uuid
import plotly.express as px
import os

NOMBRE_APP = "CRM Dashboard"
ICONO_APP = "🧹"

st.set_page_config(
    page_title=NOMBRE_APP,
    page_icon=ICONO_APP,
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
<style>
    [data-testid="stSidebar"] { background-color: #2B5BAA; }
    [data-testid="stSidebar"] * { color: white !important; }
    [data-testid="stMetric"] {
        background: transparent !important;
        border-radius: 12px;
        padding: 16px;
        border-left: 4px solid #2B5BAA;
        border: 1px solid rgba(43, 91, 170, 0.3);
    }
    [data-testid="stMetricValue"] {
        font-size: clamp(14px, 2vw, 28px) !important;
    }
    h1 { color: #2B5BAA; }
    h2, h3 { color: #4a7fd4; }
    .stButton > button {
        background-color: #2B5BAA;
        color: white !important;
        border: none;
        border-radius: 8px;
        padding: 10px 24px;
        font-size: 16px;
        width: 100%;
    }
    .stButton > button:hover { background-color: #1a3d6e; }
</style>
""", unsafe_allow_html=True)

@st.cache_resource
def get_gspread_client():
    scopes = [
        "https://www.googleapis.com/auth/spreadsheets",  # ← quita el .readonly
        "https://www.googleapis.com/auth/drive"           # ← quita el .readonly
    ]
    creds = Credentials.from_service_account_info(
        dict(st.secrets["google_credentials"]),
        scopes=scopes
    )
    return gspread.authorize(creds)
import time

@st.cache_data(ttl=300)
def cargar_datos(sheet_ids):
    client = get_gspread_client()
    dfs = []

    columnas_base = [
        "Fecha", "Nombre", "Tel", "Dirección",
        "Origen", "Monto", "Servicio",
        "Comentarios con llamada posterior a venta"
    ]

    for año, sheet_id in sheet_ids.items():

        # 🔥 SI NO HAY SHEET → CREA DATA VACÍA
        if not sheet_id:
            df_vacio = pd.DataFrame(columns=columnas_base)
            df_vacio["Año"] = año
            dfs.append(df_vacio)
            continue

        for intento in range(3):
            try:
                sh = client.open_by_key(sheet_id)
                worksheet = sh.get_worksheet(0)
                data = worksheet.get_all_records()
                df = pd.DataFrame(data)

                if df.empty:
                    df = pd.DataFrame(columns=columnas_base)

                df["Año"] = año
                dfs.append(df)

                time.sleep(1)
                break

            except Exception as e:
                if intento < 2:
                    time.sleep(2)
                else:
                    # 🔥 SI FALLA → TAMBIÉN CREA VACÍO
                    df_vacio = pd.DataFrame(columns=columnas_base)
                    df_vacio["Año"] = año
                    dfs.append(df_vacio)

    if not dfs:
        return pd.DataFrame(columns=columnas_base + ["Año"])

    return pd.concat(dfs, ignore_index=True)


# 🔥 FUNCIÓN AGREGAR CLIENTES (igual pero mejorada leve)
def agregar_a_sheets(data):
    client = get_gspread_client()
    sheet_id = SHEET_IDS[data["Año"].iloc[0]]
    sh = client.open_by_key(sheet_id)
    worksheet = sh.get_worksheet(0)

    # 🔥 folio único
    folio = str(int(datetime.now().timestamp()))

    worksheet.append_row([
        folio,                      # Folio sistema
        "",                         # Folio interno
        data["Fecha"].iloc[0],      # Fecha
        data["Nombre"].iloc[0],     # Nombre
        data["Tel"].iloc[0],        # Tel
        "",                         # Dirección
        data["Origen"].iloc[0],     # Origen
        data["Monto"].iloc[0],      # Monto
        data["Servicio"].iloc[0],   # Servicio
        "",                         # Comentarios
        "", "", ""                  # 90 días, 6 meses, 1 año
    ])

# ── LOGIN ──
def login():
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown("<br><br>", unsafe_allow_html=True)

        st.markdown(
            "<h1 style='text-align:center; color:#2B5BAA; font-size:2.5rem;'>CRM</h1>",
            unsafe_allow_html=True
        )
        st.markdown(
            "<h3 style='text-align:center; color:#2B5BAA;'>Iniciar sesión</h3>",
            unsafe_allow_html=True
        )
        st.markdown("<br>", unsafe_allow_html=True)

        usuario_temp = st.text_input("Usuario", placeholder="Tu usuario")

        st.markdown("<br>", unsafe_allow_html=True)

        with st.form("login_form"):
            password = st.text_input(
                "Contraseña",
                type="password",
                placeholder="Tu contraseña"
            )
            submitted = st.form_submit_button(
                "Entrar",
                use_container_width=True
            )

            if submitted:
                if usuario_temp in USUARIOS and USUARIOS[usuario_temp]["password"] == password:
                    st.session_state["usuario"] = usuario_temp
                    st.session_state["empresa"] = USUARIOS[usuario_temp]["empresa"]
                    st.session_state["sistema"] = USUARIOS[usuario_temp]["sistema"]
                    st.session_state["SHEET_IDS"] = USUARIOS[usuario_temp]["sheets"]
                    st.rerun()
                else:
                    st.error("Usuario o contraseña incorrectos")


if "usuario" not in st.session_state:
    login()
    st.stop()
# Cargar config dinámica del usuario
app_config = USUARIOS[st.session_state["usuario"]].get("app", {})
NOMBRE_APP = app_config.get("nombre", "CRM Dashboard")

# ── CARGAR DATOS ──
@st.cache_data(ttl=300)
def cargar_datos(sheet_ids):
    try:
        client = get_gspread_client()
    except Exception as e:
        return pd.DataFrame(), [str(e)]

    dfs = []
    errores = []
    columnas_base = [
        "Fecha", "Nombre", "Tel", "Dirección",
        "Origen", "Monto", "Servicio",
        "Comentarios con llamada posterior a venta"
    ]

    for año, sheet_id in sheet_ids.items():
        if not sheet_id:
            continue
        for intento in range(3):
            try:
                sh = client.open_by_key(sheet_id)
                worksheet = sh.get_worksheet(0)
                data = worksheet.get_all_records()
                df = pd.DataFrame(data)
                if df.empty:
                    df = pd.DataFrame(columns=columnas_base)
                df["Año"] = año
                dfs.append(df)
                time.sleep(1)
                break
            except Exception as e:
                errores.append(f"Año {año} intento {intento}: {e}")
                if intento < 2:
                    time.sleep(2)

    if not dfs:
        return pd.DataFrame(columns=columnas_base + ["Año"]), errores
    return pd.concat(dfs, ignore_index=True), errores


# ── CARGAR DATOS ──
resultado = cargar_datos(st.session_state.get("SHEET_IDS", {}))
df = resultado[0]
errores_carga = resultado[1]

if errores_carga:
    for e in errores_carga:
        st.error(e)

st.caption(f"Filas cargadas: {len(df)}")

# ─────────────────────────────
# 🔥 FALLBACK (SI NO HAY DATOS)
# ─────────────────────────────
if df is None or df.empty:
    df = pd.DataFrame({
        "Nombre": [],
        "Tel": [],
        "Fecha": [],
        "Monto": [],
        "Servicio": [],
        "Origen": [],
        "Comentarios con llamada posterior a venta": [],
        "Año": []
    })
    st.warning("⚠️ No hay datos conectados aún.")

# ─────────────────────────────
# 🔥 LIMPIEZA SIEMPRE
# ─────────────────────────────
df.columns = df.columns.str.strip()
df["Fecha"] = pd.to_datetime(df["Fecha"], errors="coerce")

df["Monto"] = (
    df["Monto"]
    .astype(str)
    .str.replace("$", "", regex=False)
    .str.replace(",", "", regex=False)
    .str.strip()
)

df["Monto"] = pd.to_numeric(df["Monto"], errors="coerce")
df["Mes"] = df["Fecha"].dt.month

# ─────────────────────────────
# 🔥 AÑOS DINÁMICOS
# ─────────────────────────────
años_disponibles = sorted(df["Año"].dropna().unique())

if not años_disponibles:
    años_disponibles = [datetime.now().year]

años_sin_2026 = años_disponibles
# ── SIDEBAR ──
with st.sidebar:
    logo_path = USUARIOS[st.session_state["usuario"]].get("app", {}).get("logo")
    if logo_path:
        try:
            logo_path_full = os.path.join(os.path.dirname(os.path.abspath(__file__)), logo_path)
            st.image(logo_path_full, width=120)
        except Exception as e:
            pass

    st.markdown(f"<h3 style='color:white'>{st.session_state['empresa']}</h3>", unsafe_allow_html=True)
    st.markdown("---")

    paginas = ["Resumen", "Ventas", "Clientes", "Servicios", "Follow Up", "Agenda", "Cotizaciones", "Chat"]

    if "pagina" not in st.session_state:
        st.session_state["pagina"] = "Resumen"

    for p in paginas:
        if st.button(p, key=f"sidebar_{p}", use_container_width=True):
            st.session_state["pagina"] = p

    st.markdown("---")
    st.caption("Datos actualizados cada 5 min")

    if st.button("Actualizar datos", key="sidebar_actualizar", use_container_width=True):
        st.cache_data.clear()
        st.rerun()

    st.markdown("---")

    if st.button("Cerrar sesión", key="sidebar_logout", use_container_width=True):
        for key in list(st.session_state.keys()):
            del st.session_state[key]
        st.rerun()


    # ── RESUMEN ──
    # 🔥 IMPORTANTE: ESTO VA FUERA DEL SIDEBAR
pagina = st.session_state["pagina"]
def limpiar_numero(valor):
    if pd.isna(valor):
        return 0

    valor = str(valor)
    valor = valor.replace("$", "")
    valor = valor.replace(",", "")
    valor = valor.replace(" ", "")

    if valor == "-" or valor == "":
        return 0

    try:
        return float(valor)
    except:
        return 0

def cargar_finanzas(url):
    try:
        df = pd.read_csv(url, header=None)
    except Exception as e:
        st.error(f"Error descargando CSV: {e}")
        return None, None, None

    def sumar_columna_desde_fila(keyword, col_idx, filas_max=50):
        # Encontrar fila del keyword
        fila_inicio = None
        for i, row in df.iterrows():
            if str(row.iloc[0]).strip() == keyword:
                fila_inicio = i
                break
        if fila_inicio is None:
            return 0

        # Buscar fila del siguiente keyword para saber dónde parar
        fila_fin = fila_inicio + filas_max

        total = 0
        for i in range(fila_inicio, min(fila_fin, len(df))):
            try:
                val = df.iloc[i, col_idx]
                limpio = str(val).replace("$", "").replace(",", "").replace("`", "").strip()
                num = float(limpio)
                if num > 0:
                    total += num
            except:
                continue
        return total

    # Detectar si es estructura semanal (columna 42 = Total Mes)
    es_semanal = df.iloc[8, 42] == "Total Mes" if len(df.columns) > 42 else False

    if es_semanal:
        # Sumar columna 42 entre ENTRADAS y SALIDAS
        ingresos = sumar_columna_desde_fila("ENTRADAS", 42, filas_max=15)
        gastos = sumar_columna_desde_fila("SALIDAS", 42, filas_max=15)
    else:
        # Estructura mensual normal — buscar max en fila de Total Entradas/Salidas
        def buscar_total(keyword):
            filas = df[df.astype(str).apply(
                lambda row: row.str.contains(keyword, case=False, na=False).any(),
                axis=1
            )]
            if filas.empty:
                return 0
            fila = filas.iloc[0]
            valores = []
            for v in fila:
                try:
                    limpio = str(v).replace("$", "").replace(",", "").replace("`", "").strip()
                    num = float(limpio)
                    if num > 0:
                        valores.append(num)
                except:
                    continue
            return max(valores) if valores else 0

        ingresos = buscar_total("Total Entradas")
        gastos = buscar_total("Total Salidas")

    utilidad = ingresos - gastos
    return ingresos, gastos, utilidad
# ── RESUMEN ──
if pagina == "Resumen":
    st.title(NOMBRE_APP)

    año_resumen = st.selectbox(
        "Año:",
        años_sin_2026,
        index=len(años_sin_2026)-1
    )

    df_r = df[df["Año"] == año_resumen]

    total_ventas = df_r["Monto"].sum()
    total_clientes = df_r["Nombre"].nunique()
    ticket_promedio = df_r["Monto"].mean()
    total_servicios = len(df_r)

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Ventas totales", f"${total_ventas:,.0f}")
    col2.metric("Clientes únicos", f"{total_clientes:,}")
    col3.metric("Ticket promedio", f"${ticket_promedio:,.0f}")
    col4.metric("Servicios realizados", f"{total_servicios:,}")

    # 📊 Comparación anual
    if año_resumen > min(años_sin_2026):
        df_ant = df[df["Año"] == año_resumen - 1]
        ventas_ant = df_ant["Monto"].sum()
        diferencia = total_ventas - ventas_ant
        porcentaje = (diferencia / ventas_ant * 100) if ventas_ant > 0 else 0
        color = "green" if diferencia > 0 else "red"
        simbolo = "▲" if diferencia > 0 else "▼"

        st.markdown(
            f"<p style='color:{color}; font-size:16px'>{simbolo} Comparado con {año_resumen-1}: ${abs(diferencia):,.0f} ({porcentaje:+.1f}%)</p>",
            unsafe_allow_html=True
        )

    # 💰 FLUJO DE EFECTIVO
    st.markdown("## 💰 Flujo de efectivo")

    finanzas_usuario = USUARIOS[st.session_state["usuario"]].get("finanzas", {})

    if finanzas_usuario:

        años_finanzas = list(finanzas_usuario.keys())

        año_finanzas = st.selectbox(
            "Año financiero",
            años_finanzas,
            index=len(años_finanzas)-1
        )

        try:
            ingresos, gastos, utilidad = cargar_finanzas(finanzas_usuario[año_finanzas])

            if ingresos is not None:

                col1, col2, col3 = st.columns(3)
                col1.metric("💰 Ingresos", f"${ingresos:,.0f}")
                col2.metric("💸 Gastos", f"${gastos:,.0f}")
                col3.metric("🟢 Utilidad", f"${utilidad:,.0f}")

            else:
                st.warning("No se pudieron leer los datos del sheet")

        except Exception as e:
            st.error("Error cargando finanzas")
            st.write(e)
    # ── VENTAS ──
elif pagina == "Ventas":
    st.title("Análisis de Ventas")

    ventas_año = df[df["Año"].isin(años_sin_2026)].groupby("Año")["Monto"].sum().reset_index()
    ventas_año.columns = ["Año", "Total"]
    st.subheader("Ventas totales por año")
    st.bar_chart(ventas_año.set_index("Año"))

    st.subheader("Comparación mensual")
    años_sel = st.multiselect("Años:", años_sin_2026, default=años_sin_2026[-2:])
    if años_sel:
        import plotly.express as px

        df_f = df[df["Año"].isin(años_sel)]
        pivot = df_f.groupby(["Año","Mes"])["Monto"].sum().reset_index()
        pivot = pivot.pivot(index="Mes", columns="Año", values="Monto").fillna(0)
        pivot = pivot.sort_index()

        nombres_meses = {1:"Ene",2:"Feb",3:"Mar",4:"Abr",5:"May",6:"Jun",
                         7:"Jul",8:"Ago",9:"Sep",10:"Oct",11:"Nov",12:"Dic"}
        pivot.index = pivot.index.map(nombres_meses)

        pivot_reset = pivot.reset_index()
        pivot_reset.columns.name = None

        fig = px.line(
            pivot_reset,
            x="Mes",
            y=[col for col in pivot_reset.columns if col != "Mes"],
            labels={"value": "Ventas", "variable": "Año"},
            category_orders={"Mes": ["Ene","Feb","Mar","Abr","May","Jun","Jul","Ago","Sep","Oct","Nov","Dic"]}
        )
        st.plotly_chart(fig, use_container_width=True)

        st.subheader("Proyección 2026")
        mes_actual = datetime.now().month
        meses_con_datos_2026 = df[(df["Año"]==2026) & (df["Monto"]>0)]["Mes"].nunique()
        ventas_2026_acum = df[df["Año"]==2026]["Monto"].sum() if 2026 in df["Año"].values else 0
        ventas_2025_mismos_meses = df[(df["Año"]==2025) & (df["Mes"] <= mes_actual)]["Monto"].sum()
        ventas_2025_total = df[df["Año"]==2025]["Monto"].sum()

        if ventas_2025_mismos_meses > 0 and ventas_2026_acum > 0:
            factor_crecimiento = ventas_2026_acum / ventas_2025_mismos_meses
            proyeccion = ventas_2025_total * factor_crecimiento
            tendencia = ((factor_crecimiento - 1) * 100)
            color = "green" if factor_crecimiento >= 1 else "red"
        else:
            proyeccion = ventas_2025_total
            tendencia = 0
            color = "gray"

        col1, col2, col3 = st.columns(3)
        col1.metric("Proyección anual 2026", f"${proyeccion:,.0f}")
        col2.metric("Ventas reales 2026", f"${ventas_2026_acum:,.0f}")
        col3.metric("Tendencia vs 2025", f"{tendencia:+.1f}%")
        st.markdown(f"<p style='color:{color}'>Basado en {meses_con_datos_2026} mes(es) de datos reales de 2026</p>", unsafe_allow_html=True)

        st.subheader("Detalle mes a mes — 2026 vs 2025")
        nombres_meses_completos = {1:"Enero",2:"Febrero",3:"Marzo",4:"Abril",5:"Mayo",6:"Junio",
                                   7:"Julio",8:"Agosto",9:"Septiembre",10:"Octubre",11:"Noviembre",12:"Diciembre"}
        resumen_meses = []
        for m in range(1, mes_actual + 1):
            v2025 = df[(df["Año"]==2025) & (df["Mes"]==m)]["Monto"].sum()
            v2026 = df[(df["Año"]==2026) & (df["Mes"]==m)]["Monto"].sum() if 2026 in df["Año"].values else 0
            diff = v2026 - v2025
            pct = ((diff / v2025) * 100) if v2025 > 0 else 0
            resumen_meses.append({
                "Mes": nombres_meses_completos[m],
                "2025": f"${v2025:,.0f}",
                "2026": f"${v2026:,.0f}",
                "Diferencia": f"${diff:,.0f}",
                "Variación": f"{pct:+.1f}%"
            })
        st.dataframe(pd.DataFrame(resumen_meses), use_container_width=True, hide_index=True)
        # CLIENTES
elif pagina == "Clientes":
    st.title("Origen de Clientes")

    año_origen = st.selectbox("Año:", años_sin_2026)
    df_o = df[df["Año"] == año_origen].copy()

    # 🔥 LIMPIEZA
    df_o["Origen"] = (
        df_o["Origen"]
        .astype(str)
        .str.strip()
        .str.lower()
    )

    # 🔥 NORMALIZAR — desde config
    origenes_config = USUARIOS[st.session_state["usuario"]].get("origenes", {})
    df_o["Origen"] = df_o["Origen"].replace(origenes_config)
    df_o["Origen"] = df_o["Origen"].replace(["", "nan"], "Sin especificar")

    # 🔥 GRÁFICA
    origen = df_o["Origen"].value_counts().reset_index()
    origen.columns = ["Canal", "Clientes"]

    st.bar_chart(origen.set_index("Canal"))
    st.dataframe(origen, use_container_width=True)

    # 🧠 HISTORIAL
    st.markdown("### 🧠 Historial de clientes")

    df_hist = df.copy()
    df_hist["Monto"] = pd.to_numeric(df_hist["Monto"], errors="coerce")
    df_hist["Fecha"] = pd.to_datetime(df_hist["Fecha"], errors="coerce")

    historial = df_hist.groupby("Nombre").agg(
        Total_Gastado=("Monto", "sum"),
        Servicios=("Monto", "count"),
        Ultima_Visita=("Fecha", "max"),
        Ticket_Promedio=("Monto", "mean")
    ).reset_index()

    historial = historial.sort_values(by="Total_Gastado", ascending=False)

    cliente_buscar = st.text_input("🔍 Buscar cliente", key=f"buscador_historial_{año_origen}")

    if cliente_buscar:
        historial = historial[
            historial["Nombre"].str.contains(cliente_buscar, case=False, na=False)
        ]

    historial["Ultima_Visita"] = historial["Ultima_Visita"].dt.strftime("%d/%m/%Y")

    st.markdown("### 🏆 Top clientes")
    top_clientes = historial.head(10)

    col1, col2 = st.columns(2)
    with col1:
        st.metric("💰 Mejor cliente", top_clientes.iloc[0]["Nombre"] if not top_clientes.empty else "-")
    with col2:
        st.metric(
            "💵 Mayor gasto",
            f"${top_clientes.iloc[0]['Total_Gastado']:,.0f}" if not top_clientes.empty else "$0"
        )

    st.dataframe(historial, use_container_width=True)

    # 👤 PERFIL
    st.markdown("### 👤 Perfil del cliente")

    clientes_lista = historial["Nombre"].dropna().unique().tolist()
    cliente_sel = st.selectbox("Selecciona un cliente", clientes_lista)

    if cliente_sel:
        df_cliente = df[df["Nombre"] == cliente_sel].copy()
        df_cliente["Fecha"] = pd.to_datetime(df_cliente["Fecha"], errors="coerce")
        df_cliente["Monto"] = pd.to_numeric(df_cliente["Monto"], errors="coerce")
        df_cliente = df_cliente.sort_values(by="Fecha", ascending=False)

        total = df_cliente["Monto"].sum()
        visitas = len(df_cliente)
        ultima = df_cliente["Fecha"].max()
        promedio = df_cliente["Monto"].mean()

        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Total gastado", f"${total:,.0f}")
        col2.metric("Servicios", visitas)
        col3.metric("Última visita", ultima.strftime("%d/%m/%Y") if pd.notnull(ultima) else "-")
        col4.metric("Ticket promedio", f"${promedio:,.0f}")

        st.markdown("### 📋 Historial completo")
        mostrar = df_cliente[[
            "Fecha", "Servicio", "Monto", "Origen",
            "Comentarios con llamada posterior a venta"
        ]].copy()
        mostrar.columns = ["Fecha", "Servicio", "Monto", "Origen", "Comentarios"]
        st.dataframe(mostrar, use_container_width=True)

    # 🔴 CLIENTES PERDIDOS
    st.markdown("## 🔴 Oportunidades de recuperación")

    df_lost = df.copy()
    df_lost["Fecha"] = pd.to_datetime(df_lost["Fecha"], errors="coerce")
    df_lost["Monto"] = pd.to_numeric(df_lost["Monto"], errors="coerce")

    hoy = datetime.now()

    ultimo = df_lost.groupby("Nombre").agg(
        Ultima_Visita=("Fecha", "max"),
        Total_Gastado=("Monto", "sum"),
        Tel=("Tel", "last")
    ).reset_index()

    ultimo["Meses_sin_servicio"] = ((hoy - ultimo["Ultima_Visita"]).dt.days / 30).round(1)

    col1, col2 = st.columns(2)
    with col1:
        meses_min = st.slider("Meses sin servicio", 3, 24, 6)
    with col2:
        monto_min = st.number_input("Monto mínimo ($)", value=1500)

    perdidos = ultimo[
        (ultimo["Meses_sin_servicio"] >= meses_min) &
        (ultimo["Total_Gastado"] >= monto_min)
    ]
    perdidos = perdidos.sort_values(by="Total_Gastado", ascending=False)

    col1, col2, col3 = st.columns(3)
    col1.metric("Clientes recuperables", len(perdidos))
    col2.metric("Dinero en riesgo", f"${perdidos['Total_Gastado'].sum():,.0f}")
    col3.metric(
        "Meses promedio sin servicio",
        f"{perdidos['Meses_sin_servicio'].mean():.1f}" if not perdidos.empty else "0"
    )

    st.markdown("### 📋 Lista priorizada")
    st.dataframe(
        perdidos[["Nombre", "Tel", "Total_Gastado", "Meses_sin_servicio"]],
        use_container_width=True
    )

    # 🚀 CONTACTO MASIVO
    st.markdown("## 🚀 Contacto masivo")

    if not perdidos.empty:
        plantillas = USUARIOS[st.session_state["usuario"]].get("plantillas", {})
        empresa = st.session_state.get("empresa", "")

        if plantillas:
            plantilla_sel = st.selectbox(
                "Selecciona plantilla para todos",
                list(plantillas.keys()),
                key="plantilla_masiva"
            )
            mensaje_base = plantillas[plantilla_sel]
        else:
            mensaje_base = "Hola {nombre}, te contactamos de {empresa}"

        if st.button("💬 Generar mensajes para todos"):
            cols = st.columns(3)
            i = 0
            for _, row in perdidos.iterrows():
                tel = str(row["Tel"]).replace("-", "").replace(" ", "")
                if tel:
                    tel = "52" + tel
                    mensaje = mensaje_base.format(nombre=row["Nombre"], empresa=empresa)
                    url = f"https://wa.me/{tel}?text={mensaje.replace(' ', '%20')}"
                    with cols[i % 3]:
                        st.link_button(f"💬 {row['Nombre']}", url)
                    i += 1

    # 💬 CONTACTO INDIVIDUAL
    st.markdown("### 💬 Contacto rápido")

    if not perdidos.empty:
        cliente_sel_contacto = st.selectbox(
            "Selecciona cliente",
            perdidos["Nombre"],
            key="select_contacto"
        )

        cliente_data = perdidos[perdidos["Nombre"] == cliente_sel_contacto].iloc[0]
        tel = str(cliente_data["Tel"]).replace("-", "").replace(" ", "")
        if tel:
            tel = "52" + tel

        PLANTILLAS_MENSAJES = {
            "Recordatorio": "Hola {nombre}, te contactamos de {empresa}. Hace tiempo no realizas un servicio con nosotros. ¿Te gustaría agendar?",
            "Promoción": "Hola {nombre}, en {empresa} tenemos una promoción especial. ¿Te interesa?",
            "Seguimiento": "Hola {nombre}, te damos seguimiento desde {empresa}. ¿Cómo fue tu servicio?",
            "Reactivación": "Hola {nombre}, te extrañamos en {empresa} 😄 ¿Agendamos esta semana?"
        }

        plantilla_sel = st.selectbox("Plantilla", list(PLANTILLAS_MENSAJES.keys()))
        mensaje = PLANTILLAS_MENSAJES[plantilla_sel].format(
            nombre=cliente_sel_contacto,
            empresa=st.session_state.get("empresa", "tu negocio")
        )
        mensaje_edit = st.text_area("Mensaje", value=mensaje)

        if tel:
            url = f"https://wa.me/{tel}?text={mensaje_edit.replace(' ', '%20')}"
            st.markdown(f"[💬 Abrir WhatsApp]({url})")
        else:
            st.warning("Este cliente no tiene teléfono válido")
        # ── SERVICIOS ──
elif pagina == "Servicios":
    st.title("Servicios más vendidos")
    año_serv = st.selectbox("Año:", años_sin_2026)
    df_s = df[df["Año"] == año_serv].copy()

    df_s = df_s[df_s["Servicio"].notna()]
    df_s = df_s[df_s["Servicio"].astype(str).str.strip() != ""]

    categorias_config = USUARIOS[st.session_state["usuario"]].get("categorias", {})

    filas_expandidas = []
    for _, row in df_s.iterrows():
        s = str(row["Servicio"]).lower()
        encontradas = set()
        for categoria, keywords in categorias_config.items():
            for kw in keywords:
                if kw in s:
                    encontradas.add(categoria)
        if not encontradas:
            encontradas.add("Otro")
        for cat in encontradas:
            filas_expandidas.append(cat)

    import collections
    conteo = collections.Counter(filas_expandidas)
    cats = pd.DataFrame(conteo.items(), columns=["Categoria", "Cantidad"])
    cats = cats.sort_values("Cantidad", ascending=False)

    fig = px.pie(
        cats,
        names="Categoria",
        values="Cantidad",
        title="Servicios más vendidos",
        hole=0.3
    )
    fig.update_traces(textposition="inside", textinfo="percent+label")
    st.plotly_chart(fig, use_container_width=True)
    st.dataframe(cats, use_container_width=True)

    # ── FOLLOW UP ──
elif pagina == "Follow Up":
    st.title("Clientes para Follow Up")

    ultimo = df.groupby("Nombre").agg(Fecha=("Fecha","max")).reset_index()
    ultimo.columns = ["Nombre", "Ultimo servicio"]

    tels = df[["Nombre","Tel"]].drop_duplicates(subset="Nombre")

    comentarios = df.sort_values("Fecha").drop_duplicates(subset="Nombre", keep="last")[
        ["Nombre","Comentarios con llamada posterior a venta"]
    ]

    ultimo = ultimo.merge(tels, on="Nombre", how="left")
    ultimo = ultimo.merge(comentarios, on="Nombre", how="left")

    ultimo.columns = ["Nombre", "Ultimo servicio", "Tel", "Comentario"]

    col1, col2 = st.columns(2)

    with col1:
        meses = st.slider("Sin servicio hace más de X meses:", 1, 24, 6)

    with col2:
        mes_filtro = st.selectbox(
            "Mes del último servicio:",
            ["Todos","Enero","Febrero","Marzo","Abril","Mayo","Junio",
             "Julio","Agosto","Septiembre","Octubre","Noviembre","Diciembre"]
        )

    fecha_limite = datetime.now() - timedelta(days=meses * 30)
    sin_servicio = ultimo[ultimo["Ultimo servicio"] < fecha_limite].copy()

    meses_dict = {
        "Enero":1,"Febrero":2,"Marzo":3,"Abril":4,"Mayo":5,"Junio":6,
        "Julio":7,"Agosto":8,"Septiembre":9,"Octubre":10,"Noviembre":11,"Diciembre":12
    }

    if mes_filtro != "Todos":
        sin_servicio = sin_servicio[
            sin_servicio["Ultimo servicio"].dt.month == meses_dict[mes_filtro]
        ]

    sin_servicio = sin_servicio.sort_values("Ultimo servicio")

    st.metric("Clientes a contactar", len(sin_servicio))
    st.dataframe(sin_servicio, use_container_width=True)

    import urllib.parse

    st.markdown("### 💬 Enviar mensaje por WhatsApp")

    if not sin_servicio.empty:

        cliente_sel = st.selectbox(
            "Selecciona cliente:",
            sin_servicio.apply(lambda x: f"{x['Nombre']} - {x['Tel']}", axis=1)
        )

        nombre = cliente_sel.split(" - ")[0]
        telefono = cliente_sel.split(" - ")[1].replace("-", "").replace(" ", "")

        # 🔥 PLANTILLAS DINÁMICAS
        PLANTILLAS_MENSAJES = {
            "Seguimiento": "Hola {nombre}, te contactamos de {empresa}. Solo para dar seguimiento a tu último servicio. ¿Cómo fue tu experiencia?",
            "Recordatorio": "Hola {nombre}, en {empresa} te recordamos que ya pasó tiempo desde tu último servicio. ¿Te gustaría agendar?",
            "Promoción": "Hola {nombre}, en {empresa} tenemos una promoción especial disponible. ¿Te interesa aprovecharla?",
            "Reactivación": "Hola {nombre}, te extrañamos en {empresa} 😄 Tenemos disponibilidad esta semana. ¿Agendamos?"
        }

        plantilla_sel = st.selectbox(
            "Selecciona plantilla",
            list(PLANTILLAS_MENSAJES.keys())
        )

        mensaje_base = PLANTILLAS_MENSAJES[plantilla_sel]

        mensaje_generado = mensaje_base.format(
            nombre=nombre,
            empresa=st.session_state.get("empresa", "nuestro negocio")
        )

        mensaje = st.text_area(
            "Mensaje",
            value=mensaje_generado
        )

        if telefono:
            telefono = "52" + telefono
            mensaje_encoded = urllib.parse.quote(mensaje)
            whatsapp_url = f"https://wa.me/{telefono}?text={mensaje_encoded}"

            st.link_button("Enviar mensaje por WhatsApp", whatsapp_url)
        else:
            st.warning("Cliente sin teléfono válido")
# CHATBOT
elif pagina == "Chat":
    st.title("🤖 Asistente del negocio")

    st.markdown("### 💡 Ejemplos de preguntas")
    st.markdown("""
    - ¿Cuánto vendí este mes?
    - ¿Cuánto vendí el mes pasado?
    - ¿Cuánto vendí en los últimos 3 meses?
    - ¿Cuánto vendí este año?
    - ¿Quién es mi mejor cliente?
    - ¿Qué clientes no han venido en 6 meses?
    - ¿Cuántos clientes tengo?
    """)

    pregunta = st.text_input("Haz una pregunta:")

    if pregunta:

        pregunta_lower = pregunta.lower()

        hoy = datetime.now()
        mes_actual = hoy.month
        año_actual = hoy.year

        # 💰 VENTAS ESTE MES
        if "este mes" in pregunta_lower:
            df_mes = df[
                (df["Mes"] == mes_actual) &
                (df["Año"] == año_actual)
            ]
            total = df_mes["Monto"].sum()
            st.success(f"Ventas este mes ({mes_actual}/{año_actual}): ${total:,.0f}")

        # 📅 MES PASADO
        elif "mes pasado" in pregunta_lower:
            if mes_actual == 1:
                mes = 12
                año = año_actual - 1
            else:
                mes = mes_actual - 1
                año = año_actual

            df_mes = df[
                (df["Mes"] == mes) &
                (df["Año"] == año)
            ]
            total = df_mes["Monto"].sum()
            st.success(f"Ventas mes pasado ({mes}/{año}): ${total:,.0f}")

        # 📊 ÚLTIMOS 3 MESES
        elif "3 meses" in pregunta_lower:
            fecha_limite = hoy - timedelta(days=90)

            df_3m = df.copy()
            df_3m["Fecha"] = pd.to_datetime(df_3m["Fecha"], errors="coerce")

            df_3m = df_3m[df_3m["Fecha"] >= fecha_limite]

            total = df_3m["Monto"].sum()
            st.success(f"Ventas últimos 3 meses: ${total:,.0f}")

        # 📆 ESTE AÑO
        elif "este año" in pregunta_lower:
            df_año = df[df["Año"] == año_actual]
            total = df_año["Monto"].sum()
            st.success(f"Ventas {año_actual}: ${total:,.0f}")

        # 💰 VENTAS GENERALES (fallback)
        elif "ventas" in pregunta_lower:
            df_año = df[df["Año"] == año_actual]
            total = df_año["Monto"].sum()
            st.success(f"Ventas {año_actual}: ${total:,.0f}")

        # 🏆 MEJOR CLIENTE
        elif "mejor cliente" in pregunta_lower:
            if not df.empty:
                agrupado = df.groupby("Nombre")["Monto"].sum()
                top = agrupado.idxmax()
                total_top = agrupado.max()
                st.success(f"Tu mejor cliente es {top} con ${total_top:,.0f}")
            else:
                st.warning("No hay datos disponibles")

        # 👥 TOTAL CLIENTES
        elif "clientes" in pregunta_lower and "perdidos" not in pregunta_lower:
            total_clientes = df["Nombre"].nunique()
            st.success(f"Tienes {total_clientes} clientes únicos")

        # 🔴 CLIENTES PERDIDOS
        elif "perdidos" in pregunta_lower or "no han venido" in pregunta_lower:

            df_lost = df.copy()
            df_lost["Fecha"] = pd.to_datetime(df_lost["Fecha"], errors="coerce")
            df_lost["Monto"] = pd.to_numeric(df_lost["Monto"], errors="coerce")

            ultimo = df_lost.groupby("Nombre").agg(
                Ultima_Visita=("Fecha", "max"),
                Total_Gastado=("Monto", "sum"),
                Tel=("Tel", "last")
            ).reset_index()

            ultimo["Meses_sin_servicio"] = ((hoy - ultimo["Ultima_Visita"]).dt.days / 30).round(1)

            perdidos = ultimo[ultimo["Meses_sin_servicio"] >= 6]

            if not perdidos.empty:
                st.dataframe(perdidos)
            else:
                st.success("No hay clientes perdidos 🎉")

        # ❌ NO ENTENDIDO
        else:
            st.warning("Aún no entiendo esa pregunta 😅")
    # AGENDA
elif pagina == "Agenda":
    st.title("📅 Agenda de Servicios")

    def parsear_fechas(serie):
        resultado = pd.to_datetime(serie, errors="coerce", format="%m/%d/%Y")
        mask = resultado.isna()
        if mask.any():
            resultado[mask] = pd.to_datetime(serie[mask], errors="coerce", format="%d/%m/%Y")
        return resultado

    df_a = df.copy()
    df_a["Fecha"] = parsear_fechas(df_a["Fecha"])
    df_a["Monto"] = pd.to_numeric(df_a["Monto"], errors="coerce")

    plantillas = USUARIOS[st.session_state["usuario"]].get("plantillas", {})
    empresa = st.session_state.get("empresa", "")

    # 📅 SELECCIÓN DE FECHA
    fecha_sel = st.date_input("Selecciona una fecha", datetime.now(), key="agenda_fecha_1")
    df_dia = df_a[df_a["Fecha"].dt.date == fecha_sel]

    # 📊 MÉTRICAS DEL DÍA
    total_dia = df_dia["Monto"].sum()
    col1, col2 = st.columns(2)
    col1.metric("Servicios ese día", len(df_dia))
    col2.metric("Ingresos del día", f"${total_dia:,.0f}")
    st.markdown("---")

    # 📋 SERVICIOS DEL DÍA
    if df_dia.empty:
        st.info("No hay servicios agendados")
    else:
        for _, row in df_dia.iterrows():
            with st.container():
                st.markdown(f"""
                **👤 Cliente:** {row.get('Nombre','')}  
                **📞 Tel:** {row.get('Tel','')}  
                **📍 Dirección:** {row.get('Dirección','')}  
                **🧼 Servicio:** {row.get('Servicio','')}  
                **💰 Monto:** ${row.get('Monto',0):,.0f}
                """)
                tel = str(row.get("Tel", "")).replace("-", "").replace(" ", "")
                if tel:
                    tel = "52" + tel
                    mensaje_template = plantillas.get("confirmacion", "Hola {nombre}")
                    mensaje = mensaje_template.format(nombre=row.get("Nombre", ""), empresa=empresa)
                    url = f"https://wa.me/{tel}?text={mensaje.replace(' ', '%20')}"
                    st.markdown(f"[💬 Enviar WhatsApp]({url})")
                else:
                    st.warning("Cliente sin teléfono")
                st.markdown("---")

    # ➕ AGENDAR SERVICIO
    st.markdown("### ➕ Agendar nuevo servicio")

    clientes_info = (
        df_a.groupby("Nombre").agg(
            Telefonos=("Tel", lambda x: " / ".join(
                str(t) for t in x.dropna().unique()
                if str(t).strip() not in ["", "nan"]
            )),
            Direccion=("Dirección", "last")
        ).reset_index()
    )
    clientes_lista = [""] + clientes_info["Nombre"].tolist()

    cliente_sel = st.selectbox("Cliente existente (opcional)", clientes_lista, key="cliente_agenda_sel")

    tel_default = ""
    dir_default = ""
    if cliente_sel:
        fila_cliente = clientes_info[clientes_info["Nombre"] == cliente_sel]
        if not fila_cliente.empty:
            tel_default = fila_cliente.iloc[0]["Telefonos"]
            dir_default = str(fila_cliente.iloc[0]["Direccion"]) if pd.notnull(fila_cliente.iloc[0]["Direccion"]) else ""

    with st.form("agendar_servicio"):
        nombre = st.text_input("Nombre del cliente", value=cliente_sel)
        telefono = st.text_input("Teléfono(s)", value=tel_default)
        direccion = st.text_input("Dirección", value=dir_default)
        servicio = st.text_input("Servicio")

        col1, col2 = st.columns(2)
        with col1:
            fecha = st.date_input("Fecha", datetime.now())
        with col2:
            monto = st.number_input("Monto", min_value=0)

        submitted = st.form_submit_button("Agendar")

        if submitted:
            try:
                client = get_gspread_client()
                sheet_id = st.session_state["SHEET_IDS"][fecha.year]
                sh = client.open_by_key(sheet_id)
                worksheet = sh.get_worksheet(0)

                # Calcular siguiente folio desde columna B
                col_b = worksheet.col_values(2)
                ultimo_folio = 0
                for v in col_b[1:]:
                    try:
                        num = int(str(v).strip().split("/")[0])
                        if num < 10000:
                            ultimo_folio = max(ultimo_folio, num)
                    except:
                        continue

                siguiente_folio = ultimo_folio + 1
                folio_interno = f"{siguiente_folio}/{str(fecha.year)[-2:]}"

                nueva_fila = [
                    siguiente_folio,
                    folio_interno,
                    fecha.strftime("%m/%d/%Y"),
                    nombre, telefono, direccion,
                    "Agenda", monto, servicio,
                    "", "", "", ""
                ]

                # Buscar primera fila vacía por columna C (Fecha)
                col_c = worksheet.col_values(3)
                datos_col_c = col_c[1:]
                primera_vacia = None
                for i, v in enumerate(datos_col_c):
                    if str(v).strip() == "":
                        primera_vacia = i + 2
                        break

                if primera_vacia is None:
                    primera_vacia = len(datos_col_c) + 2

                worksheet.insert_row(nueva_fila, primera_vacia)

                st.success("✅ Servicio agendado correctamente")
                st.cache_data.clear()
                st.cache_resource.clear()
                st.session_state["agenda_refresh"] = st.session_state.get("agenda_refresh", 0) + 1
                import time as t
                t.sleep(2)
                st.rerun()

            except Exception as e:
                st.error(f"Error al agendar: {e}")

    st.markdown("---")

    # 📅 CALENDARIO
    from streamlit_calendar import calendar

    st.markdown("### 📅 Calendario de servicios")

    def cargar_datos_calendario(sheet_ids):
        client = get_gspread_client()
        dfs = []
        columnas_base = [
            "Fecha", "Nombre", "Tel", "Dirección",
            "Origen", "Monto", "Servicio",
            "Comentarios con llamada posterior a venta"
        ]
        for año, sheet_id in sheet_ids.items():
            if not sheet_id:
                continue
            try:
                sh = client.open_by_key(sheet_id)
                worksheet = sh.get_worksheet(0)
                data = worksheet.get_all_records()
                df_tmp = pd.DataFrame(data)
                if df_tmp.empty:
                    df_tmp = pd.DataFrame(columns=columnas_base)
                df_tmp["Año"] = año
                dfs.append(df_tmp)
            except:
                continue
        if not dfs:
            return pd.DataFrame(columns=columnas_base + ["Año"])
        return pd.concat(dfs, ignore_index=True)

    with st.spinner("Cargando calendario..."):
        df_cal_raw = cargar_datos_calendario(st.session_state.get("SHEET_IDS", {}))

    df_cal_raw.columns = df_cal_raw.columns.str.strip()
    df_cal_raw["Fecha"] = parsear_fechas(df_cal_raw["Fecha"])
    if "Monto" in df_cal_raw.columns:
        df_cal_raw["Monto"] = pd.to_numeric(df_cal_raw["Monto"], errors="coerce")
    df_cal = df_cal_raw[df_cal_raw["Fecha"].dt.year >= 2021].copy()
    df_cal = df_cal.dropna(subset=["Fecha"])

    eventos = []
    for _, row in df_cal.iterrows():
        eventos.append({
            "title": f"{row.get('Nombre', '')} — {row.get('Servicio', '')}",
            "start": row["Fecha"].strftime("%Y-%m-%d"),
            "end": row["Fecha"].strftime("%Y-%m-%d"),
            "extendedProps": {
                "folio": str(row.get("Folio sistema", "")),
                "año": int(row.get("Año", 0))
            }
        })

    opciones_calendario = {
        "initialView": "dayGridMonth",
        "locale": "es",
        "headerToolbar": {
            "left": "prev,next today",
            "center": "title",
            "right": "dayGridMonth,timeGridWeek,listWeek"
        },
        "height": 600,
    }

    resultado = calendar(events=eventos, options=opciones_calendario, key="calendario_principal")

    # 📋 DETALLE AL PICAR EVENTO
    if resultado and resultado.get("eventClick"):
        evento_click = resultado["eventClick"]["event"]
        folio_click = evento_click.get("extendedProps", {}).get("folio")
        año_click = evento_click.get("extendedProps", {}).get("año")

        if folio_click and año_click:
            df_evento = df_cal[
                (df_cal["Folio sistema"].astype(str) == str(folio_click)) &
                (df_cal["Año"] == año_click)
            ]

            if not df_evento.empty:
                row = df_evento.iloc[0]

                st.markdown("---")
                st.markdown("### 📋 Detalle del servicio")
                st.markdown(f"""
                **👤 Cliente:** {row.get('Nombre','')}  
                **📞 Tel:** {row.get('Tel','')}  
                **📍 Dirección:** {row.get('Dirección','')}  
                **🧼 Servicio:** {row.get('Servicio','')}  
                **💰 Monto:** ${row.get('Monto',0):,.0f}  
                **💬 Comentarios:** {row.get('Comentarios con llamada posterior a venta','')}
                """)

                tel_ev = str(row.get("Tel", "")).replace("-", "").replace(" ", "")
                if tel_ev:
                    tel_ev = "52" + tel_ev
                    mensaje_template = plantillas.get("confirmacion", "Hola {nombre}")
                    mensaje = mensaje_template.format(nombre=row.get("Nombre", ""), empresa=empresa)
                    url = f"https://wa.me/{tel_ev}?text={mensaje.replace(' ', '%20')}"
                    st.markdown(f"[💬 Enviar WhatsApp]({url})")

                if st.button("🗑️ Borrar este servicio", key="borrar_evento"):
                    try:
                        client = get_gspread_client()
                        sheet_id = st.session_state["SHEET_IDS"][row["Fecha"].year]
                        sh = client.open_by_key(sheet_id)
                        worksheet = sh.get_worksheet(0)

                        celdas = worksheet.findall(str(folio_click))
                        if celdas:
                            worksheet.delete_rows(celdas[0].row)
                            st.success("✅ Servicio eliminado")
                            st.cache_data.clear()
                            st.cache_resource.clear()
                            st.rerun()
                        else:
                            st.warning("No se encontró el servicio en el sheet")
                    except Exception as e:
                        st.error(f"Error al borrar: {e}")
    # ── COTIZACIONES ──
elif pagina == "Cotizaciones":
    st.title("Cotizador de Servicios")

    cotizador = USUARIOS[st.session_state["usuario"]].get("cotizador", {})

    PAQUETES = cotizador.get("paquetes", [])
    MINIMO = cotizador.get("minimo", 0)
    PRECIOS = cotizador.get("precios", {})
    SERVICIOS_CON_CANTIDAD = cotizador.get("servicios_cantidad", [])
    SERVICIOS_CON_PLAZAS = cotizador.get("servicios_plazas", [])
    SERVICIOS_CON_SILLAS = cotizador.get("servicios_sillas", [])
    INTRO = cotizador.get("intro", "")
    PURT_DESC = cotizador.get("purt_descripcion", "")
    PURT_COSTO = cotizador.get("purt_costo", 0)
    DESC_PAQUETES = cotizador.get("descripcion_paquetes", {})
    DESCUENTOS = cotizador.get("descuentos_paquete", {})
    CIERRE = cotizador.get("cierre", "")
    FIRMA = cotizador.get("firma", "")

    if not PAQUETES or not PRECIOS:
        st.info("Este usuario no tiene cotizador configurado.")
        st.stop()

    st.markdown("### Agregar servicios a la cotización")

    if "items_cotizacion" not in st.session_state:
        st.session_state["items_cotizacion"] = []

    col1, col2 = st.columns([3, 1])

    with col1:
        servicio = st.selectbox("Servicio:", list(PRECIOS.keys()))

    with col2:
        if servicio in SERVICIOS_CON_CANTIDAD:
            cantidad = st.number_input("m2:", min_value=1, value=1)
            label_cantidad = "m2"
        elif servicio in SERVICIOS_CON_PLAZAS:
            cantidad = st.number_input("Plazas:", min_value=1, value=1)
            label_cantidad = "plazas"
        elif servicio in SERVICIOS_CON_SILLAS:
            cantidad = st.number_input("Sillas:", min_value=1, value=1)
            label_cantidad = "sillas"
        else:
            cantidad = 1
            label_cantidad = "unidad"

    # PRECIOS POR PAQUETE
    precio_data = {
        "Paquete": PAQUETES,
        "Precio": [f"${PRECIOS[servicio][p] * cantidad:,.0f}" for p in PAQUETES]
    }
    st.dataframe(pd.DataFrame(precio_data), use_container_width=True, hide_index=True)

    if st.button("Agregar a cotización", use_container_width=True):
        st.session_state["items_cotizacion"].append({
            "Servicio": servicio,
            "Cantidad": cantidad,
            "Label": label_cantidad,
            "Precios": {p: PRECIOS[servicio][p] * cantidad for p in PAQUETES}
        })

    # RESUMEN
    if st.session_state["items_cotizacion"]:
        st.markdown("---")
        st.markdown("### Resumen — todos los paquetes")

        filas = []
        for item in st.session_state["items_cotizacion"]:
            fila = {"Servicio": f"{item['Servicio']} ({item['Cantidad']} {item['Label']})"}
            for p in PAQUETES:
                fila[p] = f"${item['Precios'][p]:,.0f}"
            filas.append(fila)

        totales = {"Servicio": "TOTAL"}
        for p in PAQUETES:
            total_p = sum(i["Precios"][p] for i in st.session_state["items_cotizacion"])
            descuento = DESCUENTOS.get(p, 0)
            total_con_descuento = total_p * (1 - descuento / 100)
            total_final = max(total_con_descuento, MINIMO)
            nota = " *" if total_p < MINIMO else ""
            totales[p] = f"${total_final:,.0f}{nota}"

        filas.append(totales)
        st.dataframe(pd.DataFrame(filas), use_container_width=True, hide_index=True)

        # MENSAJE PROFESIONAL
        st.markdown("### Mensaje para cliente")

        nombre_cliente = st.text_input("Nombre del cliente (opcional):")
        incluir_purt = st.checkbox("Incluir descripción de PURT", value=bool(PURT_DESC))

        lineas = []

        if nombre_cliente:
            lineas.append(f"Estimado/a {nombre_cliente},\n")

        if INTRO:
            lineas.append(INTRO)
            lineas.append("")

        if incluir_purt and PURT_DESC:
            lineas.append(PURT_DESC)
            lineas.append("")

        lineas.append("El servicio de acuerdo a su solicitud tiene una inversión de:\n")

        for p in PAQUETES:
            total_p = sum(i["Precios"][p] for i in st.session_state["items_cotizacion"])
            descuento = DESCUENTOS.get(p, 0)
            total_con_descuento = total_p * (1 - descuento / 100)
            total_final = max(total_con_descuento, MINIMO)

            lineas.append(f"Paquete {p}:")
            if p in DESC_PAQUETES:
                lineas.append(DESC_PAQUETES[p])

            for item in st.session_state["items_cotizacion"]:
                lineas.append(f"{item['Servicio']} ({item['Cantidad']} {item['Label']}): ${item['Precios'][p]:,.0f}")

            if incluir_purt and PURT_COSTO > 0:
                lineas.append(f"PURT: ${PURT_COSTO:,.0f}")

            if descuento > 0:
                lineas.append(f"Descuento por volumen {descuento}%")

            lineas.append(f"TOTAL: ${total_final:,.0f}")
            lineas.append("")

        if CIERRE:
            lineas.append(CIERRE)

        if FIRMA:
            lineas.append(FIRMA)

        st.text_area("Copia este mensaje:", "\n".join(lineas), height=400)

        if st.button("Limpiar cotización", use_container_width=True):
            st.session_state["items_cotizacion"] = []
            st.rerun()