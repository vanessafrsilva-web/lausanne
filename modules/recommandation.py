import pandas as pd
import unicodedata


def recommander_logements(df_logements, criteres, top_n=3):
    df = df_logements.copy()

    if df.empty:
        return df

    def normaliser(val):
        txt = str(val).lower()
        txt = unicodedata.normalize("NFKD", txt).encode("ascii", "ignore").decode("utf-8")
        return txt

    def col_loyer(dataframe):
        for c in ["Loyer Net", "Prix", "Loyer", "Prix logement"]:
            if c in dataframe.columns:
                return c
        return None

    def texte_col(dataframe, col):
        if col in dataframe.columns:
            return dataframe[col].fillna("").astype(str).apply(normaliser)
        return pd.Series("", index=dataframe.index, dtype="string")

    def texte_global(dataframe):
        if dataframe.empty:
            return pd.Series("", index=dataframe.index, dtype="string")

        return dataframe.fillna("").astype(str).apply(
            lambda row: " ".join(normaliser(v) for v in row.tolist()),
            axis=1
        )

    def oui(val):
        return str(val).strip().lower() == "oui"

    demande = normaliser(criteres.get("mot_cle", ""))

    piquet_demande = "piquet" in demande
    parking_demande = "parking" in demande
    bethusy_demande = "bethusy" in demande
    montolieu_demande = "montolieu" in demande
    tunnel_demande = "tunnel" in demande

    ville = criteres.get("ville")
    if ville and ville != "Toutes" and "Ville" in df.columns:
        df = df[df["Ville"].fillna("").astype(str).apply(normaliser) == normaliser(ville)]

    type_objet = criteres.get("type_objet")
    if type_objet and type_objet != "Tous" and "Type objet" in df.columns:
        df = df[df["Type objet"].fillna("").astype(str).apply(normaliser) == normaliser(type_objet)]

    loyer_col = col_loyer(df)
    if loyer_col:
        loyers = pd.to_numeric(df[loyer_col], errors="coerce")

        loyer_min = float(criteres.get("loyer_min", 0) or 0)
        loyer_max = float(criteres.get("loyer_max", 0) or 0)

        if loyer_min > 0:
            df = df[loyers >= loyer_min]
            loyers = pd.to_numeric(df[loyer_col], errors="coerce")

        if loyer_max > 0:
            df = df[loyers <= loyer_max]

    if df.empty:
        return df

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

    if force_bethusy and force_montolieu:
        return df.iloc[0:0]

    # recalcul texte après filtres
    adresse_txt = texte_col(df, "Adresse")
    global_txt = texte_global(df)

    if force_bethusy:
        masque_bethusy = (
            adresse_txt.astype(str).str.contains("bethusy", na=False)
            | global_txt.astype(str).str.contains("bethusy", na=False)
        )
        df = df[masque_bethusy]

    if df.empty:
        return df

    adresse_txt = texte_col(df, "Adresse")
    global_txt = texte_global(df)

    if force_montolieu:
        masque_montolieu = (
            adresse_txt.astype(str).str.contains("montolieu", na=False)
            | global_txt.astype(str).str.contains("montolieu", na=False)
        )
        df = df[masque_montolieu]

    if df.empty:
        return df

    adresse_txt = texte_col(df, "Adresse")
    global_txt = texte_global(df)

    if exclure_tunnel:
        masque_tunnel = (
            adresse_txt.astype(str).str.contains("tunnel", na=False)
            | global_txt.astype(str).str.contains("tunnel", na=False)
        )
        df = df[~masque_tunnel]

    if df.empty:
        return df

    adresse_txt = texte_col(df, "Adresse")
    global_txt = texte_global(df)

    if tunnel_demande and not exclure_tunnel:
        masque_tunnel = (
            adresse_txt.astype(str).str.contains("tunnel", na=False)
            | global_txt.astype(str).str.contains("tunnel", na=False)
        )
        df = df[masque_tunnel]

    if df.empty:
        return df

    df = df.copy()
    df["score"] = 0.0

    loyer_col = col_loyer(df)
    if loyer_col:
        loyers = pd.to_numeric(df[loyer_col], errors="coerce")
        loyer_min = float(criteres.get("loyer_min", 0) or 0)
        loyer_max = float(criteres.get("loyer_max", 0) or 0)

        if loyer_max > 0:
            milieu = (loyer_min + loyer_max) / 2 if loyer_min > 0 else loyer_max
            ecart = (loyers - milieu).abs()
            df["score"] += (10 / (1 + ecart.fillna(9999) / 100)).round(2)

    if force_bethusy:
        df["score"] += 3

    if force_montolieu:
        df["score"] += 3

    if exclure_tunnel:
        df["score"] += 1

    # FIFO : plus ancienne date de dernière location d'abord
    if "Date de la dernière location" in df.columns:
        df["date_fifo"] = pd.to_datetime(
            df["Date de la dernière location"],
            dayfirst=True,
            errors="coerce"
        )
        df = df.sort_values(
            by=["score", "date_fifo"],
            ascending=[False, True]
        )
    else:
        df = df.sort_values(by="score", ascending=False)

    return df.head(top_n)
