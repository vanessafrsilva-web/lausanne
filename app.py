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

COULEURS = {"Celine": "#d1e9ff", "Maria Claret": "#ffdae0", "Maria Elisabeth": "#d4f8d4", "À définir": "#eeeeee", "⚠️ SANS AGENT": "#333333"}

st.set_page_config(page_title="Unité Logement - Gestion Planning", layout="wide", page_icon="📍")

# --- FONCTION DISTANCE ---
def calculer_distance(pos1, pos2):
    if not pos1 or not pos2: return 0
    R = 6371.0
    lat1, lon1 = np.radians(pos1[0]), np.radians(pos1[1])
    lat2, lon2 = np.radians(pos2[0]), np.radians(pos2[1])
    dlon = lon2 - lon1
    dlat = dlat = lat2 - lat1
    a = np.sin(dlat / 2)**2 + np.cos(lat1) * np.cos(lat2) * np.sin(dlon / 2)**2
    c = 2 * np.arctan2(np.sqrt(a), np.sqrt(1 - a))
    return R * c

if 'db' not in st.session_state:
    st.session_state.db = pd.DataFrame(columns=['ID', 'Batiment', 'Date', 'Heure', 'Agent', 'Rue', 'Type', 'Statut', 'Date_Sort'])

# --- FONCTIONS LOGIQUES ---
def calculer_creneau_securise(agent, date_str, temp_db, batiment_cible, bloc_impose=None, heure_forcee=None):
    m_jour = temp_db[(temp_db['Date'] == date_str) & (temp_db['Agent'] == agent)]
    if heure_forcee:
        if not m_jour.empty and heure_forcee in [str(h) for h in m_jour['Heure'].values]:
            return "⚠️ CONFLIT", False
        return heure_forcee, True

    if m_jour.empty:
        h_depart_str = "08:15" if bloc_impose != "Après-midi" else "13:00"
    else:
        h_depart_str = str(m_jour.iloc[-1]['Heure']).strip()

    try:
        h_obj = datetime.strptime(h_depart_str, "%H:%M")
        rue_cible = INFOS_BATIMENTS.get(batiment_cible, {}).get('rue', "Autre")
        derniere_rue = m_jour.iloc[-1]['Rue'] if not m_jour.empty else "Bureau"
        delai = 65 if derniere_rue == rue_cible else 80 
        prochaine_h = h_obj + timedelta(minutes=delai) if not m_jour.empty else h_obj
        if datetime.strptime("12:00", "%H:%M") <= prochaine_h < datetime.strptime("13:00", "%H:%M"):
            prochaine_h = datetime.strptime("13:00", "%H:%M")
        if bloc_impose == "Matin" and prochaine_h > datetime.strptime("11:45", "%H:%M"):
            return "COMPLET MATIN", False
        if prochaine_h > datetime.strptime("16:30", "%H:%M"):
            return "COMPLET JOUR", False
        return prochaine_h.strftime("%H:%M"), True
    except:
        return "08:15", True

# --- INTERFACE ---
st.title("📍 Unité Logement : Planning & Rapports")
st.caption(f"📍 Siège social : {BUREAU_ADRESSE}")

t1, t2, t3 = st.tabs(["📝 Planning Global", "📅 Vue par Agent", "📊 Rapports & Analyses"])

