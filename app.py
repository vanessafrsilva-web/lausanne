import streamlit as st
import pandas as pd
from datetime import datetime, timedelta

# Configuration des Zones Lausanne
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
    # Lecture flexible
    try:
        if uploaded_file.name.endswith('.csv'):
            df = pd.read_csv(uploaded_file)
        else:
            df = pd.read_excel(uploaded_file, engine='openpyxl')
        
        # Nettoyage des colonnes (ex: 'Date ' -> 'Date')
        df.columns = df.columns.str.strip()

        # 1. Attribution des zones et agents
        df['Zone'] = df['Batiment'].map(ZONES)
        
        # On trie pour que les "libre" arrivent après les heures fixes
        df['Heure_Tri'] = df['Heure'].astype(str).str.lower().str.strip().replace('libre', '23:59:00')
        df = df.sort_values(by=['Date', 'Zone', 'Heure_Tri'])
        
        # Attribution tournante des agents
        agents_noms = ['Maria Claret', 'Celine', 'Maria Elisabeth']
        df['Agent_Attribue'] = [agents_noms[i % len(agents_noms)] for i in range(len(df))]

        # 2. Logique de suggestion d'horaire
        suggestions = []
        for i, row in df.iterrows():
            h_brute = str(row['Heure']).lower().strip()
            
            if 'libre' in h_brute:
                # Cherche une mission FIXE du MÊME agent le MÊME jour dans le tableau trié
                jour = row['Date']
                agent = row['Agent_Attribue']
                missions_fixe = df[(df['Date'] == jour) & 
                                   (df['Agent_Attribue'] == agent) & 
                                   (~df['Heure'].astype(str).str.lower().str.contains('libre'))]
                
                if not missions_fixe.empty:
                    try:
                        # On prend la première heure fixe du jour pour cet agent
                        premiere_h = str(missions_fixe.iloc[0]['Heure'])
                        h_dt = pd.to_datetime(premiere_h, errors='coerce')
                        # On suggère 1h30 après
                        sugg = (h_dt + timedelta(hours=1, minutes=30)).strftime('%H:%M')
                        suggestions.append(f"Suggéré: {sugg}")
                    except:
                        suggestions.append("09:00 (Libre)")
                else:
                    suggestions.append("09:00 (Libre)")
            else:
                # On nettoie l'affichage de l'heure fixe (ex: 09:00:00 -> 09:00)
                try:
                    suggestions.append(pd.to_datetime(h_brute).strftime('%H:%M'))
                except:
                    suggestions.append(h_brute)

        df['Heure_Finale'] = suggestions

        # 3. Affichage final
        st.success("✅ Planning optimisé généré !")
        vue = df[['ID', 'Batiment', 'Date', 'Heure_Finale', 'Type', 'Agent_Attribue']]
        st.dataframe(vue.rename(columns={'Heure_Finale': 'Heure / Suggestion'}), use_container_width=True)
        
        # Export
        csv = vue.to_csv(index=False).encode('utf-8-sig')
        st.download_button("📥 Télécharger le planning final", csv, "planning_equipe.csv", "text/csv")

    except Exception as e:
        st.error(f"Erreur lors de l'analyse du fichier : {e}")
