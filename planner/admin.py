from django.contrib import admin
from .models import CalendarEvent


@admin.register(CalendarEvent)
class CalendarEventAdmin(admin.ModelAdmin):
    list_display = ('title', 'user', 'start', 'end', 'all_day', 'color')
    list_filter = ('all_day', 'color')
    search_fields = ('title', 'description')
