import streamlit as st
import pandas as pd
from datetime import datetime, timedelta

# --- CONFIGURATION ---
BUREAU = "Chemin Mont Paisible 18, 1011 Lausanne"
AGENTS = ["Celine", "Maria Claret", "Maria Elisabeth"]

# Adresses pour le calcul des trajets
INFOS_BATIMENTS = {
    'Bethusy A': 'Avenue de Béthusy 54, Lausanne',
    'Bethusy B': 'Avenue de Béthusy 56, Lausanne',
    'Montolieu A': 'Isabelle-de-Montolieu 90, Lausanne',
    'Montolieu B': 'Isabelle-de-Montolieu 92, Lausanne',
    'Tunnel': 'Rue du Tunnel 17, Lausanne',
    'Oron': "Route d'Oron 77, 1073 Savigny"
}

COULEURS = {"Celine": "#d1e9ff", "Maria Claret": "#ffdae0", "Maria Elisabeth": "#d4f8d4"}

st.set_page_config(page_title="Unité Logement - Expert", layout="wide")

# Initialisation
if 'db' not in st.session_state:
    st.session_state.db = pd.DataFrame(columns=['Batiment', 'Date', 'Heure', 'Agent', 'Rue', 'Type', 'Date_Sort'])
if 'conges' not in st.session_state:
    st.session_state.conges = pd.DataFrame(columns=['Agent', 'Date_Debut', 'Date_Fin'])

# --- FONCTIONS LOGIQUES ---
def est_disponible(agent, date_str):
    if st.session_state.conges.empty: return True
    try:
        dt = pd.to_datetime(date_str, dayfirst=True)
        for _, c in st.session_state.conges[st.session_state.conges['Agent'] == agent].iterrows():
            if pd.to_datetime(c['Date_Debut'], dayfirst=True) <= dt <= pd.to_datetime(c['Date_Fin'], dayfirst=True): return False
    except: pass
    return True

def trouver_meilleur_creneau(batiment, date_str, temp_db):
    rue_cible = INFOS_BATIMENTS.get(batiment, "Autre")
    m_jour = temp_db[temp_db['Date'] == date_str]
    pause_deb, pause_fin = datetime.strptime("12:00", "%H:%M"), datetime.strptime("13:00", "%H:%M")
    def ajuster(h): return pause_fin if h > pause_deb and h < pause_fin else h
    presents = [a for a in AGENTS if est_disponible(a, date_str)]
    if not presents: return "À définir", "08:15"
    if "Celine" in presents:
        m_rue = m_jour[(m_jour['Agent'] == "Celine") & (m_jour['Rue'] == rue_cible)]
        if not m_rue.empty:
            hf = datetime.strptime(m_rue.sort_values(by='Heure').iloc[-1]['Heure'], "%H:%M") + timedelta(hours=1, minutes=15)
            return "Celine", ajuster(hf).strftime("%H:%M")
        m_celine = m_jour[m_jour['Agent'] == "Celine"]
        if m_celine.empty: return "Celine", "08:15"
        hfc = datetime.strptime(m_celine.sort_values(by='Heure').iloc[-1]['Heure'], "%H:%M") + timedelta(hours=1, minutes=30)
        if hfc < datetime.strptime("15:30", "%H:%M"): return "Celine", ajuster(hfc).strftime("%H:%M")
    for agt in [a for a in ["Maria Claret", "Maria Elisabeth"] if a in presents]:
        m_agt = m_jour[m_jour['Agent'] == agt]
        if m_agt.empty: return agt, "08:15"
        hfa = datetime.strptime(m_agt.sort_values(by='Heure').iloc[-1]['Heure'], "%H:%M") + timedelta(hours=1, minutes=30)
        if hfa < datetime.strptime("16:00", "%H:%M"): return agt, ajuster(hfa).strftime("%H:%M")
    return presents[0], "08:15"

# --- INTERFACE ---
st.title("📍 Unité Logement : Optimisation & Analyses")
t1, t2, t3 = st.tabs(["📝 Planning", "📅 Calendrier", "📊 Analyses de Charge"])

