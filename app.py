import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from datetime import datetime

# ==========================================
# 1. CONFIGURACIÓN DE LA PÁGINA Y ESTILO
# ==========================================
st.set_page_config(page_title="Estellé Parquet - Seguimiento", page_icon="🏗️", layout="centered")

st.markdown("""
    <style>
    .stApp { background-color: #fdfaf4; }
    .stButton>button { 
        background-color: #6a5acd; color: white; width: 100%; 
        border-radius: 8px; height: 3.5em; font-weight: bold; border: none;
    }
    h1 { color: #6a5acd; text-align: center; margin-bottom: 0px; }
    .subtext { text-align: center; color: #888; font-size: 0.9em; margin-bottom: 30px; letter-spacing: 2px; }
    </style>
    """, unsafe_allow_html=True)

# ==========================================
# 2. CONEXIÓN Y DIAGNÓSTICO DE PESTAÑAS
# ==========================================
try:
    conn = st.connection("gsheets", type=GSheetsConnection)
    
    # Intentamos leer la configuración
    # Si falla, el bloque 'except' nos dirá qué pestañas existen realmente
    projects_df = conn.read(worksheet="Projectes")
    templates_df = conn.read(worksheet="Config_Templates")
    
except Exception as e:
    st.error("❌ ERROR DE LECTURA: No se encuentra la pestaña 'Projectes' o 'Config_Templates'")
    st.write("El robot ha entrado en el archivo, pero no reconoce los nombres de las pestañas.")
    
    # BOTÓN DE AYUDA: Esto intentará listar tus pestañas reales
    if st.button("🔍 Ver nombres reales de mis pestañas"):
        try:
            # Forzamos una lectura sin nombre para ver qué hay
            all_data = conn.read() 
            st.info("Revisa si tus pestañas tienen espacios o nombres distintos en el Excel.")
        except:
            st.warning("No se han podido listar. Revisa manualmente que los nombres sean exactos.")
    st.stop()

# ==========================================
# 3. INTERFAZ DE USUARIO (DYNAMICS)
# ==========================================
st.title("🏗️ Seguimiento de Obra")
st.markdown("<div class='subtext'>ESTELLÉ PARQUET</div>", unsafe_allow_html=True)

col_h1, col_h2 = st.columns(2)
with col_h1:
    project_sel = st.selectbox("Proyecto", projects_df['Nom'].dropna().unique())
    dades_proj = projects_df[projects_df['Nom'] == project_sel].iloc[0]
with col_h2:
    tipus_sel = st.selectbox("Tipo de Trabajo", templates_df['Tipus'].dropna().unique())
    config = templates_df[templates_df['Tipus'] == tipus_sel].iloc[0]

# Logo del Cliente
if pd.notna(dades_proj['Logo_Client']) and str(dades_proj['Logo_Client']).startswith("http"):
    st.image(dades_proj['Logo_Client'], width=100)

with st.form("main_form"):
    st.subheader(f"Informe Diario: {tipus_sel}")
    
    c1, c2, c3 = st.columns(3)
    v1, v2, v3 = 0.0, 0.0, 0.0
    
    # Solo mostramos inputs si el campo tiene nombre en el Sheets
    with c1:
        if pd.notna(config['Camp1']) and config['Camp1'] != "":
            v1 = st.number_input(f"{config['Camp1']}", min_value=0.0, step=0.1, format="%.1f")
    with c2:
        if pd.notna(config['Camp2']) and config['Camp2'] != "":
            v2 = st.number_input(f"{config['Camp2']}", min_value=0.0, step=0.1, format="%.1f")
    with c3:
        if pd.notna(config['Camp3']) and config['Camp3'] != "":
            v3 = st.number_input(f"{config['Camp3']}", min_value=0.0, step=0.1, format="%.1f")
            
    comentaris = st.text_area("Comentarios de la jornada", height=120)
    responsable = st.text_input("Responsable", value="Luis")
    
    submit = st.form_submit_button("FINALIZAR Y ENVIAR")

# ==========================================
# 4. GUARDADO Y ENVÍO
# ==========================================
if submit:
    with st.spinner("Guardando datos..."):
        try:
            # 1. ACTUALIZAR GOOGLE SHEETS
            seguiment_df = conn.read(worksheet="Seguiment")
            nueva_fila = pd.DataFrame([{
                "Data": datetime.now().strftime("%d/%m/%Y %H:%M"),
                "Projecte": project_sel, "Tipus": tipus_sel,
                "Dada1": v1, "Dada2": v2, "Dada3": v3,
                "Comentaris": comentaris, "Operari": responsable
            }])
            conn.update(worksheet="Seguiment", data=pd.concat([seguiment_df, nueva_fila], ignore_index=True))
            
            # 2. ENVIAR EMAIL
            smtp = st.secrets["smtp"]
            msg = MIMEMultipart()
            msg['Subject'] = f"Seguimiento Obra: {project_sel} ({datetime.now().strftime('%d/%m/%Y')})"
            msg['From'] = f"Estellé Parquet <{smtp['user']}>"
            msg['To'] = dades_proj['Emails_Contacte']

            html = f"""
            <div style="font-family: Arial, sans-serif; border: 1px solid #eee; border-radius: 10px; overflow: hidden; max-width: 600px;">
                <div style="background-color: #fdfaf4; padding: 20px; text-align: center;">
                    <img src="{dades_proj['Logo_Client']}" height="50">
                    <h2 style="color: #6a5acd;">Seguimiento Diario</h2>
                    <p style="font-size: 12px; color: #999;">PROYECTO: {project_sel}</p>
                </div>
                <div style="padding: 20px;">
                    <p><strong>{config['Camp1']}:</strong> {v1}</p>
                    <p><strong>{config['Camp2']}:</strong> {v2}</p>
                    <p><strong>{config['Camp3']}:</strong> {v3}</p>
                    <hr>
                    <p><strong>COMENTARIOS:</strong><br>{comentaris}</p>
                </div>
                <div style="background: #f0f0f0; padding: 10px; text-align: center; font-size: 11px;">
                    Responsable: {responsable} | Estellé Parquet Digital
                </div>
            </div>
            """
            msg.attach(MIMEText(html, 'html'))
            with smtplib.SMTP(smtp['server'], smtp['port']) as s:
                s.starttls()
                s.login(smtp['user'], smtp['password'])
                s.send_message(msg)

            st.success("✅ ¡Todo perfecto! Informe enviado.")
            st.balloons()
        except Exception as err:
            st.error(f"Error: {err}")
