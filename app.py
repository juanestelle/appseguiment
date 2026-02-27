import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from datetime import datetime

# ==========================================
# 1. CONFIGURACIÓ DE PÀGINA
# ==========================================
st.set_page_config(
    page_title="Estellé Parquet · Seguiment d'Obra",
    page_icon="🪵",
    layout="centered"
)

# ==========================================
# 2. ESTILS VISUALS
# ==========================================
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Cormorant+Garamond:wght@400;600;700&family=DM+Sans:wght@300;400;500&display=swap');

/* Reset i base */
.stApp {
    background-color: #F7F2EA;
    background-image:
        radial-gradient(ellipse at 20% 50%, rgba(193,154,107,0.08) 0%, transparent 60%),
        radial-gradient(ellipse at 80% 20%, rgba(139,100,60,0.06) 0%, transparent 50%);
    font-family: 'DM Sans', sans-serif;
}

/* Ocultar elements per defecte de Streamlit */
#MainMenu, footer, header { visibility: hidden; }
.block-container { padding-top: 2rem; padding-bottom: 3rem; max-width: 720px; }

/* CAPÇALERA */
.header-block {
    text-align: center;
    padding: 2.5rem 1rem 1.5rem;
    border-bottom: 1px solid rgba(139,100,60,0.2);
    margin-bottom: 2rem;
}
.header-block .logo-icon {
    font-size: 2.8rem;
    display: block;
    margin-bottom: 0.5rem;
}
.header-block h1 {
    font-family: 'Cormorant Garamond', serif;
    font-size: 2.6rem;
    font-weight: 700;
    color: #3D2B1F;
    letter-spacing: 0.02em;
    margin: 0;
    line-height: 1.1;
}
.header-block p {
    font-size: 0.85rem;
    color: #8B6340;
    letter-spacing: 0.12em;
    text-transform: uppercase;
    margin-top: 0.4rem;
    font-weight: 500;
}

/* TARGETES DE SECCIÓ */
.card {
    background: rgba(255,253,248,0.85);
    border: 1px solid rgba(193,154,107,0.25);
    border-radius: 12px;
    padding: 1.6rem 1.8rem;
    margin-bottom: 1.2rem;
    backdrop-filter: blur(4px);
    box-shadow: 0 2px 12px rgba(61,43,31,0.06);
}
.card-title {
    font-family: 'Cormorant Garamond', serif;
    font-size: 1.1rem;
    font-weight: 600;
    color: #5C3D2E;
    letter-spacing: 0.06em;
    text-transform: uppercase;
    margin-bottom: 1rem;
    display: flex;
    align-items: center;
    gap: 0.5rem;
}

/* LABELS dels inputs */
.stSelectbox label, .stNumberInput label, .stTextInput label, .stTextArea label {
    font-family: 'DM Sans', sans-serif !important;
    font-size: 0.78rem !important;
    font-weight: 500 !important;
    color: #7A5C44 !important;
    letter-spacing: 0.08em !important;
    text-transform: uppercase !important;
}

/* INPUTS */
.stSelectbox > div > div,
.stTextInput > div > div > input,
.stNumberInput > div > div > input,
.stTextArea > div > div > textarea {
    background-color: #FDFAF5 !important;
    border: 1px solid rgba(193,154,107,0.35) !important;
    border-radius: 8px !important;
    color: #3D2B1F !important;
    font-family: 'DM Sans', sans-serif !important;
    font-size: 0.95rem !important;
}
.stSelectbox > div > div:focus-within,
.stTextInput > div > div:focus-within,
.stNumberInput > div > div:focus-within,
.stTextArea > div > div:focus-within {
    border-color: #C19A6B !important;
    box-shadow: 0 0 0 3px rgba(193,154,107,0.15) !important;
}

