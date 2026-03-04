import streamlit as st
import pandas as pd
from datetime import datetime, timedelta

# 1. Configuration des Zones de Lausanne
ZONES = {
    'Bethusy A': 'Chailly', 'Bethusy B': 'Chailly',
    'Montolieu A': 'Montolieu', 'Montolieu B': 'Montolieu',
    'Montelieu A': 'Montolieu', 'Montelieu B': 'Montolieu',
    'Tunnel': 'Riponne', 'Oron': 'Oron'
}

st.set_page_config(page_title="Planning Lausanne", layout="wide")
st.title("📍 Planning : Attributions Unité Logement")

uploaded_file = st.file_uploader("Étape 1 : Glissez votre fichier Excel ici", type=['csv', 'xlsx'])

if uploaded_file:
    try:
        # Lecture
        df = pd.read_csv(uploaded_file) if uploaded_file.name.endswith('.csv') else pd.read_excel(uploaded_file, engine='openpyxl')
        
        # 2. Nettoyage
        df = df.dropna(how='all').fillna('')
        df.columns = df.columns.str.strip()

        # 3. Préparation (Dates et Zones)
        df['Date_Obj'] = pd.to_datetime(df['Date']) # On garde un objet date pour le filtre
        df['Date_Format'] = df['Date_Obj'].dt.strftime('%d/%m/%Y')
        df['Zone'] = df['Batiment'].map(ZONES).fillna('Autre')
        df['Heure_Tri'] = df['Heure'].astype(str).str.lower().str.strip().replace('libre', '23:59:00')
        
        df = df.sort_values(by=['Date_Obj', 'Zone', 'Heure_Tri'])
        
        # 4. Attribution des agents
        agents_noms = ['Maria Claret', 'Celine', 'Maria Elisabeth']
        df['Group_ID'] = df['Date_Format'] + "_" + df['Zone']
        groupes_uniques = df['Group_ID'].unique()
        mapping_agent = {grp: agents_noms[i % len(agents_noms)] for i, grp in enumerate(groupes_uniques)}
        df['Agent_Attribue'] = df['Group_ID'].map(mapping_agent)

        # 5. Logique Anti-Doublon
        suggestions = []
        derniere_heure_agent = {} 
        for i, row in df.iterrows():
            cle_agent = f"{row['Date_Format']}_{row['Agent_Attribue']}"
            h_brute = str(row['Heure']).lower().strip()
            if h_brute != 'libre' and h_brute != '':
                try:
                    h_dt = pd.to_datetime(h_brute)
                    derniere_heure_agent[cle_agent] = h_dt + timedelta(hours=1, minutes=15)
                    suggestions.append(h_dt.strftime('%H:%M'))
                except: suggestions.append(h_brute)
            else:
                if cle_agent in derniere_heure_agent:
                    nouvelle_h = derniere_heure_agent[cle_agent]
                    suggestions.append(f"Suggéré: {nouvelle_h.strftime('%H:%M')}")
                    derniere_heure_agent[cle_agent] = nouvelle_h + timedelta(hours=1, minutes=15)
                else:
                    suggestions.append("09:00 (Suggéré)")
                    derniere_heure_agent[cle_agent] = datetime.strptime("09:00", "%H:%M") + timedelta(hours=1, minutes=15)
        df['Heure_Finale'] = suggestions

        # --- ÉTAPE DE FILTRAGE PAR JOUR ---
        st.sidebar.header("Filtres")
        dates_disponibles = ["Toutes les dates"] + sorted(df['Date_Format'].unique().tolist())
        date_selectionnee = st.sidebar.selectbox("Choisir un jour précis :", dates_disponibles)

        # Filtrage du tableau
        if date_selectionnee != "Toutes les dates":
            df_affiche = df[df['Date_Format'] == date_selectionnee].copy()
        else:
            df_affiche = df.copy()

        # Nettoyage final des colonnes pour l'affichage
        df_final = df_affiche[['ID', 'Batiment', 'Date_Format', 'Heure_Finale', 'Type', 'Agent_Attribue']].copy()
        df_final = df_final.rename(columns={'Date_Format': 'Date', 'Heure_Finale': 'Heure / Suggestion'})

        # 6. Couleurs
        def color_agent(row):
            agent = row['Agent_Attribue']
            if agent == 'Maria Claret': return ['background-color: #ffdae0'] * len(row)
            elif agent == 'Celine': return ['background-color: #d1e9ff'] * len(row)
            elif agent == 'Maria Elisabeth': return ['background-color: #d4f8d4'] * len(row)
            return [''] * len(row)

        # 7. Affichage
        st.subheader(f"Planning : {date_selectionnee}")
        st.table(df_final.style.apply(color_agent, axis=1))
        
        # Export du planning affiché
        csv = df_final.to_csv(index=False).encode('utf-8-sig')
        st.download_button(f"📥 Télécharger le planning ({date_selectionnee})", csv, f"planning_{date_selectionnee.replace('/','-')}.csv", "text/csv")

    except Exception as e:
        st.error(f"Erreur : {e}")
