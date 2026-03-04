import streamlit as st
import pandas as pd
from datetime import datetime, timedelta

# 1. Configuration des Zones et Adresses pour trajet réel
# Lausanne (Centre) <-> Oron = ~30 min | Inter-Lausanne = ~15 min
ZONES = {
    'Bethusy A': 'Chailly', 'Bethusy B': 'Chailly',
    'Montolieu A': 'Montolieu', 'Montolieu B': 'Montolieu',
    'Montelieu A': 'Montolieu', 'Montelieu B': 'Montolieu',
    'Tunnel': 'Riponne', 'Oron': 'Oron'
}

def calculer_temps_trajet(zone_dep, zone_arr):
    if zone_dep == zone_arr:
        return 10  # 10 min de battement si on reste dans le même bâtiment/quartier
    if "Oron" in [zone_dep, zone_arr]:
        return 35  # 35 min pour aller ou revenir d'Oron
    return 20      # 20 min pour circuler entre deux zones de Lausanne

st.set_page_config(page_title="Planning Lausanne Pro - Expert", layout="wide")
st.title("📍 Planning : Unité Logement (Performance & Trajets)")

# --- BARRE LATÉRALE ---
st.sidebar.header("⚙️ Configuration")
check_mc = st.sidebar.checkbox("Maria Claret", value=True)
check_ce = st.sidebar.checkbox("Celine", value=True)
check_me = st.sidebar.checkbox("Maria Elisabeth", value=True)

agents_actifs = []
if check_mc: agents_actifs.append("Maria Claret")
if check_ce: agents_actifs.append("Celine")
if check_me: agents_actifs.append("Maria Elisabeth")

uploaded_file = st.file_uploader("Étape 1 : Glissez votre fichier Excel ici", type=['csv', 'xlsx'])

if uploaded_file and agents_actifs:
    try:
        # Lecture et nettoyage des noms de colonnes
        df = pd.read_csv(uploaded_file) if uploaded_file.name.endswith('.csv') else pd.read_excel(uploaded_file)
        df.columns = df.columns.str.strip()
        df = df.dropna(how='all').fillna('')

        # Détection automatique de la colonne Date
        col_date = next((c for c in df.columns if 'date' in c.lower()), None)
        
        if not col_date:
            st.error("⚠️ La colonne 'Date' est introuvable. Vérifiez votre fichier Excel.")
        else:
            # 2. Préparation des dates et zones
            df['Date_Obj'] = pd.to_datetime(df[col_date])
            df['Date_F'] = df['Date_Obj'].dt.strftime('%d/%m/%Y')
            df['Zone_Affiche'] = df['Batiment'].map(ZONES).fillna('Autre')
            
            # Tri pour calcul : Date -> Zone -> Heure
            df['H_Tri'] = df['Heure'].astype(str).str.lower().str.strip().replace('libre', '00:00')
            df = df.sort_values(by=['Date_Obj', 'Zone_Affiche', 'H_Tri'])
            
            # 3. Attribution des agents par zone
            df['GID'] = df['Date_F'] + "_" + df['Zone_Affiche']
            grps = df['GID'].unique()
            map_agt = {g: agents_actifs[i % len(agents_actifs)] for i, g in enumerate(grps)}
            df['Agent_Attribue'] = df['GID'].map(map_agt)

            # 4. LOGIQUE DE CALCUL (Trajet Réel + Terrain 08h-15h)
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
                duree_rdv = timedelta(hours=1, minutes=15) # 1h rdv + 15 min admin

                # Initialisation (Début à 06h30, mais terrain à 08h00)
                if cle not in fin_par_cle:
                    fin_par_cle[cle] = datetime.strptime("08:00", "%H:%M")
                    zone_par_cle[cle] = zone_actuelle

                # CALCUL DU TRAJET RÉEL
                temps_route = calculer_temps_trajet(zone_par_cle[cle], zone_actuelle)
                fin_par_cle[cle] += timedelta(minutes=temps_route)
                
                zone_par_cle[cle] = zone_actuelle

                if h_in != 'libre' and h_in != '':
                    try:
                        h_dt = datetime.strptime(h_in[:5].replace('h', ':'), "%H:%M")
                        if h_dt < fin_par_cle[cle]:
                            suggestions.append(f"❌ CONFLIT: Trajet insuffisant ({h_dt.strftime('%H:%M')})")
                        else:
                            suggestions.append(h_dt.strftime('%H:%M'))
                        fin_par_cle[cle] = h_dt + duree_rdv
                    except: suggestions.append(h_in)
                else:
                    h_s = fin_par_cle[cle]
                    if h_s + duree_rdv > datetime.strptime("12:00", "%H:%M") and h_s < datetime.strptime("13:00", "%H:%M"):
                        h_s = datetime.strptime("13:00", "%H:%M")
                    
                    if h_s > datetime.strptime("15:00", "%H:%M"):
                        suggestions.append("⚠️ Trop tard")
                    else:
                        suggestions.append(f"Suggéré: {h_s.strftime('%H:%M')}")
                        fin_par_cle[cle] = h_s + duree_rdv

            df['Résultat'] = suggestions

            # 5. Affichage final
            dates_dispo = sorted(df['Date_F'].unique())
            sel_date = st.sidebar.selectbox("Choisir une date :", dates_dispo)
            
            st.subheader(f"Planning du {sel_date}")
            df_view = df[df['Date_F'] == sel_date][['ID', 'Batiment', 'Agent_Attribue', 'Résultat', 'Type']]
            
            def style_agt(row):
                color = '#ffdae0' if row['Agent_Attribue'] == 'Maria Claret' else '#d1e9ff' if row['Agent_Attribue'] == 'Celine' else '#d4f8d4'
                styles = [f'background-color: {color}'] * len(row)
                if "❌" in str(row['Résultat']):
                    styles[3] = 'background-color: #ff4b4b; color: white; font-weight: bold'
                return styles

            st.table(df_view.style.apply(style_agt, axis=1))

    except Exception as e:
        st.error(f"Une erreur est survenue : {e}")
