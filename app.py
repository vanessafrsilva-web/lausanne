import streamlit as st
import pandas as pd
from datetime import datetime, timedelta

# --- CONFIGURATION FIXE ---
BUREAU = "Chemin Mont Paisible 18, 1011 Lausanne"
AGENTS = ["Celine", "Maria Claret", "Maria Elisabeth"]

INFOS_BATIMENTS = {
    'Bethusy A': 'Avenue de Béthusy 54, Lausanne',
    'Bethusy B': 'Avenue de Béthusy 56, Lausanne',
    'Montolieu A': 'Isabelle-de-Montolieu 90, Lausanne',
    'Montolieu B': 'Isabelle-de-Montolieu 92, Lausanne',
    'Tunnel': 'Rue du Tunnel 17, Lausanne',
    'Oron': "Route d'Oron 77, 1010 Lausanne"
}

COULEURS = {"Celine": "#d1e9ff", "Maria Claret": "#ffdae0", "Maria Elisabeth": "#d4f8d4"}

st.set_page_config(page_title="Unité Logement - Expert", layout="wide")

if 'db' not in st.session_state:
    st.session_state.db = pd.DataFrame(columns=['Batiment', 'Date', 'Heure', 'Agent', 'Rue', 'Date_Sort'])
if 'conges' not in st.session_state:
    st.session_state.conges = pd.DataFrame(columns=['Agent', 'Date_Debut', 'Date_Fin'])

# --- FONCTIONS LOGIQUES ---

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
    
    # Lecture directe de l'heure (plus de robot, donc pas de bug)
    derniere_h_str = str(m_jour.iloc[-1]['Heure']).strip()
    try:
        heure_obj = datetime.strptime(derniere_h_str, "%H:%M")
        # 1h entretien + 15 min trajet
        prochaine_h = heure_obj + timedelta(hours=1, minutes=15)
        
        # Gestion pause 12h-13h
        pause_deb = datetime.strptime("12:00", "%H:%M")
        pause_fin = datetime.strptime("13:00", "%H:%M")
        if prochaine_h >= pause_deb and prochaine_h < pause_fin:
            prochaine_h = pause_fin
            
        return prochaine_h.strftime("%H:%M")
    except:
        return "08:15"

# --- INTERFACE ---
st.title("📍 Unité Logement : Planification Optimisée")
t1, t2, t3 = st.tabs(["📝 Planning", "📅 Calendrier", "📊 Analyses"])

with st.sidebar:
    st.header("🌴 Gestion")
    abs_agt = st.selectbox("Agent", AGENTS)
    d1, d2 = st.date_input("Du"), st.date_input("Au")
    if st.button("Valider Congé"):
        st.session_state.conges = pd.concat([st.session_state.conges, pd.DataFrame([{'Agent': abs_agt, 'Date_Debut': d1.strftime('%d/%m/%Y'), 'Date_Fin': d2.strftime('%d/%m/%Y')}])], ignore_index=True)
    
    st.divider()
    up = st.file_uploader("Importer Excel", type=['xlsx'])
    if up and st.button("🚀 Lancer la Planification"):
        df_ex = pd.read_excel(up).dropna(how='all').fillna('')
        df_ex.columns = df_ex.columns.str.strip()
        
        col_d = next((c for c in df_ex.columns if 'date' in c.lower()), 'Date')
        col_h = next((c for c in df_ex.columns if 'heure' in c.lower()), 'Heure')
        col_b = next((c for c in df_ex.columns if 'bat' in c.lower()), 'Batiment')

        temp = pd.DataFrame(columns=['Batiment', 'Date', 'Heure', 'Agent', 'Rue', 'Date_Sort'])
        
        for _, row in df_ex.sort_values(by=[col_d]).iterrows():
            ds = pd.to_datetime(row[col_d]).strftime('%d/%m/%Y')
            
            # Équilibrage : on prend l'agent dispo qui a le moins de dossiers
            presents = [a for a in AGENTS if est_disponible(a, ds)]
            if presents:
                charges = {a: len(temp[(temp['Date'] == ds) & (temp['Agent'] == a)]) for a in presents}
                agt = min(charges, key=charges.get)
            else:
                agt = "À définir"
            
            h_val = str(row[col_h]).strip()
            if h_val in ["", "nan", "00:00:00", "libre"]:
                h_final = calculer_prochain_creneau(agt, ds, temp)
            else:
                h_final = h_val[:5]
            
            temp = pd.concat([temp, pd.DataFrame([{
                'Batiment': row[col_b], 'Date': ds, 'Heure': h_final, 'Agent': agt,
                'Rue': INFOS_BATIMENTS.get(row[col_b], "Autre"), 'Date_Sort': pd.to_datetime(row[col_d])
            }])], ignore_index=True)
        st.session_state.db = temp
        st.rerun()

# --- ONGLETS ---
with t1:
    if not st.session_state.db.empty:
        df_v = st.session_state.db.sort_values(by=['Date_Sort', 'Heure'])
        st.table(df_v[['Date', 'Heure', 'Agent', 'Batiment', 'Rue']].style.apply(lambda r: [f'background-color: {COULEURS.get(r["Agent"])}']*len(r), axis=1))

with t2:
    if not st.session_state.db.empty:
        sel_j = st.selectbox("Jour", sorted(st.session_state.db['Date'].unique()))
        cols = st.columns(3)
        for i, a in enumerate(AGENTS):
            with cols[i]:
                st.markdown(f"<div style='text-align:center; background-color:{COULEURS[a]}; padding:10px; border-radius:5px; color:black;'><b>{a}</b></div>", unsafe_allow_html=True)
                m = st.session_state.db[(st.session_state.db['Date'] == sel_j) & (st.session_state.db['Agent'] == a)].sort_values(by='Heure')
                for _, r in m.iterrows(): st.info(f"**{r['Heure']}**\n\n{r['Batiment']}")

with t3:
    if not st.session_state.db.empty:
        st.subheader("📊 Analyses de Charge")
        total = len(st.session_state.db)
        st.write(f"**Total missions : {total} | Temps terrain : {total}h00**")
        st.bar_chart(st.session_state.db['Agent'].value_counts())
        
        sel_j_stats = st.selectbox("Détail trajets du :", sorted(st.session_state.db['Date'].unique()), key="stats")
        day_d = st.session_state.db[st.session_state.db['Date'] == sel_j_stats]
        for a in AGENTS:
            agt_d = day_d[day_d['Agent'] == a].sort_values(by='Heure')
            if not agt_d.empty:
                itin = [BUREAU] + agt_d['Rue'].tolist() + [BUREAU]
                t_route = sum([15 if itin[k] != itin[k+1] else 5 for k in range(len(itin)-1)])
                st.write(f"👩‍💻 **{a}** : {len(agt_d)}h Terrain | {t_route} min Route")
