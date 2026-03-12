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

COULEURS = {"Celine": "#d1e9ff", "Maria Claret": "#ffdae0", "Maria Elisabeth": "#d4f8d4", "⚠️ SANS AGENT": "#eeeeee"}

st.set_page_config(page_title="Unité Logement - Gestion Planning", layout="wide", page_icon="📍")

# --- FONCTIONS TECHNIQUES ---
def trouver_secteur(batiment):
    for secteur, liste in SECTEURS.items():
        if batiment in liste: return secteur
    return batiment 

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

def calculer_creneau(agent, date_str, temp_db, batiment_cible, bloc_impose):
    m_jour = temp_db[(temp_db['Date'] == date_str) & (temp_db['Agent'] == agent)]
    h_start = "08:15" if bloc_impose == "Matin" else "13:00"
    h_limit = "11:45" if bloc_impose == "Matin" else "16:30"
    
    if m_jour.empty:
        prochaine_h = datetime.strptime(h_start, "%H:%M")
    else:
        derniere_h = datetime.strptime(str(m_jour.iloc[-1]['Heure']), "%H:%M")
        if bloc_impose == "Après-midi" and derniere_h < datetime.strptime("13:00", "%H:%M"):
            prochaine_h = datetime.strptime("13:00", "%H:%M")
        else:
            rue_act = INFOS_BATIMENTS.get(batiment_cible, {}).get('rue', "")
            delai = 65 if m_jour.iloc[-1]['Rue'] == rue_act else 85
            prochaine_h = derniere_h + timedelta(minutes=delai)

    if prochaine_h > datetime.strptime(h_limit, "%H:%M"): return "COMPLET", False
    return prochaine_h.strftime("%H:%M"), True

# --- INTERFACE ---
st.title("📍 Unité Logement : Planning & Rapports")
t1, t2, t3 = st.tabs(["📝 Planning Global", "📅 Vue par Agent", "📊 Rapports & Analyses"])

with st.sidebar:
    st.header("📂 Importation")
    up = st.file_uploader("Fichier Excel des missions", type=['xlsx'])
    
    if up and st.button("🚀 Lancer l'Attribution"):
        try:
            df_ex = pd.read_excel(up).dropna(how='all').fillna('')
            df_ex.columns = df_ex.columns.str.strip()
            
            c_id = next((c for c in df_ex.columns if 'id' in c.lower() or 'n°' in c.lower()), df_ex.columns[0])
            c_date = next((c for c in df_ex.columns if 'date' in c.lower()), 'Date')
            c_statut = next((c for c in df_ex.columns if 'statut' in c.lower()), 'Statut')
            c_absent = next((c for c in df_ex.columns if 'absent' in c.lower()), None)
            c_type = next((c for c in df_ex.columns if 'type' in c.lower()), 'Type')
            c_bat = next((c for c in df_ex.columns if 'bat' in c.lower() or 'bât' in c.lower()), 'Batiment')

            temp_rows = []
            df_ex[c_date] = pd.to_datetime(df_ex[c_date])
            
            for jour in sorted(df_ex[c_date].unique()):
                ds = pd.to_datetime(jour).strftime('%d/%m/%Y')
                df_j = df_ex[df_ex[c_date] == jour].copy()
                
                for bat_nom in df_j[c_bat].unique():
                    df_b = df_j[df_j[c_bat] == bat_nom]
                    idx_agt = 0
                    for _, row in df_b.iterrows():
                        bloc = "Après-midi" if "midi" in str(row[c_statut]).lower() else "Matin"
                        absents = [a.strip().lower() for a in str(row[c_absent]).split(';')] if c_absent else []
                        presents = [a for a in AGENTS if a.lower() not in absents]
                        
                        agt_elu, h_fin = "⚠️ SANS AGENT", "08:15"
                        if presents:
                            db_actuel = pd.DataFrame(temp_rows) if temp_rows else pd.DataFrame(columns=['Date', 'Agent', 'Heure', 'Rue'])
                            for _ in range(len(presents)):
                                p = presents[idx_agt % len(presents)]
                                res_h, possible = calculer_creneau(p, ds, db_actuel, bat_nom, bloc)
                                if possible:
                                    agt_elu, h_fin = p, res_h
                                    idx_agt += 1
                                    break
                                idx_agt += 1

                        temp_rows.append({
                            'ID': row[c_id], 'Batiment': bat_nom, 'Date': ds, 'Heure': h_fin, 
                            'Agent': agt_elu, 'Type': row[c_type] if c_type in row else "Mission", 
                            'Rue': INFOS_BATIMENTS.get(bat_nom, {}).get('rue', ''), 
                            'Statut': bloc, 'Date_Sort': jour
                        })

            st.session_state.db = pd.DataFrame(temp_rows)
            st.rerun()
        except Exception as e:
            st.error(f"Erreur : {e}")

