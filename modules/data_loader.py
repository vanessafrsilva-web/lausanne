
import pandas as pd


def charger_logements(file):
    """
    Charge un fichier CSV ou Excel contenant les logements.
    """

    if file.name.endswith(".csv"):
        df = pd.read_csv(file)
    else:
        df = pd.read_excel(file)

    # nettoyer les colonnes
    df.columns = df.columns.str.strip()

    return df
