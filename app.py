import streamlit as st
import pandas as pd
from datetime import datetime, timedelta

# --- CONFIGURATION FIXE ---
BUREAU = "18 Mon Repos" # Mis à jour selon vos informations
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

# Initialisation des bases de données dans la session
if 'db' not in st.session_state:
    st.session_state.db = pd.DataFrame(columns=['Batiment', 'Date', 'Heure', 'Agent', 'Rue', 'Type', 'Date_Sort'])
if 'conges' not in st.session_state:
    st.session_state.conges = pd.DataFrame(columns=['Agent', 'Date'])

# --- FONCTION DE VÉRIFICATION DE DISPONIBILITÉ ---
def est_disponible(agent, date_str):
    if st.session_state.conges.empty:
        return True
    # Vérifie si l'agent a un congé enregistré à cette date
    match = st.session_state.conges[(st.session_state.conges['Agent'] == agent) & 
                                    (st.session_state.conges['Date'] == date_str)]
    return match.empty

# --- MOTEUR D'ATTRIBUTION AVEC FILTRE ABSENCES ---
def trouver_meilleur_creneau(batiment, date_str, temp_db):
    rue_cible = INFOS_BATIMENTS.get(batiment, "Autre")
    missions_jour = temp_db[temp_db['Date'] == date_str]
    pause_debut = datetime.strptime("12:00", "%H:%M")
    pause_fin = datetime.strptime("13:00", "%H:%M")
    
    def ajuster_pause(heure_fin_mission):
        if heure_fin_mission > pause_debut and heure_fin_mission < pause_fin:
            return pause_fin
        return heure_fin_mission

    # Liste des agents réellement présents ce jour-là
    agents_presents = [a for a in AGENTS if est_disponible(a, date_str)]
    
    if not agents_presents:
        return "À définir (Tous absents)", "08:15"

    # PRIORITÉ 1 : CELINE (si présente)
    if "Celine" in agents_presents:
        # Même rue ?
        celine_meme_rue = missions_jour[(missions_jour['Agent'] == "Celine") & (missions_jour['Rue'] == rue_cible)]
        if not celine_meme_rue.empty:
            dernier = celine_meme_rue.sort_values(by='Heure').iloc[-1]
            h_fin = datetime.strptime(dernier['Heure'], "%H:%M") + timedelta(hours=1, minutes=20)
            h_fin = ajuster_pause(h_fin)
            return "Celine", h_fin.strftime("%H:%M")

        # Sinon, selon son heure de fin
        missions_celine = missions_jour[missions_jour['Agent'] == "Celine"]
        if missions_celine.empty:
            return "Celine", "08:15"
        else:
            h_fin_celine = datetime.strptime(missions_celine.sort_values(by='Heure').iloc[-1]['Heure'], "%H:%M") + timedelta(hours=1, minutes=45)
            h_fin_celine = ajuster_pause(h_fin_celine)
            if h_fin_celine < datetime.strptime("15:30", "%H:%M"):
                return "Celine", h_fin_celine.strftime("%H:%M")

    # PRIORITÉ 2 : SURPLUS (Maria Claret ou Elisabeth si présentes)
    surplus_presents = [a for a in ["Maria Claret", "Maria Elisabeth"] if a in agents_presents]
    for agent_surplus in surplus_presents:
        missions_agt = missions_jour[missions_jour['Agent'] == agent_surplus]
        if missions_agt.empty:
            return agent_surplus, "08:15"
        else:
            h_fin_agt = datetime.strptime(missions_agt.sort_values(by='Heure').iloc[-1]['Heure'], "%H:%M") + timedelta(hours=1, minutes=45)
            h_fin_agt = ajuster_pause(h_fin_agt)
            if h_fin_agt < datetime.strptime("16:00", "%H:%M"):
                return agent_surplus, h_fin_agt.strftime("%H:%M")

    return agents_presents[0], "Surcharge"

# TITRE FIXE
st.title("📍 Unité Logement : Optimisation Attibutions")

