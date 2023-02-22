import datetime


def year(request):
    """Добавляет переменную с текущим годом."""
    dt_now = datetime.datetime.now()
    return {
        'year': int(dt_now.strftime("%Y"))
    }
