import streamlit as st
import pandas as pd
from datetime import datetime, timedelta

# 1. Configuration des Zones
ZONES = {
    'Bethusy A': 'Chailly', 'Bethusy B': 'Chailly',
    'Montolieu A': 'Montolieu', 'Montolieu B': 'Montolieu',
    'Montelieu A': 'Montolieu', 'Montelieu B': 'Montolieu',
    'Tunnel': 'Riponne', 'Oron': 'Oron'
}

st.set_page_config(page_title="Planning Lausanne Pro", layout="wide")
st.title("📍 Planning : Unité Logement (Priorité Matin)")

uploaded_file = st.file_uploader("Étape 1 : Glissez votre fichier Excel ici", type=['csv', 'xlsx'])

if uploaded_file:
    try:
        df = pd.read_csv(uploaded_file) if uploaded_file.name.endswith('.csv') else pd.read_excel(uploaded_file, engine='openpyxl')
        df = df.dropna(how='all').fillna('')
        df.columns = df.columns.str.strip()

        # 3. Préparation
        df['Date_Obj'] = pd.to_datetime(df['Date'])
        df['Date_Format'] = df['Date_Obj'].dt.strftime('%d/%m/%Y')
        df['Zone'] = df['Batiment'].map(ZONES).fillna('Autre')
        
        # MODIFICATION DU TRI : On met "libre" en PREMIER (00:00) pour qu'ils soient planifiés dès 08:00
        df['Heure_Tri'] = df['Heure'].astype(str).str.lower().str.strip().replace('libre', '00:00:00')
        
        # Tri : Date -> Zone -> Heure_Tri
        df = df.sort_values(by=['Date_Obj', 'Zone', 'Heure_Tri'])
        
        # 4. Attribution des agents
        agents_noms = ['Maria Claret', 'Celine', 'Maria Elisabeth']
        df['Group_ID'] = df['Date_Format'] + "_" + df['Zone']
        groupes_uniques = df['Group_ID'].unique()
        mapping_agent = {grp: agents_noms[i % len(agents_noms)] for i, grp in enumerate(groupes_uniques)}
        df['Agent_Attribue'] = df['Group_ID'].map(mapping_agent)

        # 5. LOGIQUE HORAIRES (Start 08:00 | Max Départ 15:00)
        suggestions = []
        fin_mission_agent = {} 

        for i, row in df.iterrows():
            cle_agent = f"{row['Date_Format']}_{row['Agent_Attribue']}"
            h_brute = str(row['Heure']).lower().strip()
            duree = timedelta(hours=1, minutes=15)

            if cle_agent not in fin_mission_agent:
                fin_mission_agent[cle_agent] = datetime.strptime("08:00", "%H:%M")

            if h_brute != 'libre' and h_brute != '':
                # HEURE FIXE
                try:
                    h_fixe = datetime.strptime(h_brute[:5].replace('h', ':'), "%H:%M")
                    # Si l'heure fixe arrive avant la fin de la mission précédente, on alerte
                    suggestions.append(h_fixe.strftime('%H:%M'))
                    fin_mission_agent[cle_agent] = h_fixe + duree
                except:
                    suggestions.append(h_brute)
            else:
                # HEURE LIBRE -> Priorité Matin
                h_start = fin_mission_agent[cle_agent]
                
                # Gestion pause midi
                if h_start + duree > datetime.strptime("12:00", "%H:%M") and h_start < datetime.strptime("13:00", "%H:%M"):
                    h_start = datetime.strptime("13:00", "%H:%M")
                
                if h_start > datetime.strptime("15:00", "%H:%M"):
                    suggestions.append("⚠️ Trop tard (Max 15h)")
                else:
                    suggestions.append(f"Suggéré: {h_start.strftime('%H:%M')}")
                    fin_mission_agent[cle_agent] = h_start + duree

        df['Heure_Finale'] = suggestions

        # --- AFFICHAGE ---
        st.sidebar.header("Filtres")
        dates_disponibles = ["Toutes les dates"] + sorted(df['Date_Format'].unique().tolist())
        date_selectionnee = st.sidebar.selectbox("Choisir un jour :", dates_disponibles)
        df_affiche = df[df['Date_Format'] == date_selectionnee].copy() if date_selectionnee != "Toutes les dates" else df.copy()

        df_final = df_affiche[['ID', 'Batiment', 'Date_Format', 'Heure_Finale', 'Type', 'Agent_Attribue']]
        df_final = df_final.rename(columns={'Date_Format': 'Date', 'Heure_Finale': 'Heure / Suggestion'})

        def color_agent(row):
            agent = row['Agent_Attribue']
            if agent == 'Maria Claret': return ['background-color: #ffdae0'] * len(row)
            elif agent == 'Celine': return ['background-color: #d1e9ff'] * len(row)
            elif agent == 'Maria Elisabeth': return ['background-color: #d4f8d4'] * len(row)
            return [''] * len(row)

        st.table(df_final.style.apply(color_agent, axis=1))
        
    except Exception as e:
        st.error(f"Erreur : {e}")
