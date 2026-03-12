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
    'Bethusy A': {'rue': 'Avenue de Béthusy 54, Lausanne', 'lat': 46.5225, 'lon': 6.6472},
    'Bethusy B': {'rue': 'Avenue de Béthusy 56, Lausanne', 'lat': 46.5227, 'lon': 6.6475},
    'Montolieu A': {'rue': 'Isabelle-de-Montolieu 90, Lausanne', 'lat': 46.5412, 'lon': 6.6421},
    'Montolieu B': {'rue': 'Isabelle-de-Montolieu 92, Lausanne', 'lat': 46.5415, 'lon': 6.6425},
    'Tunnel': {'rue': 'Rue du Tunnel 17, Lausanne', 'lat': 46.5255, 'lon': 6.6328},
    'Oron': {'rue': "Route d'Oron 77, 1010 Lausanne", 'lat': 46.5361, 'lon': 6.6625}
}

SECTEURS = {
    'Bethusy': ['Bethusy A', 'Bethusy B'],
    'Montolieu': ['Montolieu A', 'Montolieu B'],
    'Tunnel': ['Tunnel'],
    'Oron': ['Oron']
}

def trouver_secteur(batiment):
    for secteur, liste in SECTEURS.items():
        if batiment in liste:
            return secteur
    return batiment 

COULEURS = {"Celine": "#d1e9ff", "Maria Claret": "#ffdae0", "Maria Elisabeth": "#d4f8d4", "À définir": "#eeeeee", "⚠️ SANS AGENT": "#333333"}

st.set_page_config(page_title="Unité Logement - Gestion Planning", layout="wide", page_icon="📍")

def calculer_distance(pos1, pos2):
    if not pos1 or not pos2: return 0
    R = 6371.0
    lat1, lon1 = np.radians(pos1[0]), np.radians(pos1[1])
    lat2, lon2 = np.radians(pos2[0]), np.radians(pos2[1])
    dlon = lon2 - lon1
    dlat = lat2 - lat1
    a = np.sin(dlat / 2)**2 + np.cos(lat1) * np.cos(lat2) * np.sin(dlon / 2)**2
    c = 2 * np.arctan2(np.sqrt(a), np.sqrt(1 - a))
    return R * c

if 'db' not in st.session_state:
    st.session_state.db = pd.DataFrame(columns=['ID', 'Batiment', 'Date', 'Heure', 'Agent', 'Rue', 'Type', 'Statut', 'Date_Sort'])

def calculer_creneau_securise(agent, date_str, temp_db, batiment_cible, bloc_impose):
    m_jour = temp_db[(temp_db['Date'] == date_str) & (temp_db['Agent'] == agent)]
    h_start_bloc = "08:15" if bloc_impose == "Matin" else "13:00"
    h_end_limit = "11:45" if bloc_impose == "Matin" else "16:30"
    
    if m_jour.empty:
        prochaine_h = datetime.strptime(h_start_bloc, "%H:%M")
    else:
        derniere_mission = m_jour.iloc[-1]
        derniere_h = datetime.strptime(str(derniere_mission['Heure']), "%H:%M")
        if bloc_impose == "Après-midi" and derniere_h < datetime.strptime("13:00", "%H:%M"):
            prochaine_h = datetime.strptime("13:00", "%H:%M")
        else:
            rue_actuelle = INFOS_BATIMENTS.get(batiment_cible, {}).get('rue', "Autre")
            delai = 65 if derniere_mission['Rue'] == rue_actuelle else 85
            prochaine_h = derniere_h + timedelta(minutes=delai)

    if prochaine_h > datetime.strptime(h_end_limit, "%H:%M"):
        return "COMPLET", False
    return prochaine_h.strftime("%H:%M"), True

# --- INTERFACE ---
st.title("📍 Unité Logement : Planning & Rapports")
st.caption(f"📍 Siège social : {BUREAU_ADRESSE}")

t1, t2, t3 = st.tabs(["📝 Planning Global", "📅 Vue par Agent", "📊 Rapports & Analyses"])

