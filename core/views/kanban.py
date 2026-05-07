from django.shortcuts import render
from django.contrib.auth.decorators import login_required

@login_required
def kanban(request):
    return render(request, 'core/kanban/kanban.html')