/* BOTÓ PRINCIPAL */
.stFormSubmitButton > button, .stButton > button {
    background: linear-gradient(135deg, #8B6340 0%, #C19A6B 100%) !important;
    color: #FDFAF5 !important;
    border: none !important;
    border-radius: 10px !important;
    padding: 0.8rem 2rem !important;
    font-family: 'DM Sans', sans-serif !important;
    font-size: 0.85rem !important;
    font-weight: 500 !important;
    letter-spacing: 0.1em !important;
    text-transform: uppercase !important;
    width: 100% !important;
    transition: all 0.2s ease !important;
    box-shadow: 0 4px 15px rgba(139,100,60,0.3) !important;
    margin-top: 0.5rem !important;
}
.stFormSubmitButton > button:hover, .stButton > button:hover {
    transform: translateY(-1px) !important;
    box-shadow: 0 6px 20px rgba(139,100,60,0.4) !important;
}

/* DIVIDER personalitzat */
.divider {
    border: none;
    border-top: 1px solid rgba(193,154,107,0.2);
    margin: 1.5rem 0;
}

/* BADGE de data */
.date-badge {
    display: inline-block;
    background: rgba(193,154,107,0.12);
    color: #8B6340;
    border-radius: 20px;
    padding: 0.25rem 0.75rem;
    font-size: 0.78rem;
    font-weight: 500;
    letter-spacing: 0.05em;
    margin-bottom: 1.5rem;
}

/* SUCCESS / ERROR */
.stSuccess {
    background-color: rgba(139,100,60,0.08) !important;
    border-color: rgba(139,100,60,0.3) !important;
    color: #5C3D2E !important;
    border-radius: 10px !important;
}
.stError {
    border-radius: 10px !important;
}

/* Spinner */
.stSpinner { color: #C19A6B !important; }

/* Selector de columnes */
[data-testid="column"] { gap: 0.8rem; }
</style>
""", unsafe_allow_html=True)

# ==========================================
# 3. CAPÇALERA
# ==========================================
st.markdown("""
<div class="header-block">
    <span class="logo-icon">🪵</span>
    <h1>Estellé Parquet</h1>
    <p>Sistema de Seguiment d'Obra</p>
</div>
""", unsafe_allow_html=True)

# Badge de data actual
st.markdown(f"""
<div style="text-align:center">
    <span class="date-badge">📅 {datetime.now().strftime("%A, %d de %B de %Y").capitalize()}</span>
</div>
""", unsafe_allow_html=True)

# ==========================================
# 4. CONNEXIÓ GOOGLE SHEETS
# ==========================================
conn = st.connection("gsheets", type=GSheetsConnection)

try:
    df_projectes = conn.read(worksheet="Projectes", ttl=0)
    df_templates = conn.read(worksheet="Config_Templates", ttl=0)
except Exception as e:
    st.error("⚠️ No s'ha pogut connectar amb Google Sheets")
    with st.expander("Veure detall de l'error"):
        st.code(str(e))
    st.markdown("""
    **Comprova:**
    - Que el `secrets.toml` té el format correcte
    - Que el compte de servei té accés **Editor** al document
    - Que els noms de les pestanyes són exactament `Projectes` i `Config_Templates`
    """)
    st.stop()

# ==========================================
# 5. SELECTORS DE PROJECTE I TREBALL
# ==========================================
try:
    df_projectes = df_projectes.dropna(subset=['Nom'])
    df_templates = df_templates.dropna(subset=['Tipus'])
except Exception as e:
    st.error(f"Error en l'estructura de les dades: {e}")
    st.stop()

st.markdown('<div class="card"><div class="card-title">📋 Selecció</div>', unsafe_allow_html=True)

col1, col2 = st.columns(2)
with col1:
    obra_sel = st.selectbox("Projecte", df_projectes['Nom'].unique())
    dades_p = df_projectes[df_projectes['Nom'] == obra_sel].iloc[0]
with col2:
    tipus_sel = st.selectbox("Tipus de treball", df_templates['Tipus'].unique())
    dades_t = df_templates[df_templates['Tipus'] == tipus_sel].iloc[0]

st.markdown('</div>', unsafe_allow_html=True)

# ==========================================
# 6. FORMULARI D'INFORME
# ==========================================
st.markdown(f'<div class="card"><div class="card-title">📝 Informe · {tipus_sel}</div>', unsafe_allow_html=True)

with st.form("form_obra", clear_on_submit=True):

    # Camps dinàmics segons template
    camps_actius = []
    for i, camp_key in enumerate(['Camp1', 'Camp2', 'Camp3'], 1):
        val = dades_t.get(camp_key, "")
        if pd.notna(val) and str(val).strip() != "":
            camps_actius.append((camp_key, str(val)))

    if camps_actius:
        cols = st.columns(len(camps_actius))
        valors = []
        for idx, (_, nom_camp) in enumerate(camps_actius):
            with cols[idx]:
                v = st.number_input(nom_camp, min_value=0.0, step=0.1, format="%.2f")
                valors.append(v)
        # Omplim els que no s'usen
        while len(valors) < 3:
            valors.append(0.0)
        v1, v2, v3 = valors[0], valors[1], valors[2]
    else:
        v1, v2, v3 = 0.0, 0.0, 0.0

    st.markdown('<hr class="divider">', unsafe_allow_html=True)

    comentaris = st.text_area(
        "Comentaris de la jornada",
        placeholder="Descriu el treball realitzat, incidències, observacions...",
        height=100
    )
    operari = st.text_input("Operari responsable", value="Luis")

    subm = st.form_submit_button("✉️ Enviar Informe")

st.markdown('</div>', unsafe_allow_html=True)

# ==========================================
# 7. ENVIAMENT
# ==========================================
if subm:
    if not operari.strip():
        st.warning("⚠️ Cal indicar l'operari responsable.")
        st.stop()

    with st.spinner("Enviant informe..."):
        errors = []

        # A. Guardar a Sheets
        try:
            try:
                df_seg = conn.read(worksheet="Seguiment", ttl=0)
                df_seg = df_seg.dropna(how='all')
            except Exception:
                df_seg = pd.DataFrame(columns=[
                    "Data", "Projecte", "Tipus",
                    "Dada1", "Dada2", "Dada3",
                    "Comentaris", "Operari"
                ])

            nova_fila = pd.DataFrame([{
                "Data": datetime.now().strftime("%d/%m/%Y"),
                "Hora": datetime.now().strftime("%H:%M"),
                "Projecte": obra_sel,
                "Tipus": tipus_sel,
                "Dada1": v1,
                "Dada2": v2,
                "Dada3": v3,
                "Comentaris": comentaris,
                "Operari": operari
            }])

            df_final = pd.concat([df_seg, nova_fila], ignore_index=True)
            conn.update(worksheet="Seguiment", data=df_final)

        except Exception as e:
            errors.append(f"Error en guardar al Sheets: {e}")

        # B. Enviar email
        try:
            smtp = st.secrets["smtp"]
            emails_raw = str(dades_p.get('Emails_Contacte', ''))
            destinataris = [e.strip() for e in emails_raw.split(',') if e.strip()]

            if destinataris:
                msg = MIMEMultipart('alternative')
                msg['Subject'] = f"[Estellé] Seguiment {obra_sel} · {datetime.now().strftime('%d/%m/%Y')}"
                msg['From'] = f"Estellé Parquet <{smtp['user']}>"
                msg['To'] = ", ".join(destinataris)

                # Construir resum de dades
                resum_dades = ""
                for idx, (_, nom_camp) in enumerate(camps_actius):
                    val_camp = [v1, v2, v3][idx]
                    resum_dades += f"<tr><td style='padding:6px 12px;color:#7A5C44;font-size:13px'>{nom_camp}</td><td style='padding:6px 12px;font-weight:600;color:#3D2B1F'>{val_camp}</td></tr>"

                html = f"""
                <!DOCTYPE html>
                <html>
                <body style="margin:0;padding:0;background:#F7F2EA;font-family:'Helvetica Neue',sans-serif">
                <table width="100%" cellpadding="0" cellspacing="0" style="background:#F7F2EA;padding:30px 0">
                <tr><td align="center">
                <table width="580" cellpadding="0" cellspacing="0" style="background:#FDFAF5;border-radius:14px;overflow:hidden;box-shadow:0 4px 20px rgba(61,43,31,0.1)">

                    <!-- Header -->
                    <tr><td style="background:linear-gradient(135deg,#8B6340,#C19A6B);padding:28px 32px;text-align:center">
                        <div style="font-size:28px">🪵</div>
                        <h1 style="color:#FDFAF5;font-size:22px;margin:6px 0 2px;font-weight:700;letter-spacing:1px">Estellé Parquet</h1>
                        <p style="color:rgba(253,250,245,0.8);font-size:11px;letter-spacing:2px;text-transform:uppercase;margin:0">Seguiment d'Obra</p>
                    </td></tr>

                    <!-- Info principal -->
                    <tr><td style="padding:28px 32px 16px">
                        <table width="100%" cellpadding="0" cellspacing="0">
                        <tr>
                            <td width="50%" style="padding-bottom:16px">
                                <div style="font-size:10px;color:#8B6340;letter-spacing:2px;text-transform:uppercase;margin-bottom:4px">Projecte</div>
                                <div style="font-size:17px;font-weight:700;color:#3D2B1F">{obra_sel}</div>
                            </td>
                            <td width="50%" style="padding-bottom:16px">
                                <div style="font-size:10px;color:#8B6340;letter-spacing:2px;text-transform:uppercase;margin-bottom:4px">Treball</div>
                                <div style="font-size:17px;font-weight:700;color:#3D2B1F">{tipus_sel}</div>
                            </td>
                        </tr>
                        <tr>
                            <td>
                                <div style="font-size:10px;color:#8B6340;letter-spacing:2px;text-transform:uppercase;margin-bottom:4px">Data</div>
                                <div style="font-size:15px;color:#5C3D2E">{datetime.now().strftime('%d/%m/%Y · %H:%M')}</div>
                            </td>
                            <td>
                                <div style="font-size:10px;color:#8B6340;letter-spacing:2px;text-transform:uppercase;margin-bottom:4px">Operari</div>
                                <div style="font-size:15px;color:#5C3D2E">{operari}</div>
                            </td>
                        </tr>
                        </table>
                    </td></tr>

                    <!-- Dades mesures -->
                    {f'''
                    <tr><td style="padding:0 32px 16px">
                        <div style="background:#F7F2EA;border-radius:10px;overflow:hidden">
                        <div style="padding:10px 12px;background:rgba(193,154,107,0.15);font-size:10px;color:#8B6340;letter-spacing:2px;text-transform:uppercase;font-weight:600">Mesures</div>
                        <table width="100%" cellpadding="0" cellspacing="0">
                        {resum_dades}
                        </table></div>
                    </td></tr>
                    ''' if resum_dades else ''}

                    <!-- Comentaris -->
                    {f'''
                    <tr><td style="padding:0 32px 24px">
                        <div style="font-size:10px;color:#8B6340;letter-spacing:2px;text-transform:uppercase;margin-bottom:8px">Comentaris</div>
                        <div style="background:#F7F2EA;border-left:3px solid #C19A6B;padding:12px 16px;border-radius:0 8px 8px 0;color:#3D2B1F;font-size:14px;line-height:1.6">{comentaris}</div>
                    </td></tr>
                    ''' if comentaris.strip() else ''}

                    <!-- Footer -->
                    <tr><td style="background:#3D2B1F;padding:16px 32px;text-align:center">
                        <p style="color:rgba(253,250,245,0.5);font-size:11px;margin:0;letter-spacing:1px">Estellé Parquet · Sistema Automatitzat de Seguiment</p>
                    </td></tr>

                </table>
                </td></tr>
                </table>
                </body>
                </html>
                """

                msg.attach(MIMEText(html, 'html'))

                with smtplib.SMTP(smtp['server'], smtp['port']) as s:
                    s.starttls()
                    s.login(smtp['user'], smtp['password'])
                    s.sendmail(smtp['user'], destinataris, msg.as_string())

        except Exception as e:
            errors.append(f"Error en l'enviament d'email: {e}")

        # Resultat final
        if not errors:
            st.success("✅ Informe enviat i guardat correctament!")
            st.balloons()
        else:
            for err in errors:
                st.error(err)
