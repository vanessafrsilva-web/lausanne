import streamlit as st
import pandas as pd
from datetime import datetime, timedelta

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

st.set_page_config(page_title="Unité Logement - Planning Expert v2", layout="wide")

if 'db' not in st.session_state:
    st.session_state.db = pd.DataFrame(columns=['Batiment', 'Date', 'Heure', 'Agent', 'Rue', 'Type', 'Date_Sort'])
if 'conges' not in st.session_state:
    st.session_state.conges = pd.DataFrame(columns=['Agent', 'Date_Debut', 'Date_Fin'])

# --- FONCTIONS LOGIQUES OPTIMISÉES ---

def est_disponible(agent, date_str):
    if st.session_state.conges.empty: return True
    try:
        dt_cible = pd.to_datetime(date_str, dayfirst=True)
        for _, c in st.session_state.conges[st.session_state.conges['Agent'] == agent].iterrows():
            if pd.to_datetime(c['Date_Debut'], dayfirst=True) <= dt_cible <= pd.to_datetime(c['Date_Fin'], dayfirst=True): 
                return False
    except: pass
    return True

def calculer_creneau_securise(agent, date_str, temp_db, batiment_cible):
    m_jour = temp_db[(temp_db['Date'] == date_str) & (temp_db['Agent'] == agent)]
    if m_jour.empty: 
        return "08:15", True
    
    derniere_m = m_jour.iloc[-1]
    derniere_h_str = str(derniere_m['Heure']).strip()
    derniere_rue = derniere_m['Rue']
    rue_cible = INFOS_BATIMENTS.get(batiment_cible, "Autre")

    try:
        h_obj = datetime.strptime(derniere_h_str, "%H:%M")
        
        # OPTIMISATION : Si même adresse, trajet = 5min. Sinon 30min de battement (trajet + marge)
        delai = 65 if derniere_rue == rue_cible else 80 
        prochaine_h = h_obj + timedelta(minutes=delai)
        
        # Gestion Pause déjeuner (12h-13h)
        if datetime.strptime("12:00", "%H:%M") <= prochaine_h < datetime.strptime("13:00", "%H:%M"):
            prochaine_h = datetime.strptime("13:00", "%H:%M")
            
        # Sécurité : Pas de RDV débutant après 16h15
        if prochaine_h > datetime.strptime("16:15", "%H:%M"):
            return "COMPLET", False
            
        return prochaine_h.strftime("%H:%M"), True
    except:
        return "08:15", True

# --- INTERFACE ---
st.title("📍 Unité Logement : Planning Optimisé")
t1, t2, t3 = st.tabs(["📝 Planning Global", "📅 Vue par Agent", "📊 Performance & Trajets"])

with st.sidebar:
    st.header("🌴 Congés / Absences")
    abs_agt = st.selectbox("Agent", AGENTS)
    d1, d2 = st.date_input("Du"), st.date_input("Au")
    if st.button("Valider Congé"):
        st.session_state.conges = pd.concat([st.session_state.conges, pd.DataFrame([{'Agent': abs_agt, 'Date_Debut': d1.strftime('%d/%m/%Y'), 'Date_Fin': d2.strftime('%d/%m/%Y')}])], ignore_index=True)
        st.success(f"Absence enregistrée pour {abs_agt}")

    st.divider()
    st.header("📂 Importation")
    up = st.file_uploader("Fichier Excel des missions", type=['xlsx'])
    
    if up and st.button("🚀 Lancer l'Attribution IA"):
        df_ex = pd.read_excel(up).dropna(how='all').fillna('')
        df_ex.columns = df_ex.columns.str.strip()
        
        c_date = next((c for c in df_ex.columns if 'date' in c.lower()), 'Date')
        c_heure = next((c for c in df_ex.columns if 'heure' in c.lower()), 'Heure')
        c_type = next((c for c in df_ex.columns if 'type' in c.lower()), 'Type')

        temp = pd.DataFrame(columns=['Batiment', 'Date', 'Heure', 'Agent', 'Rue', 'Type', 'Date_Sort'])
        
        # Tri par date pour une planification séquentielle
        for _, row in df_ex.sort_values(by=[c_date]).iterrows():
            ds = pd.to_datetime(row[c_date]).strftime('%d/%m/%Y')
            rue_demandee = INFOS_BATIMENTS.get(row['Batiment'], "Autre")
            
            presents = [a for a in AGENTS if est_disponible(a, ds)]
            agt_elu, h_finale = "À définir", "08:15"
            
            if presents:
                # STRATÉGIE : Calcul d'un score de proximité (0 = déjà sur place, 1 = libre, 2 = ailleurs)
                scores = {}
                for p in presents:
                    missions_agent = temp[(temp['Date'] == ds) & (temp['Agent'] == p)]
                    if missions_agent.empty:
                        scores[p] = 1 # Priorité neutre
                    else:
                        derniere_loc = missions_agent.iloc[-1]['Rue']
                        scores[p] = 0 if derniere_loc == rue_demandee else 2
                
                # Tri : Proximité d'abord, puis équité (nombre de missions déjà affectées)
                presents_tries = sorted(presents, key=lambda x: (scores[x], len(temp[(temp['Date'] == ds) & (temp['Agent'] == x)])))
                
                for p in presents_tries:
                    heure_suggere, possible = calculer_creneau_securise(p, ds, temp, row['Batiment'])
                    if possible:
                        agt_elu, h_finale = p, heure_suggere
                        break
            
            # Forçage manuel de l'heure si spécifiée dans l'Excel
            h_val = str(row[c_heure]).strip()
            if h_val not in ["", "nan", "00:00:00", "libre"]: h_finale = h_val[:5]

            temp = pd.concat([temp, pd.DataFrame([{
                'Batiment': row['Batiment'], 'Date': ds, 'Heure': h_finale, 'Agent': agt_elu, 
                'Type': row[c_type], 'Rue': rue_demandee, 
                'Date_Sort': pd.to_datetime(row[c_date])
            }])], ignore_index=True)
            
        st.session_state.db = temp
        st.rerun()

    if st.button("🗑️ Reset Complet"):
        st.session_state.db = pd.DataFrame(columns=['Batiment', 'Date', 'Heure', 'Agent', 'Rue', 'Type', 'Date_Sort'])
        st.rerun()

