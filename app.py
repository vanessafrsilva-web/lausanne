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

st.set_page_config(page_title="Unité Logement", layout="wide")

if 'db' not in st.session_state:
    st.session_state.db = pd.DataFrame(columns=['Batiment', 'Date', 'Heure', 'Agent', 'Rue', 'Type', 'Date_Sort'])
if 'conges' not in st.session_state:
    st.session_state.conges = pd.DataFrame(columns=['Agent', 'Date_Debut', 'Date_Fin'])

# --- FONCTION DE DISPONIBILITÉ ---
def est_disponible(agent, date_cible_str):
    if st.session_state.conges.empty: return True
    date_cible = pd.to_datetime(date_cible_str, dayfirst=True)
    for _, conge in st.session_state.conges[st.session_state.conges['Agent'] == agent].iterrows():
        debut = pd.to_datetime(conge['Date_Debut'], dayfirst=True)
        fin = pd.to_datetime(conge['Date_Fin'], dayfirst=True)
        if debut <= date_cible <= fin: return False
    return True

# --- MOTEUR D'ATTRIBUTION ---
def trouver_meilleur_creneau(batiment, date_str, temp_db):
    rue_cible = INFOS_BATIMENTS.get(batiment, "Autre")
    missions_jour = temp_db[temp_db['Date'] == date_str]
    pause_debut, pause_fin = datetime.strptime("12:00", "%H:%M"), datetime.strptime("13:00", "%H:%M")
    
    def ajuster_pause(h):
        return pause_fin if h > pause_debut and h < pause_fin else h

    agents_presents = [a for a in AGENTS if est_disponible(a, date_str)]
    if not agents_presents: return "À définir (Tous absents)", "08:15"

    if "Celine" in agents_presents:
        celine_meme_rue = missions_jour[(missions_jour['Agent'] == "Celine") & (missions_jour['Rue'] == rue_cible)]
        if not celine_meme_rue.empty:
            h_fin = datetime.strptime(celine_meme_rue.sort_values(by='Heure').iloc[-1]['Heure'], "%H:%M") + timedelta(hours=1, minutes=20)
            return "Celine", ajuster_pause(h_fin).strftime("%H:%M")
        
        missions_celine = missions_jour[missions_jour['Agent'] == "Celine"]
        if missions_celine.empty: return "Celine", "08:15"
        h_fin_c = datetime.strptime(missions_celine.sort_values(by='Heure').iloc[-1]['Heure'], "%H:%M") + timedelta(hours=1, minutes=45)
        if h_fin_c < datetime.strptime("15:30", "%H:%M"): return "Celine", ajuster_pause(h_fin_c).strftime("%H:%M")

    for agt in [a for a in ["Maria Claret", "Maria Elisabeth"] if a in agents_presents]:
        m_agt = missions_jour[missions_jour['Agent'] == agt]
        if m_agt.empty: return agt, "08:15"
        h_f = datetime.strptime(m_agt.sort_values(by='Heure').iloc[-1]['Heure'], "%H:%M") + timedelta(hours=1, minutes=45)
        if h_f < datetime.strptime("16:00", "%H:%M"): return agt, ajuster_pause(h_f).strftime("%H:%M")

    return agents_presents[0], "Surcharge"

st.title("📍 Unité Logement : Optimisation Attibutions")

