import streamlit as st
import pandas as pd
from datetime import datetime
import io
import plotly.express as px

from ui.styles import appliquer_styles
from modules.recommandation import recommander_logements
from modules.data_loader import charger_logements
from config.settings import (
    AGENTS,
    BUREAU_ADRESSE,
    BUREAU_GPS,
    COULEURS,
    INFOS_BATIMENTS,
    SECTEURS
)
from modules.distance import calculer_distance
from modules.calendar import generer_ics
from modules.scheduler import calculer_creneau


def reset_recherche_ia():
    st.session_state["ai_ville"] = "Toutes"
    st.session_state["ai_type_objet"] = "Tous"
    st.session_state["ai_loyer_min"] = 0.0
    st.session_state["ai_loyer_max"] = 700.0
    st.session_state["ai_parking"] = "Non"
    st.session_state["ai_piquet"] = "Non"
    st.session_state["ai_accompagne_2"] = "Non"
    st.session_state["ai_accompagne_plus_2"] = "Non"
    st.session_state["ai_demande"] = ""
    st.session_state["ai_resultats_df"] = pd.DataFrame()


@st.cache_data
def charger_excel(file):
    return pd.read_excel(file)


st.set_page_config(
    page_title="Unité Logement - 2.0",
    layout="wide",
    page_icon="📍"
)

appliquer_styles()


# --- FONCTIONS TECHNIQUES ---
def trouver_secteur(batiment):
    for secteur, liste in SECTEURS.items():
        if batiment in liste:
            return secteur
    return batiment


# --- SESSION STATE ---
if "ai_ville" not in st.session_state:
    st.session_state.ai_ville = "Toutes"

if "ai_type_objet" not in st.session_state:
    st.session_state.ai_type_objet = "Tous"

if "ai_loyer_min" not in st.session_state:
    st.session_state.ai_loyer_min = 0.0

if "ai_loyer_max" not in st.session_state:
    st.session_state.ai_loyer_max = 700.0

if "ai_parking" not in st.session_state:
    st.session_state.ai_parking = "Non"

if "ai_piquet" not in st.session_state:
    st.session_state.ai_piquet = "Non"

if "ai_accompagne_2" not in st.session_state:
    st.session_state.ai_accompagne_2 = "Non"

if "ai_accompagne_plus_2" not in st.session_state:
    st.session_state.ai_accompagne_plus_2 = "Non"

if "ai_demande" not in st.session_state:
    st.session_state.ai_demande = ""

if "ai_resultats_df" not in st.session_state:
    st.session_state.ai_resultats_df = pd.DataFrame()

if "db" not in st.session_state:
    st.session_state.db = pd.DataFrame(
        columns=["ID", "Batiment", "Date", "Heure", "Agent", "Rue", "Type", "Statut", "Date_Sort"]
    )

if "logements" not in st.session_state:
    st.session_state.logements = pd.DataFrame()

if "attributions" not in st.session_state:
    st.session_state.attributions = pd.DataFrame(columns=[
        "Nom",
        "Prénom",
        "Sexe",
        "Fonction",
        "Bâtiment",
        "Studio",
        "Type objet",
        "Prix logement",
        "Nom 2ème personne",
        "Parc",
        "Type parc",
        "Prix parc",
        "Facture",
        "Salaire",
        "Ancien locataire"
    ])


# --- INTERFACE ---
st.title("📍 Unité Logement : 2.0")

t0, t_ai, t_attrib, t1, t2, t3 = st.tabs([
    "🏠 Logements vacants",
    "🤖 Recherche intelligente",
    "📝 Attribution logement",
    "📝 Planning Global",
    "📅 Vue par Agent",
    "📊 Rapports & Analyses"
])


