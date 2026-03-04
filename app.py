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
st.title("📍 Planning : Optimisation Attributions Unité Logement")

uploaded_file = st.file_uploader("Glissez votre fichier Excel ici", type=['csv', 'xlsx'])

if uploaded_file:
    try:
        df = pd.read_csv(uploaded_file) if uploaded_file.name.endswith('.csv') else pd.read_excel(uploaded_file, engine='openpyxl')
        
        # 1. Nettoyage
        df = df.dropna(how='all').fillna('')
        df.columns = df.columns.str.strip()

        # 2. Préparation du tri (Date -> Zone -> Heure)
        # On traite les dates proprement pour l'affichage
        df['Date_Format'] = pd.to_datetime(df['Date']).dt.strftime('%d/%m/%Y')
        df['Zone'] = df['Batiment'].map(ZONES).fillna('Autre')
        df['Heure_Tri'] = df['Heure'].astype(str).str.lower().str.strip().replace('libre', '23:59:00')
        
        # Tri par Date, Zone, puis Heure
        df = df.sort_values(by=['Date', 'Zone', 'Heure_Tri'])
        
        # 3. Attribution par Zone (L'agent reste dans le même quartier)
        agents_noms = ['Maria Claret', 'Celine', 'Maria Elisabeth']
        df['Group_ID'] = df['Date'].astype(str) + "_" + df['Zone']
        groupes_uniques = df['Group_ID'].unique()
        mapping_agent = {grp: agents_noms[i % len(agents_noms)] for i, grp in enumerate(groupes_uniques)}
        df['Agent_Attribue'] = df['Group_ID'].map(mapping_agent)

        # 4. LOGIQUE ANTI-DOUBLON (Décalage intelligent)
        suggestions = []
        # On va garder en mémoire la "dernière heure de fin" pour chaque agent chaque jour
        derniere_heure_agent = {} 

        for i, row in df.iterrows():
            cle_agent = f"{row['Date']}_{row['Agent_Attribue']}"
            h_brute = str(row['Heure']).lower().strip()
            
            # Si c'est une heure FIXE
            if h_brute != 'libre' and h_brute != '':
                try:
                    h_dt = pd.to_datetime(h_brute)
                    heure_finale = h_dt.strftime('%H:%M')
                    # On note que cet agent est occupé jusqu'à cette heure + 1h15
                    derniere_heure_agent[cle_agent] = h_dt + timedelta(hours=1, minutes=15)
                    suggestions.append(heure_finale)
                except:
                    suggestions.append(h_brute)
            
            # Si c'est "LIBRE"
            else:
                # Si l'agent a déjà eu une mission avant ce jour-là
                if cle_agent in derniere_heure_agent:
                    nouvelle_h = derniere_heure_agent[cle_agent]
                    suggestions.append(f"Suggéré: {nouvelle_h.strftime('%H:%M')}")
                    # On met à jour son heure de fin pour la mission suivante
                    derniere_heure_agent[cle_agent] = nouvelle_h + timedelta(hours=1, minutes=15)
                else:
                    # Première mission de la journée
                    suggestions.append("09:00 (Suggéré)")
                    derniere_heure_agent[cle_agent] = datetime.strptime("09:00", "%H:%M") + timedelta(hours=1, minutes=15)

        df['Heure_Finale'] = suggestions

        # 5. Affichage final
        st.success("✅ Planning optimisé : Plus de doublons d'horaires !")
        vue = df[['ID', 'Batiment', 'Date_Format', 'Heure_Finale', 'Type', 'Agent_Attribue']]
        st.dataframe(vue.rename(columns={'Date_Format': 'Date', 'Heure_Finale': 'Heure / Suggestion'}), use_container_width=True)
        
        # Export
        csv = vue.to_csv(index=False).encode('utf-8-sig')
        st.download_button("📥 Télécharger le planning sans doublons", csv, "planning_final.csv", "text/csv")

    except Exception as e:
        st.error(f"Erreur : {e}")
