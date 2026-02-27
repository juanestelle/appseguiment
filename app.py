import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from datetime import datetime

# 1. CONFIGURACIÓ
st.set_page_config(page_title="Estellé Parquet", layout="centered")

st.markdown("""
    <style>
    .stApp { background-color: #fdfaf4; }
    .stButton>button { background-color: #6a5acd; color: white; border-radius: 8px; font-weight: bold; width: 100%; }
    h1 { color: #6a5acd; text-align: center; }
    </style>
    """, unsafe_allow_html=True)

# 2. CONNEXIÓ NETA
st.cache_data.clear() # Neteja total de memòria
conn = st.connection("gsheets", type=GSheetsConnection)

try:
    # Llegim les dades. Si el nom falla, el sistema s'aturarà aquí amb un missatge clar.
    df_projectes = conn.read(worksheet="Projectes")
    df_templates = conn.read(worksheet="Config_Templates")
except Exception as e:
    st.error("⚠️ ERROR 400 / LECTURA")
    st.write("Google no entén la petició. Revisa que:")
    st.write("1. L'ID als Secrets sigui NOMÉS: `17vINdoX_lvj7Yq89J3SKHU6ISHoGQHYiA_9vtBTKJEA`")
    st.write("2. Les pestanyes es diguin 'Projectes' i 'Config_Templates' (sense espais).")
    st.stop()

# 3. INTERFÍCIE
st.title("🏗️ Seguiment d'Obra")
st.write("---")

try:
    col1, col2 = st.columns(2)
    with col1:
        obra = st.selectbox("Projecte", df_projectes['Nom'].unique())
        c_p = df_projectes[df_projectes['Nom'] == obra].iloc[0]
    with col2:
        tipus = st.selectbox("Treball", df_templates['Tipus'].unique())
        c_t = df_templates[df_templates['Tipus'] == tipus].iloc[0]
except Exception as e:
    st.error(f"Error en les columnes del Sheets: {e}")
    st.stop()

with st.form("enviament"):
    st.subheader(f"Dades de {tipus}")
    v1 = st.number_input(f"{c_t['Camp1']}", step=0.1) if pd.notna(c_t['Camp1']) else 0.0
    v2 = st.number_input(f"{c_t['Camp2']}", step=0.1) if pd.notna(c_t['Camp2']) else 0.0
    v3 = st.number_input(f"{c_t['Camp3']}", step=0.1) if pd.notna(c_t['Camp3']) else 0.0
    
    comentaris = st.text_area("Observacions")
    operari = st.text_input("Operari", value="Luis")
    
    enviar = st.form_submit_button("ENVIAR ARA")

# 4. LÒGICA D'ENVIAMENT
if enviar:
    with st.spinner("Treballant..."):
        try:
            # A. Guardar al Sheets (Pestanya Seguiment)
            df_seguiment = conn.read(worksheet="Seguiment")
            nova_fila = pd.DataFrame([{
                "Data": datetime.now().strftime("%d/%m/%Y"),
                "Projecte": obra, "Tipus": tipus,
                "Dada1": v1, "Dada2": v2, "Dada3": v3,
                "Comentaris": comentaris, "Operari": operari
            }])
            updated = pd.concat([df_seguiment, nova_fila], ignore_index=True)
            conn.update(worksheet="Seguiment", data=updated)

            # B. Email
            smtp = st.secrets["smtp"]
            msg = MIMEMultipart()
            msg['Subject'] = f"Seguiment {obra}"
            msg['From'] = smtp['user']
            msg['To'] = c_p['Emails_Contacte']
            
            cos = f"Projecte: {obra}\nTreball: {tipus}\nMesures: {v1}, {v2}, {v3}\n\nComentaris: {comentaris}"
            msg.attach(MIMEText(cos, 'plain'))
            
            with smtplib.SMTP(smtp['server'], smtp['port']) as s:
                s.starttls()
                s.login(smtp['user'], smtp['password'])
                s.send_message(msg)
            
            st.success("Enviat!")
            st.balloons()
        except Exception as e:
            st.error(f"Error en l'enviament: {e}")
