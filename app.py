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
st.title("📍 Planning : Unité Logement (Correction Totale)")

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
        df = pd.read_csv(uploaded_file) if uploaded_file.name.endswith('.csv') else pd.read_excel(uploaded_file, engine='openpyxl')
        df = df.dropna(how='all').fillna('')
        df.columns = df.columns.str.strip()

        # 2. Préparation des données
        df['Date_Obj'] = pd.to_datetime(df['Date'])
        df['Date_F'] = df['Date_Obj'].dt.strftime('%d/%m/%Y')
        df['Zone_Affiche'] = df['Batiment'].map(ZONES).fillna('Autre')
        
        # Tri pour l'attribution : Date -> Zone -> Heure (Libre en premier)
        df['H_Tri'] = df['Heure'].astype(str).str.lower().str.strip().replace('libre', '00:00')
        df = df.sort_values(by=['Date_Obj', 'Zone_Affiche', 'H_Tri'])
        
        # 3. Attribution (Répartition par Zone)
        df['GID'] = df['Date_F'] + "_" + df['Zone_Affiche']
        grps = df['GID'].unique()
        map_agt = {g: agents_actifs[i % len(agents_actifs)] for i, g in enumerate(grps)}
        df['Agent_Attribue'] = df['GID'].map(map_agt)

        # 4. LOGIQUE DE CALCUL INDIVIDUELLE (Correction du beug de conflit)
        # On trie pour calculer le planning agent par agent, jour par jour
        df = df.sort_values(by=['Date_Obj', 'Agent_Attribue', 'H_Tri'])
        
        suggestions = []
        # Dictionnaires de suivi STRICTEMENT INDIVIDUELS
        fin_par_cle = {} 
        zone_par_cle = {} 

        for i, row in df.iterrows():
            agent = row['Agent_Attribue']
            jour = row['Date_F']
            # La clé combine le jour ET l'agent pour isoler les plannings
            cle = f"{jour}_{agent}" 
            
            h_in = str(row['Heure']).lower().strip()
            zone_actuelle = row['Zone_Affiche']
            duree_rdv = timedelta(hours=1, minutes=15)

            # Initialisation au début de journée terrain (08:00)
            if cle not in fin_par_cle:
                fin_par_cle[cle] = datetime.strptime("08:00", "%H:%M")
                zone_par_cle[cle] = zone_actuelle

            # Gestion du trajet (+30 min si changement de zone pour CET agent)
            if zone_actuelle != zone_par_cle[cle]:
                fin_par_cle[cle] += timedelta(minutes=30)
            
            zone_par_cle[cle] = zone_actuelle

            if h_in != 'libre' and h_in != '':
                # HEURE FIXE
                try:
                    h_dt = datetime.strptime(h_in[:5].replace('h', ':'), "%H:%M")
                    # VRAI CONFLIT : L'agent est déjà occupé par sa mission précédente
                    if h_dt < fin_par_cle[cle] and fin_par_cle[cle] > datetime.strptime("08:00", "%H:%M"):
                        suggestions.append(f"❌ CONFLIT: {h_dt.strftime('%H:%M')}")
                    else:
                        suggestions.append(h_dt.strftime('%H:%M'))
                    # On met à jour son heure de fin
                    fin_par_cle[cle] = h_dt + duree_rdv
                except:
                    suggestions.append(h_in)
            else:
                # HEURE LIBRE (Suggestion)
                h_s = fin_par_cle[cle]
                # Pause de midi (12h-13h)
                if h_s + duree_rdv > datetime.strptime
