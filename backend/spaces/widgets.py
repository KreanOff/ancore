from django import forms

from core.widgets import VisualSelect
from workplaces.services import scoped_workplace_app_path
from .defaults import configuration_name_color, issue_type_icon


class IssueTypeSelect(VisualSelect):
    """Reuse the shared select's option icons, including custom type fallbacks."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.type_icons = {}
        self.type_colors = {}

    def option_visual(self, value):
        if not value:
            return {}
        icon = issue_type_icon(value, self.type_icons.get(str(value)))
        color = configuration_name_color('types', {'key': str(value), 'color': self.type_colors.get(str(value))})
        return {'icon': icon, 'template': 'spaces/type_option.html',
                'context': {'icon': icon, 'type_color': color}}


class TaskVisibilitySelect(forms.Select):
    def create_option(self, name, value, label, selected, index, subindex=None, attrs=None):
        option = super().create_option(name, value, label, selected, index, subindex, attrs)
        option['attrs']['data-ancore-option-icon'] = 'lock' if value == 'private' else 'users'
        return option


class SpaceSelect(VisualSelect):
    def option_visual(self, value):
        space = getattr(value, 'instance', None)
        return {'template': 'spaces/avatar.html', 'context': {'space': space}} if space else {'icon': 'layers'}


class SpaceSelectMultiple(SpaceSelect, forms.SelectMultiple):
    """Use the same space avatars for multiple and single selection."""


class TeamSelect(VisualSelect):
    def option_visual(self, value):
        team = getattr(value, 'instance', None)
        if team is None:
            return {'icon': 'users'}
        return {'template': 'spaces/team_avatar.html', 'context': {
            'photo_url': scoped_workplace_app_path(team.workplace, 'teams', f'{team.pk}/photo/') if team.photo else '',
        }}
