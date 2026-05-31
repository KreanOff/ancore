from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from django.utils import timezone

from planner.models import CalendarEvent
from tasks.models import Task

@login_required
def home(request):
    now = timezone.now()

    user_tasks = Task.objects.filter(user=request.user)
    open_tasks = user_tasks.exclude(status='closed')
    recent_tasks = open_tasks.order_by('-created_at')[:5]
    upcoming_events = CalendarEvent.objects.filter(
        user=request.user,
        end__gte=now,
    ).order_by('start')[:5]

    status_rows = [
        {
            'label': label,
            'count': user_tasks.filter(status=value).count(),
        }
        for value, label in Task.STATUS_CHOICES
    ]

    context = {
        'total_tasks': user_tasks.count(),
        'open_tasks_count': open_tasks.count(),
        'completed_tasks_count': user_tasks.filter(status='closed').count(),
        'high_priority_count': open_tasks.filter(priority__in=['high', 'urgent']).count(),
        'events_count': upcoming_events.count(),
        'recent_tasks': recent_tasks,
        'upcoming_events': upcoming_events,
        'status_rows': status_rows,
    }

    return render(request, 'dashboard/home.html', context)
