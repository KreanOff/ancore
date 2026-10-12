from django import forms
from django.template.loader import render_to_string


class VisualSelect(forms.Select):
    """Pass trusted option icons/previews to AncoreCustomSelect."""

    template_name = 'core/widgets/visual_select.html'

    def __init__(self, *args, visuals=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.visuals = visuals or {}

    def create_option(self, name, value, label, selected, index, subindex=None, attrs=None):
        option = super().create_option(name, value, label, selected, index, subindex, attrs)
        visual = self.option_visual(value)
        if visual.get('icon'):
            option['attrs']['data-ancore-option-icon'] = visual['icon']
        if visual.get('template'):
            field_id = (attrs or {}).get('id', name)
            option['preview_id'] = f'{field_id}_preview_{index}_{subindex or 0}'
            option['attrs']['data-ancore-option-preview'] = option['preview_id']
            option['preview_html'] = render_to_string(visual['template'], visual.get('context', {}))
        return option

    def option_visual(self, value):
        return self.visuals.get(str(value), {})


class VisualSelectMultiple(VisualSelect, forms.SelectMultiple):
    pass
