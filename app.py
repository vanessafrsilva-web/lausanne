import streamlit as st
import pandas as pd
from datetime import datetime, timedelta

# --- CONFIGURATION FIXE ---
BUREAU = "Mon Paisible 18"
AGENTS = ["Maria Claret", "Celine", "Maria Elisabeth"]
ZONES = {
    'Bethusy A': 'Chailly', 'Bethusy B': 'Chailly',
    'Montolieu A': 'Montolieu', 'Montolieu B': 'Montolieu',
    'Tunnel': 'Riponne', 'Oron': 'Oron'
}

st.set_page_config(page_title="Planificateur Expert - Unité Logement", layout="wide")

# --- STYLE PERSONNALISÉ ---
st.markdown("""
    <style>
    .reportview-container { background: #f0f2f6; }
    .stMetric { background: white; padding: 15px; border-radius: 10px; box-shadow: 0 2px 4px rgba(0,0,0,0.05); }
    </style>
    """, unsafe_allow_html=True)

st.title("🚀 Assistant de Planification Intelligent")
st.write(f"Gestion des 30 attributions mensuelles - Départ : **{BUREAU}**")

# --- 1. BASE DE DONNÉES (Simulation de la mémoire de l'outil) ---
if 'db' not in st.session_state:
    st.session_state.db = pd.DataFrame(columns=['Batiment', 'Date', 'Heure', 'Agent', 'Zone'])

# --- 2. FORMULAIRE D'AIDE À LA DÉCISION ---
with st.expander("➕ PLANIFIER UNE NOUVELLE ATTRIBUTION", expanded=True):
    col1, col2, col3 = st.columns(3)
    
    with col1:
        nouveau_bat = st.selectbox("Bâtiment concerné :", list(ZONES.keys()))
        zone_cible = ZONES[nouveau_bat]
    
    with col2:
        date_souhaitee = st.date_input("Date prévue :")
        date_str = date_souhaitee.strftime('%d/%m/%Y')

    # --- LE MOTEUR DE SUGGESTION (L'intelligence de l'IA) ---
    missions_jour = st.session_state.db[st.session_state.db['Date'] == date_str]
    
    # Analyse des opportunités
    suggestions = []
    if not missions_jour.empty:
        # Existe-t-il déjà quelqu'un dans cette zone ce jour-là ?
        meme_zone = missions_jour[missions_jour['Zone'] == zone_cible]
        if not meme_zone.empty:
            for _, row in meme_zone.iterrows():
                suggestions.append(f"✨ OPTIMAL : {row['Agent']} est déjà à {zone_cible}. Groupez avec elle !")
    
    with col3:
        if suggestions:
            for s in suggestions: st.success(s)
        else:
            st.info("ℹ️ Aucune mission dans cette zone ce jour-là.")

    # Choix final par la collaboratrice
    c_agt, c_hr = st.columns(2)
    with c_agt: agent_choisi = st.selectbox("Attribuer à :", AGENTS)
    with c_hr: heure_choisie = st.time_input("Heure du RDV :", datetime.strptime("08:00", "%H:%M"))

    if st.button("✅ Valider et Ajouter au Planning"):
        nouvelle_ligne = {
            'Batiment': nouveau_bat, 
            'Date': date_str, 
            'Heure': heure_choisie.strftime('%H:%M'), 
            'Agent': agent_choisi, 
            'Zone': zone_cible
        }
        st.session_state.db = pd.concat([st.session_state.db, pd.DataFrame([nouvelle_ligne])], ignore_index=True)
        st.balloons()

# --- 3. VISION GLOBALE DES 30 DOSSIERS ---
st.divider()
st.subheader("📅 Tableau de Bord du Mois")

if not st.session_state.db.empty:
    # Tri intelligent
    df_tri = st.session_state.db.sort_values(by=['Date', 'Agent', 'Heure'])
    
    # Filtre par agent pour les collaboratrices
    view_agt = st.multiselect("Filtrer par collaboratrice :", AGENTS, default=AGENTS)
    df_filtered = df_tri[df_tri['Agent'].isin(view_agt)]
    
    # Affichage stylisé
    def color_agent(val):
        if val == 'Maria Claret': return 'background-color: #ffdae0'
        if val == 'Celine': return 'background-color: #d1e9ff'
        if val == 'Maria Elisabeth': return 'background-color: #d4f8d4'
        return ''

    st.table(df_filtered.style.applymap(color_agent, subset=['Agent']))

    # --- 4. ANALYSE DE PERFORMANCE ---
    st.subheader("📊 Analyse de l'Optimisation")
    c1, c2, c3 = st.columns(3)
    
    # Calcul de la charge
    total_missions = len(st.session_state.db)
    c1.metric("Dossiers Planifiés", f"{total_missions} / 30")
    
    # Calcul des regroupements (Performance)
    groupements = st.session_state.db.groupby(['Date', 'Zone']).size()
    succes_groupes = len(groupements[groupements > 1])
    c2.metric("Regroupements réussis", succes_groupes, help="Nombre de fois où plusieurs missions sont dans la même zone le même jour.")
    
    # Alerte Surcharge
    surcharge = st.session_state.db.groupby(['Date', 'Agent']).size()
    jours_critiques = len(surcharge[surcharge > 4])
    c3.metric("Alertes Surcharge", jours_critiques, delta_color="inverse", delta="Jours > 4 rdv")

else:
    st.info("Le planning est vide. Commencez à ajouter des dossiers ci-dessus.")

# --- BOUTON DE SAUVEGARDE ---
if st.sidebar.button("💾 Sauvegarder le planning (CSV)"):
    csv = st.session_state.db.to_csv(index=False)
    st.sidebar.download_button("⬇️ Télécharger", csv, "planning_avril.csv", "text/csv")
