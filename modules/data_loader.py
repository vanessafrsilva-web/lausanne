import pandas as pd


def charger_logements(file):
    """
    Charge un fichier CSV ou Excel contenant les logements.
    """

    if file.name.endswith(".csv"):
        try:
            df = pd.read_csv(file, encoding="utf-8")
        except UnicodeDecodeError:
            file.seek(0)
            try:
                df = pd.read_csv(file, encoding="cp1252", sep=None, engine="python")
            except Exception:
                file.seek(0)
                df = pd.read_csv(file, encoding="latin-1", sep=None, engine="python")
    else:
        df = pd.read_excel(file)

    df.columns = df.columns.str.strip()

    return df
