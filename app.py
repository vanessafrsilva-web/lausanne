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

def calculer_creneau_securise(agent, date_str, temp_db, batiment_cible, bloc_impose=None):
    m_jour = temp_db[(temp_db['Date'] == date_str) & (temp_db['Agent'] == agent)]
    
    # Par défaut, on commence à 08:15 le matin
    h_depart_str = "08:15"
    if bloc_impose and "midi" in bloc_impose.lower():
        h_depart_str = "13:00"
    
    if not m_jour.empty:
        h_depart_str = str(m_jour.iloc[-1]['Heure']).strip()

    try:
        h_obj = datetime.strptime(h_depart_str, "%H:%M")
        derniere_rue = m_jour.iloc[-1]['Rue'] if not m_jour.empty else "Bureau"
        rue_cible = INFOS_BATIMENTS.get(batiment_cible, {}).get('rue', "Autre")
        
        delai = 65 if derniere_rue == rue_cible else 80 
        prochaine_h = h_obj + timedelta(minutes=delai) if not m_jour.empty else h_obj
        
        # Passage automatique après-midi si fin de matinée
        if datetime.strptime("11:45", "%H:%M") < prochaine_h < datetime.strptime("13:00", "%H:%M"):
            prochaine_h = datetime.strptime("13:00", "%H:%M")
            
        # Limite de fin de journée
        if prochaine_h > datetime.strptime("16:30", "%H:%M"):
            return "COMPLET", False
            
        return prochaine_h.strftime("%H:%M"), True
    except:
        return "08:15", True

# --- INTERFACE ---
st.title("📍 Unité Logement : Planning Automatique")
st.caption(f"📍 Siège social : {BUREAU_ADRESSE}")

t1, t2, t3 = st.tabs(["📝 Planning Global", "📅 Vue par Agent", "📊 Rapports & Analyses"])

with st.sidebar:
    st.header("📂 Importation")
    up = st.file_uploader("Fichier Excel des missions", type=['xlsx'])
    st.info("Priorité : Remplissage Matin -> Après-midi (Auto)")

    if up and st.button("🚀 Lancer l'Attribution"):
        with st.spinner("Calcul en cours..."):
            try:
                df_ex = pd.read_excel(up).dropna(how='all').fillna('')
                df_ex.columns = df_ex.columns.str.strip()
                
                c_date = next((c for c in df_ex.columns if 'date' in c.lower()), 'Date')
                c_id = next((c for c in df_ex.columns if 'id' in c.lower() or 'n°' in c.lower()), df_ex.columns[0])
                c_type = next((c for c in df_ex.columns if 'type' in c.lower()), 'Type')
                c_absent = next((c for c in df_ex.columns if 'absent' in c.lower() or 'absente' in c.lower()), None)
                c_statut = next((c for c in df_ex.columns if 'statut' in c.lower()), 'Statut')

                # TRI STRATÉGIQUE : Par Date puis par Bâtiment pour forcer le regroupement
                df_ex_sorted = df_ex.copy()
                df_ex_sorted[c_date] = pd.to_datetime(df_ex_sorted[c_date])
                df_ex_sorted = df_ex_sorted.sort_values(by=[c_date, 'Batiment'])

                temp = pd.DataFrame(columns=['ID', 'Batiment', 'Date', 'Heure', 'Agent', 'Rue', 'Type', 'Statut', 'Date_Sort'])

                for _, row in df_ex_sorted.iterrows():
                    dt_raw = row[c_date]
                    ds = dt_raw.strftime('%d/%m/%Y')
                    bat_cible = row['Batiment']
                    sec_cible = trouver_secteur(bat_cible)
                    info_b = INFOS_BATIMENTS.get(bat_cible, {'rue': 'Autre'})
                    statut_val = str(row[c_statut]).strip()
                    
                    absents = [a.strip().lower().replace('-', ' ') for a in str(row[c_absent]).split(';')] if c_absent and str(row[c_absent]).strip() != "" else []
                    presents = [a for a in AGENTS if a.lower().replace('-', ' ') not in absents]
                    
                    agt_elu, h_finale = "⚠️ SANS AGENT", "08:15"
                    
                    if presents:
                        # Calcul priorité : 0 si déjà dans bâtiment, 10 si même secteur, 50 si libre
                        def calculer_priorite(nom_agt):
                            m_agt = temp[(temp['Date'] == ds) & (temp['Agent'] == nom_agt)]
                            if m_agt.empty: return 50
                            derniere = m_agt.iloc[-1]
                            if derniere['Batiment'] == bat_cible: return 0 
                            if trouver_secteur(derniere['Batiment']) == sec_cible: return 10
                            return 100

                        presents_tries = sorted(presents, key=lambda p: (calculer_priorite(p), len(temp[(temp['Date'] == ds) & (temp['Agent'] == p)])))
                        
                        for p in presents_tries:
                            res_h, possible = calculer_creneau_securise(p, ds, temp, bat_cible, statut_val)
                            if possible:
                                agt_elu, h_finale = p, res_h
                                break

                    temp = pd.concat([temp, pd.DataFrame([{
                        'ID': row[c_id], 'Batiment': bat_cible, 'Date': ds, 'Heure': h_finale, 'Agent': agt_elu, 
                        'Type': row[c_type], 'Rue': info_b['rue'], 'Statut': statut_val, 'Date_Sort': dt_raw
                    }])], ignore_index=True)
                
                st.session_state.db = temp
                st.rerun()
            except Exception as e:
                st.error(f"Erreur : {e}")

