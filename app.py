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

# Initialisation des états
if 'db' not in st.session_state:
    st.session_state.db = pd.DataFrame(columns=['Batiment', 'Date', 'Heure', 'Agent', 'Rue', 'Type', 'Date_Sort'])

# --- FONCTIONS LOGIQUES ---

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
        delai = 65 if derniere_rue == rue_cible else 80 
        prochaine_h = h_obj + timedelta(minutes=delai)
        
        if datetime.strptime("12:00", "%H:%M") <= prochaine_h < datetime.strptime("13:00", "%H:%M"):
            prochaine_h = datetime.strptime("13:00", "%H:%M")
            
        if prochaine_h > datetime.strptime("16:15", "%H:%M"):
            return "COMPLET", False
            
        return prochaine_h.strftime("%H:%M"), True
    except:
        return "08:15", True

# --- INTERFACE PRINCIPALE ---
st.title("📍 Unité Logement : Planning & Optimisation")

t1, t2, t3, t4 = st.tabs(["📝 Planning Global", "📅 Vue par Agent", "📊 Performance", "💡 Optimisation"])

with st.sidebar:
    st.header("📂 Importation")
    st.info("Les absences sont désormais gérées directement via la colonne 'Absent' de votre fichier Excel.")
    up = st.file_uploader("Fichier Excel des missions", type=['xlsx'])
    
    if up and st.button("🚀 Lancer l'Attribution IA"):
        df_ex = pd.read_excel(up).dropna(how='all').fillna('')
        df_ex.columns = df_ex.columns.str.strip()
        
        c_date = next((c for c in df_ex.columns if 'date' in c.lower()), 'Date')
        c_heure = next((c for c in df_ex.columns if 'heure' in c.lower()), 'Heure')
        c_type = next((c for c in df_ex.columns if 'type' in c.lower()), 'Type')
        c_absent = next((c for c in df_ex.columns if 'absent' in c.lower()), None)

        temp = pd.DataFrame(columns=['Batiment', 'Date', 'Heure', 'Agent', 'Rue', 'Type', 'Date_Sort'])
        
        for _, row in df_ex.sort_values(by=[c_date]).iterrows():
            ds = pd.to_datetime(row[c_date]).strftime('%d/%m/%Y')
            rue_demandee = INFOS_BATIMENTS.get(row['Batiment'], "Autre")
            
            # Gestion des absences via Excel uniquement
            absents_du_jour = []
            if c_absent and str(row[c_absent]).strip() != "":
                absents_du_jour = [a.strip().lower() for a in str(row[c_absent]).split(';')]

            # Filtrage des agents
            presents = [a for a in AGENTS if a.lower() not in absents_du_jour]
            
            agt_elu, h_finale = "À définir", "08:15"
            
            if presents:
                scores = {}
                for p in presents:
                    missions_agent = temp[(temp['Date'] == ds) & (temp['Agent'] == p)]
                    if missions_agent.empty:
                        scores[p] = 1 
                    else:
                        derniere_loc = missions_agent.iloc[-1]['Rue']
                        scores[p] = 0 if derniere_loc == rue_demandee else 2
                
                presents_tries = sorted(presents, key=lambda x: (scores[x], len(temp[(temp['Date'] == ds) & (temp['Agent'] == x)])))
                
                for p in presents_tries:
                    heure_suggere, possible = calculer_creneau_securise(p, ds, temp, row['Batiment'])
                    if possible:
                        agt_elu, h_finale = p, heure_suggere
                        break
            
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

# --- LOGIQUE DES ONGLETS ---

with t1:
    if not st.session_state.db.empty:
        df_v = st.session_state.db.sort_values(['Date_Sort', 'Heure'])
        st.dataframe(
            df_v[['Date', 'Heure', 'Agent', 'Batiment', 'Type', 'Rue']].style.apply(
                lambda r: [f'background-color: {COULEURS.get(r["Agent"])}']*6, axis=1
            ), use_container_width=True, height=500
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
        st.subheader("📊 Statistiques de l'équipe")
        nb_total = len(st.session_state.db)
        group_rue = st.session_state.db.groupby(['Date', 'Agent', 'Rue']).size()
        missions_groupees = group_rue[group_rue > 1].sum()
        taux_opti = (missions_groupees / nb_total * 100) if nb_total > 0 else 0
        
        c1, c2, c3 = st.columns(3)
        c1.metric("Total Missions", nb_total)
        c2.metric("Missions Groupées", int(missions_groupees))
        c3.metric("Taux d'Optimisation", f"{int(taux_opti)}%")

with t4:
    st.subheader("💡 Suggestions d'Optimisation IA")
    if st.session_state.db.empty:
        st.info("Importez des données pour analyser les opportunités d'optimisation.")
    else:
        df_opti = st.session_state.db.copy()
        suggestions = []

        for date in df_opti['Date'].unique():
            journee = df_opti[df_opti['Date'] == date]
            for bat, rue in INFOS_BATIMENTS.items():
                agents_sur_place = journee[journee['Rue'] == rue]['Agent'].unique()
                agents_sur_place = [a for a in agents_sur_place if a != "À définir"]
                if len(agents_sur_place) > 1:
                    suggestions.append({
                        "Type": "Double Déplacement",
                        "Priorité": "Haute",
                        "Détail": f"Le **{date}**, {', '.join(agents_sur_place)} se rendent tous à **{bat}**. Vous pourriez regrouper ces missions."
                    })

        charge = df_opti[df_opti['Agent'] != "À définir"]['Agent'].value_counts()
        for a in AGENTS:
            if a not in charge: charge[a] = 0
        
        if len(charge) > 0 and (charge.max() - charge.min() > 3):
            suggestions.append({
                "Type": "Déséquilibre de charge",
                "Priorité": "Moyenne",
                "Détail": f"**{charge.idxmax()}** a beaucoup plus de missions ({charge.max()}) que **{charge.idxmin()}** ({charge.min()})."
            })

        non_attribue = len(df_opti[df_opti['Agent'] == "À définir"])
        if non_attribue > 0:
            suggestions.append({
                "Type": "Missions en attente",
                "Priorité": "Critique",
                "Détail": f"Il reste **{non_attribue}** missions sans agent (conflit d'horaire ou absence signalée dans l'Excel)."
            })

        if suggestions:
            for s in suggestions:
                if s['Priorité'] == "Haute" or s['Priorité'] == "Critique":
                    st.error(f"**{s['Type']}** : {s['Détail']}")
                else:
                    st.warning(f"**{s['Type']}** : {s['Détail']}")
        else:
            st.success("✅ Félicitations ! Votre planning est parfaitement optimisé.")

st.divider()
st.caption("Système de gestion de planning v2.0 - Unité Logement")
