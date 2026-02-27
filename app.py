import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from datetime import datetime

# ==========================================
# 1. CONFIGURACIÓ I ESTILS
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
    .debug-info { background-color: #eef2ff; padding: 15px; border-radius: 8px; border: 1px solid #6a5acd; color: #312e81; }
    </style>
    """, unsafe_allow_html=True)

# ==========================================
# 2. CONNEXIÓ INTEL·LIGENT (AUTO-DETECTION)
# ==========================================
try:
    conn = st.connection("gsheets", type=GSheetsConnection)
    
    # Intentem carregar les pestanyes de forma flexible
    # Llegim primer sense especificar per treure la llista de pestanyes si falla
    projects_df = conn.read(worksheet="Projectes", ttl=0)
    templates_df = conn.read(worksheet="Config_Templates", ttl=0)
    
except Exception as e:
    st.error("⚠️ EL SISTEMA NO TROBA LES PESTANYES")
    st.write("Això és el que el robot 'veu' ara mateix:")
    
    # BLOC DE DIAGNÒSTIC PER A L'USUARI
    try:
        # Aquesta és una funció interna per llistar pestanyes reals
        # Si falla la càrrega directa, intentem llegir la fulla per defecte
        test_df = conn.read(ttl=0)
        st.info("✅ Connexió OK, però els noms no coincideixen.")
        st.write("Les teves pestanyes s'haurien de dir exactament: **Projectes** i **Config_Templates**.")
        st.write("Revisa que no hagis posat 'Proyectos' (en castellà) o 'Full 1'.")
    except Exception as e2:
        st.error(f"Error de permís o URL: {e2}")
        st.write("Assegura't que l'ID a Secrets és: `17vINdoX_lvj7Yq89J3SKHU6ISHoGQHYiA_9vtBTKJEA`")
    st.stop()

# ==========================================
# 3. INTERFÍCIE D'USUARI
# ==========================================
st.title("🏗️ Seguiment d'Obra")
st.markdown("<div class='subtext'>ESTELLÉ PARQUET</div>", unsafe_allow_html=True)

try:
    # Netegem dades per evitar errors de cel·les buides
    projects_df = projects_df.dropna(subset=['Nom'])
    templates_df = templates_df.dropna(subset=['Tipus'])

    col_h1, col_h2 = st.columns(2)
    with col_h1:
        projecte_sel = st.selectbox("Selecciona el Projecte", projects_df['Nom'].unique())
        dades_proj = projects_df[projects_df['Nom'] == projecte_sel].iloc[0]

    with col_h2:
        tipus_sel = st.selectbox("Tipus de Treball", templates_df['Tipus'].unique())
        config = templates_df[templates_df['Tipus'] == tipus_sel].iloc[0]

    # Logo Client
    if pd.notna(dades_proj['Logo_Client']) and str(dades_proj['Logo_Client']).startswith("http"):
        st.image(dades_proj['Logo_Client'], width=100)

except Exception as e:
    st.error(f"⚠️ Error en l'estructura de les columnes: {e}")
    st.write("Revisa que la primera fila tingui els encapçalaments: Nom, Logo_Client, Emails_Contacte...")
    st.stop()

# FORMULARI
with st.form("obra_form"):
    st.subheader(f"Diari: {tipus_sel}")
    
    c1, c2, c3 = st.columns(3)
    v1, v2, v3 = 0.0, 0.0, 0.0
    
    with c1:
        if pd.notna(config['Camp1']) and config['Camp1'] != "":
            v1 = st.number_input(f"{config['Camp1']}", min_value=0.0, step=0.1)
    with c2:
        if pd.notna(config['Camp2']) and config['Camp2'] != "":
            v2 = st.number_input(f"{config['Camp2']}", min_value=0.0, step=0.1)
    with c3:
        if pd.notna(config['Camp3']) and config['Camp3'] != "":
            v3 = st.number_input(f"{config['Camp3']}", min_value=0.0, step=0.1)
            
    comentaris = st.text_area("Comentaris de la jornada", height=150)
    responsable = st.text_input("Responsable", value="Luis")
    
    submit = st.form_submit_button("FINALITZAR I ENVIAR INFORME")

# ==========================================
# 4. ENVIAMENT
# ==========================================
if submit:
    with st.spinner("Sincronitzant..."):
        try:
            # Desar al Sheets
            seguiment_df = conn.read(worksheet="Seguiment", ttl=0)
            nova_fila = pd.DataFrame([{
                "Data": datetime.now().strftime("%d/%m/%Y %H:%M"),
                "Projecte": projecte_sel,
                "Tipus": tipus_sel,
                "Dada1": v1, "Dada2": v2, "Dada3": v3,
                "Comentaris": comentaris,
                "Operari": responsable
            }])
            updated_df = pd.concat([seguiment_df, nova_fila], ignore_index=True)
            conn.update(worksheet="Seguiment", data=updated_df)
            
            # Email
            smtp = st.secrets["smtp"]
            msg = MIMEMultipart()
            msg['Subject'] = f"Informe Obra: {projecte_sel} - {datetime.now().strftime('%d/%m/%Y')}"
            msg['From'] = f"Estellé Parquet <{smtp['user']}>"
            msg['To'] = dades_proj['Emails_Contacte']

            html = f"""
            <div style="font-family: sans-serif; border: 1px solid #6a5acd; border-radius: 12px; overflow: hidden; max-width: 600px; margin: auto; background-color: white;">
                <div style="background-color: #fdfaf4; padding: 25px; text-align: center; border-bottom: 1px solid #eee;">
                    <img src="{dades_proj['Logo_Client']}" height="50">
                    <h2 style="color: #6a5acd; margin-top: 15px;">Seguimiento Diario</h2>
                </div>
                <div style="padding: 30px;">
                    <p style="color: #999; font-size: 11px; text-transform: uppercase;">Proyecto: {projecte_sel}</p>
                    <p><strong>{config['Camp1']}:</strong> {v1}</p>
                    <p><strong>{config['Camp2']}:</strong> {v2}</p>
                    <p><strong>{config['Camp3']}:</strong> {v3}</p>
                    <div style="margin-top: 20px; padding: 15px; background: #f9f9fb; border-left: 4px solid #6a5acd;">
                        <strong>COMENTARIOS:</strong><br>{comentaris}
                    </div>
                </div>
                <div style="background: #f4f4f4; padding: 10px; text-align: center; font-size: 11px; color: #aaa;">
                    Responsable: {responsable} | Estellé Parquet Digital
                </div>
            </div>
            """
            msg.attach(MIMEText(html, 'html'))
            
            with smtplib.SMTP(smtp['server'], smtp['port']) as s:
                s.starttls()
                s.login(smtp['user'], smtp['password'])
                s.send_message(msg)

            st.success("✅ Informe enviat correctament!")
            st.balloons()
            
        except Exception as err:
            st.error(f"❌ Error final: {err}")
