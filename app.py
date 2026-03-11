import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import io
import plotly.express as px  # Nécessaire pour le nouveau graphique

# --- CONFIGURATION ---
BUREAU = "Chemin Mont-Paisible 18, 1011 Lausanne"
AGENTS = ["Celine", "Maria Claret", "Maria Elisabeth"]

# Coordonnées pour la cartographie
INFOS_BATIMENTS = {
    'Bethusy A': {'rue': 'Avenue de Béthusy 54, Lausanne', 'lat': 46.5225, 'lon': 6.6472},
    'Bethusy B': {'rue': 'Avenue de Béthusy 56, Lausanne', 'lat': 46.5227, 'lon': 6.6475},
    'Montolieu A': {'rue': 'Isabelle-de-Montolieu 90, Lausanne', 'lat': 46.5412, 'lon': 6.6421},
    'Montolieu B': {'rue': 'Isabelle-de-Montolieu 92, Lausanne', 'lat': 46.5415, 'lon': 6.6425},
    'Tunnel': {'rue': 'Rue du Tunnel 17, Lausanne', 'lat': 46.5255, 'lon': 6.6328},
    'Oron': {'rue': "Route d'Oron 77, 1010 Lausanne", 'lat': 46.5361, 'lon': 6.6625}
}

COULEURS = {"Celine": "#d1e9ff", "Maria Claret": "#ffdae0", "Maria Elisabeth": "#d4f8d4", "À définir": "#eeeeee", "⚠️ SANS AGENT": "#333333"}

# Configuration de la page
st.set_page_config(page_title="Unité Logement - Gestion Planning", layout="wide", page_icon="📍")

# Injection de CSS pour affiner l'interface
st.markdown("""
    <style>
    /* Rendre les alertes plus compactes dans la vue agent */
    [data-testid="stNotification"] {
        padding: 8px;
        margin-bottom: 2px;
    }
    /* Style pour le tableau principal */
    .dataframe {
        font-size: 12px;
    }
    </style>
    """, unsafe_allow_html=True)

# Initialisation de la base de données en session
if 'db' not in st.session_state:
    st.session_state.db = pd.DataFrame(columns=['Batiment', 'Date', 'Heure', 'Agent', 'Rue', 'Type', 'Statut', 'Date_Sort'])

# --- FONCTIONS LOGIQUES ---

def calculer_creneau_securise(agent, date_str, temp_db, batiment_cible, bloc_impose=None, heure_forcee=None):
    """Calcule l'heure de passage en fonction des déplacements et contraintes."""
    m_jour = temp_db[(temp_db['Date'] == date_str) & (temp_db['Agent'] == agent)]
    
    # Mode Fixe : Vérification simple de conflit
    if heure_forcee:
        if not m_jour.empty and heure_forcee in [str(h) for h in m_jour['Heure'].values]:
            return "⚠️ CONFLIT", False
        return heure_forcee, True

    # Mode Optimisé : Calcul de l'heure
    if m_jour.empty:
        # Heure de démarrage par défaut selon le bloc
        h_depart_str = "08:15" if bloc_impose != "Après-midi" else "13:00"
    else:
        h_depart_str = str(m_jour.iloc[-1]['Heure']).strip()

    try:
        h_obj = datetime.strptime(h_depart_str, "%H:%M")
        rue_cible = INFOS_BATIMENTS.get(batiment_cible, {}).get('rue', "Autre")
        derniere_rue = m_jour.iloc[-1]['Rue'] if not m_jour.empty else "Bureau"
        
        # Calcul du délai de route (65min si même rue, 80min sinon)
        delai = 65 if derniere_rue == rue_cible else 80 
        prochaine_h = h_obj + timedelta(minutes=delai) if not m_jour.empty else h_obj
        
        # Gestion de la pause de midi (pas de RDV entre 12h et 13h)
        if datetime.strptime("12:00", "%H:%M") <= prochaine_h < datetime.strptime("13:00", "%H:%M"):
            prochaine_h = datetime.strptime("13:00", "%H:%M")
        
        # Vérification des limites de journée
        if bloc_impose == "Matin" and prochaine_h > datetime.strptime("11:45", "%H:%M"):
            return "COMPLET MATIN", False
        if prochaine_h > datetime.strptime("16:30", "%H:%M"):
            return "COMPLET JOUR", False
            
        return prochaine_h.strftime("%H:%M"), True
    except:
        # En cas d'erreur de parsing heure, on repart sur la base
        return "08:15", True

# --- INTERFACE ---
st.title("📍 Unité Logement : Planning & Rapports")
st.caption(f"📍 Siège social : {BUREAU}")

