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

# --- FONCTION DISTANCE ---
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

# --- FONCTIONS LOGIQUES MODIFIÉES ---
def calculer_creneau_securise(agent, date_str, temp_db, batiment_cible, bloc_impose):
    m_jour = temp_db[(temp_db['Date'] == date_str) & (temp_db['Agent'] == agent)]
    
    # Définition des horaires par bloc
    h_start_bloc = "08:15" if bloc_impose == "Matin" else "13:00"
    h_end_limit = "11:45" if bloc_impose == "Matin" else "16:30"
    
    if m_jour.empty:
        prochaine_h = datetime.strptime(h_start_bloc, "%H:%M")
    else:
        derniere_mission = m_jour.iloc[-1]
        derniere_h = datetime.strptime(str(derniere_mission['Heure']), "%H:%M")
        
        # Si on passe d'une mission matin à un souhait après-midi, on reset à 13h00
        if bloc_impose == "Après-midi" and derniere_h < datetime.strptime("13:00", "%H:%M"):
            prochaine_h = datetime.strptime("13:00", "%H:%M")
        else:
            # Calcul du délai (65min si même rue, 85min si changement)
            rue_actuelle = INFOS_BATIMENTS.get(batiment_cible, {}).get('rue', "Autre")
            delai = 65 if derniere_mission['Rue'] == rue_actuelle else 85
            prochaine_h = derniere_h + timedelta(minutes=delai)

    # Vérification si le créneau dépasse la limite du bloc ou de la journée
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
        with st.spinner("Optimisation géographique en cours..."):
            try:
                df_ex = pd.read_excel(up).dropna(how='all').fillna('')
                df_ex.columns = df_ex.columns.str.strip()
                
                c_id = next((c for c in df_ex.columns if 'id' in c.lower() or 'n°' in c.lower()), df_ex.columns[0])
                c_date = next((c for c in df_ex.columns if 'date' in c.lower()), 'Date')
                c_type = next((c for c in df_ex.columns if 'type' in c.lower()), 'Type')
                c_absent = next((c for c in df_ex.columns if 'absent' in c.lower()), None)
                c_statut = next((c for c in df_ex.columns if 'statut' in c.lower()), 'Statut')

                temp = pd.DataFrame(columns=['ID', 'Batiment', 'Date', 'Heure', 'Agent', 'Rue', 'Type', 'Statut', 'Date_Sort'])
                
                # --- PRÉPARATION DU TRI POUR REGROUPEMENT ---
                df_ex[c_date] = pd.to_datetime(df_ex[c_date])
                df_ex['Secteur'] = df_ex['Batiment'].apply(trouver_secteur)
                # On trie par Date, puis par Secteur, puis par Bâtiment pour les grouper
                df_ex_sorted = df_ex.sort_values(by=[c_date, 'Secteur', 'Batiment'])

                for _, row in df_ex_sorted.iterrows():
                    dt_raw = row[c_date]
                    ds = dt_raw.strftime('%d/%m/%Y')
                    info_b = INFOS_BATIMENTS.get(row['Batiment'], {'rue': 'Autre'})
                    rue_demandee = info_b['rue']
                    
                    # Logique de Bloc
                    statut_val = str(row[c_statut]).strip().lower()
                    bloc = "Après-midi" if "midi" in statut_val or "soir" in statut_val else "Matin"
                    
                    absents = [a.strip().lower() for a in str(row[c_absent]).split(';')] if c_absent else []
                    presents = [a for a in AGENTS if a.lower() not in absents]
                    
                    agt_elu, h_finale = "⚠️ SANS AGENT", "08:15"
                    
                    if presents:
                        # Score de proximité : on favorise l'agent déjà sur place ou dans le secteur
                        def score_agent(name):
                            m_agent = temp[(temp['Date'] == ds) & (temp['Agent'] == name)]
                            if m_agent.empty: return 10
                            derniere = m_agent.iloc[-1]
                            if derniere['Batiment'] == row['Batiment']: return 0
                            if trouver_secteur(derniere['Batiment']) == row['Secteur']: return 1
                            return 5

                        presents_tries = sorted(presents, key=lambda x: (score_agent(x), len(temp[(temp['Date'] == ds) & (temp['Agent'] == x)])))
                        
                        for p in presents_tries:
                            res_h, possible = calculer_creneau_securise(p, ds, temp, row['Batiment'], bloc)
                            if possible:
                                agt_elu, h_finale = p, res_h
                                break

                    temp = pd.concat([temp, pd.DataFrame([{
                        'ID': row[c_id], 'Batiment': row['Batiment'], 'Date': ds, 'Heure': h_finale, 'Agent': agt_elu, 
                        'Type': row[c_type], 'Rue': rue_demandee, 'Statut': bloc.upper(), 'Date_Sort': dt_raw
                    }])], ignore_index=True)

                st.session_state.db = temp
                st.rerun()
            except Exception as e:
                st.error(f"Erreur : {e}")

    if not st.session_state.db.empty:
        st.divider()
        df_export = st.session_state.db.sort_values(['Date_Sort', 'Heure']).drop(columns=['Date_Sort'])
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            df_export.to_excel(writer, index=False)
        st.download_button("📥 Télécharger Excel", output.getvalue(), "Planning_Optimise.xlsx")
        if st.button("🗑️ Reset"):
            st.session_state.db = pd.DataFrame(columns=['ID', 'Batiment', 'Date', 'Heure', 'Agent', 'Rue', 'Type', 'Statut', 'Date_Sort'])
            st.rerun()

