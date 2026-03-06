import streamlit as st
import pandas as pd
from datetime import datetime, timedelta

# --- CONFIGURATION DES RÉFÉRENCES ---
BUREAU = "Mon Paisible 18, 1007 Lausanne"
AGENTS = ["Maria Claret", "Celine", "Maria Elisabeth"]
ZONES = {
    'Bethusy A': 'Chailly', 'Bethusy B': 'Chailly', 'Bethusy C': 'Chailly',
    'Montolieu A': 'Montolieu', 'Montolieu B': 'Montolieu',
    'Tunnel': 'Riponne', 'Oron': 'Oron', 'Riponne': 'Riponne'
}

st.set_page_config(page_title="Expert Planning - Unité Logement", layout="wide")

# Initialisation de la base de données interne
if 'db' not in st.session_state:
    st.session_state.db = pd.DataFrame(columns=['ID', 'Batiment', 'Date', 'Heure', 'Agent', 'Zone', 'Type'])

st.title("📍 Planificateur Intelligent : Unité Logement")
st.write(f"Gestion hybride des attributions - Départ : **{BUREAU}**")

# --- SECTION 1 : IMPORTATION MASSIVE (LES 30 DOSSIERS) ---
with st.sidebar:
    st.header("📥 Importation Excel")
    uploaded_file = st.file_uploader("Charger le fichier du mois", type=['xlsx'])
    
    if uploaded_file:
        if st.button("🚀 Fusionner les données Excel"):
            df_excel = pd.read_excel(uploaded_file).dropna(how='all').fillna('')
            df_excel.columns = df_excel.columns.str.strip()
            
            # Détection de la colonne date
            col_date = next((c for c in df_excel.columns if 'date' in c.lower()), 'Date')
            
            # Transformation pour la base de données
            new_data = pd.DataFrame({
                'ID': df_excel['ID'] if 'ID' in df_excel.columns else range(len(df_excel)),
                'Batiment': df_excel['Batiment'],
                'Date': pd.to_datetime(df_excel[col_date]).dt.strftime('%d/%m/%Y'),
                'Heure': df_excel['Heure'].astype(str),
                'Agent': "À définir",
                'Zone': df_excel['Batiment'].map(ZONES).fillna('Autre'),
                'Type': df_excel['Type'] if 'Type' in df_excel.columns else "Attribution"
            })
            
            st.session_state.db = pd.concat([st.session_state.db, new_data]).drop_duplicates().reset_index(drop=True)
            st.success(f"{len(new_data)} dossiers importés !")

# --- SECTION 2 : AJOUT MANUEL ET SUGGESTIONS ---
with st.expander("➕ AJOUTER OU MODIFIER UN DOSSIER MANUELLEMENT"):
    col1, col2, col3 = st.columns(3)
    with col1:
        n_bat = st.selectbox("Bâtiment", list(ZONES.keys()))
        n_date = st.date_input("Date", value=datetime.now())
    with col2:
        n_heure = st.text_input("Heure (ex: 10:30)", value="Libre")
        n_agent = st.selectbox("Collaboratrice", AGENTS)
    with col3:
        n_type = st.selectbox("Type", ["Entrée", "Sortie", "Visite"])
        
    # Intelligence de regroupement
    date_str = n_date.strftime('%d/%m/%Y')
    zone_actuelle = ZONES.get(n_bat, "Autre")
    voisins = st.session_state.db[(st.session_state.db['Date'] == date_str) & (st.session_state.db['Zone'] == zone_actuelle)]
    
    if not voisins.empty:
        st.info(f"💡 **Conseil Performance :** {len(voisins)} dossier(s) déjà prévus à {zone_actuelle} ce jour-là. Privilégiez ce créneau !")

    if st.button("💾 Enregistrer la modification"):
        nouvelle_ligne = {'ID': 'Manuel', 'Batiment': n_bat, 'Date': date_str, 'Heure': n_heure, 'Agent': n_agent, 'Zone': zone_actuelle, 'Type': n_type}
        st.session_state.db = pd.concat([st.session_state.db, pd.DataFrame([nouvelle_ligne])], ignore_index=True)
        st.rerun()

# --- SECTION 3 : AFFICHAGE ET OPTIMISATION ---
st.divider()
if not st.session_state.db.empty:
    # Filtres d'affichage
    f_date = st.selectbox("Filtrer par jour :", ["Toutes les dates"] + sorted(st.session_state.db['Date'].unique().tolist()))
    
    df_view = st.session_state.db.copy()
    if f_date != "Toutes les dates":
        df_view = df_view[df_view['Date'] == f_date]
    
    # Tri par Agent et Heure
    df_view = df_view.sort_values(by=['Agent', 'Heure'])

    # Style des lignes par collaboratrice
    def style_rows(row):
        color = '#ffdae0' if row['Agent'] == 'Maria Claret' else '#d1e9ff' if row['Agent'] == 'Celine' else '#d4f8d4'
        if row['Agent'] == "À définir": color = '#eeeeee'
        return [f'background-color: {color}'] * len(row)

    st.subheader(f"Planning : {f_date}")
    st.table(df_view.style.apply(style_rows, axis=1))

    # --- INDICATEURS DE PERFORMANCE ---
    st.sidebar.markdown("---")
    st.sidebar.subheader("📊 Score du Mois")
    total = len(st.session_state.db)
    regroupes = st.session_state.db.groupby(['Date', 'Zone']).size()
    score_opti = (len(regroupes[regroupes > 1]) / total * 100) if total > 0 else 0
    
    st.sidebar.metric("Dossiers totaux", total)
    st.sidebar.metric("Taux de regroupement", f"{int(score_opti)}%", help="Plus ce score est haut, moins vos collaboratrices passent de temps sur la route.")

    if st.sidebar.button("🗑️ Vider tout le planning"):
        st.session_state.db = pd.DataFrame(columns=['ID', 'Batiment', 'Date', 'Heure', 'Agent', 'Zone', 'Type'])
        st.rerun()
else:
    st.info("Aucun dossier pour le moment. Importez votre fichier Excel ou ajoutez un dossier manuellement.")
