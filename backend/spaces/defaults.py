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

ISSUE_TYPES = [
    {'key': 'task', 'label': 'Zadanie'},
    {'key': 'bug', 'label': 'Błąd'},
    {'key': 'story', 'label': 'Historyjka'},
    {'key': 'epic', 'label': 'Epik'},
]
ISSUE_TYPE_ICONS = {
    'task': 'square-check', 'bug': 'circle-alert', 'story': 'book-open', 'epic': 'zap',
    'campaign': 'megaphone', 'content': 'file-text', 'candidate': 'user-round',
    'interview': 'messages-square', 'request': 'ticket', 'incident': 'siren',
}
ISSUE_TYPE_ICON_CHOICES = [
    ('square-check', 'Zadanie'), ('circle-alert', 'Błąd'), ('book-open', 'Historyjka'),
    ('zap', 'Epik'), ('megaphone', 'Kampania'), ('file-text', 'Materiał'),
    ('user-round', 'Osoba'), ('messages-square', 'Rozmowa'), ('ticket', 'Zgłoszenie'),
    ('siren', 'Incydent'), ('shapes', 'Kształty'), ('lightbulb', 'Pomysł'),
    ('target', 'Cel'), ('rocket', 'Wdrożenie'), ('wrench', 'Usprawnienie'),
    ('flask-conical', 'Eksperyment'), ('shield-check', 'Bezpieczeństwo'),
    ('list-checks', 'Lista kontrolna'), ('calendar', 'Wydarzenie'),
    ('flag', 'Kamień milowy'), ('briefcase', 'Sprawa'), ('palette', 'Projekt graficzny'),
    ('chart-column', 'Raport'), ('settings', 'Konfiguracja'),
]
ISSUE_TYPE_ICON_VALUES = frozenset(icon for icon, _ in ISSUE_TYPE_ICON_CHOICES)


def issue_type_icon(key, configured_icon=None):
    """Resolve a type's optional icon through the shared, trusted icon catalog."""
    if isinstance(configured_icon, str) and configured_icon in ISSUE_TYPE_ICON_VALUES:
        return configured_icon
    return ISSUE_TYPE_ICONS.get(key, 'shapes') if isinstance(key, str) else 'shapes'


FLOW_STAGES = [('queue', 'Kolejka'), ('active', 'Praca w toku'), ('done', 'Zakończone')]


def status_flow_stage(status):
    """Read the flow boundary also for configurations saved before Kanban fields."""
    return status.get('flow_stage') or {'new': 'queue', 'closed': 'done'}.get(status.get('category'), 'active')


def template_settings(template='tasks'):
    labels = {
        'marketing': ['Pomysły', 'W przygotowaniu', 'Do akceptacji', 'Opublikowane', 'Do poprawy'],
        'recruitment': ['Nowe zgłoszenia', 'Rozmowy', 'Decyzja', 'Zakończone', 'Ponowny kontakt'],
        'service': ['Nowe zgłoszenia', 'W obsłudze', 'Rozwiązane', 'Zamknięte', 'Ponownie otwarte'],
    }.get(template, ['Do zrobienia', 'W toku', 'Do sprawdzenia', 'Gotowe', 'Ponownie otwarte'])
    keys = ['new', 'in_progress', 'resolved', 'closed', 'reopened']
    types = deepcopy(ISSUE_TYPES)
    if template == 'marketing':
        types += [{'key': 'campaign', 'label': 'Kampania'}, {'key': 'content', 'label': 'Materiał'}]
    elif template == 'recruitment':
        types = [{'key': 'candidate', 'label': 'Kandydatura'}, {'key': 'interview', 'label': 'Rozmowa'}] + types
    elif template == 'service':
        types = [{'key': 'request', 'label': 'Zgłoszenie'}, {'key': 'incident', 'label': 'Incydent'}] + types
    fields = []
    if template == 'recruitment':
        fields = [{'key': 'position', 'label': 'Stanowisko', 'type': 'text', 'required': False}]
    if template == 'marketing':
        fields = [{'key': 'channel', 'label': 'Kanał publikacji', 'type': 'text', 'required': False}]
    return deepcopy({'statuses': [
        {'key': key, 'label': label, 'category': key, 'transitions': [other for other in keys if other != key],
         'flow_stage': status_flow_stage({'category': key}), 'wip_limit': None, 'policy': ''}
        for key, label in zip(keys, labels)
    ], 'types': types, 'fields': fields})