# --- SIDEBAR ---
with st.sidebar:
    st.header("📂 Importation")
    st.caption("Formats acceptés : XLSX")

    up = st.file_uploader(
        "Déposer le fichier des missions",
        type=["xlsx"],
        key="upload_missions"
    )

    st.subheader("🏠 Logements vacants")
    st.caption("Formats acceptés : CSV ou XLSX")

    up_logements = st.file_uploader(
        "Déposer la liste des appartements vacants",
        type=["csv", "xlsx"],
        key="upload_logements"
    )

    if up_logements and st.button("🏠 Charger les logements", key="btn_charger_logements"):
        try:
            df_logements = charger_logements(up_logements)
            st.session_state.logements = df_logements
            st.success("Liste des logements chargée")
        except Exception as e:
            st.error(f"Erreur logements : {e}")

    if up and st.button("🚀 Lancer l'Attribution", key="btn_lancer_attribution"):
        try:
            df_ex = charger_excel(up).dropna(how="all").fillna("")
            df_ex.columns = df_ex.columns.str.strip()

            c_id = next((c for c in df_ex.columns if "id" in c.lower() or "n°" in c.lower()), df_ex.columns[0])
            c_date = next((c for c in df_ex.columns if "date" in c.lower()), "Date")
            c_statut = next((c for c in df_ex.columns if "statut" in c.lower()), "Statut")
            c_absent = next((c for c in df_ex.columns if "absent" in c.lower()), None)
            c_type = next((c for c in df_ex.columns if "type" in c.lower()), "Type")
            c_bat = next((c for c in df_ex.columns if "bat" in c.lower() or "bât" in c.lower()), "Batiment")

            temp_rows = []
            df_ex[c_date] = pd.to_datetime(df_ex[c_date], errors="coerce")
            df_ex = df_ex.dropna(subset=[c_date])

            for jour in sorted(df_ex[c_date].unique()):
                ds = pd.to_datetime(jour).strftime("%d/%m/%Y")
                df_j = df_ex[df_ex[c_date] == jour].copy()

                for bat_nom in df_j[c_bat].unique():
                    df_b = df_j[df_j[c_bat] == bat_nom]
                    idx_agt = 0

                    for _, row in df_b.iterrows():
                        bloc = "Après-midi" if "midi" in str(row[c_statut]).lower() else "Matin"
                        absents = [a.strip().lower() for a in str(row[c_absent]).split(";")] if c_absent else []
                        presents = [a for a in AGENTS if a.lower() not in absents]

                        agt_elu, h_fin = "⚠️ SANS AGENT", "08:15"

                        if presents:
                            db_actuel = (
                                pd.DataFrame(temp_rows)
                                if temp_rows
                                else pd.DataFrame(columns=["Date", "Agent", "Heure", "Rue"])
                            )

                            for _ in range(len(presents)):
                                p = presents[idx_agt % len(presents)]
                                res_h, possible = calculer_creneau(p, ds, db_actuel, bat_nom, bloc)

                                if possible:
                                    agt_elu, h_fin = p, res_h
                                    idx_agt += 1
                                    break

                                idx_agt += 1

                        temp_rows.append({
                            "ID": row[c_id],
                            "Batiment": bat_nom,
                            "Date": ds,
                            "Heure": h_fin,
                            "Agent": agt_elu,
                            "Type": str(row[c_type]),
                            "Rue": INFOS_BATIMENTS.get(bat_nom, {}).get("rue", ""),
                            "Statut": bloc,
                            "Date_Sort": jour
                        })

            st.session_state.db = pd.DataFrame(temp_rows)
            st.rerun()

        except Exception as e:
            st.error(f"Erreur missions : {e}")

    if st.button("🗑️ Reset", key="btn_reset"):
        st.session_state.db = pd.DataFrame(
            columns=["ID", "Batiment", "Date", "Heure", "Agent", "Rue", "Type", "Statut", "Date_Sort"]
        )
        st.session_state.logements = pd.DataFrame()
        st.session_state.attributions = pd.DataFrame(columns=[
            "Nom",
            "Prénom",
            "Sexe",
            "Fonction",
            "Bâtiment",
            "Studio",
            "Type objet",
            "Prix logement",
            "Nom 2ème personne",
            "Parc",
            "Type parc",
            "Prix parc",
            "Facture",
            "Salaire",
            "Ancien locataire"
        ])
        reset_recherche_ia()
        st.rerun()


