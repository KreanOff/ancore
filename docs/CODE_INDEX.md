# Indeks kodu Ancore

Plik generowany przez `python scripts/update_code_index.py`. Nie edytuj ręcznie.

Zakres: lokalne źródła skonfigurowanych aplikacji i konfiguracja Django w `backend/` oraz
zasoby `static/`, źródła `frontend/app` i `frontend/board` oraz narzędzia `scripts/` i `deploy/`.
Uwzględnia pliki nieśledzone i ignorowane przez Git, jeśli
są obecne lokalnie. Pomija sekrety, uploady, środowisko i cache Pythona.
Generator nie importuje aplikacji ani nie łączy się z bazą.

To katalog deklaracji, nie dowód dostępności funkcji lub wykonania testów.
Pola odziedziczone, dynamiczny routing i semantyka helperów nie są
odtwarzane. Aktywne zachowania i pozostałości opisują [Moduły](MODULES.md)
oraz [Mechanizmy](MECHANISMS.md).

## 1. Przegląd katalogów

| Katalog | Python poza migracjami | Migracje bez init | Szablony HTML | Metody test_* |
| --- | ---: | ---: | ---: | ---: |
| [backend/ancore](../backend/ancore) | 6 | 0 | 0 | 0 |
| [backend/core](../backend/core) | 39 | 0 | 28 | 249 |
| [backend/accounts](../backend/accounts) | 30 | 4 | 10 | 112 |
| [backend/workplaces](../backend/workplaces) | 33 | 5 | 16 | 170 |
| [backend/tasks](../backend/tasks) | 8 | 1 | 24 | 12 |
| [backend/dashboard](../backend/dashboard) | 55 | 8 | 44 | 323 |
| [backend/planner](../backend/planner) | 12 | 2 | 1 | 40 |
| [backend/documents](../backend/documents) | 41 | 3 | 30 | 215 |
| [backend/resources](../backend/resources) | 12 | 3 | 5 | 52 |
| [backend/spaces](../backend/spaces) | 72 | 6 | 47 | 513 |

## 2. Modele i relacje

## Modele: accounts

### `User`

Źródło: [backend/accounts/models.py](../backend/accounts/models.py).

Pola zadeklarowane tutaj: `email` (EmailField), `first_name` (CharField), `middle_name` (CharField), `last_name` (CharField), `avatar` (CharField), `profile_photo` (FileField), `profile_banner` (FileField), `profile_banner_x` (FloatField), `profile_banner_y` (FloatField), `profile_banner_zoom` (FloatField), `phone_number` (CharField), `job_title` (CharField), `bio` (TextField), `presence_status` (CharField), `last_seen_at` (DateTimeField), `default_workplace` (ForeignKey).

| Relacja | Cel | Ustawienia |
| --- | --- | --- |
| `default_workplace` | `'workplaces.Workplace'` | on_delete=models.SET_NULL; related_name='+'; null=True |

Metody/properties: `presence_status_class`, `get_full_name`, `__str__`.

## Modele: workplaces

### `Workplace`

Źródło: [backend/workplaces/models.py](../backend/workplaces/models.py).

Pola zadeklarowane tutaj: `name` (CharField), `description` (TextField), `code` (CharField), `slug` (SlugField), `legacy_slug` (SlugField), `avatar` (CharField), `disabled_modules` (JSONField), `workplace_photo` (FileField), `owner` (ForeignKey), `members` (ManyToManyField), `created_at` (DateTimeField), `updated_at` (DateTimeField).

| Relacja | Cel | Ustawienia |
| --- | --- | --- |
| `owner` | `settings.AUTH_USER_MODEL` | on_delete=models.CASCADE; related_name='owned_workplaces' |
| `members` | `settings.AUTH_USER_MODEL` | related_name='workplaces'; through='WorkplaceMembership' |

Metody/properties: `save`, `initials`, `ensure_owner_membership`, `__str__`.

### `WorkplaceMembership`

Źródło: [backend/workplaces/models.py](../backend/workplaces/models.py).

Pola zadeklarowane tutaj: `workplace` (ForeignKey), `user` (ForeignKey), `role` (CharField), `is_active` (BooleanField), `created_at` (DateTimeField).

| Relacja | Cel | Ustawienia |
| --- | --- | --- |
| `workplace` | `Workplace` | on_delete=models.CASCADE; related_name='memberships' |
| `user` | `settings.AUTH_USER_MODEL` | on_delete=models.CASCADE; related_name='workplace_memberships' |

Metody/properties: `__str__`.

### `WorkplaceInviteLink`

Źródło: [backend/workplaces/models.py](../backend/workplaces/models.py).

Pola zadeklarowane tutaj: `workplace` (ForeignKey), `token` (UUIDField), `created_by` (ForeignKey), `role` (CharField), `max_uses` (PositiveIntegerField), `uses` (PositiveIntegerField), `expires_at` (DateTimeField), `revoked_at` (DateTimeField), `created_at` (DateTimeField).

| Relacja | Cel | Ustawienia |
| --- | --- | --- |
| `workplace` | `Workplace` | on_delete=models.CASCADE; related_name='invite_links' |
| `created_by` | `settings.AUTH_USER_MODEL` | on_delete=models.SET_NULL; null=True |

### `WorkplaceInviteLinkUse`

Źródło: [backend/workplaces/models.py](../backend/workplaces/models.py).

Pola zadeklarowane tutaj: `link` (ForeignKey), `user` (ForeignKey), `created_at` (DateTimeField).

| Relacja | Cel | Ustawienia |
| --- | --- | --- |
| `link` | `WorkplaceInviteLink` | on_delete=models.CASCADE; related_name='redemptions' |
| `user` | `settings.AUTH_USER_MODEL` | on_delete=models.CASCADE |

### `SidebarFavorite`

Źródło: [backend/workplaces/models.py](../backend/workplaces/models.py).

Pola zadeklarowane tutaj: `user` (ForeignKey), `workplace` (ForeignKey), `item_key` (CharField), `position` (PositiveIntegerField), `created_at` (DateTimeField).

| Relacja | Cel | Ustawienia |
| --- | --- | --- |
| `user` | `settings.AUTH_USER_MODEL` | on_delete=models.CASCADE; related_name='sidebar_favorites' |
| `workplace` | `Workplace` | on_delete=models.CASCADE; related_name='sidebar_favorites' |

Metody/properties: `__str__`.

## Modele: tasks

### `TaskTag`

Źródło: [backend/tasks/models.py](../backend/tasks/models.py).

Pola zadeklarowane tutaj: `name` (CharField), `description` (TextField), `code` (CharField), `category` (CharField), `color` (CharField), `icon` (CharField), `priority` (CharField), `scope` (CharField), `owner_label` (CharField), `status` (CharField), `usage_notes` (TextField), `automation_rules` (TextField), `user` (ForeignKey), `workplace` (ForeignKey), `space` (ForeignKey), `related_tags` (ManyToManyField), `created_at` (DateTimeField).

| Relacja | Cel | Ustawienia |
| --- | --- | --- |
| `user` | `settings.AUTH_USER_MODEL` | on_delete=models.CASCADE; related_name='task_tags' |
| `workplace` | `'workplaces.Workplace'` | on_delete=models.CASCADE; related_name='task_tags'; null=True |
| `space` | `'spaces.Space'` | on_delete=models.CASCADE; related_name='tags'; null=True |
| `related_tags` | `'self'` | — |

Metody/properties: `_code_exists`, `_generate_unique_code`, `save`, `__str__`.

### `TaskTagNote`

Źródło: [backend/tasks/models.py](../backend/tasks/models.py).

Pola zadeklarowane tutaj: `tag` (ForeignKey), `author` (ForeignKey), `message` (TextField), `created_at` (DateTimeField), `updated_at` (DateTimeField), `edited_at` (DateTimeField).

| Relacja | Cel | Ustawienia |
| --- | --- | --- |
| `tag` | `TaskTag` | on_delete=models.CASCADE; related_name='tag_notes' |
| `author` | `settings.AUTH_USER_MODEL` | on_delete=models.SET_NULL; related_name='task_tag_notes'; null=True |

Metody/properties: `__str__`.

## Modele: dashboard

### `SavedTaskFilter`

Źródło: [backend/dashboard/models.py](../backend/dashboard/models.py).

Pola zadeklarowane tutaj: `owner` (ForeignKey), `workplace` (ForeignKey), `created_by` (ForeignKey), `name` (CharField), `description` (TextField), `query` (TextField), `visibility` (CharField), `shared_with` (ManyToManyField), `favorited_by` (ManyToManyField), `revision` (PositiveIntegerField), `created_at` (DateTimeField), `updated_at` (DateTimeField).

| Relacja | Cel | Ustawienia |
| --- | --- | --- |
| `owner` | `settings.AUTH_USER_MODEL` | on_delete=models.CASCADE; related_name='workspace_task_filters' |
| `workplace` | `'workplaces.Workplace'` | on_delete=models.CASCADE; related_name='task_filters' |
| `created_by` | `settings.AUTH_USER_MODEL` | on_delete=models.CASCADE; related_name='created_task_filters' |
| `shared_with` | `settings.AUTH_USER_MODEL` | related_name='shared_task_filters'; through='SavedTaskFilterMembership' |
| `favorited_by` | `settings.AUTH_USER_MODEL` | related_name='favorite_task_filters' |

Metody/properties: `__str__`.

### `SavedTaskFilterMembership`

Źródło: [backend/dashboard/models.py](../backend/dashboard/models.py).

Pola zadeklarowane tutaj: `savedtaskfilter` (ForeignKey), `user` (ForeignKey), `role` (CharField), `created_at` (DateTimeField).

| Relacja | Cel | Ustawienia |
| --- | --- | --- |
| `savedtaskfilter` | `SavedTaskFilter` | on_delete=models.CASCADE; related_name='memberships' |
| `user` | `settings.AUTH_USER_MODEL` | on_delete=models.CASCADE; related_name='task_filter_memberships' |

### `Dashboard`

Źródło: [backend/dashboard/models.py](../backend/dashboard/models.py).

Pola zadeklarowane tutaj: `owner` (ForeignKey), `workplace` (ForeignKey), `created_by` (ForeignKey), `name` (CharField), `slug` (SlugField), `description` (TextField), `icon` (CharField), `data_scope` (CharField), `scope_spaces` (ManyToManyField), `scope_filter` (ForeignKey), `refresh_interval` (PositiveSmallIntegerField), `visibility` (CharField), `shared_with` (ManyToManyField), `favorited_by` (ManyToManyField), `layout` (CharField), `revision` (PositiveIntegerField), `is_default` (BooleanField), `created_at` (DateTimeField), `updated_at` (DateTimeField).

| Relacja | Cel | Ustawienia |
| --- | --- | --- |
| `owner` | `settings.AUTH_USER_MODEL` | on_delete=models.CASCADE; related_name='workspace_dashboards' |
| `workplace` | `'workplaces.Workplace'` | on_delete=models.CASCADE; related_name='dashboards' |
| `created_by` | `settings.AUTH_USER_MODEL` | on_delete=models.CASCADE; related_name='created_dashboards' |
| `scope_spaces` | `'spaces.Space'` | related_name='scoped_dashboards' |
| `scope_filter` | `SavedTaskFilter` | on_delete=models.SET_NULL; related_name='scoped_dashboards'; null=True |
| `shared_with` | `settings.AUTH_USER_MODEL` | related_name='shared_dashboards'; through='DashboardMembership' |
| `favorited_by` | `settings.AUTH_USER_MODEL` | related_name='favorite_dashboards' |

Metody/properties: `save`, `icon_emoji`, `icon_emoji_art`, `column_count`, `__str__`.

### `DashboardMembership`

Źródło: [backend/dashboard/models.py](../backend/dashboard/models.py).

Pola zadeklarowane tutaj: `dashboard` (ForeignKey), `user` (ForeignKey), `role` (CharField), `created_at` (DateTimeField).

| Relacja | Cel | Ustawienia |
| --- | --- | --- |
| `dashboard` | `Dashboard` | on_delete=models.CASCADE; related_name='memberships' |
| `user` | `settings.AUTH_USER_MODEL` | on_delete=models.CASCADE; related_name='dashboard_memberships' |

### `DashboardGadget`

Źródło: [backend/dashboard/models.py](../backend/dashboard/models.py).

Pola zadeklarowane tutaj: `dashboard` (ForeignKey), `kind` (CharField), `title` (CharField), `space` (ForeignKey), `assignee` (CharField), `column` (PositiveSmallIntegerField), `position` (PositiveSmallIntegerField), `x` (PositiveSmallIntegerField), `y` (PositiveSmallIntegerField), `w` (PositiveSmallIntegerField), `h` (PositiveSmallIntegerField).

| Relacja | Cel | Ustawienia |
| --- | --- | --- |
| `dashboard` | `Dashboard` | on_delete=models.CASCADE; related_name='gadgets' |
| `space` | `'spaces.Space'` | on_delete=models.CASCADE; null=True |

Metody/properties: `label`.

### `NotificationState`

Źródło: [backend/dashboard/models.py](../backend/dashboard/models.py).

Pola zadeklarowane tutaj: `space_activity` (ForeignKey), `space_reminder` (ForeignKey), `user` (ForeignKey), `is_read` (BooleanField), `is_archived` (BooleanField), `is_deleted` (BooleanField).

| Relacja | Cel | Ustawienia |
| --- | --- | --- |
| `space_activity` | `'spaces.SpaceTaskActivity'` | on_delete=models.CASCADE; null=True |
| `space_reminder` | `'spaces.SpaceTaskReminder'` | on_delete=models.CASCADE; null=True |
| `user` | `settings.AUTH_USER_MODEL` | on_delete=models.CASCADE |

## Modele: planner

### `CalendarEvent`

Źródło: [backend/planner/models.py](../backend/planner/models.py).

Pola zadeklarowane tutaj: `user` (ForeignKey), `workplace` (ForeignKey), `title` (CharField), `description` (TextField), `start` (DateTimeField), `end` (DateTimeField), `all_day` (BooleanField), `color` (CharField), `created_at` (DateTimeField), `updated_at` (DateTimeField).

| Relacja | Cel | Ustawienia |
| --- | --- | --- |
| `user` | `settings.AUTH_USER_MODEL` | on_delete=models.CASCADE; related_name='calendar_events' |
| `workplace` | `'workplaces.Workplace'` | on_delete=models.CASCADE; related_name='calendar_events'; null=True |

Metody/properties: `__str__`.

## Modele: documents

### `DocumentLibrary`

Źródło: [backend/documents/models.py](../backend/documents/models.py).

Pola zadeklarowane tutaj: `name` (CharField), `color` (CharField), `description` (TextField), `photo` (FileField), `workplace` (ForeignKey), `owner` (ForeignKey), `created_at` (DateTimeField), `updated_at` (DateTimeField).

| Relacja | Cel | Ustawienia |
| --- | --- | --- |
| `workplace` | `'workplaces.Workplace'` | on_delete=models.CASCADE; related_name='document_libraries' |
| `owner` | `settings.AUTH_USER_MODEL` | on_delete=models.CASCADE; related_name='document_libraries' |

Metody/properties: `__str__`.

### `Folder`

Źródło: [backend/documents/models.py](../backend/documents/models.py).

Pola zadeklarowane tutaj: `name` (CharField), `color` (CharField), `library` (ForeignKey), `parent` (ForeignKey), `workplace` (ForeignKey), `owner` (ForeignKey), `favorited_by` (ManyToManyField), `created_at` (DateTimeField).

| Relacja | Cel | Ustawienia |
| --- | --- | --- |
| `library` | `DocumentLibrary` | on_delete=models.RESTRICT; related_name='folders' |
| `parent` | `'self'` | on_delete=models.RESTRICT; related_name='children'; null=True |
| `workplace` | `'workplaces.Workplace'` | on_delete=models.CASCADE; related_name='document_folders' |
| `owner` | `settings.AUTH_USER_MODEL` | on_delete=models.CASCADE; related_name='document_folders' |
| `favorited_by` | `settings.AUTH_USER_MODEL` | related_name='favorite_drive_folders' |

Metody/properties: `__str__`.

### `Document`

Źródło: [backend/documents/models.py](../backend/documents/models.py).

Pola zadeklarowane tutaj: `id` (UUIDField), `title` (CharField), `library` (ForeignKey), `description` (TextField), `file` (FileField), `filename` (CharField), `file_size` (PositiveBigIntegerField), `revision` (PositiveIntegerField), `office_key` (UUIDField), `office_save_error` (BooleanField), `folder` (ForeignKey), `workplace` (ForeignKey), `owner` (ForeignKey), `tags` (ManyToManyField), `favorited_by` (ManyToManyField), `deleted_at` (DateTimeField), `created_at` (DateTimeField), `updated_at` (DateTimeField).

| Relacja | Cel | Ustawienia |
| --- | --- | --- |
| `library` | `DocumentLibrary` | on_delete=models.RESTRICT; related_name='documents' |
| `folder` | `Folder` | on_delete=models.RESTRICT; related_name='documents'; null=True |
| `workplace` | `'workplaces.Workplace'` | on_delete=models.CASCADE; related_name='documents' |
| `owner` | `settings.AUTH_USER_MODEL` | on_delete=models.CASCADE; related_name='documents' |
| `tags` | `'tasks.TaskTag'` | related_name='documents' |
| `favorited_by` | `settings.AUTH_USER_MODEL` | related_name='favorite_drive_documents' |

Metody/properties: `extension`, `office_type`, `icon`, `__str__`.

### `WorkspaceDocumentFolder`

Źródło: [backend/documents/models.py](../backend/documents/models.py).

Pola zadeklarowane tutaj: `name` (CharField), `color` (CharField), `parent` (ForeignKey), `workplace` (ForeignKey), `owner` (ForeignKey), `is_starred` (BooleanField), `created_at` (DateTimeField).

| Relacja | Cel | Ustawienia |
| --- | --- | --- |
| `parent` | `'self'` | on_delete=models.RESTRICT; related_name='children'; null=True |
| `workplace` | `'workplaces.Workplace'` | on_delete=models.CASCADE; related_name='office_folders' |
| `owner` | `settings.AUTH_USER_MODEL` | on_delete=models.CASCADE; related_name='office_folders' |

Metody/properties: `__str__`.

### `WorkspaceDocument`

Źródło: [backend/documents/models.py](../backend/documents/models.py).

Pola zadeklarowane tutaj: `id` (UUIDField), `title` (CharField), `kind` (CharField), `content` (TextField), `is_template` (BooleanField), `is_pdf_form` (BooleanField), `revision` (PositiveIntegerField), `office_key` (UUIDField), `office_save_error` (BooleanField), `file` (FileField), `filename` (CharField), `file_size` (PositiveBigIntegerField), `folder` (ForeignKey), `workplace` (ForeignKey), `owner` (ForeignKey), `tags` (ManyToManyField), `favorited_by` (ManyToManyField), `deleted_at` (DateTimeField), `created_at` (DateTimeField), `updated_at` (DateTimeField).

| Relacja | Cel | Ustawienia |
| --- | --- | --- |
| `folder` | `WorkspaceDocumentFolder` | on_delete=models.RESTRICT; related_name='documents'; null=True |
| `workplace` | `'workplaces.Workplace'` | on_delete=models.CASCADE; related_name='office_documents' |
| `owner` | `settings.AUTH_USER_MODEL` | on_delete=models.CASCADE; related_name='office_documents' |
| `tags` | `'tasks.TaskTag'` | related_name='office_documents' |
| `favorited_by` | `settings.AUTH_USER_MODEL` | related_name='favorite_workspace_documents' |

Metody/properties: `extension`, `office_type`, `has_full_editor`, `icon`, `__str__`.

### `OfficeSaveReceipt`

Źródło: [backend/documents/models.py](../backend/documents/models.py).

Pola zadeklarowane tutaj: `document` (ForeignKey), `digest` (CharField), `created_at` (DateTimeField).

| Relacja | Cel | Ustawienia |
| --- | --- | --- |
| `document` | `WorkspaceDocument` | on_delete=models.CASCADE; related_name='save_receipts' |

### `DriveOfficeSaveReceipt`

Źródło: [backend/documents/models.py](../backend/documents/models.py).

Pola zadeklarowane tutaj: `document` (ForeignKey), `digest` (CharField), `created_at` (DateTimeField).

| Relacja | Cel | Ustawienia |
| --- | --- | --- |
| `document` | `Document` | on_delete=models.CASCADE; related_name='save_receipts' |

### `DocumentVersion`

Źródło: [backend/documents/models.py](../backend/documents/models.py).

Pola zadeklarowane tutaj: `document` (ForeignKey), `drive_document` (ForeignKey), `revision` (PositiveIntegerField), `file` (FileField), `filename` (CharField), `file_size` (PositiveBigIntegerField), `is_pdf_form` (BooleanField), `saved_at` (DateTimeField), `archived_at` (DateTimeField).

| Relacja | Cel | Ustawienia |
| --- | --- | --- |
| `document` | `WorkspaceDocument` | on_delete=models.CASCADE; related_name='versions'; null=True |
| `drive_document` | `Document` | on_delete=models.CASCADE; related_name='versions'; null=True |

## Modele: resources

### `Resource`

Źródło: [backend/resources/models.py](../backend/resources/models.py).

Pola zadeklarowane tutaj: `owner` (ForeignKey), `workplace` (ForeignKey), `name` (CharField), `kind` (CharField), `inventory_number` (CharField), `serial_number` (CharField), `status` (CharField), `assigned_to` (ForeignKey), `location` (CharField), `purchased_on` (DateField), `expires_on` (DateField), `return_due_on` (DateField), `notes` (TextField), `created_by` (ForeignKey), `updated_by` (ForeignKey), `created_at` (DateTimeField), `updated_at` (DateTimeField).

