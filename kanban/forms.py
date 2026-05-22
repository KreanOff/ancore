from django import forms
from .models import KanbanCard

class KanbanCardForm(forms.ModelForm):
    class Meta:
        model = KanbanCard
        fields = ['title', 'description', 'column']
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Tytuł karty'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'placeholder': 'Opis (opcjonalnie)', 'rows': 3}),
            'column': forms.Select(attrs={'class': 'form-control'}),
        }
