import random
from django.db import models
from django.conf import settings

BOARD_BACKGROUND_CHOICES = [
    ('neutral', 'Jasna'),
    ('ocean', 'Ocean'),
    ('sunset', 'Zachód słońca'),
    ('forest', 'Las'),
    ('berry', 'Jagody'),
    ('lavender', 'Lawenda'),
    ('coral', 'Koral'),
    ('midnight', 'Północ'),
    ('mint', 'Mięta'),
]

BOARD_BACKGROUND_STYLES = {
    'neutral': '#f8fafc',
    'ocean': 'linear-gradient(135deg, #0079bf 0%, #5067c5 100%)',
    'sunset': 'linear-gradient(135deg, #d29034 0%, #cc5f35 100%)',
    'forest': 'linear-gradient(135deg, #519839 0%, #2d6a4f 100%)',
    'berry': 'linear-gradient(135deg, #b04632 0%, #89609e 100%)',
    'lavender': 'linear-gradient(135deg, #89609e 0%, #5c6bc0 100%)',
    'coral': 'linear-gradient(135deg, #cd5a91 0%, #e85d75 100%)',
    'midnight': 'linear-gradient(135deg, #344563 0%, #172b4d 100%)',
    'mint': 'linear-gradient(135deg, #4bbf6b 0%, #00a86b 100%)',
}


def random_board_background():
    return random.choice([c[0] for c in BOARD_BACKGROUND_CHOICES])


class Workspace(models.Model):
    name = models.CharField(max_length=100)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='kanban_workspaces')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.name} ({self.user.username})"

class KanbanBoard(models.Model):
    workspace = models.ForeignKey(Workspace, on_delete=models.CASCADE, related_name='boards', null=True, blank=True)
    name = models.CharField(max_length=100)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='kanban_boards')
    background = models.CharField(max_length=20, choices=BOARD_BACKGROUND_CHOICES, default='ocean')
    background_image = models.FileField(upload_to='kanban_board_backgrounds/', blank=True, null=True)
    background_url = models.URLField(max_length=500, blank=True, default='')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.name} ({self.user.username})"

    @property
    def has_custom_background(self):
        return bool(self.background_image or self.background_url)

    @property
    def background_source(self):
        if self.background_image:
            return 'image'
        if self.background_url:
            return 'url'
        return 'preset'

    @property
    def background_style(self):
        if self.background_image:
            return f"url('{self.background_image.url}') center / cover no-repeat"
        if self.background_url:
            return f"url('{self.background_url}') center / cover no-repeat"
        return BOARD_BACKGROUND_STYLES.get(self.background, BOARD_BACKGROUND_STYLES['ocean'])

    @property
    def uses_wallpaper(self):
        return self.has_custom_background or self.background != 'neutral'

    def clear_custom_background(self):
        if self.background_image:
            self.background_image.delete(save=False)
        self.background_image = None
        self.background_url = ''

    def delete(self, *args, **kwargs):
        if self.background_image:
            self.background_image.delete(save=False)
        super().delete(*args, **kwargs)

    @property
    def initial(self):
        return self.name[0].upper() if self.name else '?'

class KanbanColumn(models.Model):
    board = models.ForeignKey(KanbanBoard, on_delete=models.CASCADE, related_name='columns')
    name = models.CharField(max_length=100)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['order']

    def __str__(self):
        return f"{self.name} - {self.board.name}"

class KanbanCard(models.Model):

    column = models.ForeignKey(KanbanColumn, on_delete=models.CASCADE, related_name='cards')
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    order = models.PositiveIntegerField(default=0)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='kanban_cards')
    is_completed = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['order']

    def __str__(self):
        return self.title


class KanbanAttachment(models.Model):
    card = models.ForeignKey(KanbanCard, on_delete=models.CASCADE, related_name='attachments')
    file = models.FileField(upload_to='kanban_attachments/')
    original_name = models.CharField(max_length=255)
    uploaded_at = models.DateTimeField(auto_now_add=True)
    uploaded_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)

    def __str__(self):
        return f"{self.original_name} → {self.card.title}"

    @property
    def file_extension(self):
        import os
        _, ext = os.path.splitext(self.original_name)
        return ext.lower().lstrip('.')

    @property
    def is_image(self):
        return self.file_extension in ('jpg', 'jpeg', 'png', 'gif', 'webp', 'svg')