| Relacja | Cel | Ustawienia |
| --- | --- | --- |
| `owner` | `settings.AUTH_USER_MODEL` | on_delete=models.CASCADE; related_name='owned_resources' |
| `workplace` | `'workplaces.Workplace'` | on_delete=models.CASCADE; related_name='resources' |
| `assigned_to` | `settings.AUTH_USER_MODEL` | on_delete=models.SET_NULL; related_name='assigned_resources'; null=True |
| `created_by` | `settings.AUTH_USER_MODEL` | on_delete=models.SET_NULL; related_name='created_resources'; null=True |
| `updated_by` | `settings.AUTH_USER_MODEL` | on_delete=models.SET_NULL; related_name='updated_resources'; null=True |

Metody/properties: `icon`, `__str__`.

### `ResourceActivity`

Źródło: [backend/resources/models.py](../backend/resources/models.py).

Pola zadeklarowane tutaj: `resource` (ForeignKey), `actor` (ForeignKey), `actor_name` (CharField), `action` (CharField), `changes` (JSONField), `note` (TextField), `created_at` (DateTimeField).

| Relacja | Cel | Ustawienia |
| --- | --- | --- |
| `resource` | `Resource` | on_delete=models.CASCADE; related_name='activities' |
| `actor` | `settings.AUTH_USER_MODEL` | on_delete=models.SET_NULL; related_name='resource_activities'; null=True |

## Modele: spaces

### `SpaceConfiguration`

Źródło: [backend/spaces/models.py](../backend/spaces/models.py).

Pola zadeklarowane tutaj: `workplace` (ForeignKey), `name` (CharField), `shared` (BooleanField), `settings` (JSONField).

| Relacja | Cel | Ustawienia |
| --- | --- | --- |
| `workplace` | `'workplaces.Workplace'` | on_delete=models.CASCADE |

Metody/properties: `__str__`.

### `Space`

Źródło: [backend/spaces/models.py](../backend/spaces/models.py).

Pola zadeklarowane tutaj: `name` (CharField), `description` (TextField), `user` (ForeignKey), `responsible_user` (ForeignKey), `visibility` (CharField), `private_owner` (ForeignKey), `favorited_by` (ManyToManyField), `workplace` (ForeignKey), `key` (CharField), `slug` (SlugField), `kind` (CharField), `template` (CharField), `management` (CharField), `configuration` (ForeignKey), `next_number` (PositiveIntegerField), `avatar` (CharField), `avatar_photo` (FileField), `created_at` (DateTimeField).

| Relacja | Cel | Ustawienia |
| --- | --- | --- |
| `user` | `settings.AUTH_USER_MODEL` | on_delete=models.CASCADE; related_name='owned_spaces' |
| `responsible_user` | `settings.AUTH_USER_MODEL` | on_delete=models.SET_NULL; related_name='responsible_spaces'; null=True |
| `private_owner` | `settings.AUTH_USER_MODEL` | on_delete=models.SET_NULL; related_name='private_spaces'; null=True |
| `favorited_by` | `settings.AUTH_USER_MODEL` | related_name='favorite_spaces' |
| `workplace` | `'workplaces.Workplace'` | on_delete=models.CASCADE |
| `configuration` | `SpaceConfiguration` | on_delete=models.RESTRICT; related_name='spaces' |

Metody/properties: `save`, `__str__`, `statuses`.

### `SpaceMembership`

Źródło: [backend/spaces/models.py](../backend/spaces/models.py).

Pola zadeklarowane tutaj: `space` (ForeignKey), `user` (ForeignKey), `role` (CharField).

| Relacja | Cel | Ustawienia |
| --- | --- | --- |
| `space` | `Space` | on_delete=models.CASCADE; related_name='memberships' |
| `user` | `settings.AUTH_USER_MODEL` | on_delete=models.CASCADE |

### `SpaceDashboardLayout`

Źródło: [backend/spaces/models.py](../backend/spaces/models.py).

Pola zadeklarowane tutaj: `space` (ForeignKey), `user` (ForeignKey), `widgets` (JSONField), `revision` (PositiveIntegerField), `updated_at` (DateTimeField).

| Relacja | Cel | Ustawienia |
| --- | --- | --- |
| `space` | `Space` | on_delete=models.CASCADE; related_name='dashboard_layouts' |
| `user` | `settings.AUTH_USER_MODEL` | on_delete=models.CASCADE; related_name='space_dashboard_layouts' |

### `SpaceTask`

Źródło: [backend/spaces/models.py](../backend/spaces/models.py).

Pola zadeklarowane tutaj: `task_type` (CharField), `task_group` (CharField), `reminder_at` (DateTimeField), `space` (ForeignKey), `title` (CharField), `description` (TextField), `priority` (CharField), `status` (CharField), `is_completed` (BooleanField), `completion_date` (DateTimeField), `blocked_reason` (TextField), `blocked_at` (DateTimeField), `blocked_by` (ForeignKey), `blocked_responsible` (ForeignKey), `blocked_revision` (PositiveIntegerField), `created_at` (DateTimeField), `created_by` (ForeignKey), `assignee` (ForeignKey), `due_at` (DateTimeField), `parent` (ForeignKey), `tags` (ManyToManyField), `favorited_by` (ManyToManyField), `visibility` (CharField), `private_owner` (ForeignKey).

| Relacja | Cel | Ustawienia |
| --- | --- | --- |
| `space` | `Space` | on_delete=models.CASCADE; related_name='tasks' |
| `blocked_by` | `settings.AUTH_USER_MODEL` | on_delete=models.SET_NULL; related_name='blocked_space_tasks'; null=True |
| `blocked_responsible` | `settings.AUTH_USER_MODEL` | on_delete=models.SET_NULL; related_name='space_task_blockers'; null=True |
| `created_by` | `settings.AUTH_USER_MODEL` | on_delete=models.SET_NULL; related_name='created_space_tasks'; null=True |
| `assignee` | `settings.AUTH_USER_MODEL` | on_delete=models.SET_NULL; related_name='assigned_space_tasks'; null=True |
| `parent` | `'self'` | on_delete=models.CASCADE; related_name='subtasks'; null=True |
| `tags` | `'tasks.TaskTag'` | related_name='space_tasks' |
| `favorited_by` | `settings.AUTH_USER_MODEL` | related_name='favorite_space_tasks' |
| `private_owner` | `settings.AUTH_USER_MODEL` | on_delete=models.SET_NULL; related_name='private_space_tasks'; null=True |

Metody/properties: `__str__`, `get_task_type_display`, `get_task_group_display`, `save`, `due_urgency`.

### `SpaceTaskMembership`

Źródło: [backend/spaces/models.py](../backend/spaces/models.py).

Pola zadeklarowane tutaj: `created_at` (DateTimeField), `task` (ForeignKey), `user` (ForeignKey), `role` (CharField).

| Relacja | Cel | Ustawienia |
| --- | --- | --- |
| `task` | `SpaceTask` | on_delete=models.CASCADE; related_name='memberships' |
| `user` | `settings.AUTH_USER_MODEL` | on_delete=models.CASCADE |

### `SpaceTaskActivity`

Źródło: [backend/spaces/models.py](../backend/spaces/models.py).

Pola zadeklarowane tutaj: `task` (ForeignKey), `actor` (ForeignKey), `kind` (CharField), `action` (CharField), `message` (TextField), `metadata` (JSONField), `created_at` (DateTimeField).

| Relacja | Cel | Ustawienia |
| --- | --- | --- |
| `task` | `SpaceTask` | on_delete=models.CASCADE; related_name='activities' |
| `actor` | `settings.AUTH_USER_MODEL` | on_delete=models.SET_NULL; null=True |

Metody/properties: `get_action_display`.

### `SpaceTaskFile`

Źródło: [backend/spaces/models.py](../backend/spaces/models.py).

Pola zadeklarowane tutaj: `task` (ForeignKey), `activity` (ForeignKey), `file` (FileField), `filename` (CharField), `file_size` (PositiveIntegerField).

| Relacja | Cel | Ustawienia |
| --- | --- | --- |
| `task` | `SpaceTask` | on_delete=models.CASCADE; related_name='attachments' |
| `activity` | `SpaceTaskActivity` | on_delete=models.CASCADE; related_name='images'; null=True |

Metody/properties: `get_url`.

### `SpaceTaskReminder`

Źródło: [backend/spaces/models.py](../backend/spaces/models.py).

Pola zadeklarowane tutaj: `task` (ForeignKey), `recipient` (ForeignKey), `scheduled_at` (DateTimeField), `created_at` (DateTimeField).

| Relacja | Cel | Ustawienia |
| --- | --- | --- |
| `task` | `SpaceTask` | on_delete=models.CASCADE |
| `recipient` | `settings.AUTH_USER_MODEL` | on_delete=models.CASCADE |

### `SpaceTaskWorkLog`

Źródło: [backend/spaces/models.py](../backend/spaces/models.py).

Pola zadeklarowane tutaj: `task` (ForeignKey), `author` (ForeignKey), `started_at` (DateTimeField), `ended_at` (DateTimeField), `description` (TextField), `created_at` (DateTimeField), `updated_at` (DateTimeField).

| Relacja | Cel | Ustawienia |
| --- | --- | --- |
| `task` | `SpaceTask` | on_delete=models.CASCADE; related_name='work_logs' |
| `author` | `settings.AUTH_USER_MODEL` | on_delete=models.SET_NULL; null=True |

Metody/properties: `duration_minutes`.

### `Team`

Źródło: [backend/spaces/models.py](../backend/spaces/models.py).

Pola zadeklarowane tutaj: `workplace` (ForeignKey), `owner` (ForeignKey), `created_by` (ForeignKey), `name` (CharField), `description` (TextField), `photo` (FileField), `members` (ManyToManyField), `spaces` (ManyToManyField), `created_at` (DateTimeField).

| Relacja | Cel | Ustawienia |
| --- | --- | --- |
| `workplace` | `'workplaces.Workplace'` | on_delete=models.CASCADE; related_name='teams' |
| `owner` | `settings.AUTH_USER_MODEL` | on_delete=models.CASCADE; related_name='owned_work_teams' |
| `created_by` | `settings.AUTH_USER_MODEL` | on_delete=models.SET_NULL; related_name='created_work_teams'; null=True |
| `members` | `settings.AUTH_USER_MODEL` | related_name='work_teams'; through='TeamMembership' |
| `spaces` | `Space` | related_name='teams' |

Metody/properties: `__str__`.

### `TeamMembership`

Źródło: [backend/spaces/models.py](../backend/spaces/models.py).

Pola zadeklarowane tutaj: `team` (ForeignKey), `user` (ForeignKey), `role` (CharField).

| Relacja | Cel | Ustawienia |
| --- | --- | --- |
| `team` | `Team` | on_delete=models.CASCADE; related_name='memberships' |
| `user` | `settings.AUTH_USER_MODEL` | on_delete=models.CASCADE |

### `Sprint`

Źródło: [backend/spaces/models.py](../backend/spaces/models.py).

Pola zadeklarowane tutaj: `space` (ForeignKey), `name` (CharField), `goal` (TextField), `start_on` (DateField), `end_on` (DateField), `state` (CharField), `completed_at` (DateTimeField), `result` (JSONField).

| Relacja | Cel | Ustawienia |
| --- | --- | --- |
| `space` | `Space` | on_delete=models.CASCADE; related_name='sprints' |

Metody/properties: `__str__`.

### `WorkItem`

Źródło: [backend/spaces/models.py](../backend/spaces/models.py).

Pola zadeklarowane tutaj: `task` (OneToOneField), `space` (ForeignKey), `key` (CharField), `number` (PositiveIntegerField), `status` (CharField), `work_type` (CharField), `rank` (PositiveIntegerField), `in_backlog` (BooleanField), `team` (ForeignKey), `sprint` (ForeignKey), `epic` (ForeignKey), `points` (PositiveIntegerField), `start_at` (DateTimeField), `custom_values` (JSONField), `status_entered_at` (DateTimeField), `flow_started_at` (DateTimeField), `flow_finished_at` (DateTimeField).

| Relacja | Cel | Ustawienia |
| --- | --- | --- |
| `task` | `SpaceTask` | on_delete=models.CASCADE; related_name='work_item'; null=True |
| `space` | `Space` | on_delete=models.CASCADE; related_name='items'; null=True |
| `team` | `Team` | on_delete=models.SET_NULL; related_name='items'; null=True |
| `sprint` | `Sprint` | on_delete=models.SET_NULL; related_name='items'; null=True |
| `epic` | `'self'` | on_delete=models.SET_NULL; related_name='epic_items'; null=True |

Metody/properties: `save`, `get_work_type_display`, `type_color`, `type_icon`.

## 3. Formularze

Wypisane są deklaracje klas, także bazowe klasy i widgety.

### accounts

Źródło: [backend/accounts/forms.py](../backend/accounts/forms.py).

- `UserRegistrationForm` — Meta.fields: `('first_name', 'middle_name', 'last_name', 'email')`
- `UserBannerForm` — Meta.fields: `('profile_banner', 'profile_banner_x', 'profile_banner_y', 'profile_banner_zoom')`
- `UserProfileForm` — Meta.fields: `('avatar', 'profile_photo', 'first_name', 'middle_name', 'last_name', 'email', 'username', 'phone_number', 'job_title', 'bio', 'presence_status')`

### workplaces

Źródło: [backend/workplaces/forms.py](../backend/workplaces/forms.py).

- `WorkplaceModuleSelect`
- `RegistrationWorkspaceForm`
- `WorkplaceDeleteForm`
- `WorkplaceForm` — Meta.fields: `['avatar', 'workplace_photo', 'name', 'description']`

### tasks

Źródło: [backend/tasks/forms.py](../backend/tasks/forms.py).

- `TaskTagForm` — Meta.fields: `['name', 'description', 'category', 'color', 'icon', 'priority', 'scope', 'owner_label', 'status', 'usage_notes', 'automation_rules', 'related_tags']`

### planner

Źródło: [backend/planner/forms.py](../backend/planner/forms.py).

- `CalendarEventForm` — Meta.fields: `['title', 'description', 'start', 'end', 'all_day', 'color']`

### documents

Źródło: [backend/documents/forms.py](../backend/documents/forms.py).

- `MultipleFileInput`
- `MultipleFileField`
- `UploadForm`
- `IconColorForm`
- `LibraryForm` — Meta.fields: `['name', 'color', 'description']`
- `FolderForm` — Meta.fields: `['name', 'color']`
- `DocumentForm` — Meta.fields: `['title', 'description', 'folder']`

### resources

Źródło: [backend/resources/forms.py](../backend/resources/forms.py).

- `ResourceForm` — Meta.fields: `['name', 'kind', 'inventory_number', 'serial_number', 'status', 'assigned_to', 'location', 'purchased_on', 'expires_on', 'return_due_on', 'notes']`
- `ResourceOperationForm`

### spaces

Źródło: [backend/spaces/forms.py](../backend/spaces/forms.py).

- `StyledForm`
- `SpaceAvatarForm`
- `SpaceForm`
- `SpaceDeleteForm`
- `ItemForm`
- `DetailForm`
- `SubtaskForm`
- `WorkLogForm`
- `SprintForm`
- `SprintCloseForm`
- `TeamForm`
- `TeamDeleteForm`
- `MemberForm`
- `ConfigurationColorField`
- `StatusForm`
- `ConfigurationLabelForm`
- `TypeForm`
- `ClassificationForm`
- `CategoryForm`
- `GroupForm`
- `CustomFieldForm`

## 4. Routing

Ścieżki modułowe są względne wobec include'a w głównym routingu.

### backend/ancore/urls.py

Źródło: [backend/ancore/urls.py](../backend/ancore/urls.py).

| Ścieżka / regex | Widok / include | Nazwa |
| --- | --- | --- |
| `'health/ready/'` | `readiness` | 'health-ready' |
| `'api/v1/navigation/'` | `navigation_api` | 'react-navigation' |
| `'api/v1/shell/'` | `shell_api` | 'react-shell' |
| `'^workplaces/[-a-zA-Z0-9_]+/api/v1/navigation/$'` | `navigation_api` | 'workplace-react-navigation' |
| `'^workplaces/[-a-zA-Z0-9_]+/api/v1/shell/$'` | `shell_api` | 'workplace-react-shell' |
| `'api/v1/page/'` | `page_api` | 'react-page' |
| `'^workplaces/[-a-zA-Z0-9_]+/api/v1/page/$'` | `page_api` | 'workplace-react-page' |
| `'^workplaces/[-a-zA-Z0-9_]+/filters/'` | `include((filter_urls.urlpatterns, 'workplace_filters'), namespace='workplace_filters')` | — |
| `'filters/'` | `include('dashboard.filter_urls')` | — |
| `'^workplaces/[-a-zA-Z0-9_]+/dashboards/'` | `include((pulpit_urls.urlpatterns, 'workplace_pulpits'), namespace='workplace_pulpits')` | — |
| `'dashboards/'` | `include('dashboard.pulpit_urls')` | — |
| `'^workplaces/[-a-zA-Z0-9_]+/'` | `include((spaces_urls.urlpatterns, 'workplace_spaces'), namespace='workplace_spaces')` | — |
| `'^workplaces/[-a-zA-Z0-9_]+/teams/'` | `include((team_urls.urlpatterns, 'workplace_teams'), namespace='workplace_teams')` | — |
| `''` | `include('spaces.urls')` | — |
| `'teams/'` | `include('spaces.team_urls')` | — |
| `'drive-office-service/<uuid:pk>/source/'` | `suite_views.source` | 'drive-office-service-source' |
| `'drive-office-service/<uuid:pk>/callback/'` | `suite_views.callback` | 'drive-office-service-callback' |
| `'office-service/<uuid:pk>/source/'` | `suite_views.source` | 'office-service-source' |
| `'office-service/<uuid:pk>/callback/'` | `suite_views.callback` | 'office-service-callback' |
| `'admin/'` | `admin.site.urls` | — |
| `''` | `include('dashboard.urls')` | — |
| `'accounts/'` | `include('accounts.urls')` | — |
| `'^workplaces/[-a-zA-Z0-9_]+/calendar/'` | `include((planner_urls.urlpatterns, 'workplace_planner'), namespace='workplace_planner')` | — |
| `'^workplaces/[-a-zA-Z0-9_]+/documents/'` | `include((documents_urls.urlpatterns, 'workplace_documents'), namespace='workplace_documents')` | — |
| `'^workplaces/[-a-zA-Z0-9_]+/office/'` | `include((office_urls.urlpatterns, 'workplace_office'), namespace='workplace_office')` | — |
| `'workplaces/'` | `include('workplaces.urls')` | — |
| `'^workplaces/[-a-zA-Z0-9_]+/resources/'` | `include((resources_urls.urlpatterns, 'workplace_resources'), namespace='workplace_resources')` | — |
| `'resources/'` | `include('resources.urls')` | — |
| `'documents/'` | `include('documents.urls')` | — |
| `'office/'` | `include('documents.workspace_urls')` | — |
| `'calendar/'` | `include('planner.urls')` | — |

### backend/accounts/urls.py

Źródło: [backend/accounts/urls.py](../backend/accounts/urls.py).

| Ścieżka / regex | Widok / include | Nazwa |
| --- | --- | --- |
| `'api/v1/page/'` | `accounts_api` | 'accounts-api' |
| `'login/'` | `views.AccountLoginView.as_view()` | 'login' |
| `'logout/'` | `views.AccountLogoutView.as_view()` | 'logout' |
| `'register/'` | `views.register` | 'register' |
| `'register/workspace/'` | `views.register_workspace` | 'register_workspace' |
| `'workspaces/'` | `views.select_workspace` | 'select_workspace' |
| `'profile/'` | `views.profile` | 'profile' |
| `'profile/banner/'` | `views.update_profile_banner` | 'update_profile_banner' |
| `'profile/status/'` | `views.update_presence_status` | 'update_presence_status' |
| `'presence/ping/'` | `views.presence_ping` | 'presence_ping' |

### backend/workplaces/urls.py

Źródło: [backend/workplaces/urls.py](../backend/workplaces/urls.py).

| Ścieżka / regex | Widok / include | Nazwa |
| --- | --- | --- |
| `'join/<uuid:token>/'` | `invitations.join` | 'join-link' |
| `'<int:workplace_id>/invite-links/'` | `invitations.create_link` | 'invite-link-create' |
| `'<int:workplace_id>/invite-links/<int:link_id>/revoke/'` | `invitations.revoke_link` | 'invite-link-revoke' |
| `'<int:workplace_id>/team/candidates/'` | `team_views.member_candidates` | 'member-candidates' |
| `'<int:workplace_id>/team/'` | `team_views.team` | 'team' |
| `'<int:workplace_id>/team/<int:member_id>/'` | `team_views.member_update` | 'member-update' |
| `''` | `views.workplaces` | 'workplaces' |
| `'<int:workplace_id>/switch/'` | `views.switch_workplace` | 'switch' |
| `'<int:workplace_id>/default/'` | `views.set_default_workplace` | 'set-default' |
| `'<int:workplace_id>/favorites/toggle/'` | `views.toggle_sidebar_favorite` | 'toggle-sidebar-favorite' |
| `'<int:workplace_id>/favorites/reorder/'` | `views.reorder_sidebar_favorites` | 'reorder-sidebar-favorites' |
| `'<int:workplace_id>/settings/'` | `views.update_workplace` | 'update' |
| `'<int:workplace_id>/delete/'` | `views.delete_workplace` | 'delete' |
| `'<slug:workplace_slug>/'` | `views.workplace_home` | 'workplace-home' |

### backend/dashboard/urls.py

Źródło: [backend/dashboard/urls.py](../backend/dashboard/urls.py).

| Ścieżka / regex | Widok / include | Nazwa |
| --- | --- | --- |
| `'for-you/'` | `views.for_you` | 'for_you' |
| `'^workplaces/[-a-zA-Z0-9_]+/for-you/$'` | `views.for_you` | 'workplace_for_you' |
| `'global-search/'` | `views.global_search` | 'global_search' |
| `'settings/'` | `views.settings` | 'settings' |
| `'notifications/'` | `views.notifications` | 'notifications' |
| `'notifications/action/'` | `views.notification_action` | 'notification_action' |
| `''` | `views.home` | 'home' |

### backend/planner/urls.py

Źródło: [backend/planner/urls.py](../backend/planner/urls.py).

