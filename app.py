import streamlit as st
import pandas as pd
from datetime import datetime, timedelta

# --- CONFIGURATION FIXE ---
BUREAU = "Mon Paisible 18, 1007 Lausanne"
AGENTS = ["Celine", "Maria Claret", "Maria Elisabeth"]

INFOS_BATIMENTS = {
    'Bethusy A': 'Avenue de Béthusy 84',
    'Bethusy B': 'Avenue de Béthusy 86',
    'Montolieu A': 'Isabelle-de-Montolieu 90',
    'Montolieu B': 'Isabelle-de-Montolieu 92',
    'Tunnel': 'Rue du Tunnel 17',
    'Oron': "Route d'Oron 77"
}

COULEURS = {
    "Celine": "#d1e9ff",
    "Maria Claret": "#ffdae0",
    "Maria Elisabeth": "#d4f8d4",
    "À définir": "#eeeeee"
}

st.set_page_config(page_title="Unité Logement - Planning Pro", layout="wide")

# Initialisation des variables de session (très important pour ne pas perdre les données)
if 'db' not in st.session_state:
    st.session_state.db = pd.DataFrame(columns=['Batiment', 'Date', 'Heure', 'Agent', 'Rue', 'Type', 'Date_Sort'])
if 'conges' not in st.session_state:
    st.session_state.conges = pd.DataFrame(columns=['Agent', 'Date_Debut', 'Date_Fin'])

# --- FONCTION DE DISPONIBILITÉ ---
def est_disponible(agent, date_cible_str):
    if st.session_state.conges.empty: return True
    try:
        date_cible = pd.to_datetime(date_cible_str, dayfirst=True)
        for _, conge in st.session_state.conges[st.session_state.conges['Agent'] == agent].iterrows():
            debut = pd.to_datetime(conge['Date_Debut'], dayfirst=True)
            fin = pd.to_datetime(conge['Date_Fin'], dayfirst=True)
            if debut <= date_cible <= fin: return False
    except: pass
    return True

# --- MOTEUR D'ATTRIBUTION ---
def trouver_meilleur_creneau(batiment, date_str, temp_db):
    rue_cible = INFOS_BATIMENTS.get(batiment, "Autre")
    missions_jour = temp_db[temp_db['Date'] == date_str]
    pause_debut, pause_fin = datetime.strptime("12:00", "%H:%M"), datetime.strptime("13:00", "%H:%M")
    
    def ajuster_pause(h): 
        return pause_fin if h > pause_debut and h < pause_fin else h

    presents = [a for a in AGENTS if est_disponible(a, date_str)]
    if not presents: return "À définir", "08:15"

    if "Celine" in presents:
        m_rue = missions_jour[(missions_jour['Agent'] == "Celine") & (missions_jour['Rue'] == rue_cible)]
        if not m_rue.empty:
            h_f = datetime.strptime(m_rue.sort_values(by='Heure').iloc[-1]['Heure'], "%H:%M") + timedelta(hours=1, minutes=20)
            return "Celine", ajuster_pause(h_f).strftime("%H:%M")
        m_celine = missions_jour[missions_jour['Agent'] == "Celine"]
        if m_celine.empty: return "Celine", "08:15"
        h_f_c = datetime.strptime(m_celine.sort_values(by='Heure').iloc[-1]['Heure'], "%H:%M") + timedelta(hours=1, minutes=45)
        if h_f_c < datetime.strptime("15:30", "%H:%M"): return "Celine", ajuster_pause(h_f_c).strftime("%H:%M")

    for agt in [a for a in ["Maria Claret", "Maria Elisabeth"] if a in presents]:
        m_agt = missions_jour[missions_jour['Agent'] == agt]
        if m_agt.empty: return agt, "08:15"
        h_f_a = datetime.strptime(m_agt.sort_values(by='Heure').iloc[-1]['Heure'], "%H:%M") + timedelta(hours=1, minutes=45)
        if h_f_a < datetime.strptime("16:00", "%H:%M"): return agt, ajuster_pause(h_f_a).strftime("%H:%M")
    
    return presents[0], "08:15"

# --- INTERFACE ---
st.title("📍 Unité Logement : Gestion & Planning")
tab_plan, tab_cal, tab_stats = st.tabs(["📝 Saisie & Liste", "📅 Vue Calendrier", "📊 Analyses"])