# --- BARRE LATÉRALE : ABSENCES + IMPORT + STATS ---
with st.sidebar:
    st.header("🌴 Gestion des Absences")
    abs_agent = st.selectbox("Collaboratrice", AGENTS)
    c_abs1, c_abs2 = st.columns(2)
    with c_abs1: abs_debut = st.date_input("Du", key="debut")
    with c_abs2: abs_fin = st.date_input("Au", key="fin")
    if st.button("Enregistrer l'absence"):
        st.session_state.conges = pd.concat([st.session_state.conges, pd.DataFrame([{'Agent': abs_agent, 'Date_Debut': abs_debut.strftime('%d/%m/%Y'), 'Date_Fin': abs_fin.strftime('%d/%m/%Y')}])], ignore_index=True)
    
    if not st.session_state.conges.empty:
        st.dataframe(st.session_state.conges, hide_index=True)
        if st.button("Effacer les absences"):
            st.session_state.conges = pd.DataFrame(columns=['Agent', 'Date_Debut', 'Date_Fin'])
            st.rerun()

    st.divider()
    st.header("📊 Performance & Import")
    
    # RÉCUPÉRATION DES STATS
    if not st.session_state.db.empty:
        nb_dossiers = len(st.session_state.db)
        groupements = st.session_state.db.groupby(['Date', 'Rue']).size()
        taux = (len(groupements[groupements > 1]) / nb_dossiers * 100) if nb_dossiers > 0 else 0
        
        st.metric("Dossiers planifiés", f"{nb_dossiers}")
        st.metric("Taux d'Optimisation", f"{int(taux)}%", help="Pourcentage de dossiers regroupés dans la même rue le même jour.")
    
    uploaded = st.file_uploader("Fichier Excel", type=['xlsx'])
    if uploaded and st.button("🚀 Planifier Avril"):
        df_ex = pd.read_excel(uploaded).dropna(how='all').fillna('')
        df_ex.columns = df_ex.columns.str.strip()
        col_d = next((c for c in df_ex.columns if 'date' in c.lower()), 'Date')
        temp_db = pd.DataFrame(columns=['Batiment', 'Date', 'Heure', 'Agent', 'Rue', 'Type', 'Date_Sort'])
        for _, row in df_ex.sort_values(by=[col_d, 'Batiment']).iterrows():
            date_dt = pd.to_datetime(row[col_d])
            d_str = date_dt.strftime('%d/%m/%Y')
            agt, hr = trouver_meilleur_creneau(row['Batiment'], d_str, temp_db)
            temp_db = pd.concat([temp_db, pd.DataFrame([{'Batiment': row['Batiment'], 'Date': d_str, 'Heure': hr, 'Agent': agt, 'Rue': INFOS_BATIMENTS.get(row['Batiment'], "Autre"), 'Type': "Import", 'Date_Sort': date_dt}])], ignore_index=True)
        st.session_state.db = temp_db
        st.rerun()

    if not st.session_state.db.empty:
        if st.button("🗑️ Reset Planning"):
            st.session_state.db = pd.DataFrame(columns=['Batiment', 'Date', 'Heure', 'Agent', 'Rue', 'Type', 'Date_Sort'])
            st.rerun()

# --- FORMULAIRE MANUEL ---
with st.expander("➕ AJOUTER / MODIFIER UN DOSSIER"):
    c1, c2 = st.columns(2)
    with c1:
        n_bat = st.selectbox("Bâtiment", list(INFOS_BATIMENTS.keys()))
        n_date = st.date_input("Date du dossier")
    with c2:
        s_agt, s_hr = trouver_meilleur_creneau(n_bat, n_date.strftime('%d/%m/%Y'), st.session_state.db)
        f_agt = st.selectbox("Agent", AGENTS, index=AGENTS.index(s_agt) if s_agt in AGENTS else 0)
        f_hr = st.text_input("Heure", value=s_hr)
    if st.button("Enregistrer"):
        st.session_state.db = pd.concat([st.session_state.db, pd.DataFrame([{'Batiment': n_bat, 'Date': n_date.strftime('%d/%m/%Y'), 'Heure': f_hr, 'Agent': f_agt, 'Rue': INFOS_BATIMENTS.get(n_bat, "Autre"), 'Type': "Manuel", 'Date_Sort': pd.to_datetime(n_date)}])], ignore_index=True)
        st.rerun()

# --- FILTRES ET TABLEAU ---
st.divider()
if not st.session_state.db.empty:
    st.subheader("🔍 Filtres d'affichage")
    f1, f2, f3 = st.columns(3)
    with f1: sel_date = st.selectbox("Par Date :", ["Tout"] + sorted(st.session_state.db['Date'].unique().tolist()))
    with f2: sel_agent = st.selectbox("Par Collaboratrice :", ["Tout"] + AGENTS)
    with f3: sel_bat = st.selectbox("Par Bâtiment :", ["Tout"] + sorted(st.session_state.db['Batiment'].unique().tolist()))

    df_v = st.session_state.db.copy()
    if sel_date != "Tout": df_v = df_v[df_v['Date'] == sel_date]
    if sel_agent != "Tout": df_v = df_v[df_v['Agent'] == sel_agent]
    if sel_bat != "Tout": df_v = df_v[df_v['Batiment'] == sel_bat]

    def style_agent(row): return [f'background-color: {COULEURS.get(row["Agent"])}'] * len(row)
    st.table(df_v.sort_values(by=['Date_Sort', 'Heure'])[['Date', 'Heure', 'Agent', 'Batiment', 'Rue']].style.apply(style_agent, axis=1))
