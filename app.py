import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import io

# --- CONFIGURATION FIXE ---
BUREAU = "18 Mon Repos, 1005 Lausanne"
AGENTS = ["Celine", "Maria Claret", "Maria Elisabeth"]
INFOS_BATIMENTS = {
    'Bethusy A': 'Avenue de Béthusy 54, Lausanne',
    'Bethusy B': 'Avenue de Béthusy 56, Lausanne',
    'Montolieu A': 'Isabelle-de-Montolieu 90, Lausanne',
    'Montolieu B': 'Isabelle-de-Montolieu 92, Lausanne',
    'Tunnel': 'Rue du Tunnel 17, Lausanne',
    'Oron': "Route d'Oron 77, 1010 Lausanne"
}
COULEURS = {"Celine": "#d1e9ff", "Maria Claret": "#ffdae0", "Maria Elisabeth": "#d4f8d4", "À définir": "#eeeeee"}

st.set_page_config(page_title="Unité Logement - Optimiseur Pro", layout="wide")

if 'db' not in st.session_state:
    st.session_state.db = pd.DataFrame(columns=['Batiment', 'Date', 'Heure', 'Agent', 'Rue', 'Type', 'Date_Sort'])
if 'conges' not in st.session_state:
    st.session_state.conges = pd.DataFrame(columns=['Agent', 'Date_Debut', 'Date_Fin'])

# --- LOGIQUE D'ATTRIBUTION RÉELLEMENT OPTIMISÉE ---

def planifier_missions(df_import):
    temp_results = []
    
    # 1. On identifie les colonnes
    c_date = next((c for c in df_import.columns if 'date' in c.lower()), 'Date')
    c_type = next((c for c in df_import.columns if 'type' in c.lower()), 'Type')
    c_bat = 'Batiment'
    
    # 2. On traite jour par jour
    dates_uniques = sorted(pd.to_datetime(df_import[c_date]).unique())
    
    for d in dates_uniques:
        ds_str = pd.to_datetime(d).strftime('%d/%m/%Y')
        presents = [a for a in AGENTS if est_disponible(a, ds_str)]
        
        if not presents:
            continue
            
        # Missions du jour groupées par Bâtiment pour les garder ensemble !
        missions_jour = df_import[pd.to_datetime(df_import[c_date]) == d]
        
        # On trie les bâtiments par nombre de missions (le plus gros bloc en premier)
        blocs_batiment = missions_jour.groupby(c_bat)
        
        # État des agents pour ce jour
        planning_jour = {a: {"heure_libre": datetime.strptime("08:15", "%H:%M"), "missions": 0, "last_bat": None} for a in presents}

        for batiment, groupe in blocs_batiment:
            # A quel agent donner ce bloc ? 
            # On cherche celui qui a le moins de missions pour équilibrer
            agt_elu = min(planning_jour, key=lambda x: planning_jour[x]['missions'])
            rue = INFOS_BATIMENTS.get(batiment, "Autre")
            
            for _, row in groupe.iterrows():
                h_debut = planning_jour[agt_elu]['heure_libre']
                
                # Si l'agent change de bâtiment, on ajoute du trajet (30min), sinon juste 5min
                battement = 5 if planning_jour[agt_elu]['last_bat'] == batiment else 25
                
                # Fin de la mission précédente + battement + 60min de mission
                prochain_creneau = h_debut + timedelta(minutes=battement)
                
                # Pause de midi
                if prochain_creneau.hour == 12:
                    prochain_creneau = prochain_creneau.replace(hour=13, minute=0)
                
                if prochain_creneau.hour >= 16:
                    # Si l'agent est plein, on essaie un autre agent pour ce bloc
                    autres = [a for a in presents if a != agt_elu]
                    if autres:
                        agt_elu = min(autres, key=lambda x: planning_jour[x]['missions'])
                        prochain_creneau = planning_jour[agt_elu]['heure_libre'] + timedelta(minutes=25)

                temp_results.append({
                    'Batiment': batiment,
                    'Date': ds_str,
                    'Heure': prochain_creneau.strftime("%H:%M"),
                    'Agent': agt_elu,
                    'Type': row[c_type],
                    'Rue': rue,
                    'Date_Sort': d
                })
                
                # Mise à jour de l'état de l'agent
                planning_jour[agt_elu]['heure_libre'] = prochain_creneau + timedelta(minutes=60)
                planning_jour[agt_elu]['missions'] += 1
                planning_jour[agt_elu]['last_bat'] = batiment

    return pd.DataFrame(temp_results)

def est_disponible(agent, date_str):
    if st.session_state.conges.empty: return True
    dt_cible = pd.to_datetime(date_str, dayfirst=True)
    for _, c in st.session_state.conges[st.session_state.conges['Agent'] == agent].iterrows():
        if pd.to_datetime(c['Date_Debut'], dayfirst=True) <= dt_cible <= pd.to_datetime(c['Date_Fin'], dayfirst=True): 
            return False
    return True

# --- INTERFACE ---
st.sidebar.header("⚙️ Contrôle")
up = st.sidebar.file_uploader("Charger Excel", type=['xlsx'])

if up and st.sidebar.button("🚀 Optimiser le Planning"):
    df_raw = pd.read_excel(up).dropna(how='all').fillna('')
    st.session_state.db = planifier_missions(df_raw)
    st.rerun()

if st.sidebar.button("🗑️ Reset"):
    st.session_state.db = pd.DataFrame(columns=['Batiment', 'Date', 'Heure', 'Agent', 'Rue', 'Type', 'Date_Sort'])
    st.rerun()

st.title("📍 Planning Expert Logement")

if not st.session_state.db.empty:
    t1, t2 = st.tabs(["📋 Liste Complète", "👤 Par Agent"])
    
    with t1:
        df_display = st.session_state.db.sort_values(['Date_Sort', 'Heure'])
        st.table(df_display[['Date', 'Heure', 'Agent', 'Batiment', 'Type']].style.apply(
            lambda r: [f'background-color: {COULEURS.get(r["Agent"])}']*5, axis=1))
        
        # Export Excel
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            df_display.to_excel(writer, index=False, sheet_name='Planning')
        st.download_button("📥 Télécharger Excel", data=output.getvalue(), file_name="planning_optimise.xlsx")

    with t2:
        dates = sorted(st.session_state.db['Date'].unique())
        choix_date = st.selectbox("Choisir un jour", dates)
        cols = st.columns(3)
        for i, agt in enumerate(AGENTS):
            with cols[i]:
                st.subheader(agt)
                m = st.session_state.db[(st.session_state.db['Date'] == choix_date) & (st.session_state.db['Agent'] == agt)]
                if m.empty: st.write("Libre")
                for _, r in m.sort_values('Heure').iterrows():
                    st.info(f"**{r['Heure']}** : {r['Batiment']}\n({r['Type']})")
else:
    st.info("Veuillez charger un fichier Excel dans la barre latérale pour commencer.")
