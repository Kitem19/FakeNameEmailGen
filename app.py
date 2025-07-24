# -*- coding: utf-8 -*-

# ==============================================================================
#                 GENERATORE DI PROFILI FAKE CON EMAIL TEMPORANEA
# ==============================================================================
# Versione Corretta: include l'header User-Agent per prevenire l'errore 403 Forbidden
# quando l'app è ospitata su servizi cloud come Streamlit Cloud.
#
# Per eseguirlo:
# 1. Assicurati di avere le librerie necessarie:
#    pip install streamlit pandas faker requests
# 2. Salva questo codice come `app.py`.
# 3. Esegui da terminale: `streamlit run app.py`
# ==============================================================================

import random
import requests
import pandas as pd
import streamlit as st
from faker import Faker

# --- CONFIGURAZIONE INIZIALE DELLA PAGINA STREAMLIT ---
st.set_page_config(
    page_title="Generatore Profili Fake",
    page_icon="👤",
    layout="centered"
)

# --- LISTA PREDEFINITA DI IBAN PER PAESE ---
PREDEFINED_IBANS = {
    'IT': [
        'IT60X0542811101000000123456', 'IT12A0306912345100000067890',
        'IT75U0306909606100000012345', 'IT33N0306909606100000065432'
    ],
    'FR': [
        'FR1420041010050500013M02606', 'FR7630006000011234567890189'
    ],
    'DE': [
        'DE89370400440532013000', 'DE02100100100006820101'
    ],
    'LU': [
        'LU280019400644750000', 'LU120010001234567891'
    ]
}

# --- FUNZIONI DI SUPPORTO PER L'API DI EMAIL TEMPORANEA (1secmail.com) ---
API_1SECMAIL = "https://www.1secmail.com/api/v1/"
# Definiamo un header che simula un browser comune per evitare blocchi 403.
REQUESTS_HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
}

def get_temp_email_from_api():
    """Chiama l'API di 1secmail per generare un indirizzo email casuale."""
    try:
        response = requests.get(
            f"{API_1SECMAIL}?action=genRandomMailbox&count=1", 
            headers=REQUESTS_HEADERS
        )
        response.raise_for_status()
        email_address = response.json()[0]
        return email_address
    except requests.exceptions.RequestException as e:
        if e.response and e.response.status_code == 403:
            st.error("Errore 403: L'accesso all'API di 1secmail è stato bloccato. Questo accade spesso quando l'app è ospitata su cloud.")
        else:
            st.error(f"Errore di rete nel contattare 1secmail: {e}")
        return "errore@api.com"

def show_inbox_from_api(email_address):
    """Mostra un pulsante per controllare la posta e visualizzarla."""
    if not email_address or "@" not in email_address or "errore@" in email_address:
        return

    st.markdown("---")
    st.subheader(f"📬 Casella di posta per: `{email_address}`")
    
    if st.button("🔄 Controlla/Aggiorna messaggi"):
        with st.spinner("Recupero messaggi da 1secmail.com..."):
            try:
                login, domain = email_address.split('@')
                
                check_url = f"{API_1SECMAIL}?action=getMessages&login={login}&domain={domain}"
                response_msgs = requests.get(check_url, headers=REQUESTS_HEADERS, timeout=15)
                response_msgs.raise_for_status()
                messages = response_msgs.json()

                if not messages:
                    st.info("La casella di posta è vuota.")
                    return

                st.success(f"Trovati {len(messages)} messaggi!")
                
                for msg_summary in messages:
                    msg_id = msg_summary['id']
                    read_url = f"{API_1SECMAIL}?action=readMessage&login={login}&domain={domain}&id={msg_id}"
                    response_full_msg = requests.get(read_url, headers=REQUESTS_HEADERS, timeout=15)
                    response_full_msg.raise_for_status()
                    full_msg = response_full_msg.json()

                    with st.expander(f"**Da:** {full_msg['from']} | **Oggetto:** {full_msg['subject']}"):
                        st.caption(f"Data: {full_msg['date']}")
                        st.caption(f"ID Messaggio: {full_msg['id']}")
                        
                        body_content = full_msg.get('htmlBody') or f"<pre>{full_msg.get('body')}</pre>"
                        st.components.v1.html(body_content, height=400, scrolling=True)

            except requests.exceptions.RequestException as e:
                st.error(f"Errore durante la comunicazione con 1secmail: {e}")


# --- FUNZIONI DI LOGICA PER LA GENERAZIONE DEL PROFILO ---