# --- SIDEBAR : CONGÉS ET IMPORTS ---
with st.sidebar:
    st.header("🌴 Gestion des Absences")
    abs_agent = st.selectbox("Collaboratrice absente", AGENTS)
    c1, c2 = st.columns(2)
    with c1: a_deb = st.date_input("Du", value=datetime.now())
    with c2: a_fin = st.date_input("Au", value=datetime.now())
    
    if st.button("✅ Enregistrer l'absence"):
        nouv = pd.DataFrame([{
            'Agent': abs_agent, 
            'Date_Debut': a_deb.strftime('%d/%m/%Y'), 
            'Date_Fin': a_fin.strftime('%d/%m/%Y')
        }])
        st.session_state.conges = pd.concat([st.session_state.conges, nouv], ignore_index=True)
        st.success(f"Absence enregistrée pour {abs_agent}")

    if not st.session_state.conges.empty:
        st.write("---")
        st.write("**Absences validées :**")
        st.dataframe(st.session_state.conges, hide_index=True)
        if st.button("🗑️ Effacer les absences"):
            st.session_state.conges = pd.DataFrame(columns=['Agent', 'Date_Debut', 'Date_Fin'])
            st.rerun()

    st.divider()
    st.header("📥 Import Excel")
    uploaded = st.file_uploader("Fichier .xlsx", type=['xlsx'])
    if uploaded and st.button("🚀 Planifier Avril"):
        df_ex = pd.read_excel(uploaded).dropna(how='all').fillna('')
        df_ex.columns = df_ex.columns.str.strip()
        col_d = next((c for c in df_ex.columns if 'date' in c.lower()), 'Date')
        
        temp_db = pd.DataFrame(columns=['Batiment', 'Date', 'Heure', 'Agent', 'Rue', 'Type', 'Date_Sort'])
        for _, row in df_ex.sort_values(by=[col_d, 'Batiment']).iterrows():
            dt = pd.to_datetime(row[col_d])
            d_s = dt.strftime('%d/%m/%Y')
            agt, hr = trouver_meilleur_creneau(row['Batiment'], d_s, temp_db)
            temp_db = pd.concat([temp_db, pd.DataFrame([{
                'Batiment': row['Batiment'], 'Date': d_s, 'Heure': hr, 
                'Agent': agt, 'Rue': INFOS_BATIMENTS.get(row['Batiment'], "Autre"), 
                'Type': "Import", 'Date_Sort': dt
            }])], ignore_index=True)
        st.session_state.db = temp_db
        st.rerun()

# --- LES ONGLETS (CONTENU) ---
with tab_plan:
    with st.expander("➕ AJOUTER UN DOSSIER MANUELLEMENT"):
        # ... (Code du formulaire manuel)
        c1, c2 = st.columns(2)
        with c1:
            n_bat = st.selectbox("Bâtiment", list(INFOS_BATIMENTS.keys()))
            n_date = st.date_input("Date du RDV")
        with c2:
            s_agt, s_hr = trouver_meilleur_creneau(n_bat, n_date.strftime('%d/%m/%Y'), st.session_state.db)
            f_agt = st.selectbox("Agent recommandé", AGENTS, index=AGENTS.index(s_agt) if s_agt in AGENTS else 0)
            f_hr = st.text_input("Heure du RDV", value=s_hr)
        if st.button("💾 Enregistrer"):
            nouv_l = {'Batiment': n_bat, 'Date': n_date.strftime('%d/%m/%Y'), 'Heure': f_hr, 'Agent': f_agt, 'Rue': INFOS_BATIMENTS.get(n_bat, "Autre"), 'Type': "Manuel", 'Date_Sort': pd.to_datetime(n_date)}
            st.session_state.db = pd.concat([st.session_state.db, pd.DataFrame([nouv_l])], ignore_index=True)
            st.rerun()

    if not st.session_state.db.empty:
        st.table(st.session_state.db.sort_values(by=['Date_Sort', 'Heure']).style.apply(lambda r: [f'background-color: {COULEURS.get(r["Agent"])}']*len(r), axis=1))

with tab_cal:
    # ... (Code de la vue calendrier)
    if not st.session_state.db.empty:
        sel_j = st.selectbox("Choisir le jour :", sorted(st.session_state.db['Date'].unique()))
        cols = st.columns(3)
        for i, agt in enumerate(AGENTS):
            with cols[i]:
                st.markdown(f"<div style='text-align:center; background-color:{COULEURS[agt]}; padding:10px; border-radius:5px;'><b>{agt}</b></div>", unsafe_allow_html=True)
                miss = st.session_state.db[(st.session_state.db['Date'] == sel_j) & (st.session_state.db['Agent'] == agt)].sort_values(by='Heure')
                for _, r in miss.iterrows():
                    st.info(f"**{r['Heure']}** - {r['Batiment']}")
