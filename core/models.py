from django.db import models
from django.contrib.auth.models import AbstractUser
from django.db.models import Max
from django.db.models.signals import post_delete
from django.dispatch import receiver
import os

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

    def get_file_extension(self):
        """Return file extension for icon selection"""
        if self.attachments.exists():
            first_attachment = self.attachments.first()
            return os.path.splitext(first_attachment.file.name)[1].lower()
        return ''

class TaskAttachment(models.Model):
    task = models.ForeignKey(Task, on_delete=models.CASCADE, related_name='attachments')
    file = models.FileField(upload_to='task_attachments/')
    filename = models.CharField(max_length=255)
    uploaded_at = models.DateTimeField(auto_now_add=True)
    file_size = models.PositiveIntegerField(default=0)  # Size in bytes

    def save(self, *args, **kwargs):
        if self.file:
            # Set filename from the uploaded file
            self.filename = os.path.basename(self.file.name)
            # Set file size
            self.file_size = self.file.size
        super().save(*args, **kwargs)

    def get_file_extension(self):
        """Return file extension for icon selection"""
        return os.path.splitext(self.filename)[1].lower()

    def is_image(self):
        """Check if the file is an image"""
        image_extensions = ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp', '.svg']
        return self.get_file_extension() in image_extensions

    def is_pdf(self):
        """Check if the file is a PDF"""
        return self.get_file_extension() == '.pdf'

    def get_type_class(self):
        """Return CSS class based on file type"""
        ext = self.get_file_extension()
        if self.is_image(): return 'image'
        if ext == '.pdf': return 'pdf'
        if ext in ['.doc', '.docx', '.xls', '.xlsx', '.txt', '.rtf']: return 'document'
        if ext in ['.zip', '.rar', '.7z', '.tar', '.gz']: return 'archive'
        return 'default'

    def get_type_label(self):
        """Return text label for the icon badge"""
        ext = self.get_file_extension()
        if self.is_image(): return 'IMG'
        if ext == '.pdf': return 'PDF'
        if ext in ['.doc', '.docx', '.xls', '.xlsx', '.txt', '.rtf']: return 'DOC'
        if ext in ['.zip', '.rar', '.7z', '.tar', '.gz']: return 'ZIP'
        return 'FILE'

    def get_formatted_size(self):
        """Return human-readable file size"""
        size = float(self.file_size)
        if size == 0:
            return "0 B"
        size_names = ["B", "KB", "MB", "GB"]
        i = 0
        while size >= 1024 and i < len(size_names) - 1:
            size /= 1024.0
            i += 1
        return f"{size:.1f} {size_names[i]}"

    def __str__(self):
        return f"{self.filename} - {self.task.title}"

@receiver(post_delete, sender=TaskAttachment)
def auto_delete_file_on_delete(sender, instance, **kwargs):
    """
    Deletes file from filesystem
    when corresponding TaskAttachment object is deleted.
    """
    if instance.file:
        if os.path.isfile(instance.file.path):
            os.remove(instance.file.path)