# Structure des onglets
t1, t2, t3 = st.tabs(["📝 Planning Global", "📅 Vue par Agent", "📊 Rapports & Analyses"])

# --- SIDEBAR : Import & Actions ---
with st.sidebar:
    st.header("📂 Importation")
    up = st.file_uploader("Fichier Excel des missions", type=['xlsx'])
    
    st.subheader("⚙️ Options d'attribution")
    mode_ia = st.radio("Méthode :", ["Respecter l'heure de l'Excel (Fixe)", "Optimiser par blocs (Matin / Après-midi)"])

    if up and st.button("🚀 Lancer l'Attribution"):
        with st.spinner("Calcul du planning optimisé..."):
            try:
                df_ex = pd.read_excel(up).dropna(how='all').fillna('')
                df_ex.columns = df_ex.columns.str.strip()
                
                # Mapping dynamique des colonnes (basé sur mots clés)
                c_date = next((c for c in df_ex.columns if 'date' in c.lower()), 'Date')
                c_heure = next((c for c in df_ex.columns if 'heure' in c.lower()), 'Heure')
                c_type = next((c for c in df_ex.columns if 'type' in c.lower()), 'Type')
                c_absent = next((c for c in df_ex.columns if 'absent' in c.lower()), None)
                c_statut = next((c for c in df_ex.columns if 'statut' in c.lower()), 'Statut')

                temp = pd.DataFrame(columns=['Batiment', 'Date', 'Heure', 'Agent', 'Rue', 'Type', 'Statut', 'Date_Sort'])
                
                # Tri chronologique pour l'attribution
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

                    # Détection contrainte bloc
                    bloc = "Matin" if "matin" in statut_val.lower() else ("Après-midi" if "midi" in statut_val.lower() else None)
                    
                    # Gestion des absences
                    absents = [a.strip().lower().replace('-', ' ') for a in str(row[c_absent]).split(';')] if c_absent and str(row[c_absent]).strip() != "" else []
                    presents = [a for a in AGENTS if a.lower().replace('-', ' ') not in absents]
                    
                    agt_elu = "⚠️ SANS AGENT"
                    h_finale = h_excel if h_excel else "08:15"
                    
                    if presents:
                        # Calcul score pour choisir l'agent (priorité si déjà sur place > moins chargé > premier dispo)
                        scores = {}
                        for p in presents:
                            missions_p_jour = temp[(temp['Date'] == ds) & (temp['Agent'] == p)]
                            if missions_p_jour.empty:
                                scores[p] = 1 # Dispo, commence la journée
                            elif missions_p_jour.iloc[-1]['Rue'] == rue_demandee:
                                scores[p] = 0 # Déjà sur place (priorité haute)
                            else:
                                scores[p] = 2 # Doit se déplacer

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
                    
                    # Ajout à la base temporaire
                    temp = pd.concat([temp, pd.DataFrame([{
                        'Batiment': row['Batiment'], 'Date': ds, 'Heure': h_finale, 'Agent': agt_elu, 
                        'Type': row[c_type], 'Rue': rue_demandee, 'Statut': statut_val, 'Date_Sort': dt_raw
                    }])], ignore_index=True)
                    
                st.session_state.db = temp
                st.success("Planning généré avec succès !")
                st.rerun()
            except Exception as e:
                st.error(f"Erreur lors du traitement : {e}")

    # Actions sur les données existantes
    if not st.session_state.db.empty:
        st.divider()
        st.subheader("📥 Export")
        output = io.BytesIO()
        df_export = st.session_state.db.sort_values(['Date_Sort', 'Heure']).drop(columns=['Date_Sort'])
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            df_export.to_excel(writer, index=False, sheet_name='Planning')
        
        st.download_button("📥 Télécharger le planning (Excel)", output.getvalue(), f"Planning_{datetime.now().strftime('%Y%m%d_%H%M')}.xlsx", mime="application/vnd.ms-excel")

        if st.button("🗑️ Effacer toutes les données", help="Supprime le planning actuel de la session"):
            st.session_state.db = pd.DataFrame(columns=['Batiment', 'Date', 'Heure', 'Agent', 'Rue', 'Type', 'Statut', 'Date_Sort'])
            st.rerun()

