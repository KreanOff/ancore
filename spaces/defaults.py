from copy import deepcopy


KINDS = [('software', 'Programistyczna'), ('business', 'Biznesowa'), ('service', 'Obsługowa')]
MANAGEMENT = [('team', 'Zarządzana przez zespół'), ('company', 'Zarządzana przez organizację')]
TEMPLATES = {
    'kanban': {'label': 'Kanban', 'kind': 'software', 'description': 'Ciągły przepływ pracy na tablicy i w backlogu.'},
    'scrum': {'label': 'Scrum', 'kind': 'software', 'description': 'Backlog, sprinty, epiki i estymacje.'},
    'tasks': {'label': 'Zarządzanie zadaniami', 'kind': 'business', 'description': 'Lista, tablica i terminy pracy zespołu.'},
    'marketing': {'label': 'Marketing', 'kind': 'business', 'description': 'Planowanie kampanii i przygotowanie materiałów.'},
    'recruitment': {'label': 'Rekrutacja', 'kind': 'business', 'description': 'Zgłoszenia, rozmowy i decyzje rekrutacyjne.'},
    'service': {'label': 'Obsługa zgłoszeń', 'kind': 'service', 'description': 'Kolejka zgłoszeń i śledzenie ich rozwiązania.'},
}


def template_settings(template='tasks'):
    labels = {
        'marketing': ['Pomysły', 'W przygotowaniu', 'Do akceptacji', 'Opublikowane', 'Do poprawy'],
        'recruitment': ['Nowe zgłoszenia', 'Rozmowy', 'Decyzja', 'Zakończone', 'Ponowny kontakt'],
        'service': ['Nowe zgłoszenia', 'W obsłudze', 'Rozwiązane', 'Zamknięte', 'Ponownie otwarte'],
    }.get(template, ['Do zrobienia', 'W toku', 'Do sprawdzenia', 'Gotowe', 'Ponownie otwarte'])
    keys = ['new', 'in_progress', 'resolved', 'closed', 'reopened']
    types = [{'key': 'task', 'label': 'Zadanie'}]
    if template in {'kanban', 'scrum'}:
        types += [{'key': 'bug', 'label': 'Błąd'}, {'key': 'story', 'label': 'Historyjka'}, {'key': 'epic', 'label': 'Epik'}]
    elif template == 'marketing':
        types += [{'key': 'campaign', 'label': 'Kampania'}, {'key': 'content', 'label': 'Materiał'}]
    elif template == 'recruitment':
        types = [{'key': 'candidate', 'label': 'Kandydatura'}, {'key': 'interview', 'label': 'Rozmowa'}]
    elif template == 'service':
        types = [{'key': 'request', 'label': 'Zgłoszenie'}, {'key': 'incident', 'label': 'Incydent'}]
    fields = []
    if template == 'recruitment':
        fields = [{'key': 'position', 'label': 'Stanowisko', 'type': 'text', 'required': False}]
    if template == 'marketing':
        fields = [{'key': 'channel', 'label': 'Kanał publikacji', 'type': 'text', 'required': False}]
    return deepcopy({'statuses': [
        {'key': key, 'label': label, 'category': key, 'transitions': [other for other in keys if other != key]}
        for key, label in zip(keys, labels)
    ], 'types': types, 'fields': fields})