| Ścieżka / regex | Widok / include | Nazwa |
| --- | --- | --- |
| `''` | `views.index` | 'index' |
| `'sidebar/'` | `views.sidebar` | 'sidebar' |
| `'events/'` | `views.events_list` | 'events' |
| `'events/create/'` | `views.create_event` | 'create_event' |
| `'events/<int:event_id>/update/'` | `views.update_event` | 'update_event' |
| `'events/<int:event_id>/delete/'` | `views.delete_event` | 'delete_event' |

### backend/documents/urls.py

Źródło: [backend/documents/urls.py](../backend/documents/urls.py).

| Ścieżka / regex | Widok / include | Nazwa |
| --- | --- | --- |
| `''` | `views.library` | 'library' |
| `'libraries/create/'` | `views.library_create` | 'library-create' |
| `'libraries/<int:pk>/edit/'` | `views.library_edit` | 'library-edit' |
| `'libraries/<int:pk>/photo/'` | `views.library_photo` | 'library-photo' |
| `'libraries/<int:pk>/delete/'` | `views.library_delete` | 'library-delete' |
| `'upload/'` | `views.upload` | 'upload' |
| `'folders/<int:pk>/move/'` | `move` | 'folder-move' |
| `'<uuid:pk>/move/'` | `move` | 'move' |
| `'folders/create/'` | `views.folder_create` | 'folder-create' |
| `'folders/<int:pk>/edit/'` | `views.folder_edit` | 'folder-edit' |
| `'folders/<int:pk>/delete/'` | `views.folder_delete` | 'folder-delete' |
| `'folders/<int:pk>/star/'` | `views.folder_star` | 'folder-star' |
| `'folders/<int:pk>/download/'` | `views.folder_download` | 'folder-download' |
| `'<uuid:pk>/'` | `views.detail` | 'detail' |
| `'<uuid:pk>/preview/'` | `views.preview` | 'preview' |
| `'<uuid:pk>/editor/'` | `suite.editor` | 'editor' |
| `'<uuid:pk>/rename/'` | `suite.rename` | 'rename' |
| `'<uuid:pk>/save/'` | `suite.save_office` | 'office-save' |
| `'<uuid:pk>/state/'` | `suite.state` | 'state' |
| `'<uuid:pk>/convert/'` | `suite.convert` | 'convert' |
| `'<uuid:pk>/content/'` | `views.preview_content` | 'preview-content' |
| `'<uuid:pk>/download/'` | `views.download` | 'download' |
| `'<uuid:pk>/star/'` | `views.star` | 'star' |
| `'<uuid:pk>/trash/'` | `views.trash` | 'trash' |
| `'<uuid:pk>/restore/'` | `views.restore` | 'restore' |

### backend/resources/urls.py

Źródło: [backend/resources/urls.py](../backend/resources/urls.py).

| Ścieżka / regex | Widok / include | Nazwa |
| --- | --- | --- |
| `'api/v1/'` | `api.collection` | 'api-list' |
| `'api/v1/new/'` | `api.new` | 'api-new' |
| `'api/v1/operate/'` | `api.operate` | 'api-operate' |
| `'api/v1/export/'` | `api.export` | 'api-export' |
| `'api/v1/<int:pk>/overview/'` | `api.overview` | 'api-overview' |
| `'api/v1/<int:pk>/'` | `api.detail` | 'api-detail' |
| `'api/v1/<int:pk>/delete/'` | `api.delete` | 'api-delete' |
| `''` | `views.index` | 'index' |
| `'create/'` | `views.edit` | 'create' |
| `'<int:pk>/'` | `views.overview` | 'detail' |
| `'<int:pk>/edit/'` | `views.edit` | 'edit' |
| `'<int:pk>/delete/'` | `views.delete` | 'delete' |

### backend/spaces/urls.py

Źródło: [backend/spaces/urls.py](../backend/spaces/urls.py).

| Ścieżka / regex | Widok / include | Nazwa |
| --- | --- | --- |
| `'spaces/'` | `views.index` | 'index' |
| `'spaces/manage/'` | `views.manage` | 'manage' |
| `'spaces/manage/create/'` | `views.edit` | 'manage_create' |
| `'spaces/manage/<int:pk>/edit/'` | `views.edit` | 'manage_edit' |
| `'spaces/search/'` | `views.search` | 'search' |
| `'spaces/create/'` | `views.edit` | 'create' |
| `'spaces/items/'` | `views.retired_all_items` | 'items' |
| `'spaces/items/<int:pk>/edit/'` | `views.item_edit` | 'item_edit' |
| `'spaces/items/<int:pk>/action/'` | `views.item_action` | 'item_action' |
| `'spaces/manage/<slug:pk>/edit/'` | `views.edit` | 'manage_edit' |
| `'space/<slug:pk>/'` | `views.detail` | 'detail' |
| `'space/<slug:pk>/dashboard/layout/'` | `dashboard.save_layout` | 'dashboard_layout' |
| `'space/<slug:space_pk>/tasks/<slug:key>/'` | `task_views.detail` | 'task_detail' |
| `'space/<slug:space_pk>/tasks/<slug:key>/edit/'` | `views.item_edit` | 'task_edit' |
| `'space/<slug:space_pk>/tasks/<slug:key>/action/'` | `views.item_action` | 'task_action' |
| `'space/<slug:space_pk>/tasks/<slug:key>/dates/'` | `timeline.update_dates` | 'task_dates' |
| `'space/<slug:space_pk>/tasks/<slug:key>/team/'` | `task_team.team` | 'task_team' |
| `'space/<slug:space_pk>/tasks/<slug:key>/team/candidates/'` | `task_team.candidates` | 'task_candidates' |
| `'space/<slug:space_pk>/tasks/<slug:key>/members/'` | `task_views.members` | 'task_members' |
| `'space/<slug:space_pk>/tasks/<slug:key>/files/<int:file_pk>/'` | `task_views.download` | 'task_file' |
| `'space/<slug:pk>/edit/'` | `views.edit` | 'edit' |
| `'space/<slug:pk>/delete/'` | `views.delete` | 'delete' |
| `'space/<slug:pk>/avatar/'` | `views.avatar_edit` | 'avatar' |
| `'space/<slug:pk>/avatar/photo/'` | `views.avatar_photo` | 'avatar_photo' |
| `'space/<slug:pk>/favorite/'` | `views.favorite` | 'favorite' |
| `'space/<slug:space_pk>/items/create/'` | `views.item_edit` | 'item_create' |
| `'space/<slug:pk>/sprints/create/'` | `views.sprint_create` | 'sprint_create' |
| `'space/<slug:pk>/backlog/plan/'` | `views.backlog_plan` | 'backlog_plan' |
| `'space/<slug:pk>/sprints/<int:sprint_pk>/edit/'` | `views.sprint_plan` | 'sprint_edit' |
| `'space/<slug:pk>/sprints/<int:sprint_pk>/start/'` | `views.sprint_plan` | 'sprint_start' |
| `'space/<slug:pk>/sprints/<int:sprint_pk>/complete/'` | `views.sprint_plan` | 'sprint_complete' |
| `'space/<slug:pk>/sprints/<int:sprint_pk>/action/'` | `views.sprint_action` | 'sprint_action' |
| `'space/<slug:pk>/members/'` | `views.members` | 'members' |
| `'space/<slug:pk>/team/'` | `space_team.team` | 'space_team' |
| `'space/<slug:pk>/team/candidates/'` | `space_team.candidates` | 'space_candidates' |
| `'space/<slug:pk>/members/<int:member_pk>/remove/'` | `views.remove_member` | 'remove_member' |
| `'space/<slug:pk>/configuration/'` | `views.configuration` | 'configuration' |
| `'spaces/<int:pk>/'` | `views.detail` | 'detail' |
| `'spaces/<int:pk>/dashboard/layout/'` | `dashboard.save_layout` | 'dashboard_layout' |
| `'spaces/<int:pk>/edit/'` | `views.edit` | 'edit' |
| `'spaces/<int:pk>/avatar/'` | `views.avatar_edit` | 'avatar' |
| `'spaces/<int:pk>/avatar/photo/'` | `views.avatar_photo` | 'avatar_photo' |
| `'spaces/<int:pk>/favorite/'` | `views.favorite` | 'favorite' |
| `'spaces/<int:space_pk>/items/create/'` | `views.item_edit` | 'item_create' |
| `'spaces/<int:pk>/sprints/create/'` | `views.sprint_create` | 'sprint_create' |
| `'spaces/<int:pk>/backlog/plan/'` | `views.backlog_plan` | 'backlog_plan' |
| `'spaces/<int:pk>/sprints/<int:sprint_pk>/edit/'` | `views.sprint_plan` | 'sprint_edit' |
| `'spaces/<int:pk>/sprints/<int:sprint_pk>/start/'` | `views.sprint_plan` | 'sprint_start' |
| `'spaces/<int:pk>/sprints/<int:sprint_pk>/complete/'` | `views.sprint_plan` | 'sprint_complete' |
| `'spaces/<int:pk>/sprints/<int:sprint_pk>/action/'` | `views.sprint_action` | 'sprint_action' |
| `'spaces/<int:pk>/members/'` | `views.members` | 'members' |
| `'spaces/<int:pk>/members/<int:member_pk>/remove/'` | `views.remove_member` | 'remove_member' |
| `'spaces/<int:pk>/configuration/'` | `views.configuration` | 'configuration' |

## 5. Pliki backendu i punkty wejścia

Lista funkcji jest statyczna; obejmuje też historyczne, nieużywane helpery.

### ancore

- [backend/ancore/__init__.py](../backend/ancore/__init__.py)
- [backend/ancore/asgi.py](../backend/ancore/asgi.py)
- [backend/ancore/settings.py](../backend/ancore/settings.py) — `env_list`, `env_bool`, `env_int`
- [backend/ancore/testing.py](../backend/ancore/testing.py) — `BackendDiscoverRunner`
- [backend/ancore/urls.py](../backend/ancore/urls.py)
- [backend/ancore/wsgi.py](../backend/ancore/wsgi.py)

### core

- [backend/core/__init__.py](../backend/core/__init__.py)
- [backend/core/api.py](../backend/core/api.py) — `is_api_request`, `api_error`, `api_view`, `json_object`, `csrf_failure`
- [backend/core/apps.py](../backend/core/apps.py) — `CoreConfig`
- [backend/core/avatars.py](../backend/core/avatars.py) — `preset_avatar`
- [backend/core/comment_images.py](../backend/core/comment_images.py) — `comment_image_storage`, `AttachmentPresentation`
- [backend/core/emoji.py](../backend/core/emoji.py) — `emoji_catalog`, `emoji_index`, `find_emoji`, `validate_emoji`, `emoji_art`, `emoji_payload`, `emoji_picker_config`
- [backend/core/frontend.py](../backend/core/frontend.py) — `api_url`, `render`, `form_payload`, `pagination_payload`, `page_api`, `target_request`, `dispatch`, `navigation_api`, `shell_api`
- [backend/core/health.py](../backend/core/health.py) — `readiness`
- [backend/core/hosts.py](../backend/core/hosts.py) — `ServerAddressMiddleware`
- [backend/core/list_window.py](../backend/core/list_window.py) — `WindowPage`, `window_page`, `window_url`, `window_payload`
- [backend/core/media.py](../backend/core/media.py) — `public_media`
- [backend/core/shell.py](../backend/core/shell.py) — `build_id`, `favorite_items`, `shell_payload`, `messages_payload`, `page_styles`, `navigation_response`
- [backend/core/task_files.py](../backend/core/task_files.py) — `delete_after_commit`
- [backend/core/templatetags/__init__.py](../backend/core/templatetags/__init__.py)
- [backend/core/templatetags/frontend.py](../backend/core/templatetags/frontend.py) — `global_panels_bootstrap`, `react_bundle`, `default_today_sidebar`
- [backend/core/templatetags/list_window.py](../backend/core/templatetags/list_window.py) — `load_more_url`
- [backend/core/upload_validation.py](../backend/core/upload_validation.py) — `validate_image_bytes`, `validate_image_crop`, `validate_image_upload`, `validate_attachment_upload`, `validate_comment_attachments`, `attachment_download_response`
- [backend/core/widgets.py](../backend/core/widgets.py) — `EmojiPickerInput`, `VisualSelect`, `VisualSelectMultiple`
- [backend/core/work_logs.py](../backend/core/work_logs.py) — `DateTimeLocalInput`, `TimeLogForm`

### accounts

- [backend/accounts/__init__.py](../backend/accounts/__init__.py)
- [backend/accounts/admin.py](../backend/accounts/admin.py) — `CustomUserAdmin`
- [backend/accounts/api.py](../backend/accounts/api.py) — `accounts_api`
- [backend/accounts/apps.py](../backend/accounts/apps.py) — `AccountsConfig`
- [backend/accounts/avatar.py](../backend/accounts/avatar.py) — `avatar_color_seed`, `avatar_color_style`, `avatar_color_style_from_seed`, `avatar_color_class`, `account_avatar`
- [backend/accounts/avatar_presets.py](../backend/accounts/avatar_presets.py) — `preset_avatar`
- [backend/accounts/backends.py](../backend/accounts/backends.py) — `EmailBackend`
- [backend/accounts/context_processors.py](../backend/accounts/context_processors.py) — `current_account_avatar`
- [backend/accounts/forms.py](../backend/accounts/forms.py) — `UserRegistrationForm`, `UserBannerForm`, `UserProfileForm`
- [backend/accounts/frontend.py](../backend/accounts/frontend.py) — `login_page`, `register_page`, `register_workspace_page`, `select_workspace_page`, `profile_page`
- [backend/accounts/management/__init__.py](../backend/accounts/management/__init__.py)
- [backend/accounts/management/commands/__init__.py](../backend/accounts/management/commands/__init__.py)
- [backend/accounts/management/commands/ensure_admin.py](../backend/accounts/management/commands/ensure_admin.py) — `Command`
- [backend/accounts/middleware.py](../backend/accounts/middleware.py) — `SingleAccountSessionMiddleware`, `UserPresenceMiddleware`
- [backend/accounts/models.py](../backend/accounts/models.py) — `User`, `normalize_public_username`, `default_public_username`, `unique_public_username`
- [backend/accounts/presence.py](../backend/accounts/presence.py) — `idle_seconds`, `heartbeat_seconds`, `write_throttle_seconds`, `mark_user_seen`, `mark_user_inactive`, `sync_stale_presence_statuses`
- [backend/accounts/templatetags/__init__.py](../backend/accounts/templatetags/__init__.py)
- [backend/accounts/templatetags/account_avatar.py](../backend/accounts/templatetags/account_avatar.py) — `user_avatar`
- [backend/accounts/urls.py](../backend/accounts/urls.py)
- [backend/accounts/views.py](../backend/accounts/views.py) — `AccountLoginView`, `AccountLogoutView`, `register`, `register_workspace`, `select_workspace`, `profile`, `update_profile_banner`, `update_presence_status`, `presence_ping`
- [backend/accounts/widgets.py](../backend/accounts/widgets.py) — `UserSelect`, `UserChoiceField`, `UserSelectMultiple`

### workplaces

- [backend/workplaces/__init__.py](../backend/workplaces/__init__.py)
- [backend/workplaces/admin.py](../backend/workplaces/admin.py) — `WorkplaceMembershipInline`, `WorkplaceAdmin`, `WorkplaceMembershipAdmin`, `SidebarFavoriteAdmin`
- [backend/workplaces/apps.py](../backend/workplaces/apps.py) — `WorkplacesConfig`
- [backend/workplaces/context_processors.py](../backend/workplaces/context_processors.py) — `current_workplace`
- [backend/workplaces/forms.py](../backend/workplaces/forms.py) — `WorkplaceModuleSelect`, `RegistrationWorkspaceForm`, `WorkplaceDeleteForm`, `WorkplaceForm`
- [backend/workplaces/frontend.py](../backend/workplaces/frontend.py) — `path`, `person`, `join_page`, `schema`, `form_page`, `directory_page`
- [backend/workplaces/invitations.py](../backend/workplaces/invitations.py) — `pending_join_url`, `InviteLinkForm`, `create_link`, `revoke_link`, `join`
- [backend/workplaces/middleware.py](../backend/workplaces/middleware.py) — `ActiveWorkplaceMiddleware`
- [backend/workplaces/models.py](../backend/workplaces/models.py) — `generate_workplace_code`, `Workplace`, `WorkplaceMembership`, `invitation_expiry`, `WorkplaceInviteLink`, `WorkplaceInviteLinkUse`, `SidebarFavorite`, `create_workplace_for_user`
- [backend/workplaces/navigation.py](../backend/workplaces/navigation.py) — `sidebar_favorite_catalog`, `sidebar_favorite_is_active`, `sidebar_favorites_for_request`
- [backend/workplaces/policy.py](../backend/workplaces/policy.py) — `module_enabled`, `read_only`, `module_for_request`, `module_for_path`, `check_access`, `restrict_page`
- [backend/workplaces/services.py](../backend/workplaces/services.py) — `workplace_management_url`, `workplaces_for_user`, `workplace_role`, `can_manage_team`, `workspace_owner`, `workplace_people`, `default_workplace_for_user`, `ensure_default_workplace`, `set_active_workplace`, `enable_workspace_url_scope`, `workspace_url_scope_enabled`, `scoped_workplace_app_path`, `legacy_app_path_to_scoped`, `get_active_workplace`
- [backend/workplaces/team_views.py](../backend/workplaces/team_views.py) — `TeamRoleSelect`, `AddMemberForm`, `member_candidates`, `team`, `team_context`, `member_update`
- [backend/workplaces/templatetags/__init__.py](../backend/workplaces/templatetags/__init__.py)
- [backend/workplaces/templatetags/sidebar_favorites.py](../backend/workplaces/templatetags/sidebar_favorites.py) — `sidebar_favorite_toggle`
- [backend/workplaces/templatetags/workplace_avatar.py](../backend/workplaces/templatetags/workplace_avatar.py) — `workplace_avatar_seed`, `workplace_avatar`
- [backend/workplaces/urls.py](../backend/workplaces/urls.py)
- [backend/workplaces/views.py](../backend/workplaces/views.py) — `workplaces`, `render_workplaces`, `switch_workplace`, `set_default_workplace`, `toggle_sidebar_favorite`, `reorder_sidebar_favorites`, `workplace_home`, `update_workplace`, `delete_workplace`

### tasks

- [backend/tasks/__init__.py](../backend/tasks/__init__.py)
- [backend/tasks/admin.py](../backend/tasks/admin.py)
- [backend/tasks/apps.py](../backend/tasks/apps.py) — `TasksConfig`
- [backend/tasks/forms.py](../backend/tasks/forms.py) — `TaskTagForm`
- [backend/tasks/models.py](../backend/tasks/models.py) — `TaskTag`, `TaskTagNote`
- [backend/tasks/tag_directory.py](../backend/tasks/tag_directory.py) — `tag_window_for_request`
- [backend/tasks/tagging.py](../backend/tasks/tagging.py) — `tags_in_scope`, `visible_tags`, `tag_action`

### dashboard

- [backend/dashboard/__init__.py](../backend/dashboard/__init__.py)
- [backend/dashboard/admin.py](../backend/dashboard/admin.py)
- [backend/dashboard/apps.py](../backend/dashboard/apps.py) — `DashboardConfig`
- [backend/dashboard/collaboration.py](../backend/dashboard/collaboration.py) — `mention_handle`, `mention_label`, `mention_choices`, `comment_mention_metadata`, `mention_people`
- [backend/dashboard/filter_forms.py](../backend/dashboard/filter_forms.py) — `BasicTaskSearchForm`, `SavedTaskFilterForm`, `FilterSettingsForm`
- [backend/dashboard/filter_frontend.py](../backend/dashboard/filter_frontend.py) — `filter_payload`, `filter_form_payload`, `modal_payload`, `catalog_page`, `search_page`
- [backend/dashboard/filter_search.py](../backend/dashboard/filter_search.py) — `QueryError`, `quote`, `SearchQuery`, `Parser`, `parse_query`, `date_value`, `Compiler`, `apply_query`, `basic_query`
- [backend/dashboard/filter_sharing.py](../backend/dashboard/filter_sharing.py) — `ShareForm`, `payload`, `team_url`, `team`, `candidates`
- [backend/dashboard/filter_urls.py](../backend/dashboard/filter_urls.py)
- [backend/dashboard/filter_views.py](../backend/dashboard/filter_views.py) — `get_filter`, `directory_url`, `catalog_context`, `search_context`, `index`, `manage`, `search`, `lookup`, `mutation_response`, `return_url`, `edit`, `save_query`, `favorite`, `delete`
- [backend/dashboard/filters.py](../backend/dashboard/filters.py) — `filter_url`, `visible_filters`, `filter_role`, `can_manage_filter`, `can_edit_filter_query`, `decorate_filter`, `sidebar_filters`
- [backend/dashboard/for_you.py](../backend/dashboard/for_you.py) — `for_you_context`
- [backend/dashboard/frontend.py](../backend/dashboard/frontend.py) — `for_you_page`, `settings_page`
- [backend/dashboard/identifiers.py](../backend/dashboard/identifiers.py) — `DashboardSlugConverter`, `unique_dashboard_slug`
- [backend/dashboard/models.py](../backend/dashboard/models.py) — `SavedTaskFilter`, `SavedTaskFilterMembership`, `Dashboard`, `DashboardMembership`, `DashboardGadget`, `NotificationState`
- [backend/dashboard/notification_frontend.py](../backend/dashboard/notification_frontend.py) — `notification_payload`
- [backend/dashboard/notification_service.py](../backend/dashboard/notification_service.py) — `notification_filters`, `notification_sources`, `filtered_sources`, `notification_summary`, `notification_page`, `change_notification_state`
- [backend/dashboard/pulpit_forms.py](../backend/dashboard/pulpit_forms.py) — `style_fields`, `DashboardVisibilitySelect`, `DashboardAccessForm`, `configure_preferences`, `DashboardPreferencesMixin`, `DashboardForm`, `DashboardSettingsForm`, `GadgetKindSelect`, `GadgetForm`
- [backend/dashboard/pulpit_frontend.py](../backend/dashboard/pulpit_frontend.py) — `dashboard_payload`, `gadget_payload`, `pulpit_form_payload`, `modal_payload`, `directory_page`, `detail_page`, `edit_page`
- [backend/dashboard/pulpit_grid.py](../backend/dashboard/pulpit_grid.py) — `overlaps`, `free_position`, `legacy_widgets`, `resolved_widgets`, `place_new_gadget`, `validate_widgets`
- [backend/dashboard/pulpit_navigation.py](../backend/dashboard/pulpit_navigation.py) — `sidebar_dashboards`
- [backend/dashboard/pulpit_sharing.py](../backend/dashboard/pulpit_sharing.py) — `ShareForm`, `payload`, `team_url`, `apply_access_draft`, `team`, `candidates`
- [backend/dashboard/pulpit_urls.py](../backend/dashboard/pulpit_urls.py)
- [backend/dashboard/pulpit_views.py](../backend/dashboard/pulpit_views.py) — `get_dashboard`, `index_context`, `index`, `search`, `management_url`, `manage`, `detail`, `default`, `editor_navigation_context`, `editor_context`, `gadgets`, `form_response`, `saved_response`, `edit`, `access`, `delete`, `favorite`, `gadget_edit`, `gadget_delete`, `gadget_quick_add`, `arrange`, `arrange_grid`
- [backend/dashboard/pulpits.py](../backend/dashboard/pulpits.py) — `app_url`, `visible_dashboards`, `dashboard_role`, `can_edit_dashboard`, `can_manage_dashboard`, `default_dashboard`, `dashboard_url`, `decorate_dashboard`, `decorate_gadget`, `dashboard_data_scope`, `gadget_data`, `detail_context`
- [backend/dashboard/recent.py](../backend/dashboard/recent.py) — `remember_view`, `recent_views`
- [backend/dashboard/reminders.py](../backend/dashboard/reminders.py) — `space_reminders_for_user`
- [backend/dashboard/signals.py](../backend/dashboard/signals.py) — `removed_workspace_member`, `disabled_workspace_member`
- [backend/dashboard/urls.py](../backend/dashboard/urls.py)
- [backend/dashboard/views.py](../backend/dashboard/views.py) — `global_search`, `settings`, `for_you`, `home`, `notifications`, `notification_action`

