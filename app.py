import streamlit as st
import pandas as pd

# 1. Configuration des Zones de Lausanne
ZONES = {
    'Bethusy A': 'Chailly', 'Bethusy B': 'Chailly',
    'Montolieu A': 'Montolieu', 'Montolieu B': 'Montolieu',
    'Tunnel': 'Riponne', 'Oron': 'Oron'
}

st.set_page_config(page_title="Optimiseur Lausanne", layout="wide")
st.title("📍 Planificateur d'Attributions")

# 2. Upload du fichier
uploaded_file = st.file_uploader("Glissez votre fichier Excel ou CSV ici", type=['csv', 'xlsx'])

if uploaded_file:
    # Lecture
    if uploaded_file.name.endswith('.csv'):
        df = pd.read_csv(uploaded_file)
    else:
        df = pd.read_excel(uploaded_file)

    # Nettoyage des colonnes (pour éviter les erreurs d'espaces)
    df.columns = df.columns.str.strip()
    
    # 3. Calcul de l'optimisation
    df['Zone'] = df['Batiment'].map(ZONES)
    
    # On trie d'abord par Date, puis par Zone (pour regrouper les bâtiments collés), puis par Heure
    # "libre" est considéré comme arrivant après les heures fixes
    df['Heure_Tri'] = df['Heure'].astype(str).replace('libre', '23:59')
    df = df.sort_values(by=['Date', 'Zone', 'Heure_Tri'])
    
    # Attribution tournante sur vos 3 agents
    agents = ['Agent 1', 'Agent 2', 'Agent 3']
    df['Agent_Attribue'] = [agents[i % 3] for i in range(len(df))]
    
    # 4. Affichage
    st.success("✅ Planning généré ! Les bâtiments d'une même zone sont regroupés.")
    
    # On affiche le tableau final propre
    resultat = df[['ID', 'Batiment', 'Date', 'Heure', 'Type', 'Agent_Attribue']]
    st.dataframe(resultat, use_container_width=True)
    
    # 5. Téléchargement
    csv = resultat.to_csv(index=False).encode('utf-8-sig')
    st.download_button("📥 Télécharger pour Excel", csv, "planning_lausanne.csv", "text/csv")
