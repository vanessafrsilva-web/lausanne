import pandas as pd


def recommander_logements(df_logements, criteres, top_n=3):
    df = df_logements.copy()

    if df.empty:
        return df

    def texte_global(dataframe):
        return dataframe.astype(str).apply(lambda row: " | ".join(row).lower(), axis=1)

    # -------------------------
    # FILTRES BLOQUANTS
    # -------------------------

    ville = criteres.get("ville")
    if ville and ville != "Toutes" and "Ville" in df.columns:
        df = df[df["Ville"].astype(str).str.lower() == ville.lower()]

    type_objet = criteres.get("type_objet")
    if type_objet and type_objet != "Tous" and "Type objet" in df.columns:
        df = df[df["Type objet"].astype(str).str.lower() == type_objet.lower()]

    if "Prix" in df.columns:
        prix = pd.to_numeric(df["Prix"], errors="coerce")

        loyer_min = criteres.get("loyer_min")
        if loyer_min is not None and loyer_min > 0:
            df = df[prix >= loyer_min]
            prix = pd.to_numeric(df["Prix"], errors="coerce")

        loyer_max = criteres.get("loyer_max")
        if loyer_max is not None and loyer_max > 0:
            df = df[prix <= loyer_max]

    if df.empty:
        return df

    txt = texte_global(df)

    if criteres.get("piquet") == "Oui":
        df = df[txt.str.contains("bethusy", na=False)]
        if df.empty:
            return df
        txt = texte_global(df)

    if criteres.get("accompagne_2") == "Oui":
        df = df[txt.str.contains("bethusy", na=False)]
        if df.empty:
            return df
        txt = texte_global(df)

    if criteres.get("accompagne_plus_2") == "Oui":
        df = df[txt.str.contains("montolieu", na=False)]
        if df.empty:
            return df
        txt = texte_global(df)

    if criteres.get("parking") == "Oui":
        df = df[~txt.str.contains("tunnel", na=False)]
        if df.empty:
            return df
        txt = texte_global(df)

    # -------------------------
    # SCORING
    # -------------------------
    df = df.copy()
    df["score"] = 0.0

    if "Prix" in df.columns:
        prix = pd.to_numeric(df["Prix"], errors="coerce")
        loyer_min = criteres.get("loyer_min", 0) or 0
        loyer_max = criteres.get("loyer_max", 0) or 0

        if loyer_max > 0:
            milieu = (loyer_min + loyer_max) / 2
            ecart = (prix - milieu).abs()
            df["score"] += (10 / (1 + ecart.fillna(9999) / 100)).round(2)

    mot_cle = criteres.get("mot_cle", "").strip().lower()
    if mot_cle:
        colonnes = [c for c in ["Ville", "Adresse", "Type objet", "Référence interne", "Numéro unique"] if c in df.columns]
        for col in colonnes:
            df.loc[
                df[col].astype(str).str.lower().str.contains(mot_cle, na=False),
                "score"
            ] += 2

    return df.sort_values(["score"], ascending=False).head(top_n)
