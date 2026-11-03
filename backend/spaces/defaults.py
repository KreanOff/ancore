from copy import deepcopy
import re


KINDS = [('software', 'Programistyczna'), ('business', 'Biznesowa'), ('service', 'Obsługowa')]
MANAGEMENT = [('team', 'Zarządzana przez zespół'), ('company', 'Zarządzana przez organizację')]
TASK_CATEGORY_CHOICES = [('general', 'Ogólne'), ('call', 'Telefon'), ('email', 'E-mail'), ('meeting', 'Spotkanie'), ('offer', 'Oferta'), ('invoice', 'Faktura'), ('complaint', 'Reklamacja'), ('onboarding', 'Onboarding'), ('internal', 'Wewnętrzne')]


def classification_options(settings, section):
    """Read task dictionaries also for configurations saved before they existed."""
    fallback = [{'key': key, 'label': label} for key, label in TASK_CATEGORY_CHOICES] if section == 'categories' else []
    return settings.get(section, fallback)


def classification_label(settings, section, key):
    fallback = dict(TASK_CATEGORY_CHOICES).get(key, key) if section == 'categories' else key or 'Brak grupy'
    return next((row['label'] for row in classification_options(settings, section) if row['key'] == key), fallback)


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
STATUS_ICONS = {
    'new': 'circle-dashed', 'in_progress': 'clock', 'resolved': 'circle-check',
    'closed': 'circle-x', 'reopened': 'circle-minus',
}
STATUS_ICON_CHOICES = [
    ('circle-dashed', 'Nowe'), ('layout-list', 'W kolejce'),
    ('circle-dot', 'Gotowe do rozpoczęcia'), ('calendar-clock', 'Zaplanowane'),
    ('clock', 'W toku'), ('loader-circle', 'W realizacji'),
    ('hourglass', 'Oczekiwanie'), ('circle-minus', 'Wstrzymane'),
    ('ban', 'Zablokowane'), ('clock-alert', 'Opóźnione'),
    ('eye', 'Do sprawdzenia'), ('refresh-cw', 'Do poprawy'),
    ('circle-check', 'Zakończone'), ('circle-x', 'Zamknięte'),
    ('rotate-ccw', 'Ponownie otwarte'), ('archive', 'Zarchiwizowane'),
]
STATUS_ICON_VALUES = frozenset(icon for icon, _ in STATUS_ICON_CHOICES)

# Reuse the existing type/status palette for names without a custom color.
CONFIGURATION_NAME_COLORS = {
    'types': {'task': '#2563eb', 'bug': '#dc4b3e', 'story': '#4f8f63', 'epic': '#5b5fc7'},
    'statuses': {'new': '#2563eb', 'in_progress': '#c18a34', 'resolved': '#759d42',
                 'closed': '#8a909a', 'reopened': '#7c6bd0'},
}


def configuration_name_color(section, row):
    color = row.get('color')
    if isinstance(color, str) and re.fullmatch(r'#[0-9a-fA-F]{6}', color):
        return color.lower()
    key = row.get('category' if section == 'statuses' else 'key')
    return CONFIGURATION_NAME_COLORS.get(section, {}).get(key, '#64748b')


def status_appearance(status):
    """Resolve the shared stage color without changing persisted configuration."""
    return {**status, 'color': configuration_name_color('statuses', status)}


def status_icon(status):
    """Resolve status icons, retaining icons saved before the catalogs split."""
    icon = status.get('icon')
    if isinstance(icon, str) and (icon in STATUS_ICON_VALUES or icon in ISSUE_TYPE_ICON_VALUES):
        return icon
    return STATUS_ICONS.get(status.get('category'), 'clock')


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
    transitions = {
        'new': ['in_progress'], 'in_progress': ['resolved'], 'resolved': ['closed'],
        'closed': ['reopened'], 'reopened': ['in_progress'],
    }
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
        {'key': key, 'label': label, 'category': key, 'transitions': transitions[key],
         'flow_stage': status_flow_stage({'category': key}), 'wip_limit': None, 'policy': ''}
        for key, label in zip(keys, labels)
    ], 'types': types, 'fields': fields,
        'categories': classification_options({}, 'categories'), 'groups': []})
