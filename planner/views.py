from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from tasks.models import Task

@login_required
def index(request):
    tasks = Task.objects.filter(user=request.user)
    return render(request, 'planner/index.html', {'tasks': tasks})
