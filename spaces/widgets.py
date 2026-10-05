from django import forms

from .defaults import issue_type_icon


class IssueTypeSelect(forms.Select):
    """Reuse the shared select's option icons, including custom type fallbacks."""

    def create_option(self, name, value, label, selected, index, subindex=None, attrs=None):
        option = super().create_option(name, value, label, selected, index, subindex, attrs)
        if value:
            option['attrs']['data-ancore-option-icon'] = issue_type_icon(value)
        return option
