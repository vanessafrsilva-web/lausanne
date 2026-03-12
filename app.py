import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import io
import plotly.express as px
import numpy as np

# --- CONFIGURATION ---
BUREAU_ADRESSE = "Chemin Mont-Paisible 18, 1011 Lausanne"
BUREAU_GPS = (46.5332, 6.6135) 
AGENTS = ["Celine", "Maria Claret", "Maria Elisabeth"]

INFOS_BATIMENTS = {
    'Bethusy 84 B': {'rue': 'Avenue de Béthusy 54, Lausanne', 'lat': 46.5225, 'lon': 6.6472},
    'Tunnel 17': {'rue': 'Rue du Tunnel 17, Lausanne', 'lat': 46.5255, 'lon': 6.6328},
    'Montolieu 90': {'rue': 'Isabelle-de-Montolieu 90, Lausanne', 'lat': 46.5412, 'lon': 6.6421},
    'Montolieu 92': {'rue': 'Isabelle-de-Montolieu 92, Lausanne', 'lat': 46.5415, 'lon': 6.6425},
    'Oron 77': {'rue': "Route d'Oron 77, 1010 Lausanne", 'lat': 46.5361, 'lon': 6.6625}
}

SECTEURS = {
    'Bethusy': ['Bethusy 84 B'],
    'Montolieu': ['Montolieu 90', 'Montolieu 92'],
    'Tunnel': ['Tunnel 17'],
    'Oron': ['Oron 77']
}

def trouver_secteur(batiment):
    for secteur, liste in SECTEURS.items():
        if batiment in liste: return secteur
    return batiment 

COULEURS = {"Celine": "#d1e9ff", "Maria Claret": "#ffdae0", "Maria Elisabeth": "#d4f8d4", "À définir": "#eeeeee", "⚠️ SANS AGENT": "#333333"}

st.set_page_config(page_title="Unité Logement - Gestion Planning", layout="wide", page_icon="📍")

def calculer_distance(pos1, pos2):
    if not pos1 or not pos2: return 0
    R = 6371.0
    lat1, lon1 = np.radians(pos1[0]), np.radians(pos1[1])
    lat2, lon2 = np.radians(pos2[0]), np.radians(pos2[1])
    dlon, dlat = lon2 - lon1, lat2 - lat1
    a = np.sin(dlat / 2)**2 + np.cos(lat1) * np.cos(lat2) * np.sin(dlon / 2)**2
    c = 2 * np.arctan2(np.sqrt(a), np.sqrt(1 - a))
    return R * c

if 'db' not in st.session_state:
    st.session_state.db = pd.DataFrame(columns=['ID', 'Batiment', 'Date', 'Heure', 'Agent', 'Rue', 'Type', 'Statut', 'Date_Sort'])

def calculer_creneau_securise(agent, date_str, temp_db, batiment_cible, statut_val):
    m_jour = temp_db[(temp_db['Date'] == date_str) & (temp_db['Agent'] == agent)]
    
    # Définition du point de départ selon le statut
    h_depart_str = "08:15"
    if "midi" in str(statut_val).lower():
        h_depart_str = "13:00"
    
    if m_jour.empty:
        return h_depart_str, True

    # Si l'agent a déjà des missions, on calcule la suite
    h_derniere = str(m_jour.iloc[-1]['Heure']).strip()
    try:
        h_obj = datetime.strptime(h_derniere, "%H:%M")
        rue_derniere = m_jour.iloc[-1]['Rue']
        rue_cible = INFOS_BATIMENTS.get(batiment_cible, {}).get('rue', "Autre")
        
        delai = 65 if rue_derniere == rue_cible else 80 
        prochaine_h = h_obj + timedelta(minutes=delai)
        
        # Gestion pause déjeuner
        if datetime.strptime("11:45", "%H:%M") < prochaine_h < datetime.strptime("13:00", "%H:%M"):
            prochaine_h = datetime.strptime("13:00", "%H:%M")
            
        if prochaine_h > datetime.strptime("16:30", "%H:%M"):
            return "COMPLET", False
            
        return prochaine_h.strftime("%H:%M"), True
    except:
        return h_depart_str, True

# --- INTERFACE ---
st.title("📍 Unité Logement : Attribution Parallèle")

t1, t2, t3 = st.tabs(["📝 Planning Global", "📅 Vue par Agent", "📊 Rapports & Analyses"])