# --- ONGLET 1 : Vue Globale ---
with t1:
    if not st.session_state.db.empty:
        df_v = st.session_state.db.sort_values(['Date_Sort', 'Heure'])
        
        # Fonction de stylisation des lignes
        def style_row(s):
            if s['Heure'] == "⚠️ CONFLIT": return ['background-color: #ffcccc; color: #cc0000; font-weight: bold']*7
            if s['Agent'] == "⚠️ SANS AGENT": return ['background-color: #333333; color: white; font-weight: bold']*7
            color = COULEURS.get(s['Agent'], "#eeeeee")
            # Encadré orange si statut spécial (ex: "Matin imposé")
            if str(s['Statut']).strip() != "": return [f'background-color: {color}; border: 2px solid #ff9933']*7
            return [f'background-color: {color}; color: black']*7

        st.subheader("📅 Liste chronologique des missions")
        # Affichage du dataframe stylisé
        st.dataframe(
            df_v[['Date', 'Statut', 'Heure', 'Agent', 'Batiment', 'Type', 'Rue']].style.apply(style_row, axis=1),
            use_container_width=True, 
            height=500
        )
    else:
        st.info("💡 Importez un fichier Excel dans la barre latérale pour commencer.")

# --- ONGLET 2 : Vue par Agent ---
with t2:
    if not st.session_state.db.empty:
        # Tri des dates uniques pour le sélecteur
        dates_dispo = sorted(st.session_state.db['Date'].unique(), key=lambda x: datetime.strptime(x, '%d/%m/%Y'))
        
        c_sel1, c_sel2 = st.columns([1, 2])
        with c_sel1:
            sel_j = st.selectbox("📅 Sélectionner une date :", dates_dispo)
        
        st.divider()
        
        # Colonnes pour chaque agent
        cols = st.columns(len(AGENTS))
        for i, a in enumerate(AGENTS):
            with cols[i]:
                # Header Agent
                st.markdown(f"<div style='text-align:center; background-color:{COULEURS[a]}; padding:10px; border-radius:5px; color:black; font-weight:bold; margin-bottom:10px;'>{a}</div>", unsafe_allow_html=True)
                
                # Filtrage missions de l'agent pour le jour dit
                m = st.session_state.db[(st.session_state.db['Date'] == sel_j) & (st.session_state.db['Agent'] == a)].sort_values('Heure')
                
                if m.empty:
                    st.caption("Aucune mission")
                else:
                    for _, r in m.iterrows():
                        # Choix du type de boîte d'affichage
                        if r['Heure'] == "⚠️ CONFLIT":
                            st.error(f"🕒 **{r['Heure']}**\n\n🏠 **{r['Batiment']}**\n\nSymp: {r['Type']}")
                        elif r['Statut'] != "":
                            st.warning(f"🕒 **{r['Heure']}**\n\n🏠 **{r['Batiment']}**\n\n📌 {r['Statut']}")
                        else:
                            # Utilisation d'un container embeded pour styliser un peu
                            with st.container():
                                st.markdown(f"""
                                <div style='background-color:{COULEURS[a]}; padding:10px; border-radius:5px; border:1px solid #ccc; color:black; margin-bottom:5px;'>
                                🕒 <b>{r['Heure']}</b><br>
                                🏠 <b>{r['Batiment']}</b><br>
                                📝 {r['Type']}
                                </div>
                                """, unsafe_allow_html=True)
    else:
        st.info("💡 Importez des données pour visualiser les plannings individuels.")