# --- BARRE LATÉRALE ---
with st.sidebar:
    st.header("🌴 Gestion des Absences")
    abs_agent = st.selectbox("Collaboratrice absente", AGENTS)
    abs_date = st.date_input("Date de l'absence")
    if st.button("Enregistrer l'absence"):
        nouvel_abs = pd.DataFrame([{'Agent': abs_agent, 'Date': abs_date.strftime('%d/%m/%Y')}])
        st.session_state.conges = pd.concat([st.session_state.conges, nouvel_abs], ignore_index=True)
        st.success(f"Absence de {abs_agent} enregistrée")
    
    if not st.session_state.conges.empty:
        st.write("Absences prévues :")
        st.dataframe(st.session_state.conges, hide_index=True)
        if st.button("Effacer les absences"):
            st.session_state.conges = pd.DataFrame(columns=['Agent', 'Date'])
            st.rerun()

    st.divider()
    st.header("📥 Importation Massive")
    uploaded = st.file_uploader("Fichier Excel", type=['xlsx'])
    if uploaded and st.button("🚀 Planifier Avril"):
        df_ex = pd.read_excel(uploaded).dropna(how='all').fillna('')
        df_ex.columns = df_ex.columns.str.strip()
        col_d = next((c for c in df_ex.columns if 'date' in c.lower()), 'Date')
        
        temp_db = st.session_state.db.copy()
        for _, row in df_ex.sort_values(by=[col_d, 'Batiment']).iterrows():
            date_dt = pd.to_datetime(row[col_d])
            d_str = date_dt.strftime('%d/%m/%Y')
            agt, hr = trouver_meilleur_creneau(row['Batiment'], d_str, temp_db)
            
            temp_db = pd.concat([temp_db, pd.DataFrame([{
                'Batiment': row['Batiment'], 'Date': d_str, 'Heure': hr, 
                'Agent': agt, 'Rue': INFOS_BATIMENTS.get(row['Batiment'], "Autre"), 
                'Type': "Import", 'Date_Sort': date_dt
            }])], ignore_index=True)
        st.session_state.db = temp_db
        st.success("Planning optimisé !")

# --- FORMULAIRE MANUEL ---
with st.expander("➕ AJOUTER / MODIFIER UN DOSSIER"):
    c1, c2 = st.columns(2)
    with c1:
        n_bat = st.selectbox("Bâtiment", list(INFOS_BATIMENTS.keys()))
        n_date = st.date_input("Date du dossier")
        date_str = n_date.strftime('%d/%m/%Y')
    with c2:
        s_agt, s_hr = trouver_meilleur_creneau(n_bat, date_str, st.session_state.db)
        # On ajuste l'index pour Streamlit si l'agent recommandé est absent
        idx_reco = AGENTS.index(s_agt) if s_agt in AGENTS else 0
        f_agt = st.selectbox("Agent recommandé", AGENTS, index=idx_reco)
        f_hr = st.text_input("Heure", value=s_hr)
    if st.button("Enregistrer le dossier"):
        l = {'Batiment': n_bat, 'Date': date_str, 'Heure': f_hr, 'Agent': f_agt, 
             'Rue': INFOS_BATIMENTS.get(n_bat, "Autre"), 'Type': "Manuel", 'Date_Sort': pd.to_datetime(n_date)}
        st.session_state.db = pd.concat([st.session_state.db, pd.DataFrame([l])], ignore_index=True)
        st.rerun()

# --- FILTRES ET TABLEAU ---
st.divider()
if not st.session_state.db.empty:
    st.subheader("🔍 Filtres et Vue d'ensemble")
    f1, f2, f3 = st.columns(3)
    with f1:
        sel_date = st.selectbox("Date :", ["Tout"] + sorted(st.session_state.db['Date'].unique().tolist()))
    with f2:
        sel_agent = st.selectbox("Collaboratrice :", ["Tout"] + AGENTS)
    with f3:
        sel_bat = st.selectbox("Bâtiment :", ["Tout"] + sorted(st.session_state.db['Batiment'].unique().tolist()))

    df_v = st.session_state.db.copy()
    if sel_date != "Tout": df_v = df_v[df_v['Date'] == sel_date]
    if sel_agent != "Tout": df_v = df_v[df_v['Agent'] == sel_agent]
    if sel_bat != "Tout": df_v = df_v[df_v['Batiment'] == sel_bat]

    df_v = df_v.sort_values(by=['Date_Sort', 'Heure', 'Agent'])

    def style_agent(row):
        return [f'background-color: {COULEURS.get(row["Agent"])}'] * len(row)

    st.table(df_v[['Date', 'Heure', 'Agent', 'Batiment', 'Rue']].style.apply(style_agent, axis=1))