# --- ONGLET LOGEMENTS ---
with t0:
    st.subheader("🏠 Logements disponibles")

    if not st.session_state.logements.empty:
        df_log = st.session_state.logements.copy()

        recherche = st.text_input(
            "🔎 Recherche rapide",
            placeholder="Ex: Lausanne, Montolieu, N° Studio...",
            key="vacants_recherche"
        )

        col1, col2, col3 = st.columns(3)

        with col1:
            villes = ["Toutes"] + sorted(df_log["Ville"].dropna().astype(str).unique().tolist())
            ville_sel = st.selectbox("Ville", villes, key="vacants_ville")

        with col2:
            immeubles = ["Tous"] + sorted(df_log["Adresse"].dropna().astype(str).unique().tolist())
            immeuble_sel = st.selectbox("Adresse / Immeuble", immeubles, key="vacants_immeuble")

        with col3:
            types_objet = ["Tous"] + sorted(df_log["Type objet"].dropna().astype(str).unique().tolist())
            type_objet_sel = st.selectbox("Type d'objet", types_objet, key="vacants_type_objet")

        df_filtre = df_log.copy()

        if ville_sel != "Toutes":
            df_filtre = df_filtre[df_filtre["Ville"].astype(str) == ville_sel]

        if immeuble_sel != "Tous":
            df_filtre = df_filtre[df_filtre["Adresse"].astype(str) == immeuble_sel]

        if type_objet_sel != "Tous":
            df_filtre = df_filtre[df_filtre["Type objet"].astype(str) == type_objet_sel]

        if recherche:
            recherche = recherche.lower()
            colonnes_recherche = ["Ville", "Adresse", "Type objet", "Référence interne", "Numéro unique"]

            masque = pd.Series(False, index=df_filtre.index)
            for col in colonnes_recherche:
                if col in df_filtre.columns:
                    masque = masque | df_filtre[col].astype(str).str.lower().str.contains(recherche, na=False)

            df_filtre = df_filtre[masque]

        c1, c2 = st.columns(2)
        c1.metric("Logements trouvés", len(df_filtre))
        c2.metric("Immeubles distincts", df_filtre["Adresse"].nunique() if "Adresse" in df_filtre.columns else 0)

        st.data_editor(
            df_filtre,
            use_container_width=True,
            disabled=True,
            key="vacants_tableau"
        )

        if "Adresse" in df_filtre.columns:
            st.markdown("### 📊 Répartition par immeuble")
            repartition = (
                df_filtre["Adresse"]
                .value_counts()
                .reset_index()
            )
            repartition.columns = ["Adresse", "Nombre de logements"]
            st.dataframe(repartition, use_container_width=True)

    else:
        st.info("Aucune liste de logements chargée.")


# --- ONGLET IA ---
with t_ai:
    st.subheader("🤖 Recherche intelligente de logements")

    if not st.session_state.logements.empty:
        df_log = st.session_state.logements.copy()

        col1, col2 = st.columns(2)

        with col1:
            villes = ["Toutes"] + sorted(df_log["Ville"].dropna().astype(str).unique().tolist())
            ville = st.selectbox("Ville souhaitée", villes, key="ai_ville")

            type_objet = st.selectbox(
                "Type d'objet",
                ["Tous"] + sorted(df_log["Type objet"].dropna().astype(str).unique().tolist()),
                key="ai_type_objet"
            )

            loyer_min = st.number_input(
                "Loyer minimum",
                min_value=0.0,
                step=50.0,
                key="ai_loyer_min"
            )

            loyer_max = st.number_input(
                "Loyer maximum",
                min_value=0.0,
                step=50.0,
                key="ai_loyer_max"
            )

        with col2:
            parking = st.radio("Parking", ["Non", "Oui"], key="ai_parking")
            piquet = st.radio("Piquet", ["Non", "Oui"], key="ai_piquet")
            accompagne_2 = st.radio("Accompagné à 2 personnes", ["Non", "Oui"], key="ai_accompagne_2")
            accompagne_plus_2 = st.radio("Accompagné à plus de 2 personnes", ["Non", "Oui"], key="ai_accompagne_plus_2")

        demande = st.text_area(
            "Demande utilisateur",
            placeholder="Ex: 1 personne, parking, piquet",
            key="ai_demande"
        )

        colA, colB = st.columns(2)

        with colA:
            if st.button("🔎 Chercher les meilleurs logements", key="ai_btn_recherche"):
                criteres = {
                    "ville": ville,
                    "type_objet": type_objet,
                    "loyer_min": loyer_min,
                    "loyer_max": loyer_max,
                    "parking": parking,
                    "piquet": piquet,
                    "accompagne_2": accompagne_2,
                    "accompagne_plus_2": accompagne_plus_2,
                    "mot_cle": demande
                }

                resultats = recommander_logements(df_log, criteres, top_n=3)
                st.session_state["ai_resultats_df"] = resultats.copy()
        with colB:
            st.button(
                "♻️ Reset recherche",
                key="ai_reset",
                on_click=reset_recherche_ia
            )

        if "ai_resultats_df" in st.session_state:
            if st.session_state["ai_resultats_df"].empty:
                st.warning("Aucun logement correspondant.")
            else:
                st.success("Voici les meilleurs logements proposés :")

                df_affichage = st.session_state["ai_resultats_df"].copy()

                colonnes_a_supprimer = [
                    "Type exploitation",
                    "date_fifo",
                    "score"
                ]

                df_affichage = df_affichage.drop(columns=colonnes_a_supprimer, errors="ignore")

                st.data_editor(
                    df_affichage,
                    use_container_width=True,
                    disabled=True,
                    key="ai_resultats"
                )


