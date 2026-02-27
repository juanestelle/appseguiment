import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from datetime import datetime

# ==========================================
# 1. CONFIGURACIÓ
# ==========================================
st.set_page_config(page_title="Estellé Parquet", layout="centered")

st.markdown("""
    <style>
    .stApp { background-color: #fdfaf4; }
    .stButton>button { background-color: #6a5acd; color: white; border-radius: 8px; width: 100%; font-weight: bold; }
    h1 { color: #6a5acd; text-align: center; }
    </style>
    """, unsafe_allow_html=True)

# ==========================================
# 2. CONNEXIÓ
# ==========================================
conn = st.connection("gsheets", type=GSheetsConnection)

# --- DEBUG: mostra l'error exacte de connexió ---
try:
    df_projectes = conn.read(worksheet="Projectes", ttl=0)
    df_templates = conn.read(worksheet="Config_Templates", ttl=0)
except Exception as e:
    st.error("⚠️ Error de connexió amb Google Sheets")
    st.code(str(e))  # <-- mostra l'error complet per diagnosticar
    st.markdown("""
    **Comprova:**
    - Que `.streamlit/secrets.toml` té la URL del spreadsheet correcta
    - Que el compte de servei té accés **Editor** al document
    - Que els noms de les pestanyes coincideixen exactament
    """)
    st.stop()

# ==========================================
# 3. INTERFÍCIE
# ==========================================
st.title("🏗️ Seguiment d'Obra")
st.write("---")

try:
    df_projectes = df_projectes.dropna(subset=['Nom'])
    df_templates = df_templates.dropna(subset=['Tipus'])

    col1, col2 = st.columns(2)
    with col1:
        obra_sel = st.selectbox("Projecte", df_projectes['Nom'].unique())
        dades_p = df_projectes[df_projectes['Nom'] == obra_sel].iloc[0]
    with col2:
        tipus_sel = st.selectbox("Treball", df_templates['Tipus'].unique())
        dades_t = df_templates[df_templates['Tipus'] == tipus_sel].iloc[0]
except Exception as e:
    st.error(f"Error en l'estructura de les dades: {e}")
    st.stop()

with st.form("form_obra"):
    st.subheader(f"Informe de {tipus_sel}")

    v1 = st.number_input(f"{dades_t['Camp1']}", step=0.1) if pd.notna(dades_t.get('Camp1', '')) and dades_t['Camp1'] != "" else 0.0
    v2 = st.number_input(f"{dades_t['Camp2']}", step=0.1) if pd.notna(dades_t.get('Camp2', '')) and dades_t['Camp2'] != "" else 0.0
    v3 = st.number_input(f"{dades_t['Camp3']}", step=0.1) if pd.notna(dades_t.get('Camp3', '')) and dades_t['Camp3'] != "" else 0.0

    comentaris = st.text_area("Comentaris de la jornada")
    operari = st.text_input("Operari responsable", value="Luis")

    subm = st.form_submit_button("ENVIAR INFORME")

# ==========================================
# 4. ENVIAMENT
# ==========================================
if subm:
    with st.spinner("Enviant..."):
        try:
            # A. Llegir Seguiment (robust si la pestanya és buida o nova)
            try:
                df_seg = conn.read(worksheet="Seguiment", ttl=0)
                # Eliminem files completament buides
                df_seg = df_seg.dropna(how='all')
            except Exception:
                # Si la pestanya no existeix o és buida, partim de zero
                df_seg = pd.DataFrame(columns=["Data","Projecte","Tipus","Dada1","Dada2","Dada3","Comentaris","Operari"])

            nova_fila = pd.DataFrame([{
                "Data": datetime.now().strftime("%d/%m/%Y"),
                "Projecte": obra_sel,
                "Tipus": tipus_sel,
                "Dada1": v1, "Dada2": v2, "Dada3": v3,
                "Comentaris": comentaris,
                "Operari": operari
            }])

            df_final = pd.concat([df_seg, nova_fila], ignore_index=True)
            conn.update(worksheet="Seguiment", data=df_final)

            # B. Email (gestió de múltiples destinataris separats per comes)
            smtp = st.secrets["smtp"]
            emails_raw = str(dades_p['Emails_Contacte'])
            destinataris = [e.strip() for e in emails_raw.split(',') if e.strip()]

            msg = MIMEMultipart()
            msg['Subject'] = f"Seguiment: {obra_sel} ({datetime.now().strftime('%d/%m/%Y')})"
            msg['From'] = f"Estellé Parquet <{smtp['user']}>"
            msg['To'] = ", ".join(destinataris)

            html = f"""
            <div style="font-family: sans-serif; border: 1px solid #6a5acd; padding: 20px; border-radius: 10px;">
                <h2 style="color: #6a5acd;">Informe de Trabajo</h2>
                <p><strong>Proyecto:</strong> {obra_sel}</p>
                <p><strong>Trabajo:</strong> {tipus_sel}</p>
                <hr>
                <p>Comentarios: {comentaris}</p>
                <p style="font-size: 11px; color: #888;">Operario: {operari}</p>
            </div>
            """
            msg.attach(MIMEText(html, 'html'))

            with smtplib.SMTP(smtp['server'], smtp['port']) as s:
                s.starttls()
                s.login(smtp['user'], smtp['password'])
                s.sendmail(smtp['user'], destinataris, msg.as_string())  # sendmail és més robust que send_message amb llista

            st.success("Informe enviat i guardat amb èxit!")
            st.balloons()

        except Exception as e:
            st.error(f"Error en el procés final: {e}")
            st.code(str(e))  # mostra detall complet
