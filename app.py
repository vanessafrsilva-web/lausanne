import streamlit as st
import pandas as pd
from datetime import datetime, timedelta

# --- CONFIGURATION ---
AGENTS = ["Maria Claret", "Celine", "Maria Elisabeth"]
ZONES = {
    'Bethusy A': 'Chailly', 'Bethusy B': 'Chailly', 'Bethusy C': 'Chailly',
    'Montolieu A': 'Montolieu', 'Montolieu B': 'Montolieu',
    'Tunnel': 'Riponne', 'Oron': 'Oron', 'Riponne': 'Riponne'
}
COULEURS = {"Maria Claret": "#ffdae0", "Celine": "#d1e9ff", "Maria Elisabeth": "#d4f8d4"}

st.set_page_config(page_title="IA Planning - Import Auto", layout="wide")

if 'db' not in st.session_state:
    st.session_state.db = pd.DataFrame(columns=['Batiment', 'Date', 'Heure', 'Agent', 'Zone', 'Type'])

# --- MOTEUR DE SUGGESTION (Logique partagée) ---
def obtenir_suggestion(batiment, date_str, current_db):
    zone_cible = ZONES.get(batiment, "Autre")
    missions_jour = current_db[current_db['Date'] == date_str]
    
    # 1. Si quelqu'un est déjà dans la zone, on l'ajoute à son planning
    meme_zone = missions_jour[missions_jour['Zone'] == zone_cible]
    if not meme_zone.empty:
        agent = meme_zone.iloc[-1]['Agent']
        h_prev = datetime.strptime(meme_zone.iloc[-1]['Heure'], "%H:%M")
        heure = (h_prev + timedelta(hours=1, minutes=30)).strftime("%H:%M") # 1h30 entre RDV
        return agent, heure
    
    # 2. Sinon, on prend l'agent le moins chargé
    charge = missions_jour['Agent'].value_counts()
    for agt in AGENTS:
        if agt not in charge: return agt, "08:15"
    return charge.idxmin(), "10:00"

# --- INTERFACE ---
st.title("🚀 Planification Auto : Import & Optimisation")

with st.sidebar:
    st.header("📥 Importation Intelligente")
    uploaded = st.file_uploader("Fichier Excel (30 dossiers)", type=['xlsx'])
    
    if uploaded and st.button("🚀 Planifier tout le mois"):
        df_ex = pd.read_excel(uploaded).dropna(how='all').fillna('')
        df_ex.columns = df_ex.columns.str.strip()
        col_d = next((c for c in df_ex.columns if 'date' in c.lower()), 'Date')
        
        # TRI STRATÉGIQUE AVANT ATTRIBUTION : Date + Zone (pour regrouper les trajets)
        df_ex['Date_Obj'] = pd.to_datetime(df_ex[col_d])
        df_ex = df_ex.sort_values(['Date_Obj', 'Batiment'])
        
        for _, row in df_ex.iterrows():
            date_s = row['Date_Obj'].strftime('%d/%m/%Y')
            bat = row['Batiment']
            agent, heure = obtenir_suggestion(bat, date_s, st.session_state.db)
            
            nouvelle_ligne = {
                'Batiment': bat, 'Date': date_s, 'Heure': heure, 
                'Agent': agent, 'Zone': ZONES.get(bat, "Autre"), 'Type': "Attribution"
            }
            st.session_state.db = pd.concat([st.session_state.db, pd.DataFrame([nouvelle_ligne])], ignore_index=True)
        st.success("Planning automatisé avec succès !")

# --- AFFICHAGE ---
if not st.session_state.db.empty:
    f_date = st.selectbox("Voir le planning du :", sorted(st.session_state.db['Date'].unique()))
    df_view = st.session_state.db[st.session_state.db['Date'] == f_date].sort_values(by=['Heure'])

    def apply_color(row):
        return [f'background-color: {COULEURS.get(row["Agent"], "#eeeeee")}'] * len(row)

    st.table(df_view.style.apply(apply_color, axis=1))
