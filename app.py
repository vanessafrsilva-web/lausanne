import streamlit as st
import pandas as pd
from datetime import datetime, timedelta

# --- CONFIGURATION FIXE (MISE À JOUR) ---
BUREAU = "Chemin Mont Paisible 18, 1011 Lausanne"
AGENTS = ["Celine", "Maria Claret", "Maria Elisabeth"]

INFOS_BATIMENTS = {
    'Bethusy A': 'Avenue de Béthusy 54, Lausanne',
    'Bethusy B': 'Avenue de Béthusy 56, Lausanne',
    'Montolieu A': 'Isabelle-de-Montolieu 90, Lausanne',
    'Montolieu B': 'Isabelle-de-Montolieu 92, Lausanne',
    'Tunnel': 'Rue du Tunnel 17, Lausanne',
    'Oron': "Route d'Oron 77, 1010 Lausanne" # Correction effectuée ici
}

COULEURS = {
    "Celine": "#d1e9ff",
    "Maria Claret": "#ffdae0",
    "Maria Elisabeth": "#d4f8d4",
    "À définir": "#eeeeee"
}

st.set_page_config(page_title="Unité Logement - Expert", layout="wide")

# Initialisation
if 'db' not in st.session_state:
    st.session_state.db = pd.DataFrame(columns=['Batiment', 'Date', 'Heure', 'Agent', 'Rue', 'Date_Sort'])
if 'conges' not in st.session_state:
    st.session_state.conges = pd.DataFrame(columns=['Agent', 'Date_Debut', 'Date_Fin'])

# --- FONCTIONS ---

def est_disponible(agent, date_str):
    if st.session_state.conges.empty: return True
    try:
        dt_cible = pd.to_datetime(date_str, dayfirst=True)
        for _, c in st.session_state.conges[st.session_state.conges['Agent'] == agent].iterrows():
            d = pd.to_datetime(c['Date_Debut'], dayfirst=True)
            f = pd.to_datetime(c['Date_Fin'], dayfirst=True)
            if d <= dt_cible <= f: return False
    except: pass
    return True

def calculer_prochain_creneau(agent, date_str, temp_db):
    m_jour = temp_db[(temp_db['Date'] == date_str) & (temp_db['Agent'] == agent)]
    if m_jour.empty:
        return "08:15"
    
    # On nettoie le marqueur (*) pour le calcul mathématique
    derniere_h_str = str(m_jour.iloc[-1]['Heure']).replace("(*)", "").strip()
    try:
        heure_obj = datetime.strptime(derniere_h_str, "%H:%M")
        # 1h entretien + 15 min trajet moyen
        prochaine_h = heure_obj + timedelta(hours=1, minutes=15)
        
        # Gestion pause (12h-13h)
        if datetime.strptime("12:00", "%H:%M") <= prochaine_h < datetime.strptime("13:00", "%H:%M"):
            prochaine_h = datetime.strptime("13:00", "%H:%M")
            
        return prochaine_h.strftime("%H:%M")
    except:
        return "08:15"

# --- INTERFACE ---

st.title("📍 Unité Logement : Optimisation & Analyses")
tab_plan, tab_cal, tab_stats = st.tabs(["📝 Planning", "📅 Calendrier", "📊 Analyses"])

