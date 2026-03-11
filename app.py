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

st.set_page_config(page_title="Unité Logement - Gestion Planning", layout="wide")

# Initialisation
if 'db' not in st.session_state:
    st.session_state.db = pd.DataFrame(columns=['Batiment', 'Date', 'Heure', 'Agent', 'Rue', 'Type', 'Statut', 'Date_Sort'])

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
st.title("📍 Unité Logement : Planning & Rapports")

t1, t2, t3 = st.tabs(["📝 Planning Global", "📅 Vue par Agent", "📊 Rapports Mensuels"])

with st.sidebar:
    st.header("📂 Importation")
    st.info("**Rappel :** Colonne 'Statut' (Souhaité) et colonne 'Absent' (Nom ; Nom) gérées via Excel.")
    up = st.file_uploader("Fichier Excel des missions", type=['xlsx'])
    
    if up and st.button("🚀 Lancer l'Attribution"):
        df_ex = pd.read_excel(up).dropna(how='all').fillna('')
        df_ex.columns = df_ex.columns.str.strip()
        
        c_date = next((c for c in df_ex.columns if 'date' in c.lower()), 'Date')
        c_heure = next((c for c in df_ex.columns if 'heure' in c.lower()), 'Heure')
        c_type = next((c for c in df_ex.columns if 'type' in c.lower()), 'Type')
        c_absent = next((c for c in df_ex.columns if 'absent' in c.lower()), None)
        c_statut = next((c for c in df_ex.columns if 'statut' in c.lower()), 'Statut')

        temp = pd.DataFrame(columns=['Batiment', 'Date', 'Heure', 'Agent', 'Rue', 'Type', 'Statut', 'Date_Sort'])
        
        for _, row in df_ex.sort_values(by=[c_date]).iterrows():
            dt_raw = pd.to_datetime(row[c_date])
            ds = dt_raw.strftime('%d/%m/%Y')
            rue_demandee = INFOS_BATIMENTS.get(row['Batiment'], "Autre")
            
            absents_du_jour = []
            if c_absent and str(row[c_absent]).strip() != "":
                absents_du_jour = [a.strip().lower().replace('-', ' ') for a in str(row[c_absent]).split(';')]

            presents = [a for a in AGENTS if a.lower().replace('-', ' ') not in absents_du_jour]
            
            agt_elu, h_finale = "À définir", "08:15"
            
            if presents:
                scores = {p: (1 if temp[(temp['Date'] == ds) & (temp['Agent'] == p)].empty else (0 if temp[(temp['Date'] == ds) & (temp['Agent'] == p)].iloc[-1]['Rue'] == rue_demandee else 2)) for p in presents}
                presents_tries = sorted(presents, key=lambda x: (scores[x], len(temp[(temp['Date'] == ds) & (temp['Agent'] == x)])))
                
                for p in presents_tries:
                    heure_suggere, possible = calculer_creneau_securise(p, ds, temp, row['Batiment'])
                    if possible:
                        agt_elu, h_finale = p, heure_suggere
                        break
            
            h_val = str(row[c_heure]).strip()
            if h_val not in ["", "nan", "00:00:00", "libre"]: h_finale = h_val[:5]

            statut_val = str(row[c_statut]).strip() if c_statut in row else ""

            temp = pd.concat([temp, pd.DataFrame([{
                'Batiment': row['Batiment'], 'Date': ds, 'Heure': h_finale, 'Agent': agt_elu, 
                'Type': row[c_type], 'Rue': rue_demandee, 'Statut': statut_val,
                'Date_Sort': dt_raw
            }])], ignore_index=True)
            
        st.session_state.db = temp
        st.rerun()

    if st.button("🗑️ Reset Complet"):
        st.session_state.db = pd.DataFrame(columns=['Batiment', 'Date', 'Heure', 'Agent', 'Rue', 'Type', 'Statut', 'Date_Sort'])
        st.rerun()

# --- ONGLETS ---

with t1:
    if not st.session_state.db.empty:
        df_v = st.session_state.db.sort_values(['Date_Sort', 'Heure'])
        
        def highlight_souhait(s):
            color = COULEURS.get(s['Agent'], "#eeeeee")
            if str(s['Statut']).lower() == "souhaité":
                # On applique le style sur les 7 colonnes affichées
                return [f'background-color: {color}; font-weight: bold; border: 2px solid orange']*7
            return [f'background-color: {color}']*7

        # --- ORDRE DES COLONNES MODIFIÉ ICI (Statut avant Heure) ---
        st.dataframe(
            df_v[['Date', 'Statut', 'Heure', 'Agent', 'Batiment', 'Type', 'Rue']].style.apply(highlight_souhait, axis=1),
            use_container_width=True, height=500
        )

with t2:
    if not st.session_state.db.empty:
        sel_j = st.selectbox("Sélectionner une date :", sorted(st.session_state.db['Date'].unique(), key=lambda x: datetime.strptime(x, '%d/%m/%Y')))
        cols = st.columns(len(AGENTS))
        for i, a in enumerate(AGENTS):
            with cols[i]:
                st.markdown(f"<div style='text-align:center; background-color:{COULEURS[a]}; padding:10px; border-radius:5px; color:black; font-weight:bold;'>{a}</div>", unsafe_allow_html=True)
                m = st.session_state.db[(st.session_state.db['Date'] == sel_j) & (st.session_state.db['Agent'] == a)].sort_values('Heure')
                if m.empty: st.caption("Aucune mission")
                else:
                    for _, r in m.iterrows():
                        if str(r['Statut']).lower() == "souhaité":
                            st.warning(f"🗓️ **{r['Heure']}** (Souhait)\n\n**{r['Batiment']}**\n\n*{r['Type']}*")
                        else:
                            st.info(f"🕒 **{r['Heure']}**\n\n**{r['Batiment']}**\n\n*{r['Type']}*")

with t3:
    st.markdown("<style>[data-testid='stMetricValue'], [data-testid='stMetricLabel'], .stMarkdown p, h3 {color: black !important;} table td, table th {color: black !important; font-weight: 500 !important;} .stTable {color: black !important;}</style>", unsafe_allow_html=True)
    st.subheader("📊 Rapports d'activité")
    if not st.session_state.db.empty:
        df_rep = st.session_state.db.copy()
        df_rep['Mois'] = df_rep['Date_Sort'].dt.strftime('%B %Y')
        liste_mois = df_rep['Mois'].unique()
        mois_sel = st.selectbox("Choisir le mois :", liste_mois)
        df_mois = df_rep[df_rep['Mois'] == mois_sel]
        
        entrees = df_mois[df_mois['Type'].str.contains('Entrée|entree|In', case=False)].shape[0]
        sorties = df_mois[df_mois['Type'].str.contains('Sortie|sortie|Out', case=False)].shape[0]
        
        c1, c2, c3 = st.columns(3)
        c1.metric("Total Missions", len(df_mois))
        c2.metric("📈 Entrées", entrees)
        c3.metric("📉 Sorties", sorties)
        
        st.divider()
        col_left, col_right = st.columns(2)
        with col_left:
            st.write("**Missions par Agent**")
            st.bar_chart(df_mois['Agent'].value_counts())
        with col_right:
            st.write("**Répartition par Bâtiment**")
            stats_bat = df_mois['Batiment'].value_counts().reset_index()
            stats_bat.columns = ['Bâtiment', 'Total']
            st.table(stats_bat.set_index('Bâtiment'))
    else:
        st.info("Importez des données pour générer les rapports.")

st.divider()
st.caption("v2.2 - Unité Logement")
