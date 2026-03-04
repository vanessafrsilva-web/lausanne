import streamlit as st
import pandas as pd
from datetime import datetime, timedelta

# 1. Base de données des adresses (pour le calcul réel)
ADRESSES_BATIMENTS = {
    'Tunnel': 'Rue du Tunnel 1, 1005 Lausanne',
    'Bethusy A': 'Avenue de Bethusy 54, 1012 Lausanne',
    'Bethusy B': 'Avenue de Bethusy 56, 1012 Lausanne',
    'Montolieu A': 'Chemin de Montolieu 2, 1010 Lausanne',
    'Montolieu B': 'Chemin de Montolieu 4, 1010 Lausanne',
    'Oron': 'Route de Lausanne, 1610 Oron-la-Ville',
    'Riponne': 'Place de la Riponne, 1005 Lausanne'
}

# Fonction de simulation de trajet (vitesse moyenne + distance)
# Note : Peut être remplacé par un appel direct à Google Maps API
def calculer_trajet_reel(dep_bat, arr_bat):
    if dep_bat == arr_bat:
        return 5  # 5 min pour changer d'étage ou de porte
    
    # Logique simplifiée pour l'exemple (Lausanne -> Oron est plus long)
    if "Oron" in [dep_bat, arr_bat]:
        return 25  # 25 minutes pour Oron
    return 15      # 15 minutes en moyenne dans Lausanne

st.set_page_config(page_title="Planning Lausanne Pro - GPS", layout="wide")
st.title("📍 Planning avec Temps de Trajet Réel")

# --- BARRE LATÉRALE ---
st.sidebar.header("⚙️ Agents Actifs")
agents_actifs = []
if st.sidebar.checkbox("Maria Claret", value=True): agents_actifs.append("Maria Claret")
if st.sidebar.checkbox("Celine", value=True): agents_actifs.append("Celine")
if st.sidebar.checkbox("Maria Elisabeth", value=True): agents_actifs.append("Maria Elisabeth")

uploaded_file = st.file_uploader("Glissez le fichier Excel", type=['csv', 'xlsx'])

if uploaded_file and agents_actifs:
    try:
        df = pd.read_csv(uploaded_file) if uploaded_file.name.endswith('.csv') else pd.read_excel(uploaded_file)
        df = df.dropna(how='all').fillna('')
        
        # Préparation
        df['Date_Obj'] = pd.to_datetime(df['Date'])
        df['Date_F'] = df['Date_Obj'].dt.strftime('%d/%m/%Y')
        
        # Attribution simplifiée par zone
        df = df.sort_values(by=['Date_Obj', 'Batiment'])
        zones = df['Batiment'].unique()
        map_agt = {z: agents_actifs[i % len(agents_actifs)] for i, z in enumerate(zones)}
        df['Agent_Attribue'] = df['Batiment'].map(map_agt)

        # --- CALCUL AVEC TRAJET RÉEL ---
        df = df.sort_values(by=['Date_Obj', 'Agent_Attribue', 'Heure'])
        suggestions = []
        fin_par_agent = {}
        dernier_bat_par_agent = {}

        for i, row in df.iterrows():
            agent = row['Agent_Attribue']
            jour = row['Date_F']
            cle = f"{jour}_{agent}"
            bat_actuel = row['Batiment']
            
            # Initialisation
            if cle not in fin_par_agent:
                fin_par_agent[cle] = datetime.strptime("08:00", "%H:%M")
                dernier_bat_par_agent[cle] = bat_actuel

            # CALCUL DU TRAJET RÉEL
            temps_route = calculer_trajet_reel(dernier_bat_par_agent[cle], bat_actuel)
            fin_par_agent[cle] += timedelta(minutes=temps_route)
            
            h_in = str(row['Heure']).lower().strip()
            duree_mission = timedelta(hours=1, minutes=15)

            if h_in != 'libre' and h_in != '':
                try:
                    h_dt = datetime.strptime(h_in[:5].replace('h', ':'), "%H:%M")
                    if h_dt < fin_par_agent[cle]:
                        suggestions.append(f"❌ CONFLIT: Trajet de {temps_route}min insuffisant")
                    else:
                        suggestions.append(h_dt.strftime('%H:%M'))
                    fin_par_agent[cle] = h_dt + duree_mission
                except: suggestions.append(h_in)
            else:
                h_s = fin_par_agent[cle]
                suggestions.append(f"Suggéré: {h_s.strftime('%H:%M')} (+{temps_route}m trajet)")
                fin_par_agent[cle] = h_s + duree_mission
            
            dernier_bat_par_agent[cle] = bat_actuel

        df['Résultat'] = suggestions
        st.table(df[['Batiment', 'Date_F', 'Agent_Attribue', 'Résultat']])

    except Exception as e:
        st.error(f"Erreur : {e}")
