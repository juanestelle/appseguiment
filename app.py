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
        height: 3.5em;
        font-weight: bold;
        border: none;
        transition: 0.3s;
    }
    .stButton>button:hover { background-color: #4b0082; border: none; }
    h1 { color: #6a5acd; text-align: center; margin-bottom: 0px; font-family: 'Helvetica', sans-serif; }
    .subtext { text-align: center; color: #888; font-size: 0.9em; margin-bottom: 30px; letter-spacing: 2px; }
    .stSelectbox label, .stTextInput label, .stNumberInput label, .stTextArea label {
        color: #6a5acd !important;
        font-weight: bold !important;
    }
    div[data-testid="stForm"] {
        border: 1px solid #e6e6e6;
        border-radius: 15px;
        background-color: #ffffff;
        padding: 25px;
    }
    </style>
    """, unsafe_allow_html=True)

# ==========================================
# 2. CONNEXIÓ A DADES
# ==========================================
try:
    conn = st.connection("gsheets", type=GSheetsConnection)
    projects_df = conn.read(worksheet="Projectes")
    templates_df = conn.read(worksheet="Config_Templates")
except Exception as e:
    st.error("❌ ERROR DE CONNEXIÓ")
    st.info(f"Detall: {e}")
    st.stop()

# ==========================================
# 3. INTERFÍCIE D'USUARI
# ==========================================
st.title("🏗️ Seguiment d'Obra")
st.markdown("<div class='subtext'>ESTELLÉ PARQUET</div>", unsafe_allow_html=True)

# Selectors principals
col_h1, col_h2 = st.columns(2)
with col_h1:
    noms_obres = projects_df['Nom'].dropna().unique()
    projecte_sel = st.selectbox("Projecte actiu", noms_obres)
    dades_proj = projects_df[projects_df['Nom'] == projecte_sel].iloc[0]

with col_h2:
    tipus_treball = templates_df['Tipus'].dropna().unique()
    tipus_sel = st.selectbox("Treball a realitzar", tipus_treball)
    config = templates_df[templates_df['Tipus'] == tipus_sel].iloc[0]

# Logo del Client (si existeix)
if pd.notna(dades_proj['Logo_Client']) and str(dades_proj['Logo_Client']).startswith("http"):
    st.image(dades_proj['Logo_Client'], width=100)

st.write("")

# FORMULARI DINÀMIC
with st.form("main_form"):
    st.subheader(f"Diari de {tipus_sel}")
    
    # Lògica intel·ligent: Només mostrem els camps que has omplert al Sheets
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
            
    comentaris = st.text_area("Comentaris de la jornada", height=120, placeholder="Escriu aquí qualsevol detall rellevant...")
    responsable = st.text_input("Responsable", value="Luis")
    
    st.write("")
    submit = st.form_submit_button("ENVIAR SEGUIMENT DIARI")

# ==========================================
# 4. ENVIAMENT I REGISTRE
# ==========================================
if submit:
    with st.spinner("Sincronitzant amb el núvol..."):
        try:
            # 1. ACTUALITZAR GOOGLE SHEETS
            seguiment_df = conn.read(worksheet="Seguiment")
            nova_data = pd.DataFrame([{
                "Data": datetime.now().strftime("%d/%m/%Y %H:%M"),
                "Projecte": projecte_sel,
                "Tipus": tipus_sel,
                "Dada1": v1, "Dada2": v2, "Dada3": v3,
                "Comentaris": comentaris,
                "Operari": responsable
            }])
            final_df = pd.concat([seguiment_df, nova_data], ignore_index=True)
            conn.update(worksheet="Seguiment", data=final_df)
            
            # 2. ENVIAR EMAIL (DISSENY NET)
            smtp = st.secrets["smtp"]
            msg = MIMEMultipart()
            msg['Subject'] = f"Seguiment: {projecte_sel} ({datetime.now().strftime('%d/%m/%Y')})"
            msg['From'] = f"Estellé Parquet <{smtp['user']}>"
            msg['To'] = dades_proj['Emails_Contacte']

            # Construcció dinàmica de la taula de l'email
            files_taula = ""
            if v1 > 0: files_taula += f"<tr><td>{config['Camp1']}</td><td><strong>{v1}</strong></td></tr>"
            if v2 > 0: files_taula += f"<tr><td>{config['Camp2']}</td><td><strong>{v2}</strong></td></tr>"
            if v3 > 0: files_taula += f"<tr><td>{config['Camp3']}</td><td><strong>{v3}</strong></td></tr>"

            html = f"""
            <div style="font-family: 'Helvetica', sans-serif; max-width: 600px; margin: auto; border: 1px solid #eee; border-radius: 12px; overflow: hidden;">
                <div style="background-color: #fdfaf4; padding: 30px; text-align: center;">
                    <img src="{dades_proj['Logo_Client']}" height="50">
                    <h2 style="color: #6a5acd; margin-top: 20px;">Seguimiento de Obra</h2>
                    <p style="font-size: 12px; color: #999;">PROYECTO: {projecte_sel}</p>
                </div>
                <div style="padding: 30px;">
                    <table style="width: 100%; border-collapse: collapse; margin-bottom: 20px;">
                        {files_taula}
                    </table>
                    <div style="background: #f9f9fb; padding: 20px; border-radius: 8px; border-left: 4px solid #6a5acd;">
                        <strong style="color: #6a5acd; font-size: 13px;">COMENTARIOS:</strong><br>
                        <p style="color: #444; line-height: 1.5;">{comentaris}</p>
                    </div>
                </div>
                <div style="background: #f4f4f4; padding: 15px; text-align: center; font-size: 11px; color: #888;">
                    Responsable: {responsable} | Enviado por Estellé Parquet Digital
                </div>
            </div>
            """
            msg.attach(MIMEText(html, 'html'))
            
            with smtplib.SMTP(smtp['server'], smtp['port']) as s:
                s.starttls()
                s.login(smtp['user'], smtp['password'])
                s.send_message(msg)

            st.success("✅ Informe enviat i guardat correctament!")
            st.balloons()

        except Exception as err:
            st.error(f"⚠️ Error: {err}")
