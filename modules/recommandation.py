import pandas as pd


def recommander_logements(df_logements, criteres, top_n=3):
    df = df_logements.copy()

    if df.empty:
        return df

    def col_loyer(dataframe):
        for c in ["Loyer Net", "Prix", "Loyer", "Prix logement"]:
            if c in dataframe.columns:
                return c
        return None

    def texte_col(dataframe, col):
        if col in dataframe.columns:
            return dataframe[col].astype(str).str.lower()
        return pd.Series("", index=dataframe.index)

    def texte_global(dataframe):
        return dataframe.astype(str).apply(lambda row: " | ".join(row).lower(), axis=1)

    def oui(val):
        return str(val).strip().lower() == "oui"

    demande = str(criteres.get("mot_cle", "")).lower()

    # Détection depuis la demande libre
    piquet_demande = "piquet" in demande
    parking_demande = "parking" in demande
    bethusy_demande = "bethusy" in demande
    montolieu_demande = "montolieu" in demande
    tunnel_demande = "tunnel" in demande

    # Colonnes utiles
    adresse_txt = texte_col(df, "Adresse")
    ville_txt = texte_col(df, "Ville")
    type_txt = texte_col(df, "Type objet")
    global_txt = texte_global(df)

    # -------------------------
    # FILTRES BLOQUANTS
    # -------------------------

    # Ville
    ville = criteres.get("ville")
    if ville and ville != "Toutes" and "Ville" in df.columns:
        df = df[df["Ville"].astype(str).str.lower() == str(ville).lower()]
        adresse_txt = texte_col(df, "Adresse")
        ville_txt = texte_col(df, "Ville")
        type_txt = texte_col(df, "Type objet")
        global_txt = texte_global(df)

    # Type objet
    type_objet = criteres.get("type_objet")
    if type_objet and type_objet != "Tous" and "Type objet" in df.columns:
        df = df[df["Type objet"].astype(str).str.lower() == str(type_objet).lower()]
        adresse_txt = texte_col(df, "Adresse")
        ville_txt = texte_col(df, "Ville")
        type_txt = texte_col(df, "Type objet")
        global_txt = texte_global(df)

    # Budget min / max
    loyer_col = col_loyer(df)
    if loyer_col:
        loyers = pd.to_numeric(df[loyer_col], errors="coerce")

        loyer_min = criteres.get("loyer_min")
        if loyer_min is not None and float(loyer_min) > 0:
            df = df[loyers >= float(loyer_min)]
            loyers = pd.to_numeric(df[loyer_col], errors="coerce")

        loyer_max = criteres.get("loyer_max")
        if loyer_max is not None and float(loyer_max) > 0:
            df = df[loyers <= float(loyer_max)]

        adresse_txt = texte_col(df, "Adresse")
        ville_txt = texte_col(df, "Ville")
        type_txt = texte_col(df, "Type objet")
        global_txt = texte_global(df)

    if df.empty:
        return df

    # Règles métier
    force_bethusy = (
        oui(criteres.get("piquet"))
        or oui(criteres.get("accompagne_2"))
        or piquet_demande
        or bethusy_demande
    )

    force_montolieu = (
        oui(criteres.get("accompagne_plus_2"))
        or montolieu_demande
    )

    exclure_tunnel = (
        oui(criteres.get("parking"))
        or parking_demande
    )

    # Si contradiction Bethusy + Montolieu -> aucun résultat
    if force_bethusy and force_montolieu:
        return df.iloc[0:0]

    if force_bethusy:
        df = df[adresse_txt.str.contains("bethusy", na=False) | global_txt.str.contains("bethusy", na=False)]
        adresse_txt = texte_col(df, "Adresse")
        global_txt = texte_global(df)

    if force_montolieu:
        df = df[adresse_txt.str.contains("montolieu", na=False) | global_txt.str.contains("montolieu", na=False)]
        adresse_txt = texte_col(df, "Adresse")
        global_txt = texte_global(df)

    if exclure_tunnel and not df.empty:
        df = df[~adresse_txt.str.contains("tunnel", na=False) & ~global_txt.str.contains("tunnel", na=False)]
        adresse_txt = texte_col(df, "Adresse")
        global_txt = texte_global(df)

    if tunnel_demande and not exclure_tunnel:
        df = df[adresse_txt.str.contains("tunnel", na=False) | global_txt.str.contains("tunnel", na=False)]
        adresse_txt = texte_col(df, "Adresse")
        global_txt = texte_global(df)

    if df.empty:
        return df

    # -------------------------
    # SCORING
    # -------------------------
    df = df.copy()
    df["score"] = 0.0

    # score budget : plus proche du milieu de tranche = mieux
    loyer_col = col_loyer(df)
    if loyer_col:
        loyers = pd.to_numeric(df[loyer_col], errors="coerce")
        loyer_min = float(criteres.get("loyer_min", 0) or 0)
        loyer_max = float(criteres.get("loyer_max", 0) or 0)

        if loyer_max > 0:
            milieu = (loyer_min + loyer_max) / 2 if loyer_min > 0 else loyer_max
            ecart = (loyers - milieu).abs()
            df["score"] += (10 / (1 + ecart.fillna(9999) / 100)).round(2)

    # bonus si la demande libre mentionne des mots trouvés
    if demande:
        for col in [c for c in ["Ville", "Adresse", "Type objet", "Référence interne", "Numéro unique"] if c in df.columns]:
            df.loc[df[col].astype(str).str.lower().str.contains(demande, na=False), "score"] += 2

    # bonus métier
    if force_bethusy:
        df["score"] += 3
    if force_montolieu:
        df["score"] += 3
    if exclure_tunnel:
        df["score"] += 1

    return df.sort_values(["score"], ascending=False).head(top_n)
