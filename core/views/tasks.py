from django.shortcuts import render
from django.contrib.auth.decorators import login_required

@login_required
def tasks(request):
    return render(request, 'core/tasks/tasks.html')