### planner

- [backend/planner/__init__.py](../backend/planner/__init__.py)
- [backend/planner/admin.py](../backend/planner/admin.py) — `CalendarEventAdmin`
- [backend/planner/apps.py](../backend/planner/apps.py) — `PlannerConfig`
- [backend/planner/forms.py](../backend/planner/forms.py) — `CalendarEventForm`
- [backend/planner/frontend.py](../backend/planner/frontend.py) — `calendar_page`
- [backend/planner/models.py](../backend/planner/models.py) — `CalendarEvent`
- [backend/planner/sidebar.py](../backend/planner/sidebar.py) — `sidebar_url`, `today_sidebar_payload`, `sidebar_template_context`
- [backend/planner/urls.py](../backend/planner/urls.py)
- [backend/planner/views.py](../backend/planner/views.py) — `index`, `sidebar`, `events_list`, `create_event`, `update_event`, `delete_event`

### documents

- [backend/documents/__init__.py](../backend/documents/__init__.py)
- [backend/documents/apps.py](../backend/documents/apps.py) — `DocumentsConfig`
- [backend/documents/board.py](../backend/documents/board.py) — `clean_scene`
- [backend/documents/editor_forms.py](../backend/documents/editor_forms.py) — `validate_document`, `DocumentFilesField`, `OfficeUploadForm`, `OfficeCreateForm`, `OfficeRenameForm`, `OfficeTemplateForm`, `OfficeDocumentForm`
- [backend/documents/editor_views.py](../backend/documents/editor_views.py) — `index`, `upload`, `edit`, `preview`, `import_text`, `download`, `content`, `action`
- [backend/documents/file_cleanup.py](../backend/documents/file_cleanup.py) — `delete_replaced_file`
- [backend/documents/folder_exports.py](../backend/documents/folder_exports.py) — `folder_archive`
- [backend/documents/folder_stats.py](../backend/documents/folder_stats.py) — `set_folder_summaries`
- [backend/documents/forms.py](../backend/documents/forms.py) — `MultipleFileInput`, `MultipleFileField`, `UploadForm`, `IconColorForm`, `LibraryForm`, `FolderForm`, `DocumentForm`
- [backend/documents/frontend.py](../backend/documents/frontend.py) — `dates`, `file_variant`, `file_payload`, `library_payload`, `modal_payload`, `form_page`, `directory_page`, `text_page`, `suite_page`
- [backend/documents/location_lock.py](../backend/documents/location_lock.py) — `location_write`
- [backend/documents/models.py](../backend/documents/models.py) — `document_storage`, `document_upload_path`, `library_photo_upload_path`, `DocumentLibrary`, `delete_library_photo`, `Folder`, `Document`, `delete_drive_document_file`, `WorkspaceDocumentFolder`, `WorkspaceDocument`, `delete_workspace_document_file`, `OfficeSaveReceipt`, `DriveOfficeSaveReceipt`, `DocumentVersion`, `delete_document_version_file`
- [backend/documents/move_views.py](../backend/documents/move_views.py) — `MoveForm`, `move`
- [backend/documents/office_extras.py](../backend/documents/office_extras.py) — `from_template`, `template_toggle`
- [backend/documents/office_service.py](../backend/documents/office_service.py) — `configured`, `sign`, `verify`, `capability`, `check_capability`, `service_url`, `document_key`, `save_confirmation`, `editor_config`, `NoRedirect`, `download_result`, `force_save`, `validate_ooxml`, `blank_file`, `receipt_digest`, `convert_file`
- [backend/documents/previews.py](../backend/documents/previews.py) — `inline_type`, `validate_inline`, `OfficePackage`, `build_preview`
- [backend/documents/query.py](../backend/documents/query.py) — `text_field`, `choice_field`, `query_context`, `apply_text_filters`, `apply_date_filter`, `order_results`
- [backend/documents/rich_text.py](../backend/documents/rich_text.py) — `DocumentHTML`, `clean_content`, `text_to_content`, `docx_bytes`
- [backend/documents/stars.py](../backend/documents/stars.py) — `with_personal_stars`, `toggle_star`
- [backend/documents/suite_views.py](../backend/documents/suite_views.py) — `create`, `editor`, `board_frame`, `rename`, `save_board`, `save_office`, `state`, `source`, `callback`, `upgrade_text`, `convert`
- [backend/documents/urls.py](../backend/documents/urls.py)
- [backend/documents/views.py](../backend/documents/views.py) — `library`, `library_create`, `library_edit`, `library_photo`, `library_delete`, `upload`, `folder_create`, `folder_edit`, `folder_delete`, `folder_star`, `folder_download`, `detail`, `preview`, `preview_content`, `download`, `star`, `trash`, `restore`
- [backend/documents/workspace_urls.py](../backend/documents/workspace_urls.py)

### resources

- [backend/resources/__init__.py](../backend/resources/__init__.py)
- [backend/resources/api.py](../backend/resources/api.py) — `resource_payload`, `editor_payload`, `directory_payload`, `collection`, `new`, `detail`, `delete`, `overview_payload`, `overview`, `operate`, `csv_cell`, `export`
- [backend/resources/apps.py](../backend/resources/apps.py) — `ResourcesConfig`
- [backend/resources/forms.py](../backend/resources/forms.py) — `ResourceForm`, `ResourceOperationForm`
- [backend/resources/models.py](../backend/resources/models.py) — `Resource`, `ResourceActivity`
- [backend/resources/services.py](../backend/resources/services.py) — `resource_scope`, `resource_base_url`, `resource_params`, `directory_url`, `filtered_resources`, `resource_summary`, `directory_context`, `resource_snapshot`, `record_activity`, `save_resource_form`
- [backend/resources/urls.py](../backend/resources/urls.py)
- [backend/resources/views.py](../backend/resources/views.py) — `index`, `edit`, `overview`, `delete`

### spaces

- [backend/spaces/__init__.py](../backend/spaces/__init__.py)
- [backend/spaces/access.py](../backend/spaces/access.py) — `spaces_for`, `editable_spaces`, `tree_ids`, `visible_to`, `editable_to`, `require_editable`, `task_people`
- [backend/spaces/apps.py](../backend/spaces/apps.py) — `SpacesConfig`
- [backend/spaces/avatars.py](../backend/spaces/avatars.py) — `avatar_upload_path`, `space_avatar`, `delete_avatar_after_commit`, `save_space_avatar`
- [backend/spaces/backlog.py](../backend/spaces/backlog.py) — `append_planned_items`, `bulk_plan_items`, `posted_number`, `free_rank`, `redistribute_ranks`, `move_backlog_item`
- [backend/spaces/backlog_window.py](../backend/spaces/backlog_window.py) — `limit_parameter`, `backlog_window`, `backlog_more_url`
- [backend/spaces/board.py](../backend/spaces/board.py) — `move_board_item`
- [backend/spaces/dashboard.py](../backend/spaces/dashboard.py) — `widget_catalog`, `default_widgets`, `dashboard_payload`, `validate_widgets`, `save_layout`
- [backend/spaces/defaults.py](../backend/spaces/defaults.py) — `classification_options`, `classification_label`, `issue_type_icon`, `configuration_name_color`, `status_appearance`, `status_icon`, `status_flow_stage`, `template_settings`
- [backend/spaces/forms.py](../backend/spaces/forms.py) — `StyledForm`, `SpaceAvatarForm`, `SpaceForm`, `SpaceDeleteForm`, `ItemForm`, `DetailForm`, `SubtaskForm`, `WorkLogForm`, `SprintForm`, `SprintCloseForm`, `TeamForm`, `TeamDeleteForm`, `MemberForm`, `ConfigurationColorField`, `StatusForm`, `ConfigurationLabelForm`, `TypeForm`, `ClassificationForm`, `CategoryForm`, `GroupForm`, `CustomFieldForm`
- [backend/spaces/frontend.py](../backend/spaces/frontend.py) — `space_payload`, `modal_payload`, `form_page`, `directory_page`, `item_payload`, `sprint_payload`, `detail_page`, `configuration_page`, `task_members_payload`, `file_payload`, `activity_payload`, `task_page`, `teams_page`, `team_page`
- [backend/spaces/identifiers.py](../backend/spaces/identifiers.py) — `unique_space_slug`
- [backend/spaces/item_query.py](../backend/spaces/item_query.py) — `item_sort`, `order_items`
- [backend/spaces/list_window.py](../backend/spaces/list_window.py) — `status_limit`, `group_limit`, `list_window`, `more_url`, `timeline_more_url`, `list_url`
- [backend/spaces/models.py](../backend/spaces/models.py) — `SpaceConfiguration`, `Space`, `SpaceMembership`, `SpaceDashboardLayout`, `SpaceTask`, `SpaceTaskMembership`, `SpaceTaskActivity`, `SpaceTaskFile`, `SpaceTaskReminder`, `SpaceTaskWorkLog`, `Team`, `TeamMembership`, `Sprint`, `WorkItem`
- [backend/spaces/navigation.py](../backend/spaces/navigation.py) — `sidebar_spaces`
- [backend/spaces/reports.py](../backend/spaces/reports.py) — `report_scope`, `period_window`, `minutes_label`, `percent`, `report_url`, `space_reports`, `safe_csv_cell`, `report_csv`
- [backend/spaces/schedule.py](../backend/spaces/schedule.py) — `ScheduleDateTimeField`, `local_date`, `validate_range`, `move_to_date`
- [backend/spaces/services.py](../backend/spaces/services.py) — `app_url`, `space_url`, `visible_spaces`, `manageable_spaces`, `can_manage_spaces`, `visible_items`, `decorate_directory_spaces`, `teams_for`, `manage_space`, `manage_configuration`, `manage_team`, `task_url`, `task_subtasks_url`, `create_work_item`, `record`, `transition_allowed`, `set_status`, `update_sprint`
- [backend/spaces/signals.py](../backend/spaces/signals.py) — `task_metadata`, `removed_workspace_member`, `disabled_workspace_member`, `removed_space_member`, `removed_task_member`, `deleted_team_photo`, `deleted_space_avatar`, `scoped_related_tags`, `deleted_task_file`, `scoped_space_task_tags`
- [backend/spaces/space_team.py](../backend/spaces/space_team.py) — `ShareForm`, `team_context`, `access_revision`, `payload`, `apply_access_draft`, `team`, `candidates`
- [backend/spaces/summary.py](../backend/spaces/summary.py) — `status_arc_path`, `summary_scope`, `filter_summary_items`, `materialized_summary_items`, `space_summary`
- [backend/spaces/tag_frontend.py](../backend/spaces/tag_frontend.py) — `tag_form_payload`, `tags_page`
- [backend/spaces/task_team.py](../backend/spaces/task_team.py) — `ShareForm`, `team_context`, `payload`, `team`, `candidates`
- [backend/spaces/task_views.py](../backend/spaces/task_views.py) — `task_item`, `return_url`, `manages_task`, `attach_files`, `posted_id`, `property_snapshot`, `property_changes`, `detail_post_data`, `work_log_context`, `detail`, `members`, `download`
- [backend/spaces/team_queries.py](../backend/spaces/team_queries.py) — `administrators`, `directory_context`, `detail_context`
- [backend/spaces/team_urls.py](../backend/spaces/team_urls.py)
- [backend/spaces/teams.py](../backend/spaces/teams.py) — `index`, `detail`, `edit`, `members`, `remove_member`, `delete`, `photo`
- [backend/spaces/templatetags/__init__.py](../backend/spaces/templatetags/__init__.py)
- [backend/spaces/templatetags/space_ui.py](../backend/spaces/templatetags/space_ui.py) — `type_badge_style`, `status_style`, `pagination_pages`, `space_avatar`, `status_groups`
- [backend/spaces/testing.py](../backend/spaces/testing.py) — `make_space`, `make_task`
- [backend/spaces/timeline.py](../backend/spaces/timeline.py) — `local_end`, `posted_date`, `posted_source`, `serialized_precision`, `posted_datetime`, `datetime_label`, `error_response`, `update_dates`
- [backend/spaces/urls.py](../backend/spaces/urls.py)
- [backend/spaces/views.py](../backend/spaces/views.py) — `space_object`, `base_context`, `settings_context`, `decorate_items`, `issue_type_filters`, `index_context`, `directory_url`, `index`, `manage`, `search`, `filtered_space_items`, `items_for_view`, `backlog_url`, `board_url`, `planning_totals`, `detail_context`, `detail`, `retired_all_items`, `dialog_response`, `edit`, `delete`, `avatar_edit`, `avatar_photo`, `favorite`, `item_edit`, `backlog_plan`, `item_action`, `sprint_create`, `sprint_plan`, `sprint_action`, `members`, `remove_member`, `configuration`
- [backend/spaces/widgets.py](../backend/spaces/widgets.py) — `IssueTypeSelect`, `TaskVisibilitySelect`, `SpaceSelect`, `SpaceSelectMultiple`, `TeamSelect`
- [backend/spaces/workflow.py](../backend/spaces/workflow.py) — `initial_status`, `assert_snapshot`, `validate_placement`, `update_flow_times`, `flow_snapshot`, `board_wip`, `block_responsible_people`, `set_block`

## 6. Szablony

### core

- [backend/core/templates/core/base.html](../backend/core/templates/core/base.html)
- [backend/core/templates/core/emoji.html](../backend/core/templates/core/emoji.html)
- [backend/core/templates/core/includes/attachment_icon.html](../backend/core/templates/core/includes/attachment_icon.html)
- [backend/core/templates/core/includes/avatar_picker.html](../backend/core/templates/core/includes/avatar_picker.html)
- [backend/core/templates/core/includes/avatar_presets.html](../backend/core/templates/core/includes/avatar_presets.html)
- [backend/core/templates/core/includes/bootstrap.html](../backend/core/templates/core/includes/bootstrap.html)
- [backend/core/templates/core/includes/content_skeleton.html](../backend/core/templates/core/includes/content_skeleton.html)
- [backend/core/templates/core/includes/field_help.html](../backend/core/templates/core/includes/field_help.html)
- [backend/core/templates/core/includes/icon_credit.html](../backend/core/templates/core/includes/icon_credit.html)
- [backend/core/templates/core/includes/load_more.html](../backend/core/templates/core/includes/load_more.html)
- [backend/core/templates/core/includes/modal_form_field.html](../backend/core/templates/core/includes/modal_form_field.html)
- [backend/core/templates/core/includes/modal_form_fields.html](../backend/core/templates/core/includes/modal_form_fields.html)
- [backend/core/templates/core/includes/photo_crop_dialog.html](../backend/core/templates/core/includes/photo_crop_dialog.html)
- [backend/core/templates/core/includes/priority_icon.html](../backend/core/templates/core/includes/priority_icon.html)
- [backend/core/templates/core/includes/pulpit_editor_sidebar.html](../backend/core/templates/core/includes/pulpit_editor_sidebar.html)
- [backend/core/templates/core/includes/pulpit_settings_sidebar.html](../backend/core/templates/core/includes/pulpit_settings_sidebar.html)
- [backend/core/templates/core/includes/select_priority.html](../backend/core/templates/core/includes/select_priority.html)
- [backend/core/templates/core/includes/select_status.html](../backend/core/templates/core/includes/select_status.html)
- [backend/core/templates/core/includes/settings_secondary_menu.html](../backend/core/templates/core/includes/settings_secondary_menu.html)
- [backend/core/templates/core/includes/settings_sidebar.html](../backend/core/templates/core/includes/settings_sidebar.html)
- [backend/core/templates/core/includes/sidebar_picker.html](../backend/core/templates/core/includes/sidebar_picker.html)
- [backend/core/templates/core/includes/space_settings_sidebar.html](../backend/core/templates/core/includes/space_settings_sidebar.html)
- [backend/core/templates/core/includes/today_sidebar.html](../backend/core/templates/core/includes/today_sidebar.html)
- [backend/core/templates/core/includes/trash_icon.html](../backend/core/templates/core/includes/trash_icon.html)
- [backend/core/templates/core/includes/workplace_management_sidebar.html](../backend/core/templates/core/includes/workplace_management_sidebar.html)
- [backend/core/templates/core/includes/workspace_settings_sidebar.html](../backend/core/templates/core/includes/workspace_settings_sidebar.html)
- [backend/core/templates/core/widgets/emoji_picker.html](../backend/core/templates/core/widgets/emoji_picker.html)
- [backend/core/templates/core/widgets/visual_select.html](../backend/core/templates/core/widgets/visual_select.html)

### accounts

- [backend/accounts/templates/accounts/auth_base.html](../backend/accounts/templates/accounts/auth_base.html)
- [backend/accounts/templates/accounts/includes/presence_status_icon.html](../backend/accounts/templates/accounts/includes/presence_status_icon.html)
- [backend/accounts/templates/accounts/includes/user_avatar.html](../backend/accounts/templates/accounts/includes/user_avatar.html)
- [backend/accounts/templates/accounts/includes/user_avatar_icon.html](../backend/accounts/templates/accounts/includes/user_avatar_icon.html)
- [backend/accounts/templates/accounts/login.html](../backend/accounts/templates/accounts/login.html)
- [backend/accounts/templates/accounts/profile.html](../backend/accounts/templates/accounts/profile.html)
- [backend/accounts/templates/accounts/register.html](../backend/accounts/templates/accounts/register.html)
- [backend/accounts/templates/accounts/register_workspace.html](../backend/accounts/templates/accounts/register_workspace.html)
- [backend/accounts/templates/accounts/select_workspace.html](../backend/accounts/templates/accounts/select_workspace.html)
- [backend/accounts/templates/accounts/widgets/user_select.html](../backend/accounts/templates/accounts/widgets/user_select.html)

### workplaces

- [backend/workplaces/templates/workplaces/form_page.html](../backend/workplaces/templates/workplaces/form_page.html)
- [backend/workplaces/templates/workplaces/includes/avatar_picker.html](../backend/workplaces/templates/workplaces/includes/avatar_picker.html)
- [backend/workplaces/templates/workplaces/includes/invitation_person.html](../backend/workplaces/templates/workplaces/includes/invitation_person.html)
- [backend/workplaces/templates/workplaces/includes/invite_links.html](../backend/workplaces/templates/workplaces/includes/invite_links.html)
- [backend/workplaces/templates/workplaces/includes/management_toolbar.html](../backend/workplaces/templates/workplaces/includes/management_toolbar.html)
- [backend/workplaces/templates/workplaces/includes/members_table.html](../backend/workplaces/templates/workplaces/includes/members_table.html)
- [backend/workplaces/templates/workplaces/includes/settings_page.html](../backend/workplaces/templates/workplaces/includes/settings_page.html)
- [backend/workplaces/templates/workplaces/includes/sidebar_favorite_toggle.html](../backend/workplaces/templates/workplaces/includes/sidebar_favorite_toggle.html)
- [backend/workplaces/templates/workplaces/includes/sidebar_favorites.html](../backend/workplaces/templates/workplaces/includes/sidebar_favorites.html)
- [backend/workplaces/templates/workplaces/includes/team_modals.html](../backend/workplaces/templates/workplaces/includes/team_modals.html)
- [backend/workplaces/templates/workplaces/includes/team_panel.html](../backend/workplaces/templates/workplaces/includes/team_panel.html)
- [backend/workplaces/templates/workplaces/includes/workplace_photo_editor.html](../backend/workplaces/templates/workplaces/includes/workplace_photo_editor.html)
- [backend/workplaces/templates/workplaces/join.html](../backend/workplaces/templates/workplaces/join.html)
- [backend/workplaces/templates/workplaces/widgets/module_option.html](../backend/workplaces/templates/workplaces/widgets/module_option.html)
- [backend/workplaces/templates/workplaces/widgets/module_select.html](../backend/workplaces/templates/workplaces/widgets/module_select.html)
- [backend/workplaces/templates/workplaces/workplaces.html](../backend/workplaces/templates/workplaces/workplaces.html)