with st.sidebar:
    st.header("📂 Importation")
    up = st.file_uploader("Fichier Excel des missions", type=['xlsx'])
    mode_ia = st.radio("Méthode :", ["Respecter l'heure de l'Excel (Fixe)", "Optimiser par blocs (Matin / Après-midi)"])

    if up and st.button("🚀 Lancer l'Attribution"):
        with st.spinner("Calcul en cours..."):
            try:
                df_ex = pd.read_excel(up).dropna(how='all').fillna('')
                df_ex.columns = df_ex.columns.str.strip()
                c_id = next((c for c in df_ex.columns if 'id' in c.lower() or 'n°' in c.lower()), df_ex.columns[0])
                c_date = next((c for c in df_ex.columns if 'date' in c.lower()), 'Date')
                c_heure = next((c for c in df_ex.columns if 'heure' in c.lower()), 'Heure')
                c_type = next((c for c in df_ex.columns if 'type' in c.lower()), 'Type')
                c_absent = next((c for c in df_ex.columns if 'absent' in c.lower()), None)
                c_statut = next((c for c in df_ex.columns if 'statut' in c.lower()), 'Statut')

                temp = pd.DataFrame(columns=['ID', 'Batiment', 'Date', 'Heure', 'Agent', 'Rue', 'Type', 'Statut', 'Date_Sort'])
                df_ex_sorted = df_ex.copy()
                df_ex_sorted[c_date] = pd.to_datetime(df_ex_sorted[c_date])
                df_ex_sorted = df_ex_sorted.sort_values(by=[c_date, c_heure])

                for _, row in df_ex_sorted.iterrows():
                    dt_raw = row[c_date]
                    ds = dt_raw.strftime('%d/%m/%Y')
                    info_b = INFOS_BATIMENTS.get(row['Batiment'], {'rue': 'Autre'})
                    rue_demandee = info_b['rue']
                    statut_val = str(row[c_statut]).strip()
                    h_excel = str(row[c_heure]).strip()[:5] if str(row[c_heure]).strip() not in ["", "nan", "libre"] else None
                    bloc = "Matin" if "matin" in statut_val.lower() else ("Après-midi" if "midi" in statut_val.lower() else None)
                    absents = [a.strip().lower().replace('-', ' ') for a in str(row[c_absent]).split(';')] if c_absent and str(row[c_absent]).strip() != "" else []
                    presents = [a for a in AGENTS if a.lower().replace('-', ' ') not in absents]
                    
                    agt_elu, h_finale = "⚠️ SANS AGENT", h_excel if h_excel else "08:15"
                    
                    if presents:
                        scores = {p: (0 if (not temp[(temp['Date'] == ds) & (temp['Agent'] == p)].empty and temp[(temp['Date'] == ds) & (temp['Agent'] == p)].iloc[-1]['Rue'] == rue_demandee) else 1) for p in presents}
                        presents_tries = sorted(presents, key=lambda x: (scores[x], len(temp[(temp['Date'] == ds) & (temp['Agent'] == x)])))
                        for p in presents_tries:
                            res_h, possible = calculer_creneau_securise(p, ds, temp, row['Batiment'], bloc, h_excel if "Fixe" in mode_ia else None)
                            if possible:
                                agt_elu, h_finale = p, res_h
                                break
                            elif res_h == "⚠️ CONFLIT":
                                agt_elu, h_finale = p, "⚠️ CONFLIT"

                    temp = pd.concat([temp, pd.DataFrame([{
                        'ID': row[c_id], 'Batiment': row['Batiment'], 'Date': ds, 'Heure': h_finale, 'Agent': agt_elu, 
                        'Type': row[c_type], 'Rue': rue_demandee, 'Statut': statut_val, 'Date_Sort': dt_raw
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
        st.download_button("📥 Télécharger Excel", output.getvalue(), "Planning.xlsx")
        if st.button("🗑️ Reset"):
            st.session_state.db = pd.DataFrame(columns=['ID', 'Batiment', 'Date', 'Heure', 'Agent', 'Rue', 'Type', 'Statut', 'Date_Sort'])
            st.rerun()

# --- ONGLETS ---
with t1:
    if not st.session_state.db.empty:
        # --- FILTRE ÉLÉGANT ---
        agents_dispo = sorted([a for a in st.session_state.db['Agent'].unique() if a != "⚠️ SANS AGENT"])
        
        filtre_agt = st.pills(
            "Filtrer par agent :", 
            agents_dispo, 
            selection_mode="multi", 
            default=agents_dispo
        )
        
        # On inclut toujours "SANS AGENT" dans le calcul si présent, mais on filtre sur les autres
        selection = list(filtre_agt) if filtre_agt else []
        if "⚠️ SANS AGENT" in st.session_state.db['Agent'].values:
            selection.append("⚠️ SANS AGENT")

        df_v = st.session_state.db[st.session_state.db['Agent'].isin(selection)].sort_values(['Date_Sort', 'Heure'])
        
        if not df_v.empty:
            def style_row(s):
                if s['Heure'] == "⚠️ CONFLIT": return ['background-color: #ffcccc; color: #cc0000; font-weight: bold']*8
                color = COULEURS.get(s['Agent'], "#eeeeee")
                if str(s['Statut']).strip() != "": return [f'background-color: {color}; border: 2px solid #ff9933']*8
                return [f'background-color: {color}; color: black']*8
                
            st.dataframe(
                df_v[['ID', 'Date', 'Statut', 'Heure', 'Agent', 'Batiment', 'Type', 'Rue']].style.apply(style_row, axis=1), 
                use_container_width=True, 
                height=600
            )
        else:
            st.info("Sélectionnez un agent pour voir son planning.")

with t2:
    if not st.session_state.db.empty:
        sel_j = st.selectbox("📅 Date :", sorted(st.session_state.db['Date'].unique(), key=lambda x: datetime.strptime(x, '%d/%m/%Y')))
        cols = st.columns(len(AGENTS))
        for i, a in enumerate(AGENTS):
            with cols[i]:
                st.markdown(f"<div style='text-align:center; background-color:{COULEURS[a]}; padding:10px; border-radius:5px; color:black; font-weight:bold;'>{a}</div>", unsafe_allow_html=True)
                m = st.session_state.db[(st.session_state.db['Date'] == sel_j) & (st.session_state.db['Agent'] == a)].sort_values('Heure')
                for _, r in m.iterrows():
                    color = "#ffcccc" if r['Heure'] == "⚠️ CONFLIT" else COULEURS[a]
                    st.markdown(f"<div style='background-color:{color}; padding:8px; border-radius:5px; border:1px solid #ccc; color:black; margin-top:5px;'>🆔 <b>{r['ID']}</b><br>🕒 <b>{r['Heure']}</b><br>🏠 {r['Batiment']}</div>", unsafe_allow_html=True)

with t3:
    if st.session_state.db.empty:
        st.info("Importez un fichier Excel pour voir les analyses.")
    else:
        df_rep = st.session_state.db.copy()
        df_rep['Mois'] = df_rep['Date_Sort'].dt.strftime('%B %Y')
        col_f1, col_f2 = st.columns(2)
        mois_sel = col_f1.selectbox("📅 Choisir le Mois :", df_rep['Mois'].unique())
        options_agents = [a for a in df_rep['Agent'].unique() if a != "⚠️ SANS AGENT"]
        agents_sel = col_f2.multiselect("👤 Sélectionner Agents (Analyses) :", options_agents, default=options_agents)
        df_final = df_rep[(df_rep['Mois'] == mois_sel) & (df_rep['Agent'].isin(agents_sel))]

        if df_final.empty:
            st.warning("Aucune donnée pour cette sélection.")
        else:
            total_km = 0.0
            groupes = 0
            for agent in agents_sel:
                df_agt = df_final[df_final['Agent'] == agent].sort_values(['Date_Sort', 'Heure'])
                for jour in df_agt['Date'].unique():
                    missions_j = df_agt[df_agt['Date'] == jour]
                    prev_coords = BUREAU_GPS
                    for i, (_, row) in enumerate(missions_j.iterrows()):
                        curr_b = row['Batiment']
                        coords = (INFOS_BATIMENTS[curr_b]['lat'], INFOS_BATIMENTS[curr_b]['lon']) if curr_b in INFOS_BATIMENTS else BUREAU_GPS
                        total_km += calculer_distance(prev_coords, coords)
                        if i > 0 and curr_b == missions_j.iloc[i-1]['Batiment']:
                            groupes += 1
                        prev_coords = coords
                    total_km += calculer_distance(prev_coords, BUREAU_GPS)

            tx_opti = (groupes / len(df_final) * 100) if len(df_final) > 0 else 0
            nb_entrees = df_final[df_final['Type'].str.contains('Entrée|In', case=False)].shape[0]
            nb_sorties = df_final[df_final['Type'].str.contains('Sortie|Out', case=False)].shape[0]

            st.markdown("### 📊 Indicateurs Clés")
            row1 = st.columns(4)
            row1[0].metric("Total Missions", len(df_final))
            row1[1].metric("📈 Taux Opti.", f"{tx_opti:.1f}%")
            row1[2].metric("🚗 Distance Est.", f"{total_km:.1f} km")
            row1[3].metric("📅 Jours d'activité", df_final['Date'].nunique())
            row2 = st.columns(4)
            row2[0].metric("📈 Nb Entrées", nb_entrees)
            row2[1].metric("📉 Nb Sorties", nb_sorties)
            row2[2].metric("👥 Agents actifs", len(agents_sel))
            row2[3].metric("🏠 Bâtiments visités", df_final['Batiment'].nunique())
            
            st.divider()
            df_chart = df_final.copy()
            df_chart['Semaine'] = df_chart['Date_Sort'].dt.isocalendar().week
            df_chart['Nom_Semaine'] = "Semaine " + df_chart['Semaine'].astype(str)
            fig = px.histogram(df_chart.sort_values('Semaine'), x='Nom_Semaine', color='Agent', 
                               color_discrete_map=COULEURS, barmode='group', text_auto=True)
            st.plotly_chart(fig, use_container_width=True)

st.divider()
st.caption(f"v3.9 | {datetime.now().year}")
