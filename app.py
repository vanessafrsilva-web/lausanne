import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import io

# --- CONFIGURATION FIXE ---
BUREAU = "Chemin Mont-Paisible 18, 1011 Lausanne"
AGENTS = ["Celine", "Maria Claret", "Maria Elisabeth"]

INFOS_BATIMENTS = {
    'Bethusy A': {'rue': 'Avenue de Béthusy 54, Lausanne', 'lat': 46.5225, 'lon': 6.6472},
    'Bethusy B': {'rue': 'Avenue de Béthusy 56, Lausanne', 'lat': 46.5227, 'lon': 6.6475},
    'Montolieu A': {'rue': 'Isabelle-de-Montolieu 90, Lausanne', 'lat': 46.5412, 'lon': 6.6421},
    'Montolieu B': {'rue': 'Isabelle-de-Montolieu 92, Lausanne', 'lat': 46.5415, 'lon': 6.6425},
    'Tunnel': {'rue': 'Rue du Tunnel 17, Lausanne', 'lat': 46.5255, 'lon': 6.6328},
    'Oron': {'rue': "Route d'Oron 77, 1010 Lausanne", 'lat': 46.5361, 'lon': 6.6625}
}

# Couleurs HEX pour le tableau
COULEURS_HEX = {"Celine": "#d1e9ff", "Maria Claret": "#ffdae0", "Maria Elisabeth": "#d4f8d4", "⚠️ SANS AGENT": "#eeeeee"}

# Couleurs RGB pour la carte (Format strict pour éviter l'erreur JSON)
COULEURS_RGB = {
    "Celine": [0, 123, 255, 160],
    "Maria Claret": [255, 51, 161, 160],
    "Maria Elisabeth": [40, 167, 69, 160],
    "⚠️ SANS AGENT": [200, 200, 200, 100]
}

st.set_page_config(page_title="Unité Logement - Gestion Planning", layout="wide")

if 'db' not in st.session_state:
    st.session_state.db = pd.DataFrame(columns=['Batiment', 'Date', 'Heure', 'Agent', 'Rue', 'Type', 'Statut', 'Date_Sort'])

# --- LOGIQUE D'ATTRIBUTION ---
def calculer_creneau(agent, date_str, temp_db, batiment_cible, heure_forcee=None):
    m_jour = temp_db[(temp_db['Date'] == date_str) & (temp_db['Agent'] == agent)]
    
    if heure_forcee:
        # Si l'agent a déjà quelque chose à cette heure précise
        if not m_jour.empty and heure_forcee in [str(h).strip() for h in m_jour['Heure'].values]:
            return f"⚠️ CONFLIT ({heure_forcee})", True
        return heure_forcee, True

    if m_jour.empty:
        h_actuelle = datetime.strptime("08:15", "%H:%M")
    else:
        derniere_h = str(m_jour.iloc[-1]['Heure']).strip()
        if "⚠️" in derniere_h: # Si le précédent était un conflit, on repart sur une base saine
             h_actuelle = datetime.strptime("08:15", "%H:%M")
        else:
             h_actuelle = datetime.strptime(derniere_h, "%H:%M")
        
        # Calcul du trajet
        info_b = INFOS_BATIMENTS.get(batiment_cible, {'rue': 'Autre'})
        delai = 65 if m_jour.iloc[-1]['Rue'] == info_b['rue'] else 80
        h_actuelle += timedelta(minutes=delai)

    # Pause midi
    if datetime.strptime("12:00", "%H:%M") <= h_actuelle < datetime.strptime("13:00", "%H:%M"):
        h_actuelle = datetime.strptime("13:00", "%H:%M")
        
    if h_actuelle > datetime.strptime("16:30", "%H:%M"):
        return "COMPLET", False
        
    return h_actuelle.strftime("%H:%M"), True

