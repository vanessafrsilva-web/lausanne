import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import io

# --- CONFIGURATION FIXE ---
BUREAU = "Chemin Mont-Paisible 18, 1011 Lausanne"
AGENTS = ["Celine", "Maria Claret", "Maria Elisabeth"]

# Coordonnées GPS pour la cartographie
INFOS_BATIMENTS = {
    'Bethusy A': {'rue': 'Avenue de Béthusy 54, Lausanne', 'lat': 46.5225, 'lon': 6.6472},
    'Bethusy B': {'rue': 'Avenue de Béthusy 56, Lausanne', 'lat': 46.5227, 'lon': 6.6475},
    'Montolieu A': {'rue': 'Isabelle-de-Montolieu 90, Lausanne', 'lat': 46.5412, 'lon': 6.6421},
    'Montolieu B': {'rue': 'Isabelle-de-Montolieu 92, Lausanne', 'lat': 46.5415, 'lon': 6.6425},
    'Tunnel': {'rue': 'Rue du Tunnel 17, Lausanne', 'lat': 46.5255, 'lon': 6.6328},
    'Oron': {'rue': "Route d'Oron 77, 1010 Lausanne", 'lat': 46.5361, 'lon': 6.6625}
}

# Couleurs pour l'interface (HEX)
COULEURS_HEX = {
    "Celine": "#d1e9ff",        # Bleu clair
    "Maria Claret": "#ffdae0",  # Rose clair
    "Maria Elisabeth": "#d4f8d4", # Vert clair
    "⚠️ SANS AGENT": "#eeeeee"
}

# Couleurs pour la carte (RGB)
COULEURS_RGB = {
    "Celine": [0, 123, 255, 160],
    "Maria Claret": [255, 51, 161, 160],
    "Maria Elisabeth": [40, 167, 69, 160],
    "⚠️ SANS AGENT": [200, 200, 200, 100]
}

st.set_page_config(page_title="Unité Logement - Gestion Planning", layout="wide")

if 'db' not in st.session_state:
    st.session_state.db = pd.DataFrame(columns=['Batiment', 'Date', 'Heure', 'Agent', 'Rue', 'Type', 'Statut', 'Date_Sort'])

# --- FONCTIONS LOGIQUES ---

def calculer_creneau_securise(agent, date_str, temp_db, batiment_cible, bloc_impose=None, heure_forcee=None):
    # On regarde ce que l'agent a déjà ce jour-là
    m_jour = temp_db[(temp_db['Date'] == date_str) & (temp_db['Agent'] == agent)]
    
    if heure_forcee:
        # Si l'heure est déjà prise exactement par ce même agent
        if not m_jour.empty and heure_forcee in [str(h).strip() for h in m_jour['Heure'].values]:
            return "⚠️ CONFLIT", True # On retourne True pour forcer l'ajout malgré le conflit
        return heure_forcee, True

    if m_jour.empty:
        h_depart_str = "08:15" if bloc_impose != "Après-midi" else "13:00"
    else:
        h_depart_str = str(m_jour.iloc[-1]['Heure']).strip()

    try:
        if "⚠️" in h_depart_str: h_depart_str = "08:15"
        h_obj = datetime.strptime(h_depart_str, "%H:%M")
        info_b = INFOS_BATIMENTS.get(batiment_cible, {'rue': 'Autre'})
        rue_cible = info_b['rue']
        derniere_rue = m_jour.iloc[-1]['Rue'] if not m_jour.empty else "Bureau"
        
        delai = 65 if derniere_rue == rue_cible else 80 
        prochaine_h = h_obj + timedelta(minutes=delai) if not m_jour.empty else h_obj
        
        if datetime.strptime("12:00", "%H:%M") <= prochaine_h < datetime.strptime("13:00", "%H:%M"):
            prochaine_h = datetime.strptime("13:00", "%H:%M")
        
        if prochaine_h > datetime.strptime("16:30", "%H:%M"):
            return "COMPLET JOUR", False
            
        return prochaine_h.strftime("%H:%M"), True
    except:
        return "08:15", True

