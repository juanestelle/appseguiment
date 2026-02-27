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
st.set_page_config(page_title="Estellé Parquet - Seguiment d'Obra", page_icon="🏗️", layout="centered")

st.markdown("""
    <style>
    .stApp { background-color: #fdfaf4; }
    .stButton>button { 
        background-color: #6a5acd; 
        color: white; 
        width: 100%; 
        border-radius: 8px;
        height: 3em;
        font-weight: bold;
    }
    h1 { color: #6a5acd; text-align: center; margin-bottom: 0px; }
    .subtext { text-align: center; color: #888; font-size: 0.9em; margin-bottom: 20px; }
    </style>
    """, unsafe_allow_html=True)

# ==========================================
# 2. CONNEXIÓ A DADES (DIAGNÒSTIC AVANÇAT)
# ==========================================
try:
    conn = st.connection("gsheets", type=GSheetsConnection)
    
    # Intentem llegir les pestanyes una a una per detectar l'error
    try:
        projects_df = conn.read(worksheet="Projectes")
    except Exception as e:
        st.error("No s'ha trobat la pestanya 'Projectes'. Revisa que el nom sigui exactament aquest.")
        st.stop()
        
    try:
        templates_df = conn.read(worksheet="Config_Templates")
    except Exception as e:
        st.error("No s'ha trobat la pestanya 'Config_Templates'.")
        st.stop()

except Exception as e:
    st.error("❌ ERROR CRÍTIC DE CONNEXIÓ (404)")
    st.markdown(f"""
    **El robot no pot accedir al fitxer. Passos finals:**
    1. **URL:** Comprova que als Secrets hagis posat l'ID correcte: `17vINdoX_lvj7Yq89J3SKHU6ISHoGQHYiA_9vtBTKJEA`
    2. **Editor:** El correu `app-seguiment-service@estelle-app-488715.iam.gserviceaccount.com` ha de ser **Editor** al botó Compartir.
    3. **APIs:** Confirma que 'Google Sheets API' i 'Google Drive API' estan en **'Enabled'** a la consola de Google Cloud.
    """)
    st.info(f"Detall tècnic: {e}")
    st.stop()

# ==========================================
# 3. INTERFÍCIE D'USUARI
# ==========================================
st.title("🏗️ Seguiment d'Obra")
st.markdown("<div class='subtext'>By ESTELLÉ parquet</div>", unsafe_allow_html=True)
st.write("---")

try:
    col_header1, col_header2 = st.columns(2)
    with col_header1:
        projecte_sel = st.selectbox("Projecte", projects_df['Nom'].unique())
        dades_projecte = projects_df[projects_df['Nom'] == projecte_sel].iloc[0]

    with col_header2:
        tipus_sel = st.selectbox("Tipus de Treball", templates_df['Tipus'].unique())
        config = templates_df[templates_df['Tipus'] == tipus_sel].iloc[0]

    if pd.notna(dades_projecte['Logo_Client']) and str(dades_projecte['Logo_Client']).startswith("http"):
        st.image(dades_projecte['Logo_Client'], width=100)
except Exception as e:
    st.warning(f"⚠️ Revisa les dades del Sheets: {e}")
    st.stop()

with st.form("formulari_seguiment"):
    st.subheader(f"Informe de {tipus_sel}")
    
    c1, c2, c3 = st.columns(3)
    with c1:
        v1 = st.number_input(f"{config['Camp1']}", min_value=0.0, step=0.1, format="%.1f")
    with c2:
        v2 = st.number_input(f"{config['Camp2']}", min_value=0.0, step=0.1, format="%.1f")
    with c3:
        v3 = st.number_input(f"{config['Camp3']}", min_value=0.0, step=0.1, format="%.1f")
        
    comentaris = st.text_area("Comentaris de la jornada", height=150)
    responsable = st.text_input("Responsable en obra", value="Luis")
    
    submit = st.form_submit_button("FINALITZAR I ENVIAR INFORME")

# ==========================================
# 4. PROCESSAMENT
# ==========================================
if submit:
    with st.spinner("Enviant dades..."):
        try:
            # GUARDAR A GOOGLE SHEETS
            seguiment_actual = conn.read(worksheet="Seguiment")
            nova_fila = pd.DataFrame([{
                "Data": datetime.now().strftime("%d/%m/%Y %H:%M"),
                "Projecte": projecte_sel,
                "Tipus": tipus_sel,
                "Dada1": v1,
                "Dada2": v2,
                "Dada3": v3,
                "Comentaris": comentaris,
                "Operari": responsable
            }])
            updated_df = pd.concat([seguiment_actual, nova_fila], ignore_index=True)
            conn.update(worksheet="Seguiment", data=updated_df)
            
            # ENVIAR EMAIL
            smtp_conf = st.secrets["smtp"]
            msg = MIMEMultipart()
            msg['Subject'] = f"Seguiment Obra: {projecte_sel} - {datetime.now().strftime('%d/%m/%Y')}"
            msg['From'] = f"Estellé Parquet <{smtp_conf['user']}>"
            msg['To'] = dades_projecte['Emails_Contacte']

            html_content = f"""
            <div style="font-family: Arial, sans-serif; border: 1px solid #6a5acd; border-radius: 10px; overflow: hidden; max-width: 600px;">
                <div style="background-color: #fdfaf4; padding: 20px; text-align: center;">
                    <img src="{dades_projecte['Logo_Client']}" height="50">
                    <h2 style="color: #6a5acd;">Informe de Trabajo</h2>
                </div>
                <div style="padding: 20px;">
                    <p><strong>Proyecto:</strong> {projecte_sel}</p>
                    <p><strong>{config['Camp1']}:</strong> {v1}</p>
                    <p><strong>{config['Camp2']}:</strong> {v2}</p>
                    <p><strong>{config['Camp3']}:</strong> {v3}</p>
                    <p><strong>Comentarios:</strong> {comentaris}</p>
                </div>
                <div style="background: #f0f0f0; padding: 10px; text-align: center; font-size: 12px;">
                    Responsable: {responsable} | Estellé Parquet
                </div>
            </div>
            """
            msg.attach(MIMEText(html_content, 'html'))
            
            with smtplib.SMTP(smtp_conf['server'], smtp_conf['port']) as server:
                server.starttls()
                server.login(smtp_conf['user'], smtp_conf['password'])
                server.send_message(msg)

            st.success("✅ Tot correcte! Informe enviat.")
            st.balloons()
            
        except Exception as err:
            st.error(f"❌ Error: {err}")
