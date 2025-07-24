# -*- coding: utf-8 -*-
import random
import string
import requests
import pandas as pd
import streamlit as st
from faker import Faker
import xml.etree.ElementTree as ET

st.set_page_config(page_title="Generatore Profili Fake", page_icon="👤", layout="centered")

# --- IBAN predefiniti per paese ---
PREDEFINED_IBANS = {
    'IT': ['IT60X0542811101000000123456', 'IT12A0306912345100000067890', 'IT75U0306909606100000012345'],
    'FR': ['FR1420041010050500013M02606', 'FR7630006000011234567890189'],
    'DE': ['DE89370400440532013000', 'DE02100100100006820101'],
    'LU': ['LU280019400644750000', 'LU120010001234567891']
}

API_MAILTM = "https://api.mail.tm"
REQUESTS_HEADERS = {'Accept': 'application/xml', 'Content-Type': 'application/json'}

def create_temp_email_mailtm():
    """Crea un account email su mail.tm, compatibile con risposta XML."""
    try:
        # --- PASSO 1: Recupera dominio da risposta XML ---
        resp = requests.get(f"{API_MAILTM}/domains", headers=REQUESTS_HEADERS)
        resp.raise_for_status()
        xml_root = ET.fromstring(resp.text)
        domain_el = xml_root.find(".//domain")
        if domain_el is None:
            st.error("❌ Nessun dominio trovato nella risposta XML.")
            return None
        domain = domain_el.text.strip()

        # --- PASSO 2: Genera account casuale ---
        username = ''.join(random.choices(string.ascii_lowercase + string.digits, k=12))
        password = ''.join(random.choices(string.ascii_letters + string.digits, k=16))
        address = f"{username}@{domain}"
        account_data = {'address': address, 'password': password}

        r = requests.post(f"{API_MAILTM}/accounts", json=account_data, headers={'Accept': 'application/json'})
        r.raise_for_status()

        t = requests.post(f"{API_MAILTM}/token", json=account_data, headers={'Accept': 'application/json'})
        t.raise_for_status()
        token = t.json()['token']

        return {'address': address, 'token': token}
    except Exception as e:
        st.error(f"Errore nella creazione dell’email: {e}")
        return None

def show_inbox_mailtm(address, token):
    """Mostra i messaggi email da mail.tm"""
    if not address or not token: return
    st.markdown("---")
    st.subheader(f"📬 Casella di posta per: `{address}`")
    
    if st.button("🔄 Controlla/Aggiorna messaggi"):
        with st.spinner("Recupero messaggi da mail.tm..."):
            try:
                headers = {'Authorization': f'Bearer {token}', 'Accept': 'application/json'}
                messages_response = requests.get(f"{API_MAILTM}/messages", headers=headers, timeout=20)
                messages_response.raise_for_status()
                messages = messages_response.json().get('hydra:member', [])

                if not messages:
                    st.info("📭 Nessun messaggio trovato.")
                else:
                    for msg in reversed(messages):
                        with st.expander(f"**Da:** {msg.get('from', {}).get('address', 'N/A')} | **Oggetto:** {msg.get('subject', 'Senza oggetto')}"):
                            date_str = pd.to_datetime(msg.get('createdAt')).strftime('%d/%m/%Y %H:%M')
                            st.caption(f"📅 Data: {date_str}")
                            st.text_area("📨 Contenuto", msg.get('intro', ''), height=150, disabled=True, key=msg['id'])
            except Exception as e:
                st.error(f"Errore nella lettura della posta: {e}")

def get_next_iban(country_code):
    cc = country_code.upper()
    if 'iban_state' not in st.session_state: st.session_state.iban_state = {}
    if cc not in st.session_state.iban_state or st.session_state.iban_state[cc]['index'] >= len(st.session_state.iban_state[cc]['list']):
        lst = PREDEFINED_IBANS.get(cc, ["N/A"]); random.shuffle(lst)
        st.session_state.iban_state[cc] = {'list': lst, 'index': 0}
    st.session_state.iban_state[cc]['index'] += 1
    return st.session_state.iban_state[cc]['list'][st.session_state.iban_state[cc]['index'] - 1]

def generate_single_profile(country_name, additional_fields):
    localizations = {'Italia': 'it_IT', 'Francia': 'fr_FR', 'Germania': 'de_DE', 'Lussemburgo': 'fr_LU'}
    iso_codes = {'Italia': 'IT', 'Francia': 'FR', 'Germania': 'DE', 'Lussemburgo': 'LU'}
    locale, iso_code = localizations.get(country_name), iso_codes.get(country_name)
    if not locale: st.error(f"Paese '{country_name}' non supportato."); return pd.DataFrame()

    fake = Faker(locale); profile = {}
    profile['Nome'] = fake.first_name()
    profile['Cognome'] = fake.last_name()
    profile['Data di Nascita'] = fake.date_of_birth(minimum_age=18, maximum_age=80).strftime('%d/%m/%Y')
    profile['Indirizzo'] = fake.address().replace("\n", ", ")
    profile['IBAN'] = get_next_iban(iso_code)
    profile['Paese'] = country_name

    if 'Email' in additional_fields:
        st.session_state.email_data = create_temp_email_mailtm()
        profile['Email'] = st.session_state.email_data['address'] if st.session_state.email_data else "Creazione email fallita"
    
    if 'Telefono' in additional_fields: profile['Telefono'] = fake.phone_number()
    if 'Codice Fiscale' in additional_fields: profile['Codice Fiscale'] = fake.ssn() if locale == 'it_IT' else 'N/A'
    if 'Partita IVA' in additional_fields: profile['Partita IVA'] = fake.vat_id() if hasattr(fake, 'vat_id') else 'N/A'
    return pd.DataFrame([profile])

# --- UI Streamlit ---
st.title("👤 Generatore di Profili Fake")
st.markdown("Crea dati fittizi per test, completi di email temporanea funzionante tramite **mail.tm**.")

if 'final_df' not in st.session_state: st.session_state.final_df = None
if 'email_data' not in st.session_state: st.session_state.email_data = None

with st.sidebar:
    st.header("⚙️ Opzioni di Generazione")
    country_name = st.selectbox('Paese', ('Italia', 'Francia', 'Germania', 'Lussemburgo'))
    num_profiles = st.number_input('Numero di profili', 1, 50, 1)
    additional_fields = st.multiselect('Campi aggiuntivi', ['Email', 'Telefono', 'Codice Fiscale', 'Partita IVA'], default=['Email'])

    if st.button("🚀 Genera Profili", type="primary"):
        with st.spinner("Generazione profili in corso..."):
            all_profiles = [generate_single_profile(country_name, additional_fields) for _ in range(num_profiles)]
        st.session_state.final_df = pd.concat([df for df in all_profiles if not df.empty], ignore_index=True) if any(all_profiles) else None

if st.session_state.final_df is not None:
    st.success(f"✅ Generati {len(st.session_state.final_df)} profili.")
    st.dataframe(st.session_state.final_df)
    csv = st.session_state.final_df.to_csv(index=False).encode('utf-8')
    st.download_button("📥 Scarica come CSV", csv, f'profili_{country_name.lower()}.csv', 'text/csv')

    if st.session_state.email_data and "Creazione email fallita" not in st.session_state.final_df['Email'].iloc[0]:
        show_inbox_mailtm(st.session_state.email_data['address'], st.session_state.email_data['token'])
else:
    st.info("Configura le opzioni nella barra laterale e clicca su 'Genera Profili'.")
