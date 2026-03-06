import streamlit as st
import pandas as pd
from datetime import datetime, timedelta

# --- CONFIGURATION FIXE ---
BUREAU = "Chemin Mont Paisible 18, 1011 Lausanne"
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

st.set_page_config(page_title="Unité Logement - Expert", layout="wide")

if 'db' not in st.session_state:
    st.session_state.db = pd.DataFrame(columns=['Batiment', 'Date', 'Heure', 'Agent', 'Rue', 'Type', 'Date_Sort'])
if 'conges' not in st.session_state:
    st.session_state.conges = pd.DataFrame(columns=['Agent', 'Date_Debut', 'Date_Fin'])

# --- FONCTIONS LOGIQUES ---

def est_disponible(agent, date_str):
    if st.session_state.conges.empty: return True
    try:
        dt_cible = pd.to_datetime(date_str, dayfirst=True)
        for _, c in st.session_state.conges[st.session_state.conges['Agent'] == agent].iterrows():
            if pd.to_datetime(c['Date_Debut'], dayfirst=True) <= dt_cible <= pd.to_datetime(c['Date_Fin'], dayfirst=True): return False
    except: pass
    return True

def calculer_creneau_securise(agent, date_str, temp_db):
    """Calcule l'heure et vérifie qu'on ne dépasse pas 16h30 pour le début du dernier RDV."""
    m_jour = temp_db[(temp_db['Date'] == date_str) & (temp_db['Agent'] == agent)]
    
    if m_jour.empty:
        return "08:15", True
    
    derniere_h_str = str(m_jour.iloc[-1]['Heure']).strip()
    try:
        heure_obj = datetime.strptime(derniere_h_str, "%H:%M")
        # 1h entretien + 15 min trajet
        prochaine_h = heure_obj + timedelta(hours=1, minutes=15)
        
        # Gestion pause déjeuner
        if datetime.strptime("12:00", "%H:%M") <= prochaine_h < datetime.strptime("13:00", "%H:%M"):
            prochaine_h = datetime.strptime("13:00", "%H:%M")
            
        # SÉCURITÉ : Pas de nouveau RDV si le début est après 16h15
        if prochaine_h > datetime.strptime("16:15", "%H:%M"):
            return "COMPLET", False
            
        return prochaine_h.strftime("%H:%M"), True
    except:
        return "08:15", True

# --- INTERFACE ---
st.title("📍 Unité Logement : Planification & Respect des Horaires")
t1, t2, t3 = st.tabs(["📝 Planning", "📅 Calendrier", "📊 Analyses"])

with st.sidebar:
    st.header("🌴 Gestion")
    abs_agt = st.selectbox("Agent", AGENTS)
    d1, d2 = st.date_input("Du"), st.date_input("Au")
    if st.button("Valider Congé"):
        st.session_state.conges = pd.concat([st.session_state.conges, pd.DataFrame([{'Agent': abs_agt, 'Date_Debut': d1.strftime('%d/%m/%Y'), 'Date_Fin': d2.strftime('%d/%m/%Y')}])], ignore_index=True)
    
    st.divider()
    up = st.file_uploader("Fichier Excel", type=['xlsx'])
    if up and st.button("🚀 Planifier"):
        df_ex = pd.read_excel(up).dropna(how='all').fillna('')
        df_ex.columns = df_ex.columns.str.strip()
        
        c_date = next((c for c in df_ex.columns if 'date' in c.lower()), 'Date')
        c_heure = next((c for c in df_ex.columns if 'heure' in c.lower()), 'Heure')
        c_type = next((c for c in df_ex.columns if 'type' in c.lower()), 'Type')

        temp = pd.DataFrame(columns=['Batiment', 'Date', 'Heure', 'Agent', 'Rue', 'Type', 'Date_Sort'])
        for _, row in df_ex.sort_values(by=[c_date]).iterrows():
            ds = pd.to_datetime(row[c_date]).strftime('%d/%m/%Y')
            
            # Répartition équilibrée avec vérification de l'heure de fin
            presents = [a for a in AGENTS if est_disponible(a, ds)]
            agt_elu = "À définir"
            h_finale = "08:15"
            
            # On trie les agents par ceux qui ont le moins de dossiers pour équilibrer
            if presents:
                charges = {a: len(temp[(temp['Date'] == ds) & (temp['Agent'] == a)]) for a in presents}
                presents_tries = sorted(charges, key=charges.get)
                
                for p in presents_tries:
                    heure_suggere, possible = calculer_creneau_securise(p, ds, temp)
                    if possible:
                        agt_elu = p
                        h_finale = heure_suggere
                        break
            
            # Si l'heure est imposée par l'Excel, on la garde
            h_val = str(row[c_heure]).strip()
            if h_val not in ["", "nan", "00:00:00", "libre"]:
                h_finale = h_val[:5]

            temp = pd.concat([temp, pd.DataFrame([{
                'Batiment': row['Batiment'], 'Date': ds, 'Heure': h_finale, 'Agent': agt_elu, 
                'Type': row[c_type], 'Rue': INFOS_BATIMENTS.get(row['Batiment'], "Autre"), 
                'Date_Sort': pd.to_datetime(row[c_date])
            }])], ignore_index=True)
        st.session_state.db = temp; st.rerun()

    if st.button("🗑️ Reset"):
        st.session_state.db = pd.DataFrame(columns=['Batiment', 'Date', 'Heure', 'Agent', 'Rue', 'Type', 'Date_Sort'])
        st.rerun()

# --- ONGLETS ---
with t1:
    if not st.session_state.db.empty:
        df_v = st.session_state.db.sort_values(['Date_Sort', 'Heure'])
        st.table(df_v[['Date', 'Heure', 'Agent', 'Batiment', 'Type']].style.apply(lambda r: [f'background-color: {COULEURS.get(r["Agent"])}']*len(r), axis=1))

with t3:
    if not st.session_state.db.empty:
        st.subheader("📊 Analyses de Performance")
        
        nb_total = len(st.session_state.db)
        # Calcul taux opti : dossiers dans la même rue le même jour
        group_rue = st.session_state.db.groupby(['Date', 'Rue']).size()
        taux_opti = (len(group_rue[group_rue > 1]) / nb_total * 100) if nb_total > 0 else 0
        
        c1, c2 = st.columns(2)
        c1.metric("Total Missions", nb_total)
        c2.metric("Taux d'Optimisation", f"{int(taux_opti)}%")

        st.divider()
        sel_j = st.selectbox("Analyse détaillée du :", sorted(st.session_state.db['Date'].unique()), key="stats")
        day_d = st.session_state.db[st.session_state.db['Date'] == sel_j]
        
        for a in AGENTS:
            agt_d = day_d[day_d['Agent'] == a].sort_values('Heure')
            if not agt_d.empty:
                st.markdown(f"#### 👩‍💻 {a}")
                nb_e = len(agt_d[agt_d['Type'].str.contains('Entrée', case=False, na=False)])
                nb_s = len(agt_d[agt_d['Type'].str.contains('Sortie', case=False, na=False)])
                itin = [BUREAU] + agt_d['Rue'].tolist() + [BUREAU]
                t_route = sum([15 if itin[k] != itin[k+1] else 5 for k in range(len(itin)-1)])
                
                col_x, col_y = st.columns(2)
                col_x.write(f"🏠 **Terrain : {len(agt_d)}h00** | 🚗 **Route : {t_route} min**")
                col_y.write(f"📥 **Entrées : {nb_e}** | 📤 **Sorties : {nb_s}**")
                st.divider()
