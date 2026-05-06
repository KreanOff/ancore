from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from .forms import UserRegistrationForm

@login_required
def home(request):
    return render(request, 'core/home.html')

@login_required
def tasks(request):
    return render(request, 'core/tasks.html')

@login_required
def kanban(request):
    return render(request, 'core/kanban.html')

@login_required
def calendar(request):
    return render(request, 'core/calendar.html')

@login_required
def tickets(request):
    return render(request, 'core/tickets.html')

def register(request):
    if request.method == 'POST':
        form = UserRegistrationForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, f'Your account has been created! You can now log in.')
            return redirect('login')
    else:
        form = UserRegistrationForm()
    return render(request, 'core/register.html', {'form': form})
