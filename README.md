# Aplicació Estellé Parquet - Seguiment de Projectes

Aquesta aplicació permet als equips d'instal·lació d'Estellé Parquet registrar i seguir el progrés dels projectes de parquet, incloent-hi fotografies, mesures i signatures.

## Funcionalitats principals

- **Autenticació per PIN**: Accés restringit per equips d'instal·lació
- **Selecció de projectes**: Llistat de projectes assignats a cada equip
- **Registre de treballs**: Entrada de mesures i descripció de treballs realitzats
- **Galeria de fotografies**: Captura i pujada d'imatges del procés
- **Signatures digitals**: Captura de signatures del responsable i del client
- **Integració amb Google Sheets**: Dades emmagatzemades automàticament
- **Notificacions per correu**: Enviament automàtic d'informes

## Arquitectura

L'aplicació es basa en el patró de disseny orientat a objectes, dividint la funcionalitat en mètodes específics per millorar la mantenibilitat i la comprensió del codi.

### Classes principals

- `EstelleParquetApp`: Classe principal que encapsula tota la lògica de l'aplicació

### Mòduls utilitzats

- `streamlit`: Framework per a la interfície web
- `pandas`: Manipulació de dades
- `PIL`: Processament d'imatges
- `google-sheets-api`: Connexió amb Google Sheets
- `smtplib`: Enviament de correus electrònics

## Variables d'entorn

Cal definir les següents variables dins del fitxer `secrets.toml` de Streamlit:

```toml
[smtp]
server = "smtp.gmail.com"
port = 587
user = "el_teu_correu@gmail.com"
password = "la_teua_clau_d_app"
```

## Instal·lació

1. Clona el repositori
2. Instal·la les dependències: `pip install -r requirements.txt`
3. Configura les credencials de Google Sheets
4. Executa l'aplicació: `streamlit run app_refactor.py`

## Contribució

Per contribuir a aquest projecte, si us plau segueix les següents passes:

1. Bifurca el repositori
2. Crea una branca per a la nova funcionalitat (`git checkout -b feature/nova-funcionalitat`)
3. Fes commit de canvis (`git commit -am 'Afegir nova funcionalitat'`)
4. Puja la branca (`git push origin feature/nova-funcionalitat`)
5. Obre un pull request

## Llicència

Aquest projecte està llicenciat sota la llicència MIT - veure el fitxer [LICENSE](LICENSE) per als detalls.