### tasks

- [backend/tasks/templates/tasks/includes/comment_composer.html](../backend/tasks/templates/tasks/includes/comment_composer.html)
- [backend/tasks/templates/tasks/includes/comment_images.html](../backend/tasks/templates/tasks/includes/comment_images.html)
- [backend/tasks/templates/tasks/includes/directory_actions_menu.html](../backend/tasks/templates/tasks/includes/directory_actions_menu.html)
- [backend/tasks/templates/tasks/includes/directory_column_manager.html](../backend/tasks/templates/tasks/includes/directory_column_manager.html)
- [backend/tasks/templates/tasks/includes/directory_filter_aggregate.html](../backend/tasks/templates/tasks/includes/directory_filter_aggregate.html)
- [backend/tasks/templates/tasks/includes/directory_pagination_toolbar.html](../backend/tasks/templates/tasks/includes/directory_pagination_toolbar.html)
- [backend/tasks/templates/tasks/includes/directory_sort_builder.html](../backend/tasks/templates/tasks/includes/directory_sort_builder.html)
- [backend/tasks/templates/tasks/includes/issue_group_header.html](../backend/tasks/templates/tasks/includes/issue_group_header.html)
- [backend/tasks/templates/tasks/includes/project_choice_filter_detail.html](../backend/tasks/templates/tasks/includes/project_choice_filter_detail.html)
- [backend/tasks/templates/tasks/includes/project_info_modal.html](../backend/tasks/templates/tasks/includes/project_info_modal.html)
- [backend/tasks/templates/tasks/includes/project_members_panel.html](../backend/tasks/templates/tasks/includes/project_members_panel.html)
- [backend/tasks/templates/tasks/includes/project_team_modals.html](../backend/tasks/templates/tasks/includes/project_team_modals.html)
- [backend/tasks/templates/tasks/includes/project_text_filter_detail.html](../backend/tasks/templates/tasks/includes/project_text_filter_detail.html)
- [backend/tasks/templates/tasks/includes/status_group_header.html](../backend/tasks/templates/tasks/includes/status_group_header.html)
- [backend/tasks/templates/tasks/includes/tag_directory.html](../backend/tasks/templates/tasks/includes/tag_directory.html)
- [backend/tasks/templates/tasks/includes/tag_filters.html](../backend/tasks/templates/tasks/includes/tag_filters.html)
- [backend/tasks/templates/tasks/includes/tag_modal.html](../backend/tasks/templates/tasks/includes/tag_modal.html)
- [backend/tasks/templates/tasks/includes/tag_notes_modal.html](../backend/tasks/templates/tasks/includes/tag_notes_modal.html)
- [backend/tasks/templates/tasks/includes/tag_notes_thread.html](../backend/tasks/templates/tasks/includes/tag_notes_thread.html)
- [backend/tasks/templates/tasks/includes/tag_sort.html](../backend/tasks/templates/tasks/includes/tag_sort.html)
- [backend/tasks/templates/tasks/includes/task_activity_item.html](../backend/tasks/templates/tasks/includes/task_activity_item.html)
- [backend/tasks/templates/tasks/includes/work_log_fields.html](../backend/tasks/templates/tasks/includes/work_log_fields.html)
- [backend/tasks/templates/tasks/includes/work_log_list.html](../backend/tasks/templates/tasks/includes/work_log_list.html)
- [backend/tasks/templates/tasks/includes/work_log_modal.html](../backend/tasks/templates/tasks/includes/work_log_modal.html)

### dashboard

- [backend/dashboard/templates/dashboard/filters/base.html](../backend/dashboard/templates/dashboard/filters/base.html)
- [backend/dashboard/templates/dashboard/filters/directory.html](../backend/dashboard/templates/dashboard/filters/directory.html)
- [backend/dashboard/templates/dashboard/filters/favorite.html](../backend/dashboard/templates/dashboard/filters/favorite.html)
- [backend/dashboard/templates/dashboard/filters/form.html](../backend/dashboard/templates/dashboard/filters/form.html)
- [backend/dashboard/templates/dashboard/filters/index.html](../backend/dashboard/templates/dashboard/filters/index.html)
- [backend/dashboard/templates/dashboard/filters/results.html](../backend/dashboard/templates/dashboard/filters/results.html)
- [backend/dashboard/templates/dashboard/filters/row_actions.html](../backend/dashboard/templates/dashboard/filters/row_actions.html)
- [backend/dashboard/templates/dashboard/filters/search.html](../backend/dashboard/templates/dashboard/filters/search.html)
- [backend/dashboard/templates/dashboard/filters/search_results.html](../backend/dashboard/templates/dashboard/filters/search_results.html)
- [backend/dashboard/templates/dashboard/filters/search_toolbar.html](../backend/dashboard/templates/dashboard/filters/search_toolbar.html)
- [backend/dashboard/templates/dashboard/filters/sidebar.html](../backend/dashboard/templates/dashboard/filters/sidebar.html)
- [backend/dashboard/templates/dashboard/filters/sidebar_navigation.html](../backend/dashboard/templates/dashboard/filters/sidebar_navigation.html)
- [backend/dashboard/templates/dashboard/filters/sidebar_picker.html](../backend/dashboard/templates/dashboard/filters/sidebar_picker.html)
- [backend/dashboard/templates/dashboard/filters/sidebar_row.html](../backend/dashboard/templates/dashboard/filters/sidebar_row.html)
- [backend/dashboard/templates/dashboard/for_you.html](../backend/dashboard/templates/dashboard/for_you.html)
- [backend/dashboard/templates/dashboard/home.html](../backend/dashboard/templates/dashboard/home.html)
- [backend/dashboard/templates/dashboard/includes/notification_controls.html](../backend/dashboard/templates/dashboard/includes/notification_controls.html)
- [backend/dashboard/templates/dashboard/includes/notification_list.html](../backend/dashboard/templates/dashboard/includes/notification_list.html)
- [backend/dashboard/templates/dashboard/includes/notification_pagination.html](../backend/dashboard/templates/dashboard/includes/notification_pagination.html)
- [backend/dashboard/templates/dashboard/includes/settings_row.html](../backend/dashboard/templates/dashboard/includes/settings_row.html)
- [backend/dashboard/templates/dashboard/includes/settings_spaces_directory.html](../backend/dashboard/templates/dashboard/includes/settings_spaces_directory.html)
- [backend/dashboard/templates/dashboard/includes/work_progress.html](../backend/dashboard/templates/dashboard/includes/work_progress.html)
- [backend/dashboard/templates/dashboard/pulpits/actions.html](../backend/dashboard/templates/dashboard/pulpits/actions.html)
- [backend/dashboard/templates/dashboard/pulpits/base.html](../backend/dashboard/templates/dashboard/pulpits/base.html)
- [backend/dashboard/templates/dashboard/pulpits/canvas.html](../backend/dashboard/templates/dashboard/pulpits/canvas.html)
- [backend/dashboard/templates/dashboard/pulpits/catalog.html](../backend/dashboard/templates/dashboard/pulpits/catalog.html)
- [backend/dashboard/templates/dashboard/pulpits/catalog_preview.html](../backend/dashboard/templates/dashboard/pulpits/catalog_preview.html)
- [backend/dashboard/templates/dashboard/pulpits/detail.html](../backend/dashboard/templates/dashboard/pulpits/detail.html)
- [backend/dashboard/templates/dashboard/pulpits/directory.html](../backend/dashboard/templates/dashboard/pulpits/directory.html)
- [backend/dashboard/templates/dashboard/pulpits/edit.html](../backend/dashboard/templates/dashboard/pulpits/edit.html)
- [backend/dashboard/templates/dashboard/pulpits/fields.html](../backend/dashboard/templates/dashboard/pulpits/fields.html)
- [backend/dashboard/templates/dashboard/pulpits/form.html](../backend/dashboard/templates/dashboard/pulpits/form.html)
- [backend/dashboard/templates/dashboard/pulpits/gadget.html](../backend/dashboard/templates/dashboard/pulpits/gadget.html)
- [backend/dashboard/templates/dashboard/pulpits/gadget_preview.html](../backend/dashboard/templates/dashboard/pulpits/gadget_preview.html)
- [backend/dashboard/templates/dashboard/pulpits/gadgets.html](../backend/dashboard/templates/dashboard/pulpits/gadgets.html)
- [backend/dashboard/templates/dashboard/pulpits/index.html](../backend/dashboard/templates/dashboard/pulpits/index.html)
- [backend/dashboard/templates/dashboard/pulpits/layout_preview.html](../backend/dashboard/templates/dashboard/pulpits/layout_preview.html)
- [backend/dashboard/templates/dashboard/pulpits/row_actions.html](../backend/dashboard/templates/dashboard/pulpits/row_actions.html)
- [backend/dashboard/templates/dashboard/pulpits/search_results.html](../backend/dashboard/templates/dashboard/pulpits/search_results.html)
- [backend/dashboard/templates/dashboard/pulpits/settings_members.html](../backend/dashboard/templates/dashboard/pulpits/settings_members.html)
- [backend/dashboard/templates/dashboard/pulpits/sidebar_navigation.html](../backend/dashboard/templates/dashboard/pulpits/sidebar_navigation.html)
- [backend/dashboard/templates/dashboard/pulpits/sidebar_picker.html](../backend/dashboard/templates/dashboard/pulpits/sidebar_picker.html)
- [backend/dashboard/templates/dashboard/pulpits/sidebar_row.html](../backend/dashboard/templates/dashboard/pulpits/sidebar_row.html)
- [backend/dashboard/templates/dashboard/settings.html](../backend/dashboard/templates/dashboard/settings.html)

### planner

- [backend/planner/templates/planner/index.html](../backend/planner/templates/planner/index.html)

### documents

- [backend/documents/templates/documents/filter_sort.html](../backend/documents/templates/documents/filter_sort.html)
- [backend/documents/templates/documents/form.html](../backend/documents/templates/documents/form.html)
- [backend/documents/templates/documents/includes/color_field.html](../backend/documents/templates/documents/includes/color_field.html)
- [backend/documents/templates/documents/includes/drag_attributes.html](../backend/documents/templates/documents/includes/drag_attributes.html)
- [backend/documents/templates/documents/includes/drive_icon.html](../backend/documents/templates/documents/includes/drive_icon.html)
- [backend/documents/templates/documents/includes/file_icon.html](../backend/documents/templates/documents/includes/file_icon.html)
- [backend/documents/templates/documents/includes/file_icon_shape.html](../backend/documents/templates/documents/includes/file_icon_shape.html)
- [backend/documents/templates/documents/includes/files_empty.html](../backend/documents/templates/documents/includes/files_empty.html)
- [backend/documents/templates/documents/includes/files_grid.html](../backend/documents/templates/documents/includes/files_grid.html)
- [backend/documents/templates/documents/includes/folder_icon.html](../backend/documents/templates/documents/includes/folder_icon.html)
- [backend/documents/templates/documents/includes/libraries_empty.html](../backend/documents/templates/documents/includes/libraries_empty.html)
- [backend/documents/templates/documents/includes/libraries_grid.html](../backend/documents/templates/documents/includes/libraries_grid.html)
- [backend/documents/templates/documents/includes/library_actions.html](../backend/documents/templates/documents/includes/library_actions.html)
- [backend/documents/templates/documents/includes/library_avatar.html](../backend/documents/templates/documents/includes/library_avatar.html)
- [backend/documents/templates/documents/includes/move_action.html](../backend/documents/templates/documents/includes/move_action.html)
- [backend/documents/templates/documents/includes/row_actions.html](../backend/documents/templates/documents/includes/row_actions.html)
- [backend/documents/templates/documents/libraries.html](../backend/documents/templates/documents/libraries.html)
- [backend/documents/templates/documents/library.html](../backend/documents/templates/documents/library.html)
- [backend/documents/templates/documents/modal_host.html](../backend/documents/templates/documents/modal_host.html)
- [backend/documents/templates/documents/office/actions.html](../backend/documents/templates/documents/office/actions.html)
- [backend/documents/templates/documents/office/board_frame.html](../backend/documents/templates/documents/office/board_frame.html)
- [backend/documents/templates/documents/office/create_card.html](../backend/documents/templates/documents/office/create_card.html)
- [backend/documents/templates/documents/office/editor.html](../backend/documents/templates/documents/office/editor.html)
- [backend/documents/templates/documents/office/index.html](../backend/documents/templates/documents/office/index.html)
- [backend/documents/templates/documents/office/name.html](../backend/documents/templates/documents/office/name.html)
- [backend/documents/templates/documents/office/suite.html](../backend/documents/templates/documents/office/suite.html)
- [backend/documents/templates/documents/preview.html](../backend/documents/templates/documents/preview.html)
- [backend/documents/templates/documents/return_filters.html](../backend/documents/templates/documents/return_filters.html)
- [backend/documents/templates/documents/sidebar.html](../backend/documents/templates/documents/sidebar.html)
- [backend/documents/templates/documents/toolbar.html](../backend/documents/templates/documents/toolbar.html)

### resources

- [backend/resources/templates/resources/detail.html](../backend/resources/templates/resources/detail.html)
- [backend/resources/templates/resources/directory.html](../backend/resources/templates/resources/directory.html)
- [backend/resources/templates/resources/form.html](../backend/resources/templates/resources/form.html)
- [backend/resources/templates/resources/index.html](../backend/resources/templates/resources/index.html)
- [backend/resources/templates/resources/react.html](../backend/resources/templates/resources/react.html)

### spaces

- [backend/spaces/templates/spaces/avatar.html](../backend/spaces/templates/spaces/avatar.html)
- [backend/spaces/templates/spaces/avatar_picker.html](../backend/spaces/templates/spaces/avatar_picker.html)
- [backend/spaces/templates/spaces/backlog.html](../backend/spaces/templates/spaces/backlog.html)
- [backend/spaces/templates/spaces/backlog_header_details.html](../backend/spaces/templates/spaces/backlog_header_details.html)
- [backend/spaces/templates/spaces/backlog_move_form.html](../backend/spaces/templates/spaces/backlog_move_form.html)
- [backend/spaces/templates/spaces/base.html](../backend/spaces/templates/spaces/base.html)
- [backend/spaces/templates/spaces/board_order_form.html](../backend/spaces/templates/spaces/board_order_form.html)
- [backend/spaces/templates/spaces/card.html](../backend/spaces/templates/spaces/card.html)
- [backend/spaces/templates/spaces/configuration.html](../backend/spaces/templates/spaces/configuration.html)
- [backend/spaces/templates/spaces/detail.html](../backend/spaces/templates/spaces/detail.html)
- [backend/spaces/templates/spaces/directory.html](../backend/spaces/templates/spaces/directory.html)
- [backend/spaces/templates/spaces/directory_row_actions.html](../backend/spaces/templates/spaces/directory_row_actions.html)
- [backend/spaces/templates/spaces/form.html](../backend/spaces/templates/spaces/form.html)
- [backend/spaces/templates/spaces/form_page.html](../backend/spaces/templates/spaces/form_page.html)
- [backend/spaces/templates/spaces/index.html](../backend/spaces/templates/spaces/index.html)
- [backend/spaces/templates/spaces/issue_type.html](../backend/spaces/templates/spaces/issue_type.html)
- [backend/spaces/templates/spaces/item_list.html](../backend/spaces/templates/spaces/item_list.html)
- [backend/spaces/templates/spaces/item_planning.html](../backend/spaces/templates/spaces/item_planning.html)
- [backend/spaces/templates/spaces/item_snapshot.html](../backend/spaces/templates/spaces/item_snapshot.html)
- [backend/spaces/templates/spaces/item_toolbar.html](../backend/spaces/templates/spaces/item_toolbar.html)
- [backend/spaces/templates/spaces/load_more.html](../backend/spaces/templates/spaces/load_more.html)
- [backend/spaces/templates/spaces/pagination.html](../backend/spaces/templates/spaces/pagination.html)
- [backend/spaces/templates/spaces/reports.html](../backend/spaces/templates/spaces/reports.html)
- [backend/spaces/templates/spaces/row.html](../backend/spaces/templates/spaces/row.html)
- [backend/spaces/templates/spaces/search_results.html](../backend/spaces/templates/spaces/search_results.html)
- [backend/spaces/templates/spaces/settings_form.html](../backend/spaces/templates/spaces/settings_form.html)
- [backend/spaces/templates/spaces/settings_members.html](../backend/spaces/templates/spaces/settings_members.html)
- [backend/spaces/templates/spaces/sidebar_navigation.html](../backend/spaces/templates/spaces/sidebar_navigation.html)
- [backend/spaces/templates/spaces/sidebar_picker.html](../backend/spaces/templates/spaces/sidebar_picker.html)
- [backend/spaces/templates/spaces/sidebar_row.html](../backend/spaces/templates/spaces/sidebar_row.html)
- [backend/spaces/templates/spaces/sprint_card.html](../backend/spaces/templates/spaces/sprint_card.html)
- [backend/spaces/templates/spaces/sprint_header_details.html](../backend/spaces/templates/spaces/sprint_header_details.html)
- [backend/spaces/templates/spaces/subtask_modal.html](../backend/spaces/templates/spaces/subtask_modal.html)
- [backend/spaces/templates/spaces/summary.html](../backend/spaces/templates/spaces/summary.html)
- [backend/spaces/templates/spaces/summary_widget.html](../backend/spaces/templates/spaces/summary_widget.html)
- [backend/spaces/templates/spaces/tags.html](../backend/spaces/templates/spaces/tags.html)
- [backend/spaces/templates/spaces/task_attachments.html](../backend/spaces/templates/spaces/task_attachments.html)
- [backend/spaces/templates/spaces/task_comment.html](../backend/spaces/templates/spaces/task_comment.html)
- [backend/spaces/templates/spaces/task_detail.html](../backend/spaces/templates/spaces/task_detail.html)
- [backend/spaces/templates/spaces/task_list.html](../backend/spaces/templates/spaces/task_list.html)
- [backend/spaces/templates/spaces/task_sidebar.html](../backend/spaces/templates/spaces/task_sidebar.html)
- [backend/spaces/templates/spaces/team.html](../backend/spaces/templates/spaces/team.html)
- [backend/spaces/templates/spaces/team_avatar.html](../backend/spaces/templates/spaces/team_avatar.html)
- [backend/spaces/templates/spaces/teams.html](../backend/spaces/templates/spaces/teams.html)
- [backend/spaces/templates/spaces/template_picker.html](../backend/spaces/templates/spaces/template_picker.html)
- [backend/spaces/templates/spaces/timeline.html](../backend/spaces/templates/spaces/timeline.html)
- [backend/spaces/templates/spaces/type_option.html](../backend/spaces/templates/spaces/type_option.html)

## 7. Zasoby frontendowe

### css

- [static/css/base/fonts.css](../static/css/base/fonts.css)
- [static/css/base/reset.css](../static/css/base/reset.css)
- [static/css/base/variables.css](../static/css/base/variables.css)
- [static/css/calendar.css](../static/css/calendar.css)
- [static/css/components/alerts.css](../static/css/components/alerts.css)
- [static/css/components/app-toolbar.css](../static/css/components/app-toolbar.css)
- [static/css/components/attachments.css](../static/css/components/attachments.css)
- [static/css/components/auth.css](../static/css/components/auth.css)
- [static/css/components/buttons.css](../static/css/components/buttons.css)
- [static/css/components/cards.css](../static/css/components/cards.css)
- [static/css/components/checkboxes.css](../static/css/components/checkboxes.css)
- [static/css/components/dashboard.css](../static/css/components/dashboard.css)
- [static/css/components/data-table.css](../static/css/components/data-table.css)
- [static/css/components/dialogs.css](../static/css/components/dialogs.css)
- [static/css/components/documents.css](../static/css/components/documents.css)
- [static/css/components/dropdown-layer.css](../static/css/components/dropdown-layer.css)
- [static/css/components/emoji-picker.css](../static/css/components/emoji-picker.css)
- [static/css/components/file-upload.css](../static/css/components/file-upload.css)
- [static/css/components/forms.css](../static/css/components/forms.css)
- [static/css/components/global-search.css](../static/css/components/global-search.css)
- [static/css/components/load-more.css](../static/css/components/load-more.css)
- [static/css/components/modal-system.css](../static/css/components/modal-system.css)
- [static/css/components/modals.css](../static/css/components/modals.css)
- [static/css/components/notifications-panel.css](../static/css/components/notifications-panel.css)
- [static/css/components/notifications.css](../static/css/components/notifications.css)
- [static/css/components/office.css](../static/css/components/office.css)
- [static/css/components/page-header.css](../static/css/components/page-header.css)
- [static/css/components/profile.css](../static/css/components/profile.css)
- [static/css/components/pulpits.css](../static/css/components/pulpits.css)
- [static/css/components/react.css](../static/css/components/react.css)
- [static/css/components/resources.css](../static/css/components/resources.css)
- [static/css/components/settings.css](../static/css/components/settings.css)
- [static/css/components/shared-controls.css](../static/css/components/shared-controls.css)
- [static/css/components/space-avatars.css](../static/css/components/space-avatars.css)
- [static/css/components/spaces.css](../static/css/components/spaces.css)
- [static/css/components/sticky-note.css](../static/css/components/sticky-note.css)
- [static/css/components/tables.css](../static/css/components/tables.css)
- [static/css/components/task-edit.css](../static/css/components/task-edit.css)
- [static/css/components/task-filters.css](../static/css/components/task-filters.css)
- [static/css/components/tasks.css](../static/css/components/tasks.css)
- [static/css/components/toolbar.css](../static/css/components/toolbar.css)
- [static/css/components/workplace-team.css](../static/css/components/workplace-team.css)
- [static/css/components/workplaces.css](../static/css/components/workplaces.css)
- [static/css/layout/main.css](../static/css/layout/main.css)
- [static/css/layout/panels.css](../static/css/layout/panels.css)
- [static/css/layout/responsive.css](../static/css/layout/responsive.css)
- [static/css/layout/sidebar.css](../static/css/layout/sidebar.css)
- [static/css/style.css](../static/css/style.css)
- [static/css/theme/elestio.css](../static/css/theme/elestio.css)

