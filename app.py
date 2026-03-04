import streamlit as st
import pandas as pd
from datetime import datetime, timedelta

# Configuration des zones Lausanne
ZONES = {
    'Bethusy A': 'Chailly', 'Bethusy B': 'Chailly',
    'Montolieu A': 'Montolieu', 'Montolieu B': 'Montolieu',
    'Montelieu A': 'Montolieu', 'Montelieu B': 'Montolieu',
    'Tunnel': 'Riponne', 'Oron': 'Oron'
}

st.set_page_config(page_title="Planning Maria & Celine", layout="wide")
st.title("📍 Planning : Maria Claret, Celine, Maria Elisabeth")

uploaded_file = st.file_uploader("Glissez votre fichier Excel ici", type=['csv', 'xlsx'])

if uploaded_file:
    # Lecture
    df = pd.read_csv(uploaded_file) if uploaded_file.name.endswith('.csv') else pd.read_excel(uploaded_file, engine='openpyxl')
    df.columns = df.columns.str.strip()

    # 1. Préparation des données
    df['Zone'] = df['Batiment'].map(ZONES)
    # On transforme "libre" en 23:59 pour que ça arrive en dernier dans le tri
    df['Heure_Tri'] = df['Heure'].astype(str).str.lower().replace('libre', '23:59:00')
    
    # Tri par Date, puis par Agent, puis par Heure
    df = df.sort_values(by=['Date', 'Heure_Tri'])
    
    # 2. Attribution des 3 agents
    agents_noms = ['Maria Claret', 'Celine', 'Maria Elisabeth']
    # On s'assure de répartir sur les 20 tâches
    df['Agent_Attribue'] = [agents_noms[i % len(agents_noms)] for i in range(len(df))]

    # 3. Suggestion d'horaire pour les "Libres"
    suggestions = []
    for i, row in df.iterrows():
        heure_actuelle = str(row['Heure']).lower()
        
        if 'libre' in heure_actuelle:
            # On cherche si l'agent a une mission AVANT le même jour
            missions_avant = df[(df['Date'] == row['Date']) & 
                                (df['Agent_Attribue'] == row['Agent_Attribue']) & 
                                (df['Heure'].astype(str).lower() != 'libre')]
            
            if not missions_avant.empty:
                # On prend la dernière heure fixe connue
                derniere_heure = str(missions_avant.iloc[-1]['Heure'])
                try:
                    # On ajoute 1h30
                    h_fixe = pd.to_datetime(derniere_heure, format='%H:%M:%S').time()
                    h_suggeree = (datetime.combine(datetime.today(), h_fixe) + timedelta(hours=1, minutes=30)).strftime('%H:%M')
                    suggestions.append(f"Suggéré: {h_suggeree} (Libre)")
                except:
                    # Si format d'heure bizarre (ex: 9h00 au lieu de 09:00:00)
                    suggestions.append("À définir (Libre)")
            else:
                suggestions.append("09:00 (Libre - Début)")
        else:
            suggestions.append(heure_actuelle)

    df['Heure_Finale'] = suggestions

    # 4. Affichage propre
    st.success("✅ Planning optimisé !")
    vue_finale = df[['ID', 'Batiment', 'Date', 'Heure_Finale', 'Type', 'Agent_Attribue']]
    st.dataframe(vue_finale.rename(columns={'Heure_Finale': 'Heure/Suggestion'}), use_container_width=True)
    
    # Export
    csv = vue_finale.to_csv(index=False).encode('utf-8-sig')
    st.download_button("📥 Télécharger le planning final", csv, "planning_equipe.csv", "text/csv")
