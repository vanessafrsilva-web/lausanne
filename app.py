import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import io

# --- CONFIGURATION ---
BUREAU = "Chemin Mont-Paisible 18, 1011 Lausanne"
AGENTS = ["Celine", "Maria Claret", "Maria Elisabeth"]

# Ajout des coordonnées pour la cartographie
INFOS_BATIMENTS = {
    'Bethusy A': {'rue': 'Avenue de Béthusy 54, Lausanne', 'lat': 46.5225, 'lon': 6.6472},
    'Bethusy B': {'rue': 'Avenue de Béthusy 56, Lausanne', 'lat': 46.5227, 'lon': 6.6475},
    'Montolieu A': {'rue': 'Isabelle-de-Montolieu 90, Lausanne', 'lat': 46.5412, 'lon': 6.6421},
    'Montolieu B': {'rue': 'Isabelle-de-Montolieu 92, Lausanne', 'lat': 46.5415, 'lon': 6.6425},
    'Tunnel': {'rue': 'Rue du Tunnel 17, Lausanne', 'lat': 46.5255, 'lon': 6.6328},
    'Oron': {'rue': "Route d'Oron 77, 1010 Lausanne", 'lat': 46.5361, 'lon': 6.6625}
}

COULEURS = {"Celine": "#d1e9ff", "Maria Claret": "#ffdae0", "Maria Elisabeth": "#d4f8d4", "À définir": "#eeeeee"}

st.set_page_config(page_title="Unité Logement - Gestion Planning", layout="wide")

if 'db' not in st.session_state:
    st.session_state.db = pd.DataFrame(columns=['Batiment', 'Date', 'Heure', 'Agent', 'Rue', 'Type', 'Statut', 'Date_Sort'])

# --- FONCTIONS LOGIQUES ---

def calculer_creneau_securise(agent, date_str, temp_db, batiment_cible, bloc_impose=None, heure_forcee=None):
    m_jour = temp_db[(temp_db['Date'] == date_str) & (temp_db['Agent'] == agent)]
    
    if heure_forcee:
        if not m_jour.empty and heure_forcee in [str(h) for h in m_jour['Heure'].values]:
            return "⚠️ CONFLIT", False
        return heure_forcee, True

    if m_jour.empty:
        h_depart_str = "08:15" if bloc_impose != "Après-midi" else "13:00"
    else:
        h_depart_str = str(m_jour.iloc[-1]['Heure']).strip()

    try:
        h_obj = datetime.strptime(h_depart_str, "%H:%M")
        rue_cible = INFOS_BATIMENTS.get(batiment_cible, {}).get('rue', "Autre")
        derniere_rue = m_jour.iloc[-1]['Rue'] if not m_jour.empty else "Bureau"
        
        delai = 65 if derniere_rue == rue_cible else 80 
        prochaine_h = h_obj + timedelta(minutes=delai) if not m_jour.empty else h_obj
        
        if datetime.strptime("12:00", "%H:%M") <= prochaine_h < datetime.strptime("13:00", "%H:%M"):
            prochaine_h = datetime.strptime("13:00", "%H:%M")
        
        if bloc_impose == "Matin" and prochaine_h > datetime.strptime("11:45", "%H:%M"):
            return "COMPLET MATIN", False
        if prochaine_h > datetime.strptime("16:30", "%H:%M"):
            return "COMPLET JOUR", False
            
        return prochaine_h.strftime("%H:%M"), True
    except:
        return "08:15", True

# --- INTERFACE ---
st.title("📍 Unité Logement : Planning & Rapports")
st.caption(f"📍 Siège social : {BUREAU}")

t1, t2, t3 = st.tabs(["📝 Planning Global", "📅 Vue par Agent", "📊 Rapports Mensuels"])

