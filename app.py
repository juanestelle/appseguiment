def enviar_email(projecte, logo_client, dades, comentaris, responsable):
    # Dades de configuració (Això aniria a Streamlit Secrets)
    SMTP_SERVER = "smtp.gmail.com" 
    SMTP_PORT = 587
    SENDER_EMAIL = "la_teva_cuenta@gmail.com"
    SENDER_PASSWORD = "tu_app_password" # Contrasenya d'aplicació de Google

    msg = MIMEMultipart('alternative')
    msg['Subject'] = f"Seguiment d'Obra: {projecte} - {datetime.now().strftime('%d/%m/%Y')}"
    msg['From'] = f"Estellé Parquet <{SENDER_EMAIL}>"
    msg['To'] = "email_del_client@dominio.com" # Agafat del Sheets

    html = f"""
    <html>
    <body style="font-family: 'Helvetica', sans-serif; background-color: #fdfaf4; padding: 20px;">
        <div style="max-width: 600px; margin: auto; background: white; border-radius: 8px; padding: 40px; border: 1px solid #eee;">
            <div style="text-align: center; margin-bottom: 20px;">
                <img src="{logo_client}" width="150" style="margin-bottom: 10px;">
                <p style="color: #888; font-size: 12px;">PROYECTO: {projecte}</p>
            </div>
            <div style="border-top: 1px solid #eee; padding-top: 20px;">
                <h2 style="color: #6a5acd; text-align: center;">TRABAJOS</h2>
                <div style="display: flex; justify-content: space-around; text-align: center;">
                    <div><strong>{dades[0]}</strong><br><span style="color:#888;">{dades[1]}</span></div>
                </div>
            </div>
            <div style="margin-top: 30px;">
                <p><strong>COMENTARIOS:</strong> {comentaris}</p>
            </div>
            <div style="margin-top: 40px; font-size: 12px; color: #aaa; text-align: center;">
                Responsable en obra: {responsable}<br>
                Estellé Parquet - Seguiment Digital
            </div>
        </div>
    </body>
    </html>
    """
    msg.attach(MIMEText(html, 'html'))
    
    with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
        server.starttls()
        server.login(SENDER_EMAIL, SENDER_PASSWORD)
        server.send_message(msg)
