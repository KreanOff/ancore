from django.shortcuts import render

def home(request):
    return render(request, 'core/home.html')

def tasks(request):
    return render(request, 'core/tasks.html')

def kanban(request):
    return render(request, 'core/kanban.html')

def calendar(request):
    return render(request, 'core/calendar.html')

def tickets(request):
    return render(request, 'core/tickets.html')

def register(request):
    return render(request, 'core/register.html')
