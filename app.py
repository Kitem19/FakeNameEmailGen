# -*- coding: utf-8 -*-

# ==============================================================================
#                 GENERATORE DI PROFILI FAKE CON EMAIL TEMPORANEA
# ==============================================================================
# Versione 4: Corregge il flusso di interazione con l'API di mail.tm.
# Il processo corretto è:
# 1. Creare un account (`POST /accounts`)
# 2. Effettuare il login per ottenere un token (`POST /token`)
# Questo risolve il `KeyError: 'token'` precedente.
#
# Per eseguirlo:
# 1. Assicurati di avere le librerie: pip install streamlit pandas faker requests
# 2. Salva come `app.py` e esegui: streamlit run app.py
# ==============================================================================

import random
import string
import requests
import pandas as pd
import streamlit as st
from faker import Faker

# --- CONFIGURAZIONE INIZIALE DELLA PAGINA ---
st.set_page_config(
    page_title="Generatore Profili Fake",
    page_icon="👤",
    layout="centered"
)

# --- LISTA IBAN ---
PREDEFINED_IBANS = {
    'IT': ['IT60X0542811101000000123456', 'IT12A0306912345100000067890', 'IT75U0306909606100000012345', 'IT33N0306909606100000065432'],
    'FR': ['FR1420041010050500013M02606', 'FR7630006000011234567890189'],
    'DE': ['DE89370400440532013000', 'DE02100100100006820101'],
    'LU': ['LU280019400644750000', 'LU120010001234567891']
}

# --- FUNZIONI API PER mail.tm ---
API_MAILTM = "https://api.mail.tm"
REQUESTS_HEADERS = {'Accept': 'application/json', 'Content-Type': 'application/json'}

def create_temp_email_mailtm():
    """Crea un account email su mail.tm e ottiene un token di autenticazione."""
    try:
        # --- PASSO 1: Ottieni un dominio disponibile ---
        domains_response = requests.get(f"{API_MAILTM}/domains", headers=REQUESTS_HEADERS)
        domains_response.raise_for_status()
        # Prendiamo il primo dominio dalla lista
        domain = domains_response.json()['hydra:member'][0]['domain']

        # Genera un nome utente e una password casuali
        username = ''.join(random.choices(string.ascii_lowercase + string.digits, k=12))
        password = ''.join(random.choices(string.ascii_letters + string.digits, k=16))
        address = f"{username}@{domain}"
        
        account_data = {'address': address, 'password': password}

        # --- PASSO 2: Crea l'account ---
        account_response = requests.post(f"{API_MAILTM}/accounts", json=account_data, headers=REQUESTS_HEADERS)
        account_response.raise_for_status()
        
        # --- PASSO 3: Richiedi il token (effettua il "login") ---
        token_response = requests.post(f"{API_MAILTM}/token", json=account_data, headers=REQUESTS_HEADERS)
        token_response.raise_for_status()
        
        # Ora la risposta CONTIENE il token
        token = token_response.json()['token']
        
        return {'address': address, 'token': token}

    except requests.exceptions.RequestException as e:
        st.error(f"Errore durante la creazione dell'email con mail.tm: {e}")
        # Aggiungo un debug per vedere la risposta in caso di errore
        if e.response:
            st.json(e.response.json())
        return None

def show_inbox_mailtm(address, token):
    """Usa il token per leggere la casella di posta di un indirizzo mail.tm."""
    if not address or not token:
        return

    st.markdown("---")
    st.subheader(f"📬 Casella di posta per: `{address}`")
    
    if st.button("🔄 Controlla/Aggiorna messaggi"):
        with st.spinner("Recupero messaggi da mail.tm..."):
            try:
                auth_header = {**REQUESTS_HEADERS, 'Authorization': f'Bearer {token}'}
                
                messages_response = requests.get(f"{API_MAILTM}/messages", headers=auth_header, timeout=20)
                messages_response.raise_for_status()
                messages = messages_response.json()['hydra:member']

                if not messages:
                    st.info("La casella di posta è vuota.")
                    return

                st.success(f"Trovati {len(messages)} messaggi!")
                
                for msg_summary in messages:
                    with st.expander(f"**Da:** {msg_summary['from']['address']} | **Oggetto:** {msg_summary['subject']}"):
                        st.caption(f"Data: {pd.to_datetime(msg_summary['createdAt']).strftime('%d/%m/%Y %H:%M')}")
                        st.text_area("Anteprima del corpo", msg_summary['intro'], height=150, disabled=True)

            except requests.exceptions.RequestException as e:
                st.error(f"Errore durante la lettura della posta da mail.tm: {e}")

