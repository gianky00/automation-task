def format_duration(seconds):
    """Converte una durata in secondi in una stringa formattata HH:MM:SS.ss."""
    if seconds is None:
        return ""
    try:
        seconds = float(seconds)
        hours, remainder = divmod(seconds, 3600)
        minutes, seconds = divmod(remainder, 60)
        return f"{int(hours):02}:{int(minutes):02}:{seconds:05.2f}"
    except (ValueError, TypeError):
        return "Invalido"