# --- ONGLET ATTRIBUTION ---
with t_attrib:
    st.subheader("📝 Formulaire d'attribution")

    if not st.session_state.logements.empty:
        df_log = st.session_state.logements.copy()

        logements_options = df_log["Numéro unique"].dropna().astype(str).tolist()

        logement_selectionne = st.selectbox(
            "Choisir un logement",
            logements_options,
            key="attrib_logement"
        )

        logement_info = df_log[df_log["Numéro unique"].astype(str) == logement_selectionne].iloc[0]

        st.markdown("### 🏠 Informations du logement")
        st.write("**Bâtiment / Adresse :**", logement_info.get("Adresse", ""))
        st.write("**Ville :**", logement_info.get("Ville", ""))
        st.write("**Type objet :**", logement_info.get("Type objet", ""))
        st.write("**Surface :**", logement_info.get("Surface", ""))

        st.markdown("### 👤 Informations du locataire")
        col1, col2 = st.columns(2)

        with col1:
            nom = st.text_input("Nom", key="attrib_nom")
            prenom = st.text_input("Prénom", key="attrib_prenom")
            sexe = st.radio("Sexe", ["Masculin", "Féminin"], key="attrib_sexe")

        with col2:
            fonction = st.text_input("Fonction", key="attrib_fonction")
            nom_2eme = st.text_input("Nom pour la 2ème personne", key="attrib_nom2")
            ancien_locataire = st.text_input("Nom de l'ancien locataire", key="attrib_ancien")

        st.markdown("### 🚗 Place de parc et administratif")
        col3, col4 = st.columns(2)

        with col3:
            parc = st.text_input("Parc #", key="attrib_parc")
            type_parc = st.radio("Type de parc", ["Intérieur", "Extérieur"], key="attrib_type_parc")
            prix_parc = st.number_input("Prix parc", min_value=0.0, value=0.0, key="attrib_prix_parc")

        with col4:
            facture = st.text_input("Facture", key="attrib_facture")
            salaire = st.text_input("Salaire", key="attrib_salaire")

        if st.button("✅ Valider l'attribution", key="attrib_valider"):
            nouvelle_attribution = pd.DataFrame([{
                "Nom": nom,
                "Prénom": prenom,
                "Sexe": sexe,
                "Fonction": fonction,
                "Bâtiment": logement_info.get("Adresse", ""),
                "Studio": logement_info.get("Numéro unique", ""),
                "Type objet": logement_info.get("Type objet", ""),
                "Prix logement": logement_info.get("Prix", logement_info.get("Loyer Net", "")),
                "Nom 2ème personne": nom_2eme,
                "Parc": parc,
                "Type parc": type_parc,
                "Prix parc": prix_parc,
                "Facture": facture,
                "Salaire": salaire,
                "Ancien locataire": ancien_locataire
            }])

            st.session_state.attributions = pd.concat(
                [st.session_state.attributions, nouvelle_attribution],
                ignore_index=True
            )

            st.success("Attribution enregistrée avec succès.")

        st.markdown("### 📋 Attributions enregistrées")
        st.dataframe(st.session_state.attributions, use_container_width=True)

    else:
        st.warning("Charge d'abord la liste des logements vacants dans la sidebar.")


