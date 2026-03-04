import streamlit as st
import pandas as pd
from datetime import datetime, timedelta

# Zones de proximité
ZONES = {
    'Bethusy A': 'Chailly', 'Bethusy B': 'Chailly',
    'Montolieu A': 'Montolieu', 'Montolieu B': 'Montolieu',
    'Montelieu A': 'Montolieu', 'Montelieu B': 'Montolieu',
    'Tunnel': 'Riponne', 'Oron': 'Oron'
}

st.set_page_config(page_title="Planning Lausanne", layout="wide")
st.title("📍 Planning : Maria, Celine & Elisabeth")

uploaded_file = st.file_uploader("Glissez votre fichier Excel ici", type=['csv', 'xlsx'])

if uploaded_file:
    try:
        df = pd.read_csv(uploaded_file) if uploaded_file.name.endswith('.csv') else pd.read_excel(uploaded_file, engine='openpyxl')
        
        # 1. NETTOYAGE ANTI-NAN (On supprime les lignes vides du bas de l'Excel)
        df = df.dropna(how='all') # Supprime les lignes totalement vides
        df.columns = df.columns.str.strip()
        
        # On remplace les cases vides restantes par du texte vide pour éviter l'affichage "NaN"
        df = df.fillna('')

        # 2. NETTOYAGE DE LA DATE
        df['Date'] = pd.to_datetime(df['Date']).dt.strftime('%d/%m/%Y')

        # 3. Préparation du tri
        df['Zone'] = df['Batiment'].map(ZONES).fillna('Autre')
        df['Heure_Tri'] = df['Heure'].astype(str).str.lower().str.strip().replace('libre', '23:59:00')
        
        df = df.sort_values(by=['Date', 'Zone', 'Heure_Tri'])
        
        # 4. ATTRIBUTION PAR ZONE
        agents_noms = ['Maria Claret', 'Celine', 'Maria Elisabeth']
        df['Group_ID'] = df['Date'].astype(str) + "_" + df['Zone']
        
        groupes_uniques = df['Group_ID'].unique()
        mapping_agent = {grp: agents_noms[i % len(agents_noms)] for i, grp in enumerate(groupes_uniques)}
        df['Agent_Attribue'] = df['Group_ID'].map(mapping_agent)

        # 5. SUGGESTION D'HORAIRE
        suggestions = []
        for i, row in df.iterrows():
            h_val = str(row['Heure']).lower().strip()
            if 'libre' in h_val or h_val == '':
                fixes = df[(df['Date'] == row['Date']) & 
                           (df['Agent_Attribue'] == row['Agent_Attribue']) & 
                           (~df['Heure'].astype(str).str.lower().str.contains('libre'))]
                
                if not fixes.empty:
                    try:
                        h_ref = pd.to_datetime(str(fixes.iloc[0]['Heure']), errors='coerce')
                        sugg = (h_ref + timedelta(hours=1, minutes=15)).strftime('%H:%M')
                        suggestions.append(f"Suggéré: {sugg}")
                    except:
                        suggestions.append("10:00 (Libre)")
                else:
                    suggestions.append("09:00 (Libre)")
            else:
                try:
                    # On affiche juste HH:MM sans les secondes
                    suggestions.append(pd.to_datetime(h_val).strftime('%H:%M'))
                except:
                    suggestions.append(h_val)

        df['Heure_Finale'] = suggestions

        # 6. AFFICHAGE FINAL SANS NAN
        st.success("✅ Planning propre (sans NaN) !")
        vue = df[['ID', 'Batiment', 'Date', 'Heure_Finale', 'Type', 'Agent_Attribue']]
        st.dataframe(vue.rename(columns={'Heure_Finale': 'Heure / Suggestion'}), use_container_width=True)
        
        # Export
        csv = vue.to_csv(index=False).encode('utf-8-sig')
        st.download_button("📥 Télécharger le planning final", csv, "planning_lausanne.csv", "text/csv")

    except Exception as e:
        st.error(f"Erreur : {e}")
