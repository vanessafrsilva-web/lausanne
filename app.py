import streamlit as st
import pandas as pd
from datetime import datetime, timedelta

# --- CONFIGURATION MISE À JOUR ---
BUREAU = "Mon Paisible 18, 1007 Lausanne"
AGENTS = ["Celine", "Maria Claret", "Maria Elisabeth"] # Celine en tête de liste

INFOS_BATIMENTS = {
    'Bethusy A': 'Avenue de Béthusy 54',
    'Bethusy B': 'Avenue de Béthusy 56',
    'Montolieu A': 'Isabelle-de-Montolieu 90',
    'Montolieu B': 'Isabelle-de-Montolieu 92',
    'Tunnel': 'Rue du Tunnel 17',
    'Oron': "Route d'Oron 77"
}

COULEURS = {
    "Celine": "#d1e9ff",         # Bleu (Prioritaire)
    "Maria Claret": "#ffdae0",   # Rose
    "Maria Elisabeth": "#d4f8d4", # Vert
    "À définir": "#eeeeee"
}

st.set_page_config(page_title="Planning Logement : Optimisation Attibutions", layout="wide")

if 'db' not in st.session_state:
    st.session_state.db = pd.DataFrame(columns=['Batiment', 'Date', 'Heure', 'Agent', 'Rue', 'Type'])

# --- MOTEUR D'ATTRIBUTION PRIORITÉ CÉLINE ---
def trouver_meilleur_creneau(batiment, date_str, temp_db):
    rue_cible = INFOS_BATIMENTS.get(batiment, "Autre")
    missions_jour = temp_db[temp_db['Date'] == date_str]
    
    # 1. Si la journée est vide -> On commence toujours par Celine
    if missions_jour.empty:
        return "Celine", "08:15"
    
    # 2. On vérifie si Celine est déjà dans cette rue
    celine_meme_rue = missions_jour[(missions_jour['Agent'] == "Celine") & (missions_jour['Rue'] == rue_cible)]
    if not celine_meme_rue.empty:
        dernier = celine_meme_rue.sort_values(by='Heure').iloc[-1]
        h_fin = datetime.strptime(dernier['Heure'], "%H:%M") + timedelta(hours=1, minutes=20)
        return "Celine", h_fin.strftime("%H:%M")

    # 3. Si Celine n'est pas dans cette rue, on regarde son heure de fin
    missions_celine = missions_jour[missions_jour['Agent'] == "Celine"]
    if not missions_celine.empty:
        h_fin_celine = datetime.strptime(missions_celine.sort_values(by='Heure').iloc[-1]['Heure'], "%H:%M") + timedelta(hours=1, minutes=45)
        # Si Céline finit avant 15h, on continue avec elle
        if h_fin_celine < datetime.strptime("15:00", "%H:%M"):
            return "Celine", h_fin_celine.strftime("%H:%M")
    
    # 4. Si Céline est surchargée (> 15h) ou occupée ailleurs, on passe au surplus (les Maria)
    for agent_surplus in ["Maria Claret", "Maria Elisabeth"]:
        missions_agt = missions_jour[missions_jour['Agent'] == agent_surplus]
        if missions_agt.empty:
            return agent_surplus, "08:15"
        else:
            h_fin_agt = datetime.strptime(missions_agt.sort_values(by='Heure').iloc[-1]['Heure'], "%H:%M") + timedelta(hours=1, minutes=45)
            if h_fin_agt < datetime.strptime("15:30", "%H:%M"):
                return agent_surplus, h_fin_agt.strftime("%H:%M")

    return "Celine", "Surcharge"

st.title("🚀 IA Planning : Focus Rue & Adresses")

# --- BARRE LATÉRALE ---
with st.sidebar:
    st.header("📥 Importation Massive")
    uploaded = st.file_uploader("Fichier Excel", type=['xlsx'])
    
    if uploaded and st.button("🚀 Planification du mois"):
        df_ex = pd.read_excel(uploaded).dropna(how='all').fillna('')
        df_ex.columns = df_ex.columns.str.strip()
        col_d = next((c for c in df_ex.columns if 'date' in c.lower()), 'Date')
        
        temp_db = st.session_state.db.copy()
        for _, row in df_ex.sort_values(by=[col_d, 'Batiment']).iterrows():
            b, d = row['Batiment'], pd.to_datetime(row[col_d]).strftime('%d/%m/%Y')
            agt, hr = trouver_meilleur_creneau(b, d, temp_db)
            temp_db = pd.concat([temp_db, pd.DataFrame([{
                'Batiment': b, 'Date': d, 'Heure': hr, 'Agent': agt, 
                'Rue': INFOS_BATIMENTS.get(b, "Autre"), 'Type': "Import"
            }])], ignore_index=True)
        st.session_state.db = temp_db
        st.success("Planning optimisé (Céline prioritaire) !")

    st.divider()
    st.header("📊 Performance")
    if not st.session_state.db.empty:
        total = len(st.session_state.db)
        groupements = st.session_state.db.groupby(['Date', 'Rue']).size()
        score = (len(groupements[groupements > 1]) / total * 100) if total > 0 else 0
        st.metric("Taux d'Occupation (Rue)", f"{int(score)}%")
        
        csv = st.session_state.db.to_csv(index=False).encode('utf-8')
        st.download_button("📥 Télécharger le planning (CSV)", csv, "planning_export.csv", "text/csv")
        
        if st.button("🗑️ Reset Planning"):
            st.session_state.db = pd.DataFrame(columns=['Batiment', 'Date', 'Heure', 'Agent', 'Rue', 'Type'])
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
        l = {'Batiment': n_bat, 'Date': date_str, 'Heure': f_hr, 'Agent': f_agt, 'Rue': INFOS_BATIMENTS.get(n_bat, "Autre"), 'Type': "Manuel"}
        st.session_state.db = pd.concat([st.session_state.db, pd.DataFrame([l])], ignore_index=True)
        st.rerun()

# --- TABLEAU FINAL ---
st.divider()
if not st.session_state.db.empty:
    sel_d = st.selectbox("Afficher le planning du :", sorted(st.session_state.db['Date'].unique()))
    df_v = st.session_state.db[st.session_state.db['Date'] == sel_d].sort_values(by=['Agent', 'Heure'])

    def style_agent(row):
        return [f'background-color: {COULEURS.get(row["Agent"])}'] * len(row)

    st.subheader(f"Planning du {sel_d}")
    st.table(df_v[['Batiment', 'Rue', 'Heure', 'Agent']].style.apply(style_agent, axis=1))
