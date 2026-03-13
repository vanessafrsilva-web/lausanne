from datetime import datetime, timedelta
from config.settings import INFOS_BATIMENTS
def calculer_creneau(agent, date_str, temp_db, batiment_cible, bloc_impose):
    m_jour = temp_db[(temp_db['Date'] == date_str) & (temp_db['Agent'] == agent)]
    h_start = "08:15" if bloc_impose == "Matin" else "13:00"
    h_limit = "11:45" if bloc_impose == "Matin" else "16:30"
    
    if m_jour.empty:
        prochaine_h = datetime.strptime(h_start, "%H:%M")
    else:
        derniere_h = datetime.strptime(str(m_jour.iloc[-1]['Heure']), "%H:%M")
        if bloc_impose == "Après-midi" and derniere_h < datetime.strptime("13:00", "%H:%M"):
            prochaine_h = datetime.strptime("13:00", "%H:%M")
        else:
            rue_act = INFOS_BATIMENTS.get(batiment_cible, {}).get('rue', "")
            delai = 65 if m_jour.iloc[-1]['Rue'] == rue_act else 85
            prochaine_h = derniere_h + timedelta(minutes=delai)

    if prochaine_h > datetime.strptime(h_limit, "%H:%M"): return "COMPLET", False
    return prochaine_h.strftime("%H:%M"), True
