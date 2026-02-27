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

# Injectem CSS per personalitzar la interfície (CORREGIT: unsafe_allow_html=True)
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
    .stSelectbox label, .stTextInput label, .stNumberInput label {
        color: #4b0082;
        font-weight: bold;
    }
    h1 { color: #6a5acd; text-align: center; }
    </style>
    """, unsafe_allow_html=True)

# ==========================================
# 2. CONNEXIÓ A DADES (GOOGLE SHEETS)
# ==========================================
try:
    # Creem la connexió usant els secrets de Streamlit
    conn = st.connection("gsheets", type=GSheetsConnection)
    
    # Intentem llegir les pestanyes. 
    # ATENCIÓ: Si falla aquí amb un 404, és l'ID del Sheet o el permís del correu del JSON.
    projects_df = conn.read(worksheet="Projectes")
    templates_df = conn.read(worksheet="Config_Templates")
except Exception as e:
    st.error("❌ ERROR DE CONNEXIÓ AMB EL FULL DE CÀLCUL (404)")
    st.markdown(f"""
    ### Com solucionar-ho ara mateix:
    1. **L'ID del Spreadsheet:** Revisa que l'ID que has posat als Secrets de Streamlit sigui el correcte. 
       *És el codi de lletres i números que hi ha a la URL del teu navegador.*
    2. **Compartir el fitxer:** * Obre el teu fitxer **JSON** (el de la clau de Google).
       * Busca on diu `"client_email": "nom-del-robot@projecte.iam.gserviceaccount.com"`.
       * **Copia aquest correu.**
       * Ves al teu Google Sheet, clica el botó **Compartir** i enganxa aquest correu amb permís d'**Editor**.
    3. **Noms de les pestanyes:** Verifica que les pestanyes del teu Google Sheet es diguin exactament: 
       `Projectes`, `Config_Templates` i `Seguiment`.
    
    **Detall tècnic de l'error:** `{e}`
    """)
    st.stop()

# ==========================================
# 3. INTERFÍCIE D'USUARI (FORMULARI)
# ==========================================
st.title("🏗️ Seguiment d'Obra")
st.write("---")

# Selecció de Projecte i Tipus de Treball
try:
    col_header1, col_header2 = st.columns(2)
    with col_header1:
        projecte_sel = st.selectbox("Selecciona el Projecte", projects_df['Nom'].unique())
        dades_projecte = projects_df[projects_df['Nom'] == projecte_sel].iloc[0]

    with col_header2:
        tipus_sel = st.selectbox("Tipus de Treball", templates_df['Tipus'].unique())
        config = templates_df[templates_df['Tipus'] == tipus_sel].iloc[0]

    # Mostrem el logo del client si la URL és vàlida
    if pd.notna(dades_projecte['Logo_Client']) and str(dades_projecte['Logo_Client']).startswith("http"):
        st.image(dades_projecte['Logo_Client'], width=120)
except Exception as e:
    st.warning(f"⚠️ Hi ha un problema amb les dades de les pestanyes: {e}")
    st.stop()

st.write("") 

with st.form("formulari_seguiment"):
    st.subheader(f"Dades de la Jornada: {tipus_sel}")
    
    c1, c2, c3 = st.columns(3)
    with c1:
        v1 = st.number_input(f"{config['Camp1']}", min_value=0.0, step=0.1, format="%.1f")
    with c2:
        v2 = st.number_input(f"{config['Camp2']}", min_value=0.0, step=0.1, format="%.1f")
    with c3:
        v3 = st.number_input(f"{config['Camp3']}", min_value=0.0, step=0.1, format="%.1f")
        
    comentaris = st.text_area("Comentaris de la jornada (incidències, estat de l'obra, etc.)", height=150)
    responsable = st.text_input("Responsable en obra", value="Luis")
    
    st.write("---")
    submit = st.form_submit_button("FINALITZAR I ENVIAR INFORME")

# ==========================================
# 4. PROCESSAMENT: GUARDAR I ENVIAR EMAIL
# ==========================================
if submit:
    with st.spinner("Processant informe..."):
        try:
            # A. GUARDAR DADES AL GOOGLE SHEET
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
            <html>
            <body style="font-family: Arial, sans-serif; background-color: #fdfaf4; padding: 20px; color: #333;">
                <div style="max-width: 600px; margin: auto; background: white; border: 1px solid #eee; border-radius: 10px; overflow: hidden;">
                    <div style="padding: 20px; text-align: center; border-bottom: 1px solid #f0f0f0;">
                        <img src="{dades_projecte['Logo_Client']}" height="60" style="margin-bottom: 10px;">
                        <div style="font-size: 12px; color: #999; letter-spacing: 1px;">PROYECTO: {projecte_sel}</div>
                    </div>
                    
                    <div style="padding: 30px;">
                        <h2 style="color: #6a5acd; text-align: center; font-size: 20px; margin-bottom: 25px;">TRABAJOS</h2>
                        
                        <table style="width: 100%; text-align: center; border-collapse: collapse;">
                            <tr>
                                <td style="padding: 10px;">
                                    <span style="font-size: 24px; font-weight: bold; color: #444;">{v1}</span><br>
                                    <span style="font-size: 13px; color: #888;">{config['Camp1']}</span>
                                </td>
                                <td style="padding: 10px;">
                                    <span style="font-size: 24px; font-weight: bold; color: #444;">{v2}</span><br>
                                    <span style="font-size: 13px; color: #888;">{config['Camp2']}</span>
                                </td>
                                <td style="padding: 10px;">
                                    <span style="font-size: 24px; font-weight: bold; color: #444;">{v3}</span><br>
                                    <span style="font-size: 13px; color: #888;">{config['Camp3']}</span>
                                </td>
                            </tr>
                        </table>
                        
                        <div style="margin-top: 30px; padding: 20px; background-color: #f9f9fb; border-radius: 5px;">
                            <strong style="color: #6a5acd; font-size: 14px;">COMENTARIOS DE LA JORNADA:</strong>
                            <p style="font-size: 14px; line-height: 1.6; color: #555;">{comentaris}</p>
                        </div>
                    </div>
                    
                    <div style="padding: 20px; background: #fdfaf4; text-align: center; border-top: 1px solid #eee;">
                        <p style="font-size: 12px; color: #aaa; margin: 0;">Responsable en obra: <strong>{responsable}</strong></p>
                        <p style="font-size: 10px; color: #ccc; margin-top: 10px;">Generat automàticament per Estellé Parquet Digital</p>
                    </div>
                </div>
            </body>
            </html>
            """
            
            msg.attach(MIMEText(html_content, 'html'))
            
            with smtplib.SMTP(smtp_conf['server'], smtp_conf['port']) as server:
                server.starttls()
                server.login(smtp_conf['user'], smtp_conf['password'])
                server.send_message(msg)

            st.success("✅ Dades guardades i informe enviat amb èxit!")
            st.balloons()
            
        except Exception as err:
            st.error(f"❌ Error durant el procés d'enviament: {err}")
