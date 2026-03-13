
def generer_ics(df_agent):
    ics_content = "BEGIN:VCALENDAR\nVERSION:2.0\nPRODID:-//Unite Logement//Planning//FR\n"
    for _, row in df_agent.iterrows():
        try:
            date_obj = datetime.strptime(row['Date'], '%d/%m/%Y')
            heure_obj = datetime.strptime(row['Heure'], '%H:%M')
            start = date_obj.replace(hour=heure_obj.hour, minute=heure_obj.minute)
            end = start + timedelta(minutes=60)
            ics_content += "BEGIN:VEVENT\n"
            ics_content += f"SUMMARY:Mission {row['ID']} - {row['Batiment']}\n"
            ics_content += f"DTSTART:{start.strftime('%Y%m%dT%H%M%S')}\n"
            ics_content += f"DTEND:{end.strftime('%Y%m%dT%H%M%S')}\n"
            ics_content += f"LOCATION:{row['Rue']}\n"
            ics_content += f"DESCRIPTION:Type: {row['Type']}\n"
            ics_content += "END:VEVENT\n"
        except: continue
    ics_content += "END:VCALENDAR"
    return ics_content
