import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import io
import plotly.express as px

# --- CONFIGURATION ---
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

COULEURS = {"Celine": "#d1e9ff", "Maria Claret": "#ffdae0", "Maria Elisabeth": "#d4f8d4", "À définir": "#eeeeee", "⚠️ SANS AGENT": "#333333"}

st.set_page_config(page_title="Unité Logement - Gestion Planning", layout="wide", page_icon="📍")

st.markdown("""
    <style>
    [data-testid="stNotification"] { padding: 8px; margin-bottom: 2px; }
    .dataframe { font-size: 12px; }
    </style>
    """, unsafe_allow_html=True)

if 'db' not in st.session_state:
    # AJOUT DE LA COLONNE ID DANS LA STRUCTURE INITIALE
    st.session_state.db = pd.DataFrame(columns=['ID', 'Batiment', 'Date', 'Heure', 'Agent', 'Rue', 'Type', 'Statut', 'Date_Sort'])

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

t1, t2, t3 = st.tabs(["📝 Planning Global", "📅 Vue par Agent", "📊 Rapports & Analyses"])

with st.sidebar:
    st.header("📂 Importation")
    up = st.file_uploader("Fichier Excel des missions", type=['xlsx'])
    mode_ia = st.radio("Méthode :", ["Respecter l'heure de l'Excel (Fixe)", "Optimiser par blocs (Matin / Après-midi)"])

    if up and st.button("🚀 Lancer l'Attribution"):
        with st.spinner("Calcul en cours..."):
            try:
                df_ex = pd.read_excel(up).dropna(how='all').fillna('')
                df_ex.columns = df_ex.columns.str.strip()
                
                # IDENTIFICATION DES COLONNES
                c_id = next((c for c in df_ex.columns if 'id' in c.lower() or 'n°' in c.lower()), df_ex.columns[0])
                c_date = next((c for c in df_ex.columns if 'date' in c.lower()), 'Date')
                c_heure = next((c for c in df_ex.columns if 'heure' in c.lower()), 'Heure')
                c_type = next((c for c in df_ex.columns if 'type' in c.lower()), 'Type')
                c_absent = next((c for c in df_ex.columns if 'absent' in c.lower()), None)
                c_statut = next((c for c in df_ex.columns if 'statut' in c.lower()), 'Statut')

                temp = pd.DataFrame(columns=['ID', 'Batiment', 'Date', 'Heure', 'Agent', 'Rue', 'Type', 'Statut', 'Date_Sort'])
                df_ex_sorted = df_ex.copy()
                df_ex_sorted[c_date] = pd.to_datetime(df_ex_sorted[c_date])
                df_ex_sorted = df_ex_sorted.sort_values(by=[c_date, c_heure])

                for _, row in df_ex_sorted.iterrows():
                    dt_raw = row[c_date]
                    ds = dt_raw.strftime('%d/%m/%Y')
                    info_b = INFOS_BATIMENTS.get(row['Batiment'], {'rue': 'Autre'})
                    rue_demandee = info_b['rue']
                    statut_val = str(row[c_statut]).strip()
                    h_excel = str(row[c_heure]).strip()[:5] if str(row[c_heure]).strip() not in ["", "nan", "libre"] else None
                    bloc = "Matin" if "matin" in statut_val.lower() else ("Après-midi" if "midi" in statut_val.lower() else None)
                    absents = [a.strip().lower().replace('-', ' ') for a in str(row[c_absent]).split(';')] if c_absent and str(row[c_absent]).strip() != "" else []
                    presents = [a for a in AGENTS if a.lower().replace('-', ' ') not in absents]
                    
                    agt_elu, h_finale = "⚠️ SANS AGENT", h_excel if h_excel else "08:15"
                    
                    if presents:
                        scores = {p: (0 if (not temp[(temp['Date'] == ds) & (temp['Agent'] == p)].empty and temp[(temp['Date'] == ds) & (temp['Agent'] == p)].iloc[-1]['Rue'] == rue_demandee) else 1) for p in presents}
                        presents_tries = sorted(presents, key=lambda x: (scores[x], len(temp[(temp['Date'] == ds) & (temp['Agent'] == x)])))
                        for p in presents_tries:
                            res_h, possible = calculer_creneau_securise(p, ds, temp, row['Batiment'], bloc, h_excel if "Fixe" in mode_ia else None)
                            if possible:
                                agt_elu, h_finale = p, res_h
                                break
                            elif res_h == "⚠️ CONFLIT":
                                agt_elu, h_finale = p, "⚠️ CONFLIT"

                    temp = pd.concat([temp, pd.DataFrame([{
                        'ID': row[c_id], # STOCKAGE DE L'ID
                        'Batiment': row['Batiment'], 'Date': ds, 'Heure': h_finale, 'Agent': agt_elu, 
                        'Type': row[c_type], 'Rue': rue_demandee, 'Statut': statut_val, 'Date_Sort': dt_raw
                    }])], ignore_index=True)
                st.session_state.db = temp
                st.rerun()
            except Exception as e:
                st.error(f"Erreur : {e}")

    if not st.session_state.db.empty:
        st.divider()
        df_export = st.session_state.db.sort_values(['Date_Sort', 'Heure']).drop(columns=['Date_Sort'])
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            df_export.to_excel(writer, index=False)
        st.download_button("📥 Télécharger Excel", output.getvalue(), "Planning.xlsx")
        if st.button("🗑️ Reset"):
            st.session_state.db = pd.DataFrame(columns=['ID', 'Batiment', 'Date', 'Heure', 'Agent', 'Rue', 'Type', 'Statut', 'Date_Sort'])
            st.rerun()

