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

st.set_page_config(page_title="Planning Lausanne", layout="wide")
st.title("📍 Planning : Maria Claret, Celine, Maria Elisabeth")

uploaded_file = st.file_uploader("Glissez votre fichier Excel ici", type=['csv', 'xlsx'])

if uploaded_file:
    # Lecture robuste
    try:
        if uploaded_file.name.endswith('.csv'):
            df = pd.read_csv(uploaded_file)
        else:
            df = pd.read_excel(uploaded_file, engine='openpyxl')
        
        # Nettoyage des colonnes (ex: 'Date ' -> 'Date')
        df.columns = df.columns.str.strip()

        # 1. Préparation et Tri
        df['Zone'] = df['Batiment'].map(ZONES)
        # On force le tri pour que les "libre" arrivent après les heures fixes
        df['Heure_Tri'] = df['Heure'].astype(str).str.lower().replace('libre', '23:59:00')
        df = df.sort_values(by=['Date', 'Heure_Tri'])
        
        # 2. Attribution des agents
        agents_noms = ['Maria Claret', 'Celine', 'Maria Elisabeth']
        df['Agent_Attribue'] = [agents_noms[i % len(agents_noms)] for i in range(len(df))]

        # 3. Calcul des suggestions d'horaires
        suggestions = []
        for i, row in df.iterrows():
            h_val = str(row['Heure']).lower().strip()
            
            if 'libre' in h_val:
                # Cherche une mission FIXE du même agent le même jour
                jour = row['Date']
                agent = row['Agent_Attribue']
                fixes = df[(df['Date'] == jour) & (df['Agent_Attribue'] == agent) & (~df['Heure'].astype(str).str.lower().contains('libre', na=False))]
                
                if not fixes.empty:
                    try:
                        derniere_h = pd.to_datetime(str(fixes.iloc[0]['Heure']), errors='coerce')
                        sugg = (derniere_h + timedelta(hours=1, minutes=30)).strftime('%H:%M')
                        suggestions.append(f"Suggéré: {sugg}")
                    except:
                        suggestions.append("09:00 (Libre)")
                else:
                    suggestions.append("09:00 (Libre)")
            else:
                # Formatage de l'heure fixe (ex: 15:00:00 -> 15:00)
                try:
                    suggestions.append(pd.to_datetime(h_val).strftime('%H:%M'))
                except:
                    suggestions.append(h_val)

        df['Heure_Finale'] = suggestions

        # 4. Affichage
        st.success("✅ Planning Maria & Celine généré !")
        vue = df[['ID', 'Batiment', 'Date', 'Heure_Finale', 'Type', 'Agent_Attribue']]
        st.dataframe(vue.rename(columns={'Heure_Finale': 'Heure / Suggestion'}), use_container_width=True)
        
        # Export
        csv = vue.to_csv(index=False).encode('utf-8-sig')
        st.download_button("📥 Télécharger le planning final", csv, "planning_equipe.csv", "text/csv")

    except Exception as e:
        st.error(f"Erreur lors de l'analyse : {e}")
