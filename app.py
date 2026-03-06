import streamlit as st
import pandas as pd
from datetime import datetime, timedelta

# --- CONFIGURATION FIXE ---
BUREAU = "Mon Paisible 18, 1007 Lausanne"
AGENTS = ["Celine", "Maria Claret", "Maria Elisabeth"]

INFOS_BATIMENTS = {
    'Bethusy A': 'Avenue de Béthusy 54',
    'Bethusy B': 'Avenue de Béthusy 56',
    'Montolieu A': 'Isabelle-de-Montolieu 90',
    'Montolieu B': 'Isabelle-de-Montolieu 92',
    'Tunnel': 'Rue du Tunnel 17',
    'Oron': "Route d'Oron 77"
}

COULEURS = {
    "Celine": "#d1e9ff",
    "Maria Claret": "#ffdae0",
    "Maria Elisabeth": "#d4f8d4",
    "À définir": "#eeeeee"
}

st.set_page_config(page_title="Unité Logement", layout="wide")

if 'db' not in st.session_state:
    st.session_state.db = pd.DataFrame(columns=['Batiment', 'Date', 'Heure', 'Agent', 'Rue', 'Type', 'Date_Sort'])

# --- MOTEUR D'ATTRIBUTION PRIORITÉ CÉLINE + PAUSE MIDI ---
def trouver_meilleur_creneau(batiment, date_str, temp_db):
    rue_cible = INFOS_BATIMENTS.get(batiment, "Autre")
    missions_jour = temp_db[temp_db['Date'] == date_str]
    pause_debut = datetime.strptime("12:00", "%H:%M")
    pause_fin = datetime.strptime("13:00", "%H:%M")
    
    def ajuster_pause(heure_fin_mission):
        if heure_fin_mission > pause_debut and heure_fin_mission < pause_fin:
            return pause_fin
        return heure_fin_mission

    if missions_jour.empty:
        return "Celine", "08:15"
    
    celine_meme_rue = missions_jour[(missions_jour['Agent'] == "Celine") & (missions_jour['Rue'] == rue_cible)]
    if not celine_meme_rue.empty:
        dernier = celine_meme_rue.sort_values(by='Heure').iloc[-1]
        h_fin = datetime.strptime(dernier['Heure'], "%H:%M") + timedelta(hours=1, minutes=20)
        h_fin = ajuster_pause(h_fin)
        return "Celine", h_fin.strftime("%H:%M")

    missions_celine = missions_jour[missions_jour['Agent'] == "Celine"]
    if not missions_celine.empty:
        h_fin_celine = datetime.strptime(missions_celine.sort_values(by='Heure').iloc[-1]['Heure'], "%H:%M") + timedelta(hours=1, minutes=45)
        h_fin_celine = ajuster_pause(h_fin_celine)
        if h_fin_celine < datetime.strptime("15:30", "%H:%M"):
            return "Celine", h_fin_celine.strftime("%H:%M")
    
    for agent_surplus in ["Maria Claret", "Maria Elisabeth"]:
        missions_agt = missions_jour[missions_jour['Agent'] == agent_surplus]
        if missions_agt.empty:
            return agent_surplus, "08:15"
        else:
            h_fin_agt = datetime.strptime(missions_agt.sort_values(by='Heure').iloc[-1]['Heure'], "%H:%M") + timedelta(hours=1, minutes=45)
            h_fin_agt = ajuster_pause(h_fin_agt)
            if h_fin_agt < datetime.strptime("16:00", "%H:%M"):
                return agent_surplus, h_fin_agt.strftime("%H:%M")

    return "Celine", "Surcharge"

# TITRE FIXE
st.title("📍 Unité Logement : Optimisation Attibutions")