# --- ONGLETS PLANNING / RAPPORTS ---
if not st.session_state.db.empty:

    with t1:
        df_v = st.session_state.db.sort_values(["Date_Sort", "Heure"])

        def style_agent(row):
            color = COULEURS.get(row["Agent"], "#ffffff")
            return [f"background-color: {color}; color: black"] * len(row)

        st.dataframe(
            df_v[["ID", "Date", "Statut", "Heure", "Agent", "Batiment", "Type"]].style.apply(style_agent, axis=1),
            use_container_width=True
        )

        st.divider()
        st.markdown("### 📥 Exportation")

        col_dl1, col_dl2 = st.columns(2)

        out_std = io.BytesIO()
        df_v.drop(columns=["Date_Sort"]).to_excel(out_std, index=False)
        col_dl1.download_button(
            "📄 Télécharger Liste Standard",
            out_std.getvalue(),
            "Planning_Liste.xlsx",
            use_container_width=True,
            key="planning_export_standard"
        )

        df_pivot = df_v.copy()
        df_pivot["Contenu"] = df_pivot["Batiment"] + " (ID:" + df_pivot["ID"].astype(str) + ")"
        df_visual = df_pivot.pivot_table(
            index=["Date", "Heure"],
            columns="Agent",
            values="Contenu",
            aggfunc="first"
        ).reset_index().fillna("")

        out_vis = io.BytesIO()
        df_visual.to_excel(out_vis, index=False)
        col_dl2.download_button(
            "✨ Télécharger Version par Agent",
            out_vis.getvalue(),
            "Planning_Equipe.xlsx",
            type="primary",
            use_container_width=True,
            key="planning_export_agent"
        )

        st.divider()
        st.markdown("### 📅 Synchronisation Outlook")
        st.caption("Télécharge le fichier de ton agente pour synchroniser son calendrier.")

        cols_ics = st.columns(len(AGENTS))
        for i, agt in enumerate(AGENTS):
            df_agt_ics = df_v[df_v["Agent"] == agt]
            if not df_agt_ics.empty:
                ics_data = generer_ics(df_agt_ics)
                cols_ics[i].download_button(
                    f"Sync Outlook - {agt}",
                    data=ics_data,
                    file_name=f"Planning_{agt}.ics",
                    mime="text/calendar",
                    use_container_width=True,
                    key=f"ics_{agt}"
                )

    with t2:
        dates_j = sorted(
            st.session_state.db["Date"].unique(),
            key=lambda x: datetime.strptime(x, "%d/%m/%Y")
        )

        sel_j = st.selectbox("📅 Sélectionner une date :", dates_j, key="vue_agent_date")
        cols_v = st.columns(len(AGENTS))

        for i, a in enumerate(AGENTS):
            with cols_v[i]:
                st.markdown(
                    f"<div style='text-align:center; background-color:{COULEURS[a]}; padding:10px; border-radius:5px; color:black; font-weight:bold;'>{a}</div>",
                    unsafe_allow_html=True
                )

                m = st.session_state.db[
                    (st.session_state.db["Date"] == sel_j) &
                    (st.session_state.db["Agent"] == a)
                ].sort_values("Heure")

                for _, r in m.iterrows():
                    st.markdown(
                        f"<div style='background-color:{COULEURS[a]}; padding:8px; border-radius:5px; border:1px solid #ccc; color:black; margin-top:5px;'>🆔 <b>{r['ID']}</b><br>🕒 <b>{r['Heure']}</b><br>🏠 {r['Batiment']}</div>",
                        unsafe_allow_html=True
                    )

    with t3:
        df_rep = st.session_state.db.copy()
        df_rep["Date_Sort"] = pd.to_datetime(df_rep["Date_Sort"])
        df_rep["Mois"] = df_rep["Date_Sort"].dt.strftime("%B %Y")

        mois_sel = st.selectbox("📅 Mois :", df_rep["Mois"].unique(), key="rapport_mois")
        agents_sel = st.multiselect("👤 Agents :", AGENTS, default=AGENTS, key="rapport_agents")

        df_f = df_rep[
            (df_rep["Mois"] == mois_sel) &
            (df_rep["Agent"].isin(agents_sel))
        ].copy()

        if not df_f.empty:
            total_km = 0.0

            for agent in agents_sel:
                df_agt = df_f[df_f["Agent"] == agent].sort_values(["Date_Sort", "Heure"])

                for jour_dt in df_agt["Date_Sort"].unique():
                    m_j = df_agt[df_agt["Date_Sort"] == jour_dt]
                    pt_actuel = BUREAU_GPS

                    for _, row in m_j.iterrows():
                        nom_b = str(row["Batiment"]).strip()
                        coords = next(
                            (v for k, v in INFOS_BATIMENTS.items() if k.lower() == nom_b.lower()),
                            None
                        )

                        if coords:
                            dest = (coords["lat"], coords["lon"])
                            total_km += calculer_distance(pt_actuel, dest)
                            pt_actuel = dest

                    total_km += calculer_distance(pt_actuel, BUREAU_GPS)

            st.markdown("### 📊 Indicateurs Clés")

            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Total Missions", len(df_f))
            c2.metric("🚗 Distance Est.", f"{total_km:.1f} km")

            nb_ent = df_f[df_f["Type"].str.contains("Entrée|In", case=False, na=False)].shape[0]
            nb_sor = df_f[df_f["Type"].str.contains("Sortie|Out", case=False, na=False)].shape[0]

            c3.metric("📈 Total Entrées", nb_ent)
            c4.metric("📉 Total Sorties", nb_sor)

            st.plotly_chart(
                px.histogram(df_f, x="Date", color="Agent", barmode="group", color_discrete_map=COULEURS),
                use_container_width=True
            )

            st.subheader("🏠 Volume par bâtiment")
            st.table(
                df_f.groupby("Batiment").size().reset_index(name="Missions").sort_values("Missions", ascending=False)
            )

st.caption(f"v4.7 | {datetime.now().year}")