# --- SIDEBAR ---
with st.sidebar:
    st.header("📂 Importation")
    up = st.file_uploader("Fichier Excel des missions", type=['xlsx'])
    mode_ia = st.radio("Méthode :", ["Respecter l'heure de l'Excel (Fixe)", "Optimiser les horaires"])
    
    if up and st.button("🚀 Lancer l'Attribution"):
        df_ex = pd.read_excel(up).dropna(how='all').fillna('')
        df_ex.columns = df_ex.columns.str.strip()
        
        # Détection auto colonnes
        c_date = next((c for c in df_ex.columns if 'date' in c.lower()), 'Date')
        c_heure = next((c for c in df_ex.columns if 'heure' in c.lower()), 'Heure')
        c_type = next((c for c in df_ex.columns if 'type' in c.lower()), 'Type')
        c_abs = next((c for c in df_ex.columns if 'absent' in c.lower()), None)
        c_stat = next((c for c in df_ex.columns if 'statut' in c.lower()), 'Statut')

        temp = []
        for _, row in df_ex.sort_values(by=[c_date, c_heure]).iterrows():
            dt_raw = pd.to_datetime(row[c_date])
            ds = dt_raw.strftime('%d/%m/%Y')
            h_ex = str(row[c_heure]).strip()[:5] if str(row[c_heure]).strip() not in ["", "nan"] else None
            
            absents = [a.strip().lower() for a in str(row[c_abs]).split(';')] if c_abs else []
            presents = [a for a in AGENTS if a.lower() not in absents]
            
            agt_elu, h_fin = "⚠️ SANS AGENT", h_ex if h_ex else "08:15"
            
            if presents:
                # On trie les agents par charge de travail actuelle
                p_tries = sorted(presents, key=lambda x: len([r for r in temp if r['Agent'] == x and r['Date'] == ds]))
                for p in p_tries:
                    res_h, ok = calculer_creneau(p, ds, pd.DataFrame(temp), row['Batiment'], h_ex if "Fixe" in mode_ia else None)
                    if ok:
                        agt_elu, h_fin = p, res_h
                        break
            
            temp.append({
                'Batiment': row['Batiment'], 'Date': ds, 'Heure': h_fin, 'Agent': agt_elu,
                'Type': row[c_type], 'Rue': INFOS_BATIMENTS.get(row['Batiment'], {'rue': 'Autre'})['rue'],
                'Statut': str(row[c_stat]), 'Date_Sort': dt_raw
            })
            
        st.session_state.db = pd.DataFrame(temp)
        st.rerun()

    st.button("🗑️ Reset Complet", on_click=lambda: st.session_state.update({'db': pd.DataFrame(columns=['Batiment', 'Date', 'Heure', 'Agent', 'Rue', 'Type', 'Statut', 'Date_Sort'])}))

# --- TABS ---
t1, t2, t3 = st.tabs(["📝 Planning Global", "📅 Vue Agent", "📊 Rapports"])

with t1:
    if not st.session_state.db.empty:
        df_v = st.session_state.db.sort_values(['Date_Sort', 'Heure'])
        def style_rows(s):
            if "⚠️" in str(s['Heure']): return ['background-color: #ffb3b3; color: #b30000']*7
            return [f'background-color: {COULEURS_HEX.get(s["Agent"], "#eee")}']*7
        st.dataframe(df_v[['Date', 'Heure', 'Agent', 'Batiment', 'Type', 'Statut', 'Rue']].style.apply(style_rows, axis=1), use_container_width=True)

with t2:
    if not st.session_state.db.empty:
        sel_j = st.selectbox("Date :", sorted(st.session_state.db['Date'].unique(), key=lambda x: datetime.strptime(x, '%d/%m/%Y')))
        cols = st.columns(len(AGENTS))
        for i, a in enumerate(AGENTS):
            with cols[i]:
                st.markdown(f"<div style='text-align:center; background-color:{COULEURS_HEX[a]}; padding:10px; border-radius:5px; font-weight:bold;'>{a}</div>", unsafe_allow_html=True)
                m = st.session_state.db[(st.session_state.db['Date'] == sel_j) & (st.session_state.db['Agent'] == a)].sort_values('Heure')
                for _, r in m.iterrows():
                    if "⚠️" in str(r['Heure']): st.error(f"🚨 {r['Heure']}\n\n{r['Batiment']}")
                    else: st.info(f"🕒 **{r['Heure']}**\n\n**{r['Batiment']}**")

with t3:
    if not st.session_state.db.empty:
        df_rep = st.session_state.db.copy()
        df_rep['Mois'] = df_rep['Date_Sort'].dt.strftime('%B %Y')
        m1, m2 = st.columns(2)
        mois = m1.selectbox("Mois :", df_rep['Mois'].unique())
        agt = m2.selectbox("Agent :", ["Tous"] + AGENTS)
        
        df_f = df_rep[df_rep['Mois'] == mois]
        if agt != "Tous": df_f = df_f[df_f['Agent'] == agt]
        
        c1, c2, c3 = st.columns(3)
        c1.metric("Missions", len(df_f))
        c2.metric("Entrées", len(df_f[df_f['Type'].str.contains('Entrée', case=False)]))
        c3.metric("Sorties", len(df_f[df_f['Type'].str.contains('Sortie', case=False)]))
        
        cl, cr = st.columns([1, 1.5])
        with cl:
            st.subheader("🏠 Bâtiments")
            st.table(df_f.groupby('Batiment').size().reset_index(name='Nb').sort_values('Nb', ascending=False))
        with cr:
            st.subheader(f"📍 Carte : {agt}")
            map_data = []
            for b_name in df_f['Batiment'].unique():
                if b_name in INFOS_BATIMENTS:
                    count = len(df_f[df_f['Batiment'] == b_name])
                    agent_ref = df_f[df_f['Batiment'] == b_name]['Agent'].iloc[0]
                    map_data.append({
                        'lat': float(INFOS_BATIMENTS[b_name]['lat']),
                        'lon': float(INFOS_BATIMENTS[b_name]['lon']),
                        'size': int(count * 50),
                        'color': COULEURS_RGB.get(agent_ref, [200, 200, 200, 150])
                    })
            if map_data:
                st.map(pd.DataFrame(map_data), latitude='lat', longitude='lon', size='size', color='color')
