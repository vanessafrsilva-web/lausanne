import pandas as pd


def recommander_logements(df_logements, criteres, top_n=3):

    df = df_logements.copy()

    if df.empty:
        return df

    df["score"] = 0

    # Ville
    ville = criteres.get("ville")
    if ville and ville != "Toutes":
        df.loc[df["Ville"].astype(str).str.lower() == ville.lower(), "score"] += 4

    # Type objet
    type_objet = criteres.get("type_objet")
    if type_objet and type_objet != "Tous":
        df.loc[df["Type objet"].astype(str).str.lower() == type_objet.lower(), "score"] += 4

    # Budget
    budget_max = criteres.get("budget_max")
    if budget_max and "Prix" in df.columns:
        prix = pd.to_numeric(df["Prix"], errors="coerce")
        df.loc[prix <= budget_max, "score"] += 5

    # Surface
    surface_min = criteres.get("surface_min")
    if surface_min and "Surface" in df.columns:
        surf = pd.to_numeric(df["Surface"], errors="coerce")
        df.loc[surf >= surface_min, "score"] += 4

    # Recherche libre
    mot_cle = criteres.get("mot_cle", "").lower()

    if mot_cle:
        colonnes = ["Ville", "Adresse", "Type objet", "Référence interne"]

        for col in colonnes:
            if col in df.columns:
                df.loc[df[col].astype(str).str.lower().str.contains(mot_cle, na=False), "score"] += 2

    # garder les meilleurs
    df = df[df["score"] > 0]

    df = df.sort_values("score", ascending=False)

    return df.head(top_n)
