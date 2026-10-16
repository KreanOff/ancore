from .forms import CalendarEventForm
from core.frontend import form_payload


def calendar_page(request, context):
    return {'type': 'calendar', 'title': 'Kalendarz', 'data': {
        'config': context['calendar_config'], 'form': form_payload(CalendarEventForm()),
    }}