with st.sidebar:
    st.header("🌴 Congés")
    abs_agt = st.selectbox("Agent", AGENTS)
    c1, c2 = st.columns(2)
    with c1: d_deb = st.date_input("Du")
    with c2: d_fin = st.date_input("Au")
    if st.button("Valider Congé"):
        nouv = pd.DataFrame([{'Agent': abs_agt, 'Date_Debut': d_deb.strftime('%d/%m/%Y'), 'Date_Fin': d_fin.strftime('%d/%m/%Y')}])
        st.session_state.conges = pd.concat([st.session_state.conges, nouv], ignore_index=True)

    st.divider()
    up = st.file_uploader("Importer Excel", type=['xlsx'])
    if up and st.button("🚀 Planifier Avril"):
        df_ex = pd.read_excel(up).dropna(how='all').fillna('')
        df_ex.columns = df_ex.columns.str.strip()
        
        c_date = next((c for c in df_ex.columns if 'date' in c.lower()), 'Date')
        c_heure = next((c for c in df_ex.columns if 'heure' in c.lower()), 'Heure')
        c_bat = next((c for c in df_ex.columns if 'batiment' in c.lower() or 'bâtiment' in c.lower()), 'Batiment')
        
        temp = pd.DataFrame(columns=['Batiment', 'Date', 'Heure', 'Agent', 'Rue', 'Date_Sort'])
        
        for _, row in df_ex.sort_values(by=[c_date]).iterrows():
            dt = pd.to_datetime(row[c_date])
            ds = dt.strftime('%d/%m/%Y')
            
            agt = "À définir"
            for a in AGENTS:
                if est_disponible(a, ds):
                    agt = a
                    break
            
            h_val = str(row[c_heure]).strip()
            if h_val in ["", "nan", "00:00:00", "libre"]:
                h_final = f"{calculer_prochain_creneau(agt, ds, temp)} (*)"
            else:
                h_final = h_val[:5]
            
            temp = pd.concat([temp, pd.DataFrame([{
                'Batiment': row[c_bat], 'Date': ds, 'Heure': h_final, 'Agent': agt,
                'Rue': INFOS_BATIMENTS.get(row[c_bat], "Autre"), 'Date_Sort': dt
            }])], ignore_index=True)
        st.session_state.db = temp
        st.rerun()

    if st.button("🗑️ Reset"):
        st.session_state.db = pd.DataFrame(columns=['Batiment', 'Date', 'Heure', 'Agent', 'Rue', 'Date_Sort'])
        st.rerun()

# --- ONGLETS ---

with tab_plan:
    if not st.session_state.db.empty:
        df_v = st.session_state.db.sort_values(by=['Date_Sort', 'Heure'])
        st.table(df_v[['Date', 'Heure', 'Agent', 'Batiment', 'Rue']].style.apply(lambda r: [f'background-color: {COULEURS.get(r["Agent"])}']*len(r), axis=1))

with tab_cal:
    if not st.session_state.db.empty:
        jours = sorted(st.session_state.db['Date'].unique())
        sel_j = st.selectbox("Journée du :", jours)
        cols = st.columns(3)
        for i, a in enumerate(AGENTS):
            with cols[i]:
                st.markdown(f"<div style='text-align:center; background-color:{COULEURS[a]}; padding:10px; border-radius:5px; color:black;'><b>{a}</b></div>", unsafe_allow_html=True)
                data = st.session_state.db[(st.session_state.db['Date'] == sel_j) & (st.session_state.db['Agent'] == a)].sort_values(by='Heure')
                if data.empty: st.write("Libre")
                else:
                    for _, r in data.iterrows(): st.info(f"**{r['Heure']}**\n\n{r['Batiment']}")

with tab_stats:
    if not st.session_state.db.empty:
        st.subheader("📊 Analyses de Charge")
        c1, c2 = st.columns(2)
        total = len(st.session_state.db)
        c1.metric("Total Missions", total)
        c2.metric("Travail Terrain", f"{total}h00")
        
        st.divider()
        sel_j_an = st.selectbox("Calcul trajets pour le :", sorted(st.session_state.db['Date'].unique()), key="an")
        day_d = st.session_state.db[st.session_state.db['Date'] == sel_j_an]
        
        for a in AGENTS:
            agt_d = day_d[day_d['Agent'] == a].sort_values(by='Heure')
            if not agt_d.empty:
                st.write(f"#### 👩‍💻 {a}")
                itin = [BUREAU] + agt_d['Rue'].tolist() + [BUREAU]
                t_route = 0
                for k in range(len(itin)-1):
                    dep, arr = itin[k], itin[k+1]
                    dur = 5 if dep == arr else 15 # Oron étant à Lausanne, le trajet est standard
                    t_route += dur
                    st.write(f"🚗 {dep.split(',')[0]} ➡️ {arr.split(',')[0]} ({dur} min)")
                st.success(f"**Total :** {len(agt_d)}h Terrain | {t_route} min Route")
                st.divider()
