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
    'Oron': "Route d'Oron 77, 1010 Lausanne"
}
COULEURS = {"Celine": "#d1e9ff", "Maria Claret": "#ffdae0", "Maria Elisabeth": "#d4f8d4"}

st.set_page_config(page_title="Unité Logement - Expert", layout="wide")

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
            d = pd.to_datetime(c['Date_Debut'], dayfirst=True)
            f = pd.to_datetime(c['Date_Fin'], dayfirst=True)
            if d <= dt <= f: return False
    except: pass
    return True

def trouver_meilleur_creneau(batiment, date_str, temp_db):
    rue_cible = INFOS_BATIMENTS.get(batiment, "Autre")
    m_jour = temp_db[temp_db['Date'] == date_str]
    pause_deb, pause_fin = datetime.strptime("12:00", "%H:%M"), datetime.strptime("13:00", "%H:%M")
    
    presents = [a for a in AGENTS if est_disponible(a, date_str)]
    if not presents: return "À définir", "08:15"
    
    for agt_name in AGENTS:
        if agt_name in presents:
            m_agt = m_jour[m_jour['Agent'] == agt_name]
            if m_agt.empty: return agt_name, "08:15"
            
            # Lecture propre de l'heure précédente pour ajouter la durée
            derniere_h = str(m_agt.iloc[-1]['Heure']).strip()
            try:
                # 1h entretien + 15 min trajet moyen
                hf = datetime.strptime(derniere_h, "%H:%M") + timedelta(hours=1, minutes=15)
                # Gestion pause déjeuner
                if hf > pause_deb and hf < pause_fin: hf = pause_fin
                if hf < datetime.strptime("17:30", "%H:%M"):
                    return agt_name, hf.strftime("%H:%M")
            except: pass
    return presents[0], "08:15"

# --- INTERFACE ---
st.title("📍 Unité Logement : Gestion des Attributions")
t1, t2, t3 = st.tabs(["📝 Planning", "📅 Calendrier", "📊 Analyses de Charge"])

with st.sidebar:
    st.header("🌴 Congés")
    abs_agt = st.selectbox("Agent", AGENTS)
    d1, d2 = st.date_input("Du"), st.date_input("Au")
    if st.button("Valider Congé"):
        st.session_state.conges = pd.concat([st.session_state.conges, pd.DataFrame([{'Agent': abs_agt, 'Date_Debut': d1.strftime('%d/%m/%Y'), 'Date_Fin': d2.strftime('%d/%m/%Y')}])], ignore_index=True)
    st.divider()
    up = st.file_uploader("Importer Excel", type=['xlsx'])
    if up and st.button("🚀 Planifier Avril"):
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
                f_hr = hr
            else:
                f_hr = h_ex
                # On cherche l'agent dispo même si l'heure est imposée
                agt, _ = trouver_meilleur_creneau(row['Batiment'], ds, temp)
            
            temp = pd.concat([temp, pd.DataFrame([{
                'Batiment': row['Batiment'], 'Date': ds, 'Heure': f_hr, 'Agent': agt, 
                'Rue': INFOS_BATIMENTS.get(row['Batiment'], "Autre"), 'Type': "Import", 'Date_Sort': dt
            }])], ignore_index=True)
        st.session_state.db = temp
        st.rerun()

with t1:
    if not st.session_state.db.empty:
        df_show = st.session_state.db.sort_values(by=['Date_Sort', 'Heure'])
        st.table(df_show[['Date', 'Heure', 'Agent', 'Batiment', 'Rue']].style.apply(lambda r: [f'background-color: {COULEURS.get(r["Agent"])}']*len(r), axis=1))

with t3:
    if not st.session_state.db.empty:
        st.subheader("📊 Rapport d'activité (Entretien 1h + Route)")
        sel_j_stats = st.selectbox("Détail des trajets pour le :", sorted(st.session_state.db['Date'].unique()))
        day_data = st.session_state.db[st.session_state.db['Date'] == sel_j_stats]
        
        for agent in AGENTS:
            agt_data = day_data[day_data['Agent'] == agent].sort_values(by='Heure')
            if not agt_data.empty:
                st.markdown(f"#### 👩‍💻 {agent}")
                itin = [BUREAU] + agt_data['Rue'].tolist() + [BUREAU]
                t_route = 0
                for k in range(len(itin)-1):
                    d, a = itin[k], itin[k+1]
                    duree = 25 if "Oron" in d or "Oron" in a else (5 if d == a else 15)
                    t_route += duree
                    st.write(f"🚗 {d.split(',')[0]} ➡️ {a.split(',')[0]} ({duree} min)")
                st.write(f"⏱️ **Total Terrain : {len(agt_data)}h00 | Total Route : {t_route} min**")
                st.divider()
