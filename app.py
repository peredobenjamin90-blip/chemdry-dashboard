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
    [data-testid="stSidebar"] > div:first-child {
        padding-top: 0rem !important;
    }
    section[data-testid="stSidebar"] > div {
        padding-top: 0.5rem !important;
    }
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

@st.cache_data(ttl=600)
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

    sheet_items = list(sheet_ids.items())

    for idx, (año, sheet_id) in enumerate(sheet_items):
        if not sheet_id:
            continue

        if idx > 0:
            time.sleep(2)

        for intento in range(3):
            try:
                sh = client.open_by_key(sheet_id)
                worksheet = sh.get_worksheet(0)

                # Leer todo como valores crudos sin validar headers
                valores = worksheet.get_all_values()

                if not valores or len(valores) < 2:
                    df = pd.DataFrame(columns=columnas_base)
                else:
                    headers = valores[0]
                    filas = valores[1:]
                    # Normalizar headers duplicados o vacíos
                    headers_limpios = []
                    conteo = {}
                    for h in headers:
                        h = h.strip()
                        if h == "":
                            h = "Col_vacia"
                        if h in conteo:
                            conteo[h] += 1
                            h = f"{h}_{conteo[h]}"
                        else:
                            conteo[h] = 0
                        headers_limpios.append(h)

                    df = pd.DataFrame(filas, columns=headers_limpios)

                df["Año"] = año
                dfs.append(df)
                break

            except Exception as e:
                error_str = str(e)
                errores.append(f"Año {año} intento {intento}: {error_str}")

                if "429" in error_str:
                    wait = (intento + 1) * 10
                    time.sleep(wait)
                elif intento < 2:
                    time.sleep(3)

    if not dfs:
        return pd.DataFrame(columns=columnas_base + ["Año"]), errores
    return pd.concat(dfs, ignore_index=True), errores
resultado = cargar_datos(st.session_state.get("SHEET_IDS", {}))
df = resultado[0]
errores_carga = resultado[1]
st.caption(f"Columnas detectadas: {list(df.columns[:10])}")

# Solo mostrar errores que no sean rate limit resuelto
errores_graves = [e for e in errores_carga if "429" not in e or df.empty]
if errores_graves:
    for e in errores_graves:
        st.error(e)
elif errores_carga and not df.empty:
    st.caption("⚠️ Algunos sheets tardaron en cargar pero los datos están disponibles.")
