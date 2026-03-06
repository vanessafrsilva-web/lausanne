import streamlit as st
import pandas as pd
from datetime import datetime, timedelta

# --- CONFIGURATION ---
BUREAU = "Chemin Mont Paisible 18, 1011 Lausanne"
AGENTS = ["Celine", "Maria Claret", "Maria Elisabeth"]
INFOS_BATIMENTS = {
    'Bethusy A': 'Avenue de Béthusy 54, Lausanne',
    'Bethusy B': 'Avenue de Béthusy 56, Lausanne',
    'Montolieu A': 'Isabelle-de-Montolieu 90, Lausanne',
    'Montolieu B': 'Isabelle-de-Montolieu 92, Lausanne',
    'Tunnel': 'Rue du Tunnel 17, Lausanne',
    'Oron': "Route d'Oron 77, 1073 Savigny"
}
COULEURS = {"Celine": "#d1e9ff", "Maria Claret": "#ffdae0", "Maria Elisabeth": "#d4f8d4", "À définir": "#eeeeee"}

st.set_page_config(page_title="Unité Logement - Expert", layout="wide")

if 'db' not in st.session_state:
    st.session_state.db = pd.DataFrame(columns=['Batiment', 'Date', 'Heure', 'Agent', 'Rue', 'Type', 'Date_Sort'])
if 'conges' not in st.session_state:
    st.session_state.conges = pd.DataFrame(columns=['Agent', 'Date_Debut', 'Date_Fin'])

# --- FONCTIONS ---
def est_disponible(agent, date_str):
    if st.session_state.conges.empty: return True
    try:
        dt = pd.to_datetime(date_str, dayfirst=True)
        for _, c in st.session_state.conges[st.session_state.conges['Agent'] == agent].iterrows():
            d = pd.to_datetime(c['Date_Debut'], dayfirst=True)
            f = pd.to_datetime(c['Date_Fin'], dayfirst=True)
            if d <= dt <= f: return False
    except: pass
    return True

def trouver_meilleur_creneau(batiment, date_str, temp_db):
    rue_cible = INFOS_BATIMENTS.get(batiment, "Autre")
    m_jour = temp_db[temp_db['Date'] == date_str]
    pause_deb, pause_fin = datetime.strptime("12:00", "%H:%M"), datetime.strptime("13:00", "%H:%M")
    
    def ajuster(h): return pause_fin if h > pause_deb and h < pause_fin else h
    
    presents = [a for a in AGENTS if est_disponible(a, date_str)]
    if not presents: return "À définir", "08:15"
    
    for agt_name in AGENTS:
        if agt_name in presents:
            m_agt = m_jour[m_jour['Agent'] == agt_name]
            if m_agt.empty: return agt_name, "08:15"
            
            # Correction du bug : on extrait seulement les 5 derniers caractères (HH:MM)
            derniere_heure_str = str(m_agt.iloc[-1]['Heure'])[-5:] 
            try:
                hf = datetime.strptime(derniere_heure_str, "%H:%M") + timedelta(hours=1, minutes=20)
                hf = ajuster(hf)
                if hf < datetime.strptime("17:30", "%H:%M"):
                    return agt_name, hf.strftime("%H:%M")
            except: pass
    return presents[0], "08:15"

# --- INTERFACE ---
st.title("📍 Unité Logement : Optimisation & Analyses")
t1, t2, t3 = st.tabs(["📝 Planning", "📅 Calendrier", "📊 Analyses"])

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
        col_h = next((c for c in df_ex.columns if 'heure' in c.lower()), 'Heure')
        
        temp = pd.DataFrame(columns=['Batiment', 'Date', 'Heure', 'Agent', 'Rue', 'Type', 'Date_Sort'])
        for _, row in df_ex.sort_values(by=[col_d, 'Batiment']).iterrows():
            dt = pd.to_datetime(row[col_d]); ds = dt.strftime('%d/%m/%Y')
            h_ex = str(row[col_h]).strip()
            
            if h_ex == "" or h_ex.lower() in ["nan", "libre"]:
                agt, hr = trouver_meilleur_creneau(row['Batiment'], ds, temp)
                f_hr = f"🤖 {hr}" # Version simplifiée pour éviter les bugs de caractères
            else:
                f_hr = h_ex
                agt, _ = trouver_meilleur_creneau(row['Batiment'], ds, temp)
            
            temp = pd.concat([temp, pd.DataFrame([{
                'Batiment': row['Batiment'], 'Date': ds, 'Heure': f_hr, 'Agent': agt, 
                'Rue': INFOS_BATIMENTS.get(row['Batiment'], "Autre"), 'Type': "Import", 'Date_Sort': dt
            }])], ignore_index=True)
        st.session_state.db = temp
        st.rerun()

    if st.button("🗑️ Reset"):
        st.session_state.db = pd.DataFrame(columns=['Batiment', 'Date', 'Heure', 'Agent', 'Rue', 'Type', 'Date_Sort'])
        st.rerun()

# --- CONTENU ---
with t1:
    if not st.session_state.db.empty:
        df_show = st.session_state.db.sort_values(by=['Date_Sort', 'Heure'])
        st.table(df_show[['Date', 'Heure', 'Agent', 'Batiment', 'Rue']].style.apply(lambda r: [f'background-color: {COULEURS.get(r["Agent"])}']*len(r), axis=1))

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
        st.metric("Total Dossiers", len(st.session_state.db))
        st.bar_chart(st.session_state.db['Agent'].value_counts())