# --- ONGLETS ---
with t1:
    if not st.session_state.db.empty:
        df_v = st.session_state.db.sort_values(['Date_Sort', 'Heure'])
        def style_row(s):
            if s['Heure'] == "⚠️ CONFLIT": return ['background-color: #ffcccc; color: #cc0000; font-weight: bold']*8
            color = COULEURS.get(s['Agent'], "#eeeeee")
            if str(s['Statut']).strip() != "": return [f'background-color: {color}; border: 2px solid #ff9933']*8
            return [f'background-color: {color}; color: black']*8
        # AFFICHAGE DE LA COLONNE ID DANS LE TABLEAU
        st.dataframe(df_v[['ID', 'Date', 'Statut', 'Heure', 'Agent', 'Batiment', 'Type', 'Rue']].style.apply(style_row, axis=1), use_container_width=True, height=500)

with t2:
    if not st.session_state.db.empty:
        sel_j = st.selectbox("📅 Date :", sorted(st.session_state.db['Date'].unique(), key=lambda x: datetime.strptime(x, '%d/%m/%Y')))
        cols = st.columns(len(AGENTS))
        for i, a in enumerate(AGENTS):
            with cols[i]:
                st.markdown(f"<div style='text-align:center; background-color:{COULEURS[a]}; padding:10px; border-radius:5px; color:black; font-weight:bold;'>{a}</div>", unsafe_allow_html=True)
                m = st.session_state.db[(st.session_state.db['Date'] == sel_j) & (st.session_state.db['Agent'] == a)].sort_values('Heure')
                for _, r in m.iterrows():
                    color = "#ffcccc" if r['Heure'] == "⚠️ CONFLIT" else COULEURS[a]
                    # AFFICHAGE DE L'ID DANS LES CARTES AGENTS
                    st.markdown(f"<div style='background-color:{color}; padding:8px; border-radius:5px; border:1px solid #ccc; color:black; margin-top:5px;'>🆔 <b>{r['ID']}</b><br>🕒 <b>{r['Heure']}</b><br>🏠 {r['Batiment']}</div>", unsafe_allow_html=True)

with t3:
    if not st.session_state.db.empty:
        df_rep = st.session_state.db.copy()
        df_rep['Mois'] = df_rep['Date_Sort'].dt.strftime('%B %Y')
        mois_sel = st.selectbox("📅 Mois :", df_rep['Mois'].unique())
        df_mois = df_rep[df_rep['Mois'] == mois_sel]
        agents_sel = st.multiselect("👤 Agents :", sorted(df_mois['Agent'].unique()), default=[a for a in df_mois['Agent'].unique() if a != "⚠️ SANS AGENT"])
        df_final = df_mois[df_mois['Agent'].isin(agents_sel)]

        if not df_final.empty:
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Missions", len(df_final))
            c2.metric("📈 Entrées", df_final[df_final['Type'].str.contains('Entrée|In', case=False)].shape[0])
            c3.metric("📉 Sorties", df_final[df_final['Type'].str.contains('Sortie|Out', case=False)].shape[0])
            c4.metric("📅 Jours", df_final['Date'].nunique())
            
            st.divider()
            st.subheader("📊 Charge de travail hebdomadaire")
            df_chart = df_final.copy()
            df_chart['Semaine'] = df_chart['Date_Sort'].dt.isocalendar().week
            df_chart['Nom_Semaine'] = "Semaine " + df_chart['Semaine'].astype(str)
            
            fig = px.histogram(df_chart.sort_values('Semaine'), x='Nom_Semaine', color='Agent', 
                               title=f"Total missions : {len(df_final)}", color_discrete_map=COULEURS,
                               barmode='group', text_auto=True)
            fig.update_layout(xaxis_title="Semaine", yaxis_title="Nb Missions")
            st.plotly_chart(fig, use_container_width=True)

            st.divider()
            cl, cr = st.columns(2)
            with cl:
                st.subheader("🏠 Par bâtiment")
                st.table(df_final.groupby('Batiment').size().reset_index(name='Missions').sort_values('Missions', ascending=False))
            with cr:
                st.subheader("📍 Carte")
                st.map(pd.DataFrame([{'lat': INFOS_BATIMENTS[b]['lat'], 'lon': INFOS_BATIMENTS[b]['lon'], 'Missions': count} 
                       for b, count in df_final.groupby('Batiment').size().items() if b in INFOS_BATIMENTS]))

st.divider()
st.caption(f"v3.3 | {datetime.now().year}")
