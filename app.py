import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import io

# --- CONFIGURATION ---
BUREAU = "Chemin Mont-Paisible 18, 1011 Lausanne"
AGENTS = ["Celine", "Maria Claret", "Maria Elisabeth"]
INFOS_BATIMENTS = {
    'Bethusy A': 'Avenue de Béthusy 54, Lausanne', 'Bethusy B': 'Avenue de Béthusy 56, Lausanne',
    'Montolieu A': 'Isabelle-de-Montolieu 90, Lausanne', 'Montolieu B': 'Isabelle-de-Montolieu 92, Lausanne',
    'Tunnel': 'Rue du Tunnel 17, Lausanne', 'Oron': "Route d'Oron 77, 1010 Lausanne"
}
COULEURS = {"Celine": "#d1e9ff", "Maria Claret": "#ffdae0", "Maria Elisabeth": "#d4f8d4", "⚠️ SANS AGENT": "#eeeeee"}

st.set_page_config(page_title="CHUV - Unité Logement", layout="wide")

# Style pour garantir la visibilité des rapports
st.markdown("""
    <style>
    [data-testid="stMetricValue"] { color: #0076bd !important; }
    [data-testid="stMetricLabel"] { color: #333333 !important; }
    .stTable td { color: black !important; font-weight: 500; }
    </style>
""", unsafe_allow_html=True)

if 'db' not in st.session_state:
    st.session_state.db = pd.DataFrame(columns=['Batiment', 'Date', 'Heure', 'Agent', 'Rue', 'Type', 'Statut', 'Date_Sort'])

# --- LOGIQUE ---
def calculer_creneau_securise(agent, date_str, temp_db, batiment_cible, bloc_impose=None, heure_forcee=None):
    m_jour = temp_db[(temp_db['Date'] == date_str) & (temp_db['Agent'] == agent)]
    if heure_forcee:
        if not m_jour.empty and heure_forcee in [str(h) for h in m_jour['Heure'].values]:
            return "⚠️ CONFLIT", False
        return heure_forcee, True
    h_depart_str = "08:15" if m_jour.empty and bloc_impose != "Après-midi" else ("13:00" if m_jour.empty else str(m_jour.iloc[-1]['Heure']).strip())
    try:
        h_obj = datetime.strptime(h_depart_str, "%H:%M")
        rue_c = INFOS_BATIMENTS.get(batiment_cible, "Autre")
        derniere_rue = m_jour.iloc[-1]['Rue'] if not m_jour.empty else "Bureau"
        delai = 65 if derniere_rue == rue_c else 80 
        prochaine_h = h_obj + timedelta(minutes=delai) if not m_jour.empty else h_obj
        if datetime.strptime("12:00", "%H:%M") <= prochaine_h < datetime.strptime("13:00", "%H:%M"):
            prochaine_h = datetime.strptime("13:00", "%H:%M")
        if (bloc_impose == "Matin" and prochaine_h > datetime.strptime("11:45", "%H:%M")) or (prochaine_h > datetime.strptime("16:30", "%H:%M")):
            return "COMPLET", False
        return prochaine_h.strftime("%H:%M"), True
    except: return "08:15", True

# --- HEADER ---
st.markdown(f"""
    <div style="border-left: 10px solid #0076bd; padding-left: 20px; margin-bottom: 20px;">
        <h1 style="margin:0; font-size:45px; color:black;">CHUV</h1>
        <h3 style="margin:0; color:#555;">Unité Logement - Gestion Planning</h3>
        <p style="color:#888;">📍 {BUREAU}</p>
    </div>
""", unsafe_allow_html=True)

t1, t2, t3 = st.tabs(["📝 Planning", "📅 Vue Agents", "📊 Rapports & Export"])