with st.sidebar:
    st.header("📂 Importation")
    up = st.file_uploader("Fichier Excel des missions", type=['xlsx'])
    
    if up and st.button("🚀 Lancer l'Attribution"):
        with st.spinner("Optimisation de la répartition..."):
            try:
                df_ex = pd.read_excel(up).dropna(how='all').fillna('')
                df_ex.columns = df_ex.columns.str.strip()
                
                c_id = next((c for c in df_ex.columns if 'id' in c.lower() or 'n°' in c.lower()), df_ex.columns[0])
                c_date = next((c for c in df_ex.columns if 'date' in c.lower()), 'Date')
                c_type = next((c for c in df_ex.columns if 'type' in c.lower()), 'Type')
                c_absent = next((c for c in df_ex.columns if 'absent' in c.lower()), None)
                c_statut = next((c for c in df_ex.columns if 'statut' in c.lower()), 'Statut')

                temp = pd.DataFrame(columns=['ID', 'Batiment', 'Date', 'Heure', 'Agent', 'Rue', 'Type', 'Statut', 'Date_Sort'])
                df_ex[c_date] = pd.to_datetime(df_ex[c_date])
                
                # --- LOGIQUE DE RÉPARTITION ÉQUITABLE PAR BÂTIMENT ---
                for jour in df_ex[c_date].unique():
                    ds = pd.to_datetime(jour).strftime('%d/%m/%Y')
                    df_jour = df_ex[df_ex[c_date] == jour]
                    
                    # On traite chaque bâtiment du jour séparément pour équilibrer
                    for bat in df_jour['Batiment'].unique():
                        df_bat = df_jour[df_jour['Batiment'] == bat]
                        
                        # Liste des agents dispos ce jour-là (non absents pour ce bâtiment spécifique)
                        # Pour simplifier, on prend les agents et on tournera dessus
                        index_agent = 0
                        
                        for _, row in df_bat.iterrows():
                            statut_val = str(row[c_statut]).strip().lower()
                            bloc = "Après-midi" if "midi" in statut_val else "Matin"
                            absents = [a.strip().lower() for a in str(row[c_absent]).split(';')] if c_absent else []
                            presents = [a for a in AGENTS if a.lower() not in absents]
                            
                            agt_elu, h_finale = "⚠️ SANS AGENT", "08:15"
                            
                            if presents:
                                # On essaie les agents les uns après les autres pour équilibrer la charge
                                # au lieu de remplir Celine au maximum d'abord.
                                for _ in range(len(presents)):
                                    p = presents[index_agent % len(presents)]
                                    res_h, possible = calculer_creneau_securise(p, ds, temp, bat, bloc)
                                    if possible:
                                        agt_elu, h_finale = p, res_h
                                        index_agent += 1 # On passe au suivant pour la prochaine mission
                                        break
                                    index_agent += 1

                            temp = pd.concat([temp, pd.DataFrame([{
                                'ID': row[c_id], 'Batiment': row['Batiment'], 'Date': ds, 'Heure': h_finale, 'Agent': agt_elu, 
                                'Type': row[c_type], 'Rue': INFOS_BATIMENTS.get(bat, {}).get('rue', ''), 'Statut': bloc.upper(), 'Date_Sort': jour
                            }])], ignore_index=True)

                st.session_state.db = temp
                st.rerun()
            except Exception as e:
                st.error(f"Erreur : {e}")

    if not st.session_state.db.empty:
        st.divider()
        if st.button("🗑️ Reset"):
            st.session_state.db = pd.DataFrame(columns=['ID', 'Batiment', 'Date', 'Heure', 'Agent', 'Rue', 'Type', 'Statut', 'Date_Sort'])
            st.rerun()

# --- AFFICHAGE ---
with t1:
    if not st.session_state.db.empty:
        st.dataframe(st.session_state.db[['ID', 'Date', 'Statut', 'Heure', 'Agent', 'Batiment', 'Type']].sort_values(['Date_Sort', 'Heure']), use_container_width=True)

with t2:
    if not st.session_state.db.empty:
        sel_j = st.selectbox("📅 Date :", sorted(st.session_state.db['Date'].unique()))
        cols = st.columns(len(AGENTS))
        for i, a in enumerate(AGENTS):
            with cols[i]:
                st.markdown(f"<div style='text-align:center; background-color:{COULEURS[a]}; padding:10px; border-radius:5px; color:black; font-weight:bold;'>{a}</div>", unsafe_allow_html=True)
                m = st.session_state.db[(st.session_state.db['Date'] == sel_j) & (st.session_state.db['Agent'] == a)].sort_values('Heure')
                for _, r in m.iterrows():
                    st.markdown(f"<div style='background-color:{COULEURS[a]}; padding:8px; border-radius:5px; border:1px solid #ccc; color:black; margin-top:5px;'>🆔 <b>{r['ID']}</b><br>🕒 <b>{r['Heure']}</b><br>🏠 {r['Batiment']}</div>", unsafe_allow_html=True)

with t3:
    st.info("Importez un fichier pour les analyses.")

st.divider()
st.caption(f"v4.2 | Répartition Équilibrée | {datetime.now().year}")
