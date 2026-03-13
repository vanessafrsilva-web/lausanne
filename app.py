import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import io
import plotly.express as px
import numpy as np

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


@st.cache_data
def charger_excel(file):
    return pd.read_excel(file)


st.set_page_config(
    page_title="Unité Logement - Gestion Planning",
    layout="wide",
    page_icon="📍"
)

# -- Visuel CSS
st.markdown("""
<style>

/* Sidebar blanche */
section[data-testid="stSidebar"] {
    background-color: #073763;
}

section[data-testid="stSidebar"] * {
    color: #102a43;
}

[data-testid="stAppViewContainer"] {
    background-color: #eef4fb;
}

.main {
    background-color: #073763;
}

}

/* Zone centrale */
.main {
    background-color: #073763;
}

/* Texte principal */
[data-testid="stAppViewContainer"] * {
        color: #ffffff;
}

/* uploader sidebar */
section[data-testid="stSidebar"] [data-testid="stFileUploader"] {
    border: 1px solid #fffff;
    border-radius: 10px;
    padding: 12px;
    background-color: #5086c4;
}

/* bouton sidebar */
section[data-testid="stSidebar"] .stButton > button {
    background-color: #fffff;
    color: #5086c4;
    border-radius: 8px;
    border: none;
}

section[data-testid="stSidebar"] .stButton > button:hover {
    background-color: #9fc5e8;
}

</style>
""", unsafe_allow_html=True)

# --- FONCTIONS TECHNIQUES ---
def trouver_secteur(batiment):
    for secteur, liste in SECTEURS.items():
        if batiment in liste:
            return secteur
    return batiment


# --- SESSION STATE ---
if "db" not in st.session_state:
    st.session_state.db = pd.DataFrame(
        columns=["ID", "Batiment", "Date", "Heure", "Agent", "Rue", "Type", "Statut", "Date_Sort"]
    )

if "logements" not in st.session_state:
    st.session_state.logements = pd.DataFrame()


# --- INTERFACE ---
st.title("📍 Unité Logement : Planning & Rapports")

t0, t1, t2, t3 = st.tabs([
    "🏠 Logements vacants",
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

    if up_logements and st.button("🏠 Charger les logements"):
        try:
            df_logements = charger_logements(up_logements)
            st.session_state.logements = df_logements
            st.success("Liste des logements chargée")
        except Exception as e:
            st.error(f"Erreur logements : {e}")

    if up and st.button("🚀 Lancer l'Attribution"):
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
            df_ex[c_date] = pd.to_datetime(df_ex[c_date])

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

    if st.button("🗑️ Reset"):
        st.session_state.db = pd.DataFrame(
            columns=["ID", "Batiment", "Date", "Heure", "Agent", "Rue", "Type", "Statut", "Date_Sort"]
        )
        st.session_state.logements = pd.DataFrame()
        st.rerun()


# --- ONGLET LOGEMENTS ---
with t0:
    st.subheader("🏠 Logements disponibles")

    if not st.session_state.logements.empty:
        df_log = st.session_state.logements.copy()

        df_log["Surface"] = (
            df_log["Surface"]
            .astype(str)
            .str.replace(",", ".", regex=False)
            .str.extract(r"(\d+\.?\d*)")[0]
        )
        df_log["Surface"] = pd.to_numeric(df_log["Surface"], errors="coerce")

        col1, col2, col3 = st.columns(3)

        with col1:
            villes = ["Toutes"] + sorted(df_log["Ville"].dropna().astype(str).unique().tolist())
            ville_sel = st.selectbox("Ville", villes)

        with col2:
            immeubles = ["Tous"] + sorted(df_log["Adresse"].dropna().astype(str).unique().tolist())
            immeuble_sel = st.selectbox("Adresse / Immeuble", immeubles)

        with col3:
            surface_min = st.number_input("Surface minimum", min_value=0, value=20)

        df_filtre = df_log.copy()

        if ville_sel != "Toutes":
            df_filtre = df_filtre[df_filtre["Ville"].astype(str) == ville_sel]

        if immeuble_sel != "Tous":
            df_filtre = df_filtre[df_filtre["Adresse"].astype(str) == immeuble_sel]

        if surface_min > 0:
            df_filtre = df_filtre[df_filtre["Surface"] >= surface_min]

        st.write(f"Logements trouvés : {len(df_filtre)}")
        st.dataframe(df_filtre, use_container_width=True)

    else:
        st.info("Aucune liste de logements chargée.")


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
            use_container_width=True
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
            use_container_width=True
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
                    use_container_width=True
                )

    with t2:
        dates_j = sorted(
            st.session_state.db["Date"].unique(),
            key=lambda x: datetime.strptime(x, "%d/%m/%Y")
        )

        sel_j = st.selectbox("📅 Sélectionner une date :", dates_j)
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

        mois_sel = st.selectbox("📅 Mois :", df_rep["Mois"].unique())
        agents_sel = st.multiselect("👤 Agents :", AGENTS, default=AGENTS)

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