# --- BARRE LATÉRALE ---
with st.sidebar:
    st.header("📥 Importation Massive")
    uploaded = st.file_uploader("Fichier Excel", type=['xlsx'])
    
    if uploaded and st.button("🚀 Planifier Avril"):
        df_ex = pd.read_excel(uploaded).dropna(how='all').fillna('')
        df_ex.columns = df_ex.columns.str.strip()
        col_d = next((c for c in df_ex.columns if 'date' in c.lower()), 'Date')
        
        temp_db = st.session_state.db.copy()
        for _, row in df_ex.sort_values(by=[col_d, 'Batiment']).iterrows():
            date_dt = pd.to_datetime(row[col_d])
            d_str = date_dt.strftime('%d/%m/%Y')
            agt, hr = trouver_meilleur_creneau(row['Batiment'], d_str, temp_db)
            
            temp_db = pd.concat([temp_db, pd.DataFrame([{
                'Batiment': row['Batiment'], 'Date': d_str, 'Heure': hr, 
                'Agent': agt, 'Rue': INFOS_BATIMENTS.get(row['Batiment'], "Autre"), 
                'Type': "Import", 'Date_Sort': date_dt
            }])], ignore_index=True)
        st.session_state.db = temp_db
        st.success("Planning optimisé !")

    st.divider()
    st.header("📊 Performance")
    if not st.session_state.db.empty:
        total = len(st.session_state.db)
        groupements = st.session_state.db.groupby(['Date', 'Rue']).size()
        score = (len(groupements[groupements > 1]) / total * 100) if total > 0 else 0
        st.metric("Taux d'Occupation", f"{int(score)}%")
        
        if st.button("🗑️ Reset Planning"):
            st.session_state.db = pd.DataFrame(columns=['Batiment', 'Date', 'Heure', 'Agent', 'Rue', 'Type', 'Date_Sort'])
            st.rerun()

# --- FORMULAIRE MANUEL ---
with st.expander("➕ AJOUTER / MODIFIER UN DOSSIER"):
    c1, c2 = st.columns(2)
    with c1:
        n_bat = st.selectbox("Bâtiment", list(INFOS_BATIMENTS.keys()))
        n_date = st.date_input("Date")
        date_str = n_date.strftime('%d/%m/%Y')
    with c2:
        s_agt, s_hr = trouver_meilleur_creneau(n_bat, date_str, st.session_state.db)
        f_agt = st.selectbox("Agent recommandé", AGENTS, index=AGENTS.index(s_agt))
        f_hr = st.text_input("Heure", value=s_hr)
    if st.button("Enregistrer"):
        l = {'Batiment': n_bat, 'Date': date_str, 'Heure': f_hr, 'Agent': f_agt, 
             'Rue': INFOS_BATIMENTS.get(n_bat, "Autre"), 'Type': "Manuel", 'Date_Sort': pd.to_datetime(n_date)}
        st.session_state.db = pd.concat([st.session_state.db, pd.DataFrame([l])], ignore_index=True)
        st.rerun()

# --- SYSTÈME DE FILTRES DYNAMIQUES ---
st.divider()
if not st.session_state.db.empty:
    st.subheader("🔍 Filtres d'affichage")
    f1, f2, f3 = st.columns(3)
    
    with f1:
        list_dates = ["Tout"] + sorted(st.session_state.db['Date'].unique().tolist())
        sel_date = st.selectbox("Filtrer par Date :", list_dates)
    with f2:
        list_agents = ["Tout"] + AGENTS
        sel_agent = st.selectbox("Filtrer par Collaboratrice :", list_agents)
    with f3:
        list_bats = ["Tout"] + sorted(st.session_state.db['Batiment'].unique().tolist())
        sel_bat = st.selectbox("Filtrer par Bâtiment :", list_bats)

    # Application des filtres
    df_v = st.session_state.db.copy()
    if sel_date != "Tout":
        df_v = df_v[df_v['Date'] == sel_date]
    if sel_agent != "Tout":
        df_v = df_v[df_v['Agent'] == sel_agent]
    if sel_bat != "Tout":
        df_v = df_v[df_v['Batiment'] == sel_bat]

    # Tri final (Date, Heure, Agent)
    df_v = df_v.sort_values(by=['Date_Sort', 'Heure', 'Agent'])

    # Style
    def style_agent(row):
        return [f'background-color: {COULEURS.get(row["Agent"])}'] * len(row)

    st.write(f"**Nombre d'entrées affichées :** {len(df_v)}")
    st.table(df_v[['Date', 'Heure', 'Agent', 'Batiment', 'Rue']].style.apply(style_agent, axis=1))
