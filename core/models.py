from django.db import models
from django.contrib.auth.models import AbstractUser
from django.db.models import Max

class User(AbstractUser):
    email = models.EmailField(unique=True)
    first_name = models.CharField(max_length=150)
    last_name = models.CharField(max_length=150)

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username', 'first_name', 'last_name']

    def __str__(self):
        return self.email

class Task(models.Model):
    PRIORITY_CHOICES = [
        ('low', 'Niski'),
        ('medium', 'Średni'),
        ('high', 'Wysoki'),
    ]

    STATUS_CHOICES = [
        ('new', 'Nowe'),
        ('in_progress', 'Realizowane'),
        ('resolved', 'Rozwiązane'),
        ('closed', 'Zamknięte'),
        ('reopened', 'Ponownie otwarte'),
    ]

    task_id = models.PositiveIntegerField(default=0)
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    priority = models.CharField(max_length=10, choices=PRIORITY_CHOICES, default='medium')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='new')
    is_completed = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    completion_date = models.DateTimeField(null=True, blank=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='tasks')

    def save(self, *args, **kwargs):
        from django.utils import timezone
        
        # Get original status if this is an update
        if self.pk:
            original_task = Task.objects.get(pk=self.pk)
            original_status = original_task.status
        else:
            original_status = None
        
        # Set completion_date when status changes to 'closed'
        if self.status == 'closed' and original_status != 'closed':
            self.completion_date = timezone.now()
            self.is_completed = True
        elif self.status != 'closed' and original_status == 'closed':
            self.completion_date = None
            self.is_completed = False
            
        if not self.pk or self.task_id == 0:
            # Get the highest task_id for this user
            max_task_id = Task.objects.filter(user=self.user).aggregate(Max('task_id'))['task_id__max'] or 0
            self.task_id = max_task_id + 1
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        user = self.user
        super().delete(*args, **kwargs)
        # Renumber remaining tasks for this user
        self._renumber_user_tasks(user)

    @classmethod
    def _renumber_user_tasks(cls, user):
        """Renumber tasks sequentially starting from 1 for a specific user"""
        tasks = cls.objects.filter(user=user).order_by('task_id')
        for index, task in enumerate(tasks, 1):
            if task.task_id != index:
                task.task_id = index
                task.save(update_fields=['task_id'])

    def __str__(self):
        return self.title
