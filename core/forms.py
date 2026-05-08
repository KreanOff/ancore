from django import forms
from django.contrib.auth.forms import UserCreationForm
from .models import User, Task

class UserRegistrationForm(UserCreationForm):
    first_name = forms.CharField(max_length=150, required=True, widget=forms.TextInput(attrs={
        'placeholder': 'Imię',
        'id': 'first-name'
    }))
    last_name = forms.CharField(max_length=150, required=True, widget=forms.TextInput(attrs={
        'placeholder': 'Nazwisko',
        'id': 'last-name'
    }))
    email = forms.EmailField(required=True, widget=forms.EmailInput(attrs={
        'placeholder': 'Adres Email',
        'id': 'email'
    }))

    class Meta(UserCreationForm.Meta):
        model = User
        fields = ('first_name', 'last_name', 'email')

    def save(self, commit=True):
        user = super().save(commit=False)
        user.first_name = self.cleaned_data['first_name']
        user.last_name = self.cleaned_data['last_name']
        user.email = self.cleaned_data['email']
        # Set username to email since we use email as USERNAME_FIELD
        user.username = self.cleaned_data['email']
        if commit:
            user.save()
        return user

class TaskForm(forms.ModelForm):
    class Meta:
        model = Task
        fields = ['title', 'description', 'priority', 'status']
        widgets = {
            'title': forms.TextInput(attrs={
                'placeholder': 'Wprowadź tytuł zadania...',
                'class': 'form-input'
            }),
            'description': forms.Textarea(attrs={
                'placeholder': 'Wprowadź opis zadania...',
                'rows': 4,
                'class': 'form-input'
            }),
            'priority': forms.Select(attrs={
                'class': 'form-input'
            }),
            'status': forms.Select(attrs={
                'class': 'form-input'
            }),
        }