def asignar_ids_clientes():
    import unicodedata
    import json

    client = get_gspread_client()
    sheet_ids = st.session_state.get("SHEET_IDS", {})

    def normalizar(nombre):
        nombre = str(nombre).strip().lower()
        nombre = unicodedata.normalize("NFKD", nombre)
        nombre = "".join(c for c in nombre if not unicodedata.combining(c))
        nombre = " ".join(nombre.split())
        return nombre

    datos_sheets = {}
    for año, sheet_id in sheet_ids.items():
        if not sheet_id:
            continue
        try:
            sh = client.open_by_key(sheet_id)
            ws = sh.get_worksheet(0)
            col_nombres = ws.col_values(4)  # col D = Nombre (antes de insertar)
            datos_sheets[año] = {"ws": ws, "sh": sh, "nombres": col_nombres}
        except Exception as e:
            st.warning(f"No se pudo leer el sheet {año}: {e}")

    if not datos_sheets:
        st.error("No hay sheets disponibles.")
        return

    mapa_id = {}
    contador = 1
    for año, data in datos_sheets.items():
        for nombre in data["nombres"][1:]:
            if not nombre or str(nombre).strip() in ["", "nan"]:
                continue
            norm = normalizar(nombre)
            if norm not in mapa_id:
                mapa_id[norm] = contador
                contador += 1

    st.info(f"Se identificaron {contador - 1} clientes únicos.")

    for año, data in datos_sheets.items():
        ws = data["ws"]
        sh = data["sh"]
        nombres = data["nombres"]
        try:
            sheet_tab_id = ws.id
            sh.batch_update({"requests": [{
                "insertDimension": {
                    "range": {
                        "sheetId": sheet_tab_id,
                        "dimension": "COLUMNS",
                        "startIndex": 3,
                        "endIndex": 4
                    },
                    "inheritFromBefore": False
                }
            }]})

            ws.update_cell(1, 4, "ID Cliente")

            updates = []
            for i, nombre in enumerate(nombres[1:], start=2):
                if not nombre or str(nombre).strip() in ["", "nan"]:
                    continue
                norm = normalizar(nombre)
                id_cliente = mapa_id.get(norm, "")
                updates.append({"range": f"D{i}", "values": [[id_cliente]]})

            for i in range(0, len(updates), 100):
                ws.batch_update(updates[i:i+100])

            st.success(f"✅ Sheet {año} — {len(updates)} filas actualizadas")
        except Exception as e:
            st.error(f"Error en sheet {año}: {e}")

    st.success(f"🎉 Listo — columna ID Cliente agregada entre Fecha y Nombre")
    st.warning("Estructura nueva: A=Folio sistema | B=Folio interno | C=Fecha | D=ID Cliente | E=Nombre | F=Tel")
    st.cache_data.clear()

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

    # ─────────────────────────────
    # 🔔 BANNER DE RECORDATORIOS
    # ─────────────────────────────
    if "meses_recordatorio" not in st.session_state:
        st.session_state["meses_recordatorio"] = 6

    meses_recordatorio = st.session_state["meses_recordatorio"]

    df_banner = df.copy()
    df_banner["Fecha"] = pd.to_datetime(df_banner["Fecha"], errors="coerce")

    ultimo_banner = df_banner.groupby("Nombre").agg(
        Ultima_Visita=("Fecha", "max")
    ).reset_index()
    ultimo_banner["Meses_sin_servicio"] = (
        (datetime.now() - ultimo_banner["Ultima_Visita"]).dt.days / 30
    ).round(1)

    clientes_pendientes = ultimo_banner[
        ultimo_banner["Meses_sin_servicio"] >= meses_recordatorio
    ]

    if not clientes_pendientes.empty:
        col_banner, col_config = st.columns([4, 1])
        with col_banner:
            if st.button(
                f"🔔 {len(clientes_pendientes)} clientes llevan {meses_recordatorio}+ meses sin servicio — Ver en Follow Up →",
                use_container_width=True,
                key="btn_banner_followup"
            ):
                st.session_state["pagina"] = "Follow Up"
                st.session_state["followup_meses_override"] = meses_recordatorio
                st.rerun()
        with col_config:
            if st.button(
                "⚙️ Configurar",
                key="btn_config_recordatorio",
                use_container_width=True
            ):
                st.session_state["mostrar_config_recordatorio"] = not st.session_state.get(
                    "mostrar_config_recordatorio", False
                )

        if st.session_state.get("mostrar_config_recordatorio", False):
            nuevo_umbral = st.slider(
                "Avisar cuando un cliente lleve X meses sin servicio:",
                1, 24, meses_recordatorio,
                key="slider_recordatorio"
            )
            if nuevo_umbral != meses_recordatorio:
                st.session_state["meses_recordatorio"] = nuevo_umbral
                st.rerun()

    st.markdown("---")

    # ─────────────────────────────
    # 📊 VENTAS Y FLUJO DE EFECTIVO
    # ─────────────────────────────
    st.subheader("📊 Ventas")

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

    if año_resumen > min(años_sin_2026):
        df_ant = df[df["Año"] == año_resumen - 1]
        ventas_ant = df_ant["Monto"].sum()
        diferencia = total_ventas - ventas_ant
        porcentaje = (diferencia / ventas_ant * 100) if ventas_ant > 0 else 0
        color = "green" if diferencia > 0 else "red"
        simbolo = "▲" if diferencia > 0 else "▼"
        st.markdown(
            f"<p style='color:{color}; font-size:16px'>{simbolo} Comparado con {año_resumen-1}: "
            f"${abs(diferencia):,.0f} ({porcentaje:+.1f}%)</p>",
            unsafe_allow_html=True
        )

    # ─────────────────────────────
    # 💰 FLUJO DE EFECTIVO
    # ─────────────────────────────
    st.subheader("💰 Flujo de efectivo")

    finanzas_usuario = USUARIOS[st.session_state["usuario"]].get("finanzas", {})

    if finanzas_usuario:
        años_finanzas = list(finanzas_usuario.keys())
        año_finanzas = st.selectbox(
            "Año financiero:",
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
    else:
        st.info("No hay datos de flujo de efectivo configurados.")
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
        st.markdown(
            f"<p style='color:{color}'>Basado en {meses_con_datos_2026} mes(es) de datos reales de 2026</p>",
            unsafe_allow_html=True
        )

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

    # ─────────────────────────────
    # 📈 CONVERSIÓN DE FOLLOW UP
    # ─────────────────────────────
    st.markdown("---")
    st.subheader("📈 Conversión de Follow Up")

    if "followup_resultados" not in st.session_state:
        st.session_state["followup_resultados"] = []

    resultados = st.session_state["followup_resultados"]

    if resultados:
        import collections
        conteo_resultados = collections.Counter(r["resultado"] for r in resultados)
        total_contactados = len(resultados)
        agendaron = conteo_resultados.get("Agendó", 0)
        tasa = (agendaron / total_contactados * 100) if total_contactados > 0 else 0

        col1, col2, col3 = st.columns(3)
        col1.metric("Total contactados", total_contactados)
        col2.metric("Agendaron", agendaron)
        col3.metric("Tasa de conversión", f"{tasa:.1f}%")

        df_res = pd.DataFrame(resultados)
        conteo_df = df_res["resultado"].value_counts().reset_index()
        conteo_df.columns = ["Resultado", "Cantidad"]
        st.bar_chart(conteo_df.set_index("Resultado"))

        with st.expander("Ver detalle completo"):
            st.dataframe(
                pd.DataFrame(resultados)[["timestamp", "nombre", "resultado", "bloque"]],
                use_container_width=True,
                hide_index=True
            )
    else:
        st.info("Aún no hay resultados de follow up registrados. Márcalos en la página Follow Up.")
        # CLIENTES
elif pagina == "Clientes":
    import urllib.parse
    import base64
    import streamlit.components.v1 as components

    st.title("Origen de Clientes")

    año_origen = st.selectbox("Año:", años_sin_2026)
    df_o = df[df["Año"] == año_origen].copy()

    df_o["Origen"] = (
        df_o["Origen"]
        .astype(str)
        .str.strip()
        .str.lower()
    )

    origenes_config = USUARIOS[st.session_state["usuario"]].get("origenes", {})
    df_o["Origen"] = df_o["Origen"].replace(origenes_config)
    df_o["Origen"] = df_o["Origen"].replace(["", "nan"], "Sin especificar")

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
        PLANTILLAS_MASIVAS = {
            "Recordatorio": "Hola {nombre}, te contactamos de {empresa}. Hace tiempo no realizas un servicio con nosotros. ¿Te gustaría agendar?",
            "Promoción": "Hola {nombre}, en {empresa} tenemos una promoción especial. ¿Te interesa?",
            "Seguimiento": "Hola {nombre}, te damos seguimiento desde {empresa}. ¿Cómo fue tu servicio?",
            "Reactivación": "Hola {nombre}, te extrañamos en {empresa} 😄 ¿Agendamos esta semana?"
        }

        empresa = st.session_state.get("empresa", "")

        plantilla_sel_masiva = st.selectbox(
            "Plantilla para todos",
            list(PLANTILLAS_MASIVAS.keys()),
            key="plantilla_masiva_clientes"
        )
        mensaje_base_masivo = PLANTILLAS_MASIVAS[plantilla_sel_masiva]

        urls_perdidos = []
        for _, row in perdidos.iterrows():
            tel = str(row["Tel"]).replace("-", "").replace(" ", "")
            if tel and tel != "nan":
                tel_completo = "52" + tel
                mensaje = mensaje_base_masivo.format(nombre=row["Nombre"], empresa=empresa)
                urls_perdidos.append((
                    row["Nombre"],
                    f"https://wa.me/{tel_completo}?text={urllib.parse.quote(mensaje)}"
                ))

        if urls_perdidos:
            cols = st.columns(3)
            for i, (nombre_btn, url_btn) in enumerate(urls_perdidos):
                with cols[i % 3]:
                    st.link_button(f"💬 {nombre_btn}", url_btn)

            html_links_cl = ""
            for nombre_link, url_link in urls_perdidos:
                html_links_cl += f"""
                <a href="{url_link}" target="_blank" style="
                    display:block; background-color:#25D366; color:white;
                    text-decoration:none; padding:12px 16px; border-radius:8px;
                    margin-bottom:8px; font-size:15px; font-family:sans-serif;
                ">💬 {nombre_link}</a>
                """

            pagina_html_cl = f"""
            <!DOCTYPE html><html><head><meta charset="utf-8">
            <title>Contacto masivo</title>
            <style>
                body{{font-family:sans-serif;padding:24px;max-width:500px;margin:auto;background:#f9f9f9;}}
                h2{{color:#128C7E;}}p{{color:#555;margin-bottom:20px;}}
            </style></head>
            <body>
                <h2>📋 {len(urls_perdidos)} clientes a contactar</h2>
                <p>Haz click en cada nombre para abrir WhatsApp Web.</p>
                {html_links_cl}
            </body></html>
            """

            b64_cl = base64.b64encode(pagina_html_cl.encode("utf-8")).decode("utf-8")
            components.html(f"""
            <a href="data:text/html;base64,{b64_cl}" target="_blank" style="
                display:block; background-color:#128C7E; color:white;
                text-decoration:none; text-align:center; border-radius:8px;
                padding:14px 24px; font-size:16px; font-family:sans-serif; margin-top:8px;
            ">🚀 Abrir panel de contacto masivo ({len(urls_perdidos)} contactos)</a>
            """, height=65)

    # 💬 CONTACTO INDIVIDUAL
    st.markdown("### 💬 Contacto rápido")

    if not perdidos.empty:
        PLANTILLAS_IND = {
            "Recordatorio": "Hola {nombre}, te contactamos de {empresa}. Hace tiempo no realizas un servicio con nosotros. ¿Te gustaría agendar?",
            "Promoción": "Hola {nombre}, en {empresa} tenemos una promoción especial. ¿Te interesa?",
            "Seguimiento": "Hola {nombre}, te damos seguimiento desde {empresa}. ¿Cómo fue tu servicio?",
            "Reactivación": "Hola {nombre}, te extrañamos en {empresa} 😄 ¿Agendamos esta semana?"
        }

        cliente_sel_contacto = st.selectbox(
            "Selecciona cliente",
            perdidos["Nombre"],
            key="select_contacto"
        )

        cliente_data = perdidos[perdidos["Nombre"] == cliente_sel_contacto].iloc[0]
        tel = str(cliente_data["Tel"]).replace("-", "").replace(" ", "")
        if tel and tel != "nan":
            tel = "52" + tel

        plantilla_ind_cl = st.selectbox(
            "Plantilla",
            list(PLANTILLAS_IND.keys()),
            key="plantilla_ind_clientes"
        )
        mensaje = PLANTILLAS_IND[plantilla_ind_cl].format(
            nombre=cliente_sel_contacto,
            empresa=st.session_state.get("empresa", "tu negocio")
        )
        mensaje_edit = st.text_area("Mensaje", value=mensaje, key="msg_edit_clientes")

        if tel and tel != "52nan":
            url = f"https://wa.me/{tel}?text={urllib.parse.quote(mensaje_edit)}"
            st.link_button("💬 Abrir WhatsApp", url)
        else:
            st.warning("Este cliente no tiene teléfono válido")

    # 🔢 NUMERACIÓN ÚNICA
    st.markdown("---")
    st.markdown("### 🔢 Numeración única de clientes")
    with st.expander("⚠️ Usar solo una vez"):
        st.markdown("Inserta columna **ID Cliente** entre Fecha y Nombre en todos los sheets. Clientes repetidos entre años reciben el mismo número. **No correr dos veces.**")
        confirmar = st.checkbox("Entiendo que esto modifica los sheets permanentemente")
        if confirmar:
            if st.button("🔢 Asignar IDs únicos", use_container_width=True):
                asignar_ids_clientes()
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
    import urllib.parse
    import json
    import base64
    import streamlit.components.v1 as components
    from datetime import datetime

    if "followup_historial" not in st.session_state:
        st.session_state["followup_historial"] = []
    if "followup_resultados" not in st.session_state:
        st.session_state["followup_resultados"] = []

    ultimo = df.groupby("Nombre").agg(Fecha=("Fecha","max")).reset_index()
    ultimo.columns = ["Nombre", "Ultimo servicio"]

    tels = df[["Nombre","Tel"]].drop_duplicates(subset="Nombre")
    comentarios = df.sort_values("Fecha").drop_duplicates(subset="Nombre", keep="last")[
        ["Nombre","Comentarios con llamada posterior a venta"]
    ]

    ultimo = ultimo.merge(tels, on="Nombre", how="left")
    ultimo = ultimo.merge(comentarios, on="Nombre", how="left")
    ultimo.columns = ["Nombre", "Ultimo servicio", "Tel", "Comentario"]

    # ── Si viene del banner, usar ese umbral; si no, el slider ──
    meses_default = st.session_state.pop("followup_meses_override", None)

    col1, col2 = st.columns(2)
    with col1:
        meses = st.slider(
            "Sin servicio hace más de X meses:",
            1, 24,
            meses_default if meses_default is not None else 6
        )
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

    hoy = datetime.now()
    def get_columna_followup(ultima_fecha):
        if pd.isna(ultima_fecha):
            return 13
        meses_sin = (hoy - ultima_fecha).days / 30
        if meses_sin < 3:
            return 11
        elif meses_sin < 8:
            return 12
        else:
            return 13

    st.metric("Clientes a contactar", len(sin_servicio))
    st.dataframe(sin_servicio, use_container_width=True)

    st.markdown("### 🚀 Enviar mensaje a todos")

    PLANTILLAS_MENSAJES = {
        "Seguimiento": "Hola {nombre}, te contactamos de {empresa}. Solo para dar seguimiento a tu último servicio. ¿Cómo fue tu experiencia?",
        "Recordatorio": "Hola {nombre}, en {empresa} te recordamos que ya pasó tiempo desde tu último servicio. ¿Te gustaría agendar?",
        "Promoción": "Hola {nombre}, en {empresa} tenemos una promoción especial disponible. ¿Te interesa aprovecharla?",
        "Reactivación": "Hola {nombre}, te extrañamos en {empresa} 😄 Tenemos disponibilidad esta semana. ¿Agendamos?"
    }

    plantilla_masiva = st.selectbox(
        "Plantilla:",
        list(PLANTILLAS_MENSAJES.keys()),
        key="plantilla_masiva_followup"
    )

    mensaje_masivo_preview = PLANTILLAS_MENSAJES[plantilla_masiva].format(
        nombre="[Nombre]",
        empresa=st.session_state.get("empresa", "nuestro negocio")
    )
    mensaje_masivo_edit = st.text_area(
        "Edita el mensaje ({nombre} y {empresa} se reemplazan automáticamente):",
        value=mensaje_masivo_preview,
        key="mensaje_masivo_edit"
    )

    TAMANO_BLOQUE = 20

    if not sin_servicio.empty:
        clientes_validos = sin_servicio[
            sin_servicio["Tel"].notna() &
            (sin_servicio["Tel"].astype(str).str.strip() != "") &
            (sin_servicio["Tel"].astype(str).str.strip() != "nan")
        ].reset_index(drop=True)

        total_bloques = (len(clientes_validos) + TAMANO_BLOQUE - 1) // TAMANO_BLOQUE

        st.caption(f"📦 {len(clientes_validos)} clientes divididos en {total_bloques} bloque(s) de {TAMANO_BLOQUE}")

        bloque_sel = st.selectbox(
            "Selecciona bloque a enviar:",
            [f"Bloque {i+1} ({i*TAMANO_BLOQUE+1}-{min((i+1)*TAMANO_BLOQUE, len(clientes_validos))})"
             for i in range(total_bloques)],
            key="bloque_sel"
        )

        idx_bloque = int(bloque_sel.split(" ")[1]) - 1
        inicio = idx_bloque * TAMANO_BLOQUE
        fin = inicio + TAMANO_BLOQUE
        clientes_bloque = clientes_validos.iloc[inicio:fin]

        urls_bloque = []
        for _, row in clientes_bloque.iterrows():
            tel = str(row["Tel"]).replace("-", "").replace(" ", "").strip()
            tel_completo = "52" + tel
            mensaje_final = mensaje_masivo_edit.format(
                nombre=row["Nombre"],
                empresa=st.session_state.get("empresa", "nuestro negocio")
            )
            mensaje_encoded = urllib.parse.quote(mensaje_final)
            urls_bloque.append((row["Nombre"], f"https://wa.me/{tel_completo}?text={mensaje_encoded}"))

        st.markdown(f"**Clientes en este bloque ({len(clientes_bloque)}):**")
        cols = st.columns(3)
        for i, (nombre_btn, url_btn) in enumerate(urls_bloque):
            with cols[i % 3]:
                st.link_button(f"💬 {nombre_btn}", url_btn)

        # ── PANEL DE ENVÍO MASIVO ──
        html_links = ""
        for nombre_link, url_link in urls_bloque:
            html_links += f"""
            <a href="{url_link}" target="_blank" style="
                display:block; background-color:#25D366; color:white;
                text-decoration:none; padding:12px 16px; border-radius:8px;
                margin-bottom:8px; font-size:15px; font-family:sans-serif;
            ">💬 {nombre_link}</a>
            """

        pagina_html = f"""
        <!DOCTYPE html><html><head><meta charset="utf-8">
        <title>WhatsApp Follow Up — Bloque {idx_bloque + 1}</title>
        <style>
            body{{font-family:sans-serif;padding:24px;max-width:500px;margin:auto;background:#f9f9f9;}}
            h2{{color:#128C7E;}}p{{color:#555;margin-bottom:20px;}}
        </style></head>
        <body>
            <h2>📋 Bloque {idx_bloque + 1} — {len(urls_bloque)} contactos</h2>
            <p>Haz click en cada nombre para abrir WhatsApp Web en una pestaña nueva.</p>
            {html_links}
        </body></html>
        """

        b64 = base64.b64encode(pagina_html.encode("utf-8")).decode("utf-8")
        components.html(f"""
        <a href="data:text/html;base64,{b64}" target="_blank" style="
            display:block; background-color:#128C7E; color:white;
            text-decoration:none; text-align:center; border-radius:8px;
            padding:14px 24px; font-size:16px; font-family:sans-serif; margin-top:8px;
        ">🚀 Abrir panel de envío — Bloque {idx_bloque + 1} ({len(urls_bloque)} contactos)</a>
        """, height=65)

        st.markdown("---")

        # ── REGISTRO DE RESULTADO ──
        st.markdown("### ✅ Marcar resultado del bloque")
        st.caption("Registra qué pasó con cada cliente. Esto alimenta el dashboard de conversión en Resumen.")

        OPCIONES_RESULTADO = ["Agendó", "No contestó", "Número inválido", "No le interesa", "Pendiente"]

        with st.expander(f"Registrar resultados — Bloque {idx_bloque + 1}"):
            resultados_bloque = {}
            for _, row in clientes_bloque.iterrows():
                resultados_bloque[row["Nombre"]] = st.selectbox(
                    row["Nombre"],
                    OPCIONES_RESULTADO,
                    index=4,
                    key=f"resultado_{row['Nombre']}_{idx_bloque}"
                )

        if st.button(f"✅ Guardar resultados y marcar bloque {idx_bloque+1} como enviado", use_container_width=True):
            timestamp = datetime.now().strftime("%d/%m/%Y %H:%M")
            errores_update = []

            with st.spinner("Guardando..."):
                try:
                    for nombre_r, resultado_r in resultados_bloque.items():
                        st.session_state["followup_resultados"].append({
                            "nombre": nombre_r,
                            "resultado": resultado_r,
                            "timestamp": timestamp,
                            "bloque": idx_bloque + 1
                        })

                    client = get_gspread_client()
                    sheet_ids = st.session_state.get("SHEET_IDS", {})

                    for _, row in clientes_bloque.iterrows():
                        nombre_cliente = row["Nombre"]
                        col_followup = get_columna_followup(row["Ultimo servicio"])

                        for año, sheet_id in sheet_ids.items():
                            if not sheet_id:
                                continue
                            try:
                                sh = client.open_by_key(sheet_id)
                                worksheet = sh.get_worksheet(0)
                                celdas = worksheet.findall(nombre_cliente)
                                for celda in celdas:
                                    resultado_celda = resultados_bloque.get(nombre_cliente, "Ok")
                                    worksheet.update_cell(celda.row, col_followup, resultado_celda)
                            except Exception as e:
                                errores_update.append(f"{nombre_cliente} ({año}): {e}")

                    st.session_state["followup_historial"].append({
                        "bloque": idx_bloque + 1,
                        "timestamp": timestamp,
                        "mes_filtro": mes_filtro,
                        "clientes": len(clientes_bloque),
                        "plantilla": plantilla_masiva,
                        "nombres": [n for n, _ in urls_bloque],
                        "resultados": resultados_bloque
                    })

                    st.success(f"✅ Bloque {idx_bloque+1} guardado — {timestamp}")
                    if errores_update:
                        st.warning(f"Algunos no se pudieron actualizar: {errores_update[:3]}")
                    st.cache_data.clear()

                except Exception as e:
                    st.error(f"Error guardando: {e}")

    if st.session_state["followup_historial"]:
        st.markdown("### 📋 Historial de envíos esta sesión")
        for h in reversed(st.session_state["followup_historial"]):
            with st.expander(f"Bloque {h['bloque']} — {h['timestamp']} — {h['clientes']} clientes — {h['mes_filtro']}"):
                st.caption(f"Plantilla: {h['plantilla']}")
                if "resultados" in h:
                    for nombre_h, resultado_h in h["resultados"].items():
                        st.write(f"• {nombre_h}: **{resultado_h}**")
                else:
                    st.write(", ".join(h['nombres']))

    st.markdown("---")

    st.markdown("### 💬 Enviar mensaje individual")

    if not sin_servicio.empty:
        cliente_sel = st.selectbox(
            "Selecciona cliente:",
            sin_servicio.apply(lambda x: f"{x['Nombre']} - {x['Tel']}", axis=1)
        )

        nombre = cliente_sel.split(" - ")[0]
        telefono = cliente_sel.split(" - ")[1].replace("-", "").replace(" ", "")

        plantilla_ind = st.selectbox(
            "Selecciona plantilla",
            list(PLANTILLAS_MENSAJES.keys()),
            key="plantilla_individual"
        )

        mensaje_base = PLANTILLAS_MENSAJES[plantilla_ind]
        mensaje_generado = mensaje_base.format(
            nombre=nombre,
            empresa=st.session_state.get("empresa", "nuestro negocio")
        )

        mensaje = st.text_area("Mensaje", value=mensaje_generado)

        if telefono and telefono != "nan":
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
    import urllib.parse

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

    # ─────────────────────────────
    # 📅 SELECCIÓN DE FECHA
    # ─────────────────────────────
    fecha_sel = st.date_input("Selecciona una fecha", datetime.now(), key="agenda_fecha_1")
    df_dia = df_a[df_a["Fecha"].dt.date == fecha_sel]

    total_dia = df_dia["Monto"].sum()
    col1, col2 = st.columns(2)
    col1.metric("Servicios ese día", len(df_dia))
    col2.metric("Ingresos del día", f"${total_dia:,.0f}")
    st.markdown("---")

    if df_dia.empty:
        st.info("No hay servicios agendados para este día.")
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
                if tel and tel != "nan":
                    tel_completo = "52" + tel
                    mensaje_template = plantillas.get("confirmacion", "Hola {nombre}")
                    mensaje = mensaje_template.format(nombre=row.get("Nombre", ""), empresa=empresa)
                    url = f"https://wa.me/{tel_completo}?text={urllib.parse.quote(mensaje)}"
                    st.markdown(f"[💬 Enviar WhatsApp]({url})")
                else:
                    st.warning("Cliente sin teléfono")
                st.markdown("---")

    # ─────────────────────────────
    # ➕ AGENDAR NUEVO SERVICIO
    # ─────────────────────────────
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
            if not nombre.strip():
                st.error("El nombre del cliente es obligatorio.")
            elif fecha.year not in st.session_state.get("SHEET_IDS", {}):
                st.error(f"No hay sheet configurado para el año {fecha.year}.")
            else:
                try:
                    client = get_gspread_client()
                    sheet_id = st.session_state["SHEET_IDS"][fecha.year]
                    sh = client.open_by_key(sheet_id)
                    worksheet = sh.get_worksheet(0)

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

                    st.success(f"✅ Servicio agendado para {nombre} el {fecha.strftime('%d/%m/%Y')}")
                    st.cache_data.clear()
                    st.cache_resource.clear()
                    # Limpiar evento seleccionado para no confundir
                    if "evento_seleccionado" in st.session_state:
                        del st.session_state["evento_seleccionado"]
                    import time as t
                    t.sleep(2)
                    st.rerun()

                except Exception as e:
                    st.error(f"Error al agendar: {e}")

    st.markdown("---")

    # ─────────────────────────────
    # 📅 CALENDARIO
    # ─────────────────────────────
    from streamlit_calendar import calendar

    st.markdown("### 📅 Calendario de servicios")

    @st.cache_data(ttl=300)
    def cargar_datos_calendario(sheet_ids_tuple):
        # Recibe tuple para que sea hasheable por cache
        sheet_ids = dict(sheet_ids_tuple)
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
                time.sleep(1)
            except Exception:
                continue
        if not dfs:
            return pd.DataFrame(columns=columnas_base + ["Año"])
        return pd.concat(dfs, ignore_index=True)

    sheet_ids_tuple = tuple(sorted(st.session_state.get("SHEET_IDS", {}).items()))

    with st.spinner("Cargando calendario..."):
        df_cal_raw = cargar_datos_calendario(sheet_ids_tuple)

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

    resultado_cal = calendar(
        events=eventos,
        options=opciones_calendario,
        key=f"calendario_principal_{st.session_state.get('agenda_refresh', 0)}"
    )

    # ── Guardar evento clickeado en session_state para que persista ──
    if resultado_cal and resultado_cal.get("eventClick"):
        evento_click = resultado_cal["eventClick"]["event"]
        folio_click = evento_click.get("extendedProps", {}).get("folio")
        año_click = evento_click.get("extendedProps", {}).get("año")
        if folio_click and año_click:
            st.session_state["evento_seleccionado"] = {
                "folio": folio_click,
                "año": año_click
            }

    # ─────────────────────────────
    # 📋 DETALLE DEL EVENTO — persiste entre reruns
    # ─────────────────────────────
    if "evento_seleccionado" in st.session_state:
        ev = st.session_state["evento_seleccionado"]
        folio_click = ev["folio"]
        año_click = ev["año"]

        df_evento = df_cal[
            (df_cal["Folio sistema"].astype(str) == str(folio_click)) &
            (df_cal["Año"] == año_click)
        ]

        if not df_evento.empty:
            row = df_evento.iloc[0]

            st.markdown("---")
            st.markdown("### 📋 Detalle del servicio")

            col1, col2 = st.columns([3, 1])
            with col1:
                st.markdown(f"""
                **👤 Cliente:** {row.get('Nombre','')}  
                **📞 Tel:** {row.get('Tel','')}  
                **📍 Dirección:** {row.get('Dirección','')}  
                **🧼 Servicio:** {row.get('Servicio','')}  
                **📅 Fecha:** {row['Fecha'].strftime('%d/%m/%Y')}  
                **💰 Monto:** ${row.get('Monto', 0):,.0f}  
                **💬 Comentarios:** {row.get('Comentarios con llamada posterior a venta','')}
                """)
            with col2:
                if st.button("✖ Cerrar detalle", use_container_width=True):
                    del st.session_state["evento_seleccionado"]
                    st.rerun()

            tel_ev = str(row.get("Tel", "")).replace("-", "").replace(" ", "")
            if tel_ev and tel_ev != "nan":
                tel_ev = "52" + tel_ev
                mensaje_template = plantillas.get("confirmacion", "Hola {nombre}")
                mensaje = mensaje_template.format(nombre=row.get("Nombre", ""), empresa=empresa)
                url = f"https://wa.me/{tel_ev}?text={urllib.parse.quote(mensaje)}"
                st.markdown(f"[💬 Enviar WhatsApp]({url})")

            # ── EDITAR FECHA ──
            st.markdown("#### ✏️ Corregir fecha del servicio")
            with st.form("editar_fecha_form"):
                nueva_fecha = st.date_input(
                    "Nueva fecha:",
                    value=row["Fecha"].date()
                )
                confirmar_edicion = st.form_submit_button("📅 Cambiar fecha", use_container_width=True)

                if confirmar_edicion:
                    if nueva_fecha == row["Fecha"].date():
                        st.warning("La fecha es la misma, no hay nada que cambiar.")
                    else:
                        try:
                            client = get_gspread_client()
                            sheet_id = st.session_state["SHEET_IDS"][año_click]
                            sh = client.open_by_key(sheet_id)
                            worksheet = sh.get_worksheet(0)

                            celdas = worksheet.findall(str(folio_click))
                            if celdas:
                                fila_num = celdas[0].row
                                # Columna C = Fecha (índice 3)
                                worksheet.update_cell(fila_num, 3, nueva_fecha.strftime("%m/%d/%Y"))
                                st.success(f"✅ Fecha cambiada a {nueva_fecha.strftime('%d/%m/%Y')}")
                                st.cache_data.clear()
                                del st.session_state["evento_seleccionado"]
                                st.session_state["agenda_refresh"] = st.session_state.get("agenda_refresh", 0) + 1
                                import time as t
                                t.sleep(1)
                                st.rerun()
                            else:
                                st.error("No se encontró el servicio en el sheet. Verifica el folio.")
                        except KeyError:
                            st.error(f"No hay sheet configurado para el año {año_click}.")
                        except Exception as e:
                            st.error(f"Error al cambiar fecha: {e}")

            # ── BORRAR SERVICIO ──
            st.markdown("#### 🗑️ Eliminar servicio")
            with st.form("borrar_form"):
                st.warning("Esta acción no se puede deshacer.")
                confirmar_borrado = st.checkbox("Confirmo que quiero eliminar este servicio")
                borrar_btn = st.form_submit_button("🗑️ Eliminar", use_container_width=True)

                if borrar_btn:
                    if not confirmar_borrado:
                        st.error("Marca la casilla de confirmación antes de eliminar.")
                    else:
                        try:
                            client = get_gspread_client()
                            sheet_id = st.session_state["SHEET_IDS"][año_click]
                            sh = client.open_by_key(sheet_id)
                            worksheet = sh.get_worksheet(0)

                            celdas = worksheet.findall(str(folio_click))
                            if celdas:
                                worksheet.delete_rows(celdas[0].row)
                                st.success("✅ Servicio eliminado correctamente.")
                                st.cache_data.clear()
                                st.cache_resource.clear()
                                del st.session_state["evento_seleccionado"]
                                st.session_state["agenda_refresh"] = st.session_state.get("agenda_refresh", 0) + 1
                                import time as t
                                t.sleep(1)
                                st.rerun()
                            else:
                                st.error("No se encontró el servicio en el sheet.")
                        except KeyError:
                            st.error(f"No hay sheet configurado para el año {año_click}.")
                        except Exception as e:
                            st.error(f"Error al eliminar: {e}")
        else:
            # El folio no se encontró — limpiar para no dejar estado sucio
            st.warning("No se encontró el servicio seleccionado. Puede que ya haya sido eliminado.")
            if st.button("Limpiar selección"):
                del st.session_state["evento_seleccionado"]
                st.rerun()
    # ── COTIZACIONES ──
elif pagina == "Cotizaciones":
    import base64
    import streamlit.components.v1 as components

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

        # ── MENSAJE PROFESIONAL ──
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

        # ── PDF ──
        st.markdown("### 📄 Descargar cotización")

        nombre_pdf = nombre_cliente if nombre_cliente else "Cliente"
        fecha_pdf = datetime.now().strftime("%d/%m/%Y")
        empresa_pdf = st.session_state.get("empresa", "")

        filas_pdf = ""
        for p in PAQUETES:
            total_p = sum(i["Precios"][p] for i in st.session_state["items_cotizacion"])
            descuento = DESCUENTOS.get(p, 0)
            total_con_descuento = total_p * (1 - descuento / 100)
            total_final = max(total_con_descuento, MINIMO)

            servicios_html = ""
            for item in st.session_state["items_cotizacion"]:
                servicios_html += f"""
                <tr>
                    <td style='padding:6px 12px; border-bottom:1px solid #eee;'>
                        {item['Servicio']} ({item['Cantidad']} {item['Label']})
                    </td>
                    <td style='padding:6px 12px; text-align:right; border-bottom:1px solid #eee;'>
                        ${item['Precios'][p]:,.0f}
                    </td>
                </tr>
                """

            if incluir_purt and PURT_COSTO > 0:
                servicios_html += f"""
                <tr>
                    <td style='padding:6px 12px; border-bottom:1px solid #eee;'>PURT</td>
                    <td style='padding:6px 12px; text-align:right; border-bottom:1px solid #eee;'>
                        ${PURT_COSTO:,.0f}
                    </td>
                </tr>
                """

            if descuento > 0:
                servicios_html += f"""
                <tr>
                    <td style='padding:6px 12px; border-bottom:1px solid #eee; color:#888;'>
                        Descuento {descuento}%
                    </td>
                    <td style='padding:6px 12px; text-align:right; border-bottom:1px solid #eee; color:#888;'>
                        -${total_p * descuento / 100:,.0f}
                    </td>
                </tr>
                """

            desc_paquete_html = f"<p style='color:#555; font-size:13px; margin:4px 0 8px 0;'>{DESC_PAQUETES[p]}</p>" if p in DESC_PAQUETES else ""

            filas_pdf += f"""
            <div style="margin-bottom:24px; border:1px solid #ddd; border-radius:8px; overflow:hidden;">
                <div style="background:#2B5BAA; color:white; padding:10px 16px; font-weight:bold; font-size:15px;">
                    Paquete {p}
                </div>
                <div style="padding:8px 12px;">
                    {desc_paquete_html}
                </div>
                <table style="width:100%; border-collapse:collapse; font-size:14px;">
                    {servicios_html}
                    <tr style="background:#f0f4ff;">
                        <td style="padding:10px 12px; font-weight:bold;">TOTAL</td>
                        <td style="padding:10px 12px; text-align:right; font-weight:bold; font-size:16px;">
                            ${total_final:,.0f}
                        </td>
                    </tr>
                </table>
            </div>
            """

        intro_html = f"<p style='margin-bottom:16px;'>{INTRO}</p>" if INTRO else ""
        purt_html = f"<p style='margin-bottom:16px; color:#555;'>{PURT_DESC}</p>" if (incluir_purt and PURT_DESC) else ""
        cierre_html = f"<p style='margin-top:8px;'>{CIERRE}</p>" if CIERRE else ""
        firma_html = f"<p style='margin-top:4px; color:#555;'>{FIRMA}</p>" if FIRMA else ""

        html_pdf = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <title>Cotización — {nombre_pdf}</title>
            <style>
                body {{
                    font-family: Arial, sans-serif;
                    padding: 48px;
                    max-width: 680px;
                    margin: auto;
                    color: #333;
                    font-size: 14px;
                }}
                h1 {{ color: #2B5BAA; margin-bottom: 4px; font-size: 28px; }}
                .meta {{ color: #666; font-size: 13px; margin-bottom: 24px; line-height: 1.8; }}
                .divider {{ border: none; border-top: 1px solid #eee; margin: 24px 0; }}
                .footer {{ margin-top: 40px; font-size: 13px; color: #888;
                           border-top: 1px solid #eee; padding-top: 16px; }}
                @media print {{
                    body {{ padding: 24px; }}
                }}
            </style>
        </head>
        <body>
            <h1>Cotización de servicios</h1>
            <div class="meta">
                <strong>Para:</strong> {nombre_pdf}<br>
                <strong>De:</strong> {empresa_pdf}<br>
                <strong>Fecha:</strong> {fecha_pdf}
            </div>

            <hr class="divider">

            {intro_html}
            {purt_html}

            <p style="margin-bottom:20px;">
                El servicio de acuerdo a su solicitud tiene una inversión de:
            </p>

            {filas_pdf}

            <div class="footer">
                {cierre_html}
                {firma_html}
            </div>
        </body>
        </html>
        """

        b64_pdf = base64.b64encode(html_pdf.encode("utf-8")).decode("utf-8")
        nombre_archivo = f"cotizacion_{nombre_pdf.replace(' ', '_')}_{datetime.now().strftime('%d%m%Y')}.html"

        components.html(f"""
        <a href="data:text/html;base64,{b64_pdf}"
           download="{nombre_archivo}"
           style="
               display:block;
               background-color:#2B5BAA;
               color:white;
               text-decoration:none;
               text-align:center;
               border-radius:8px;
               padding:14px 24px;
               font-size:16px;
               font-family:Arial, sans-serif;
               margin-top:8px;
           ">
            📄 Descargar cotización
        </a>
        """, height=65)

        st.caption("Se descarga como archivo HTML. Ábrelo en el navegador y usa Cmd+P / Ctrl+P → Guardar como PDF.")

        st.markdown("---")

        if st.button("Limpiar cotización", use_container_width=True):
            st.session_state["items_cotizacion"] = []
            st.rerun()