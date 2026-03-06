import streamlit as st
import pandas as pd
from datetime import datetime, timedelta

# --- CONFIGURATION ---
BUREAU = "Chemin Mont Paisible 18, 1011 Lausanne"
AGENTS = ["Celine", "Maria Claret", "Maria Elisabeth"]
INFOS_BATIMENTS = {
    'Bethusy A': 'Avenue de Béthusy 54, Lausanne', 'Bethusy B': 'Avenue de Béthusy 56, Lausanne',
    'Montolieu A': 'Isabelle-de-Montolieu 90, Lausanne', 'Montolieu B': 'Isabelle-de-Montolieu 92, Lausanne',
    'Tunnel': 'Rue du Tunnel 17, Lausanne', 'Oron': "Route d'Oron 77, 1010 Lausanne"
}
COULEURS = {"Celine": "#d1e9ff", "Maria Claret": "#ffdae0", "Maria Elisabeth": "#d4f8d4", "À définir": "#eeeeee"}

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
            if pd.to_datetime(c['Date_Debut'], dayfirst=True) <= dt_cible <= pd.to_datetime(c['Date_Fin'], dayfirst=True): return False
    except: pass
    return True

def calculer_heure_fin(heure_debut_str):
    """Calcule la fin de mission : 1h entretien + 15min trajet."""
    h_obj = datetime.strptime(heure_debut_str.replace("(*)", "").strip(), "%H:%M")
    h_fin = h_obj + timedelta(hours=1, minutes=15)
    # Saut de la pause déjeuner
    if h_fin > datetime.strptime("12:00", "%H:%M") and h_obj < datetime.strptime("13:00", "%H:%M"):
        h_obj = datetime.strptime("13:00", "%H:%M")
        h_fin = h_obj + timedelta(hours=1, minutes=15)
    return h_obj.strftime("%H:%M"), h_fin

def trouver_agent_et_heure(date_str, temp_db):
    """Cherche l'agent disponible avec la charge la plus légère et respectant 08h-17h."""
    # On trie les agents par nombre de dossiers déjà assignés aujourd'hui
    agents_dispos = [a for a in AGENTS if est_disponible(a, date_str)]
    
    # On stocke les scores de charge
    charges = {a: len(temp_db[(temp_db['Date'] == date_str) & (temp_db['Agent'] == a)]) for a in agents_dispos}
    # Trier les agents par celui qui a le moins de travail
    agents_tries = sorted(charges, key=charges.get)

    for agt in agents_tries:
        m_jour = temp_db[(temp_db['Date'] == date_str) & (temp_db['Agent'] == agt)]
        if m_jour.empty:
            return agt, "08:15"
        
        derniere_h = m_jour.iloc[-1]['Heure']
        h_debut_propose, h_fin_prevue = calculer_heure_fin(derniere_h)
        
        # Vérification de la limite de 17h30
        if h_fin_prevue <= datetime.strptime("17:35", "%H:%M"):
            return agt, h_debut_propose
            
    return "À définir", "08:15"

# --- INTERFACE ---
st.title("📍 Unité Logement : Planification Intelligente")
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
        temp = pd.DataFrame(columns=['Batiment', 'Date', 'Heure', 'Agent', 'Rue', 'Date_Sort'])
        
        for _, row in df_ex.sort_values(by=['Date']).iterrows():
            ds = pd.to_datetime(row['Date']).strftime('%d/%m/%Y')
            h_ex = str(row['Heure']).strip()
            
            if h_ex in ["", "nan", "00:00:00", "libre"]:
                agt, h_final = trouver_agent_et_heure(ds, temp)
                h_final = f"{h_final} (*)"
            else:
                h_final = h_ex[:5]
                # Pour les heures imposées, on prend l'agent le moins chargé
                agents_libres = [a for a in AGENTS if est_disponible(a, ds)]
                if agents_libres:
                    charges = {a: len(temp[(temp['Date'] == ds) & (temp['Agent'] == a)]) for a in agents_libres}
                    agt = min(charges, key=charges.get)
                else: agt = "À définir"

            temp = pd.concat([temp, pd.DataFrame([{
                'Batiment': row['Batiment'], 'Date': ds, 'Heure': h_final, 'Agent': agt,
                'Rue': INFOS_BATIMENTS.get(row['Batiment'], "Autre"), 'Date_Sort': pd.to_datetime(row['Date'])
            }])], ignore_index=True)
        st.session_state.db = temp
        st.rerun()

# --- AFFICHAGE ---
with t1:
    if not st.session_state.db.empty:
        st.table(st.session_state.db.sort_values(['Date_Sort', 'Heure'])[['Date', 'Heure', 'Agent', 'Batiment', 'Rue']].style.apply(lambda r: [f'background-color: {COULEURS.get(r["Agent"])}']*len(r), axis=1))

with t2:
    if not st.session_state.db.empty:
        sel_j = st.selectbox("Jour", sorted(st.session_state.db['Date'].unique()))
        cols = st.columns(3)
        for i, a in enumerate(AGENTS):
            with cols[i]:
                st.markdown(f"<div style='text-align:center; background-color:{COULEURS[a]}; padding:10px; border-radius:5px;'><b>{a}</b></div>", unsafe_allow_html=True)
                m = st.session_state.db[(st.session_state.db['Date'] == sel_j) & (st.session_state.db['Agent'] == a)].sort_values('Heure')
                for _, r in m.iterrows(): st.info(f"**{r['Heure']}**\n{r['Batiment']}")

with t3:
    if not st.session_state.db.empty:
        st.bar_chart(st.session_state.db['Agent'].value_counts())
        sel_j_stats = st.selectbox("Détail du :", sorted(st.session_state.db['Date'].unique()), key="st")
        for a in AGENTS:
            d_agt = st.session_state.db[(st.session_state.db['Date'] == sel_j_stats) & (st.session_state.db['Agent'] == a)].sort_values('Heure')
            if not d_agt.empty:
                itin = [BUREAU] + d_agt['Rue'].tolist() + [BUREAU]
                t_route = sum([15 if itin[k] != itin[k+1] else 5 for k in range(len(itin)-1)])
                st.write(f"👩‍💻 **{a}** : {len(d_agt)}h Terrain | {t_route} min de route")