### js

- [static/js/attachment-icons.js](../static/js/attachment-icons.js)
- [static/js/auth.js](../static/js/auth.js)
- [static/js/calendar.js](../static/js/calendar.js)
- [static/js/collaboration.js](../static/js/collaboration.js)
- [static/js/comment-images.js](../static/js/comment-images.js)
- [static/js/custom-select.js](../static/js/custom-select.js)
- [static/js/documents.js](../static/js/documents.js)
- [static/js/dropdown-layer.js](../static/js/dropdown-layer.js)
- [static/js/field-help.js](../static/js/field-help.js)
- [static/js/file-upload.js](../static/js/file-upload.js)
- [static/js/filter-navigation.js](../static/js/filter-navigation.js)
- [static/js/flaticon-icons.js](../static/js/flaticon-icons.js)
- [static/js/for-you.js](../static/js/for-you.js)
- [static/js/global-search.js](../static/js/global-search.js)
- [static/js/layout.js](../static/js/layout.js)
- [static/js/modal.js](../static/js/modal.js)
- [static/js/notifications-panel.js](../static/js/notifications-panel.js)
- [static/js/notifications.js](../static/js/notifications.js)
- [static/js/office-suite.js](../static/js/office-suite.js)
- [static/js/office.js](../static/js/office.js)
- [static/js/presence.js](../static/js/presence.js)
- [static/js/profile.js](../static/js/profile.js)
- [static/js/project-team.js](../static/js/project-team.js)
- [static/js/pulpit-navigation.js](../static/js/pulpit-navigation.js)
- [static/js/pulpits.js](../static/js/pulpits.js)
- [static/js/resources.js](../static/js/resources.js)
- [static/js/row-actions.js](../static/js/row-actions.js)
- [static/js/settings.js](../static/js/settings.js)
- [static/js/space-navigation.js](../static/js/space-navigation.js)
- [static/js/space-picker.js](../static/js/space-picker.js)
- [static/js/spaces.js](../static/js/spaces.js)
- [static/js/sticky-note.js](../static/js/sticky-note.js)
- [static/js/task-filters.js](../static/js/task-filters.js)
- [static/js/task-modals.js](../static/js/task-modals.js)
- [static/js/task-work-log.js](../static/js/task-work-log.js)
- [static/js/tasks.js](../static/js/tasks.js)
- [static/js/workplace-avatars.js](../static/js/workplace-avatars.js)
- [static/js/workplace-team.js](../static/js/workplace-team.js)

### img

- [static/img/auth/README.md](../static/img/auth/README.md)
- [static/img/auth/wallpaper-fluent-bloom-light-4k.webp](../static/img/auth/wallpaper-fluent-bloom-light-4k.webp)
- [static/img/auth/wallpaper-red-black-white.png](../static/img/auth/wallpaper-red-black-white.png)
- [static/img/auth/wallpaper-violet-dunes-4k.webp](../static/img/auth/wallpaper-violet-dunes-4k.webp)
- [static/img/auth/wallpaper-violet-dunes-light-4k.webp](../static/img/auth/wallpaper-violet-dunes-light-4k.webp)
- [static/img/empty-states/README.md](../static/img/empty-states/README.md)
- [static/img/empty-states/dashboard-empty.webp](../static/img/empty-states/dashboard-empty.webp)
- [static/img/empty-states/filters-empty.webp](../static/img/empty-states/filters-empty.webp)
- [static/img/empty-states/for-you-assigned-empty.webp](../static/img/empty-states/for-you-assigned-empty.webp)
- [static/img/empty-states/for-you-starred-empty.webp](../static/img/empty-states/for-you-starred-empty.webp)
- [static/img/empty-states/for-you-tasks-empty.webp](../static/img/empty-states/for-you-tasks-empty.webp)
- [static/img/empty-states/for-you-viewed-empty.webp](../static/img/empty-states/for-you-viewed-empty.webp)
- [static/img/empty-states/for-you-worked-empty.webp](../static/img/empty-states/for-you-worked-empty.webp)
- [static/img/empty-states/gadget-column-empty.webp](../static/img/empty-states/gadget-column-empty.webp)
- [static/img/empty-states/spaces-empty.webp](../static/img/empty-states/spaces-empty.webp)
- [static/img/favicon-ancore-large.png](../static/img/favicon-ancore-large.png)
- [static/img/logo-ancore.png](../static/img/logo-ancore.png)
- [static/img/logo.png](../static/img/logo.png)
- [static/img/space-avatars/PROMPT-extra.txt](../static/img/space-avatars/PROMPT-extra.txt)
- [static/img/space-avatars/PROMPT.txt](../static/img/space-avatars/PROMPT.txt)
- [static/img/space-avatars/illustrations-extra-v1.png](../static/img/space-avatars/illustrations-extra-v1.png)
- [static/img/space-avatars/illustrations-v1.png](../static/img/space-avatars/illustrations-v1.png)
- [static/img/space-templates/kanban.svg](../static/img/space-templates/kanban.svg)
- [static/img/space-templates/marketing.svg](../static/img/space-templates/marketing.svg)
- [static/img/space-templates/recruitment.svg](../static/img/space-templates/recruitment.svg)
- [static/img/space-templates/scrum.svg](../static/img/space-templates/scrum.svg)
- [static/img/space-templates/service.svg](../static/img/space-templates/service.svg)
- [static/img/space-templates/tasks.svg](../static/img/space-templates/tasks.svg)
- [static/img/user-avatars/PROMPT-extra.txt](../static/img/user-avatars/PROMPT-extra.txt)
- [static/img/user-avatars/PROMPT.txt](../static/img/user-avatars/PROMPT.txt)
- [static/img/user-avatars/illustrations-extra-v1.png](../static/img/user-avatars/illustrations-extra-v1.png)
- [static/img/user-avatars/illustrations-v1.png](../static/img/user-avatars/illustrations-v1.png)

### React — frontend/app

- [frontend/app/.prettierrc.json](../frontend/app/.prettierrc.json)
- [frontend/app/build.mjs](../frontend/app/build.mjs)
- [frontend/app/package.json](../frontend/app/package.json)
- [frontend/app/pnpm-lock.yaml](../frontend/app/pnpm-lock.yaml)
- [frontend/app/pnpm-workspace.yaml](../frontend/app/pnpm-workspace.yaml)
- [frontend/app/src/PageApp.tsx](../frontend/app/src/PageApp.tsx)
- [frontend/app/src/accounts/AuthPage.tsx](../frontend/app/src/accounts/AuthPage.tsx)
- [frontend/app/src/accounts/BannerCropper.tsx](../frontend/app/src/accounts/BannerCropper.tsx)
- [frontend/app/src/accounts/BannerEditor.tsx](../frontend/app/src/accounts/BannerEditor.tsx)
- [frontend/app/src/accounts/PresenceSelect.tsx](../frontend/app/src/accounts/PresenceSelect.tsx)
- [frontend/app/src/accounts/ProfileEditor.tsx](../frontend/app/src/accounts/ProfileEditor.tsx)
- [frontend/app/src/accounts/ProfilePage.tsx](../frontend/app/src/accounts/ProfilePage.tsx)
- [frontend/app/src/accounts/WorkspacePickerPage.tsx](../frontend/app/src/accounts/WorkspacePickerPage.tsx)
- [frontend/app/src/accounts/banner-crop.ts](../frontend/app/src/accounts/banner-crop.ts)
- [frontend/app/src/accounts/types.ts](../frontend/app/src/accounts/types.ts)
- [frontend/app/src/calendar/CalendarPage.tsx](../frontend/app/src/calendar/CalendarPage.tsx)
- [frontend/app/src/calendar/EventEditor.tsx](../frontend/app/src/calendar/EventEditor.tsx)
- [frontend/app/src/calendar/colors.ts](../frontend/app/src/calendar/colors.ts)
- [frontend/app/src/calendar/dates.ts](../frontend/app/src/calendar/dates.ts)
- [frontend/app/src/dashboard/ForYouPage.tsx](../frontend/app/src/dashboard/ForYouPage.tsx)
- [frontend/app/src/dashboard/SettingsPage.tsx](../frontend/app/src/dashboard/SettingsPage.tsx)
- [frontend/app/src/dashboard/SpacesSettingsDirectory.tsx](../frontend/app/src/dashboard/SpacesSettingsDirectory.tsx)
- [frontend/app/src/documents/DirectoryPage.tsx](../frontend/app/src/documents/DirectoryPage.tsx)
- [frontend/app/src/documents/DocumentDialog.tsx](../frontend/app/src/documents/DocumentDialog.tsx)
- [frontend/app/src/documents/Filters.tsx](../frontend/app/src/documents/Filters.tsx)
- [frontend/app/src/documents/Icons.tsx](../frontend/app/src/documents/Icons.tsx)
- [frontend/app/src/documents/Rows.tsx](../frontend/app/src/documents/Rows.tsx)
- [frontend/app/src/documents/Sidebar.tsx](../frontend/app/src/documents/Sidebar.tsx)
- [frontend/app/src/documents/SuitePage.tsx](../frontend/app/src/documents/SuitePage.tsx)
- [frontend/app/src/documents/TextPage.tsx](../frontend/app/src/documents/TextPage.tsx)
- [frontend/app/src/documents/requests.ts](../frontend/app/src/documents/requests.ts)
- [frontend/app/src/documents/richText.ts](../frontend/app/src/documents/richText.ts)
- [frontend/app/src/documents/types.ts](../frontend/app/src/documents/types.ts)
- [frontend/app/src/documents/useActions.ts](../frontend/app/src/documents/useActions.ts)
- [frontend/app/src/documents/useDrag.tsx](../frontend/app/src/documents/useDrag.tsx)
- [frontend/app/src/documents/useOffice.ts](../frontend/app/src/documents/useOffice.ts)
- [frontend/app/src/filters/DirectoryPage.tsx](../frontend/app/src/filters/DirectoryPage.tsx)
- [frontend/app/src/filters/SearchPage.tsx](../frontend/app/src/filters/SearchPage.tsx)
- [frontend/app/src/filters/SearchToolbar.tsx](../frontend/app/src/filters/SearchToolbar.tsx)
- [frontend/app/src/filters/SettingsDialog.tsx](../frontend/app/src/filters/SettingsDialog.tsx)
- [frontend/app/src/filters/types.ts](../frontend/app/src/filters/types.ts)
- [frontend/app/src/forms/FormDialog.tsx](../frontend/app/src/forms/FormDialog.tsx)
- [frontend/app/src/main.tsx](../frontend/app/src/main.tsx)
- [frontend/app/src/pulpits/AccessEditor.tsx](../frontend/app/src/pulpits/AccessEditor.tsx)
- [frontend/app/src/pulpits/Actions.tsx](../frontend/app/src/pulpits/Actions.tsx)
- [frontend/app/src/pulpits/Catalog.tsx](../frontend/app/src/pulpits/Catalog.tsx)
- [frontend/app/src/pulpits/DetailPage.tsx](../frontend/app/src/pulpits/DetailPage.tsx)
- [frontend/app/src/pulpits/DirectoryPage.tsx](../frontend/app/src/pulpits/DirectoryPage.tsx)
- [frontend/app/src/pulpits/EditPage.tsx](../frontend/app/src/pulpits/EditPage.tsx)
- [frontend/app/src/pulpits/Gadget.tsx](../frontend/app/src/pulpits/Gadget.tsx)
- [frontend/app/src/pulpits/SettingsPage.tsx](../frontend/app/src/pulpits/SettingsPage.tsx)
- [frontend/app/src/pulpits/autoRefresh.ts](../frontend/app/src/pulpits/autoRefresh.ts)
- [frontend/app/src/pulpits/types.ts](../frontend/app/src/pulpits/types.ts)
- [frontend/app/src/resources/App.tsx](../frontend/app/src/resources/App.tsx)
- [frontend/app/src/resources/Detail.tsx](../frontend/app/src/resources/Detail.tsx)
- [frontend/app/src/resources/Editor.tsx](../frontend/app/src/resources/Editor.tsx)
- [frontend/app/src/resources/Operation.tsx](../frontend/app/src/resources/Operation.tsx)
- [frontend/app/src/resources/Table.tsx](../frontend/app/src/resources/Table.tsx)
- [frontend/app/src/resources/columns.tsx](../frontend/app/src/resources/columns.tsx)
- [frontend/app/src/resources/types.ts](../frontend/app/src/resources/types.ts)
- [frontend/app/src/shared/AccessEditor.tsx](../frontend/app/src/shared/AccessEditor.tsx)
- [frontend/app/src/shared/Avatar.tsx](../frontend/app/src/shared/Avatar.tsx)
- [frontend/app/src/shared/AvatarControl.tsx](../frontend/app/src/shared/AvatarControl.tsx)
- [frontend/app/src/shared/ColorControl.tsx](../frontend/app/src/shared/ColorControl.tsx)
- [frontend/app/src/shared/DashboardCanvas.tsx](../frontend/app/src/shared/DashboardCanvas.tsx)
- [frontend/app/src/shared/DirectoryColumns.tsx](../frontend/app/src/shared/DirectoryColumns.tsx)
- [frontend/app/src/shared/DirectoryToolbar.tsx](../frontend/app/src/shared/DirectoryToolbar.tsx)
- [frontend/app/src/shared/Dropdown.tsx](../frontend/app/src/shared/Dropdown.tsx)
- [frontend/app/src/shared/Emoji.tsx](../frontend/app/src/shared/Emoji.tsx)
- [frontend/app/src/shared/EmojiPicker.tsx](../frontend/app/src/shared/EmojiPicker.tsx)
- [frontend/app/src/shared/EmptyState.tsx](../frontend/app/src/shared/EmptyState.tsx)
- [frontend/app/src/shared/FieldLabel.tsx](../frontend/app/src/shared/FieldLabel.tsx)
- [frontend/app/src/shared/Icon.tsx](../frontend/app/src/shared/Icon.tsx)
- [frontend/app/src/shared/LoadMore.tsx](../frontend/app/src/shared/LoadMore.tsx)
- [frontend/app/src/shared/LocalDirectoryTable.tsx](../frontend/app/src/shared/LocalDirectoryTable.tsx)
- [frontend/app/src/shared/MemberDirectory.tsx](../frontend/app/src/shared/MemberDirectory.tsx)
- [frontend/app/src/shared/Members.tsx](../frontend/app/src/shared/Members.tsx)
- [frontend/app/src/shared/Modal.tsx](../frontend/app/src/shared/Modal.tsx)
- [frontend/app/src/shared/PageHeader.tsx](../frontend/app/src/shared/PageHeader.tsx)
- [frontend/app/src/shared/PageTabs.tsx](../frontend/app/src/shared/PageTabs.tsx)
- [frontend/app/src/shared/Pagination.tsx](../frontend/app/src/shared/Pagination.tsx)
- [frontend/app/src/shared/RightSidebarContent.tsx](../frontend/app/src/shared/RightSidebarContent.tsx)
- [frontend/app/src/shared/Select.tsx](../frontend/app/src/shared/Select.tsx)
- [frontend/app/src/shared/SharingDialog.tsx](../frontend/app/src/shared/SharingDialog.tsx)
- [frontend/app/src/shared/StatusGroup.tsx](../frontend/app/src/shared/StatusGroup.tsx)
- [frontend/app/src/shared/WidgetCatalog.tsx](../frontend/app/src/shared/WidgetCatalog.tsx)
- [frontend/app/src/shared/api.ts](../frontend/app/src/shared/api.ts)
- [frontend/app/src/shared/clipboard.ts](../frontend/app/src/shared/clipboard.ts)
- [frontend/app/src/shared/globals.d.ts](../frontend/app/src/shared/globals.d.ts)
- [frontend/app/src/shared/inert.ts](../frontend/app/src/shared/inert.ts)
- [frontend/app/src/shared/issue-type-color.ts](../frontend/app/src/shared/issue-type-color.ts)
- [frontend/app/src/shared/page.ts](../frontend/app/src/shared/page.ts)
- [frontend/app/src/shared/status-color.ts](../frontend/app/src/shared/status-color.ts)
- [frontend/app/src/shared/table.tsx](../frontend/app/src/shared/table.tsx)
- [frontend/app/src/shared/useDirtyGuard.ts](../frontend/app/src/shared/useDirtyGuard.ts)
- [frontend/app/src/shared/useLoadMorePage.ts](../frontend/app/src/shared/useLoadMorePage.ts)
- [frontend/app/src/shared/usePageActions.ts](../frontend/app/src/shared/usePageActions.ts)
- [frontend/app/src/shell/CollectionPicker.tsx](../frontend/app/src/shell/CollectionPicker.tsx)
- [frontend/app/src/shell/Collections.tsx](../frontend/app/src/shell/Collections.tsx)
- [frontend/app/src/shell/GlobalPanels.tsx](../frontend/app/src/shell/GlobalPanels.tsx)
- [frontend/app/src/shell/NotificationPanel.tsx](../frontend/app/src/shell/NotificationPanel.tsx)
- [frontend/app/src/shell/Search.tsx](../frontend/app/src/shell/Search.tsx)
- [frontend/app/src/shell/Shell.tsx](../frontend/app/src/shell/Shell.tsx)
- [frontend/app/src/shell/Sidebar.tsx](../frontend/app/src/shell/Sidebar.tsx)
- [frontend/app/src/shell/States.tsx](../frontend/app/src/shell/States.tsx)
- [frontend/app/src/shell/Sticker.tsx](../frontend/app/src/shell/Sticker.tsx)
- [frontend/app/src/shell/Toasts.tsx](../frontend/app/src/shell/Toasts.tsx)
- [frontend/app/src/shell/TodaySidebar.tsx](../frontend/app/src/shell/TodaySidebar.tsx)
- [frontend/app/src/shell/WorkspaceMenu.tsx](../frontend/app/src/shell/WorkspaceMenu.tsx)
- [frontend/app/src/shell/WorkspaceSelect.tsx](../frontend/app/src/shell/WorkspaceSelect.tsx)
- [frontend/app/src/shell/navigation-types.ts](../frontend/app/src/shell/navigation-types.ts)
- [frontend/app/src/shell/navigation.ts](../frontend/app/src/shell/navigation.ts)
- [frontend/app/src/shell/sidebarSizing.ts](../frontend/app/src/shell/sidebarSizing.ts)
- [frontend/app/src/shell/storage.ts](../frontend/app/src/shell/storage.ts)
- [frontend/app/src/shell/types.ts](../frontend/app/src/shell/types.ts)
- [frontend/app/src/shell/useFavorites.tsx](../frontend/app/src/shell/useFavorites.tsx)
- [frontend/app/src/shell/useShellLayout.ts](../frontend/app/src/shell/useShellLayout.ts)
- [frontend/app/src/spaces/BlockDialog.tsx](../frontend/app/src/spaces/BlockDialog.tsx)
- [frontend/app/src/spaces/ConfigurationColor.tsx](../frontend/app/src/spaces/ConfigurationColor.tsx)
- [frontend/app/src/spaces/ConfigurationIcon.tsx](../frontend/app/src/spaces/ConfigurationIcon.tsx)
- [frontend/app/src/spaces/ConfigurationPage.tsx](../frontend/app/src/spaces/ConfigurationPage.tsx)
- [frontend/app/src/spaces/ConfigurationTable.tsx](../frontend/app/src/spaces/ConfigurationTable.tsx)
- [frontend/app/src/spaces/DetailPage.tsx](../frontend/app/src/spaces/DetailPage.tsx)
- [frontend/app/src/spaces/DirectoryPage.tsx](../frontend/app/src/spaces/DirectoryPage.tsx)
- [frontend/app/src/spaces/Item.tsx](../frontend/app/src/spaces/Item.tsx)
- [frontend/app/src/spaces/ItemToolbar.tsx](../frontend/app/src/spaces/ItemToolbar.tsx)
- [frontend/app/src/spaces/ReportsView.tsx](../frontend/app/src/spaces/ReportsView.tsx)
- [frontend/app/src/spaces/SettingsPage.tsx](../frontend/app/src/spaces/SettingsPage.tsx)
- [frontend/app/src/spaces/SpaceHeader.tsx](../frontend/app/src/spaces/SpaceHeader.tsx)
- [frontend/app/src/spaces/Summary.tsx](../frontend/app/src/spaces/Summary.tsx)
- [frontend/app/src/spaces/SummaryDashboard.tsx](../frontend/app/src/spaces/SummaryDashboard.tsx)
- [frontend/app/src/spaces/SummaryDistribution.tsx](../frontend/app/src/spaces/SummaryDistribution.tsx)
- [frontend/app/src/spaces/TeamsPage.tsx](../frontend/app/src/spaces/TeamsPage.tsx)
- [frontend/app/src/spaces/TimelineView.tsx](../frontend/app/src/spaces/TimelineView.tsx)
- [frontend/app/src/spaces/TypeFields.tsx](../frontend/app/src/spaces/TypeFields.tsx)
- [frontend/app/src/spaces/ViewToolbar.tsx](../frontend/app/src/spaces/ViewToolbar.tsx)
- [frontend/app/src/spaces/WorkflowBoard.tsx](../frontend/app/src/spaces/WorkflowBoard.tsx)
- [frontend/app/src/spaces/WorkflowMinimap.tsx](../frontend/app/src/spaces/WorkflowMinimap.tsx)
- [frontend/app/src/spaces/WorkflowStageFields.tsx](../frontend/app/src/spaces/WorkflowStageFields.tsx)
- [frontend/app/src/spaces/configuration-appearance.ts](../frontend/app/src/spaces/configuration-appearance.ts)
- [frontend/app/src/spaces/configuration-form.ts](../frontend/app/src/spaces/configuration-form.ts)
- [frontend/app/src/spaces/kanban.ts](../frontend/app/src/spaces/kanban.ts)
- [frontend/app/src/spaces/summaryLayout.ts](../frontend/app/src/spaces/summaryLayout.ts)
- [frontend/app/src/spaces/timeline.ts](../frontend/app/src/spaces/timeline.ts)
- [frontend/app/src/spaces/types.ts](../frontend/app/src/spaces/types.ts)
- [frontend/app/src/spaces/useItemMotion.ts](../frontend/app/src/spaces/useItemMotion.ts)
- [frontend/app/src/spaces/useSummaryMotion.ts](../frontend/app/src/spaces/useSummaryMotion.ts)
- [frontend/app/src/spaces/useWorkflowCamera.ts](../frontend/app/src/spaces/useWorkflowCamera.ts)
- [frontend/app/src/spaces/workflow-board.ts](../frontend/app/src/spaces/workflow-board.ts)
- [frontend/app/src/spaces/workflow-minimap.ts](../frontend/app/src/spaces/workflow-minimap.ts)
- [frontend/app/src/spaces/workflow-viewport.ts](../frontend/app/src/spaces/workflow-viewport.ts)
- [frontend/app/src/tags/NotesDialog.tsx](../frontend/app/src/tags/NotesDialog.tsx)
- [frontend/app/src/tags/TagsPage.tsx](../frontend/app/src/tags/TagsPage.tsx)
- [frontend/app/src/tags/types.ts](../frontend/app/src/tags/types.ts)
- [frontend/app/src/tasks/Activity.tsx](../frontend/app/src/tasks/Activity.tsx)
- [frontend/app/src/tasks/CommentComposer.tsx](../frontend/app/src/tasks/CommentComposer.tsx)
- [frontend/app/src/tasks/Description.tsx](../frontend/app/src/tasks/Description.tsx)
- [frontend/app/src/tasks/SchemaDialog.tsx](../frontend/app/src/tasks/SchemaDialog.tsx)
- [frontend/app/src/tasks/TaskPage.tsx](../frontend/app/src/tasks/TaskPage.tsx)
- [frontend/app/src/tasks/TaskWorkflow.tsx](../frontend/app/src/tasks/TaskWorkflow.tsx)
- [frontend/app/src/tasks/types.ts](../frontend/app/src/tasks/types.ts)
- [frontend/app/src/tasks/useTaskSave.ts](../frontend/app/src/tasks/useTaskSave.ts)
- [frontend/app/src/workspaces/AvatarControl.tsx](../frontend/app/src/workspaces/AvatarControl.tsx)
- [frontend/app/src/workspaces/DirectoryPage.tsx](../frontend/app/src/workspaces/DirectoryPage.tsx)
- [frontend/app/src/workspaces/JoinPage.tsx](../frontend/app/src/workspaces/JoinPage.tsx)
- [frontend/app/src/workspaces/Picker.tsx](../frontend/app/src/workspaces/Picker.tsx)
- [frontend/app/src/workspaces/SettingsPage.tsx](../frontend/app/src/workspaces/SettingsPage.tsx)
- [frontend/app/src/workspaces/TeamTable.tsx](../frontend/app/src/workspaces/TeamTable.tsx)
- [frontend/app/src/workspaces/WorkspaceForm.tsx](../frontend/app/src/workspaces/WorkspaceForm.tsx)
- [frontend/app/src/workspaces/types.ts](../frontend/app/src/workspaces/types.ts)
- [frontend/app/tests/banner-crop.test.mjs](../frontend/app/tests/banner-crop.test.mjs)
- [frontend/app/tests/board-read-only.test.mjs](../frontend/app/tests/board-read-only.test.mjs)
- [frontend/app/tests/calendar-colors.test.mjs](../frontend/app/tests/calendar-colors.test.mjs)
- [frontend/app/tests/calendar-dates.test.mjs](../frontend/app/tests/calendar-dates.test.mjs)
- [frontend/app/tests/calendar-save.test.mjs](../frontend/app/tests/calendar-save.test.mjs)
- [frontend/app/tests/calendar-sidebar.test.mjs](../frontend/app/tests/calendar-sidebar.test.mjs)
- [frontend/app/tests/confirmation.test.mjs](../frontend/app/tests/confirmation.test.mjs)
- [frontend/app/tests/dashboard-canvas.test.mjs](../frontend/app/tests/dashboard-canvas.test.mjs)
- [frontend/app/tests/directory-load-more.test.mjs](../frontend/app/tests/directory-load-more.test.mjs)
- [frontend/app/tests/document-dialog-focus.test.mjs](../frontend/app/tests/document-dialog-focus.test.mjs)
- [frontend/app/tests/documents-landing.test.mjs](../frontend/app/tests/documents-landing.test.mjs)
- [frontend/app/tests/documents-sidebar.test.mjs](../frontend/app/tests/documents-sidebar.test.mjs)
- [frontend/app/tests/dropdown-keyboard.test.mjs](../frontend/app/tests/dropdown-keyboard.test.mjs)
- [frontend/app/tests/dropdown-layer.test.mjs](../frontend/app/tests/dropdown-layer.test.mjs)
- [frontend/app/tests/field-control.test.mjs](../frontend/app/tests/field-control.test.mjs)
- [frontend/app/tests/filter-load-more-draft.test.mjs](../frontend/app/tests/filter-load-more-draft.test.mjs)
- [frontend/app/tests/form-error-focus.test.mjs](../frontend/app/tests/form-error-focus.test.mjs)
- [frontend/app/tests/form-layout.test.mjs](../frontend/app/tests/form-layout.test.mjs)
- [frontend/app/tests/full-page-lifecycle.test.mjs](../frontend/app/tests/full-page-lifecycle.test.mjs)
- [frontend/app/tests/global-search.test.mjs](../frontend/app/tests/global-search.test.mjs)
- [frontend/app/tests/inert.test.mjs](../frontend/app/tests/inert.test.mjs)
- [frontend/app/tests/item-filtering.test.mjs](../frontend/app/tests/item-filtering.test.mjs)
- [frontend/app/tests/kanban-flow.test.mjs](../frontend/app/tests/kanban-flow.test.mjs)
- [frontend/app/tests/load-more-page.test.mjs](../frontend/app/tests/load-more-page.test.mjs)
- [frontend/app/tests/member-toolbar.test.mjs](../frontend/app/tests/member-toolbar.test.mjs)
- [frontend/app/tests/modal-lifecycle.test.mjs](../frontend/app/tests/modal-lifecycle.test.mjs)
- [frontend/app/tests/module-accessibility.test.mjs](../frontend/app/tests/module-accessibility.test.mjs)
- [frontend/app/tests/navigation.test.mjs](../frontend/app/tests/navigation.test.mjs)
- [frontend/app/tests/office-save.test.mjs](../frontend/app/tests/office-save.test.mjs)
- [frontend/app/tests/pulpit-access-draft.test.mjs](../frontend/app/tests/pulpit-access-draft.test.mjs)
- [frontend/app/tests/pulpit-grid-editor.test.mjs](../frontend/app/tests/pulpit-grid-editor.test.mjs)
- [frontend/app/tests/pulpit-refresh.test.mjs](../frontend/app/tests/pulpit-refresh.test.mjs)
- [frontend/app/tests/reports-interactions.test.mjs](../frontend/app/tests/reports-interactions.test.mjs)
- [frontend/app/tests/sidebar-sizing.test.mjs](../frontend/app/tests/sidebar-sizing.test.mjs)
- [frontend/app/tests/space-board-create.test.mjs](../frontend/app/tests/space-board-create.test.mjs)
- [frontend/app/tests/space-list-loading.test.mjs](../frontend/app/tests/space-list-loading.test.mjs)
- [frontend/app/tests/space-settings-configuration.test.mjs](../frontend/app/tests/space-settings-configuration.test.mjs)
- [frontend/app/tests/suite-read-only.test.mjs](../frontend/app/tests/suite-read-only.test.mjs)
- [frontend/app/tests/summary-distribution.test.mjs](../frontend/app/tests/summary-distribution.test.mjs)
- [frontend/app/tests/summary-interactions.test.mjs](../frontend/app/tests/summary-interactions.test.mjs)
- [frontend/app/tests/summary-layout.test.mjs](../frontend/app/tests/summary-layout.test.mjs)
- [frontend/app/tests/task-actions.test.mjs](../frontend/app/tests/task-actions.test.mjs)
- [frontend/app/tests/task-members.test.mjs](../frontend/app/tests/task-members.test.mjs)
- [frontend/app/tests/task-refresh.test.mjs](../frontend/app/tests/task-refresh.test.mjs)
- [frontend/app/tests/task-workflow.test.mjs](../frontend/app/tests/task-workflow.test.mjs)
- [frontend/app/tests/timeline-interactions.test.mjs](../frontend/app/tests/timeline-interactions.test.mjs)
- [frontend/app/tests/timeline.test.mjs](../frontend/app/tests/timeline.test.mjs)
- [frontend/app/tests/today-sidebar.test.mjs](../frontend/app/tests/today-sidebar.test.mjs)
- [frontend/app/tests/workflow-board.test.mjs](../frontend/app/tests/workflow-board.test.mjs)
- [frontend/app/tests/workflow-camera.test.mjs](../frontend/app/tests/workflow-camera.test.mjs)
- [frontend/app/tests/workflow-minimap.test.mjs](../frontend/app/tests/workflow-minimap.test.mjs)
- [frontend/app/tests/workflow-viewport.test.mjs](../frontend/app/tests/workflow-viewport.test.mjs)
- [frontend/app/tests/workspace-menu-keyboard.test.mjs](../frontend/app/tests/workspace-menu-keyboard.test.mjs)
- [frontend/app/tsconfig.json](../frontend/app/tsconfig.json)

