import streamlit as st
import pandas as pd

# On accepte les deux orthographes pour éviter les erreurs
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
    # Lecture du fichier
    df = pd.read_csv(uploaded_file) if uploaded_file.name.endswith('.csv') else pd.read_excel(uploaded_file)

    # Nettoyage automatique des noms de colonnes (enlève les espaces comme dans 'Date ')
    df.columns = df.columns.str.strip()
    
    # 3. Attribution des zones et tri
    df['Zone'] = df['Batiment'].map(ZONES)
    
    # Gestion du tri : on met les "libre" en fin de journée
    df['Heure_Tri'] = df['Heure'].astype(str).replace('libre', '23:59')
    df = df.sort_values(by=['Date', 'Zone', 'Heure_Tri'])
    
    # Attribution équitable sur 3 agents
    agents = ['Agent 1', 'Agent 2', 'Agent 3']
    df['Agent_Attribue'] = [agents[i % 3] for i in range(len(df))]
    
    # 4. Affichage
    st.success("✅ Planning optimisé généré !")
    st.dataframe(df[['ID', 'Batiment', 'Date', 'Heure', 'Agent_Attribue']], use_container_width=True)
    
    # 5. Export
    csv = df.to_csv(index=False).encode('utf-8-sig')
    st.download_button("📥 Télécharger le résultat pour Excel", csv, "planning_final.csv", "text/csv")
