import streamlit as st
import pandas as pd
from datetime import datetime, timedelta

# Configuration Lausanne
ZONES = {
    'Bethusy A': 'Chailly', 'Bethusy B': 'Chailly',
    'Montolieu A': 'Montolieu', 'Montolieu B': 'Montolieu',
    'Montelieu A': 'Montolieu', 'Montelieu B': 'Montolieu',
    'Tunnel': 'Riponne', 'Oron': 'Oron'
}

st.set_page_config(page_title="Planning Lausanne", layout="wide")
st.title("📍 Planning : Maria Claret, Celine, Maria Elisabeth")

uploaded_file = st.file_uploader("Glissez votre fichier Excel ici", type=['csv', 'xlsx'])

if uploaded_file:
    df = pd.read_csv(uploaded_file) if uploaded_file.name.endswith('.csv') else pd.read_excel(uploaded_file, engine='openpyxl')
    df.columns = df.columns.str.strip()

    # 1. Attribution des zones et agents
    df['Zone'] = df['Batiment'].map(ZONES)
    
    # Tri intelligent
    df['Heure_Tri'] = df['Heure'].astype(str).replace('libre', '23:59')
    df = df.sort_values(by=['Date', 'Zone', 'Heure_Tri'])
    
    # Noms des agents
    agents = ['Maria Claret', 'Celine', 'Maria Elisabeth']
    df['Agent_Attribue'] = [agents[i % 3] for i in range(len(df))]
    
    # 2. LOGIQUE DES HORAIRES SUGGÉRÉS
    def suggerer_heure(row, group):
        current_heure = str(row['Heure']).lower()
        if 'libre' in current_heure:
            # On cherche s'il y a une autre mission avec une heure fixe pour cet agent ce jour-là
            autres = group[(group['Agent_Attribue'] == row['Agent_Attribue']) & (group['Heure'].astype(str).lower() != 'libre')]
            if not autres.empty:
                ref_heure = pd.to_datetime(autres.iloc[0]['Heure'], format='%H:%M:%S', errors='coerce')
                if pd.isna(ref_heure): # Test format court %H:%M
                     ref_heure = pd.to_datetime(autres.iloc[0]['Heure'], format='%H:%M', errors='coerce')
                
                # On suggère 1h30 après la mission fixe
                suggested = (ref_heure + timedelta(hours=1, minutes=30)).strftime('%H:%M')
                return f"Suggéré: {suggested} (Libre)"
            return "À définir (Libre)"
        return current_heure

    # On applique la suggestion par groupe de Date
    df['Heure_Finale'] = df.apply(lambda x: suggerer_heure(x, df[df['Date'] == x['Date']]), axis=1)

    # 3. Affichage
    st.success("✅ Planning optimisé avec les horaires suggérés !")
    
    final_view = df[['ID', 'Batiment', 'Date', 'Heure_Finale', 'Type', 'Agent_Attribue']]
    st.dataframe(final_view.rename(columns={'Heure_Finale': 'Heure/Suggestion'}), use_container_width=True)
    
    # Export
    csv = final_view.to_csv(index=False).encode('utf-8-sig')
    st.download_button("📥 Télécharger le Planning Maria & Celine", csv, "planning_equipe.csv", "text/csv")