def get_next_iban(country_code):
    """Recupera il prossimo IBAN disponibile da una lista mescolata."""
    country_code_upper = country_code.upper()
    
    if 'iban_state' not in st.session_state:
        st.session_state.iban_state = {}

    if country_code_upper not in st.session_state.iban_state or \
       st.session_state.iban_state[country_code_upper]['index'] >= len(st.session_state.iban_state[country_code_upper]['list']):
        
        iban_list = PREDEFINED_IBANS.get(country_code_upper, ["N/A - Lista paese vuota"])
        random.shuffle(iban_list)
        st.session_state.iban_state[country_code_upper] = {'list': iban_list, 'index': 0}

    state = st.session_state.iban_state[country_code_upper]
    iban_to_return = state['list'][state['index']]
    
    st.session_state.iban_state[country_code_upper]['index'] += 1
    
    return iban_to_return


def generate_single_profile(country_name, additional_fields):
    """Genera un singolo profilo fake con tutti i dati richiesti."""
    localizations = {'Italia': 'it_IT', 'Francia': 'fr_FR', 'Germania': 'de_DE', 'Lussemburgo': 'fr_LU'}
    iso_codes = {'Italia': 'IT', 'Francia': 'FR', 'Germania': 'DE', 'Lussemburgo': 'LU'}
    
    locale = localizations.get(country_name)
    iso_code = iso_codes.get(country_name)
    
    if not locale:
        st.error(f"Paese '{country_name}' non supportato.")
        return pd.DataFrame()

    fake = Faker(locale)
    profile = {}

    profile['Nome'] = fake.first_name()
    profile['Cognome'] = fake.last_name()
    profile['Data di Nascita'] = fake.date_of_birth(minimum_age=18, maximum_age=80).strftime('%d/%m/%Y')
    profile['Indirizzo'] = fake.address().replace("\n", ", ")
    profile['IBAN'] = get_next_iban(iso_code)
    profile['Paese'] = country_name

    if 'Email' in additional_fields:
        profile['Email'] = get_temp_email_from_api()
    if 'Telefono' in additional_fields:
        profile['Telefono'] = fake.phone_number()
    if 'Codice Fiscale' in additional_fields:
        profile['Codice Fiscale'] = fake.ssn() if locale == 'it_IT' else 'N/A (Solo Italia)'
    if 'Partita IVA' in additional_fields:
        profile['Partita IVA'] = fake.vat_id() if hasattr(fake, 'vat_id') else 'N/A'

    return pd.DataFrame([profile])


# ==============================================================================
#                      INTERFACCIA UTENTE (UI) CON STREAMLIT
# ==============================================================================

st.title("👤 Generatore di Profili Fake")
st.markdown("Crea dati fittizi per test, completi di email temporanea funzionante.")

with st.sidebar:
    st.header("⚙️ Opzioni di Generazione")
    
    country_name = st.selectbox(
        'Seleziona il Paese',
        ('Italia', 'Francia', 'Germania', 'Lussemburgo')
    )
    
    num_profiles = st.number_input(
        'Numero di profili da generare',
        min_value=1,
        max_value=50,
        value=1,
        step=1
    )
    
    additional_fields = st.multiselect(
        'Campi aggiuntivi da includere',
        ['Email', 'Telefono', 'Codice Fiscale', 'Partita IVA'],
        default=['Email']
    )
    
    generate_button = st.button("🚀 Genera Profili", type="primary")

if generate_button:
    all_profiles = []
    progress_bar = st.progress(0, text="Generazione profili in corso...")
    
    for i in range(num_profiles):
        profile_df = generate_single_profile(country_name, additional_fields)
        if not profile_df.empty:
            all_profiles.append(profile_df)
        progress_bar.progress((i + 1) / num_profiles, text=f"Generato profilo {i + 1}/{num_profiles}")

    if all_profiles:
        final_df = pd.concat(all_profiles, ignore_index=True)
        
        st.success(f"✅ Generati con successo {len(final_df)} profili.")
        st.dataframe(final_df)
        
        csv = final_df.to_csv(index=False).encode('utf-8')
        st.download_button(
           label="📥 Scarica come CSV",
           data=csv,
           file_name=f'profili_generati_{country_name.lower()}.csv',
           mime='text/csv',
        )
        
        if num_profiles == 1 and 'Email' in final_df.columns:
            email_address = final_df['Email'].iloc[0]
            show_inbox_from_api(email_address)

else:
    st.info("Configura le opzioni nella barra laterale e clicca su 'Genera Profili'.")
