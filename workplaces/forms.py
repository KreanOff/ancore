from django import forms

from .models import Workplace


class WorkplaceForm(forms.ModelForm):
    class Meta:
        model = Workplace
        fields = ['name']
        widgets = {
            'name': forms.TextInput(attrs={
                'placeholder': 'Nazwa workplace',
                'class': 'form-input',
                'autocomplete': 'off',
            }),
        }

    def clean_name(self):
        return (self.cleaned_data.get('name') or '').strip()
