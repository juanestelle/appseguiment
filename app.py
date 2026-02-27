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
# 2. CONNEXIÓ A DADES
# ==========================================
try:
    conn = st.connection("gsheets", type=GSheetsConnection)
    
    # Carreguem les dades (L'error venia d'aquí)
    projects_df = conn.read(worksheet="Projectes")
    templates_df = conn.read(worksheet="Config_Templates")
    
except Exception as e:
    st.error("❌ ERROR EN LES PESTANYES DEL SHEETS")
    st.markdown(f"""
    **L'App ha connectat al fitxer, però no troba la informació:**
    1. Comprova que a la part inferior del teu Google Sheet hi hagi una pestanya anomenada **Projectes** i una altra **Config_Templates**.
    2. Vigila que no hi hagi **espais** abans o després del nom.
    
    *Detall tècnic:* `{e}`
    """)
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
        # Netegem possibles duplicats o valors buits
        noms_projectes = projects_df['Nom'].dropna().unique()
        projecte_sel = st.selectbox("Selecciona el Projecte", noms_projectes)
        dades_projecte = projects_df[projects_df['Nom'] == projecte_sel].iloc[0]

    with col_header2:
        tipus_treball = templates_df['Tipus'].dropna().unique()
        tipus_sel = st.selectbox("Tipus de Treball", tipus_treball)
        config = templates_df[templates_df['Tipus'] == tipus_sel].iloc[0]

    # Mostrem el logo del client
    if pd.notna(dades_projecte['Logo_Client']) and str(dades_projecte['Logo_Client']).startswith("http"):
        st.image(dades_projecte['Logo_Client'], width=100)
except Exception as e:
    st.warning(f"⚠️ Revisa les columnes del teu Sheets. Error: {e}")
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
    with st.spinner("Guardant i enviant..."):
        try:
            # A. GUARDAR A GOOGLE SHEETS
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
            
            # B. ENVIAR EMAIL
            smtp_conf = st.secrets["smtp"]
            msg = MIMEMultipart()
            msg['Subject'] = f"Seguiment Obra: {projecte_sel} - {datetime.now().strftime('%d/%m/%Y')}"
            msg['From'] = f"Estellé Parquet <{smtp_conf['user']}>"
            msg['To'] = dades_projecte['Emails_Contacte']

            html_content = f"""
            <div style="font-family: Arial, sans-serif; border: 1px solid #6a5acd; border-radius: 10px; overflow: hidden; max-width: 600px; background-color: white;">
                <div style="background-color: #fdfaf4; padding: 20px; text-align: center; border-bottom: 1px solid #eee;">
                    <img src="{dades_projecte['Logo_Client']}" height="50">
                    <h2 style="color: #6a5acd; margin-top: 10px;">Seguimiento Diario</h2>
                </div>
                <div style="padding: 30px;">
                    <p style="color: #888; font-size: 12px; margin-bottom: 20px;">PROYECTO: {projecte_sel}</p>
                    <table style="width: 100%; text-align: center; margin-bottom: 20px;">
                        <tr>
                            <td><strong>{v1}</strong><br><span style="color:#888; font-size:11px;">{config['Camp1']}</span></td>
                            <td><strong>{v2}</strong><br><span style="color:#888; font-size:11px;">{config['Camp2']}</span></td>
                            <td><strong>{v3}</strong><br><span style="color:#888; font-size:11px;">{config['Camp3']}</span></td>
                        </tr>
                    </table>
                    <div style="background: #f9f9fb; padding: 15px; border-radius: 5px; border-left: 4px solid #6a5acd;">
                        <strong>COMENTARIOS:</strong><br>{comentaris}
                    </div>
                </div>
                <div style="background: #f0f0f0; padding: 10px; text-align: center; font-size: 11px; color: #aaa;">
                    Responsable: {responsable} | Estellé Parquet Digital
                </div>
            </div>
            """
            msg.attach(MIMEText(html_content, 'html'))
            
            with smtplib.SMTP(smtp_conf['server'], smtp_conf['port']) as server:
                server.starttls()
                server.login(smtp_conf['user'], smtp_conf['password'])
                server.send_message(msg)

            st.success("✅ Informe enviat correctament!")
            st.balloons()
            
        except Exception as err:
            st.error(f"❌ Error: {err}")
