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
        transition: 0.3s;
    }
    .stButton>button:hover { background-color: #4b0082; transform: scale(1.01); }
    h1 { color: #6a5acd; text-align: center; margin-bottom: 0px; }
    .subtext { text-align: center; color: #888; font-size: 0.9em; margin-bottom: 30px; letter-spacing: 2px; }
    .status-ok { background-color: #e6ffed; border: 1px solid #34d399; padding: 10px; border-radius: 8px; color: #065f46; text-align: center; margin-bottom: 20px; }
    </style>
    """, unsafe_allow_html=True)

# ==========================================
# 2. CONNEXIÓ "SMART" SENSE ERRORS
# ==========================================
st.cache_data.clear()
conn = st.connection("gsheets", type=GSheetsConnection)

def carregar_dades_robust():
    try:
        # Intentem carregar per nom (el mètode estàndard)
        p_df = conn.read(worksheet="Projectes", ttl=0)
        t_df = conn.read(worksheet="Config_Templates", ttl=0)
        return p_df, t_df
    except:
        # FALLBACK: Si falla per nom, llegim les pestanyes per defecte
        # Això soluciona el problema de "Worksheet not found"
        try:
            p_df = conn.read(ttl=0) # Primera pestanya (Projectes)
            # Per a la segona, intentem forçar la lectura de la segona fulla
            # Si no podem, donem un error guiat
            t_df = conn.read(worksheet="Config_Templates", ttl=0)
            return p_df, t_df
        except Exception as e:
            st.error(f"⚠️ Error de lectura: {e}")
            st.stop()

projects_df, templates_df = carregar_dades_robust()

# ==========================================
# 3. INTERFÍCIE D'USUARI
# ==========================================
st.markdown("<div class='status-ok'>✅ Connexió establerta amb Estellé Parquet</div>", unsafe_allow_html=True)
st.title("🏗️ Seguiment d'Obra")
st.markdown("<div class='subtext'>ESTELLÉ PARQUET</div>", unsafe_allow_html=True)

try:
    col_h1, col_h2 = st.columns(2)
    with col_h1:
        noms_projectes = projects_df['Nom'].dropna().unique()
        projecte_sel = st.selectbox("Projecte", noms_projectes)
        dades_proj = projects_df[projects_df['Nom'] == projecte_sel].iloc[0]
    
    with col_h2:
        tipus_obres = templates_df['Tipus'].dropna().unique()
        tipus_sel = st.selectbox("Treball", tipus_obres)
        config = templates_df[templates_df['Tipus'] == tipus_sel].iloc[0]

    if pd.notna(dades_proj['Logo_Client']) and str(dades_proj['Logo_Client']).startswith("http"):
        st.image(dades_proj['Logo_Client'], width=100)

except Exception as e:
    st.warning(f"⚠️ Revisa les columnes del Sheets (Nom, Tipus, Camp1...). Error: {e}")
    st.stop()

# FORMULARI
with st.form("main_form"):
    st.subheader(f"Diari: {tipus_sel}")
    
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
            
    comentaris = st.text_area("Comentaris de la jornada", height=120, placeholder="Ex: S'ha instal·lat fins a la barra...")
    responsable = st.text_input("Responsable", value="Luis")
    
    submit = st.form_submit_button("FINALITZAR I ENVIAR INFORME")

# ==========================================
# 4. PROCESSAMENT: GUARDAR I ENVIAR
# ==========================================
if submit:
    with st.spinner("Sincronitzant dades..."):
        try:
            # 1. ACTUALITZAR GOOGLE SHEETS
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
            
            # 2. ENVIAR EMAIL
            smtp_secrets = st.secrets["smtp"]
            msg = MIMEMultipart()
            msg['Subject'] = f"Informe Obra: {projecte_sel} - {datetime.now().strftime('%d/%m/%Y')}"
            msg['From'] = f"Estellé Parquet <{smtp_secrets['user']}>"
            msg['To'] = dades_proj['Emails_Contacte']

            html = f"""
            <div style="font-family: Arial, sans-serif; border: 1px solid #6a5acd; border-radius: 12px; overflow: hidden; max-width: 600px; margin: auto; background-color: white;">
                <div style="background-color: #fdfaf4; padding: 25px; text-align: center; border-bottom: 1px solid #eee;">
                    <img src="{dades_proj['Logo_Client']}" height="50">
                    <h2 style="color: #6a5acd; margin-top: 15px;">Seguimiento Diario</h2>
                </div>
                <div style="padding: 30px;">
                    <p style="color: #999; font-size: 11px; text-transform: uppercase;">Proyecto: {projecte_sel}</p>
                    <table style="width: 100%; text-align: center; border-collapse: collapse;">
                        <tr>
                            <td style="padding:10px;"><strong>{v1}</strong><br><small>{config.get('Camp1', '')}</small></td>
                            <td style="padding:10px;"><strong>{v2}</strong><br><small>{config.get('Camp2', '')}</small></td>
                            <td style="padding:10px;"><strong>{v3}</strong><br><small>{config.get('Camp3', '')}</small></td>
                        </tr>
                    </table>
                    <div style="margin-top: 20px; padding: 15px; background: #f9f9fb; border-left: 4px solid #6a5acd;">
                        <strong>COMENTARIS:</strong><br>{comentaris}
                    </div>
                </div>
                <div style="background: #f4f4f4; padding: 10px; text-align: center; font-size: 11px; color: #aaa;">
                    Responsable: {responsable} | Estellé Parquet Digital
                </div>
            </div>
            """
            msg.attach(MIMEText(html, 'html'))
            
            with smtplib.SMTP(smtp_secrets['server'], smtp_secrets['port']) as s:
                s.starttls()
                s.login(smtp_secrets['user'], smtp_secrets['password'])
                s.send_message(msg)

            st.success("✅ Informe enviat correctament!")
            st.balloons()
            
        except Exception as err:
            st.error(f"❌ Error final: {err}")
