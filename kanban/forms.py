from django import forms
from .models import KanbanCard

class KanbanCardForm(forms.ModelForm):
    class Meta:
        model = KanbanCard
        fields = ['title', 'description', 'priority', 'column']
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Tytuł karty'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'placeholder': 'Opis (opcjonalnie)', 'rows': 3}),
            'priority': forms.Select(attrs={'class': 'form-control'}),
            'column': forms.Select(attrs={'class': 'form-control'}),
        }