with st.sidebar:
    st.header("🌴 Congés")
    abs_agt = st.selectbox("Agent", AGENTS)
    d1, d2 = st.date_input("Du"), st.date_input("Au")
    if st.button("Valider"):
        st.session_state.conges = pd.concat([st.session_state.conges, pd.DataFrame([{'Agent': abs_agt, 'Date_Debut': d1.strftime('%d/%m/%Y'), 'Date_Fin': d2.strftime('%d/%m/%Y')}])], ignore_index=True)
    st.divider()
    up = st.file_uploader("Excel", type=['xlsx'])
    if up and st.button("🚀 Planifier"):
        df_ex = pd.read_excel(up).dropna(how='all').fillna('')
        df_ex.columns = df_ex.columns.str.strip()
        col_d = next((c for c in df_ex.columns if 'date' in c.lower()), 'Date')
        temp = pd.DataFrame(columns=['Batiment', 'Date', 'Heure', 'Agent', 'Rue', 'Type', 'Date_Sort'])
        for _, row in df_ex.sort_values(by=[col_d, 'Batiment']).iterrows():
            dt = pd.to_datetime(row[col_d]); ds = dt.strftime('%d/%m/%Y')
            agt, hr = trouver_meilleur_creneau(row['Batiment'], ds, temp)
            temp = pd.concat([temp, pd.DataFrame([{'Batiment': row['Batiment'], 'Date': ds, 'Heure': hr, 'Agent': agt, 'Rue': INFOS_BATIMENTS.get(row['Batiment'], "Autre"), 'Type': "Import", 'Date_Sort': dt}])], ignore_index=True)
        st.session_state.db = temp; st.rerun()

with t1:
    if not st.session_state.db.empty:
        st.table(st.session_state.db.sort_values(by=['Date_Sort', 'Heure']).style.apply(lambda r: [f'background-color: {COULEURS.get(r["Agent"])}']*len(r), axis=1))

with t2:
    if not st.session_state.db.empty:
        sel_j = st.selectbox("Jour", sorted(st.session_state.db['Date'].unique()))
        cols = st.columns(3)
        for i, a in enumerate(AGENTS):
            with cols[i]:
                st.markdown(f"<div style='text-align:center; background-color:{COULEURS[a]}; padding:10px; border-radius:5px;'><b>{a}</b></div>", unsafe_allow_html=True)
                m = st.session_state.db[(st.session_state.db['Date'] == sel_j) & (st.session_state.db['Agent'] == a)].sort_values(by='Heure')
                for _, r in m.iterrows(): st.info(f"**{r['Heure']}** - {r['Batiment']}")

# --- ONGLET ANALYSES COMPLET ---
with t3:
    if not st.session_state.db.empty:
        st.subheader("📊 Rapport d'activité et Déplacements")
        
        # 1. Résumé Global
        nb_tot = len(st.session_state.db)
        groupements = st.session_state.db.groupby(['Date', 'Rue']).size()
        opti = (len(groupements[groupements > 1]) / nb_tot * 100) if nb_tot > 0 else 0
        
        c1, c2, c3 = st.columns(3)
        c1.metric("Total Entretiens", f"{nb_tot}")
        c2.metric("Temps Terrain Total", f"{nb_tot}h")
        c3.metric("Taux d'Optimisation", f"{int(opti)}%")

        st.divider()

        # 2. Détail par Collaboratrice (Temps de Route)
        sel_j_stats = st.selectbox("Sélectionner une journée pour analyser les trajets :", sorted(st.session_state.db['Date'].unique()))
        st.write(f"### Détail des déplacements du {sel_j_stats}")
        
        day_data = st.session_state.db[st.session_state.db['Date'] == sel_j_stats]
        
        for agent in AGENTS:
            agt_data = day_data[day_data['Agent'] == agent].sort_values(by='Heure')
            if not agt_data.empty:
                st.markdown(f"#### 👩‍💻 {agent}")
                
                # Itinéraire : Bureau -> Missions -> Bureau
                itineraire = [BUREAU] + agt_data['Rue'].tolist() + [BUREAU]
                temps_route_total = 0
                
                # Tableau de trajet
                trajets = []
                for k in range(len(itineraire)-1):
                    dep = itineraire[k]
                    arr = itineraire[k+1]
                    
                    # Logique de temps : Oron est loin, le centre est plus proche
                    if "Oron" in dep or "Oron" in arr:
                        duree = 25 
                    elif dep == arr:
                        duree = 5 # Même rue
                    else:
                        duree = 15 # Trajet standard Lausanne
                        
                    temps_route_total += duree
                    trajets.append({"De": dep.split(',')[0], "À": arr.split(',')[0], "Temps est.": f"{duree} min"})
                
                st.table(pd.DataFrame(trajets))
                
                col_res1, col_res2 = st.columns(2)
                col_res1.write(f"🏠 **Total Terrain :** {len(agt_data)}h00")
                col_res2.write(f"🚗 **Total Route :** {temps_route_total} min")
                st.divider()
    else:
        st.info("Veuillez importer des données pour générer les analyses.")
