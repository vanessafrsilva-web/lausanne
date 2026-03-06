import streamlit as st
import pandas as pd
from datetime import datetime, timedelta

# --- CONFIGURATION ---
BUREAU = "Chemin Mont Paisible 18, 1011 Lausanne"
AGENTS = ["Celine", "Maria Claret", "Maria Elisabeth"]
INFOS_BATIMENTS = {
    'Bethusy A': 'Avenue de Béthusy 54, Lausanne', 'Bethusy B': 'Avenue de Béthusy 56, Lausanne',
    'Montolieu A': 'Isabelle-de-Montolieu 90, Lausanne', 'Montolieu B': 'Isabelle-de-Montolieu 92, Lausanne',
    'Tunnel': 'Rue du Tunnel 17, Lausanne', 'Oron': "Route d'Oron 77, 1073 Savigny"
}
COULEURS = {"Celine": "#d1e9ff", "Maria Claret": "#ffdae0", "Maria Elisabeth": "#d4f8d4"}

st.set_page_config(page_title="Unité Logement - Expert", layout="wide")

# Initialisation
if 'db' not in st.session_state:
    st.session_state.db = pd.DataFrame(columns=['Batiment', 'Date', 'Heure', 'Agent', 'Rue', 'Date_Sort'])
if 'conges' not in st.session_state:
    st.session_state.conges = pd.DataFrame(columns=['Agent', 'Date_Debut', 'Date_Fin'])

# --- FONCTIONS ---
def est_disponible(agent, date_str):
    if st.session_state.conges.empty: return True
    dt = pd.to_datetime(date_str, dayfirst=True)
    for _, c in st.session_state.conges[st.session_state.conges['Agent'] == agent].iterrows():
        if pd.to_datetime(c['Date_Debut'], dayfirst=True) <= dt <= pd.to_datetime(c['Date_Fin'], dayfirst=True): return False
    return True

def trouver_creneau(agent, date_str, temp_db):
    m_jour = temp_db[(temp_db['Date'] == date_str) & (temp_db['Agent'] == agent)]
    if m_jour.empty: return "08:15"
    derniere_h = str(m_jour.iloc[-1]['Heure']).replace("(*)", "").strip()
    try:
        # 1h entretien + 15 min route
        hf = datetime.strptime(derniere_h, "%H:%M") + timedelta(hours=1, minutes=15)
        if datetime.strptime("12:00", "%H:%M") <= hf < datetime.strptime("13:00", "%H:%M"): hf = datetime.strptime("13:00", "%H:%M")
        return hf.strftime("%H:%M")
    except: return "08:15"

# --- INTERFACE ---
st.title("📍 Unité Logement : Planning & Analyses")
t1, t2, t3 = st.tabs(["📝 Planning", "📅 Calendrier", "📊 Analyses"])

with st.sidebar:
    st.header("🌴 Gestion")
    abs_agt = st.selectbox("Agent", AGENTS)
    d1, d2 = st.date_input("Du"), st.date_input("Au")
    if st.button("Ajouter Congé"):
        st.session_state.conges = pd.concat([st.session_state.conges, pd.DataFrame([{'Agent': abs_agt, 'Date_Debut': d1.strftime('%d/%m/%Y'), 'Date_Fin': d2.strftime('%d/%m/%Y')}])], ignore_index=True)
    st.divider()
    up = st.file_uploader("Importer Excel", type=['xlsx'])
    if up and st.button("🚀 Planifier"):
        df_ex = pd.read_excel(up).dropna(how='all').fillna('')
        temp = pd.DataFrame(columns=['Batiment', 'Date', 'Heure', 'Agent', 'Rue', 'Date_Sort'])
        for _, row in df_ex.iterrows():
            ds = pd.to_datetime(row['Date']).strftime('%d/%m/%Y')
            # Attribution auto à Celine si dispo, sinon Maria
            presents = [a for a in AGENTS if est_disponible(a, ds)]
            agt = presents[0] if presents else "À définir"
            
            h_ex = str(row['Heure']).strip()
            if h_ex in ["", "nan", "00:00:00"]:
                h_final = f"{trouver_creneau(agt, ds, temp)} (*)"
            else:
                h_final = h_ex[:5]
                
            temp = pd.concat([temp, pd.DataFrame([{'Batiment': row['Batiment'], 'Date': ds, 'Heure': h_final, 'Agent': agt, 'Rue': INFOS_BATIMENTS.get(row['Batiment'], "Autre"), 'Date_Sort': pd.to_datetime(row['Date'])}])], ignore_index=True)
        st.session_state.db = temp; st.rerun()

# --- ONGLETS ---
with t1:
    if not st.session_state.db.empty:
        st.dataframe(st.session_state.db.sort_values(['Date_Sort', 'Heure'])[['Date', 'Heure', 'Agent', 'Batiment', 'Rue']], use_container_width=True)

with t2:
    if not st.session_state.db.empty:
        sel_j = st.selectbox("Choisir un jour", sorted(st.session_state.db['Date'].unique()))
        cols = st.columns(3)
        for i, a in enumerate(AGENTS):
            with cols[i]:
                st.markdown(f"<div style='text-align:center; background-color:{COULEURS[a]}; padding:10px; border-radius:5px; color:black;'><b>{a}</b></div>", unsafe_allow_html=True)
                m = st.session_state.db[(st.session_state.db['Date'] == sel_j) & (st.session_state.db['Agent'] == a)].sort_values('Heure')
                for _, r in m.iterrows(): st.warning(f"**{r['Heure']}**\n\n{r['Batiment']}")

with t3:
    if not st.session_state.db.empty:
        st.subheader("📊 Analyse des charges et trajets")
        sel_j_an = st.selectbox("Détail pour le :", sorted(st.session_state.db['Date'].unique()), key="an_day")
        day_d = st.session_state.db[st.session_state.db['Date'] == sel_j_an]
        for agent in AGENTS:
            agt_d = day_d[day_d['Agent'] == agent].sort_values('Heure')
            if not agt_d.empty:
                st.markdown(f"#### 👩‍💻 {agent}")
                itin = [BUREAU] + agt_d['Rue'].tolist() + [BUREAU]
                t_route = 0
                for k in range(len(itin)-1):
                    d, a = itin[k], itin[k+1]
                    dur = 25 if "Oron" in d or "Oron" in a else (5 if d == a else 15)
                    t_route += dur
                    st.write(f"🚗 {d.split(',')[0]} ➡️ {a.split(',')[0]} ({dur} min)")
                st.info(f"⏱️ **Terrain : {len(agt_d)}h00 | Route : {t_route} min**")