# --- ONGLETS (AFFICHAGE) ---
with t1:
    if not st.session_state.db.empty:
        agents_dispo = sorted([a for a in st.session_state.db['Agent'].unique() if a != "⚠️ SANS AGENT"])
        st.write("🔍 **Filtrer par agent :**")
        cols_filtre = st.columns(len(agents_dispo) + 1)
        selection = []
        for i, agent in enumerate(agents_dispo):
            if cols_filtre[i].checkbox(agent, value=True, key=f"filter_{agent}"):
                selection.append(agent)
        if "⚠️ SANS AGENT" in st.session_state.db['Agent'].values:
            selection.append("⚠️ SANS AGENT")

        df_v = st.session_state.db[st.session_state.db['Agent'].isin(selection)].sort_values(['Date_Sort', 'Heure'])
        
        if not df_v.empty:
            def style_row(s):
                color = COULEURS.get(s['Agent'], "#eeeeee")
                return [f'background-color: {color}; color: black']*8
                
            st.dataframe(
                df_v[['ID', 'Date', 'Statut', 'Heure', 'Agent', 'Batiment', 'Type', 'Rue']].style.apply(style_row, axis=1), 
                use_container_width=True, height=600
            )

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

with t3:
    if st.session_state.db.empty:
        st.info("Importez un fichier Excel pour voir les analyses.")
    else:
        df_rep = st.session_state.db.copy()
        df_rep['Mois'] = df_rep['Date_Sort'].dt.strftime('%B %Y')
        col_f1, col_f2 = st.columns(2)
        mois_sel = col_f1.selectbox("📅 Choisir le Mois :", df_rep['Mois'].unique())
        options_agents = [a for a in df_rep['Agent'].unique() if a != "⚠️ SANS AGENT"]
        agents_sel = col_f2.multiselect("👤 Sélectionner Agents :", options_agents, default=options_agents)
        df_final = df_rep[(df_rep['Mois'] == mois_sel) & (df_rep['Agent'].isin(agents_sel))]

        if not df_final.empty:
            total_km = 0.0
            total_missions = len(df_final)
            for agent in agents_sel:
                df_agt = df_final[df_final['Agent'] == agent].sort_values(['Date_Sort', 'Heure'])
                for jour in df_agt['Date'].unique():
                    missions_j = df_agt[df_agt['Date'] == jour]
                    prev_coords = BUREAU_GPS
                    for _, row in missions_j.iterrows():
                        coords = (INFOS_BATIMENTS[row['Batiment']]['lat'], INFOS_BATIMENTS[row['Batiment']]['lon']) if row['Batiment'] in INFOS_BATIMENTS else BUREAU_GPS
                        total_km += calculer_distance(prev_coords, coords)
                        prev_coords = coords
                    total_km += calculer_distance(prev_coords, BUREAU_GPS)

            st.markdown("### 📊 Indicateurs Clés")
            r1 = st.columns(4)
            r1[0].metric("Total Missions", total_missions)
            r1[1].metric("🚗 Distance Est.", f"{total_km:.1f} km")
            r1[2].metric("👥 Agents actifs", len(agents_sel))
            r1[3].metric("📅 Jours", df_final['Date'].nunique())

st.divider()
st.caption(f"v4.1 | Optimisation par Secteur & Blocs | {datetime.now().year}")