# --- ONGLET 3 : Rapports & Graphiques ---
with t3:
    if not st.session_state.db.empty:
        df_rep = st.session_state.db.copy()
        # Création colonne Mois pour filtrage
        df_rep['Mois'] = df_rep['Date_Sort'].dt.strftime('%B %Y')
        
        # --- FILTRES DE L'ONGLET ---
        st.subheader("🔍 Filtres d'analyse")
        c_f1, c_f2 = st.columns(2)
        with c_f1:
            mois_sel = st.selectbox("📅 Choisir le mois :", df_rep['Mois'].unique(), index=0)
        
        # Filtrage par mois d'abord
        df_mois = df_rep[df_rep['Mois'] == mois_sel]
        
        with c_f2:
            agents_dispo = sorted(df_mois['Agent'].unique())
            # Selection par défaut : tous sauf "Sans Agent"
            def_agents = [ag for ag in agents_dispo if ag != "⚠️ SANS AGENT"]
            agents_sel = st.multiselect("👤 Filtrer par Agent :", agents_dispo, default=def_agents)

        # Application du filtre agent final
        df_final = df_mois[df_mois['Agent'].isin(agents_sel)]
        
        st.divider()

        if not df_final.empty:
            # --- MÉTRIQUES ---
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Total Missions", len(df_final))
            c2.metric("📈 Entrées/In", df_final[df_final['Type'].str.contains('Entrée|In', case=False)].shape[0])
            c3.metric("📉 Sorties/Out", df_final[df_final['Type'].str.contains('Sortie|Out', case=False)].shape[0])
            
            # Calcul jours travaillés (distincts)
            jours_trav = df_final['Date'].nunique()
            c4.metric("📅 Jours d'activité", jours_trav)
            
            st.divider()
            
            # --- NOUVEAU : GRAPHIQUE DE CHARGE HEBDOMADAIRE ---
  # --- CORRECTION : GRAPHIQUE DE CHARGE HEBDOMADAIRE ---
            st.subheader("📊 Charge de travail hebdomadaire")
            
            df_chart = df_final.copy()
            # On s'assure que la date est bien reconnue
            df_chart['Date_Sort'] = pd.to_datetime(df_chart['Date_Sort'])
            # On extrait le numéro de semaine
            df_chart['Semaine'] = df_chart['Date_Sort'].dt.isocalendar().week
            df_chart['Nom_Semaine'] = "Semaine " + df_chart['Semaine'].astype(str)

            if not df_chart.empty:
                # On crée le graphique directement à partir de df_chart
                # Plotly va compter les lignes tout seul avec 'count'
                fig = px.histogram(
                    df_chart, 
                    x='Nom_Semaine', 
                    color='Agent',
                    title=f"Nombre total de missions : {len(df_chart)}",
                    color_discrete_map=COULEURS,
                    barmode='group',
                    text_auto=True # Cette option compte et affiche le total automatiquement
                )
                
                fig.update_layout(
                    xaxis_title="Semaine",
                    yaxis_title="Nombre de Missions",
                    legend_title="Agent",
                    xaxis={'categoryorder':'category ascending'} # Garde les semaines dans l'ordre
                )
                
                st.plotly_chart(fig, use_container_width=True)
                # Création du graphique Plotly Express
# Création du graphique Plotly Express corrigé
                fig = px.bar(
                    grp_wk, 
                    x='Nom_Semaine', 
                    y='Nb_Missions', 
                    color='Agent',
                    title=f"Répartition des missions par semaine ({mois_sel})",
                    color_discrete_map=COULEURS,
                    text='Nb_Missions',  # <-- Corrigé ici (on utilise 'text' au lieu de 'text_value')
                    barmode='group'
                )
                
                # Amélioration du layout
                fig.update_layout(
                    xaxis_title="Semaine",
                    yaxis_title="Nombre de Missions",
                    legend_title="Agent",
                    uniformtext_minsize=8, uniformtext_mode='hide'
                )
                fig.update_traces(texttemplate='%{y}', textposition='outside')
                
                # Affichage dans Streamlit
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.write("Pas assez de données pour générer le graphique hebdomadaire.")

            st.divider()
            
            # --- SECTION BASSE : TABLEAU & CARTE ---
            col_left, col_right = st.columns([1, 1])
            
            # Statistiques par bâtiment
            stats_bat = df_final.groupby('Batiment').size().reset_index(name='Missions').sort_values('Missions', ascending=False)

            with col_left:
                st.subheader("🏠 Volume par bâtiment")
                if not stats_bat.empty:
                    # Affichage table propre
                    st.dataframe(stats_bat, use_container_width=True, hide_index=True)
                else:
                    st.write("Aucune donnée pour cette sélection.")

            with col_right:
                st.subheader("📍 Cartographie des interventions")
                map_data = []
                for _, row in stats_bat.iterrows():
                    nom_bat = row['Batiment']
                    if nom_bat in INFOS_BATIMENTS:
                        map_data.append({
                            'lat': float(INFOS_BATIMENTS[nom_bat]['lat']),
                            'lon': float(INFOS_BATIMENTS[nom_bat]['lon']),
                            'Missions': int(row['Missions']),
                            'Nom': nom_bat
                        })
                
                if map_data:
                    df_map = pd.DataFrame(map_data)
                    # Calcul taille des points sur la carte
                    df_map['taille_point'] = (df_map['Missions'] * 15).astype(float)
                    
                    st.map(
                        df_map, 
                        latitude='lat', 
                        longitude='lon', 
                        size='taille_point', 
                        color="#FF4B4B" # Couleur rouge Streamlit
                    )
                else:
                    st.info("Aucune donnée géographique (coordonnées lat/lon) pour les bâtiments sélectionnés ce mois-ci.")
        else:
             st.warning("Aucune donnée ne correspond aux filtres sélectionnés (Mois/Agents).")
    else:
        st.info("💡 Veuillez importer des données pour générer les rapports et analyses.")

# Bas de page
st.divider()
st.caption(f"v3.1 - Edition Analyses Graphiques | {datetime.now().strftime('%Y')}")
