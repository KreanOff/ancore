from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from ..models import Task

@login_required
def calendar(request):
    tasks = Task.objects.filter(user=request.user)
    return render(request, 'tasks/calendar.html', {'tasks': tasks})