# --- INTERFACE SIDEBAR ---
with st.sidebar:
    st.header("📂 Importation")
    up = st.file_uploader("Fichier Excel des missions", type=['xlsx'])
    mode_ia = st.radio("Méthode :", ["Respecter l'heure de l'Excel (Fixe)", "Optimiser par blocs"])

    if up and st.button("🚀 Lancer l'Attribution"):
        df_ex = pd.read_excel(up).dropna(how='all').fillna('')
        df_ex.columns = df_ex.columns.str.strip()
        
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

    if st.button("🗑️ Reset Complet"):
        st.session_state.db = pd.DataFrame(columns=['Batiment', 'Date', 'Heure', 'Agent', 'Rue', 'Type', 'Statut', 'Date_Sort'])
        st.rerun()

# --- CORPS PRINCIPAL ---
st.title("📍 Unité Logement : Planning")

t1, t2, t3 = st.tabs(["📝 Planning Global", "📅 Vue par Agent", "📊 Rapports Mensuels"])

with t1:
    if not st.session_state.db.empty:
        df_v = st.session_state.db.sort_values(['Date_Sort', 'Heure'])
        def style_row(s):
            if "⚠️ CONFLIT" in str(s['Heure']): return ['background-color: #ffb3b3; color: #b30000; font-weight: bold']*7
            color = COULEURS_HEX.get(s['Agent'], "#eeeeee")
            return [f'background-color: {color}']*7
        st.dataframe(df_v[['Date', 'Heure', 'Agent', 'Batiment', 'Type', 'Statut', 'Rue']].style.apply(style_row, axis=1), use_container_width=True, height=500)

with t2:
    if not st.session_state.db.empty:
        sel_j = st.selectbox("Sélectionner la date :", sorted(st.session_state.db['Date'].unique(), key=lambda x: datetime.strptime(x, '%d/%m/%Y')))
        cols = st.columns(len(AGENTS))
        for i, a in enumerate(AGENTS):
            with cols[i]:
                st.markdown(f"<div style='text-align:center; background-color:{COULEURS_HEX[a]}; padding:10px; border-radius:5px; color:black; font-weight:bold; margin-bottom:10px'>{a}</div>", unsafe_allow_html=True)
                # On récupère toutes les missions de l'agent pour ce jour
                m_agent = st.session_state.db[(st.session_state.db['Date'] == sel_j) & (st.session_state.db['Agent'] == a)].sort_values('Heure')
                
                for _, r in m_agent.iterrows():
                    # Si c'est un conflit, on affiche en rouge
                    if "⚠️ CONFLIT" in str(r['Heure']):
                        st.error(f"🚨 **CONFLIT**\n\nHeure Excel identique\n\n**{r['Batiment']}**")
                    else:
                        st.info(f"🕒 **{r['Heure']}**\n\n**{r['Batiment']}**\n\n_{r['Type']}_")

with t3:
    if not st.session_state.db.empty:
        df_rep = st.session_state.db.copy()
        df_rep['Mois'] = df_rep['Date_Sort'].dt.strftime('%B %Y')
        mois_sel = st.selectbox("Mois :", df_rep['Mois'].unique())
        df_m = df_rep[df_rep['Mois'] == mois_sel]
        
        st.divider()
        cl, cr = st.columns([1, 1.5])
        with cl:
            st.subheader("🏠 Volume")
            st.table(df_m.groupby('Batiment').size().reset_index(name='Nb').sort_values('Nb', ascending=False))
        with cr:
            st.subheader("📍 Carte")
            map_points = []
            for bat in df_m['Batiment'].unique():
                if bat in INFOS_BATIMENTS:
                    count = len(df_m[df_m['Batiment'] == bat])
                    agt_name = df_m[df_m['Batiment'] == bat]['Agent'].iloc[0]
                    map_points.append({
                        'lat': float(INFOS_BATIMENTS[bat]['lat']),
                        'lon': float(INFOS_BATIMENTS[bat]['lon']),
                        'Taille': int(count * 40),
                        'Couleur': COULEURS_RGB.get(agt_name, [200, 200, 200, 150])
                    })
            if map_points:
                st.map(pd.DataFrame(map_points), latitude='lat', longitude='lon', size='Taille', color='Couleur')

st.caption("v3.4")