with st.sidebar:
    st.header("📂 Importation")
    up = st.file_uploader("Fichier Excel des missions", type=['xlsx'])

    if up and st.button("🚀 Lancer l'Attribution Parallèle"):
        with st.spinner("Répartition en cours..."):
            try:
                df_ex = pd.read_excel(up).dropna(how='all').fillna('')
                df_ex.columns = df_ex.columns.str.strip()
                
                c_date = next((c for c in df_ex.columns if 'date' in c.lower()), 'Date')
                c_id = next((c for c in df_ex.columns if 'id' in c.lower() or 'n°' in c.lower()), df_ex.columns[0])
                c_type = next((c for c in df_ex.columns if 'type' in c.lower()), 'Type')
                c_absent = next((c for c in df_ex.columns if 'absent' in c.lower() or 'absente' in c.lower()), None)
                c_statut = next((c for c in df_ex.columns if 'statut' in c.lower()), 'Statut')

                df_ex_sorted = df_ex.copy()
                df_ex_sorted[c_date] = pd.to_datetime(df_ex_sorted[c_date])
                # On trie par date, puis par bâtiment pour grouper les lieux
                df_ex_sorted = df_ex_sorted.sort_values(by=[c_date, 'Batiment'])

                temp = pd.DataFrame(columns=['ID', 'Batiment', 'Date', 'Heure', 'Agent', 'Rue', 'Type', 'Statut', 'Date_Sort'])

                for _, row in df_ex_sorted.iterrows():
                    ds = row[c_date].strftime('%d/%m/%Y')
                    bat_cible = row['Batiment']
                    sec_cible = trouver_secteur(bat_cible)
                    
                    absents = [a.strip().lower() for a in str(row[c_absent]).split(';')] if c_absent else []
                    presents = [a for a in AGENTS if a.lower() not in absents]
                    
                    agt_elu, h_finale = "⚠️ SANS AGENT", "08:15"
                    
                    if presents:
                        # --- LOGIQUE DE RÉPARTITION PARALLÈLE ---
                        # On trie les agents par :
                        # 1. Priorité de bâtiment (si un agent est déjà là ET a peu de missions)
                        # 2. NOMBRE DE MISSIONS TOTAL (pour remplir tout le monde en même temps le matin)
                        def score_agent(nom_agt):
                            m_agt = temp[(temp['Date'] == ds) & (temp['Agent'] == nom_agt)]
                            nb_missions = len(m_agt)
                            
                            priorite = 2 # Par défaut
                            if not m_agt.empty:
                                if m_agt.iloc[-1]['Batiment'] == bat_cible:
                                    priorite = 0 # Très prioritaire si déjà là
                                elif trouver_secteur(m_agt.iloc[-1]['Batiment']) == sec_cible:
                                    priorite = 1 # Prioritaire si secteur
                            
                            return (priorite, nb_missions)

                        presents_tries = sorted(presents, key=score_agent)
                        
                        for p in presents_tries:
                            res_h, possible = calculer_creneau_securise(p, ds, temp, bat_cible, row[c_statut])
                            if possible:
                                agt_elu, h_finale = p, res_h
                                break

                    temp = pd.concat([temp, pd.DataFrame([{
                        'ID': row[c_id], 'Batiment': bat_cible, 'Date': ds, 'Heure': h_finale, 'Agent': agt_elu, 
                        'Type': row[c_type], 'Rue': INFOS_BATIMENTS.get(bat_cible, {}).get('rue', 'Autre'), 
                        'Statut': row[c_statut], 'Date_Sort': row[c_date]
                    }])], ignore_index=True)
                
                st.session_state.db = temp
                st.rerun()
            except Exception as e:
                st.error(f"Erreur : {e}")

# --- AFFICHAGE (Identique mais avec le tri corrigé) ---
with t1:
    if not st.session_state.db.empty:
        df_v = st.session_state.db.sort_values(['Date_Sort', 'Heure', 'Agent'])
        st.dataframe(df_v[['ID', 'Date', 'Heure', 'Agent', 'Batiment', 'Type', 'Rue']], use_container_width=True, height=600)

with t2:
    if not st.session_state.db.empty:
        sel_j = st.selectbox("📅 Date :", sorted(st.session_state.db['Date'].unique(), key=lambda x: datetime.strptime(x, '%d/%m/%Y')))
        cols = st.columns(len(AGENTS))
        for i, a in enumerate(AGENTS):
            with cols[i]:
                st.markdown(f"<div style='text-align:center; background-color:{COULEURS[a]}; padding:10px; border-radius:5px; color:black; font-weight:bold;'>{a}</div>", unsafe_allow_html=True)
                m = st.session_state.db[(st.session_state.db['Date'] == sel_j) & (st.session_state.db['Agent'] == a)].sort_values('Heure')
                for _, r in m.iterrows():
                    st.markdown(f"<div style='background-color:{COULEURS[a]}; padding:8px; border-radius:5px; border:1px solid #ccc; color:black; margin-top:5px;'>🆔 <b>{r['ID']}</b><br>🕒 <b>{r['Heure']}</b><br>🏠 {r['Batiment']}</div>", unsafe_allow_html=True)

st.divider()
st.caption(f"v4.4 | {datetime.now().year}")
