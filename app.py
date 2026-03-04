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
st.title("📍 Planning : Unité Logement (Zéro Conflit Garanti)")

# --- BARRE LATÉRALE ---
st.sidebar.header("⚙️ Configuration")
check_maria_c = st.sidebar.checkbox("Maria Claret", value=True)
check_celine = st.sidebar.checkbox("Celine", value=True)
check_maria_e = st.sidebar.checkbox("Maria Elisabeth", value=True)

agents_actifs = []
if check_maria_c: agents_actifs.append("Maria Claret")
if check_celine: agents_actifs.append("Celine")
if check_maria_e: agents_actifs.append("Maria Elisabeth")

uploaded_file = st.file_uploader("Étape 1 : Glissez votre fichier Excel ici", type=['csv', 'xlsx'])

if uploaded_file and agents_actifs:
    try:
        df = pd.read_csv(uploaded_file) if uploaded_file.name.endswith('.csv') else pd.read_excel(uploaded_file, engine='openpyxl')
        df = df.dropna(how='all').fillna('')
        df.columns = df.columns.str.strip()

        # 2. Préparation
        df['Date_Obj'] = pd.to_datetime(df['Date'])
        df['Date_F'] = df['Date_Obj'].dt.strftime('%d/%m/%Y')
        df['Zone_Affiche'] = df['Batiment'].map(ZONES).fillna('Autre')
        
        # Tri technique
        df['H_Tri'] = df['Heure'].astype(str).str.lower().str.strip().replace('libre', '00:00')
        df = df.sort_values(by=['Date_Obj', 'Zone_Affiche', 'H_Tri'])
        
        # 3. Attribution (Répartition par Zone)
        df['GID'] = df['Date_F'] + "_" + df['Zone_Affiche']
        grps = df['GID'].unique()
        map_agt = {g: agents_actifs[i % len(agents_actifs)] for i, g in enumerate(grps)}
        df['Agent_Attribue'] = df['GID'].map(map_agt)

        # 4. LOGIQUE DE CALCUL PAR AGENT (ISOLATION TOTALE)
        suggestions = []
        # On crée un dictionnaire pour stocker les temps de fin PAR AGENT
        # On utilise une clé "Date + Nom Complet" pour être certain de ne pas mélanger les Maria
        fin_vrai_agent = {} 
        zone_vrai_agent = {} 

        # On trie pour calculer le planning agent par agent
        df = df.sort_values(by=['Date_Obj', 'Agent_Attribue', 'H_Tri'])

        for i, row in df.iterrows():
            nom_complet = str(row['Agent_Attribue'])
            jour = str(row['Date_F'])
            # CLÉ UNIQUE : Jour + Identité complète
            identite_cle = f"{jour}_{nom_complet}" 
            
            h_in = str(row['Heure']).lower().strip()
            zone_actuelle = row['Zone_Affiche']
            duree_rdv = timedelta(hours=1, minutes=15)

            # Si c'est le premier rdv de la journée pour cet agent précis, on démarre à 08:00
            if identite_cle not in fin_vrai_agent:
                fin_vrai_agent[identite_cle] = datetime.strptime("08:00", "%H:%M")
                zone_vrai_agent[identite_cle] = zone_actuelle

            # Calcul du trajet (seulement si CET agent change de zone)
            if zone_actuelle != zone_vrai_agent[identite_cle]:
                fin_vrai_agent[identite_cle] += timedelta(minutes=30)
            
            zone_vrai_agent[identite_cle] = zone_actuelle

            if h_in != 'libre' and h_in != '':
                try:
                    h_dt = datetime.strptime(h_in[:5].replace('h', ':'), "%H:%M")
                    # CONFLIT uniquement si CET agent précis est déjà occupé par SA mission précédente
                    if h_dt < fin_vrai_agent[identite_cle] and fin_vrai_agent[identite_cle] > datetime.strptime("08:00", "%H:%M"):
                        suggestions.append(f"❌ CONFLIT: {h_dt.strftime('%H:%M')}")
                    else:
                        suggestions.append(h_dt.strftime('%H:%M'))
                    fin_vrai_agent[identite_cle] = h_dt + duree_rdv
                except:
                    suggestions.append(h_in)
            else:
                # Suggestion terrain
                h_s = fin_vrai_agent[identite_cle]
                if h_s + duree_rdv > datetime.strptime("12:00", "%H:%M") and h_s < datetime.strptime("13:00", "%H:%M"):
                    h_s = datetime.strptime("13:00", "%H:%M")
                
                if h_s > datetime.strptime("15:00", "%H:%M"):
                    suggestions.append("⚠️ Trop tard")
                else:
                    suggestions.append(f"Suggéré: {h_s.strftime('%H:%M')}")
                    fin_vrai_agent[identite_cle] = h_s + duree_rdv

        df['Heure_Finale'] = suggestions

        # 5. Affichage final
        dates = ["Toutes les dates"] + sorted(df['Date_F'].unique().tolist())
        sel_date = st.sidebar.selectbox("Choisir un jour :", dates)
        
        df_view = df[df['Date_F'] == sel_date].copy() if sel_date != "Toutes les dates" else df.copy()
        # On trie par agent pour que le tableau soit bien lisible
        df_view = df_view.sort_values(by=['Agent_Attribue', 'Heure_Finale'])
        
        df_final = df_view[['ID', 'Batiment', 'Date_F', 'Heure_Finale', 'Type', 'Agent_Attribue']]
        df_final = df_final.rename(columns={'Date_F': 'Date', 'Heure_Finale': 'Heure / Suggestion'})

        def apply_style(row):
            agt = str(row['Agent_Attribue'])
            # Couleurs par agent
            color = '#ffdae0' if agt == 'Maria Claret' else '#d1e9ff' if agt == 'Celine' else '#d4f8d4'
            styles = [f'background-color: {color}'] * len(row)
            if "❌" in str(row['Heure / Suggestion']):
                styles[3] = 'background-color: #ff4b4b; color: white; font-weight: bold'
            return styles

        st.table(df_final.style.apply(apply_style, axis=1))

    except Exception as e:
        st.error(f"Erreur technique : {e}")
