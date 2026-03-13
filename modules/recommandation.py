def recommander_logements(df_logements, criteres, top_n=3):
    df = df_logements.copy()

    if df.empty:
        return df

    df["score"] = 0

    # Ville
    ville = criteres.get("ville")
    if ville and ville != "Toutes":
        df.loc[df["Ville"].astype(str).str.lower() == ville.lower(), "score"] += 4

    # Type d'objet
    type_objet = criteres.get("type_objet")
    if type_objet and type_objet != "Tous":
        df.loc[df["Type objet"].astype(str).str.lower() == type_objet.lower(), "score"] += 4

    # Budget max
    budget_max = criteres.get("budget_max")
    if budget_max and "Prix" in df.columns:
        prix_num = pd.to_numeric(df["Prix"], errors="coerce")
        df.loc[prix_num <= budget_max, "score"] += 5

        # bonus si proche du budget sans le dépasser
        ecart = (budget_max - prix_num).abs()
        df.loc[prix_num <= budget_max, "score"] += (1 / (1 + ecart.fillna(9999) / 100)).round(2)

    # Surface min
    surface_min = criteres.get("surface_min")
    if surface_min and "Surface" in df.columns:
        surf_num = pd.to_numeric(df["Surface"], errors="coerce")
        df.loc[surf_num >= surface_min, "score"] += 4

    # Parking
    parking = criteres.get("parking")
    if parking and "Type objet" in df.columns:
        mask_parking = df.apply(
            lambda row: "parc" in " ".join([str(v).lower() for v in row.values]),
            axis=1
        )
        df.loc[mask_parking, "score"] += 2

    # Mot-clé libre
    mot_cle = criteres.get("mot_cle", "").strip().lower()
    if mot_cle:
        colonnes_recherche = [c for c in ["Ville", "Adresse", "Type objet", "Référence interne", "Numéro unique"] if c in df.columns]
        for col in colonnes_recherche:
            df.loc[df[col].astype(str).str.lower().str.contains(mot_cle, na=False), "score"] += 2

    # On garde les logements avec score > 0
    df = df[df["score"] > 0].copy()

    # Tri final
    colonnes_tri = ["score"]
    if "Prix" in df.columns:
        df["Prix_num"] = pd.to_numeric(df["Prix"], errors="coerce")
        colonnes_tri.append("Prix_num")

    df = df.sort_values(colonnes_tri, ascending=[False] + [True] * (len(colonnes_tri) - 1))

    return df.head(top_n)