# --- ONGLETS ---
with t1:
    if not st.session_state.db.empty:
        df_v = st.session_state.db.sort_values(['Date_Sort', 'Heure'])
        st.dataframe(
            df_v[['Date', 'Heure', 'Agent', 'Batiment', 'Type', 'Rue']].style.apply(
                lambda r: [f'background-color: {COULEURS.get(r["Agent"])}']*6, axis=1
            ), use_container_width=True, height=600
        )

with t2:
    if not st.session_state.db.empty:
        sel_j = st.selectbox("Sélectionner une date :", sorted(st.session_state.db['Date'].unique()))
        cols = st.columns(len(AGENTS))
        for i, a in enumerate(AGENTS):
            with cols[i]:
                st.markdown(f"<div style='text-align:center; background-color:{COULEURS[a]}; padding:10px; border-radius:5px; color:black; font-weight:bold;'>{a}</div>", unsafe_allow_html=True)
                m = st.session_state.db[(st.session_state.db['Date'] == sel_j) & (st.session_state.db['Agent'] == a)].sort_values('Heure')
                if m.empty: st.caption("Aucune mission")
                else:
                    for _, r in m.iterrows():
                        st.info(f"🕒 **{r['Heure']}**\n\n**{r['Batiment']}**\n\n*{r['Type']}*")

with t3:
    if not st.session_state.db.empty:
        st.subheader("📊 Indicateurs d'Optimisation")
        nb_total = len(st.session_state.db)
        # Un trajet est optimisé si l'agent a 2 missions à la même adresse le même jour
        group_rue = st.session_state.db.groupby(['Date', 'Agent', 'Rue']).size()
        missions_groupees = group_rue[group_rue > 1].sum()
        taux_opti = (missions_groupees / nb_total * 100) if nb_total > 0 else 0
        
        c1, c2, c3 = st.columns(3)
        c1.metric("Total Missions", nb_total)
        c2.metric("Missions Groupées", int(missions_groupees))
        c3.metric("Taux d'Optimisation", f"{int(taux_opti)}%")

        st.divider()
        sel_j_stats = st.selectbox("Détails des déplacements du :", sorted(st.session_state.db['Date'].unique()), key="stats_an")
        day_d = st.session_state.db[st.session_state.db['Date'] == sel_j_stats]
        
        for a in AGENTS:
            agt_d = day_d[day_d['Agent'] == a].sort_values('Heure')
            if not agt_d.empty:
                with st.expander(f"Itinéraire de {a}", expanded=True):
                    # Calcul simplifié des trajets
                    itin = [BUREAU] + agt_d['Rue'].tolist() + [BUREAU]
                    t_route = 0
                    etapes = []
                    for k in range(len(itin)-1):
                        if itin[k] != itin[k+1]:
                            t_route += 20 # Moyenne 20min par trajet différent
                            etapes.append(f"🚗 Vers {itin[k+1]}")
                        else:
                            t_route += 5 # 5min si même bâtiment
                            etapes.append(f"🚶 Sur place : {itin[k+1]}")
                    
                    col_info, col_map = st.columns([1, 2])
                    col_info.write(f"⏱️ Temps estimé route : **{t_route} min**")
                    col_info.write(f"📋 Missions : **{len(agt_d)}**")
                    col_map.write(" > ".join(etapes))