# (Les onglets t1, t2, t3 restent identiques à la version v4.2 pour assurer la continuité des visuels)
# ... [Code des onglets inchangé] ...

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
        def style_row(s):
            color = COULEURS.get(s['Agent'], "#eeeeee")
            return [f'background-color: {color}; color: black']*8
        st.dataframe(df_v[['ID', 'Date', 'Statut', 'Heure', 'Agent', 'Batiment', 'Type', 'Rue']].style.apply(style_row, axis=1), use_container_width=True, height=600)

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
    if not st.session_state.db.empty:
        df_rep = st.session_state.db.copy()
        df_rep['Mois'] = df_rep['Date_Sort'].dt.strftime('%B %Y')
        col_f1, col_f2 = st.columns(2)
        mois_sel = col_f1.selectbox("📅 Choisir le Mois :", df_rep['Mois'].unique())
        options_agents = [a for a in df_rep['Agent'].unique() if a != "⚠️ SANS AGENT"]
        agents_sel = col_f2.multiselect("👤 Agents :", options_agents, default=options_agents)
        df_final = df_rep[(df_rep['Mois'] == mois_sel) & (df_rep['Agent'].isin(agents_sel))]
        if not df_final.empty:
            total_km, g_bat, g_sec = 0.0, 0, 0
            total_missions = len(df_final)
            for agent in agents_sel:
                df_agt = df_final[df_final['Agent'] == agent].sort_values(['Date_Sort', 'Heure'])
                for jour in df_agt['Date'].unique():
                    missions_j = df_agt[df_agt['Date'] == jour]
                    prev_coords, prev_bat, prev_sec = BUREAU_GPS, None, None
                    for i, (_, row) in enumerate(missions_j.iterrows()):
                        curr_b = row['Batiment']
                        curr_sec = trouver_secteur(curr_b)
                        coords = (INFOS_BATIMENTS[curr_b]['lat'], INFOS_BATIMENTS[curr_b]['lon']) if curr_b in INFOS_BATIMENTS else BUREAU_GPS
                        total_km += calculer_distance(prev_coords, coords)
                        if i > 0:
                            if curr_b == prev_bat: g_bat += 1; g_sec += 1
                            elif curr_sec == prev_sec: g_sec += 1
                        prev_coords, prev_bat, prev_sec = coords, curr_b, curr_sec
                    total_km += calculer_distance(prev_coords, BUREAU_GPS)
            st.markdown("### 📊 Indicateurs Clés")
            r1, r2 = st.columns(4), st.columns(4)
            r1[0].metric("Total Missions", total_missions)
            r1[1].metric("🏢 Opti. Bâtiment", f"{(g_bat/total_missions*100):.1f}%")
            r1[2].metric("📍 Opti. Secteur", f"{(g_sec/total_missions*100):.1f}%")
            r1[3].metric("🚗 Distance Est.", f"{total_km:.1f} km")
            r2[0].metric("📈 Nb Entrées", df_final[df_final['Type'].str.contains('Entrée|In', case=False)].shape[0])
            r2[1].metric("📉 Nb Sorties", df_final[df_final['Type'].str.contains('Sortie|Out', case=False)].shape[0])
            r2[2].metric("👥 Agents actifs", len(agents_sel))
            r2[3].metric("📅 Jours", df_final['Date'].nunique())
            st.divider()
            cl, cr = st.columns(2)
            with cl:
                st.subheader("🏠 Par bâtiment")
                st.table(df_final.groupby('Batiment').size().reset_index(name='Missions').sort_values('Missions', ascending=False))
            with cr:
                st.subheader("📍 Carte")
                map_data = [{'lat': INFOS_BATIMENTS[b]['lat'], 'lon': INFOS_BATIMENTS[b]['lon'], 'Missions': count} 
                            for b, count in df_final.groupby('Batiment').size().items() if b in INFOS_BATIMENTS]
                if map_data: st.map(pd.DataFrame(map_data), size="Missions")

st.divider()
st.caption(f"v4.3 | {datetime.now().year}")