with st.sidebar:
    st.header("📂 Importation")
    up = st.file_uploader("Fichier Excel des missions", type=['xlsx'])
    
    st.subheader("⚙️ Options d'attribution")
    mode_ia = st.radio("Méthode :", ["Respecter l'heure de l'Excel (Fixe)", "Optimiser par blocs (Matin / Après-midi)"])

    if up and st.button("🚀 Lancer l'Attribution"):
        df_ex = pd.read_excel(up).dropna(how='all').fillna('')
        df_ex.columns = df_ex.columns.str.strip()
        
        c_date = next((c for c in df_ex.columns if 'date' in c.lower()), 'Date')
        c_heure = next((c for c in df_ex.columns if 'heure' in c.lower()), 'Heure')
        c_type = next((c for c in df_ex.columns if 'type' in c.lower()), 'Type')
        c_absent = next((c for c in df_ex.columns if 'absent' in c.lower()), None)
        c_statut = next((c for c in df_ex.columns if 'statut' in c.lower()), 'Statut')

        temp = pd.DataFrame(columns=['Batiment', 'Date', 'Heure', 'Agent', 'Rue', 'Type', 'Statut', 'Date_Sort'])
        
        for _, row in df_ex.sort_values(by=[c_date, c_heure]).iterrows():
            dt_raw = pd.to_datetime(row[c_date])
            ds = dt_raw.strftime('%d/%m/%Y')
            info_b = INFOS_BATIMENTS.get(row['Batiment'], {'rue': 'Autre'})
            rue_demandee = info_b['rue']
            statut_val = str(row[c_statut]).strip()
            h_excel = str(row[c_heure]).strip()[:5] if str(row[c_heure]).strip() not in ["", "nan", "libre"] else None

            bloc = "Matin" if "matin" in statut_val.lower() else ("Après-midi" if "midi" in statut_val.lower() else None)
            absents = [a.strip().lower().replace('-', ' ') for a in str(row[c_absent]).split(';')] if c_absent and str(row[c_absent]).strip() != "" else []
            presents = [a for a in AGENTS if a.lower().replace('-', ' ') not in absents]
            
            agt_elu = "⚠️ SANS AGENT"
            h_finale = h_excel if h_excel else "08:15"
            
            if presents:
                scores = {p: (1 if temp[(temp['Date'] == ds) & (temp['Agent'] == p)].empty else (0 if temp[(temp['Date'] == ds) & (temp['Agent'] == p)].iloc[-1]['Rue'] == rue_demandee else 2)) for p in presents}
                presents_tries = sorted(presents, key=lambda x: (scores[x], len(temp[(temp['Date'] == ds) & (temp['Agent'] == x)])))
                
                for p in presents_tries:
                    h_forcee = h_excel if "Fixe" in mode_ia else None
                    res_h, possible = calculer_creneau_securise(p, ds, temp, row['Batiment'], bloc, h_forcee)
                    if possible:
                        agt_elu, h_finale = p, res_h
                        break
                    elif res_h == "⚠️ CONFLIT":
                        h_finale = "⚠️ CONFLIT"
                        agt_elu = p
            
            temp = pd.concat([temp, pd.DataFrame([{
                'Batiment': row['Batiment'], 'Date': ds, 'Heure': h_finale, 'Agent': agt_elu, 
                'Type': row[c_type], 'Rue': rue_demandee, 'Statut': statut_val, 'Date_Sort': dt_raw
            }])], ignore_index=True)
            
        st.session_state.db = temp
        st.rerun()

    if not st.session_state.db.empty:
        output = io.BytesIO()
        df_export = st.session_state.db.sort_values(['Date_Sort', 'Heure']).drop(columns=['Date_Sort'])
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            df_export.to_excel(writer, index=False, sheet_name='Planning')
        
        st.download_button("📥 Télécharger Excel", output.getvalue(), f"Planning_{datetime.now().strftime('%Y%m%d')}.xlsx")

    if st.button("🗑️ Reset Complet"):
        st.session_state.db = pd.DataFrame(columns=['Batiment', 'Date', 'Heure', 'Agent', 'Rue', 'Type', 'Statut', 'Date_Sort'])
        st.rerun()

# --- ONGLETS ---
with t1:
    if not st.session_state.db.empty:
        df_v = st.session_state.db.sort_values(['Date_Sort', 'Heure'])
        def style_row(s):
            if s['Heure'] == "⚠️ CONFLIT": return ['background-color: #ffcccc; color: red; font-weight: bold']*7
            if s['Agent'] == "⚠️ SANS AGENT": return ['background-color: #333333; color: white; font-weight: bold']*7
            color = COULEURS.get(s['Agent'], "#eeeeee")
            if s['Statut'] != "": return [f'background-color: {color}; border: 2px solid orange']*7
            return [f'background-color: {color}']*7

        st.dataframe(df_v[['Date', 'Statut', 'Heure', 'Agent', 'Batiment', 'Type', 'Rue']].style.apply(style_row, axis=1), use_container_width=True, height=400)

with t2:
    if not st.session_state.db.empty:
        sel_j = st.selectbox("Sélectionner une date :", sorted(st.session_state.db['Date'].unique(), key=lambda x: datetime.strptime(x, '%d/%m/%Y')))
        cols = st.columns(len(AGENTS))
        for i, a in enumerate(AGENTS):
            with cols[i]:
                st.markdown(f"<div style='text-align:center; background-color:{COULEURS[a]}; padding:10px; border-radius:5px; color:black; font-weight:bold;'>{a}</div>", unsafe_allow_html=True)
                m = st.session_state.db[(st.session_state.db['Date'] == sel_j) & (st.session_state.db['Agent'] == a)].sort_values('Heure')
                for _, r in m.iterrows():
                    box = st.error if r['Heure'] == "⚠️ CONFLIT" else (st.warning if r['Statut'] != "" else st.info)
                    box(f"🕒 **{r['Heure']}**\n\n**{r['Batiment']}**")

with t3:
    if not st.session_state.db.empty:
        df_rep = st.session_state.db.copy()
        df_rep['Mois'] = df_rep['Date_Sort'].dt.strftime('%B %Y')
        mois_sel = st.selectbox("Choisir le mois :", df_rep['Mois'].unique())
        df_mois = df_rep[df_rep['Mois'] == mois_sel]
        
        c1, c2, c3 = st.columns(3)
        c1.metric("Total Missions", len(df_mois))
        c2.metric("📈 Entrées", df_mois[df_mois['Type'].str.contains('Entrée|In', case=False)].shape[0])
        c3.metric("📉 Sorties", df_mois[df_mois['Type'].str.contains('Sortie|Out', case=False)].shape[0])
        
        st.divider()
        col_left, col_right = st.columns([1, 1])
        
        with col_left:
            st.subheader("🏠 Volume par bâtiment")
            stats_bat = df_mois.groupby('Batiment').size().reset_index(name='Missions').sort_values('Missions', ascending=False)
            st.table(stats_bat)

        with col_right:
            st.subheader("📍 Cartographie")
            map_data = []
            for _, row in stats_bat.iterrows():
                if row['Batiment'] in INFOS_BATIMENTS:
                    map_data.append({
                        'lat': INFOS_BATIMENTS[row['Batiment']]['lat'],
                        'lon': INFOS_BATIMENTS[row['Batiment']]['lon'],
                        'Missions': row['Missions']
                    })
            if map_data:
                df_map = pd.DataFrame(map_data)
                # Taille des points basée sur le nombre de missions
                st.map(df_map, latitude='lat', longitude='lon', size=df_map['Missions'] * 20, color="#FF4B4B")
            else:
                st.info("Aucune donnée géographique à afficher.")
    else:
        st.info("Veuillez importer des données.")

st.caption("v3.0 - Edition Cartographique")
