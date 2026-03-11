import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import io

# --- CONFIGURATION FIXE ---
BUREAU = "Chemin Mont-Paisible 18, 1011 Lausanne"
AGENTS = ["Celine", "Maria Claret", "Maria Elisabeth"]

# Coordonnées GPS
INFOS_BATIMENTS = {
    'Bethusy A': {'rue': 'Avenue de Béthusy 54, Lausanne', 'lat': 46.5225, 'lon': 6.6472},
    'Bethusy B': {'rue': 'Avenue de Béthusy 56, Lausanne', 'lat': 46.5227, 'lon': 6.6475},
    'Montolieu A': {'rue': 'Isabelle-de-Montolieu 90, Lausanne', 'lat': 46.5412, 'lon': 6.6421},
    'Montolieu B': {'rue': 'Isabelle-de-Montolieu 92, Lausanne', 'lat': 46.5415, 'lon': 6.6425},
    'Tunnel': {'rue': 'Rue du Tunnel 17, Lausanne', 'lat': 46.5255, 'lon': 6.6328},
    'Oron': {'rue': "Route d'Oron 77, 1010 Lausanne", 'lat': 46.5361, 'lon': 6.6625}
}

# Couleurs pour le planning (HEX)
COULEURS_HEX = {"Celine": "#d1e9ff", "Maria Claret": "#ffdae0", "Maria Elisabeth": "#d4f8d4", "À définir": "#eeeeee"}

# Couleurs pour la carte (Format RGB requis par Streamlit pour éviter l'erreur JSON)
COULEURS_RGB = {
    "Celine": [0, 123, 255, 160],          # Bleu
    "Maria Claret": [255, 51, 161, 160],    # Rose
    "Maria Elisabeth": [40, 167, 69, 160],  # Vert
    "⚠️ SANS AGENT": [200, 200, 200, 100]
}

st.set_page_config(page_title="Unité Logement - Gestion Planning", layout="wide")

if 'db' not in st.session_state:
    st.session_state.db = pd.DataFrame(columns=['Batiment', 'Date', 'Heure', 'Agent', 'Rue', 'Type', 'Statut', 'Date_Sort'])

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

with st.sidebar:
    st.header("📂 Importation")
    up = st.file_uploader("Fichier Excel des missions", type=['xlsx'])
    mode_ia = st.radio("Méthode :", ["Respecter l'heure de l'Excel (Fixe)", "Optimiser par blocs"])

    if up and st.button("🚀 Lancer l'Attribution"):
        df_ex = pd.read_excel(up).dropna(how='all').fillna('')
        df_ex.columns = df_ex.columns.str.strip()
        
        # Identification des colonnes
        c_date = next((c for c in df_ex.columns if 'date' in c.lower()), 'Date')
        c_heure = next((c for c in df_ex.columns if 'heure' in c.lower()), 'Heure')
        c_type = next((c for c in df_ex.columns if 'type' in c.lower()), 'Type')
        c_absent = next((c for c in df_ex.columns if 'absent' in c.lower()), None)
        c_statut = next((c for c in df_ex.columns if 'statut' in c.lower()), 'Statut')

        temp = pd.DataFrame(columns=['Batiment', 'Date', 'Heure', 'Agent', 'Rue', 'Type', 'Statut', 'Date_Sort'])
        
        for _, row in df_ex.sort_values(by=[c_date, c_heure]).iterrows():
            dt_raw = pd.to_datetime(row[c_date])
            ds = dt_raw.strftime('%d/%m/%Y')
            info_b = INFOS_BATIMENTS.get(row['Batiment'], {'rue': 'Autre'})
            rue_demandee = info_b['rue']
            statut_val = str(row[c_statut]).strip()
            h_excel = str(row[c_heure]).strip()[:5] if str(row[c_heure]).strip() not in ["", "nan", "libre"] else None

            absents = [a.strip().lower().replace('-', ' ') for a in str(row[c_absent]).split(';')] if c_absent and str(row[c_absent]).strip() != "" else []
            presents = [a for a in AGENTS if a.lower().replace('-', ' ') not in absents]
            
            agt_elu, h_finale = "⚠️ SANS AGENT", h_excel if h_excel else "08:15"
            
            if presents:
                presents_tries = sorted(presents, key=lambda x: len(temp[(temp['Date'] == ds) & (temp['Agent'] == x)]))
                for p in presents_tries:
                    res_h, possible = calculer_creneau_securise(p, ds, temp, row['Batiment'], None, h_excel if "Fixe" in mode_ia else None)
                    if possible:
                        agt_elu, h_finale = p, res_h
                        break
            
            temp = pd.concat([temp, pd.DataFrame([{
                'Batiment': row['Batiment'], 'Date': ds, 'Heure': h_finale, 'Agent': agt_elu, 
                'Type': row[c_type], 'Rue': rue_demandee, 'Statut': statut_val, 'Date_Sort': dt_raw
            }])], ignore_index=True)
            
        st.session_state.db = temp
        st.rerun()

    if st.button("🗑️ Reset"):
        st.session_state.db = pd.DataFrame(columns=['Batiment', 'Date', 'Heure', 'Agent', 'Rue', 'Type', 'Statut', 'Date_Sort'])
        st.rerun()

t1, t2, t3 = st.tabs(["📝 Planning", "📅 Vue Agent", "📊 Rapports"])

with t1:
    if not st.session_state.db.empty:
        df_v = st.session_state.db.sort_values(['Date_Sort', 'Heure'])
        st.dataframe(df_v[['Date', 'Heure', 'Agent', 'Batiment', 'Type', 'Statut']], use_container_width=True)

with t3:
    if not st.session_state.db.empty:
        df_rep = st.session_state.db.copy()
        df_rep['Mois'] = df_rep['Date_Sort'].dt.strftime('%B %Y')
        mois_sel = st.selectbox("Mois :", df_rep['Mois'].unique())
        agent_sel = st.selectbox("Agent (Carte) :", ["Tous"] + AGENTS)
        
        df_m = df_rep[df_rep['Mois'] == mois_sel]
        if agent_sel != "Tous":
            df_m = df_m[df_m['Agent'] == agent_sel]

        col1, col2 = st.columns([1, 2])
        with col1:
            stats = df_m.groupby('Batiment').size().reset_index(name='Missions')
            st.table(stats)
        
        with col2:
            # Reconstruction propre des données carte pour éviter l'erreur JSON
            map_list = []
            for _, r in stats.iterrows():
                b_name = r['Batiment']
                if b_name in INFOS_BATIMENTS:
                    # Trouver l'agent pour la couleur
                    first_agt = df_m[df_m['Batiment'] == b_name]['Agent'].iloc[0]
                    map_list.append({
                        'lat': float(INFOS_BATIMENTS[b_name]['lat']),
                        'lon': float(INFOS_BATIMENTS[b_name]['lon']),
                        'size': int(r['Missions'] * 50),
                        'color': COULEURS_RGB.get(first_agt, [200, 200, 200, 150])
                    })
            
            if map_list:
                df_map = pd.DataFrame(map_list)
                st.map(df_map, latitude='lat', longitude='lon', size='size', color='color')
            else:
                st.info("Aucune donnée GPS")

st.caption("v3.2 - Fix JSON Error")