with st.sidebar:
    st.header("📂 Importation")
    up = st.file_uploader("Fichier Excel", type=['xlsx'])
    mode_ia = st.radio("Méthode :", ["Respecter l'heure Excel (Fixe)", "Optimiser par blocs (IA)"])

    if up and st.button("🚀 Lancer l'IA"):
        df_ex = pd.read_excel(up).dropna(how='all').fillna('')
        df_ex.columns = df_ex.columns.str.strip()
        temp = pd.DataFrame(columns=['Batiment', 'Date', 'Heure', 'Agent', 'Rue', 'Type', 'Statut', 'Date_Sort'])
        for _, row in df_ex.sort_values(by=[df_ex.columns[0]]).iterrows():
            ds = pd.to_datetime(row[df_ex.columns[0]]).strftime('%d/%m/%Y')
            statut = str(row.get('Statut', '')).strip()
            h_ex = str(row.get('Heure', ''))[:5] if str(row.get('Heure', '')) not in ["", "nan"] else None
            absents = [a.strip().lower() for a in str(row.get('Absent', '')).split(';')]
            presents = [a for a in AGENTS if a.lower() not in absents]
            agt_elu, h_fin = "⚠️ SANS AGENT", (h_ex if h_ex else "08:15")
            if presents:
                p_tries = sorted(presents, key=lambda x: len(temp[(temp['Date'] == ds) & (temp['Agent'] == x)]))
                for p in p_tries:
                    res, ok = calculer_creneau_securise(p, ds, temp, row['Batiment'], "Matin" if "matin" in statut.lower() else None, h_ex if "Fixe" in mode_ia else None)
                    if ok: agt_elu, h_fin = p, res; break
                    elif res == "⚠️ CONFLIT": h_fin, agt_elu = res, p
            temp = pd.concat([temp, pd.DataFrame([{'Batiment': row['Batiment'], 'Date': ds, 'Heure': h_fin, 'Agent': agt_elu, 'Type': row.get('Type',''), 'Rue': INFOS_BATIMENTS.get(row['Batiment'], 'Autre'), 'Statut': statut, 'Date_Sort': pd.to_datetime(row[df_ex.columns[0]])}])], ignore_index=True)
        st.session_state.db = temp
        st.rerun()

    if st.button("🗑️ Reset"):
        st.session_state.db = pd.DataFrame(columns=['Batiment', 'Date', 'Heure', 'Agent', 'Rue', 'Type', 'Statut', 'Date_Sort'])
        st.rerun()

# --- CONTENU ---
with t1:
    if not st.session_state.db.empty:
        df_v = st.session_state.db.sort_values(['Date_Sort', 'Heure'])
        st.dataframe(df_v[['Date', 'Heure', 'Agent', 'Batiment', 'Type', 'Statut']].style.apply(lambda x: ['background-color: #ffcccc' if x['Heure'] == "⚠️ CONFLIT" else f'background-color: {COULEURS.get(x["Agent"], "#eee")}']*6, axis=1), use_container_width=True)

with t2:
    if not st.session_state.db.empty:
        sel = st.selectbox("Date :", st.session_state.db['Date'].unique())
        c = st.columns(3)
        for i, a in enumerate(AGENTS):
            with c[i]:
                st.markdown(f"<div style='text-align:center; background-color:{COULEURS[a]}; padding:5px; border-radius:5px; color:black;'><b>{a}</b></div>", unsafe_allow_html=True)
                for _, r in st.session_state.db[(st.session_state.db['Date'] == sel) & (st.session_state.db['Agent'] == a)].iterrows():
                    st.info(f"🕒 {r['Heure']} - {r['Batiment']}")

with t3:
    if not st.session_state.db.empty:
        st.subheader("📊 Analyse du Planning")
        col1, col2, col3 = st.columns(3)
        col1.metric("Total Missions", len(st.session_state.db))
        col2.metric("Entrées", len(st.session_state.db[st.session_state.db['Type'].str.contains('Entrée', case=False)]))
        col3.metric("Sorties", len(st.session_state.db[st.session_state.db['Type'].str.contains('Sortie', case=False)]))
        
        c1, c2 = st.columns(2)
        with c1:
            st.markdown("**📍 Missions par Bâtiment**")
            st.table(st.session_state.db['Batiment'].value_counts().rename_axis('Bâtiment').reset_index(name='Nombre'))
        with c2:
            st.markdown("**👤 Charge par Agent**")
            st.table(st.session_state.db['Agent'].value_counts().rename_axis('Agent').reset_index(name='Nombre'))
        
        st.divider()
        st.subheader("📥 Exportation")
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            st.session_state.db.to_excel(writer, index=False, sheet_name='Planning_Optimise')
        st.download_button(label="📥 Télécharger le planning final (Excel)", data=output.getvalue(), file_name=f"Planning_CHUV_{datetime.now().strftime('%d_%m')}.xlsx")
    else:
        st.warning("Importez un fichier Excel pour générer les rapports.")