### React — frontend/board

- [frontend/board/board.css](../frontend/board/board.css)
- [frontend/board/board.jsx](../frontend/board/board.jsx)
- [frontend/board/build.mjs](../frontend/board/build.mjs)
- [frontend/board/entry.js](../frontend/board/entry.js)
- [frontend/board/package.json](../frontend/board/package.json)
- [frontend/board/pnpm-lock.yaml](../frontend/board/pnpm-lock.yaml)
- [frontend/board/pnpm-workspace.yaml](../frontend/board/pnpm-workspace.yaml)

## 8. Testy

Liczby dotyczą definicji metod, nie uruchomionych przypadków.

### backend/core/test_comment_images.py

Źródło: [backend/core/test_comment_images.py](../backend/core/test_comment_images.py).

- `CommentImageTests`: 16 metod testowych.

### backend/core/test_document_frontend.py

Źródło: [backend/core/test_document_frontend.py](../backend/core/test_document_frontend.py).

- `ReactDocumentTests`: 21 metod testowych.

### backend/core/test_emoji.py

Źródło: [backend/core/test_emoji.py](../backend/core/test_emoji.py).

- `EmojiLibraryTests`: 2 metod testowych.

### backend/core/test_file_lifecycle.py

Źródło: [backend/core/test_file_lifecycle.py](../backend/core/test_file_lifecycle.py).

- `FileLifecycleTests`: 6 metod testowych.
- `PublicMediaTests`: 1 metod testowych.

### backend/core/test_filter_frontend.py

Źródło: [backend/core/test_filter_frontend.py](../backend/core/test_filter_frontend.py).

- `ReactFilterAndTagTests`: 15 metod testowych.

### backend/core/test_form_payload.py

Źródło: [backend/core/test_form_payload.py](../backend/core/test_form_payload.py).

- `PayloadForm`: 0 metod testowych.
- `FormPayloadFieldIdentityTests`: 2 metod testowych.

### backend/core/test_frontend.py

Źródło: [backend/core/test_frontend.py](../backend/core/test_frontend.py).

- `ReactPageApiTests`: 20 metod testowych.

### backend/core/test_list_window.py

Źródło: [backend/core/test_list_window.py](../backend/core/test_list_window.py).

- `ListWindowTests`: 7 metod testowych.

### backend/core/test_navigation_frontend.py

Źródło: [backend/core/test_navigation_frontend.py](../backend/core/test_navigation_frontend.py).

- `ReactNavigationTests`: 17 metod testowych.

### backend/core/test_production.py

Źródło: [backend/core/test_production.py](../backend/core/test_production.py).

- `ProductionConfigurationTests`: 3 metod testowych.
- `ServerAddressTests`: 2 metod testowych.

### backend/core/test_production_installer.py

Źródło: [backend/core/test_production_installer.py](../backend/core/test_production_installer.py).

- `ProductionInstallerTests`: 26 metod testowych.

### backend/core/test_project_layout.py

Źródło: [backend/core/test_project_layout.py](../backend/core/test_project_layout.py).

- `ProjectLayoutTests`: 6 metod testowych.

### backend/core/test_pulpit_frontend.py

Źródło: [backend/core/test_pulpit_frontend.py](../backend/core/test_pulpit_frontend.py).

- `ReactPulpitTests`: 15 metod testowych.

### backend/core/test_schema_baseline.py

Źródło: [backend/core/test_schema_baseline.py](../backend/core/test_schema_baseline.py).

- `CleanMigrationGraphTests`: 3 metod testowych.
- `CleanDatabaseSchemaTests`: 1 metod testowych.

### backend/core/test_shell_frontend.py

Źródło: [backend/core/test_shell_frontend.py](../backend/core/test_shell_frontend.py).

- `GlobalPanelsApiTests`: 16 metod testowych.

### backend/core/test_space_settings_frontend.py

Źródło: [backend/core/test_space_settings_frontend.py](../backend/core/test_space_settings_frontend.py).

- `SpaceSettingsFrontendTests`: 28 metod testowych.

### backend/core/test_status_updates.py

Źródło: [backend/core/test_status_updates.py](../backend/core/test_status_updates.py).

- `StatusUpdateTests`: 3 metod testowych.
- `ConcurrentStatusUpdateTests`: 1 metod testowych.

### backend/core/test_task_integrity.py

Źródło: [backend/core/test_task_integrity.py](../backend/core/test_task_integrity.py).

- `ConcurrentSpaceTaskNumberTests`: 2 metod testowych.
- `TaskIdentityTests`: 1 metod testowych.
- `SpaceTaskIdentityTests`: 6 metod testowych.

### backend/core/test_workspace_frontend.py

Źródło: [backend/core/test_workspace_frontend.py](../backend/core/test_workspace_frontend.py).

- `ReactWorkspaceTests`: 12 metod testowych.

### backend/core/tests.py

Źródło: [backend/core/tests.py](../backend/core/tests.py).

- `UploadValidationTests`: 6 metod testowych.
- `SidebarActiveStateTests`: 11 metod testowych.

### backend/accounts/test_avatars.py

Źródło: [backend/accounts/test_avatars.py](../backend/accounts/test_avatars.py).

- `UserAvatarTests`: 9 metod testowych.

### backend/accounts/test_banner.py

Źródło: [backend/accounts/test_banner.py](../backend/accounts/test_banner.py).

- `UserBannerTests`: 24 metod testowych.

### backend/accounts/test_email_identity.py

Źródło: [backend/accounts/test_email_identity.py](../backend/accounts/test_email_identity.py).

- `EmailIdentityTests`: 9 metod testowych.

### backend/accounts/test_ensure_admin.py

Źródło: [backend/accounts/test_ensure_admin.py](../backend/accounts/test_ensure_admin.py).

- `EnsureAdminTests`: 12 metod testowych.

### backend/accounts/test_frontend.py

Źródło: [backend/accounts/test_frontend.py](../backend/accounts/test_frontend.py).

- `AccountFrontendTests`: 17 metod testowych.

### backend/accounts/test_login_redirects.py

Źródło: [backend/accounts/test_login_redirects.py](../backend/accounts/test_login_redirects.py).

- `LoginRedirectTests`: 9 metod testowych.

### backend/accounts/test_registration_races.py

Źródło: [backend/accounts/test_registration_races.py](../backend/accounts/test_registration_races.py).

- `RegistrationRaceTests`: 1 metod testowych.

### backend/accounts/test_registration_workspace.py

Źródło: [backend/accounts/test_registration_workspace.py](../backend/accounts/test_registration_workspace.py).

- `RegistrationWorkspaceTests`: 8 metod testowych.

### backend/accounts/tests.py

Źródło: [backend/accounts/tests.py](../backend/accounts/tests.py).

- `UserRegistrationFormTests`: 2 metod testowych.
- `AuthPageViewTests`: 2 metod testowych.
- `ProfileViewTests`: 13 metod testowych.
- `SingleAccountSessionTests`: 6 metod testowych.

### backend/workplaces/test_avatars.py

Źródło: [backend/workplaces/test_avatars.py](../backend/workplaces/test_avatars.py).

- `WorkplaceAvatarTests`: 8 metod testowych.

### backend/workplaces/test_default_preference.py

Źródło: [backend/workplaces/test_default_preference.py](../backend/workplaces/test_default_preference.py).

- `DefaultWorkplacePreferenceTests`: 12 metod testowych.
- `DefaultWorkplaceMigrationTests`: 1 metod testowych.

### backend/workplaces/test_defaults.py

Źródło: [backend/workplaces/test_defaults.py](../backend/workplaces/test_defaults.py).

- `DefaultWorkplaceTests`: 3 metod testowych.

### backend/workplaces/test_deletions.py

Źródło: [backend/workplaces/test_deletions.py](../backend/workplaces/test_deletions.py).

- `ConcurrentWorkplaceDeletionTests`: 3 metod testowych.

### backend/workplaces/test_directory_actions.py

Źródło: [backend/workplaces/test_directory_actions.py](../backend/workplaces/test_directory_actions.py).

- `WorkspaceDirectoryActionTests`: 12 metod testowych.

### backend/workplaces/test_email_retirement_migration.py

Źródło: [backend/workplaces/test_email_retirement_migration.py](../backend/workplaces/test_email_retirement_migration.py).

- `EmailInvitationRetirementMigrationTests`: 1 metod testowych.

### backend/workplaces/test_identifiers.py

Źródło: [backend/workplaces/test_identifiers.py](../backend/workplaces/test_identifiers.py).

- `WorkspaceIdentifierTests`: 10 metod testowych.

### backend/workplaces/test_management.py

Źródło: [backend/workplaces/test_management.py](../backend/workplaces/test_management.py).

- `WorkspaceManagementTests`: 18 metod testowych.

### backend/workplaces/test_manual_members.py

Źródło: [backend/workplaces/test_manual_members.py](../backend/workplaces/test_manual_members.py).

- `ManualMemberTests`: 6 metod testowych.
- `ManualMemberConcurrencyTests`: 2 metod testowych.

### backend/workplaces/test_member_candidates.py

Źródło: [backend/workplaces/test_member_candidates.py](../backend/workplaces/test_member_candidates.py).

- `MemberCandidateTests`: 10 metod testowych.

### backend/workplaces/test_read_only_documents.py

Źródło: [backend/workplaces/test_read_only_documents.py](../backend/workplaces/test_read_only_documents.py).

- `ReadOnlyTextDocumentTests`: 6 metod testowych.
- `OfficeRoleDowngradeTests`: 2 metod testowych.

### backend/workplaces/test_team.py

Źródło: [backend/workplaces/test_team.py](../backend/workplaces/test_team.py).

- `TeamAccessTests`: 20 metod testowych.

### backend/workplaces/test_workspace_migration.py

Źródło: [backend/workplaces/test_workspace_migration.py](../backend/workplaces/test_workspace_migration.py).

- `WorkspaceSystemMigrationTests`: 1 metod testowych.

### backend/workplaces/test_workspace_system.py

Źródło: [backend/workplaces/test_workspace_system.py](../backend/workplaces/test_workspace_system.py).

- `WorkspaceSystemTests`: 13 metod testowych.
- `ConcurrentInviteLinkTests`: 1 metod testowych.

### backend/workplaces/tests.py

Źródło: [backend/workplaces/tests.py](../backend/workplaces/tests.py).

- `WorkplaceSelectionTests`: 41 metod testowych.

### backend/tasks/tests.py

Źródło: [backend/tasks/tests.py](../backend/tasks/tests.py).

- `SharedTaskStyleTests`: 12 metod testowych.

### backend/dashboard/test_collaboration.py

Źródło: [backend/dashboard/test_collaboration.py](../backend/dashboard/test_collaboration.py).

- `CollaborationTests`: 14 metod testowych.

### backend/dashboard/test_default_pulpit.py

Źródło: [backend/dashboard/test_default_pulpit.py](../backend/dashboard/test_default_pulpit.py).

- `DefaultPulpitTests`: 7 metod testowych.

### backend/dashboard/test_filter_role_migration.py

Źródło: [backend/dashboard/test_filter_role_migration.py](../backend/dashboard/test_filter_role_migration.py).

- `FilterRoleMigrationTests`: 1 metod testowych.

### backend/dashboard/test_filter_sharing.py

Źródło: [backend/dashboard/test_filter_sharing.py](../backend/dashboard/test_filter_sharing.py).

- `FilterSharingTests`: 11 metod testowych.

### backend/dashboard/test_filters.py

Źródło: [backend/dashboard/test_filters.py](../backend/dashboard/test_filters.py).

- `TaskFilterTests`: 27 metod testowych.

### backend/dashboard/test_for_you.py

Źródło: [backend/dashboard/test_for_you.py](../backend/dashboard/test_for_you.py).

- `ForYouTests`: 28 metod testowych.

### backend/dashboard/test_home.py

Źródło: [backend/dashboard/test_home.py](../backend/dashboard/test_home.py).

- `DashboardHomeTests`: 4 metod testowych.

### backend/dashboard/test_notifications.py

Źródło: [backend/dashboard/test_notifications.py](../backend/dashboard/test_notifications.py).

- `NotificationCenterTests`: 25 metod testowych.

### backend/dashboard/test_pulpit_catalog.py

Źródło: [backend/dashboard/test_pulpit_catalog.py](../backend/dashboard/test_pulpit_catalog.py).

- `GadgetCatalogTests`: 5 metod testowych.

### backend/dashboard/test_pulpit_editor.py

Źródło: [backend/dashboard/test_pulpit_editor.py](../backend/dashboard/test_pulpit_editor.py).

- `PulpitEditorTests`: 7 metod testowych.

### backend/dashboard/test_pulpit_grid.py

Źródło: [backend/dashboard/test_pulpit_grid.py](../backend/dashboard/test_pulpit_grid.py).

