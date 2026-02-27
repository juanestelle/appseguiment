import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from datetime import datetime

# 1. CONFIGURACIÓ DE LA PÀGINA
st.set_page_config(page_title="Estellé Parquet - Seguiment", page_icon="🏗️")

# Estils personalitzats (el lila de la teva marca)
st.markdown("""
    <style>
    .main { background-color: #fdfaf4; }
    .stButton>button { background-color: #6a5acd; color: white; width: 100%; }
    </style>
    """, unsafe_allow_status_code=True)

# 2. CONNEXIÓ A GOOGLE SHEETS
try:
    conn = st.connection("gsheets", type=GSheetsConnection)
    
    # Llegim les tres pestanyes que hem creat
    projects_df = conn.read(worksheet="Projectes")
    templates_df = conn.read(worksheet="Config_Templates")
except Exception as e:
    st.error(f"Error connectant amb Google Sheets: {e}")
    st.stop()

# 3. INTERFÍCIE D'USUARI
st.title("🏗️ Seguiment d'Obra")

# Selecció de Projecte
projecte_sel = st.selectbox("Selecciona l'Obra", projects_df['Nom'].unique())
dades_projecte = projects_df[projects_df['Nom'] == projecte_sel].iloc[0]

# Selecció de Template (Parquet, Moqueta, etc.)
tipus_obra = st.radio("Tipus de treball", templates_df['Tipus'].unique(), horizontal=True)
config = templates_df[templates_df['Tipus'] == tipus_obra].iloc[0]

# Mostrem el logo del client si existeix
if pd.notna(dades_projecte['Logo_Client']):
    st.image(dades_projecte['Logo_Client'], width=150)

# 4. FORMULARI DE DADES
with st.form("diari_obra"):
    st.subheader(f"Informe de {tipus_obra}")
    
    col1, col2 = st.columns(2)
    with col1:
        v1 = st.number_input(f"{config['Camp1']}", min_value=0.0, step=0.1)
        v3 = st.number_input(f"{config['Camp3']}", min_value=0.0, step=0.1)
    with col2:
        v2 = st.number_input(f"{config['Camp2']}", min_value=0.0, step=0.1)
        responsable = st.text_input("Responsable en obra", value="Luis")

    comentaris = st.text_area("Comentaris de la jornada (incidències, piano, etc.)")
    
    enviar = st.form_submit_button("Finalitzar i enviar informe per Email")

# 5. LÒGICA D'ENVIAMENT
if enviar:
    with st.spinner("Guardant dades i enviant correu..."):
        try:
            # A. Lògica d'Email (usant els Secrets [smtp])
            smtp_config = st.secrets["smtp"]
            
            msg = MIMEMultipart()
            msg['Subject'] = f"Seguiment Obra: {projecte_sel} ({datetime.now().strftime('%d/%m/%Y')})"
            msg['From'] = f"Estellé Parquet <{smtp_config['user']}>"
            msg['To'] = dades_projecte['Emails_Contacte']

            html = f"""
            <div style="font-family: sans-serif; border: 1px solid #6a5acd; padding: 20px; border-radius: 10px;">
                <h2 style="color: #6a5acd;">Informe Diario - Estellé Parquet</h2>
                <p><strong>Proyecto:</strong> {projecte_sel}</p>
                <hr>
                <p><strong>{config['Camp1']}:</strong> {v1}</p>
                <p><strong>{config['Camp2']}:</strong> {v2}</p>
                <p><strong>{config['Camp3']}:</strong> {v3}</p>
                <p><strong>Comentarios:</strong> {comentaris}</p>
                <br>
                <p style="font-size: 0.8em; color: gray;">Responsable: {responsable}</p>
            </div>
            """
            msg.attach(MIMEText(html, 'html'))

            with smtplib.SMTP(smtp_config['server'], smtp_config['port']) as server:
                server.starttls()
                server.login(smtp_config['user'], smtp_config['password'])
                server.send_message(msg)

            st.success(f"Informe enviat correctament a {dades_projecte['Emails_Contacte']}")
            st.balloons()
            
        except Exception as e:
            st.error(f"S'ha produït un error: {e}")
