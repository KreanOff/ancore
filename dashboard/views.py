from django.contrib.auth.decorators import login_required
from django.db.models import Count, Q
from django.shortcuts import render
from django.utils import timezone

from kanban.models import KanbanBoard, KanbanCard
from planner.models import CalendarEvent
from tasks.models import Task

@login_required
def home(request):
    user = request.user
    now = timezone.now()
    today = timezone.localdate()

    tasks = Task.objects.filter(user=user)
    open_tasks = tasks.exclude(status='closed')
    closed_tasks = tasks.filter(status='closed')
    total_tasks = tasks.count()
    closed_tasks_count = closed_tasks.count()
    completion_rate = round((closed_tasks_count / total_tasks) * 100) if total_tasks else 0

    upcoming_events = CalendarEvent.objects.filter(
        user=user,
        end__gte=now,
    ).order_by('start')[:5]

    recent_tasks = open_tasks.order_by('-created_at')[:5]
    recent_cards = KanbanCard.objects.filter(
        user=user,
        is_completed=False,
    ).select_related('column', 'column__board').order_by('-updated_at')[:5]

    active_boards = KanbanBoard.objects.filter(user=user).annotate(
        card_count=Count('columns__cards', filter=Q(columns__cards__user=user)),
        open_card_count=Count(
            'columns__cards',
            filter=Q(columns__cards__user=user, columns__cards__is_completed=False),
        ),
    ).order_by('-open_card_count', '-card_count', 'name')[:4]

    status_rows = [
        {
            'label': label,
            'count': tasks.filter(status=value).count(),
            'slug': value,
        }
        for value, label in Task.STATUS_CHOICES
    ]

    context = {
        'today': today,
        'stats': {
            'open_tasks': open_tasks.count(),
            'closed_tasks': closed_tasks_count,
            'completion_rate': completion_rate,
            'upcoming_events': CalendarEvent.objects.filter(user=user, end__gte=now).count(),
            'active_boards': KanbanBoard.objects.filter(user=user).count(),
        },
        'recent_tasks': recent_tasks,
        'upcoming_events': upcoming_events,
        'recent_cards': recent_cards,
        'active_boards': active_boards,
        'status_rows': status_rows,
    }
    return render(request, 'dashboard/home.html', context)
