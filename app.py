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
st.title("📍 Planning : Unité Logement (Version 08:00 - 15:00)")

# --- BARRE LATÉRALE ---
st.sidebar.header("⚙️ Configuration")
check_maria_c = st.sidebar.checkbox("Maria Claret", value=True)
check_celine = st.sidebar.checkbox("Celine", value=True)
check_maria_e = st.sidebar.checkbox("Maria Elisabeth", value=True)

agents_actifs = []
if check_maria_c: agents_actifs.append("Maria Claret")
if check_celine: agents_actifs.append("Celine")
if check_maria_e: agents_actifs.append("Maria Elisabeth")

uploaded_file = st.file_uploader("Glissez votre fichier Excel ici", type=['csv', 'xlsx'])

if uploaded_file and agents_actifs:
    try:
        # Lecture
        df = pd.read_csv(uploaded_file) if uploaded_file.name.endswith('.csv') else pd.read_excel(uploaded_file, engine='openpyxl')
        df = df.dropna(how='all').fillna('')
        df.columns = df.columns.str.strip()

        # 2. Préparation
        df['Date_Obj'] = pd.to_datetime(df['Date'])
        df['Date_F'] = df['Date_Obj'].dt.strftime('%d/%m/%Y')
        df['Zone_Affiche'] = df['Batiment'].map(ZONES).fillna('Autre')
        
        # Tri initial
        df['H_Tri'] = df['Heure'].astype(str).str.lower().str.strip().replace('libre', '00:00')
        df = df.sort_values(by=['Date_Obj', 'Zone_Affiche', 'H_Tri'])
        
        # 3. Attribution des agents
        df['GID'] = df['Date_F'] + "_" + df['Zone_Affiche']
        grps = df['GID'].unique()
        map_agt = {g: agents_actifs[i % len(agents_actifs)] for i, g in enumerate(grps)}
        df['Agent_Attribue'] = df['GID'].map(map_agt)

        # 4. Logique de Calcul (Correction Syntaxique)
        df = df.sort_values(by=['Date_Obj', 'Agent_Attribue', 'H_Tri'])
        suggestions = []
        fin_par_cle = {} 
        zone_par_cle = {} 

        for i, row in df.iterrows():
            agent = row['Agent_Attribue']
            jour = row['Date_F']
            cle = f"{jour}_{agent}" 
            
            h_in = str(row['Heure']).lower().strip()
            zone_actuelle = row['Zone_Affiche']
            duree_rdv = timedelta(hours=1, minutes=15)

            if cle not in fin_par_cle:
                fin_par_cle[cle] = datetime.strptime("08:00", "%H:%M")
                zone_par_cle[cle] = zone_actuelle

            if zone_actuelle != zone_par_cle[cle]:
                fin_par_cle[cle] += timedelta(minutes=30)
            
            zone_par_cle[cle] = zone_actuelle

            if h_in != 'libre' and h_in != '':
                try:
                    h_dt = datetime.strptime(h_in[:5].replace('h', ':'), "%H:%M")
                    if h_dt < fin_par_cle[cle] and fin_par_cle[cle] > datetime.strptime("08:00", "%H:%M"):
                        suggestions.append(f"❌ CONFLIT: {h_dt.strftime('%H:%M')}")
                    else:
                        suggestions.append(h_dt.strftime('%H:%M'))
                    fin_par_cle[cle] = h_dt + duree_rdv
                except:
                    suggestions.append(h_in)
            else:
                h_s = fin_par_cle[cle]
                # PAUSE MIDI (Correction de la ligne qui buggait)
                if h_s + duree_rdv > datetime.strptime("12:00", "%H:%M") and h_s < datetime.strptime("13:00", "%H:%M"):
                    h_s = datetime.strptime("13:00", "%H:%M")
                
                if h_s > datetime.strptime("15:00", "%H:%M"):
                    suggestions.append("⚠️ Trop tard")
                else:
                    suggestions.append(f"Suggéré: {h_s.strftime('%H:%M')}")
                    fin_par_cle[cle] = h_s + duree_rdv

        df['Heure_Finale'] = suggestions

        # 5. Affichage
        dates = ["Toutes les dates"] + sorted(df['Date_F'].unique().tolist())
        sel_date = st.sidebar.selectbox("Choisir un jour :", dates)
        
        df_view = df[df['Date_F'] == sel_date].copy() if sel_date != "Toutes les dates" else df.copy()
        df_final = df_view[['ID', 'Batiment', 'Date_F', 'Heure_Finale', 'Type', 'Agent_Attribue']]
        df_final = df_final.rename(columns={'Date_F': 'Date', 'Heure_Finale': 'Heure/Suggestion'})

        def apply_style(row):
            agt = row['Agent_Attribue']
            color = '#ffdae0' if agt == 'Maria Claret' else '#d1e9ff' if agt == 'Celine' else '#d4f8d4'
            styles = [f'background-color: {color}'] * len(row)
            if "❌" in str(row['Heure/Suggestion']):
                styles[3] = 'background-color: #ff4b4b; color: white; font-weight: bold'
            return styles

        st.table(df_final.style.apply(apply_style, axis=1))

    except Exception as e:
        st.error(f"Erreur technique : {e}")
elif not agents_actifs:
    st.warning("Veuillez sélectionner au moins un agent à gauche.")
