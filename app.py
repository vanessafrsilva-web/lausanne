import streamlit as st
import pandas as pd

# Dictionnaire des zones de Lausanne
ZONES = {
    'Bethusy A': 'Chailly', 'Bethusy B': 'Chailly',
    'Montolieu A': 'Montolieu', 'Montolieu B': 'Montolieu',
    'Montelieu A': 'Montolieu', 'Montelieu B': 'Montolieu',
    'Tunnel': 'Riponne', 'Oron': 'Oron'
}

st.set_page_config(page_title="Planning Lausanne", layout="wide")
st.title("📍 Optimisation des Attributions")

uploaded_file = st.file_uploader("Glissez votre fichier Excel ou CSV ici", type=['csv', 'xlsx'])

if uploaded_file:
    # Lecture intelligente du fichier
    try:
        if uploaded_file.name.endswith('.csv'):
            df = pd.read_csv(uploaded_file)
        else:
            # On utilise openpyxl pour lire le format .xlsx
            df = pd.read_excel(uploaded_file, engine='openpyxl')

        # Nettoyage des colonnes (enlève les espaces comme dans 'Date ')
        df.columns = df.columns.str.strip()
        
        # Attribution des zones
        df['Zone'] = df['Batiment'].map(ZONES)
        
        # Gestion du tri (Date, puis Zone pour regrouper, puis Heure)
        df['Heure_Tri'] = df['Heure'].astype(str).replace('libre', '23:59')
        df = df.sort_values(by=['Date', 'Zone', 'Heure_Tri'])
        
        # Attribution équitable sur 3 agents
        agents = ['Agent 1', 'Agent 2', 'Agent 3']
        df['Agent_Attribue'] = [agents[i % 3] for i in range(len(df))]
        
        # Affichage du résultat
        st.success("✅ Planning généré avec succès !")
        colonnes_a_afficher = ['ID', 'Batiment', 'Date', 'Heure', 'Type', 'Agent_Attribue']
        st.dataframe(df[colonnes_a_afficher], use_container_width=True)
        
        # Exportation
        csv = df.to_csv(index=False).encode('utf-8-sig')
        st.download_button("📥 Télécharger le résultat pour Excel", csv, "planning_final.csv", "text/csv")

    except Exception as e:
        st.error(f"Oups ! Il y a un souci avec le fichier : {e}")