# --- FUNZIONI DI LOGICA PER LA GENERAZIONE DEL PROFILO ---
def get_next_iban(country_code):
    country_code_upper = country_code.upper()
    if 'iban_state' not in st.session_state: st.session_state.iban_state = {}
    if country_code_upper not in st.session_state.iban_state or st.session_state.iban_state[country_code_upper]['index'] >= len(st.session_state.iban_state[country_code_upper]['list']):
        iban_list = PREDEFINED_IBANS.get(country_code_upper, ["N/A"]); random.shuffle(iban_list)
        st.session_state.iban_state[country_code_upper] = {'list': iban_list, 'index': 0}
    state = st.session_state.iban_state[country_code_upper]; iban_to_return = state['list'][state['index']]
    st.session_state.iban_state[country_code_upper]['index'] += 1
    return iban_to_return

def generate_single_profile(country_name, additional_fields):
    localizations = {'Italia': 'it_IT', 'Francia': 'fr_FR', 'Germania': 'de_DE', 'Lussemburgo': 'fr_LU'}
    iso_codes = {'Italia': 'IT', 'Francia': 'FR', 'Germania': 'DE', 'Lussemburgo': 'LU'}
    
    locale, iso_code = localizations.get(country_name), iso_codes.get(country_name)
    if not locale: st.error(f"Paese '{country_name}' non supportato."); return pd.DataFrame()

    fake = Faker(locale)
    profile = {}
    profile['Nome'] = fake.first_name()
    profile['Cognome'] = fake.last_name()
    profile['Data di Nascita'] = fake.date_of_birth(minimum_age=18, maximum_age=80).strftime('%d/%m/%Y')
    profile['Indirizzo'] = fake.address().replace("\n", ", ")
    profile['IBAN'] = get_next_iban(iso_code)
    profile['Paese'] = country_name

    if 'Email' in additional_fields:
        # Salva i dati dell'email in una variabile di sessione dedicata
        st.session_state.email_data = create_temp_email_mailtm()
        profile['Email'] = st.session_state.email_data['address'] if st.session_state.email_data else "Creazione email fallita"
    
    if 'Telefono' in additional_fields: profile['Telefono'] = fake.phone_number()
    if 'Codice Fiscale' in additional_fields: profile['Codice Fiscale'] = fake.ssn() if locale == 'it_IT' else 'N/A'
    if 'Partita IVA' in additional_fields: profile['Partita IVA'] = fake.vat_id() if hasattr(fake, 'vat_id') else 'N/A'
    return pd.DataFrame([profile])


# ==============================================================================
#                      INTERFACCIA UTENTE (UI) CON STREAMLIT
# ==============================================================================

st.title("👤 Generatore di Profili Fake")
st.markdown("Crea dati fittizi per test, completi di email temporanea funzionante tramite **mail.tm**.")

with st.sidebar:
    st.header("⚙️ Opzioni di Generazione")
    country_name = st.selectbox('Paese', ('Italia', 'Francia', 'Germania', 'Lussemburgo'))
    num_profiles = st.number_input('Numero di profili', 1, 50, 1)
    additional_fields = st.multiselect('Campi aggiuntivi', ['Email', 'Telefono', 'Codice Fiscale', 'Partita IVA'], default=['Email'])
    
    if st.button("🚀 Genera Profili", type="primary"):
        # Logica di generazione
        all_profiles = []
        progress_bar = st.progress(0, text="Generazione profili in corso...")
        
        for i in range(num_profiles):
            profile_df = generate_single_profile(country_name, additional_fields)
            if not profile_df.empty:
                all_profiles.append(profile_df)
            progress_bar.progress((i + 1) / num_profiles, text=f"Generato profilo {i + 1}/{num_profiles}")

        if all_profiles:
            st.session_state.final_df = pd.concat(all_profiles, ignore_index=True)
        else:
            st.session_state.final_df = None
        
        # Non è necessario un rerun, Streamlit aggiorna la pagina dopo l'esecuzione del blocco del pulsante

# --- Visualizzazione dei risultati ---
if 'final_df' in st.session_state and st.session_state.final_df is not None:
    final_df = st.session_state.final_df
    st.success(f"✅ Generati con successo {len(final_df)} profili.")
    st.dataframe(final_df)
    
    csv = final_df.to_csv(index=False).encode('utf-8')
    st.download_button("📥 Scarica come CSV", csv, f'profili_{country_name.lower()}.csv', 'text/csv')
    
    if 'email_data' in st.session_state and st.session_state.email_data:
        show_inbox_mailtm(st.session_state.email_data['address'], st.session_state.email_data['token'])
else:
     st.info("Configura le opzioni nella barra laterale e clicca su 'Genera Profili'.")
