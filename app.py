import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import io
import numpy as np

# --- CONFIGURATION ---
BUREAU_ADRESSE = "Chemin Mont-Paisible 18, 1011 Lausanne"
BUREAU_GPS = (46.5332, 6.6135) 
AGENTS = ["Celine", "Maria Claret", "Maria Elisabeth"]

INFOS_BATIMENTS = {
    'Bethusy A': {'rue': 'Avenue de Béthusy 54, Lausanne', 'lat': 46.5225, 'lon': 6.6472},
    'Bethusy B': {'rue': 'Avenue de Béthusy 56, Lausanne', 'lat': 46.5227, 'lon': 6.6475},
    'Montolieu A': {'rue': 'Isabelle-de-Montolieu 90, Lausanne', 'lat': 46.5412, 'lon': 6.6421},
    'Montolieu B': {'rue': 'Isabelle-de-Montolieu 92, Lausanne', 'lat': 46.5415, 'lon': 6.6425},
    'Tunnel': {'rue': 'Rue du Tunnel 17, Lausanne', 'lat': 46.5255, 'lon': 6.6328},
    'Oron': {'rue': "Route d'Oron 77, 1010 Lausanne", 'lat': 46.5361, 'lon': 6.6625}
}

SECTEURS = {
    'Bethusy': ['Bethusy A', 'Bethusy B'],
    'Montolieu': ['Montolieu A', 'Montolieu B'],
    'Tunnel': ['Tunnel'],
    'Oron': ['Oron']
}

COULEURS = {"Celine": "#d1e9ff", "Maria Claret": "#ffdae0", "Maria Elisabeth": "#d4f8d4", "⚠️ SANS AGENT": "#333333"}

def trouver_secteur(batiment):
    for secteur, liste in SECTEURS.items():
        if batiment in liste: return secteur
    return "Autre"

st.set_page_config(page_title="Unité Logement - Gestion Planning", layout="wide", page_icon="📍")

if 'db' not in st.session_state:
    st.session_state.db = pd.DataFrame(columns=['ID', 'Batiment', 'Date', 'Heure', 'Agent', 'Rue', 'Type', 'Statut', 'Date_Sort'])

# --- LOGIQUE DE CRÉNEAU ---
def calculer_creneau(agent, date_str, temp_db, batiment_cible, bloc_impose):
    m_jour = temp_db[(temp_db['Date'] == date_str) & (temp_db['Agent'] == agent)]
    h_start = "08:15" if bloc_impose == "Matin" else "13:00"
    h_limit = "11:45" if bloc_impose == "Matin" else "16:30"
    
    if m_jour.empty:
        prochaine_h = datetime.strptime(h_start, "%H:%M")
    else:
        derniere_h = datetime.strptime(str(m_jour.iloc[-1]['Heure']), "%H:%M")
        if bloc_impose == "Après-midi" and derniere_h < datetime.strptime("13:00", "%H:%M"):
            prochaine_h = datetime.strptime("13:00", "%H:%M")
        else:
            rue_actuelle = INFOS_BATIMENTS.get(batiment_cible, {}).get('rue', "")
            delai = 65 if m_jour.iloc[-1]['Rue'] == rue_actuelle else 85
            prochaine_h = derniere_h + timedelta(minutes=delai)

    if prochaine_h > datetime.strptime(h_limit, "%H:%M"):
        return "COMPLET", False
    return prochaine_h.strftime("%H:%M"), True

# --- INTERFACE ---
st.title("📍 Unité Logement : Planning & Rapports")

t1, t2, t3 = st.tabs(["📝 Planning Global", "📅 Vue par Agent", "📊 Rapports"])

