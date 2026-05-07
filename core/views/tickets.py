from django.shortcuts import render
from django.contrib.auth.decorators import login_required

@login_required
def tickets(request):
    return render(request, 'core/tickets/tickets.html')
