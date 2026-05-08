from django.shortcuts import render, redirect
from django.contrib import messages
from core.forms import UserRegistrationForm

def register(request):
    if request.method == 'POST':
        form = UserRegistrationForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Konto zostało utworzone pomyślnie! Możesz się teraz zalogować.')
            return redirect('login')
    else:
        form = UserRegistrationForm()
    return render(request, 'core/registration/register.html', {'form': form})