with st.sidebar:
    st.header("📂 Importation")
    up = st.file_uploader("Fichier Excel", type=['xlsx'])
    
    if up and st.button("🚀 Lancer l'Attribution"):
        try:
            df_ex = pd.read_excel(up).dropna(how='all').fillna('')
            df_ex.columns = df_ex.columns.str.strip()
            
            # Identification colonnes
            c_id = next((c for c in df_ex.columns if 'id' in c.lower() or 'n°' in c.lower()), df_ex.columns[0])
            c_date = next((c for c in df_ex.columns if 'date' in c.lower()), 'Date')
            c_statut = next((c for c in df_ex.columns if 'statut' in c.lower()), 'Statut')
            c_absent = next((c for c in df_ex.columns if 'absent' in c.lower()), None)
            
            temp = pd.DataFrame(columns=['ID', 'Batiment', 'Date', 'Heure', 'Agent', 'Rue', 'Type', 'Statut', 'Date_Sort'])
            df_ex[c_date] = pd.to_datetime(df_ex[c_date])
            
            # Traitement par jour
            for jour in sorted(df_ex[c_date].unique()):
                ds = pd.to_datetime(jour).strftime('%d/%m/%Y')
                df_j = df_ex[df_ex[c_date] == jour].copy()
                df_j['Secteur'] = df_j['Batiment'].apply(trouver_secteur)
                
                # Distribution par secteur pour grouper les agents au même endroit
                for secteur in df_j['Secteur'].unique():
                    df_s = df_j[df_j['Secteur'] == secteur]
                    
                    # On fait tourner les agents disponibles pour équilibrer le bâtiment
                    idx_agt = 0
                    for _, row in df_s.iterrows():
                        bloc = "Après-midi" if "midi" in str(row[c_statut]).lower() else "Matin"
                        absents = [a.strip().lower() for a in str(row[c_absent]).split(';')] if c_absent else []
                        presents = [a for a in AGENTS if a.lower() not in absents]
                        
                        agt_elu, h_finale = "⚠️ SANS AGENT", "08:15"
                        if presents:
                            for _ in range(len(presents)):
                                p = presents[idx_agt % len(presents)]
                                res_h, possible = calculer_creneau(p, ds, temp, row['Batiment'], bloc)
                                if possible:
                                    agt_elu, h_finale = p, res_h
                                    idx_agt += 1
                                    break
                                idx_agt += 1

                        new_row = pd.DataFrame([{
                            'ID': row[c_id], 'Batiment': row['Batiment'], 'Date': ds, 'Heure': h_finale, 
                            'Agent': agt_elu, 'Type': row.get('Type', 'Mission'), 
                            'Rue': INFOS_BATIMENTS.get(row['Batiment'], {}).get('rue', ''), 
                            'Statut': bloc, 'Date_Sort': jour
                        }])
                        temp = pd.concat([temp, new_row], ignore_index=True)

            st.session_state.db = temp
            st.rerun()
        except Exception as e:
            st.error(f"Erreur de lecture : {e}")

# --- AFFICHAGE ---
if not st.session_state.db.empty:
    with t1:
        st.dataframe(st.session_state.db[['ID', 'Date', 'Statut', 'Heure', 'Agent', 'Batiment', 'Type']].sort_values(['Date_Sort', 'Heure']), use_container_width=True)
    
    with t2:
        sel_j = st.selectbox("Sélectionner une date :", sorted(st.session_state.db['Date'].unique()))
        cols = st.columns(len(AGENTS))
        for i, a in enumerate(AGENTS):
            with cols[i]:
                st.markdown(f"<div style='text-align:center; background-color:{COULEURS[a]}; padding:10px; border-radius:5px; font-weight:bold;'>{a}</div>", unsafe_allow_html=True)
                m = st.session_state.db[(st.session_state.db['Date'] == sel_j) & (st.session_state.db['Agent'] == a)].sort_values('Heure')
                for _, r in m.iterrows():
                    st.markdown(f"<div style='background-color:{COULEURS[a]}; padding:8px; border-radius:5px; border:1px solid #ccc; margin-top:5px;'>🆔 {r['ID']}<br>🕒 <b>{r['Heure']}</b><br>🏠 {r['Batiment']}</div>", unsafe_allow_html=True)
else:
    st.info("Veuillez importer un fichier Excel pour générer le planning.")

if st.sidebar.button("🗑️ Reset"):
    st.session_state.db = pd.DataFrame(columns=['ID', 'Batiment', 'Date', 'Heure', 'Agent', 'Rue', 'Type', 'Statut', 'Date_Sort'])
    st.rerun()
