import streamlit as st
import pandas as pd
from datetime import datetime, timedelta

# --- CONFIGURATION ---
BUREAU = "Mon Paisible 18"
AGENTS = ["Maria Claret", "Celine", "Maria Elisabeth"]
ZONES = {
    'Bethusy A': 'Chailly', 'Bethusy B': 'Chailly', 'Bethusy C': 'Chailly',
    'Montolieu A': 'Montolieu', 'Montolieu B': 'Montolieu',
    'Tunnel': 'Riponne', 'Oron': 'Oron', 'Riponne': 'Riponne'
}
COULEURS = {
    "Maria Claret": "#ffdae0",   # Rose
    "Celine": "#d1e9ff",         # Bleu
    "Maria Elisabeth": "#d4f8d4", # Vert
    "À définir": "#eeeeee"       # Gris
}

st.set_page_config(page_title="IA Planning Unité Logement", layout="wide")

if 'db' not in st.session_state:
    st.session_state.db = pd.DataFrame(columns=['Batiment', 'Date', 'Heure', 'Agent', 'Zone', 'Type'])

st.title("🚀 Assistant Intelligent : Planification Avril")

# --- FONCTION DE SUGGESTION D'HORAIRE ET AGENT ---
def suggerer_meilleur_creneau(batiment, date_str):
    zone_cible = ZONES.get(batiment, "Autre")
    missions_jour = st.session_state.db[st.session_state.db['Date'] == date_str]
    
    if missions_jour.empty:
        # Premier de la journée : on suggère 08h15 (trajet depuis le bureau)
        return AGENTS[0], "08:15", "✨ Premier RDV : départ Mon Paisible à 08h00."
    
    # Chercher si un agent est déjà dans la même zone
    meme_zone = missions_jour[missions_jour['Zone'] == zone_cible]
    if not meme_zone.empty:
        agent_sur_place = meme_zone.iloc[-1]['Agent']
        derniere_heure = datetime.strptime(meme_zone.iloc[-1]['Heure'], "%H:%M")
        suggestion_h = (derniere_heure + timedelta(hours=1, minutes=20)).strftime("%H:%M")
        return agent_sur_place, suggestion_h, f"🎯 OPTIMAL : {agent_sur_place} est déjà à {zone_cible}."

    # Sinon, prendre l'agent le moins chargé
    charge = missions_jour['Agent'].value_counts()
    for agt in AGENTS:
        if agt not in charge:
            return agt, "08:15", f"⚖️ ÉQUILIBRE : {agt} n'a rien encore ce jour-là."
    
    agent_libre = charge.idxmin()
    return agent_libre, "10:00", "📅 DISPONIBILITÉ : Agent le moins chargé."

# --- INTERFACE ---
with st.sidebar:
    st.header("📥 Importation")
    uploaded = st.file_uploader("Fichier Excel (30 dossiers)", type=['xlsx'])
    if uploaded and st.button("Fusionner l'Excel"):
        df_ex = pd.read_excel(uploaded).dropna(how='all').fillna('')
        df_ex.columns = df_ex.columns.str.strip()
        col_d = next((c for c in df_ex.columns if 'date' in c.lower()), 'Date')
        new_data = pd.DataFrame({
            'Batiment': df_ex['Batiment'],
            'Date': pd.to_datetime(df_ex[col_d]).dt.strftime('%d/%m/%Y'),
            'Heure': "À définir",
            'Agent': "À définir",
            'Zone': df_ex['Batiment'].map(ZONES).fillna('Autre'),
            'Type': "Attribution"
        })
        st.session_state.db = pd.concat([st.session_state.db, new_data]).drop_duplicates().reset_index(drop=True)
        st.success("Importé !")

# --- FORMULAIRE INTELLIGENT ---
with st.expander("➕ PLANIFIER UN DOSSIER (AIDE À LA DÉCISION)", expanded=True):
    c1, c2 = st.columns(2)
    with c1:
        n_bat = st.selectbox("Bâtiment :", list(ZONES.keys()))
        n_date = st.date_input("Date :")
        date_s = n_date.strftime('%d/%m/%Y')
    
    # Appel du moteur de suggestion
    sugg_agent, sugg_heure, raison = suggerer_meilleur_creneau(n_bat, date_s)
    
    with c2:
        st.info(f"💡 **Recommandation IA :**\n\n{raison}")
        agent_final = st.selectbox("Agent recommandé :", AGENTS, index=AGENTS.index(sugg_agent))
        heure_final = st.text_input("Heure recommandée :", value=sugg_heure)

    if st.button("✅ Valider l'attribution"):
        nouvelle_ligne = {
            'Batiment': n_bat, 'Date': date_s, 'Heure': heure_final, 
            'Agent': agent_final, 'Zone': ZONES.get(n_bat, "Autre"), 'Type': "Attribution"
        }
        st.session_state.db = pd.concat([st.session_state.db, pd.DataFrame([nouvelle_ligne])], ignore_index=True)
        st.rerun()

# --- AFFICHAGE ---
st.divider()
if not st.session_state.db.empty:
    f_date = st.selectbox("Voir le planning du :", sorted(st.session_state.db['Date'].unique()))
    df_view = st.session_state.db[st.session_state.db['Date'] == f_date].sort_values(by=['Heure'])

    def apply_color(row):
        return [f'background-color: {COULEURS.get(row["Agent"], "#eeeeee")}'] * len(row)

    st.subheader(f"Planning du {f_date}")
    st.table(df_view.style.apply(apply_color, axis=1))
