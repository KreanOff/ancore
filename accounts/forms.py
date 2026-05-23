from django import forms
from django.contrib.auth.forms import UserCreationForm
from .models import User

class UserRegistrationForm(UserCreationForm):
    _input_attrs = {'class': 'form-input'}

    first_name = forms.CharField(max_length=150, required=True, widget=forms.TextInput(attrs={
        **{'placeholder': 'Imię', 'id': 'first-name'},
        **_input_attrs,
    }))
    last_name = forms.CharField(max_length=150, required=True, widget=forms.TextInput(attrs={
        **{'placeholder': 'Nazwisko', 'id': 'last-name'},
        **_input_attrs,
    }))
    email = forms.EmailField(required=True, widget=forms.EmailInput(attrs={
        **{'placeholder': 'Adres Email', 'id': 'email'},
        **_input_attrs,
    }))

    class Meta(UserCreationForm.Meta):
        model = User
        fields = ('first_name', 'last_name', 'email')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs.setdefault('class', 'form-input')

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
