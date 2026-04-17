import pandas as pd
import streamlit as st
from datetime import datetime, timedelta
import gspread
from google.oauth2.service_account import Credentials
from config import USUARIOS
import uuid

st.set_page_config(
    page_title="Chem-Dry Dashboard",
    page_icon="🧹",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
<style>
    [data-testid="stSidebar"] { background-color: #2B5BAA; }
    [data-testid="stSidebar"] * { color: white !important; }
    [data-testid="stMetric"] {
        background: #f8f9fa;
        border-radius: 12px;
        padding: 16px;
        border-left: 4px solid #2B5BAA;
    }
    [data-testid="stMetricValue"] {
        font-size: clamp(14px, 2vw, 28px) !important;
    }
    h1 { color: #2B5BAA; }
    h2, h3 { color: #1a3d6e; }
    .stButton > button {
        background-color: #2B5BAA;
        color: white;
        border: none;
        border-radius: 8px;
        padding: 10px 24px;
        font-size: 16px;
        width: 100%;
    }
    .stButton > button:hover { background-color: #1a3d6e; }
</style>
""", unsafe_allow_html=True)

# ── GOOGLE SHEETS ──
SHEET_IDS = {
    2022: "1L3wzHhc6_sN7h361uqXFI7lKzGobl_vtuHEDVTbCEdc",
    2023: "1e7B1Hp5zWJ3kLSS6d8CQoESYsaDWyIrFhIGcSRJE_Ag",
    2024: "1cVfveU9err9N6RI23OOHEABV8m8Rj9wRkO3F27o6TAg",
    2025: "1IodGW1K7c7GQBa90k6O8YCFOtwt3sA2PDFa7mmOkZ0E",
    2026: "1mqcHNhQEjEhKYYuY6iDOVpmPDH7br0VJITxdVx7wzls",
}

@st.cache_resource
def get_gspread_client():
    scopes = [
        "https://www.googleapis.com/auth/spreadsheets.readonly",
        "https://www.googleapis.com/auth/drive.readonly"
    ]
    creds = Credentials.from_service_account_info(
        dict(st.secrets["google_credentials"]),
        scopes=scopes
    )
    return gspread.authorize(creds)

import time

@st.cache_data(ttl=300)
def cargar_datos():
    client = get_gspread_client()
    dfs = []

    for año, sheet_id in SHEET_IDS.items():
        for intento in range(3):  # 🔥 retry automático
            try:
                sh = client.open_by_key(sheet_id)
                worksheet = sh.get_worksheet(0)
                data = worksheet.get_all_records()
                df = pd.DataFrame(data)

                if df.empty:
                    break

                df["Año"] = año
                dfs.append(df)

                time.sleep(1)  # 🔥 evita saturar Google
                break

            except Exception as e:
                if intento < 2:
                    time.sleep(2)  # 🔥 espera antes de reintentar
                else:
                    st.error(f"Error cargando {año}: {e}")

    if not dfs:
        return pd.DataFrame()

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
        st.markdown("<h1 style='text-align:center; color:#2B5BAA;'>Chem-Dry</h1>", unsafe_allow_html=True)
        st.markdown("<h3 style='text-align:center; color:#2B5BAA;'>Dashboard</h3>", unsafe_allow_html=True)
        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown("<h4 style='text-align:center; color:#1a3d6e;'>Iniciar sesión</h4>", unsafe_allow_html=True)
        usuario = st.text_input("Usuario", placeholder="Tu usuario")
        password = st.text_input("Contraseña", type="password", placeholder="Tu contraseña")
        st.markdown("""
        <script>
        document.addEventListener("keydown", function(e) {
            if(e.key === "Enter") {
                const buttons = window.parent.document.querySelectorAll("button");
                buttons.forEach(b => { if(b.innerText === "Entrar") b.click(); });
            }
        });
        </script>
        """, unsafe_allow_html=True)
        if st.button("Entrar"):
            if usuario in USUARIOS and USUARIOS[usuario]["password"] == password:
                st.session_state["usuario"] = usuario
                st.session_state["nombre"] = USUARIOS[usuario]["nombre"]
                st.rerun()
            else:
                st.error("Usuario o contraseña incorrectos")

if "usuario" not in st.session_state:
    login()
    st.stop()

# ── CARGAR DATOS ──
df = cargar_datos()

if df is not None and not df.empty:
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
    años_disponibles = sorted(df["Año"].unique())
    años_sin_2026 = años_disponibles

    # ── SIDEBAR ──
    with st.sidebar:
        st.markdown(f"<h3 style='color:white'>{st.session_state['nombre']}</h3>", unsafe_allow_html=True)
        st.markdown("---")

        paginas = ["Resumen", "Ventas", "Clientes", "Servicios", "Follow Up", "Agenda", "Comentarios", "Cotizaciones"]

        if "pagina" not in st.session_state:
            st.session_state["pagina"] = "Resumen"

        for p in paginas:
            if st.button(p, key=p, use_container_width=True):
                st.session_state["pagina"] = p

        st.markdown("---")
        st.caption("Datos actualizados cada 5 min")
        if st.button("Actualizar datos", use_container_width=True):
            st.cache_data.clear()
            st.rerun()
        st.markdown("---")
        if st.button("Cerrar sesión", use_container_width=True):
            for key in list(st.session_state.keys()):
                del st.session_state[key]
            st.rerun()

    pagina = st.session_state["pagina"]

    # ── RESUMEN ──
    if pagina == "Resumen":
        st.title("Dashboard Chem-Dry")
        año_resumen = st.selectbox("Año:", años_sin_2026, index=len(años_sin_2026)-1)
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
            st.markdown(f"<p style='color:{color}; font-size:16px'>{simbolo} Comparado con {año_resumen-1}: ${abs(diferencia):,.0f} ({porcentaje:+.1f}%)</p>", unsafe_allow_html=True)

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
            df_f = df[df["Año"].isin(años_sel)]
            pivot = df_f.groupby(["Año","Mes"])["Monto"].sum().reset_index()
            pivot = pivot.pivot(index="Mes", columns="Año", values="Monto").fillna(0)
            st.line_chart(pivot)

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
        nombres_meses = {1:"Enero",2:"Febrero",3:"Marzo",4:"Abril",5:"Mayo",6:"Junio",
                        7:"Julio",8:"Agosto",9:"Septiembre",10:"Octubre",11:"Noviembre",12:"Diciembre"}
        resumen_meses = []
        for m in range(1, mes_actual + 1):
            v2025 = df[(df["Año"]==2025) & (df["Mes"]==m)]["Monto"].sum()
            v2026 = df[(df["Año"]==2026) & (df["Mes"]==m)]["Monto"].sum() if 2026 in df["Año"].values else 0
            diff = v2026 - v2025
            pct = ((diff / v2025) * 100) if v2025 > 0 else 0
            resumen_meses.append({
                "Mes": nombres_meses[m],
                "2025": f"${v2025:,.0f}",
                "2026": f"${v2026:,.0f}",
                "Diferencia": f"${diff:,.0f}",
                "Variación": f"{pct:+.1f}%"
            })
        st.dataframe(pd.DataFrame(resumen_meses), use_container_width=True, hide_index=True)

    # ── CLIENTES ──
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

        # 🔥 NORMALIZAR
        df_o["Origen"] = df_o["Origen"].replace({
            "int": "Internet",
            "internet": "Internet",
            "rep": "Repetición",
            "repeticion": "Repetición",
            "rec": "Recomendación",
            "recomendacion": "Recomendación",
            "ref": "Recomendación",
            "face": "Facebook",
            "amigo": "Amigo",
            "amigos": "Amigo",
            "club": "Club",
            "primo": "Primo",
            "maristas": "Maristas"
        })

        df_o["Origen"] = df_o["Origen"].replace(["", "nan"], "Sin especificar")

        # 🔥 GRÁFICA
        origen = df_o["Origen"].value_counts().reset_index()
        origen.columns = ["Canal", "Clientes"]

        st.bar_chart(origen.set_index("Canal"))
        st.dataframe(origen, use_container_width=True)

        # ─────────────────────────────
        # 🧠 HISTORIAL DE CLIENTES (PRO)
        # ─────────────────────────────
        st.markdown("### 🧠 Historial de clientes")

        df_hist = df.copy()
        df_hist["Monto"] = pd.to_numeric(df_hist["Monto"], errors="coerce")
        df_hist["Fecha"] = pd.to_datetime(df_hist["Fecha"], errors="coerce")

        # 🔥 AGRUPAR CLIENTES
        historial = df_hist.groupby("Nombre").agg(
            Total_Gastado=("Monto", "sum"),
            Servicios=("Monto", "count"),
            Ultima_Visita=("Fecha", "max"),
            Ticket_Promedio=("Monto", "mean")
        ).reset_index()

        historial = historial.sort_values(by="Total_Gastado", ascending=False)

        # 🔍 BUSCADOR (BIEN PUESTO)
        cliente_buscar = st.text_input(
            "🔍 Buscar cliente",
            key=f"buscador_historial_{año_origen}"
        )

        if cliente_buscar:
            historial = historial[
                historial["Nombre"].str.contains(cliente_buscar, case=False, na=False)
            ]

        # 🔥 FORMATO
        historial["Ultima_Visita"] = historial["Ultima_Visita"].dt.strftime("%d/%m/%Y")

        # 🔥 TOP CLIENTES (VISUAL PRO)
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

# 🔥 TABLA
        st.dataframe(historial, use_container_width=True)

        # PERFIL DEL CLIENTE A DETALLE
        st.markdown("### 👤 Perfil del cliente")

        clientes_lista = historial["Nombre"].dropna().unique().tolist()

        cliente_sel = st.selectbox("Selecciona un cliente", clientes_lista)

        if cliente_sel:
            df_cliente = df[df["Nombre"] == cliente_sel].copy()

            df_cliente["Fecha"] = pd.to_datetime(df_cliente["Fecha"], errors="coerce")
            df_cliente["Monto"] = pd.to_numeric(df_cliente["Monto"], errors="coerce")

            df_cliente = df_cliente.sort_values(by="Fecha", ascending=False)

    # 🔥 MÉTRICAS
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
                "Fecha",
                "Servicio",
                "Monto",
                "Origen",
                "Comentarios con llamada posterior a venta"
            ]].copy()

            mostrar.columns = ["Fecha", "Servicio", "Monto", "Origen", "Comentarios"]

            st.dataframe(mostrar, use_container_width=True)
        # ─────────────────────────────
# 🔴 CLIENTES PERDIDOS (PRO)
# ─────────────────────────────
        st.markdown("## 🔴 Oportunidades de recuperación")

        df_lost = df.copy()
        df_lost["Fecha"] = pd.to_datetime(df_lost["Fecha"], errors="coerce")
        df_lost["Monto"] = pd.to_numeric(df_lost["Monto"], errors="coerce")

        hoy = datetime.now()

        # Última visita + valor total
        ultimo = df_lost.groupby("Nombre").agg(
            Ultima_Visita=("Fecha", "max"),
            Total_Gastado=("Monto", "sum"),
            Tel=("Tel", "last")
        ).reset_index()

        # Calcular meses sin servicio
        ultimo["Meses_sin_servicio"] = ((hoy - ultimo["Ultima_Visita"]).dt.days / 30).round(1)

        # 🔥 FILTROS DINÁMICOS (PRO)
        col1, col2 = st.columns(2)

        with col1:
            meses_min = st.slider("Meses sin servicio", 3, 24, 6)

        with col2:
            monto_min = st.number_input("Monto mínimo ($)", value=1500)

        # Aplicar filtros
        perdidos = ultimo[
            (ultimo["Meses_sin_servicio"] >= meses_min) &
            (ultimo["Total_Gastado"] >= monto_min)
        ]

        perdidos = perdidos.sort_values(by="Total_Gastado", ascending=False)

        # 🔥 MÉTRICAS CLAVE
        col1, col2, col3 = st.columns(3)

        col1.metric("Clientes recuperables", len(perdidos))
        col2.metric("Dinero en riesgo", f"${perdidos['Total_Gastado'].sum():,.0f}")
        col3.metric("Meses promedio sin servicio", f"{perdidos['Meses_sin_servicio'].mean():.1f}" if not perdidos.empty else "0")

        st.markdown("### 📋 Lista priorizada")

        st.dataframe(
            perdidos[["Nombre", "Tel", "Total_Gastado", "Meses_sin_servicio"]],
            use_container_width=True
        )

        # 🔥 ACCIÓN DIRECTA (WhatsApp)
        st.markdown("### 💬 Contacto rápido")

        if not perdidos.empty:

            # 🔥 SELECTOR DE CLIENTE
            cliente_sel = st.selectbox(
                "Selecciona cliente",
                perdidos["Nombre"],
                key="select_contacto"
                )

            cliente_data = perdidos[perdidos["Nombre"] == cliente_sel].iloc[0]

                # 🔥 LIMPIAR TEL
            tel = str(cliente_data["Tel"]).replace("-", "").replace(" ", "")
            if tel:
                    tel = "52" + tel

                # 🔥 MENSAJE EDITABLE
            mensaje = st.text_area(
                "Mensaje",
                value=f"Hola {cliente_sel}, hace tiempo que no realizamos un servicio contigo. Tenemos disponibilidad esta semana, ¿te gustaría agendar?",
                key="mensaje_contacto"
            )

                # 🔥 GENERAR LINK
            if tel:
                url = f"https://wa.me/{tel}?text={mensaje.replace(' ', '%20')}"
                    
                st.markdown(f"[💬 Abrir WhatsApp]({url})")
            else:
                st.warning("Este cliente no tiene teléfono válido")

        else:
            st.info("No hay clientes en este filtro")
        # ─────────────────────────────
        # ➕ AGREGAR CLIENTE
        # ─────────────────────────────
        st.markdown("### ➕ Agregar nuevo cliente")
        st.markdown("### 📂 Seleccionar destino")

        año_destino = st.selectbox(
            "Guardar cliente en el año:",
            list(SHEET_IDS.keys()),
            index=len(SHEET_IDS)-1
        )

        with st.form("nuevo_cliente"):
            nombre = st.text_input("Nombre")
            telefono = st.text_input("Teléfono")
            direccion = st.text_input("Dirección")
            servicio = st.text_input("Servicio")
            fecha = st.date_input("Fecha del servicio")
            monto = st.number_input("Monto", min_value=0)

            submitted = st.form_submit_button("Guardar cliente")

            if submitted:
                try:
                    client = get_gspread_client()
                    sheet_id = SHEET_IDS[año_destino]
                    sh = client.open_by_key(sheet_id)
                    worksheet = sh.get_worksheet(0)

                    nueva_fila = [
                        "",
                        "",
                        fecha.strftime("%d/%m/%Y"),
                        nombre,
                        telefono,
                        direccion,
                        "Manual",
                        monto,
                        servicio,
                        "", "", "", ""
                    ]

                    worksheet.append_row(nueva_fila)

                    st.success("✅ Cliente agregado correctamente")
                    st.cache_data.clear()
                    st.rerun()

                except Exception as e:
                    st.error(f"Error al guardar: {e}")

        # ─────────────────────────────
        # ❌ ELIMINAR CLIENTE
        # ─────────────────────────────
        st.markdown("### ❌ Eliminar cliente")

        nombres_clientes = df_o["Nombre"].dropna().unique().tolist()

        cliente_eliminar = st.selectbox("Selecciona cliente:", nombres_clientes)

        if st.button("Eliminar cliente"):
            try:
                client = get_gspread_client()
                sheet_id = SHEET_IDS[año_origen]
                sh = client.open_by_key(sheet_id)
                worksheet = sh.get_worksheet(0)

                data = worksheet.get_all_values()
                fila_a_borrar = None

                for i, row in enumerate(data):
                    if len(row) > 3 and row[3] == cliente_eliminar:
                        fila_a_borrar = i + 1
                        break

                if fila_a_borrar:
                    worksheet.delete_rows(fila_a_borrar)
                    st.success(f"✅ Cliente '{cliente_eliminar}' eliminado")
                    st.cache_data.clear()
                    st.rerun()
                else:
                    st.warning("No se encontró el cliente en el Sheet")

            except Exception as e:
                st.error(f"Error eliminando: {e}")
        # ── SERVICIOS ──
        elif pagina == "Servicios":
            st.title("Servicios más vendidos")
            año_serv = st.selectbox("Año:", años_sin_2026)
            df_s = df[df["Año"] == año_serv].copy()

            def categorizar(servicio):
                if pd.isna(servicio): return "Sin especificar"
                s = str(servicio).lower()
                if "alfombra" in s: return "Alfombra"
                if "sala" in s: return "Sala"
                if "colchón" in s or "colchon" in s: return "Colchon"
                if "tapete" in s: return "Tapete"
                if "silla" in s: return "Sillas"
                if "auto" in s or "interior" in s: return "Interior auto"
                if "futón" in s or "futon" in s: return "Futon"
                return "Otro"

            df_s["Categoria"] = df_s["Servicio"].apply(categorizar)
            cats = df_s["Categoria"].value_counts().reset_index()
            cats.columns = ["Categoria", "Cantidad"]
            st.bar_chart(cats.set_index("Categoria"))
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
            mes_filtro = st.selectbox("Mes del último servicio:",
                ["Todos","Enero","Febrero","Marzo","Abril","Mayo","Junio",
                 "Julio","Agosto","Septiembre","Octubre","Noviembre","Diciembre"])

        fecha_limite = datetime.now() - timedelta(days=meses*30)
        sin_servicio = ultimo[ultimo["Ultimo servicio"] < fecha_limite].copy()

        meses_dict = {"Enero":1,"Febrero":2,"Marzo":3,"Abril":4,"Mayo":5,"Junio":6,
                      "Julio":7,"Agosto":8,"Septiembre":9,"Octubre":10,"Noviembre":11,"Diciembre":12}

        if mes_filtro != "Todos":
            sin_servicio = sin_servicio[
                sin_servicio["Ultimo servicio"].dt.month == meses_dict[mes_filtro]
            ]

        sin_servicio = sin_servicio.sort_values("Ultimo servicio")
        st.metric("Clientes a contactar", len(sin_servicio))
        st.dataframe(sin_servicio, use_container_width=True)
        import urllib.parse

        st.markdown("### Enviar mensaje por WhatsApp")

        if not sin_servicio.empty:
    # Selector de cliente (nombre + teléfono para evitar duplicados)
                cliente_sel = st.selectbox(
                    "Selecciona cliente:",
                    sin_servicio.apply(lambda x: f"{x['Nombre']} - {x['Tel']}", axis=1)
    )

    # Separar datos
                nombre = cliente_sel.split(" - ")[0]
                telefono = cliente_sel.split(" - ")[1].replace("-", "").replace(" ", "")

    # Mensaje
                mensaje = f"""Hola {nombre}, te saluda Chem-Dry 👋

Solo para darte seguimiento a tu último servicio.

¿Te gustaría agendar otra limpieza o mantenimiento?

Quedamos atentos 😊"""

    # Codificar mensaje para URL
                mensaje_encoded = urllib.parse.quote(mensaje)

    # Crear link de WhatsApp
                whatsapp_url = f"https://wa.me/52{telefono}?text={mensaje_encoded}"

    # Botón
                st.link_button("Enviar mensaje por WhatsApp", whatsapp_url)
    # AGENDA
    elif pagina == "Agenda":
        st.title("📅 Agenda de Servicios")

        df_a = df.copy()
        df_a["Fecha"] = pd.to_datetime(df_a["Fecha"], errors="coerce")

        # ─────────────────────────────
        # ➕ AGENDAR SERVICIO
        # ─────────────────────────────
        st.markdown("### ➕ Agendar nuevo servicio")

        clientes_existentes = df_a["Nombre"].dropna().unique().tolist()

        with st.form("agendar_servicio"):
            cliente_sel = st.selectbox("Cliente existente (opcional)", [""] + clientes_existentes)

            nombre = st.text_input("Nombre del cliente", value=cliente_sel)
            telefono = st.text_input("Teléfono")
            direccion = st.text_input("Dirección")
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
                    sheet_id = SHEET_IDS[fecha.year]
                    sh = client.open_by_key(sheet_id)
                    worksheet = sh.get_worksheet(0)

                    folio = str(int(datetime.now().timestamp()))

                    nueva_fila = [
                        folio,
                        "",
                        fecha.strftime("%d/%m/%Y"),
                        nombre,
                        telefono,
                        direccion,
                        "Agenda",
                        monto,
                        servicio,
                        "", "", "", ""
                    ]

                    worksheet.append_row(nueva_fila)

                    st.success("✅ Servicio agendado correctamente")
                    st.cache_data.clear()
                    st.rerun()

                except Exception as e:
                    st.error(f"Error al agendar: {e}")

        st.markdown("---")

        # ─────────────────────────────
        # 📅 VER AGENDA
        # ─────────────────────────────
        fecha_sel = st.date_input("Selecciona una fecha", datetime.now())

        df_dia = df_a[df_a["Fecha"].dt.date == fecha_sel]

        st.metric("Servicios ese día", len(df_dia))

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
                    """)

                    # 🔥 BOTÓN WHATSAPP
                    tel = str(row.get("Tel","")).replace("-", "").replace(" ", "")
                    if tel:
                        tel = "52" + tel

                        mensaje = f"Hola {row.get('Nombre','')}, confirmamos tu servicio Chem-Dry para hoy."
                        url = f"https://wa.me/{tel}?text={mensaje.replace(' ', '%20')}"

                        st.markdown(f"[💬 Enviar WhatsApp]({url})")

                    st.markdown("---")

    # ── COMENTARIOS ──
    elif pagina == "Comentarios":
        st.title("Comentarios de clientes")
        año_com = st.selectbox("Año:", años_sin_2026)
        buscar = st.text_input("Buscar por nombre o comentario:")
        df_c = df[(df["Año"]==año_com) & (df["Comentarios con llamada posterior a venta"].notna())].copy()
        df_c = df_c[["Nombre","Fecha","Comentarios con llamada posterior a venta"]]
        df_c.columns = ["Cliente","Fecha","Comentario"]
        df_c = df_c[df_c["Comentario"].astype(str).str.strip() != ""]
        if buscar:
            df_c = df_c[
                df_c["Cliente"].str.contains(buscar, case=False, na=False) |
                df_c["Comentario"].str.contains(buscar, case=False, na=False)
            ]
        st.write(f"**{len(df_c)} comentarios**")
        st.dataframe(df_c, use_container_width=True)

    # ── COTIZACIONES ──
    elif pagina == "Cotizaciones":
        st.title("Cotizador de Servicios")

        PAQUETES = ["Healthy", "Premium", "Protección", "Ecológico", "Sencillo"]
        MINIMO = 950

        PRECIOS = {
            "Alfombra (por m2)": {"Healthy": 127, "Premium": 91, "Protección": 76, "Ecológico": 57, "Sencillo": 49},
            "Tapete Oriental / Lana": {"Healthy": 413, "Premium": 359, "Protección": 328, "Ecológico": 254, "Sencillo": 235},
            "Tapete Sintético": {"Healthy": 232, "Premium": 196, "Protección": 167, "Ecológico": 149, "Sencillo": 132},
            "Tapete Seda o Algodón": {"Healthy": 659, "Premium": 625, "Protección": 587, "Ecológico": 454, "Sencillo": 375},
            "Mueble - Asiento y Respaldo Fijos": {"Healthy": 526, "Premium": 434, "Protección": 382, "Ecológico": 274, "Sencillo": 202},
            "Mueble - Solo Asiento o Respaldo": {"Healthy": 583, "Premium": 515, "Protección": 417, "Ecológico": 308, "Sencillo": 245},
            "Mueble - Asiento + Respaldo Removible": {"Healthy": 649, "Premium": 568, "Protección": 485, "Ecológico": 362, "Sencillo": 289},
            "Mueble - Chaise Lounge": {"Healthy": 656, "Premium": 559, "Protección": 455, "Ecológico": 369, "Sencillo": 281},
            "Taburete / Puff": {"Healthy": 306, "Premium": 251, "Protección": 203, "Ecológico": 138, "Sencillo": 99},
            "Reposet o Recliner": {"Healthy": 691, "Premium": 581, "Protección": 486, "Ecológico": 372, "Sencillo": 308},
            "Silla de Oficina (tela)": {"Healthy": 220, "Premium": 179, "Protección": 149, "Ecológico": 125, "Sencillo": 116},
            "Sillón Ejecutivo (tela)": {"Healthy": 304, "Premium": 233, "Protección": 202, "Ecológico": 165, "Sencillo": 161},
            "Silla Comedor - Solo Asiento o Respaldo (tela)": {"Healthy": 153, "Premium": 123, "Protección": 108, "Ecológico": 87, "Sencillo": 78},
            "Silla Comedor - Asiento + Respaldo (tela)": {"Healthy": 220, "Premium": 160, "Protección": 136, "Ecológico": 111, "Sencillo": 104},
            "Mampara (por m2)": {"Healthy": 135, "Premium": 101, "Protección": 83, "Ecológico": 72, "Sencillo": 67},
            "Auto Pequeño (Tsuru, Ikon, Chevy)": {"Healthy": 2163, "Premium": 1906, "Protección": 1617, "Ecológico": 1370, "Sencillo": 1283},
            "Auto Mediano (Jetta, Accord, Focus)": {"Healthy": 2312, "Premium": 2163, "Protección": 1854, "Ecológico": 1597, "Sencillo": 1539},
            "Auto Grande (Lincoln, Cadillac)": {"Healthy": 2575, "Premium": 2266, "Protección": 2009, "Ecológico": 1751, "Sencillo": 1742},
            "Camioneta (hasta 3 filas)": {"Healthy": 2781, "Premium": 2575, "Protección": 2369, "Ecológico": 2163, "Sencillo": 2228},
            "Camioneta Pick Up": {"Healthy": 1920, "Premium": 1755, "Protección": 1527, "Ecológico": 1299, "Sencillo": 1452},
            "Camioneta Pick Up Doble Cabina": {"Healthy": 2313, "Premium": 2093, "Protección": 1813, "Ecológico": 1521, "Sencillo": 1553},
            "Colchón Cuna / Corral": {"Healthy": 631, "Premium": 529, "Protección": 493, "Ecológico": 368, "Sencillo": 324},
            "Colchón Individual": {"Healthy": 1177, "Premium": 1065, "Protección": 896, "Ecológico": 734, "Sencillo": 648},
            "Colchón Matrimonial": {"Healthy": 1464, "Premium": 1179, "Protección": 1115, "Ecológico": 915, "Sencillo": 821},
            "Colchón Queen Size": {"Healthy": 1563, "Premium": 1381, "Protección": 1239, "Ecológico": 1050, "Sencillo": 974},
            "Colchón King Size": {"Healthy": 1757, "Premium": 1555, "Protección": 1391, "Ecológico": 1154, "Sencillo": 1026},
        }

        SERVICIOS_CON_CANTIDAD = ["Alfombra (por m2)", "Tapete Oriental / Lana", "Tapete Sintético", "Tapete Seda o Algodón", "Mampara (por m2)"]
        SERVICIOS_CON_PLAZAS = ["Mueble - Asiento y Respaldo Fijos", "Mueble - Solo Asiento o Respaldo", "Mueble - Asiento + Respaldo Removible", "Mueble - Chaise Lounge", "Taburete / Puff", "Reposet o Recliner"]
        SERVICIOS_CON_SILLAS = ["Silla de Oficina (tela)", "Sillón Ejecutivo (tela)", "Silla Comedor - Solo Asiento o Respaldo (tela)", "Silla Comedor - Asiento + Respaldo (tela)"]

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
                st.write("")

        precio_data = {"Paquete": PAQUETES, "Precio": [f"${PRECIOS[servicio][p] * cantidad:,.0f}" for p in PAQUETES]}
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
                total_p = sum(item["Precios"][p] for item in st.session_state["items_cotizacion"])
                total_p_final = max(total_p, MINIMO)
                nota = " *" if total_p < MINIMO else ""
                totales[p] = f"${total_p_final:,.0f}{nota}"
            filas.append(totales)

            st.dataframe(pd.DataFrame(filas), use_container_width=True, hide_index=True)

            hay_minimo = any(
                sum(item["Precios"][p] for item in st.session_state["items_cotizacion"]) < MINIMO
                for p in PAQUETES
            )
            if hay_minimo:
                st.warning(f"Los paquetes marcados con * aplican mínimo de servicio de ${MINIMO:,.0f} MXN")

            st.markdown("### Mensaje para cliente")
            nombre_cliente = st.text_input("Nombre del cliente (opcional):")

            lineas = []
            if nombre_cliente:
                lineas.append(f"Estimado/a {nombre_cliente},")
                lineas.append("")
            lineas.append("Le compartimos la cotización de nuestros servicios Chem-Dry:")
            lineas.append("")
            for item in st.session_state["items_cotizacion"]:
                lineas.append(f"• {item['Servicio']} ({item['Cantidad']} {item['Label']})")
            lineas.append("")
            lineas.append("Precios por paquete:")
            lineas.append("")
            for p in PAQUETES:
                total_p = sum(item["Precios"][p] for item in st.session_state["items_cotizacion"])
                total_p_final = max(total_p, MINIMO)
                nota = " (mínimo de servicio aplicado)" if total_p < MINIMO else ""
                lineas.append(f"  {p}: ${total_p_final:,.0f}{nota}")
            lineas.append("")
            lineas.append("Todos nuestros paquetes incluyen limpieza profunda con tecnología Chem-Dry.")
            lineas.append("¿Le agendamos una visita?")

            st.text_area("Copia este mensaje:", "\n".join(lineas), height=280)

            if st.button("Limpiar cotización", use_container_width=True):
                st.session_state["items_cotizacion"] = []
                st.rerun()