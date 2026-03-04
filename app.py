import streamlit as st
import pandas as pd
from datetime import datetime, timedelta

# Zones de proximité Lausanne
ZONES = {
    'Bethusy A': 'Chailly', 'Bethusy B': 'Chailly',
    'Montolieu A': 'Montolieu', 'Montolieu B': 'Montolieu',
    'Montelieu A': 'Montolieu', 'Montelieu B': 'Montolieu',
    'Tunnel': 'Riponne', 'Oron': 'Oron'
}

st.set_page_config(page_title="Planning Optimisé Lausanne", layout="wide")
st.title("📍 Planning Maria, Celine & Elisabeth")

uploaded_file = st.file_uploader("Glissez votre fichier Excel ici", type=['csv', 'xlsx'])

if uploaded_file:
    try:
        df = pd.read_csv(uploaded_file) if uploaded_file.name.endswith('.csv') else pd.read_excel(uploaded_file, engine='openpyxl')
        df.columns = df.columns.str.strip()

        # 1. Préparation des zones et tri
        df['Zone'] = df['Batiment'].map(ZONES)
        df['Heure_Tri'] = df['Heure'].astype(str).str.lower().str.strip().replace('libre', '23:59:00')
        
        # TRI CRUCIAL : Date d'abord, puis Bâtiment (pour les grouper ensemble)
        df = df.sort_values(by=['Date', 'Batiment', 'Heure_Tri'])
        
        # 2. ATTRIBUTION PAR GROUPE (Bâtiment + Date)
        agents_noms = ['Maria Claret', 'Celine', 'Maria Elisabeth']
        df['Agent_Attribue'] = ""
        
        # On crée un identifiant unique pour chaque groupe "Jour + Bâtiment"
        df['Group_ID'] = df['Date'].astype(str) + "_" + df['Batiment']
        
        # On attribue un agent différent à chaque nouveau groupe
        groupes_uniques = df['Group_ID'].unique()
        mapping_agent = {grp: agents_noms[i % len(agents_noms)] for i, grp in enumerate(groupes_uniques)}
        
        df['Agent_Attribue'] = df['Group_ID'].map(mapping_agent)

        # 3. SUGGESTION D'HORAIRE
        suggestions = []
        # On regroupe par Date et Agent pour calculer les horaires à la suite
        for i, row in df.iterrows():
            h_val = str(row['Heure']).lower().strip()
            
            if 'libre' in h_val:
                # Cherche s'il y a une heure fixe AVANT pour cet agent ce jour-là
                fixes = df[(df['Date'] == row['Date']) & 
                           (df['Agent_Attribue'] == row['Agent_Attribue']) & 
                           (~df['Heure'].astype(str).str.lower().str.contains('libre'))]
                
                if not fixes.empty:
                    try:
                        derniere_h = pd.to_datetime(str(fixes.iloc[0]['Heure']), errors='coerce')
                        # On suggère 1h15 après (plus serré pour l'optimisation)
                        sugg = (derniere_h + timedelta(hours=1, minutes=15)).strftime('%H:%M')
                        suggestions.append(f"Suggéré: {sugg}")
                    except:
                        suggestions.append("10:00 (Libre)")
                else:
                    suggestions.append("09:00 (Libre)")
            else:
                try:
                    suggestions.append(pd.to_datetime(h_val).strftime('%H:%M'))
                except:
                    suggestions.append(h_val)

        df['Heure_Finale'] = suggestions

        # 4. Affichage
        st.success("✅ Optimisation terminée : Les agents restent au même bâtiment !")
        vue = df[['ID', 'Batiment', 'Date', 'Heure_Finale', 'Type', 'Agent_Attribue']]
        st.dataframe(vue.rename(columns={'Heure_Finale': 'Heure / Suggestion'}), use_container_width=True)
        
        # Export
        csv = vue.to_csv(index=False).encode('utf-8-sig')
        st.download_button("📥 Télécharger le planning groupé", csv, "planning_optimise.csv", "text/csv")

    except Exception as e:
        st.error(f"Erreur : {e}")
