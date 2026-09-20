"""Serialize catalog location writes before locking individual documents."""
from functools import wraps

from django.db import transaction
from django.shortcuts import get_object_or_404

from workplaces.models import Workplace


def location_write(view):
    @wraps(view)
    def wrapped(request, *args, **kwargs):
        if request.method != 'POST':
            return view(request, *args, **kwargs)
        with transaction.atomic():
            get_object_or_404(Workplace.objects.select_for_update(), pk=request.workplace.pk, owner=request.user)
            return view(request, *args, **kwargs)
    return wrapped