- `PulpitGridTests`: 13 metod testowych.
- `PulpitGridMigrationTests`: 1 metod testowych.

### backend/dashboard/test_pulpit_group_retirement.py

Źródło: [backend/dashboard/test_pulpit_group_retirement.py](../backend/dashboard/test_pulpit_group_retirement.py).

- `PulpitGroupRetirementTests`: 3 metod testowych.

### backend/dashboard/test_pulpit_management.py

Źródło: [backend/dashboard/test_pulpit_management.py](../backend/dashboard/test_pulpit_management.py).

- `PulpitManagementTests`: 12 metod testowych.

### backend/dashboard/test_pulpit_navigation.py

Źródło: [backend/dashboard/test_pulpit_navigation.py](../backend/dashboard/test_pulpit_navigation.py).

- `PulpitNavigationTests`: 8 metod testowych.

### backend/dashboard/test_pulpit_preferences.py

Źródło: [backend/dashboard/test_pulpit_preferences.py](../backend/dashboard/test_pulpit_preferences.py).

- `DashboardPreferencesTests`: 11 metod testowych.

### backend/dashboard/test_pulpit_role_migration.py

Źródło: [backend/dashboard/test_pulpit_role_migration.py](../backend/dashboard/test_pulpit_role_migration.py).

- `PulpitRoleMigrationTests`: 1 metod testowych.

### backend/dashboard/test_pulpit_roles.py

Źródło: [backend/dashboard/test_pulpit_roles.py](../backend/dashboard/test_pulpit_roles.py).

- `PulpitRoleTests`: 10 metod testowych.

### backend/dashboard/test_pulpit_settings.py

Źródło: [backend/dashboard/test_pulpit_settings.py](../backend/dashboard/test_pulpit_settings.py).

- `SidebarParser`: 0 metod testowych.
- `PulpitSettingsPageTests`: 7 metod testowych.

### backend/dashboard/test_pulpit_sharing.py

Źródło: [backend/dashboard/test_pulpit_sharing.py](../backend/dashboard/test_pulpit_sharing.py).

- `PulpitSharingFixture`: 0 metod testowych.
- `PulpitSharingTests`: 11 metod testowych.
- `PulpitBulkSharingTests`: 13 metod testowych.
- `PulpitAccessDraftTests`: 13 metod testowych.

### backend/dashboard/test_pulpit_urls.py

Źródło: [backend/dashboard/test_pulpit_urls.py](../backend/dashboard/test_pulpit_urls.py).

- `PulpitUrlTests`: 6 metod testowych.
- `PulpitSlugConcurrencyTests`: 1 metod testowych.

### backend/dashboard/test_pulpits.py

Źródło: [backend/dashboard/test_pulpits.py](../backend/dashboard/test_pulpits.py).

- `PulpitTests`: 32 metod testowych.

### backend/dashboard/test_reminders.py

Źródło: [backend/dashboard/test_reminders.py](../backend/dashboard/test_reminders.py).

- `SpaceTaskReminderTests`: 8 metod testowych.

### backend/dashboard/test_search_regressions.py

Źródło: [backend/dashboard/test_search_regressions.py](../backend/dashboard/test_search_regressions.py).

- `GlobalSearchRegressionTests`: 18 metod testowych.

### backend/dashboard/test_workspace_invitations.py

Źródło: [backend/dashboard/test_workspace_invitations.py](../backend/dashboard/test_workspace_invitations.py).

- `RetiredWorkspaceInvitationTests`: 7 metod testowych.

### backend/dashboard/tests.py

Źródło: [backend/dashboard/tests.py](../backend/dashboard/tests.py).

- `DashboardViewTests`: 7 metod testowych.
- `GlobalSearchTests`: 5 metod testowych.
- `SettingsSpacesCategoryTests`: 7 metod testowych.

### backend/planner/test_sidebar.py

Źródło: [backend/planner/test_sidebar.py](../backend/planner/test_sidebar.py).

- `TodaySidebarTests`: 24 metod testowych.

### backend/planner/test_task_calendar.py

Źródło: [backend/planner/test_task_calendar.py](../backend/planner/test_task_calendar.py).

- `TaskCalendarTests`: 4 metod testowych.

### backend/planner/tests.py

Źródło: [backend/planner/tests.py](../backend/planner/tests.py).

- `CalendarEventTests`: 12 metod testowych.

### backend/documents/test_colors.py

Źródło: [backend/documents/test_colors.py](../backend/documents/test_colors.py).

- `IconColorTests`: 6 metod testowych.

### backend/documents/test_drive_folders.py

Źródło: [backend/documents/test_drive_folders.py](../backend/documents/test_drive_folders.py).

- `DriveFolderTests`: 7 metod testowych.

### backend/documents/test_drive_office.py

Źródło: [backend/documents/test_drive_office.py](../backend/documents/test_drive_office.py).

- `DriveOfficeTests`: 15 metod testowych.

### backend/documents/test_folder_icons.py

Źródło: [backend/documents/test_folder_icons.py](../backend/documents/test_folder_icons.py).

- `FolderIconTestsMixin`: 3 metod testowych.
- `DriveFolderIconTests`: 0 metod testowych.

### backend/documents/test_library_photos.py

Źródło: [backend/documents/test_library_photos.py](../backend/documents/test_library_photos.py).

- `LibraryPhotoTests`: 8 metod testowych.

### backend/documents/test_moves.py

Źródło: [backend/documents/test_moves.py](../backend/documents/test_moves.py).

- `CatalogMoveTests`: 8 metod testowych.
- `DriveMoveTests`: 4 metod testowych.
- `ConcurrentMoveTests`: 1 metod testowych.

### backend/documents/test_office.py

Źródło: [backend/documents/test_office.py](../backend/documents/test_office.py).

- `RichTextTests`: 3 metod testowych.
- `OfficeTests`: 20 metod testowych.

### backend/documents/test_office_extras.py

Źródło: [backend/documents/test_office_extras.py](../backend/documents/test_office_extras.py).

- `OfficeExtrasTests`: 16 metod testowych.

### backend/documents/test_office_folders.py

Źródło: [backend/documents/test_office_folders.py](../backend/documents/test_office_folders.py).

- `OfficeFlatCatalogTests`: 6 metod testowych.

### backend/documents/test_office_query.py

Źródło: [backend/documents/test_office_query.py](../backend/documents/test_office_query.py).

- `OfficeQueryTests`: 9 metod testowych.

### backend/documents/test_personal_star_migration.py

Źródło: [backend/documents/test_personal_star_migration.py](../backend/documents/test_personal_star_migration.py).

- `PersonalDocumentStarMigrationTests`: 1 metod testowych.

### backend/documents/test_personal_stars.py

Źródło: [backend/documents/test_personal_stars.py](../backend/documents/test_personal_stars.py).

- `PersonalDocumentStarTests`: 8 metod testowych.

### backend/documents/test_previews.py

Źródło: [backend/documents/test_previews.py](../backend/documents/test_previews.py).

- `PreviewParserTests`: 9 metod testowych.
- `DocumentPreviewTests`: 9 metod testowych.

### backend/documents/test_query.py

Źródło: [backend/documents/test_query.py](../backend/documents/test_query.py).

- `DocumentQueryTests`: 10 metod testowych.

### backend/documents/test_rename.py

Źródło: [backend/documents/test_rename.py](../backend/documents/test_rename.py).

- `EditorRenameTests`: 9 metod testowych.

### backend/documents/test_suite.py

Źródło: [backend/documents/test_suite.py](../backend/documents/test_suite.py).

- `FullEditorTests`: 20 metod testowych.
- `SceneValidationTests`: 3 metod testowych.

### backend/documents/test_text_uploads.py

Źródło: [backend/documents/test_text_uploads.py](../backend/documents/test_text_uploads.py).

- `TextUploadTests`: 2 metod testowych.

### backend/documents/tests.py

Źródło: [backend/documents/tests.py](../backend/documents/tests.py).

- `DocumentLibraryTests`: 38 metod testowych.

### backend/resources/test_api.py

Źródło: [backend/resources/test_api.py](../backend/resources/test_api.py).

- `ResourceApiTests`: 16 metod testowych.

### backend/resources/test_lifecycle.py

Źródło: [backend/resources/test_lifecycle.py](../backend/resources/test_lifecycle.py).

- `ResourceLifecycleTests`: 16 metod testowych.

### backend/resources/test_migrations.py

Źródło: [backend/resources/test_migrations.py](../backend/resources/test_migrations.py).

- `ResourceLifecycleMigrationTests`: 1 metod testowych.

### backend/resources/tests.py

Źródło: [backend/resources/tests.py](../backend/resources/tests.py).

- `ResourceTests`: 19 metod testowych.

### backend/spaces/test_avatars.py

Źródło: [backend/spaces/test_avatars.py](../backend/spaces/test_avatars.py).

- `SpaceAvatarTests`: 16 metod testowych.

### backend/spaces/test_backlog_drag.py

Źródło: [backend/spaces/test_backlog_drag.py](../backend/spaces/test_backlog_drag.py).

- `BacklogDragTests`: 19 metod testowych.

### backend/spaces/test_backlog_ordering.py

Źródło: [backend/spaces/test_backlog_ordering.py](../backend/spaces/test_backlog_ordering.py).

- `BacklogOrderingTests`: 7 metod testowych.

### backend/spaces/test_backlog_planning.py

Źródło: [backend/spaces/test_backlog_planning.py](../backend/spaces/test_backlog_planning.py).

- `BacklogPlanningTests`: 23 metod testowych.

### backend/spaces/test_backlog_window.py

Źródło: [backend/spaces/test_backlog_window.py](../backend/spaces/test_backlog_window.py).

- `BacklogWindowTests`: 9 metod testowych.

### backend/spaces/test_board_create.py

Źródło: [backend/spaces/test_board_create.py](../backend/spaces/test_board_create.py).

- `BoardCreateTests`: 8 metod testowych.

### backend/spaces/test_board_order.py

Źródło: [backend/spaces/test_board_order.py](../backend/spaces/test_board_order.py).

- `BoardOrderTests`: 17 metod testowych.

### backend/spaces/test_configuration_writes.py

Źródło: [backend/spaces/test_configuration_writes.py](../backend/spaces/test_configuration_writes.py).

- `ConfigurationWriteTests`: 3 metod testowych.

### backend/spaces/test_dashboard.py

Źródło: [backend/spaces/test_dashboard.py](../backend/spaces/test_dashboard.py).

- `SpaceDashboardTests`: 12 metod testowych.

### backend/spaces/test_independent_tasks.py

Źródło: [backend/spaces/test_independent_tasks.py](../backend/spaces/test_independent_tasks.py).

- `IndependentTaskTests`: 21 metod testowych.

### backend/spaces/test_issue_types.py

Źródło: [backend/spaces/test_issue_types.py](../backend/spaces/test_issue_types.py).

- `IssueTypeTests`: 13 metod testowych.

### backend/spaces/test_item_query.py

Źródło: [backend/spaces/test_item_query.py](../backend/spaces/test_item_query.py).

- `ItemQueryTests`: 5 metod testowych.

### backend/spaces/test_kanban_configuration.py

Źródło: [backend/spaces/test_kanban_configuration.py](../backend/spaces/test_kanban_configuration.py).

- `KanbanConfigurationTests`: 26 metod testowych.

### backend/spaces/test_kanban_workflow.py

Źródło: [backend/spaces/test_kanban_workflow.py](../backend/spaces/test_kanban_workflow.py).

- `KanbanWorkflowTests`: 22 metod testowych.
- `KanbanCapacityRaceTests`: 1 metod testowych.

### backend/spaces/test_list_window.py

Źródło: [backend/spaces/test_list_window.py](../backend/spaces/test_list_window.py).

- `ListWindowTests`: 16 metod testowych.

### backend/spaces/test_management.py

Źródło: [backend/spaces/test_management.py](../backend/spaces/test_management.py).

- `SpaceManagementTests`: 10 metod testowych.

### backend/spaces/test_navigation.py

Źródło: [backend/spaces/test_navigation.py](../backend/spaces/test_navigation.py).

- `SpaceNavigationTests`: 6 metod testowych.

### backend/spaces/test_reports.py

Źródło: [backend/spaces/test_reports.py](../backend/spaces/test_reports.py).

- `SpaceReportsTests`: 11 metod testowych.

### backend/spaces/test_schedule_migration.py

Źródło: [backend/spaces/test_schedule_migration.py](../backend/spaces/test_schedule_migration.py).

- `ScheduleMigrationTests`: 1 metod testowych.

### backend/spaces/test_settings_actions.py

Źródło: [backend/spaces/test_settings_actions.py](../backend/spaces/test_settings_actions.py).

- `SpaceSettingsActionTests`: 12 metod testowych.

### backend/spaces/test_space_sharing.py

Źródło: [backend/spaces/test_space_sharing.py](../backend/spaces/test_space_sharing.py).

- `SpaceSharingTests`: 21 metod testowych.

### backend/spaces/test_status_colors.py

Źródło: [backend/spaces/test_status_colors.py](../backend/spaces/test_status_colors.py).

- `StatusColorTests`: 3 metod testowych.

### backend/spaces/test_subtask_fields.py

Źródło: [backend/spaces/test_subtask_fields.py](../backend/spaces/test_subtask_fields.py).

- `SubtaskFieldsTests`: 10 metod testowych.

### backend/spaces/test_subtask_navigation.py

Źródło: [backend/spaces/test_subtask_navigation.py](../backend/spaces/test_subtask_navigation.py).

- `SubtaskNavigationTests`: 7 metod testowych.

### backend/spaces/test_summary.py

Źródło: [backend/spaces/test_summary.py](../backend/spaces/test_summary.py).

- `StatusArcGeometryTests`: 6 metod testowych.
- `SpaceSummaryTests`: 15 metod testowych.

### backend/spaces/test_tags.py

Źródło: [backend/spaces/test_tags.py](../backend/spaces/test_tags.py).

- `SpaceTagTests`: 14 metod testowych.
- `TagWindowTests`: 6 metod testowych.

### backend/spaces/test_task_autosave.py

Źródło: [backend/spaces/test_task_autosave.py](../backend/spaces/test_task_autosave.py).

- `TaskAutosaveTests`: 23 metod testowych.

### backend/spaces/test_task_classification.py

Źródło: [backend/spaces/test_task_classification.py](../backend/spaces/test_task_classification.py).

- `TaskClassificationTests`: 14 metod testowych.

### backend/spaces/test_task_detail_parity.py

Źródło: [backend/spaces/test_task_detail_parity.py](../backend/spaces/test_task_detail_parity.py).

- `DetailParityTests`: 15 metod testowych.

### backend/spaces/test_task_owner_membership.py

Źródło: [backend/spaces/test_task_owner_membership.py](../backend/spaces/test_task_owner_membership.py).

- `TaskOwnerMembershipTests`: 8 metod testowych.

### backend/spaces/test_teams.py

Źródło: [backend/spaces/test_teams.py](../backend/spaces/test_teams.py).

- `TeamSystemTests`: 20 metod testowych.
- `TeamAdminConcurrencyTests`: 1 metod testowych.

### backend/spaces/test_timeline.py

Źródło: [backend/spaces/test_timeline.py](../backend/spaces/test_timeline.py).

- `TimelineTests`: 21 metod testowych.

### backend/spaces/test_urls.py

Źródło: [backend/spaces/test_urls.py](../backend/spaces/test_urls.py).

- `SpaceUrlTests`: 8 metod testowych.
- `ConcurrentSpaceSlugTests`: 1 metod testowych.

### backend/spaces/test_work_logs.py

Źródło: [backend/spaces/test_work_logs.py](../backend/spaces/test_work_logs.py).

- `SpaceTaskWorkLogTests`: 22 metod testowych.

### backend/spaces/test_write_access.py

Źródło: [backend/spaces/test_write_access.py](../backend/spaces/test_write_access.py).

- `SpaceWorkspaceRoleTests`: 3 metod testowych.
- `SpaceWriteAccessRaceTests`: 7 metod testowych.

### backend/spaces/tests.py

Źródło: [backend/spaces/tests.py](../backend/spaces/tests.py).

- `SpaceTests`: 30 metod testowych.

## 9. Migracje obecne lokalnie

Obecność na tej liście nie oznacza śledzenia w Git lub zastosowania w bazie.

### accounts

- [backend/accounts/migrations/0001_initial.py](../backend/accounts/migrations/0001_initial.py)
- [backend/accounts/migrations/0002_user_default_workplace.py](../backend/accounts/migrations/0002_user_default_workplace.py)
- [backend/accounts/migrations/0003_user_profile_banner.py](../backend/accounts/migrations/0003_user_profile_banner.py)
- [backend/accounts/migrations/0004_user_profile_banner_crop.py](../backend/accounts/migrations/0004_user_profile_banner_crop.py)

### workplaces

- [backend/workplaces/migrations/0001_initial.py](../backend/workplaces/migrations/0001_initial.py)
- [backend/workplaces/migrations/0002_workplace_disabled_modules_workplaceinvitation_email_and_more.py](../backend/workplaces/migrations/0002_workplace_disabled_modules_workplaceinvitation_email_and_more.py)
- [backend/workplaces/migrations/0003_workplaceinvitelinkuse.py](../backend/workplaces/migrations/0003_workplaceinvitelinkuse.py)
- [backend/workplaces/migrations/0004_workplaceinvitation_unique_pending_workspace_email.py](../backend/workplaces/migrations/0004_workplaceinvitation_unique_pending_workspace_email.py)
- [backend/workplaces/migrations/0005_remove_email_invitations.py](../backend/workplaces/migrations/0005_remove_email_invitations.py)

### tasks

- [backend/tasks/migrations/0001_initial.py](../backend/tasks/migrations/0001_initial.py)

### dashboard

- [backend/dashboard/migrations/0001_initial.py](../backend/dashboard/migrations/0001_initial.py)
- [backend/dashboard/migrations/0002_initial.py](../backend/dashboard/migrations/0002_initial.py)
- [backend/dashboard/migrations/0003_dashboard_preferences.py](../backend/dashboard/migrations/0003_dashboard_preferences.py)
- [backend/dashboard/migrations/0004_dashboard_emoji_library.py](../backend/dashboard/migrations/0004_dashboard_emoji_library.py)
- [backend/dashboard/migrations/0005_dashboard_membership_roles.py](../backend/dashboard/migrations/0005_dashboard_membership_roles.py)
- [backend/dashboard/migrations/0006_saved_filter_membership_roles.py](../backend/dashboard/migrations/0006_saved_filter_membership_roles.py)
- [backend/dashboard/migrations/0007_remove_workspace_invitations.py](../backend/dashboard/migrations/0007_remove_workspace_invitations.py)
- [backend/dashboard/migrations/0008_dashboard_gadget_grid.py](../backend/dashboard/migrations/0008_dashboard_gadget_grid.py)

### planner

- [backend/planner/migrations/0001_initial.py](../backend/planner/migrations/0001_initial.py)
- [backend/planner/migrations/0002_custom_event_color.py](../backend/planner/migrations/0002_custom_event_color.py)

### documents

- [backend/documents/migrations/0001_initial.py](../backend/documents/migrations/0001_initial.py)
- [backend/documents/migrations/0002_initial.py](../backend/documents/migrations/0002_initial.py)
- [backend/documents/migrations/0003_personal_document_stars.py](../backend/documents/migrations/0003_personal_document_stars.py)

### resources

- [backend/resources/migrations/0001_initial.py](../backend/resources/migrations/0001_initial.py)
- [backend/resources/migrations/0002_resourceactivity_resource_return_due_on_and_more.py](../backend/resources/migrations/0002_resourceactivity_resource_return_due_on_and_more.py)
- [backend/resources/migrations/0003_alter_resourceactivity_actor_name.py](../backend/resources/migrations/0003_alter_resourceactivity_actor_name.py)

### spaces

- [backend/spaces/migrations/0001_initial.py](../backend/spaces/migrations/0001_initial.py)
- [backend/spaces/migrations/0002_initial.py](../backend/spaces/migrations/0002_initial.py)
- [backend/spaces/migrations/0003_space_dashboard_layout.py](../backend/spaces/migrations/0003_space_dashboard_layout.py)
- [backend/spaces/migrations/0004_workitem_start_at.py](../backend/spaces/migrations/0004_workitem_start_at.py)
- [backend/spaces/migrations/0005_kanban_flow.py](../backend/spaces/migrations/0005_kanban_flow.py)
- [backend/spaces/migrations/0006_task_classification.py](../backend/spaces/migrations/0006_task_classification.py)

## 10. Narzędzia i wdrożenie

Źródła narzędzi i konfiguracji usług; bez lokalnych ustawień, archiwów i certyfikatów.

### scripts

- [scripts/assets/build_flaticon_icons.py](../scripts/assets/build_flaticon_icons.py)
- [scripts/assets/build_fluent_emoji.py](../scripts/assets/build_fluent_emoji.py)
- [scripts/assets/flaticon-icon-map.json](../scripts/assets/flaticon-icon-map.json)
- [scripts/office/configure.py](../scripts/office/configure.py)
- [scripts/office/start.sh](../scripts/office/start.sh)
- [scripts/run_tests.py](../scripts/run_tests.py)
- [scripts/start_office.sh](../scripts/start_office.sh)
- [scripts/update_code_index.py](../scripts/update_code_index.py)

### deploy

- [deploy/Dockerfile](../deploy/Dockerfile)
- [deploy/backend/entrypoint.sh](../deploy/backend/entrypoint.sh)
- [deploy/backend/gunicorn.conf.py](../deploy/backend/gunicorn.conf.py)
- [deploy/backend/requirements.txt](../deploy/backend/requirements.txt)
- [deploy/cli/configure.py](../deploy/cli/configure.py)
- [deploy/cli/runtime.sh](../deploy/cli/runtime.sh)
- [deploy/cli/setup.sh](../deploy/cli/setup.sh)
- [deploy/compose.yaml](../deploy/compose.yaml)
- [deploy/postgres/init.sh](../deploy/postgres/init.sh)
- [deploy/production.env.example](../deploy/production.env.example)
