import streamlit as st
import pandas as pd
from datetime import datetime, timedelta

# --- CONFIGURATION FIXE ---
BUREAU = "18 Mon Repos"
AGENTS = ["Celine", "Maria Claret", "Maria Elisabeth"]

INFOS_BATIMENTS = {
    'Bethusy A': 'Avenue de Béthusy 54',
    'Bethusy B': 'Avenue de Béthusy 56',
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

# Initialisation
if 'db' not in st.session_state:
    st.session_state.db = pd.DataFrame(columns=['Batiment', 'Date', 'Heure', 'Agent', 'Rue', 'Type', 'Date_Sort'])
if 'conges' not in st.session_state:
    st.session_state.conges = pd.DataFrame(columns=['Agent', 'Date_Debut', 'Date_Fin'])

# --- FONCTIONS LOGIQUES ---
def est_disponible(agent, date_cible_str):
    if st.session_state.conges.empty: return True
    date_cible = pd.to_datetime(date_cible_str, dayfirst=True)
    for _, conge in st.session_state.conges[st.session_state.conges['Agent'] == agent].iterrows():
        debut = pd.to_datetime(conge['Date_Debut'], dayfirst=True)
        fin = pd.to_datetime(conge['Date_Fin'], dayfirst=True)
        if debut <= date_cible <= fin: return False
    return True

def trouver_meilleur_creneau(batiment, date_str, temp_db):
    rue_cible = INFOS_BATIMENTS.get(batiment, "Autre")
    missions_jour = temp_db[temp_db['Date'] == date_str]
    pause_debut, pause_fin = datetime.strptime("12:00", "%H:%M"), datetime.strptime("13:00", "%H:%M")
    def ajuster_pause(h): return pause_fin if h > pause_debut and h < pause_fin else h

    presents = [a for a in AGENTS if est_disponible(a, date_str)]
    if not presents: return "À définir (Tous absents)", "08:15"

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
    return presents[0], "Surcharge"

# --- INTERFACE ---
st.title("📍 Unité Logement : Optimisation Attibutions")
tab_plan, tab_cal, tab_stats = st.tabs(["📝 Saisie & Liste", "📅 Vue Calendrier (Outlook)", "📊 Analyses"])

# --- SIDEBAR ---
with st.sidebar:
    st.header("🌴 Congés")
    abs_agent = st.selectbox("Collaboratrice", AGENTS)
    c1, c2 = st.columns(2)
    with c1: a_deb = st.date_input("Du")
    with c2: a_fin = st.date_input("Au")
    if st.button("Valider absence"):
        st.session_state.conges = pd.concat([st.session_state.conges, pd.DataFrame([{'Agent': abs_agent, 'Date_Debut': a_deb.strftime('%d/%m/%Y'), 'Date_Fin': a_fin.strftime('%d/%m/%Y')}])], ignore_index=True)
    
    st.divider()
    st.header("📥 Import Excel")
    uploaded = st.file_uploader("Fichier .xlsx", type=['xlsx'])
    if uploaded and st.button("🚀 Planifier Avril"):
        df_ex = pd.read_excel(uploaded).dropna(how='all').fillna('')
        df_ex.columns = df_ex.columns.str.strip()
        col_d = next((c for c in df_ex.columns if 'date' in c.lower()), 'Date')
        temp_db = pd.DataFrame(columns=['Batiment', 'Date', 'Heure', 'Agent', 'Rue', 'Type', 'Date_Sort'])
        for _, row in df_ex.sort_values(by=[col_d, 'Batiment']).iterrows():
            dt = pd.to_datetime(row[col_d]); d_s = dt.strftime('%d/%m/%Y')
            agt, hr = trouver_meilleur_creneau(row['Batiment'], d_s, temp_db)
            temp_db = pd.concat([temp_db, pd.DataFrame([{'Batiment': row['Batiment'], 'Date': d_s, 'Heure': hr, 'Agent': agt, 'Rue': INFOS_BATIMENTS.get(row['Batiment'], "Autre"), 'Type': "Import", 'Date_Sort': dt}])], ignore_index=True)
        st.session_state.db = temp_db
        st.rerun()
    
    if st.button("🗑️ Reset Général"):
        st.session_state.db = pd.DataFrame(columns=['Batiment', 'Date', 'Heure', 'Agent', 'Rue', 'Type', 'Date_Sort'])
        st.rerun()

# --- TAB 1 : LISTE ---
with tab_plan:
    st.subheader("📋 Liste des missions")
    if not st.session_state.db.empty:
        df_v = st.session_state.db.sort_values(by=['Date_Sort', 'Heure'])
        st.table(df_v[['Date', 'Heure', 'Agent', 'Batiment', 'Rue']].style.apply(lambda r: [f'background-color: {COULEURS.get(r["Agent"])}']*len(r), axis=1))

# --- TAB 2 : CALENDRIER (TYPE OUTLOOK) ---
with tab_cal:
    st.subheader("📅 Vue Planning Journalière")
    if not st.session_state.db.empty:
        # Choix du jour à afficher
        jours_dispos = sorted(st.session_state.db['Date'].unique())
        jour_selectionne = st.selectbox("Choisir une date à visualiser :", jours_dispos)
        
        st.write(f"### 🗓️ Détails du {jour_selectionne}")
        
        # Création de 3 colonnes (une par agent)
        cols = st.columns(3)
        
        for i, agent in enumerate(AGENTS):
            with cols[i]:
                st.markdown(f"<div style='text-align:center; background-color:{COULEURS[agent]}; padding:10px; border-radius:5px; font-weight:bold; color: black;'>{agent}</div>", unsafe_allow_html=True)
                
                # Missions de l'agent ce jour-là
                missions_du_jour = st.session_state.db[(st.session_state.db['Date'] == jour_selectionne) & (st.session_state.db['Agent'] == agent)]
                missions_du_jour = missions_du_jour.sort_values(by='Heure')
                
                if missions_du_jour.empty:
                    st.info("Aucune mission")
                else:
                    for _, row in missions_du_jour.iterrows():
                        # Affichage style "Bloc Calendrier"
                        st.markdown(f"""
                        <div style='border-left: 5px solid gray; background-color: #f9f9f9; padding: 10px; margin-top: 10px; border-radius: 3px; color: black;'>
                            <b style='color: #333;'>{row['Heure']}</b><br>
                            🏢 {row['Batiment']}<br>
                            📍 {row['Rue']}
                        </div>
                        """, unsafe_allow_html=True)
    else:
        st.info("Importez des données pour afficher le calendrier.")

# --- TAB 3 : ANALYSES ---
with tab_stats:
    st.subheader("📊 Performance")
    if not st.session_state.db.empty:
        nb = len(st.session_state.db)
        st.metric("Total Missions", nb)
        st.bar_chart(st.session_state.db['Agent'].value_counts())
