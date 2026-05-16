import calendar
from datetime import datetime, date

def get_days_until_payday(payday_day: int, payday_month: int = None) -> int:
    today = datetime.now().date()
    
    try:
        if payday_month:
            year = today.year
            if payday_month < today.month:
                year += 1
            _, last_day = calendar.monthrange(year, payday_month)
            target_date = date(year, payday_month, min(payday_day, last_day))
        else:
            _, last_day_current = calendar.monthrange(today.year, today.month)
            target_day = min(payday_day, last_day_current)
            target_date = date(today.year, today.month, target_day)
            if target_date <= today:
                raise ValueError("прошло")
    except ValueError:
        month = today.month + 1
        year = today.year
        if month > 12:
            month = 1
            year += 1
        _, last_day_next = calendar.monthrange(year, month)
        target_day = min(payday_day, last_day_next)
        target_date = date(year, month, target_day)
        
    days_left = (target_date - today).days
    return max(days_left, 1)

def format_history_row(row):
    date_str, cat, desc, amt, sat = row
    short_date = date_str.split(' ')[0][5:]
    emoji = "✅" if sat == 'happy' else "❌" if sat == 'sad' else "▫️"
    return f"📅 {short_date} | {cat} | <b>{amt}</b> | {emoji}"
