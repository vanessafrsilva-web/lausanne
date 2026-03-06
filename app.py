import streamlit as st
import pandas as pd
from datetime import datetime, timedelta

# --- CONFIGURATION FIXE ---
BUREAU = "Mon Paisible 18, 1007 Lausanne"
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
    "À définir": "#eeeeee"
}

st.set_page_config(page_title="IA Planning - Unité Logement", layout="wide")

if 'db' not in st.session_state:
    st.session_state.db = pd.DataFrame(columns=['Batiment', 'Date', 'Heure', 'Agent', 'Zone', 'Type'])

# --- MOTEUR D'ATTRIBUTION ET HORAIRES ---
def trouver_meilleur_creneau(batiment, date_str, temp_db):
    zone_cible = ZONES.get(batiment, "Autre")
    missions_jour = temp_db[temp_db['Date'] == date_str]
    
    # 1. Si journée vide -> 08:15 (trajet depuis le bureau)
    if missions_jour.empty:
        return AGENTS[0], "08:15"
    
    # 2. Chercher si un agent est déjà dans la même zone
    meme_zone = missions_jour[missions_jour['Zone'] == zone_cible]
    if not meme_zone.empty:
        dernier = meme_zone.sort_values(by='Heure').iloc[-1]
        h_fin = datetime.strptime(dernier['Heure'], "%H:%M") + timedelta(hours=1, minutes=20)
        return dernier['Agent'], h_fin.strftime("%H:%M")

    # 3. Sinon, équilibrage de la charge
    stats = {agt: len(missions_jour[missions_jour['Agent'] == agt]) for agt in AGENTS}
    agent_libre = min(stats, key=stats.get)
    missions_agt = missions_jour[missions_jour['Agent'] == agent_libre]
    
    if missions_agt.empty:
        return agent_libre, "08:15"
    else:
        # Trajet + important si changement de zone
        h_fin = datetime.strptime(missions_agt.sort_values(by='Heure').iloc[-1]['Heure'], "%H:%M") + timedelta(hours=1, minutes=45)
        return agent_libre, h_fin.strftime("%H:%M")

st.title("🚀 IA Planning : Optimisation & Occupation")

# --- BARRE LATÉRALE : IMPORT & SCORES ---
with st.sidebar:
    st.header("📥 Importation")
    uploaded = st.file_uploader("Fichier Excel (30 dossiers)", type=['xlsx'])
    
    if uploaded and st.button("🚀 Planifier Avril automatiquement"):
        df_ex = pd.read_excel(uploaded).dropna(how='all').fillna('')
        df_ex.columns = df_ex.columns.str.strip()
        col_d = next((c for c in df_ex.columns if 'date' in c.lower()), 'Date')
        df_ex = df_ex.sort_values(by=[col_d, 'Batiment'])
        
        temp_db = st.session_state.db.copy()
        for _, row in df_ex.iterrows():
            b, d = row['Batiment'], pd.to_datetime(row[col_d]).strftime('%d/%m/%Y')
            agt, hr = trouver_meilleur_creneau(b, d, temp_db)
            temp_db = pd.concat([temp_db, pd.DataFrame([{
                'Batiment': b, 'Date': d, 'Heure': hr, 'Agent': agt, 'Zone': ZONES.get(b, "Autre"), 'Type': "Import"
            }])], ignore_index=True)
        st.session_state.db = temp_db
        st.success("Dossiers planifiés !")

    st.divider()
    st.header("📊 Performance du Mois")
    if not st.session_state.db.empty:
        total = len(st.session_state.db)
        # Calcul du taux de regroupement (Efficacité)
        groupements = st.session_state.db.groupby(['Date', 'Zone']).size()
        score = (len(groupements[groupements > 1]) / total * 100) if total > 0 else 0
        
        st.metric("Total Dossiers", f"{total} / 30")
        st.metric("Taux d'Occupation", f"{int(score)}%", help="Objectif : Maximiser les regroupements par zone.")
        
        if st.button("🗑️ Reset Planning"):
            st.session_state.db = pd.DataFrame(columns=['Batiment', 'Date', 'Heure', 'Agent', 'Zone', 'Type'])
            st.rerun()

# --- FORMULAIRE MANUEL ---
with st.expander("➕ AJOUTER / MODIFIER MANUELLEMENT"):
    c1, c2 = st.columns(2)
    with c1:
        n_bat = st.selectbox("Bâtiment", list(ZONES.keys()))
        n_date = st.date_input("Date").strftime('%d/%m/%Y')
    with c2:
        s_agt, s_hr = trouver_meilleur_creneau(n_bat, n_date, st.session_state.db)
        f_agt = st.selectbox("Agent recommandé", AGENTS, index=AGENTS.index(s_agt))
        f_hr = st.text_input("Heure", value=s_hr)
    if st.button("Enregistrer"):
        l = {'Batiment': n_bat, 'Date': n_date, 'Heure': f_hr, 'Agent': f_agt, 'Zone': ZONES.get(n_bat, "Autre"), 'Type': "Manuel"}
        st.session_state.db = pd.concat([st.session_state.db, pd.DataFrame([l])], ignore_index=True)
        st.rerun()

# --- TABLEAU FINAL ---
st.divider()
if not st.session_state.db.empty:
    sel_d = st.selectbox("Voir le planning du :", sorted(st.session_state.db['Date'].unique()))
    df_v = st.session_state.db[st.session_state.db['Date'] == sel_d].sort_values(by='Heure')

    def style_agent(row):
        return [f'background-color: {COULEURS.get(row["Agent"])}'] * len(row)

    st.subheader(f"Planning du {sel_d}")
    st.table(df_v[['Batiment', 'Heure', 'Agent', 'Zone']].style.apply(style_agent, axis=1))