# --- AFFICHAGE ---
if not st.session_state.db.empty:
    with t1:
        df_v = st.session_state.db.sort_values(['Date_Sort', 'Heure'])
        def style_agent(row):
            color = COULEURS.get(row['Agent'], "#ffffff")
            return [f'background-color: {color}; color: black'] * len(row)
        st.dataframe(df_v[['ID', 'Date', 'Statut', 'Heure', 'Agent', 'Batiment', 'Type']].style.apply(style_agent, axis=1), use_container_width=True)
        
        st.divider()
        st.subheader("📥 Exportation Stylée")
        
        # Préparation du format visuel par colonnes
        df_pivot = df_v.copy()
        df_pivot['Contenu'] = df_pivot['Batiment'] + " (ID:" + df_pivot['ID'].astype(str) + ")"
        df_visual = df_pivot.pivot_table(index=['Date', 'Heure'], columns='Agent', values='Contenu', aggfunc='first').reset_index().fillna('')
        
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            df_visual.to_excel(writer, index=False, sheet_name='Planning')
            workbook  = writer.book
            worksheet = writer.sheets['Planning']
            
            # Formatage des couleurs dans Excel
            for i, agent in enumerate(df_visual.columns):
                if agent in COULEURS:
                    fmt = workbook.add_format({'bg_color': COULEURS[agent], 'border': 1})
                    worksheet.set_column(i, i, 25, fmt)
            
        st.download_button("✨ Télécharger le Planning Visuel Coloré", output.getvalue(), "Planning_Equipe.xlsx", type="primary")

    with t2:
        dates_j = sorted(st.session_state.db['Date'].unique(), key=lambda x: datetime.strptime(x, '%d/%m/%Y'))
        sel_j = st.selectbox("📅 Date :", dates_j)
        cols = st.columns(len(AGENTS))
        for i, a in enumerate(AGENTS):
            with cols[i]:
                st.markdown(f"<div style='text-align:center; background-color:{COULEURS[a]}; padding:10px; border-radius:5px; color:black; font-weight:bold;'>{a}</div>", unsafe_allow_html=True)
                m = st.session_state.db[(st.session_state.db['Date'] == sel_j) & (st.session_state.db['Agent'] == a)].sort_values('Heure')
                for _, r in m.iterrows():
                    st.markdown(f"<div style='background-color:{COULEURS[a]}; padding:8px; border-radius:5px; border:1px solid #ccc; color:black; margin-top:5px;'>🆔 <b>{r['ID']}</b><br>🕒 <b>{r['Heure']}</b><br>🏠 {r['Batiment']}</div>", unsafe_allow_html=True)

    with t3:
        # --- RESTAURATION TOTALE DES RAPPORTS D'ORIGINE ---
        df_rep = st.session_state.db.copy()
        df_rep['Mois'] = df_rep['Date_Sort'].dt.strftime('%B %Y')
        col_f1, col_f2 = st.columns(2)
        mois_sel = col_f1.selectbox("📅 Mois :", df_rep['Mois'].unique())
        agents_sel = col_f2.multiselect("👤 Agents :", AGENTS, default=AGENTS)
        df_f = df_rep[(df_rep['Mois'] == mois_sel) & (df_rep['Agent'].isin(agents_sel))]

        if not df_f.empty:
            total_km, groupes_bat, groupes_sec = 0.0, 0, 0
            total_missions = len(df_f)
            
            for agent in agents_sel:
                df_agt = df_f[df_f['Agent'] == agent].sort_values(['Date_Sort', 'Heure'])
                for jour in df_agt['Date'].unique():
                    m_j = df_agt[df_agt['Date'] == jour]
                    prev_coords, prev_bat, prev_sec = BUREAU_GPS, None, None
                    for i, (_, row) in enumerate(m_j.iterrows()):
                        curr_b = row['Batiment']
                        curr_sec = trouver_secteur(curr_b)
                        coords = (INFOS_BATIMENTS[curr_b]['lat'], INFOS_BATIMENTS[curr_b]['lon']) if curr_b in INFOS_BATIMENTS else BUREAU_GPS
                        total_km += calculer_distance(prev_coords, coords)
                        if i > 0:
                            if curr_b == prev_bat: groupes_bat += 1
                            elif curr_sec == prev_sec: groupes_sec += 1
                        prev_coords, prev_bat, prev_sec = coords, curr_b, curr_sec
                    total_km += calculer_distance(prev_coords, BUREAU_GPS)

            st.markdown("### 📊 Indicateurs Clés")
            r1, r2, r3, r4 = st.columns(4)
            r1.metric("Total Missions", total_missions)
            r2.metric("🚗 Distance Est.", f"{total_km:.1f} km")
            r3.metric("🏢 Opti. Bâtiment", f"{(groupes_bat/total_missions*100):.1f}%")
            r4.metric("📍 Opti. Secteur", f"{(groupes_sec/total_missions*100):.1f}%")
            
            nb_entrees = df_f[df_f['Type'].str.contains('Entrée|In', case=False)].shape[0]
            nb_sorties = df_f[df_f['Type'].str.contains('Sortie|Out', case=False)].shape[0]
            st.columns(4)[0].metric("📈 Entrées", nb_entrees)
            st.columns(4)[1].metric("📉 Sorties", nb_sorties)

            st.plotly_chart(px.histogram(df_f, x='Date', color='Agent', barmode='group', color_discrete_map=COULEURS), use_container_width=True)
            
            cl, cr = st.columns(2)
            with cl:
                st.subheader("🏠 Par bâtiment")
                st.table(df_f.groupby('Batiment').size().reset_index(name='Missions').sort_values('Missions', ascending=False))
            with cr:
                st.subheader("📍 Carte")
                map_data = [{'lat': INFOS_BATIMENTS[b]['lat'], 'lon': INFOS_BATIMENTS[b]['lon'], 'Missions': c} 
                            for b, c in df_f.groupby('Batiment').size().items() if b in INFOS_BATIMENTS]
                if map_data: st.map(pd.DataFrame(map_data), size="Missions")
else:
    st.info("Importez un fichier Excel pour commencer.")

if st.sidebar.button("🗑️ Reset"):
    st.session_state.db = pd.DataFrame(columns=['ID', 'Batiment', 'Date', 'Heure', 'Agent', 'Rue', 'Type', 'Statut', 'Date_Sort'])
    st.rerun()
