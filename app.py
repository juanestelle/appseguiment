import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from datetime import datetime

# ==========================================
# 1. CONFIGURACIÓ DE LA PÀGINA I ESTILS
# ==========================================
st.set_page_config(page_title="Estellé Parquet - Seguiment", page_icon="🏗️", layout="centered")

st.markdown("""
    <style>
    .stApp { background-color: #fdfaf4; }
    .stButton>button { 
        background-color: #6a5acd; color: white; width: 100%; 
        border-radius: 8px; height: 3.5em; font-weight: bold; border: none;
    }
    h1 { color: #6a5acd; text-align: center; margin-bottom: 0px; }
    .subtext { text-align: center; color: #888; font-size: 0.9em; margin-bottom: 30px; letter-spacing: 2px; }
    .diag-box { background-color: #ffecec; border: 1px solid #ff5c5c; padding: 20px; border-radius: 10px; color: #b91d1d; }
    </style>
    """, unsafe_allow_html=True)

# ==========================================
# 2. CONNEXIÓ I DIAGNÒSTIC FORÇAT
# ==========================================
# Afegim ttl=0 per forçar Streamlit a no llegir dades velles
conn = st.connection("gsheets", type=GSheetsConnection)

def carregar_dades():
    try:
        # Intentem llegir les dades sense cache (ttl=0)
        p_df = conn.read(worksheet="Projectes", ttl=0)
        t_df = conn.read(worksheet="Config_Templates", ttl=0)
        return p_df, t_df, None
    except Exception as e:
        return None, None, str(e)

projects_df, templates_df, error_msg = carregar_dades()

if error_msg:
    st.markdown("<div class='diag-box'><h3>⚠️ EL ROBOT NO TROBA LES PESTANYES</h3>", unsafe_allow_html=True)
    st.write("Dins del teu Google Sheets, les pestanyes de baix **S'HAN DE DIR EXACTAMENT:**")
    st.code("Projectes\nConfig_Templates\nSeguiment")
    
    st.write("---")
    st.write("🔍 **Diagnòstic per a l'oficina:**")
    
    # Intentem llistar què veu el robot realment
    if st.button("PREM AQUÍ PER VEURE QUÈ VEU EL ROBOT"):
        try:
            # Això intenta llegir la primera pestanya que trobi, es digui com es digui
            raw_data = conn.read(ttl=0)
            st.success("Connexió establerta! El robot veu dades, però no troba els noms 'Projectes' o 'Config_Templates'.")
            st.write("Comprova que no hagis posat la primera lletra en minúscula o hagis deixat un espai al final del nom de la pestanya al Sheets.")
        except Exception as e2:
            st.error(f"Error fatal: {e2}")
    
    st.markdown("</div>", unsafe_allow_html=True)
    st.stop()

# ==========================================
# 3. INTERFÍCIE D'USUARI
# ==========================================
st.title("🏗️ Seguiment d'Obra")
st.markdown("<div class='subtext'>ESTELLÉ PARQUET</div>", unsafe_allow_html=True)

try:
    col_h1, col_h2 = st.columns(2)
    with col_h1:
        projecte_sel = st.selectbox("Projecte", projects_df['Nom'].dropna().unique())
        dades_proj = projects_df[projects_df['Nom'] == projecte_sel].iloc[0]
    with col_h2:
        tipus_sel = st.selectbox("Tipus de Treball", templates_df['Tipus'].dropna().unique())
        config = templates_df[templates_df['Tipus'] == tipus_sel].iloc[0]

    if pd.notna(dades_proj['Logo_Client']) and str(dades_proj['Logo_Client']).startswith("http"):
        st.image(dades_proj['Logo_Client'], width=100)

except Exception as e:
    st.error(f"⚠️ Error en les columnes: Revisa que la fila 1 tingui 'Nom', 'Tipus', etc. Detall: {e}")
    st.stop()

with st.form("main_form"):
    st.subheader(f"Informe de {tipus_sel}")
    
    c1, c2, c3 = st.columns(3)
    v1, v2, v3 = 0.0, 0.0, 0.0
    
    with c1:
        if pd.notna(config['Camp1']) and config['Camp1'] != "":
            v1 = st.number_input(f"{config['Camp1']}", min_value=0.0, step=0.1, format="%.1f")
    with c2:
        if pd.notna(config['Camp2']) and config['Camp2'] != "":
            v2 = st.number_input(f"{config['Camp2']}", min_value=0.0, step=0.1, format="%.1f")
    with c3:
        if pd.notna(config['Camp3']) and config['Camp3'] != "":
            v3 = st.number_input(f"{config['Camp3']}", min_value=0.0, step=0.1, format="%.1f")
            
    comentaris = st.text_area("Comentaris de la jornada", height=120)
    responsable = st.text_input("Responsable", value="Luis")
    
    submit = st.form_submit_button("FINALITZAR I ENVIAR")

# ==========================================
# 4. PROCESSAMENT
# ==========================================
if submit:
    with st.spinner("Guardant..."):
        try:
            seguiment_df = conn.read(worksheet="Seguiment", ttl=0)
            nova_fila = pd.DataFrame([{
                "Data": datetime.now().strftime("%d/%m/%Y %H:%M"),
                "Projecte": projecte_sel, "Tipus": tipus_sel,
                "Dada1": v1, "Dada2": v2, "Dada3": v3,
                "Comentaris": comentaris, "Operari": responsable
            }])
            conn.update(worksheet="Seguiment", data=pd.concat([seguiment_df, nova_fila], ignore_index=True))
            
            smtp = st.secrets["smtp"]
            msg = MIMEMultipart()
            msg['Subject'] = f"Seguiment: {projecte_sel} ({datetime.now().strftime('%d/%m/%Y')})"
            msg['From'] = f"Estellé Parquet <{smtp['user']}>"
            msg['To'] = dades_proj['Emails_Contacte']

            html = f"<html><body><h2 style='color: #6a5acd;'>Informe {projecte_sel}</h2><p>{comentaris}</p></body></html>"
            msg.attach(MIMEText(html, 'html'))
            
            with smtplib.SMTP(smtp['server'], smtp['port']) as s:
                s.starttls()
                s.login(smtp['user'], smtp['password'])
                s.send_message(msg)

            st.success("✅ Informe enviat!")
            st.balloons()
        except Exception as err:
            st.error(f"Error: {err}")
