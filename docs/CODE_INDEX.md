# Indeks kodu Ancore

Plik generowany przez `python scripts/update_code_index.py`. Nie edytuj ręcznie.

Zakres: lokalne źródła skonfigurowanych aplikacji, konfiguracja Django oraz
zasoby `static/`. Uwzględnia pliki nieśledzone i ignorowane przez Git, jeśli
są obecne lokalnie. Pomija sekrety, uploady, środowisko i cache Pythona.
Generator nie importuje aplikacji ani nie łączy się z bazą.

To katalog deklaracji, nie dowód dostępności funkcji lub wykonania testów.
Pola odziedziczone, dynamiczny routing i semantyka helperów nie są
odtwarzane. Aktywne zachowania i pozostałości opisują [Moduły](MODULES.md)
oraz [Mechanizmy](MECHANISMS.md).

## 1. Przegląd katalogów

| Katalog | Python poza migracjami | Migracje bez init | Szablony HTML | Metody test_* |
| --- | ---: | ---: | ---: | ---: |
| [ancore](../ancore) | 5 | 0 | 0 | 0 |
| [core](../core) | 21 | 0 | 20 | 55 |
| [accounts](../accounts) | 20 | 7 | 9 | 56 |
| [workplaces](../workplaces) | 22 | 10 | 13 | 116 |
| [tasks](../tasks) | 42 | 66 | 46 | 332 |
| [kanban](../kanban) | 18 | 39 | 10 | 9 |
| [contacts](../contacts) | 10 | 8 | 11 | 6 |
| [dashboard](../dashboard) | 41 | 14 | 43 | 237 |
| [planner](../planner) | 9 | 2 | 2 | 7 |
| [documents](../documents) | 37 | 11 | 31 | 203 |
| [resources](../resources) | 7 | 1 | 2 | 19 |
| [spaces](../spaces) | 41 | 9 | 39 | 223 |

## 2. Modele i relacje

## Modele: core

Brak zadeklarowanych modeli domenowych w tym pliku.

## Modele: accounts

### `User`

Źródło: [accounts/models.py](../accounts/models.py).

Pola zadeklarowane tutaj: `email` (EmailField), `first_name` (CharField), `middle_name` (CharField), `last_name` (CharField), `avatar` (CharField), `profile_photo` (FileField), `phone_number` (CharField), `job_title` (CharField), `bio` (TextField), `presence_status` (CharField), `last_seen_at` (DateTimeField).

Metody/properties: `presence_status_class`, `get_full_name`, `__str__`.

## Modele: workplaces

### `Workplace`

Źródło: [workplaces/models.py](../workplaces/models.py).

Pola zadeklarowane tutaj: `name` (CharField), `description` (TextField), `code` (CharField), `slug` (SlugField), `legacy_slug` (SlugField), `avatar` (CharField), `workplace_photo` (FileField), `owner` (ForeignKey), `members` (ManyToManyField), `created_at` (DateTimeField), `updated_at` (DateTimeField).

| Relacja | Cel | Ustawienia |
| --- | --- | --- |
| `owner` | `settings.AUTH_USER_MODEL` | on_delete=models.CASCADE; related_name='owned_workplaces' |
| `members` | `settings.AUTH_USER_MODEL` | related_name='workplaces'; through='WorkplaceMembership' |

Metody/properties: `save`, `initials`, `ensure_owner_membership`, `__str__`.

### `WorkplaceMembership`

Źródło: [workplaces/models.py](../workplaces/models.py).

Pola zadeklarowane tutaj: `workplace` (ForeignKey), `user` (ForeignKey), `role` (CharField), `is_active` (BooleanField), `created_at` (DateTimeField).

| Relacja | Cel | Ustawienia |
| --- | --- | --- |
| `workplace` | `Workplace` | on_delete=models.CASCADE; related_name='memberships' |
| `user` | `settings.AUTH_USER_MODEL` | on_delete=models.CASCADE; related_name='workplace_memberships' |

Metody/properties: `__str__`.

### `WorkplaceInvitation`

Źródło: [workplaces/models.py](../workplaces/models.py).

Pola zadeklarowane tutaj: `workplace` (ForeignKey), `recipient` (ForeignKey), `invited_by` (ForeignKey), `role` (CharField), `status` (CharField), `created_at` (DateTimeField), `expires_at` (DateTimeField).

| Relacja | Cel | Ustawienia |
| --- | --- | --- |
| `workplace` | `Workplace` | on_delete=models.CASCADE; related_name='invitations' |
| `recipient` | `settings.AUTH_USER_MODEL` | on_delete=models.CASCADE; related_name='workplace_invitations' |
| `invited_by` | `settings.AUTH_USER_MODEL` | on_delete=models.SET_NULL; related_name='sent_workplace_invitations'; null=True |

### `SidebarFavorite`

Źródło: [workplaces/models.py](../workplaces/models.py).

Pola zadeklarowane tutaj: `user` (ForeignKey), `workplace` (ForeignKey), `item_key` (CharField), `position` (PositiveIntegerField), `created_at` (DateTimeField).

| Relacja | Cel | Ustawienia |
| --- | --- | --- |
| `user` | `settings.AUTH_USER_MODEL` | on_delete=models.CASCADE; related_name='sidebar_favorites' |
| `workplace` | `Workplace` | on_delete=models.CASCADE; related_name='sidebar_favorites' |

Metody/properties: `__str__`.

## Modele: tasks

### `TaskProject`

Źródło: [tasks/models.py](../tasks/models.py).

Pola zadeklarowane tutaj: `space_archived` (BooleanField), `visibility` (CharField), `private_owner` (ForeignKey), `shared_with` (ManyToManyField), `favorited_by` (ManyToManyField), `name` (CharField), `description` (TextField), `code` (CharField), `next_section_code_number` (PositiveIntegerField), `icon` (CharField), `priority` (CharField), `status` (CharField), `stage` (CharField), `health` (CharField), `start_at` (DateField), `due_at` (DateField), `budget_amount` (DecimalField), `currency` (CharField), `source` (CharField), `company` (ForeignKey), `responsible_user` (ForeignKey), `user` (ForeignKey), `workplace` (ForeignKey), `created_at` (DateTimeField).

| Relacja | Cel | Ustawienia |
| --- | --- | --- |
| `private_owner` | `settings.AUTH_USER_MODEL` | on_delete=models.SET_NULL; related_name='private_task_projects'; null=True |
| `shared_with` | `settings.AUTH_USER_MODEL` | related_name='shared_task_projects'; through='TaskProjectMembership' |
| `favorited_by` | `settings.AUTH_USER_MODEL` | related_name='favorite_task_projects' |
| `company` | `'contacts.Company'` | on_delete=models.SET_NULL; related_name='task_projects'; null=True |
| `responsible_user` | `settings.AUTH_USER_MODEL` | on_delete=models.SET_NULL; related_name='responsible_task_projects'; null=True |
| `user` | `settings.AUTH_USER_MODEL` | on_delete=models.CASCADE; related_name='task_projects' |
| `workplace` | `'workplaces.Workplace'` | on_delete=models.CASCADE; related_name='task_projects'; null=True |

Metody/properties: `_code_scope_models`, `_code_exists`, `_generate_unique_code`, `save`, `__str__`, `get_status_display`, `get_stage_display`, `get_health_display`.

### `TaskProjectMembership`

Źródło: [tasks/models.py](../tasks/models.py).

Pola zadeklarowane tutaj: `project` (ForeignKey), `user` (ForeignKey), `role` (CharField), `created_at` (DateTimeField).

| Relacja | Cel | Ustawienia |
| --- | --- | --- |
| `project` | `TaskProject` | on_delete=models.CASCADE; related_name='memberships' |
| `user` | `settings.AUTH_USER_MODEL` | on_delete=models.CASCADE |

### `TaskProjectInvitation`

Źródło: [tasks/models.py](../tasks/models.py).

Pola zadeklarowane tutaj: `project` (ForeignKey), `recipient` (ForeignKey), `invited_by` (ForeignKey), `role` (CharField), `status` (CharField), `created_at` (DateTimeField), `expires_at` (DateTimeField).

| Relacja | Cel | Ustawienia |
| --- | --- | --- |
| `project` | `TaskProject` | on_delete=models.CASCADE; related_name='invitations' |
| `recipient` | `settings.AUTH_USER_MODEL` | on_delete=models.CASCADE; related_name='project_invitations' |
| `invited_by` | `settings.AUTH_USER_MODEL` | on_delete=models.SET_NULL; related_name='sent_project_invitations'; null=True |

### `TaskProjectTemplate`

Źródło: [tasks/models.py](../tasks/models.py).

Pola zadeklarowane tutaj: `visibility` (CharField), `private_owner` (ForeignKey), `user` (ForeignKey), `workplace` (ForeignKey), `name` (CharField), `template_name` (CharField), `description` (TextField), `structure` (JSONField), `created_at` (DateTimeField).

| Relacja | Cel | Ustawienia |
| --- | --- | --- |
| `private_owner` | `settings.AUTH_USER_MODEL` | on_delete=models.SET_NULL; related_name='private_task_project_templates'; null=True |
| `user` | `settings.AUTH_USER_MODEL` | on_delete=models.CASCADE |
| `workplace` | `'workplaces.Workplace'` | on_delete=models.CASCADE; null=True |

Metody/properties: `__str__`.

### `TaskProjectNote`

Źródło: [tasks/models.py](../tasks/models.py).

Pola zadeklarowane tutaj: `project` (ForeignKey), `author` (ForeignKey), `message` (TextField), `created_at` (DateTimeField), `updated_at` (DateTimeField), `edited_at` (DateTimeField).

| Relacja | Cel | Ustawienia |
| --- | --- | --- |
| `project` | `TaskProject` | on_delete=models.CASCADE; related_name='project_notes' |
| `author` | `settings.AUTH_USER_MODEL` | on_delete=models.SET_NULL; related_name='task_project_notes'; null=True |

Metody/properties: `__str__`.

### `TaskSection`

Źródło: [tasks/models.py](../tasks/models.py).

Pola zadeklarowane tutaj: `visibility` (CharField), `private_owner` (ForeignKey), `shared_with` (ManyToManyField), `favorited_by` (ManyToManyField), `project` (ForeignKey), `title` (CharField), `description` (TextField), `code` (CharField), `code_number` (PositiveIntegerField), `next_task_code_number` (PositiveIntegerField), `priority` (CharField), `status` (CharField), `kind` (CharField), `icon` (CharField), `owner` (ForeignKey), `due_at` (DateField), `wip_limit` (PositiveIntegerField), `order` (PositiveIntegerField), `created_at` (DateTimeField).

| Relacja | Cel | Ustawienia |
| --- | --- | --- |
| `private_owner` | `settings.AUTH_USER_MODEL` | on_delete=models.SET_NULL; related_name='private_task_sections'; null=True |
| `shared_with` | `settings.AUTH_USER_MODEL` | related_name='shared_task_sections'; through='TaskSectionMembership' |
| `favorited_by` | `settings.AUTH_USER_MODEL` | related_name='favorite_task_sections' |
| `project` | `TaskProject` | on_delete=models.CASCADE; related_name='sections' |
| `owner` | `settings.AUTH_USER_MODEL` | on_delete=models.SET_NULL; related_name='owned_task_sections'; null=True |

Metody/properties: `_claim_next_code_number`, `save`, `full_code`, `__str__`.

### `TaskSectionMembership`

Źródło: [tasks/models.py](../tasks/models.py).

Pola zadeklarowane tutaj: `section` (ForeignKey), `user` (ForeignKey), `role` (CharField), `created_at` (DateTimeField).

| Relacja | Cel | Ustawienia |
| --- | --- | --- |
| `section` | `TaskSection` | on_delete=models.CASCADE; related_name='memberships' |
| `user` | `settings.AUTH_USER_MODEL` | on_delete=models.CASCADE |

### `TaskSectionInvitation`

Źródło: [tasks/models.py](../tasks/models.py).

Pola zadeklarowane tutaj: `section` (ForeignKey), `recipient` (ForeignKey), `invited_by` (ForeignKey), `role` (CharField), `status` (CharField), `created_at` (DateTimeField), `expires_at` (DateTimeField).

| Relacja | Cel | Ustawienia |
| --- | --- | --- |
| `section` | `TaskSection` | on_delete=models.CASCADE; related_name='invitations' |
| `recipient` | `settings.AUTH_USER_MODEL` | on_delete=models.CASCADE; related_name='section_invitations' |
| `invited_by` | `settings.AUTH_USER_MODEL` | on_delete=models.SET_NULL; related_name='sent_section_invitations'; null=True |

### `TaskSectionNote`

Źródło: [tasks/models.py](../tasks/models.py).

Pola zadeklarowane tutaj: `section` (ForeignKey), `author` (ForeignKey), `message` (TextField), `created_at` (DateTimeField), `updated_at` (DateTimeField), `edited_at` (DateTimeField).

| Relacja | Cel | Ustawienia |
| --- | --- | --- |
| `section` | `TaskSection` | on_delete=models.CASCADE; related_name='section_notes' |
| `author` | `settings.AUTH_USER_MODEL` | on_delete=models.SET_NULL; related_name='task_section_notes'; null=True |

Metody/properties: `__str__`.

### `TaskTag`

Źródło: [tasks/models.py](../tasks/models.py).

Pola zadeklarowane tutaj: `name` (CharField), `description` (TextField), `code` (CharField), `category` (CharField), `color` (CharField), `icon` (CharField), `priority` (CharField), `scope` (CharField), `owner_label` (CharField), `status` (CharField), `usage_notes` (TextField), `automation_rules` (TextField), `user` (ForeignKey), `workplace` (ForeignKey), `space` (ForeignKey), `related_tags` (ManyToManyField), `created_at` (DateTimeField).

| Relacja | Cel | Ustawienia |
| --- | --- | --- |
| `user` | `settings.AUTH_USER_MODEL` | on_delete=models.CASCADE; related_name='task_tags' |
| `workplace` | `'workplaces.Workplace'` | on_delete=models.CASCADE; related_name='task_tags'; null=True |
| `space` | `'spaces.Space'` | on_delete=models.CASCADE; related_name='tags'; null=True |
| `related_tags` | `'self'` | — |

Metody/properties: `_code_scope_models`, `_code_exists`, `_generate_unique_code`, `save`, `__str__`.

### `TaskTagNote`

Źródło: [tasks/models.py](../tasks/models.py).

Pola zadeklarowane tutaj: `tag` (ForeignKey), `author` (ForeignKey), `message` (TextField), `created_at` (DateTimeField), `updated_at` (DateTimeField), `edited_at` (DateTimeField).

| Relacja | Cel | Ustawienia |
| --- | --- | --- |
| `tag` | `TaskTag` | on_delete=models.CASCADE; related_name='tag_notes' |
| `author` | `settings.AUTH_USER_MODEL` | on_delete=models.SET_NULL; related_name='task_tag_notes'; null=True |

Metody/properties: `__str__`.

### `Task`

Źródło: [tasks/models.py](../tasks/models.py).

Pola zadeklarowane tutaj: `space_archived` (BooleanField), `visibility` (CharField), `private_owner` (ForeignKey), `shared_with` (ManyToManyField), `favorited_by` (ManyToManyField), `task_id` (PositiveIntegerField), `code_number` (PositiveIntegerField), `title` (CharField), `description` (TextField), `priority` (CharField), `status` (CharField), `is_completed` (BooleanField), `created_at` (DateTimeField), `completion_date` (DateTimeField), `due_at` (DateTimeField), `reminder_at` (DateTimeField), `estimated_minutes` (PositiveIntegerField), `time_spent_hours` (PositiveIntegerField), `time_spent_minutes` (PositiveIntegerField), `task_type` (CharField), `blocked_reason` (TextField), `user` (ForeignKey), `workplace` (ForeignKey), `assignee` (ForeignKey), `section` (ForeignKey), `tags` (ManyToManyField), `parent` (ForeignKey).

| Relacja | Cel | Ustawienia |
| --- | --- | --- |
| `private_owner` | `settings.AUTH_USER_MODEL` | on_delete=models.SET_NULL; related_name='private_tasks'; null=True |
| `shared_with` | `settings.AUTH_USER_MODEL` | related_name='shared_tasks'; through='TaskMembership' |
| `favorited_by` | `settings.AUTH_USER_MODEL` | related_name='favorite_tasks' |
| `user` | `settings.AUTH_USER_MODEL` | on_delete=models.CASCADE; related_name='tasks' |
| `workplace` | `'workplaces.Workplace'` | on_delete=models.CASCADE; related_name='tasks'; null=True |
| `assignee` | `settings.AUTH_USER_MODEL` | on_delete=models.SET_NULL; related_name='assigned_tasks'; null=True |
| `section` | `TaskSection` | on_delete=models.CASCADE; related_name='tasks'; null=True |
| `tags` | `TaskTag` | related_name='tasks' |
| `parent` | `'self'` | on_delete=models.CASCADE; related_name='subtasks'; null=True |

Metody/properties: `_claim_next_code_number`, `save`, `delete`, `_renumber_user_tasks`, `__str__`, `code`, `full_code`, `_activity_datetime`, `_activity_time_spent`, `has_time_spent`, `time_spent_label`, `due_urgency`, `get_file_extension`.

### `TaskMembership`

Źródło: [tasks/models.py](../tasks/models.py).

Pola zadeklarowane tutaj: `task` (ForeignKey), `user` (ForeignKey), `role` (CharField), `created_at` (DateTimeField).

| Relacja | Cel | Ustawienia |
| --- | --- | --- |
| `task` | `Task` | on_delete=models.CASCADE; related_name='memberships' |
| `user` | `settings.AUTH_USER_MODEL` | on_delete=models.CASCADE |

### `TaskWorkLog`

Źródło: [tasks/models.py](../tasks/models.py).

Pola zadeklarowane tutaj: `task` (ForeignKey), `author` (ForeignKey), `started_at` (DateTimeField), `ended_at` (DateTimeField), `description` (TextField), `created_at` (DateTimeField), `updated_at` (DateTimeField).

| Relacja | Cel | Ustawienia |
| --- | --- | --- |
| `task` | `Task` | on_delete=models.CASCADE; related_name='work_logs' |
| `author` | `settings.AUTH_USER_MODEL` | on_delete=models.SET_NULL; related_name='task_work_logs'; null=True |

Metody/properties: `duration_minutes`, `__str__`.

### `TaskAttachment`

Źródło: [tasks/models.py](../tasks/models.py).

Pola zadeklarowane tutaj: `task` (ForeignKey), `file` (FileField), `filename` (CharField), `uploaded_at` (DateTimeField), `file_size` (PositiveIntegerField).

| Relacja | Cel | Ustawienia |
| --- | --- | --- |
| `task` | `Task` | on_delete=models.CASCADE; related_name='attachments' |

Metody/properties: `save`, `get_file_extension`, `is_image`, `is_pdf`, `get_type_class`, `get_type_label`, `get_formatted_size`, `__str__`.

### `TaskActivity`

Źródło: [tasks/models.py](../tasks/models.py).

Pola zadeklarowane tutaj: `task` (ForeignKey), `actor` (ForeignKey), `kind` (CharField), `action` (CharField), `message` (TextField), `metadata` (JSONField), `created_at` (DateTimeField).

| Relacja | Cel | Ustawienia |
| --- | --- | --- |
| `task` | `Task` | on_delete=models.CASCADE; related_name='activities' |
| `actor` | `settings.AUTH_USER_MODEL` | on_delete=models.SET_NULL; related_name='task_activities'; null=True |

Metody/properties: `__str__`.

### `TaskCommentImage`

Źródło: [tasks/models.py](../tasks/models.py).

Pola zadeklarowane tutaj: `activity` (ForeignKey).

| Relacja | Cel | Ustawienia |
| --- | --- | --- |
| `activity` | `TaskActivity` | on_delete=models.CASCADE; related_name='images' |

## Modele: kanban

### `KanbanProject`

Źródło: [kanban/models.py](../kanban/models.py).

Pola zadeklarowane tutaj: `visibility` (CharField), `private_owner` (ForeignKey), `shared_with` (ManyToManyField), `name` (CharField), `description` (TextField), `code` (CharField), `icon` (CharField), `priority` (CharField), `status` (CharField), `stage` (CharField), `health` (CharField), `start_at` (DateField), `due_at` (DateField), `budget_amount` (DecimalField), `currency` (CharField), `source` (CharField), `company` (ForeignKey), `responsible_user` (ForeignKey), `user` (ForeignKey), `favorited_by` (ManyToManyField), `workplace` (ForeignKey), `created_at` (DateTimeField).

| Relacja | Cel | Ustawienia |
| --- | --- | --- |
| `private_owner` | `settings.AUTH_USER_MODEL` | on_delete=models.SET_NULL; related_name='private_kanban_projects'; null=True |
| `shared_with` | `settings.AUTH_USER_MODEL` | related_name='shared_kanban_projects'; through='KanbanProjectMembership' |
| `company` | `'contacts.Company'` | on_delete=models.SET_NULL; related_name='kanban_projects'; null=True |
| `responsible_user` | `settings.AUTH_USER_MODEL` | on_delete=models.SET_NULL; related_name='responsible_kanban_projects'; null=True |
| `user` | `settings.AUTH_USER_MODEL` | on_delete=models.CASCADE; related_name='kanban_projects' |
| `favorited_by` | `settings.AUTH_USER_MODEL` | related_name='favorite_kanban_projects' |
| `workplace` | `'workplaces.Workplace'` | on_delete=models.CASCADE; related_name='kanban_projects'; null=True |

Metody/properties: `_code_scope_models`, `_code_exists`, `_generate_unique_code`, `save`, `__str__`.

### `KanbanProjectNote`

Źródło: [kanban/models.py](../kanban/models.py).

Pola zadeklarowane tutaj: `project` (ForeignKey), `author` (ForeignKey), `message` (TextField), `created_at` (DateTimeField), `updated_at` (DateTimeField), `edited_at` (DateTimeField).

| Relacja | Cel | Ustawienia |
| --- | --- | --- |
| `project` | `KanbanProject` | on_delete=models.CASCADE; related_name='project_notes' |
| `author` | `settings.AUTH_USER_MODEL` | on_delete=models.SET_NULL; related_name='kanban_project_notes'; null=True |

Metody/properties: `__str__`.

### `KanbanSection`

Źródło: [kanban/models.py](../kanban/models.py).

Pola zadeklarowane tutaj: `visibility` (CharField), `private_owner` (ForeignKey), `shared_with` (ManyToManyField), `project` (ForeignKey), `favorited_by` (ManyToManyField), `title` (CharField), `description` (TextField), `kind` (CharField), `icon` (CharField), `order` (PositiveIntegerField), `created_at` (DateTimeField).

| Relacja | Cel | Ustawienia |
| --- | --- | --- |
| `private_owner` | `settings.AUTH_USER_MODEL` | on_delete=models.SET_NULL; related_name='private_kanban_sections'; null=True |
| `shared_with` | `settings.AUTH_USER_MODEL` | related_name='shared_kanban_sections'; through='KanbanSectionMembership' |
| `project` | `KanbanProject` | on_delete=models.CASCADE; related_name='sections' |
| `favorited_by` | `settings.AUTH_USER_MODEL` | related_name='favorite_kanban_sections' |

Metody/properties: `__str__`.

### `KanbanBoardColumn`

Źródło: [kanban/models.py](../kanban/models.py).

Pola zadeklarowane tutaj: `section` (ForeignKey), `title` (CharField), `order` (PositiveIntegerField), `is_done` (BooleanField), `created_at` (DateTimeField).

| Relacja | Cel | Ustawienia |
| --- | --- | --- |
| `section` | `KanbanSection` | on_delete=models.CASCADE; related_name='columns' |

Metody/properties: `ensure_defaults_for_section`, `__str__`.

### `Kanban`

Źródło: [kanban/models.py](../kanban/models.py).

Pola zadeklarowane tutaj: `task_id` (PositiveIntegerField), `title` (CharField), `description` (TextField), `priority` (CharField), `status` (CharField), `is_completed` (BooleanField), `created_at` (DateTimeField), `completion_date` (DateTimeField), `due_at` (DateTimeField), `time_spent_hours` (PositiveIntegerField), `time_spent_minutes` (PositiveIntegerField), `user` (ForeignKey), `workplace` (ForeignKey), `section` (ForeignKey), `column` (ForeignKey), `tags` (ManyToManyField), `parent` (ForeignKey).

| Relacja | Cel | Ustawienia |
| --- | --- | --- |
| `user` | `settings.AUTH_USER_MODEL` | on_delete=models.CASCADE; related_name='kanban_items' |
| `workplace` | `'workplaces.Workplace'` | on_delete=models.CASCADE; related_name='kanban_items'; null=True |
| `section` | `KanbanSection` | on_delete=models.SET_NULL; related_name='tasks'; null=True |
| `column` | `KanbanBoardColumn` | on_delete=models.SET_NULL; related_name='cards'; null=True |
| `tags` | `TaskTag` | related_name='kanban_cards' |
| `parent` | `'self'` | on_delete=models.CASCADE; related_name='subtasks'; null=True |

Metody/properties: `save`, `delete`, `_renumber_user_tasks`, `__str__`, `_activity_datetime`, `_activity_time_spent`, `has_time_spent`, `time_spent_label`, `get_file_extension`.

### `KanbanAttachment`

Źródło: [kanban/models.py](../kanban/models.py).

Pola zadeklarowane tutaj: `task` (ForeignKey), `file` (FileField), `filename` (CharField), `uploaded_at` (DateTimeField), `file_size` (PositiveIntegerField).

| Relacja | Cel | Ustawienia |
| --- | --- | --- |
| `task` | `Kanban` | on_delete=models.CASCADE; related_name='attachments' |

Metody/properties: `save`, `get_file_extension`, `is_image`, `is_pdf`, `get_type_class`, `get_type_label`, `get_formatted_size`, `__str__`.

### `KanbanActivity`

Źródło: [kanban/models.py](../kanban/models.py).

Pola zadeklarowane tutaj: `task` (ForeignKey), `actor` (ForeignKey), `kind` (CharField), `action` (CharField), `message` (TextField), `metadata` (JSONField), `created_at` (DateTimeField).

| Relacja | Cel | Ustawienia |
| --- | --- | --- |
| `task` | `Kanban` | on_delete=models.CASCADE; related_name='activities' |
| `actor` | `settings.AUTH_USER_MODEL` | on_delete=models.SET_NULL; related_name='kanban_activities'; null=True |

Metody/properties: `__str__`.

### `KanbanCommentImage`

Źródło: [kanban/models.py](../kanban/models.py).

Pola zadeklarowane tutaj: `activity` (ForeignKey).

| Relacja | Cel | Ustawienia |
| --- | --- | --- |
| `activity` | `KanbanActivity` | on_delete=models.CASCADE; related_name='images' |

### `KanbanProjectMembership`

Źródło: [kanban/models.py](../kanban/models.py).

Pola zadeklarowane tutaj: `project` (ForeignKey), `user` (ForeignKey), `role` (CharField), `created_at` (DateTimeField).

| Relacja | Cel | Ustawienia |
| --- | --- | --- |
| `project` | `KanbanProject` | on_delete=models.CASCADE; related_name='memberships' |
| `user` | `settings.AUTH_USER_MODEL` | on_delete=models.CASCADE |

### `KanbanSectionMembership`

Źródło: [kanban/models.py](../kanban/models.py).

Pola zadeklarowane tutaj: `section` (ForeignKey), `user` (ForeignKey), `role` (CharField), `created_at` (DateTimeField).

| Relacja | Cel | Ustawienia |
| --- | --- | --- |
| `section` | `KanbanSection` | on_delete=models.CASCADE; related_name='memberships' |
| `user` | `settings.AUTH_USER_MODEL` | on_delete=models.CASCADE |

## Modele: contacts

### `Company`

Źródło: [contacts/models.py](../contacts/models.py).

Pola zadeklarowane tutaj: `name` (CharField), `website` (URLField), `email` (EmailField), `phone` (CharField), `address` (CharField), `notes` (TextField), `company_photo` (FileField), `owner` (ForeignKey), `workplace` (ForeignKey), `members` (ManyToManyField), `created_at` (DateTimeField), `updated_at` (DateTimeField).

| Relacja | Cel | Ustawienia |
| --- | --- | --- |
| `owner` | `settings.AUTH_USER_MODEL` | on_delete=models.CASCADE; related_name='companies' |
| `workplace` | `'workplaces.Workplace'` | on_delete=models.CASCADE; related_name='companies'; null=True |
| `members` | `settings.AUTH_USER_MODEL` | related_name='company_memberships'; through='CompanyMembership' |

Metody/properties: `__str__`, `initials`.

### `CompanyMembership`

Źródło: [contacts/models.py](../contacts/models.py).

Pola zadeklarowane tutaj: `company` (ForeignKey), `user` (ForeignKey), `role` (CharField), `created_at` (DateTimeField).

| Relacja | Cel | Ustawienia |
| --- | --- | --- |
| `company` | `Company` | on_delete=models.CASCADE; related_name='memberships' |
| `user` | `settings.AUTH_USER_MODEL` | on_delete=models.CASCADE; related_name='company_membership_rows' |

Metody/properties: `__str__`.

### `Contact`

Źródło: [contacts/models.py](../contacts/models.py).

Pola zadeklarowane tutaj: `first_name` (CharField), `middle_name` (CharField), `last_name` (CharField), `company` (CharField), `company_record` (ForeignKey), `role` (CharField), `email` (EmailField), `phone` (CharField), `source` (CharField), `status` (CharField), `notes` (TextField), `last_contacted_at` (DateTimeField), `created_at` (DateTimeField), `updated_at` (DateTimeField), `user` (ForeignKey), `workplace` (ForeignKey).

| Relacja | Cel | Ustawienia |
| --- | --- | --- |
| `company_record` | `Company` | on_delete=models.SET_NULL; related_name='contacts'; null=True |
| `user` | `settings.AUTH_USER_MODEL` | on_delete=models.CASCADE; related_name='contacts' |
| `workplace` | `'workplaces.Workplace'` | on_delete=models.CASCADE; related_name='contacts'; null=True |

Metody/properties: `__str__`, `display_name`, `initials`.

### `UserContact`

Źródło: [contacts/models.py](../contacts/models.py).

Pola zadeklarowane tutaj: `owner` (ForeignKey), `workplace` (ForeignKey), `target_user` (ForeignKey), `linked_contact` (ForeignKey), `note` (CharField), `created_at` (DateTimeField).

| Relacja | Cel | Ustawienia |
| --- | --- | --- |
| `owner` | `settings.AUTH_USER_MODEL` | on_delete=models.CASCADE; related_name='user_contacts' |
| `workplace` | `'workplaces.Workplace'` | on_delete=models.CASCADE; related_name='user_contacts'; null=True |
| `target_user` | `settings.AUTH_USER_MODEL` | on_delete=models.CASCADE; related_name='added_by_users' |
| `linked_contact` | `Contact` | on_delete=models.SET_NULL; related_name='linked_user_contacts'; null=True |

Metody/properties: `__str__`.

### `ContactActivity`

Źródło: [contacts/models.py](../contacts/models.py).

Pola zadeklarowane tutaj: `contact` (ForeignKey), `actor` (ForeignKey), `kind` (CharField), `action` (CharField), `message` (TextField), `metadata` (JSONField), `created_at` (DateTimeField).

| Relacja | Cel | Ustawienia |
| --- | --- | --- |
| `contact` | `Contact` | on_delete=models.CASCADE; related_name='activities' |
| `actor` | `settings.AUTH_USER_MODEL` | on_delete=models.SET_NULL; related_name='contact_activities'; null=True |

Metody/properties: `__str__`.

### `SharedItem`

Źródło: [contacts/models.py](../contacts/models.py).

Pola zadeklarowane tutaj: `content_type` (ForeignKey), `object_id` (PositiveBigIntegerField), `content_object` (GenericForeignKey), `shared_by` (ForeignKey), `shared_with` (ForeignKey), `permission` (CharField), `note` (CharField), `created_at` (DateTimeField).

| Relacja | Cel | Ustawienia |
| --- | --- | --- |
| `content_type` | `ContentType` | on_delete=models.CASCADE |
| `content_object` | `'content_type'` | — |
| `shared_by` | `settings.AUTH_USER_MODEL` | on_delete=models.CASCADE; related_name='shared_items_sent' |
| `shared_with` | `settings.AUTH_USER_MODEL` | on_delete=models.CASCADE; related_name='shared_items_received' |

Metody/properties: `__str__`.

### `SharedItemLink`

Źródło: [contacts/models.py](../contacts/models.py).

Pola zadeklarowane tutaj: `content_type` (ForeignKey), `object_id` (PositiveBigIntegerField), `content_object` (GenericForeignKey), `created_by` (ForeignKey), `token` (CharField), `permission` (CharField), `is_active` (BooleanField), `created_at` (DateTimeField), `deactivated_at` (DateTimeField).

| Relacja | Cel | Ustawienia |
| --- | --- | --- |
| `content_type` | `ContentType` | on_delete=models.CASCADE |
| `content_object` | `'content_type'` | — |
| `created_by` | `settings.AUTH_USER_MODEL` | on_delete=models.CASCADE; related_name='shared_item_links' |

Metody/properties: `save`, `deactivate`, `__str__`.

## Modele: dashboard

### `SavedTaskFilter`

Źródło: [dashboard/models.py](../dashboard/models.py).

Pola zadeklarowane tutaj: `owner` (ForeignKey), `workplace` (ForeignKey), `created_by` (ForeignKey), `name` (CharField), `description` (TextField), `query` (TextField), `visibility` (CharField), `shared_with` (ManyToManyField), `favorited_by` (ManyToManyField), `revision` (PositiveIntegerField), `created_at` (DateTimeField), `updated_at` (DateTimeField).

| Relacja | Cel | Ustawienia |
| --- | --- | --- |
| `owner` | `settings.AUTH_USER_MODEL` | on_delete=models.CASCADE; related_name='workspace_task_filters' |
| `workplace` | `'workplaces.Workplace'` | on_delete=models.CASCADE; related_name='task_filters' |
| `created_by` | `settings.AUTH_USER_MODEL` | on_delete=models.CASCADE; related_name='created_task_filters' |
| `shared_with` | `settings.AUTH_USER_MODEL` | related_name='shared_task_filters' |
| `favorited_by` | `settings.AUTH_USER_MODEL` | related_name='favorite_task_filters' |

Metody/properties: `__str__`.

### `Dashboard`

Źródło: [dashboard/models.py](../dashboard/models.py).

Pola zadeklarowane tutaj: `owner` (ForeignKey), `workplace` (ForeignKey), `created_by` (ForeignKey), `name` (CharField), `slug` (SlugField), `description` (TextField), `visibility` (CharField), `shared_with` (ManyToManyField), `favorited_by` (ManyToManyField), `layout` (CharField), `revision` (PositiveIntegerField), `is_default` (BooleanField), `created_at` (DateTimeField), `updated_at` (DateTimeField).

| Relacja | Cel | Ustawienia |
| --- | --- | --- |
| `owner` | `settings.AUTH_USER_MODEL` | on_delete=models.CASCADE; related_name='workspace_dashboards' |
| `workplace` | `'workplaces.Workplace'` | on_delete=models.CASCADE; related_name='dashboards' |
| `created_by` | `settings.AUTH_USER_MODEL` | on_delete=models.CASCADE; related_name='created_dashboards' |
| `shared_with` | `settings.AUTH_USER_MODEL` | related_name='shared_dashboards' |
| `favorited_by` | `settings.AUTH_USER_MODEL` | related_name='favorite_dashboards' |

Metody/properties: `save`, `column_count`, `__str__`.

### `DashboardGadget`

Źródło: [dashboard/models.py](../dashboard/models.py).

Pola zadeklarowane tutaj: `dashboard` (ForeignKey), `kind` (CharField), `title` (CharField), `space` (ForeignKey), `assignee` (CharField), `column` (PositiveSmallIntegerField), `position` (PositiveSmallIntegerField).

| Relacja | Cel | Ustawienia |
| --- | --- | --- |
| `dashboard` | `Dashboard` | on_delete=models.CASCADE; related_name='gadgets' |
| `space` | `'spaces.Space'` | on_delete=models.CASCADE; null=True |

Metody/properties: `label`.

### `ObjectFollow`

Źródło: [dashboard/models.py](../dashboard/models.py).

Pola zadeklarowane tutaj: `user` (ForeignKey), `task` (ForeignKey), `kanban` (ForeignKey), `task_project` (ForeignKey), `kanban_project` (ForeignKey), `created_at` (DateTimeField).

| Relacja | Cel | Ustawienia |
| --- | --- | --- |
| `user` | `settings.AUTH_USER_MODEL` | on_delete=models.CASCADE |
| `task` | `'tasks.Task'` | on_delete=models.CASCADE; null=True |
| `kanban` | `'kanban.Kanban'` | on_delete=models.CASCADE; null=True |
| `task_project` | `'tasks.TaskProject'` | on_delete=models.CASCADE; null=True |
| `kanban_project` | `'kanban.KanbanProject'` | on_delete=models.CASCADE; null=True |

### `ActivityInterest`

Źródło: [dashboard/models.py](../dashboard/models.py).

Pola zadeklarowane tutaj: `user` (ForeignKey), `task_activity` (ForeignKey), `kanban_activity` (ForeignKey), `mentioned` (BooleanField), `followed` (BooleanField).

| Relacja | Cel | Ustawienia |
| --- | --- | --- |
| `user` | `settings.AUTH_USER_MODEL` | on_delete=models.CASCADE |
| `task_activity` | `'tasks.TaskActivity'` | on_delete=models.CASCADE; null=True |
| `kanban_activity` | `'kanban.KanbanActivity'` | on_delete=models.CASCADE; null=True |

### `TaskReminder`

Źródło: [dashboard/models.py](../dashboard/models.py).

Pola zadeklarowane tutaj: `task` (ForeignKey), `recipient` (ForeignKey), `scheduled_at` (DateTimeField), `created_at` (DateTimeField).

| Relacja | Cel | Ustawienia |
| --- | --- | --- |
| `task` | `'tasks.Task'` | on_delete=models.CASCADE |
| `recipient` | `settings.AUTH_USER_MODEL` | on_delete=models.CASCADE |

### `NotificationState`

Źródło: [dashboard/models.py](../dashboard/models.py).

Pola zadeklarowane tutaj: `space_activity` (ForeignKey), `space_reminder` (ForeignKey), `user` (ForeignKey), `task_activity` (ForeignKey), `kanban_activity` (ForeignKey), `invitation` (ForeignKey), `section_invitation` (ForeignKey), `project_invitation` (ForeignKey), `reminder` (ForeignKey), `is_read` (BooleanField), `is_archived` (BooleanField), `is_deleted` (BooleanField).

| Relacja | Cel | Ustawienia |
| --- | --- | --- |
| `space_activity` | `'spaces.SpaceTaskActivity'` | on_delete=models.CASCADE; null=True |
| `space_reminder` | `'spaces.SpaceTaskReminder'` | on_delete=models.CASCADE; null=True |
| `user` | `settings.AUTH_USER_MODEL` | on_delete=models.CASCADE |
| `task_activity` | `'tasks.TaskActivity'` | on_delete=models.CASCADE; null=True |
| `kanban_activity` | `'kanban.KanbanActivity'` | on_delete=models.CASCADE; null=True |
| `invitation` | `'workplaces.WorkplaceInvitation'` | on_delete=models.CASCADE; null=True |
| `section_invitation` | `'tasks.TaskSectionInvitation'` | on_delete=models.CASCADE; null=True |
| `project_invitation` | `'tasks.TaskProjectInvitation'` | on_delete=models.CASCADE; null=True |
| `reminder` | `TaskReminder` | on_delete=models.CASCADE; null=True |

## Modele: planner

### `CalendarEvent`

Źródło: [planner/models.py](../planner/models.py).

Pola zadeklarowane tutaj: `user` (ForeignKey), `workplace` (ForeignKey), `title` (CharField), `description` (TextField), `start` (DateTimeField), `end` (DateTimeField), `all_day` (BooleanField), `color` (CharField), `created_at` (DateTimeField), `updated_at` (DateTimeField).

| Relacja | Cel | Ustawienia |
| --- | --- | --- |
| `user` | `settings.AUTH_USER_MODEL` | on_delete=models.CASCADE; related_name='calendar_events' |
| `workplace` | `'workplaces.Workplace'` | on_delete=models.CASCADE; related_name='calendar_events'; null=True |

Metody/properties: `__str__`.

## Modele: documents

### `DocumentLibrary`

Źródło: [documents/models.py](../documents/models.py).

Pola zadeklarowane tutaj: `name` (CharField), `color` (CharField), `description` (TextField), `photo` (FileField), `workplace` (ForeignKey), `owner` (ForeignKey), `created_at` (DateTimeField), `updated_at` (DateTimeField).

| Relacja | Cel | Ustawienia |
| --- | --- | --- |
| `workplace` | `'workplaces.Workplace'` | on_delete=models.CASCADE; related_name='document_libraries' |
| `owner` | `settings.AUTH_USER_MODEL` | on_delete=models.CASCADE; related_name='document_libraries' |

Metody/properties: `__str__`.

### `Folder`

Źródło: [documents/models.py](../documents/models.py).

Pola zadeklarowane tutaj: `name` (CharField), `color` (CharField), `library` (ForeignKey), `parent` (ForeignKey), `workplace` (ForeignKey), `owner` (ForeignKey), `is_starred` (BooleanField), `created_at` (DateTimeField).

| Relacja | Cel | Ustawienia |
| --- | --- | --- |
| `library` | `DocumentLibrary` | on_delete=models.RESTRICT; related_name='folders' |
| `parent` | `'self'` | on_delete=models.RESTRICT; related_name='children'; null=True |
| `workplace` | `'workplaces.Workplace'` | on_delete=models.CASCADE; related_name='document_folders' |
| `owner` | `settings.AUTH_USER_MODEL` | on_delete=models.CASCADE; related_name='document_folders' |

Metody/properties: `__str__`.

### `Document`

Źródło: [documents/models.py](../documents/models.py).

Pola zadeklarowane tutaj: `id` (UUIDField), `title` (CharField), `library` (ForeignKey), `description` (TextField), `file` (FileField), `filename` (CharField), `file_size` (PositiveBigIntegerField), `revision` (PositiveIntegerField), `office_key` (UUIDField), `office_save_error` (BooleanField), `folder` (ForeignKey), `workplace` (ForeignKey), `owner` (ForeignKey), `tags` (ManyToManyField), `is_starred` (BooleanField), `deleted_at` (DateTimeField), `created_at` (DateTimeField), `updated_at` (DateTimeField).

| Relacja | Cel | Ustawienia |
| --- | --- | --- |
| `library` | `DocumentLibrary` | on_delete=models.RESTRICT; related_name='documents' |
| `folder` | `Folder` | on_delete=models.RESTRICT; related_name='documents'; null=True |
| `workplace` | `'workplaces.Workplace'` | on_delete=models.CASCADE; related_name='documents' |
| `owner` | `settings.AUTH_USER_MODEL` | on_delete=models.CASCADE; related_name='documents' |
| `tags` | `'tasks.TaskTag'` | related_name='documents' |

Metody/properties: `extension`, `office_type`, `icon`, `__str__`.

### `WorkspaceDocumentFolder`

Źródło: [documents/models.py](../documents/models.py).

Pola zadeklarowane tutaj: `name` (CharField), `color` (CharField), `parent` (ForeignKey), `workplace` (ForeignKey), `owner` (ForeignKey), `is_starred` (BooleanField), `created_at` (DateTimeField).

| Relacja | Cel | Ustawienia |
| --- | --- | --- |
| `parent` | `'self'` | on_delete=models.RESTRICT; related_name='children'; null=True |
| `workplace` | `'workplaces.Workplace'` | on_delete=models.CASCADE; related_name='office_folders' |
| `owner` | `settings.AUTH_USER_MODEL` | on_delete=models.CASCADE; related_name='office_folders' |

Metody/properties: `__str__`.

### `WorkspaceDocument`

Źródło: [documents/models.py](../documents/models.py).

Pola zadeklarowane tutaj: `id` (UUIDField), `title` (CharField), `kind` (CharField), `content` (TextField), `is_template` (BooleanField), `is_pdf_form` (BooleanField), `revision` (PositiveIntegerField), `office_key` (UUIDField), `office_save_error` (BooleanField), `file` (FileField), `filename` (CharField), `file_size` (PositiveBigIntegerField), `folder` (ForeignKey), `workplace` (ForeignKey), `owner` (ForeignKey), `tags` (ManyToManyField), `is_starred` (BooleanField), `deleted_at` (DateTimeField), `created_at` (DateTimeField), `updated_at` (DateTimeField).

| Relacja | Cel | Ustawienia |
| --- | --- | --- |
| `folder` | `WorkspaceDocumentFolder` | on_delete=models.RESTRICT; related_name='documents'; null=True |
| `workplace` | `'workplaces.Workplace'` | on_delete=models.CASCADE; related_name='office_documents' |
| `owner` | `settings.AUTH_USER_MODEL` | on_delete=models.CASCADE; related_name='office_documents' |
| `tags` | `'tasks.TaskTag'` | related_name='office_documents' |

Metody/properties: `extension`, `office_type`, `has_full_editor`, `icon`, `__str__`.

### `OfficeSaveReceipt`

Źródło: [documents/models.py](../documents/models.py).

Pola zadeklarowane tutaj: `document` (ForeignKey), `digest` (CharField), `created_at` (DateTimeField).

| Relacja | Cel | Ustawienia |
| --- | --- | --- |
| `document` | `WorkspaceDocument` | on_delete=models.CASCADE; related_name='save_receipts' |

### `DriveOfficeSaveReceipt`

Źródło: [documents/models.py](../documents/models.py).

Pola zadeklarowane tutaj: `document` (ForeignKey), `digest` (CharField), `created_at` (DateTimeField).

| Relacja | Cel | Ustawienia |
| --- | --- | --- |
| `document` | `Document` | on_delete=models.CASCADE; related_name='save_receipts' |

### `DocumentVersion`

Źródło: [documents/models.py](../documents/models.py).

Pola zadeklarowane tutaj: `document` (ForeignKey), `drive_document` (ForeignKey), `revision` (PositiveIntegerField), `file` (FileField), `filename` (CharField), `file_size` (PositiveBigIntegerField), `is_pdf_form` (BooleanField), `saved_at` (DateTimeField), `archived_at` (DateTimeField).

| Relacja | Cel | Ustawienia |
| --- | --- | --- |
| `document` | `WorkspaceDocument` | on_delete=models.CASCADE; related_name='versions'; null=True |
| `drive_document` | `Document` | on_delete=models.CASCADE; related_name='versions'; null=True |

## Modele: resources

### `Resource`

Źródło: [resources/models.py](../resources/models.py).

Pola zadeklarowane tutaj: `owner` (ForeignKey), `workplace` (ForeignKey), `name` (CharField), `kind` (CharField), `inventory_number` (CharField), `serial_number` (CharField), `status` (CharField), `assigned_to` (ForeignKey), `location` (CharField), `purchased_on` (DateField), `expires_on` (DateField), `notes` (TextField), `created_by` (ForeignKey), `updated_by` (ForeignKey), `created_at` (DateTimeField), `updated_at` (DateTimeField).

| Relacja | Cel | Ustawienia |
| --- | --- | --- |
| `owner` | `settings.AUTH_USER_MODEL` | on_delete=models.CASCADE; related_name='owned_resources' |
| `workplace` | `'workplaces.Workplace'` | on_delete=models.CASCADE; related_name='resources' |
| `assigned_to` | `settings.AUTH_USER_MODEL` | on_delete=models.SET_NULL; related_name='assigned_resources'; null=True |
| `created_by` | `settings.AUTH_USER_MODEL` | on_delete=models.SET_NULL; related_name='created_resources'; null=True |
| `updated_by` | `settings.AUTH_USER_MODEL` | on_delete=models.SET_NULL; related_name='updated_resources'; null=True |

Metody/properties: `icon`, `__str__`.

## Modele: spaces

### `SpaceConfiguration`

Źródło: [spaces/models.py](../spaces/models.py).

Pola zadeklarowane tutaj: `workplace` (ForeignKey), `name` (CharField), `shared` (BooleanField), `settings` (JSONField).

| Relacja | Cel | Ustawienia |
| --- | --- | --- |
| `workplace` | `'workplaces.Workplace'` | on_delete=models.CASCADE |

Metody/properties: `__str__`.

### `Space`

Źródło: [spaces/models.py](../spaces/models.py).

Pola zadeklarowane tutaj: `project` (OneToOneField), `name` (CharField), `description` (TextField), `user` (ForeignKey), `responsible_user` (ForeignKey), `visibility` (CharField), `private_owner` (ForeignKey), `favorited_by` (ManyToManyField), `workplace` (ForeignKey), `key` (CharField), `slug` (SlugField), `kind` (CharField), `template` (CharField), `management` (CharField), `configuration` (ForeignKey), `next_number` (PositiveIntegerField), `avatar` (CharField), `avatar_photo` (FileField), `created_at` (DateTimeField).

| Relacja | Cel | Ustawienia |
| --- | --- | --- |
| `project` | `'tasks.TaskProject'` | on_delete=models.SET_NULL; related_name='space'; null=True |
| `user` | `settings.AUTH_USER_MODEL` | on_delete=models.CASCADE; related_name='owned_spaces' |
| `responsible_user` | `settings.AUTH_USER_MODEL` | on_delete=models.SET_NULL; related_name='responsible_spaces'; null=True |
| `private_owner` | `settings.AUTH_USER_MODEL` | on_delete=models.SET_NULL; related_name='private_spaces'; null=True |
| `favorited_by` | `settings.AUTH_USER_MODEL` | related_name='favorite_spaces' |
| `workplace` | `'workplaces.Workplace'` | on_delete=models.CASCADE |
| `configuration` | `SpaceConfiguration` | on_delete=models.RESTRICT; related_name='spaces' |

Metody/properties: `save`, `__str__`, `statuses`.

### `SpaceMembership`

Źródło: [spaces/models.py](../spaces/models.py).

Pola zadeklarowane tutaj: `space` (ForeignKey), `user` (ForeignKey), `role` (CharField).

| Relacja | Cel | Ustawienia |
| --- | --- | --- |
| `space` | `Space` | on_delete=models.CASCADE; related_name='memberships' |
| `user` | `settings.AUTH_USER_MODEL` | on_delete=models.CASCADE |

### `SpaceTask`

Źródło: [spaces/models.py](../spaces/models.py).

Pola zadeklarowane tutaj: `task_type` (CharField), `reminder_at` (DateTimeField), `space` (ForeignKey), `title` (CharField), `description` (TextField), `priority` (CharField), `status` (CharField), `is_completed` (BooleanField), `completion_date` (DateTimeField), `created_at` (DateTimeField), `created_by` (ForeignKey), `assignee` (ForeignKey), `due_at` (DateTimeField), `parent` (ForeignKey), `tags` (ManyToManyField), `favorited_by` (ManyToManyField), `visibility` (CharField), `private_owner` (ForeignKey).

| Relacja | Cel | Ustawienia |
| --- | --- | --- |
| `space` | `Space` | on_delete=models.CASCADE; related_name='tasks' |
| `created_by` | `settings.AUTH_USER_MODEL` | on_delete=models.SET_NULL; related_name='created_space_tasks'; null=True |
| `assignee` | `settings.AUTH_USER_MODEL` | on_delete=models.SET_NULL; related_name='assigned_space_tasks'; null=True |
| `parent` | `'self'` | on_delete=models.CASCADE; related_name='subtasks'; null=True |
| `tags` | `'tasks.TaskTag'` | related_name='space_tasks' |
| `favorited_by` | `settings.AUTH_USER_MODEL` | related_name='favorite_space_tasks' |
| `private_owner` | `settings.AUTH_USER_MODEL` | on_delete=models.SET_NULL; related_name='private_space_tasks'; null=True |

Metody/properties: `__str__`, `save`, `due_urgency`.

### `SpaceTaskMembership`

Źródło: [spaces/models.py](../spaces/models.py).

Pola zadeklarowane tutaj: `created_at` (DateTimeField), `task` (ForeignKey), `user` (ForeignKey), `role` (CharField).

| Relacja | Cel | Ustawienia |
| --- | --- | --- |
| `task` | `SpaceTask` | on_delete=models.CASCADE; related_name='memberships' |
| `user` | `settings.AUTH_USER_MODEL` | on_delete=models.CASCADE |

### `SpaceTaskActivity`

Źródło: [spaces/models.py](../spaces/models.py).

Pola zadeklarowane tutaj: `task` (ForeignKey), `actor` (ForeignKey), `kind` (CharField), `action` (CharField), `message` (TextField), `metadata` (JSONField), `created_at` (DateTimeField).

| Relacja | Cel | Ustawienia |
| --- | --- | --- |
| `task` | `SpaceTask` | on_delete=models.CASCADE; related_name='activities' |
| `actor` | `settings.AUTH_USER_MODEL` | on_delete=models.SET_NULL; null=True |

Metody/properties: `get_action_display`.

### `SpaceTaskFile`

Źródło: [spaces/models.py](../spaces/models.py).

Pola zadeklarowane tutaj: `task` (ForeignKey), `activity` (ForeignKey), `file` (FileField), `filename` (CharField), `file_size` (PositiveIntegerField), `legacy_storage` (BooleanField).

| Relacja | Cel | Ustawienia |
| --- | --- | --- |
| `task` | `SpaceTask` | on_delete=models.CASCADE; related_name='attachments' |
| `activity` | `SpaceTaskActivity` | on_delete=models.CASCADE; related_name='images'; null=True |

Metody/properties: `get_url`.

### `SpaceTaskReminder`

Źródło: [spaces/models.py](../spaces/models.py).

Pola zadeklarowane tutaj: `task` (ForeignKey), `recipient` (ForeignKey), `scheduled_at` (DateTimeField), `created_at` (DateTimeField).

| Relacja | Cel | Ustawienia |
| --- | --- | --- |
| `task` | `SpaceTask` | on_delete=models.CASCADE |
| `recipient` | `settings.AUTH_USER_MODEL` | on_delete=models.CASCADE |

### `SpaceTaskWorkLog`

Źródło: [spaces/models.py](../spaces/models.py).

Pola zadeklarowane tutaj: `task` (ForeignKey), `author` (ForeignKey), `started_at` (DateTimeField), `ended_at` (DateTimeField), `description` (TextField), `created_at` (DateTimeField), `updated_at` (DateTimeField).

| Relacja | Cel | Ustawienia |
| --- | --- | --- |
| `task` | `SpaceTask` | on_delete=models.CASCADE; related_name='work_logs' |
| `author` | `settings.AUTH_USER_MODEL` | on_delete=models.SET_NULL; null=True |

Metody/properties: `duration_minutes`.

### `Team`

Źródło: [spaces/models.py](../spaces/models.py).

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

Źródło: [spaces/models.py](../spaces/models.py).

Pola zadeklarowane tutaj: `team` (ForeignKey), `user` (ForeignKey), `role` (CharField).

| Relacja | Cel | Ustawienia |
| --- | --- | --- |
| `team` | `Team` | on_delete=models.CASCADE; related_name='memberships' |
| `user` | `settings.AUTH_USER_MODEL` | on_delete=models.CASCADE |

### `Sprint`

Źródło: [spaces/models.py](../spaces/models.py).

Pola zadeklarowane tutaj: `space` (ForeignKey), `name` (CharField), `goal` (TextField), `start_on` (DateField), `end_on` (DateField), `state` (CharField), `completed_at` (DateTimeField), `result` (JSONField).

| Relacja | Cel | Ustawienia |
| --- | --- | --- |
| `space` | `Space` | on_delete=models.CASCADE; related_name='sprints' |

Metody/properties: `__str__`.

### `WorkItem`

Źródło: [spaces/models.py](../spaces/models.py).

Pola zadeklarowane tutaj: `task` (OneToOneField), `legacy_task` (OneToOneField), `space` (ForeignKey), `key` (CharField), `number` (PositiveIntegerField), `status` (CharField), `work_type` (CharField), `rank` (PositiveIntegerField), `in_backlog` (BooleanField), `team` (ForeignKey), `sprint` (ForeignKey), `epic` (ForeignKey), `points` (PositiveIntegerField), `start_on` (DateField), `custom_values` (JSONField).

| Relacja | Cel | Ustawienia |
| --- | --- | --- |
| `task` | `SpaceTask` | on_delete=models.CASCADE; related_name='work_item'; null=True |
| `legacy_task` | `'tasks.Task'` | on_delete=models.SET_NULL; related_name='work_item'; null=True |
| `space` | `Space` | on_delete=models.CASCADE; related_name='items'; null=True |
| `team` | `Team` | on_delete=models.SET_NULL; related_name='items'; null=True |
| `sprint` | `Sprint` | on_delete=models.SET_NULL; related_name='items'; null=True |
| `epic` | `'self'` | on_delete=models.SET_NULL; related_name='epic_items'; null=True |

Metody/properties: `save`, `get_work_type_display`, `type_icon`.

### `LegacyKanbanLink`

Źródło: [spaces/models.py](../spaces/models.py).

Pola zadeklarowane tutaj: `kind` (CharField), `source_id` (PositiveBigIntegerField), `target_id` (PositiveBigIntegerField), `space` (ForeignKey).

| Relacja | Cel | Ustawienia |
| --- | --- | --- |
| `space` | `Space` | on_delete=models.SET_NULL; null=True |

## 3. Formularze

Wypisane są deklaracje klas, także bazowe klasy i widgety.

### core

Źródło: [core/forms.py](../core/forms.py).


### accounts

Źródło: [accounts/forms.py](../accounts/forms.py).

- `UserRegistrationForm` — Meta.fields: `('first_name', 'middle_name', 'last_name', 'email')`
- `UserProfileForm` — Meta.fields: `('avatar', 'profile_photo', 'first_name', 'middle_name', 'last_name', 'email', 'username', 'phone_number', 'job_title', 'bio', 'presence_status')`

### workplaces

Źródło: [workplaces/forms.py](../workplaces/forms.py).

- `WorkplaceForm` — Meta.fields: `['avatar', 'workplace_photo', 'name', 'description']`

### tasks

Źródło: [tasks/forms.py](../tasks/forms.py).

- `LenientModelChoiceField`
- `DateTimeLocalInput`
- `MultipleFileInput`
- `ProjectVisibilitySelect`
- `TaskAccessForm`
- `TaskForm` — Meta.fields: `['title', 'visibility', 'parent', 'section', 'tags', 'description', 'task_type', 'assignee', 'priority', 'status', 'due_at', 'reminder_at']`
- `TaskWorkLogForm`
- `TaskProjectBaseForm`
- `TaskProjectTemplateNameForm` — Meta.fields: `('template_name',)`
- `TaskProjectForm` — Meta.fields: `['name', 'visibility', 'template', 'code', 'section_title', 'section_code', 'description', 'company', 'responsible_user', 'status', 'stage', 'health', 'priority', 'start_at', 'due_at', 'source']`
- `TaskProjectRenameForm` — Meta.fields: `['name', 'visibility', 'code', 'description', 'company', 'responsible_user', 'status', 'stage', 'health', 'priority', 'start_at', 'due_at', 'source']`
- `TaskSectionAccessForm`
- `TaskSectionForm` — Meta.fields: `['visibility', 'title', 'code', 'description', 'kind', 'status', 'owner', 'priority', 'due_at', 'wip_limit']`
- `TaskSectionRenameForm` — Meta.fields: `['visibility', 'title', 'code', 'description', 'kind', 'status', 'owner', 'priority', 'due_at', 'wip_limit']`
- `TaskTagForm` — Meta.fields: `['name', 'description', 'category', 'color', 'icon', 'priority', 'scope', 'owner_label', 'status', 'usage_notes', 'automation_rules', 'related_tags']`
- `QuickTaskForm` — Meta.fields: `['title']`
- `TaskModalForm` — Meta.fields: `['title', 'visibility', 'section', 'tags', 'description', 'task_type', 'assignee', 'priority', 'status', 'due_at', 'reminder_at']`
- `SubTaskModalForm` — Meta.fields: `['title', 'visibility', 'description', 'status', 'due_at']`

### kanban

Źródło: [kanban/forms.py](../kanban/forms.py).

- `LenientModelChoiceField`
- `TwoDigitNumberInput`
- `DynamicStatusFormMixin`
- `MultipleFileInput`
- `KanbanForm` — Meta.fields: `['title', 'parent', 'section', 'tags', 'description', 'priority', 'status', 'due_at', 'time_spent_hours', 'time_spent_minutes']`
- `KanbanAccessForm`
- `KanbanProjectBaseForm`
- `KanbanProjectForm` — Meta.fields: `['visibility', 'name', 'section_title', 'description', 'company', 'responsible_user', 'status', 'stage', 'health', 'priority', 'start_at', 'due_at', 'budget_amount', 'currency', 'source']`
- `KanbanProjectRenameForm` — Meta.fields: `['visibility', 'name', 'description', 'company', 'responsible_user', 'status', 'stage', 'health', 'priority', 'start_at', 'due_at', 'budget_amount', 'currency', 'source']`
- `KanbanSectionForm` — Meta.fields: `['visibility', 'title', 'description']`
- `KanbanSectionRenameForm` — Meta.fields: `['visibility', 'title', 'description']`
- `KanbanTagForm` — Meta.fields: `['name', 'description', 'category', 'color', 'icon', 'priority', 'scope', 'owner_label', 'status', 'usage_notes', 'automation_rules', 'related_tags']`
- `KanbanBoardColumnForm` — Meta.fields: `['title']`
- `QuickKanbanForm` — Meta.fields: `['title']`
- `KanbanModalForm` — Meta.fields: `['title', 'section', 'tags', 'description', 'priority', 'status', 'due_at']`
- `SubKanbanModalForm` — Meta.fields: `['title', 'description', 'status']`

### contacts

Źródło: [contacts/forms.py](../contacts/forms.py).

- `ContactForm` — Meta.fields: `['first_name', 'middle_name', 'last_name', 'company', 'company_record', 'role', 'email', 'phone', 'source', 'last_contacted_at', 'notes']`
- `ContactModalForm`
- `CompanyForm` — Meta.fields: `['company_photo', 'name', 'website', 'email', 'phone', 'address', 'notes']`
- `CompanyModalForm`

### planner

Źródło: [planner/forms.py](../planner/forms.py).

- `CalendarEventForm` — Meta.fields: `['title', 'description', 'start', 'end', 'all_day', 'color']`

### documents

Źródło: [documents/forms.py](../documents/forms.py).

- `MultipleFileInput`
- `MultipleFileField`
- `UploadForm`
- `IconColorForm`
- `LibraryForm` — Meta.fields: `['name', 'color', 'description']`
- `FolderForm` — Meta.fields: `['name', 'color']`
- `DocumentForm` — Meta.fields: `['title', 'description', 'folder']`

### resources

Źródło: [resources/forms.py](../resources/forms.py).

- `ResourceForm` — Meta.fields: `['name', 'kind', 'inventory_number', 'serial_number', 'status', 'assigned_to', 'location', 'purchased_on', 'expires_on', 'notes']`

### spaces

Źródło: [spaces/forms.py](../spaces/forms.py).

- `StyledForm`
- `SpaceAvatarForm`
- `SpaceForm`
- `ItemForm`
- `DetailForm`
- `SubtaskForm`
- `WorkLogForm`
- `SprintForm`
- `SprintCloseForm`
- `TeamForm`
- `MemberForm`
- `StatusForm`
- `TypeForm`
- `CustomFieldForm`

## 4. Routing

Ścieżki modułowe są względne wobec include'a w głównym routingu.

### ancore/urls.py

Źródło: [ancore/urls.py](../ancore/urls.py).

| Ścieżka / regex | Widok / include | Nazwa |
| --- | --- | --- |
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
| `'^workplaces/[-a-zA-Z0-9_]+/tasks/'` | `include((tasks_urls.urlpatterns, 'workplace_tasks'), namespace='workplace_tasks')` | — |
| `'^workplaces/[-a-zA-Z0-9_]+/kanban/'` | `include((kanban_urls.urlpatterns, 'workplace_kanban'), namespace='workplace_kanban')` | — |
| `'^workplaces/[-a-zA-Z0-9_]+/calendar/'` | `include((planner_urls.urlpatterns, 'workplace_planner'), namespace='workplace_planner')` | — |
| `'^workplaces/[-a-zA-Z0-9_]+/documents/'` | `include((documents_urls.urlpatterns, 'workplace_documents'), namespace='workplace_documents')` | — |
| `'^workplaces/[-a-zA-Z0-9_]+/office/'` | `include((office_urls.urlpatterns, 'workplace_office'), namespace='workplace_office')` | — |
| `'workplaces/'` | `include('workplaces.urls')` | — |
| `'^workplaces/[-a-zA-Z0-9_]+/resources/'` | `include((resources_urls.urlpatterns, 'workplace_resources'), namespace='workplace_resources')` | — |
| `'resources/'` | `include('resources.urls')` | — |
| `'documents/'` | `include('documents.urls')` | — |
| `'office/'` | `include('documents.workspace_urls')` | — |
| `'tasks/'` | `include('tasks.urls')` | — |
| `'kanban/'` | `include('kanban.urls')` | — |
| `'calendar/'` | `include('planner.urls')` | — |

### accounts/urls.py

Źródło: [accounts/urls.py](../accounts/urls.py).

| Ścieżka / regex | Widok / include | Nazwa |
| --- | --- | --- |
| `'login/'` | `views.AccountLoginView.as_view()` | 'login' |
| `'logout/'` | `views.AccountLogoutView.as_view()` | 'logout' |
| `'register/'` | `views.register` | 'register' |
| `'profile/'` | `views.profile` | 'profile' |
| `'profile/status/'` | `views.update_presence_status` | 'update_presence_status' |
| `'profile/add-account/'` | `views.add_account` | 'add_account' |
| `'profile/switch-account/'` | `views.switch_account` | 'switch_account' |
| `'profile/remove-account/'` | `views.remove_account` | 'remove_account' |
| `'presence/ping/'` | `views.presence_ping` | 'presence_ping' |

### workplaces/urls.py

Źródło: [workplaces/urls.py](../workplaces/urls.py).

| Ścieżka / regex | Widok / include | Nazwa |
| --- | --- | --- |
| `'<int:workplace_id>/team/candidates/'` | `team_views.invitation_candidates` | 'invitation-candidates' |
| `'<int:workplace_id>/team/'` | `team_views.team` | 'team' |
| `'<int:workplace_id>/team/<int:member_id>/'` | `team_views.member_update` | 'member-update' |
| `'<int:workplace_id>/invitations/<int:invitation_id>/cancel/'` | `team_views.invitation_cancel` | 'invitation-cancel' |
| `'invitations/<int:invitation_id>/respond/'` | `team_views.invitation_response` | 'invitation-response' |
| `''` | `views.workplaces` | 'workplaces' |
| `'<int:workplace_id>/switch/'` | `views.switch_workplace` | 'switch' |
| `'<int:workplace_id>/favorites/toggle/'` | `views.toggle_sidebar_favorite` | 'toggle-sidebar-favorite' |
| `'<int:workplace_id>/favorites/reorder/'` | `views.reorder_sidebar_favorites` | 'reorder-sidebar-favorites' |
| `'<int:workplace_id>/settings/'` | `views.update_workplace` | 'update' |
| `'<int:workplace_id>/delete/'` | `views.delete_workplace` | 'delete' |
| `'<slug:workplace_slug>/'` | `views.workplace_home` | 'workplace-home' |

### tasks/urls.py

Źródło: [tasks/urls.py](../tasks/urls.py).

| Ścieżka / regex | Widok / include | Nazwa |
| --- | --- | --- |
| `''` | `retired_tasks` | 'tasks' |
| `'groups/<int:section_id>/'` | `retired_tasks` | 'task_group' |
| `'view-task/<int:task_id>/'` | `retired_tasks` | 'view-task' |
| `'view-subtask/<int:task_id>/'` | `retired_tasks` | 'view-subtask' |
| `'attachments/<int:attachment_id>/download/'` | `retired_tasks` | 'download_attachment' |
| `'comment-images/<int:image_id>/'` | `retired_tasks` | 'comment_image' |

### kanban/urls.py

Źródło: [kanban/urls.py](../kanban/urls.py).

| Ścieżka / regex | Widok / include | Nazwa |
| --- | --- | --- |
| `''` | `retired_kanban` | 'tasks' |
| `'groups/<int:section_id>/'` | `retired_kanban` | 'task_group' |
| `'view-task/<int:task_id>/'` | `retired_kanban` | 'view-task' |
| `'view-subtask/<int:task_id>/'` | `retired_kanban` | 'view-subtask' |
| `'attachments/<int:attachment_id>/download/'` | `retired_kanban` | 'download_attachment' |
| `'comment-images/<int:image_id>/'` | `retired_kanban` | 'comment_image' |

### contacts/urls.py

Źródło: [contacts/urls.py](../contacts/urls.py).

| Ścieżka / regex | Widok / include | Nazwa |
| --- | --- | --- |

### dashboard/urls.py

Źródło: [dashboard/urls.py](../dashboard/urls.py).

| Ścieżka / regex | Widok / include | Nazwa |
| --- | --- | --- |
| `'for-you/'` | `views.for_you` | 'for_you' |
| `'^workplaces/[-a-zA-Z0-9_]+/for-you/$'` | `views.for_you` | 'workplace_for_you' |
| `'global-search/'` | `views.global_search` | 'global_search' |
| `'settings/'` | `views.settings` | 'settings' |
| `'notifications/'` | `views.notifications` | 'notifications' |
| `'notifications/action/'` | `views.notification_action` | 'notification_action' |
| `''` | `views.home` | 'home' |

### planner/urls.py

Źródło: [planner/urls.py](../planner/urls.py).

| Ścieżka / regex | Widok / include | Nazwa |
| --- | --- | --- |
| `''` | `views.index` | 'index' |
| `'events/'` | `views.events_list` | 'events' |
| `'events/create/'` | `views.create_event` | 'create_event' |
| `'events/<int:event_id>/update/'` | `views.update_event` | 'update_event' |
| `'events/<int:event_id>/delete/'` | `views.delete_event` | 'delete_event' |

### documents/urls.py

Źródło: [documents/urls.py](../documents/urls.py).

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

### resources/urls.py

Źródło: [resources/urls.py](../resources/urls.py).

| Ścieżka / regex | Widok / include | Nazwa |
| --- | --- | --- |
| `''` | `views.index` | 'index' |
| `'create/'` | `views.edit` | 'create' |
| `'<int:pk>/edit/'` | `views.edit` | 'edit' |
| `'<int:pk>/delete/'` | `views.delete` | 'delete' |

### spaces/urls.py

Źródło: [spaces/urls.py](../spaces/urls.py).

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
| `'space/<slug:space_pk>/tasks/<slug:key>/'` | `task_views.detail` | 'task_detail' |
| `'space/<slug:space_pk>/tasks/<slug:key>/edit/'` | `views.item_edit` | 'task_edit' |
| `'space/<slug:space_pk>/tasks/<slug:key>/action/'` | `views.item_action` | 'task_action' |
| `'space/<slug:space_pk>/tasks/<slug:key>/team/'` | `task_team.team` | 'task_team' |
| `'space/<slug:space_pk>/tasks/<slug:key>/team/candidates/'` | `task_team.candidates` | 'task_candidates' |
| `'space/<slug:space_pk>/tasks/<slug:key>/members/'` | `task_views.members` | 'task_members' |
| `'space/<slug:space_pk>/tasks/<slug:key>/files/<int:file_pk>/'` | `task_views.download` | 'task_file' |
| `'space/<slug:pk>/edit/'` | `views.edit` | 'edit' |
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
| `'space/<slug:pk>/members/<int:member_pk>/remove/'` | `views.remove_member` | 'remove_member' |
| `'space/<slug:pk>/configuration/'` | `views.configuration` | 'configuration' |
| `'spaces/<int:pk>/'` | `views.detail` | 'detail' |
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

- [ancore/__init__.py](../ancore/__init__.py)
- [ancore/asgi.py](../ancore/asgi.py)
- [ancore/settings.py](../ancore/settings.py) — `env_list`, `env_bool`, `env_int`
- [ancore/urls.py](../ancore/urls.py)
- [ancore/wsgi.py](../ancore/wsgi.py)

### core

- [core/__init__.py](../core/__init__.py)
- [core/admin.py](../core/admin.py)
- [core/apps.py](../core/apps.py) — `CoreConfig`
- [core/avatars.py](../core/avatars.py) — `preset_avatar`
- [core/comment_images.py](../core/comment_images.py) — `comment_image_storage`, `comment_image_path`, `AttachmentPresentation`, `CommentImage`, `delete_comment_image_file`, `save_comment`, `comment_image_response`
- [core/forms.py](../core/forms.py)
- [core/media.py](../core/media.py) — `public_media`
- [core/models.py](../core/models.py)
- [core/task_files.py](../core/task_files.py) — `delete_after_commit`
- [core/task_numbering.py](../core/task_numbering.py) — `lock_task_numbers`, `renumber_tasks`
- [core/task_requests.py](../core/task_requests.py) — `task_detail_lookup`, `task_primary_keys`
- [core/upload_validation.py](../core/upload_validation.py) — `validate_image_bytes`, `validate_image_crop`, `validate_image_upload`, `validate_attachment_upload`, `validate_comment_attachments`, `attachment_download_response`
- [core/views/__init__.py](../core/views/__init__.py)
- [core/widgets.py](../core/widgets.py) — `VisualSelect`, `VisualSelectMultiple`
- [core/work_logs.py](../core/work_logs.py) — `DateTimeLocalInput`, `TimeLogForm`

### accounts

- [accounts/__init__.py](../accounts/__init__.py)
- [accounts/admin.py](../accounts/admin.py) — `CustomUserAdmin`
- [accounts/apps.py](../accounts/apps.py) — `AccountsConfig`
- [accounts/avatar.py](../accounts/avatar.py) — `avatar_color_seed`, `avatar_color_style`, `avatar_color_style_from_seed`, `avatar_color_class`, `account_avatar`
- [accounts/avatar_presets.py](../accounts/avatar_presets.py) — `preset_avatar`
- [accounts/backends.py](../accounts/backends.py) — `EmailBackend`
- [accounts/context_processors.py](../accounts/context_processors.py) — `current_account_avatar`
- [accounts/forms.py](../accounts/forms.py) — `UserRegistrationForm`, `UserProfileForm`
- [accounts/middleware.py](../accounts/middleware.py) — `UserPresenceMiddleware`
- [accounts/models.py](../accounts/models.py) — `User`, `normalize_public_username`, `default_public_username`, `unique_public_username`
- [accounts/presence.py](../accounts/presence.py) — `idle_seconds`, `heartbeat_seconds`, `write_throttle_seconds`, `mark_user_seen`, `mark_user_inactive`, `sync_stale_presence_statuses`
- [accounts/templatetags/__init__.py](../accounts/templatetags/__init__.py)
- [accounts/templatetags/account_avatar.py](../accounts/templatetags/account_avatar.py) — `user_avatar`
- [accounts/urls.py](../accounts/urls.py)
- [accounts/views.py](../accounts/views.py) — `AccountLoginView`, `AccountLogoutView`, `register`, `profile`, `update_presence_status`, `add_account`, `switch_account`, `remove_account`, `presence_ping`
- [accounts/widgets.py](../accounts/widgets.py) — `UserSelect`, `UserChoiceField`, `UserSelectMultiple`

### workplaces

- [workplaces/__init__.py](../workplaces/__init__.py)
- [workplaces/admin.py](../workplaces/admin.py) — `WorkplaceMembershipInline`, `WorkplaceAdmin`, `WorkplaceMembershipAdmin`, `SidebarFavoriteAdmin`
- [workplaces/apps.py](../workplaces/apps.py) — `WorkplacesConfig`
- [workplaces/context_processors.py](../workplaces/context_processors.py) — `current_workplace`
- [workplaces/forms.py](../workplaces/forms.py) — `WorkplaceForm`
- [workplaces/middleware.py](../workplaces/middleware.py) — `ActiveWorkplaceMiddleware`
- [workplaces/models.py](../workplaces/models.py) — `generate_workplace_code`, `Workplace`, `WorkplaceMembership`, `invitation_expiry`, `WorkplaceInvitation`, `SidebarFavorite`, `create_workplace_for_user`
- [workplaces/navigation.py](../workplaces/navigation.py) — `sidebar_favorite_catalog`, `sidebar_favorite_is_active`, `sidebar_favorites_for_request`
- [workplaces/services.py](../workplaces/services.py) — `workplace_management_url`, `pending_invitations_for_user`, `workplaces_for_user`, `workplace_role`, `can_manage_team`, `workspace_owner`, `workplace_people`, `ensure_default_workplace`, `set_active_workplace`, `backfill_legacy_records_for_workplace`, `enable_workspace_url_scope`, `workspace_url_scope_enabled`, `scoped_workplace_app_path`, `legacy_app_path_to_scoped`, `get_active_workplace`
- [workplaces/team_views.py](../workplaces/team_views.py) — `TeamRoleSelect`, `InvitationForm`, `invitation_candidates`, `team`, `team_context`, `invitation_response`, `member_update`, `invitation_cancel`
- [workplaces/templatetags/__init__.py](../workplaces/templatetags/__init__.py)
- [workplaces/templatetags/sidebar_favorites.py](../workplaces/templatetags/sidebar_favorites.py) — `sidebar_favorite_toggle`
- [workplaces/templatetags/workplace_avatar.py](../workplaces/templatetags/workplace_avatar.py) — `workplace_avatar_seed`, `workplace_avatar`
- [workplaces/urls.py](../workplaces/urls.py)
- [workplaces/views.py](../workplaces/views.py) — `workplaces`, `render_workplaces`, `switch_workplace`, `toggle_sidebar_favorite`, `reorder_sidebar_favorites`, `workplace_home`, `update_workplace`, `delete_workplace`

### tasks

- [tasks/__init__.py](../tasks/__init__.py)
- [tasks/access.py](../tasks/access.py) — `task_tree_ids`, `require_deletable_tasks`, `editable_to`, `require_editable`, `visible_to`
- [tasks/admin.py](../tasks/admin.py)
- [tasks/apps.py](../tasks/apps.py) — `TasksConfig`
- [tasks/directory.py](../tasks/directory.py) — `directory_tab`, `directory_queryset`, `directory_tabs`, `decorate_favorites`
- [tasks/forms.py](../tasks/forms.py) — `LenientModelChoiceField`, `DateTimeLocalInput`, `MultipleFileInput`, `ProjectVisibilitySelect`, `TaskAccessForm`, `TaskForm`, `TaskWorkLogForm`, `TaskProjectBaseForm`, `TaskProjectTemplateNameForm`, `TaskProjectForm`, `TaskProjectRenameForm`, `TaskSectionAccessForm`, `TaskSectionForm`, `TaskSectionRenameForm`, `TaskTagForm`, `QuickTaskForm`, `TaskModalForm`, `SubTaskModalForm`
- [tasks/hierarchy.py](../tasks/hierarchy.py) — `save_task_edit`
- [tasks/models.py](../tasks/models.py) — `format_base36`, `parse_hierarchy_code_number`, `TaskProject`, `TaskProjectMembership`, `TaskProjectInvitation`, `TaskProjectTemplate`, `TaskProjectNote`, `TaskSection`, `TaskSectionMembership`, `TaskSectionInvitation`, `TaskSectionNote`, `TaskTag`, `TaskTagNote`, `Task`, `TaskMembership`, `TaskWorkLog`, `TaskAttachment`, `TaskActivity`, `TaskCommentImage`, `auto_delete_file_on_delete`, `create_task_activity_on_create`
- [tasks/project_template_forms.py](../tasks/project_template_forms.py) — `style_fields`, `TemplateDetailsForm`, `TemplateSectionForm`, `TemplateTaskForm`
- [tasks/project_templates.py](../tasks/project_templates.py) — `template_descendants`, `update_template_item`, `delete_template_item`, `save_project_template`, `populate_project_from_template`
- [tasks/sharing.py](../tasks/sharing.py) — `share_candidates`, `project_role`, `project_access_data`, `section_candidates`, `section_role`, `section_access_data`, `task_candidates`, `task_role`
- [tasks/sharing_signals.py](../tasks/sharing_signals.py) — `revoke_project_shares`, `membership_deleted`, `membership_disabled`, `project_member_deleted`, `section_member_deleted`, `task_member_deleted`
- [tasks/tagging.py](../tasks/tagging.py) — `tags_in_scope`, `visible_tags`, `form_tags`, `tag_action`
- [tasks/urls.py](../tasks/urls.py) — `retired_tasks`
- [tasks/views/__init__.py](../tasks/views/__init__.py)
- [tasks/views/directory.py](../tasks/views/directory.py) — `directory_favorite`
- [tasks/views/project_team.py](../tasks/views/project_team.py) — `ProjectShareForm`, `team_payload`, `project_team`, `project_candidates`
- [tasks/views/project_templates.py](../tasks/views/project_templates.py) — `project_templates`, `edit_project_template`
- [tasks/views/section_team.py](../tasks/views/section_team.py) — `SectionShareForm`, `team_payload`, `section_team`, `section_candidates`
- [tasks/views/task_team.py](../tasks/views/task_team.py) — `TaskShareForm`, `team_payload`, `task_team`, `task_candidates`
- [tasks/views/tasks.py](../tasks/views/tasks.py) — `tasks`, `task_group`, `create_share_link`, `revoke_share_link`, `accept_share_link`, `update_task_status`, `delete_task`, `delete_attachment`, `download_attachment`, `delete_tasks`, `bulk_update_status`, `view_task`, `view_subtask`, `comment_image`
- [tasks/views.py](../tasks/views.py)

### kanban

- [kanban/__init__.py](../kanban/__init__.py)
- [kanban/access.py](../kanban/access.py) — `card_tree_ids`, `visible_to`, `editable_to`, `require_editable`, `require_deletable`
- [kanban/admin.py](../kanban/admin.py)
- [kanban/apps.py](../kanban/apps.py) — `KanbanConfig`
- [kanban/directory.py](../kanban/directory.py) — `directory_tab`, `directory_queryset`, `decorate_favorites`
- [kanban/forms.py](../kanban/forms.py) — `LenientModelChoiceField`, `TwoDigitNumberInput`, `board_column_status_choices`, `DynamicStatusFormMixin`, `MultipleFileInput`, `KanbanForm`, `KanbanAccessForm`, `KanbanProjectBaseForm`, `KanbanProjectForm`, `KanbanProjectRenameForm`, `KanbanSectionForm`, `KanbanSectionRenameForm`, `KanbanTagForm`, `KanbanBoardColumnForm`, `QuickKanbanForm`, `KanbanModalForm`, `SubKanbanModalForm`
- [kanban/models.py](../kanban/models.py) — `KanbanProject`, `KanbanProjectNote`, `KanbanSection`, `KanbanBoardColumn`, `Kanban`, `KanbanAttachment`, `KanbanActivity`, `KanbanCommentImage`, `auto_delete_file_on_delete`, `create_task_activity_on_create`, `KanbanProjectMembership`, `KanbanSectionMembership`
- [kanban/sharing.py](../kanban/sharing.py) — `share_candidates`, `project_role`, `project_access_data`, `section_candidates`, `section_role`, `section_access_data`
- [kanban/sharing_signals.py](../kanban/sharing_signals.py) — `revoke_workspace_shares`, `workspace_member_deleted`, `workspace_member_disabled`, `project_member_deleted`
- [kanban/urls.py](../kanban/urls.py) — `retired_kanban`
- [kanban/views/__init__.py](../kanban/views/__init__.py)
- [kanban/views/directory.py](../kanban/views/directory.py) — `directory_favorite`
- [kanban/views/project_team.py](../kanban/views/project_team.py) — `ProjectShareForm`, `team_payload`, `project_team`, `project_candidates`
- [kanban/views/section_team.py](../kanban/views/section_team.py) — `SectionShareForm`, `team_payload`, `section_team`, `section_candidates`
- [kanban/views/tasks.py](../kanban/views/tasks.py) — `tasks`, `task_group`, `reorder_board_columns`, `update_task_status`, `delete_task`, `delete_attachment`, `download_attachment`, `delete_tasks`, `bulk_update_status`, `view_task`, `view_subtask`, `comment_image`

### contacts

- [contacts/__init__.py](../contacts/__init__.py)
- [contacts/admin.py](../contacts/admin.py)
- [contacts/apps.py](../contacts/apps.py) — `ContactsConfig`
- [contacts/forms.py](../contacts/forms.py) — `ContactForm`, `ContactModalForm`, `CompanyForm`, `CompanyModalForm`
- [contacts/models.py](../contacts/models.py) — `Company`, `CompanyMembership`, `Contact`, `UserContact`, `ContactActivity`, `SharedItem`, `SharedItemLink`
- [contacts/templatetags/__init__.py](../contacts/templatetags/__init__.py)
- [contacts/templatetags/company_avatar.py](../contacts/templatetags/company_avatar.py) — `company_avatar_seed`, `company_avatar`
- [contacts/urls.py](../contacts/urls.py)
- [contacts/views.py](../contacts/views.py) — `lookup_ancore_login`, `contacts`, `guest_contacts`, `view_contact`, `edit_contact`, `delete_contact`, `user_directory`, `add_user_contact`, `companies`, `view_company`, `edit_company`, `delete_company`

### dashboard

- [dashboard/__init__.py](../dashboard/__init__.py)
- [dashboard/admin.py](../dashboard/admin.py)
- [dashboard/apps.py](../dashboard/apps.py) — `DashboardConfig`
- [dashboard/collaboration.py](../dashboard/collaboration.py) — `mention_handle`, `mention_label`, `mention_choices`, `comment_mention_metadata`, `mention_people`, `follow_context`, `follow_object`, `deliver_activity_interest`
- [dashboard/filter_forms.py](../dashboard/filter_forms.py) — `BasicTaskSearchForm`, `SavedTaskFilterForm`
- [dashboard/filter_search.py](../dashboard/filter_search.py) — `QueryError`, `quote`, `SearchQuery`, `Parser`, `parse_query`, `date_value`, `Compiler`, `apply_query`, `basic_query`
- [dashboard/filter_urls.py](../dashboard/filter_urls.py)
- [dashboard/filter_views.py](../dashboard/filter_views.py) — `get_filter`, `catalog_context`, `search_context`, `index`, `manage`, `search`, `lookup`, `mutation_response`, `return_url`, `edit`, `save_query`, `favorite`, `delete`
- [dashboard/filters.py](../dashboard/filters.py) — `filter_url`, `visible_filters`, `decorate_filter`, `sidebar_filters`
- [dashboard/for_you.py](../dashboard/for_you.py) — `for_you_context`
- [dashboard/identifiers.py](../dashboard/identifiers.py) — `DashboardSlugConverter`, `unique_dashboard_slug`
- [dashboard/models.py](../dashboard/models.py) — `SavedTaskFilter`, `Dashboard`, `DashboardGadget`, `ObjectFollow`, `ActivityInterest`, `TaskReminder`, `NotificationState`
- [dashboard/notification_service.py](../dashboard/notification_service.py) — `notification_filters`, `notification_sources`, `filtered_sources`, `notification_summary`, `notification_page`, `change_notification_state`
- [dashboard/overview.py](../dashboard/overview.py) — `dashboard_overview`
- [dashboard/pulpit_forms.py](../dashboard/pulpit_forms.py) — `style_fields`, `DashboardVisibilitySelect`, `DashboardLayoutSelect`, `DashboardAccessForm`, `DashboardForm`, `DashboardSettingsForm`, `GadgetKindSelect`, `GadgetForm`
- [dashboard/pulpit_navigation.py](../dashboard/pulpit_navigation.py) — `sidebar_dashboards`
- [dashboard/pulpit_urls.py](../dashboard/pulpit_urls.py)
- [dashboard/pulpit_views.py](../dashboard/pulpit_views.py) — `get_dashboard`, `index_context`, `index`, `search`, `management_url`, `management_context`, `manage`, `detail`, `default`, `editor_navigation_context`, `editor_context`, `gadgets`, `form_response`, `saved_response`, `edit`, `access`, `delete`, `favorite`, `gadget_edit`, `gadget_delete`, `gadget_quick_add`, `arrange`
- [dashboard/pulpits.py](../dashboard/pulpits.py) — `app_url`, `visible_dashboards`, `default_dashboard`, `dashboard_url`, `decorate_dashboard`, `decorate_gadget`, `gadget_data`, `detail_context`
- [dashboard/recent.py](../dashboard/recent.py) — `remember_view`, `recent_views`
- [dashboard/reminders.py](../dashboard/reminders.py) — `reminders_for_user`, `space_reminders_for_user`
- [dashboard/urls.py](../dashboard/urls.py)
- [dashboard/views.py](../dashboard/views.py) — `global_search`, `settings`, `for_you`, `home`, `notifications`, `notification_action`

### planner

- [planner/__init__.py](../planner/__init__.py)
- [planner/admin.py](../planner/admin.py) — `CalendarEventAdmin`
- [planner/apps.py](../planner/apps.py) — `PlannerConfig`
- [planner/forms.py](../planner/forms.py) — `CalendarEventForm`
- [planner/models.py](../planner/models.py) — `CalendarEvent`
- [planner/urls.py](../planner/urls.py)
- [planner/views.py](../planner/views.py) — `index`, `events_list`, `create_event`, `update_event`, `delete_event`

### documents

- [documents/__init__.py](../documents/__init__.py)
- [documents/apps.py](../documents/apps.py) — `DocumentsConfig`
- [documents/board.py](../documents/board.py) — `clean_scene`
- [documents/editor_forms.py](../documents/editor_forms.py) — `validate_document`, `DocumentFilesField`, `OfficeUploadForm`, `OfficeCreateForm`, `OfficeRenameForm`, `OfficeTemplateForm`, `OfficeDocumentForm`
- [documents/editor_views.py](../documents/editor_views.py) — `index`, `upload`, `edit`, `preview`, `import_text`, `download`, `content`, `action`
- [documents/file_cleanup.py](../documents/file_cleanup.py) — `delete_replaced_file`
- [documents/folder_exports.py](../documents/folder_exports.py) — `folder_archive`
- [documents/folder_stats.py](../documents/folder_stats.py) — `set_folder_summaries`
- [documents/forms.py](../documents/forms.py) — `MultipleFileInput`, `MultipleFileField`, `UploadForm`, `IconColorForm`, `LibraryForm`, `FolderForm`, `DocumentForm`
- [documents/location_lock.py](../documents/location_lock.py) — `location_write`
- [documents/models.py](../documents/models.py) — `document_storage`, `document_upload_path`, `library_photo_upload_path`, `DocumentLibrary`, `delete_library_photo`, `Folder`, `Document`, `delete_drive_document_file`, `WorkspaceDocumentFolder`, `WorkspaceDocument`, `delete_workspace_document_file`, `OfficeSaveReceipt`, `DriveOfficeSaveReceipt`, `DocumentVersion`, `delete_document_version_file`
- [documents/move_views.py](../documents/move_views.py) — `MoveForm`, `move`
- [documents/office_extras.py](../documents/office_extras.py) — `from_template`, `template_toggle`
- [documents/office_service.py](../documents/office_service.py) — `configured`, `sign`, `verify`, `capability`, `check_capability`, `service_url`, `document_key`, `editor_config`, `NoRedirect`, `download_result`, `force_save`, `validate_ooxml`, `blank_file`, `receipt_digest`, `convert_file`
- [documents/previews.py](../documents/previews.py) — `inline_type`, `validate_inline`, `OfficePackage`, `build_preview`
- [documents/query.py](../documents/query.py) — `text_field`, `choice_field`, `query_context`, `apply_text_filters`, `apply_date_filter`, `order_results`
- [documents/rich_text.py](../documents/rich_text.py) — `DocumentHTML`, `clean_content`, `text_to_content`, `docx_bytes`
- [documents/suite_views.py](../documents/suite_views.py) — `create`, `editor`, `board_frame`, `rename`, `save_board`, `save_office`, `state`, `source`, `callback`, `upgrade_text`, `convert`
- [documents/urls.py](../documents/urls.py)
- [documents/views.py](../documents/views.py) — `library`, `library_create`, `library_edit`, `library_photo`, `library_delete`, `upload`, `folder_create`, `folder_edit`, `folder_delete`, `folder_star`, `folder_download`, `detail`, `preview`, `preview_content`, `download`, `star`, `trash`, `restore`
- [documents/workspace_urls.py](../documents/workspace_urls.py)

### resources

- [resources/__init__.py](../resources/__init__.py)
- [resources/apps.py](../resources/apps.py) — `ResourcesConfig`
- [resources/forms.py](../resources/forms.py) — `ResourceForm`
- [resources/models.py](../resources/models.py) — `Resource`
- [resources/urls.py](../resources/urls.py)
- [resources/views.py](../resources/views.py) — `index`, `edit`, `delete`

### spaces

- [spaces/__init__.py](../spaces/__init__.py)
- [spaces/access.py](../spaces/access.py) — `spaces_for`, `editable_spaces`, `tree_ids`, `visible_to`, `editable_to`, `require_editable`, `task_people`
- [spaces/apps.py](../spaces/apps.py) — `SpacesConfig`
- [spaces/avatars.py](../spaces/avatars.py) — `avatar_upload_path`, `space_avatar`, `delete_avatar_after_commit`
- [spaces/backlog.py](../spaces/backlog.py) — `append_planned_items`, `bulk_plan_items`, `posted_number`, `free_rank`, `redistribute_ranks`, `move_backlog_item`
- [spaces/board.py](../spaces/board.py) — `move_board_item`
- [spaces/defaults.py](../spaces/defaults.py) — `issue_type_icon`, `template_settings`
- [spaces/forms.py](../spaces/forms.py) — `StyledForm`, `SpaceAvatarForm`, `SpaceForm`, `ItemForm`, `DetailForm`, `SubtaskForm`, `WorkLogForm`, `SprintForm`, `SprintCloseForm`, `TeamForm`, `MemberForm`, `StatusForm`, `TypeForm`, `CustomFieldForm`
- [spaces/identifiers.py](../spaces/identifiers.py) — `unique_space_slug`
- [spaces/middleware.py](../spaces/middleware.py) — `LegacyKanbanMiddleware`
- [spaces/models.py](../spaces/models.py) — `SpaceConfiguration`, `Space`, `SpaceMembership`, `SpaceTask`, `SpaceTaskMembership`, `SpaceTaskActivity`, `SpaceTaskFile`, `SpaceTaskReminder`, `SpaceTaskWorkLog`, `Team`, `TeamMembership`, `Sprint`, `WorkItem`, `LegacyKanbanLink`
- [spaces/navigation.py](../spaces/navigation.py) — `sidebar_spaces`
- [spaces/services.py](../spaces/services.py) — `app_url`, `space_url`, `visible_spaces`, `manageable_spaces`, `can_manage_spaces`, `visible_items`, `decorate_directory_spaces`, `teams_for`, `manage_space`, `manage_configuration`, `manage_team`, `task_url`, `create_work_item`, `record`, `transition_allowed`, `set_status`, `update_sprint`
- [spaces/signals.py](../spaces/signals.py) — `task_metadata`, `removed_workspace_member`, `disabled_workspace_member`, `removed_space_member`, `removed_task_member`, `deleted_team_photo`, `deleted_space_avatar`, `scoped_task_tags`, `scoped_related_tags`, `deleted_task_file`, `scoped_space_task_tags`
- [spaces/summary.py](../spaces/summary.py) — `summary_scope`, `filter_summary_items`, `space_summary`
- [spaces/task_team.py](../spaces/task_team.py) — `ShareForm`, `team_context`, `payload`, `team`, `candidates`
- [spaces/task_views.py](../spaces/task_views.py) — `task_item`, `return_url`, `manages_task`, `attach_files`, `posted_id`, `property_snapshot`, `property_changes`, `detail_post_data`, `work_log_context`, `detail`, `members`, `download`
- [spaces/team_urls.py](../spaces/team_urls.py)
- [spaces/teams.py](../spaces/teams.py) — `index`, `detail`, `edit`, `members`, `remove_member`, `photo`
- [spaces/templatetags/__init__.py](../spaces/templatetags/__init__.py)
- [spaces/templatetags/space_ui.py](../spaces/templatetags/space_ui.py) — `pagination_pages`, `space_avatar`, `status_groups`
- [spaces/testing.py](../spaces/testing.py) — `make_space`
- [spaces/urls.py](../spaces/urls.py)
- [spaces/views.py](../spaces/views.py) — `space_object`, `base_context`, `decorate_items`, `issue_type_filters`, `index_context`, `index`, `manage`, `search`, `filtered_space_items`, `items_for_view`, `backlog_url`, `planning_totals`, `detail_context`, `detail`, `retired_all_items`, `dialog_response`, `edit`, `avatar_edit`, `avatar_photo`, `favorite`, `item_edit`, `backlog_plan`, `item_action`, `sprint_create`, `sprint_plan`, `sprint_action`, `members`, `remove_member`, `configuration`
- [spaces/widgets.py](../spaces/widgets.py) — `IssueTypeSelect`, `TaskVisibilitySelect`, `SpaceSelect`, `TeamSelect`

## 6. Szablony

### core

- [core/templates/core/base.html](../core/templates/core/base.html)
- [core/templates/core/includes/attachment_icon.html](../core/templates/core/includes/attachment_icon.html)
- [core/templates/core/includes/attachment_upload_icon.html](../core/templates/core/includes/attachment_upload_icon.html)
- [core/templates/core/includes/avatar_picker.html](../core/templates/core/includes/avatar_picker.html)
- [core/templates/core/includes/avatar_presets.html](../core/templates/core/includes/avatar_presets.html)
- [core/templates/core/includes/bootstrap.html](../core/templates/core/includes/bootstrap.html)
- [core/templates/core/includes/content_skeleton.html](../core/templates/core/includes/content_skeleton.html)
- [core/templates/core/includes/icon_credit.html](../core/templates/core/includes/icon_credit.html)
- [core/templates/core/includes/management_sidebar.html](../core/templates/core/includes/management_sidebar.html)
- [core/templates/core/includes/photo_crop_dialog.html](../core/templates/core/includes/photo_crop_dialog.html)
- [core/templates/core/includes/priority_icon.html](../core/templates/core/includes/priority_icon.html)
- [core/templates/core/includes/pulpit_editor_sidebar.html](../core/templates/core/includes/pulpit_editor_sidebar.html)
- [core/templates/core/includes/select_priority.html](../core/templates/core/includes/select_priority.html)
- [core/templates/core/includes/select_status.html](../core/templates/core/includes/select_status.html)
- [core/templates/core/includes/settings_secondary_menu.html](../core/templates/core/includes/settings_secondary_menu.html)
- [core/templates/core/includes/settings_sidebar.html](../core/templates/core/includes/settings_sidebar.html)
- [core/templates/core/includes/sidebar_picker.html](../core/templates/core/includes/sidebar_picker.html)
- [core/templates/core/includes/trash_icon.html](../core/templates/core/includes/trash_icon.html)
- [core/templates/core/includes/workplace_management_sidebar.html](../core/templates/core/includes/workplace_management_sidebar.html)
- [core/templates/core/widgets/visual_select.html](../core/templates/core/widgets/visual_select.html)

### accounts

- [accounts/templates/accounts/add_account.html](../accounts/templates/accounts/add_account.html)
- [accounts/templates/accounts/auth_base.html](../accounts/templates/accounts/auth_base.html)
- [accounts/templates/accounts/includes/presence_status_icon.html](../accounts/templates/accounts/includes/presence_status_icon.html)
- [accounts/templates/accounts/includes/user_avatar.html](../accounts/templates/accounts/includes/user_avatar.html)
- [accounts/templates/accounts/includes/user_avatar_icon.html](../accounts/templates/accounts/includes/user_avatar_icon.html)
- [accounts/templates/accounts/login.html](../accounts/templates/accounts/login.html)
- [accounts/templates/accounts/profile.html](../accounts/templates/accounts/profile.html)
- [accounts/templates/accounts/register.html](../accounts/templates/accounts/register.html)
- [accounts/templates/accounts/widgets/user_select.html](../accounts/templates/accounts/widgets/user_select.html)

### workplaces

- [workplaces/templates/workplaces/includes/avatar_picker.html](../workplaces/templates/workplaces/includes/avatar_picker.html)
- [workplaces/templates/workplaces/includes/edit_modal.html](../workplaces/templates/workplaces/includes/edit_modal.html)
- [workplaces/templates/workplaces/includes/invitation_person.html](../workplaces/templates/workplaces/includes/invitation_person.html)
- [workplaces/templates/workplaces/includes/invitation_response_modal.html](../workplaces/templates/workplaces/includes/invitation_response_modal.html)
- [workplaces/templates/workplaces/includes/invitations_table.html](../workplaces/templates/workplaces/includes/invitations_table.html)
- [workplaces/templates/workplaces/includes/management_toolbar.html](../workplaces/templates/workplaces/includes/management_toolbar.html)
- [workplaces/templates/workplaces/includes/members_table.html](../workplaces/templates/workplaces/includes/members_table.html)
- [workplaces/templates/workplaces/includes/sidebar_favorite_toggle.html](../workplaces/templates/workplaces/includes/sidebar_favorite_toggle.html)
- [workplaces/templates/workplaces/includes/sidebar_favorites.html](../workplaces/templates/workplaces/includes/sidebar_favorites.html)
- [workplaces/templates/workplaces/includes/team_modals.html](../workplaces/templates/workplaces/includes/team_modals.html)
- [workplaces/templates/workplaces/includes/team_panel.html](../workplaces/templates/workplaces/includes/team_panel.html)
- [workplaces/templates/workplaces/includes/workplace_photo_editor.html](../workplaces/templates/workplaces/includes/workplace_photo_editor.html)
- [workplaces/templates/workplaces/workplaces.html](../workplaces/templates/workplaces/workplaces.html)

### tasks

- [tasks/templates/tasks/edit_task.html](../tasks/templates/tasks/edit_task.html)
- [tasks/templates/tasks/includes/comment_composer.html](../tasks/templates/tasks/includes/comment_composer.html)
- [tasks/templates/tasks/includes/comment_images.html](../tasks/templates/tasks/includes/comment_images.html)
- [tasks/templates/tasks/includes/directory_actions_menu.html](../tasks/templates/tasks/includes/directory_actions_menu.html)
- [tasks/templates/tasks/includes/directory_column_manager.html](../tasks/templates/tasks/includes/directory_column_manager.html)
- [tasks/templates/tasks/includes/directory_empty_copy.html](../tasks/templates/tasks/includes/directory_empty_copy.html)
- [tasks/templates/tasks/includes/directory_filter_aggregate.html](../tasks/templates/tasks/includes/directory_filter_aggregate.html)
- [tasks/templates/tasks/includes/directory_members.html](../tasks/templates/tasks/includes/directory_members.html)
- [tasks/templates/tasks/includes/directory_menu_header.html](../tasks/templates/tasks/includes/directory_menu_header.html)
- [tasks/templates/tasks/includes/directory_pagination_toolbar.html](../tasks/templates/tasks/includes/directory_pagination_toolbar.html)
- [tasks/templates/tasks/includes/directory_row_menu.html](../tasks/templates/tasks/includes/directory_row_menu.html)
- [tasks/templates/tasks/includes/directory_sort_builder.html](../tasks/templates/tasks/includes/directory_sort_builder.html)
- [tasks/templates/tasks/includes/follow_button.html](../tasks/templates/tasks/includes/follow_button.html)
- [tasks/templates/tasks/includes/group_directory_filter_builder.html](../tasks/templates/tasks/includes/group_directory_filter_builder.html)
- [tasks/templates/tasks/includes/issue_group_header.html](../tasks/templates/tasks/includes/issue_group_header.html)
- [tasks/templates/tasks/includes/project_access_panel.html](../tasks/templates/tasks/includes/project_access_panel.html)
- [tasks/templates/tasks/includes/project_access_tabs.html](../tasks/templates/tasks/includes/project_access_tabs.html)
- [tasks/templates/tasks/includes/project_choice_filter_detail.html](../tasks/templates/tasks/includes/project_choice_filter_detail.html)
- [tasks/templates/tasks/includes/project_directory_filter_sort.html](../tasks/templates/tasks/includes/project_directory_filter_sort.html)
- [tasks/templates/tasks/includes/project_info_modal.html](../tasks/templates/tasks/includes/project_info_modal.html)
- [tasks/templates/tasks/includes/project_members_panel.html](../tasks/templates/tasks/includes/project_members_panel.html)
- [tasks/templates/tasks/includes/project_note_item.html](../tasks/templates/tasks/includes/project_note_item.html)
- [tasks/templates/tasks/includes/project_team_modals.html](../tasks/templates/tasks/includes/project_team_modals.html)
- [tasks/templates/tasks/includes/project_text_filter_detail.html](../tasks/templates/tasks/includes/project_text_filter_detail.html)
- [tasks/templates/tasks/includes/section_notes_thread.html](../tasks/templates/tasks/includes/section_notes_thread.html)
- [tasks/templates/tasks/includes/status_group_header.html](../tasks/templates/tasks/includes/status_group_header.html)
- [tasks/templates/tasks/includes/status_pagination.html](../tasks/templates/tasks/includes/status_pagination.html)
- [tasks/templates/tasks/includes/tag_directory.html](../tasks/templates/tasks/includes/tag_directory.html)
- [tasks/templates/tasks/includes/tag_filters.html](../tasks/templates/tasks/includes/tag_filters.html)
- [tasks/templates/tasks/includes/tag_modal.html](../tasks/templates/tasks/includes/tag_modal.html)
- [tasks/templates/tasks/includes/tag_notes_modal.html](../tasks/templates/tasks/includes/tag_notes_modal.html)
- [tasks/templates/tasks/includes/tag_notes_thread.html](../tasks/templates/tasks/includes/tag_notes_thread.html)
- [tasks/templates/tasks/includes/tag_sort.html](../tasks/templates/tasks/includes/tag_sort.html)
- [tasks/templates/tasks/includes/task_activity_item.html](../tasks/templates/tasks/includes/task_activity_item.html)
- [tasks/templates/tasks/includes/task_display_manager.html](../tasks/templates/tasks/includes/task_display_manager.html)
- [tasks/templates/tasks/includes/task_issue_row.html](../tasks/templates/tasks/includes/task_issue_row.html)
- [tasks/templates/tasks/includes/tasks_project_tree_initial_state.html](../tasks/templates/tasks/includes/tasks_project_tree_initial_state.html)
- [tasks/templates/tasks/includes/tasks_secondary_menu.html](../tasks/templates/tasks/includes/tasks_secondary_menu.html)
- [tasks/templates/tasks/includes/template_item_menu.html](../tasks/templates/tasks/includes/template_item_menu.html)
- [tasks/templates/tasks/includes/work_log_fields.html](../tasks/templates/tasks/includes/work_log_fields.html)
- [tasks/templates/tasks/includes/work_log_list.html](../tasks/templates/tasks/includes/work_log_list.html)
- [tasks/templates/tasks/includes/work_log_modal.html](../tasks/templates/tasks/includes/work_log_modal.html)
- [tasks/templates/tasks/project_template_edit.html](../tasks/templates/tasks/project_template_edit.html)
- [tasks/templates/tasks/project_templates.html](../tasks/templates/tasks/project_templates.html)
- [tasks/templates/tasks/tasks.html](../tasks/templates/tasks/tasks.html)
- [tasks/templates/tasks/view_task.html](../tasks/templates/tasks/view_task.html)

### kanban

- [kanban/templates/kanban/edit_task.html](../kanban/templates/kanban/edit_task.html)
- [kanban/templates/kanban/includes/board_display_manager.html](../kanban/templates/kanban/includes/board_display_manager.html)
- [kanban/templates/kanban/includes/directory_empty_copy.html](../kanban/templates/kanban/includes/directory_empty_copy.html)
- [kanban/templates/kanban/includes/task_board_card.html](../kanban/templates/kanban/includes/task_board_card.html)
- [kanban/templates/kanban/includes/task_issue_row.html](../kanban/templates/kanban/includes/task_issue_row.html)
- [kanban/templates/kanban/includes/tasks_project_tree_initial_state.html](../kanban/templates/kanban/includes/tasks_project_tree_initial_state.html)
- [kanban/templates/kanban/includes/tasks_secondary_menu.html](../kanban/templates/kanban/includes/tasks_secondary_menu.html)
- [kanban/templates/kanban/includes/tasks_section_actions.html](../kanban/templates/kanban/includes/tasks_section_actions.html)
- [kanban/templates/kanban/tasks.html](../kanban/templates/kanban/tasks.html)
- [kanban/templates/kanban/view_task.html](../kanban/templates/kanban/view_task.html)

### contacts

- [contacts/templates/contacts/companies.html](../contacts/templates/contacts/companies.html)
- [contacts/templates/contacts/contacts.html](../contacts/templates/contacts/contacts.html)
- [contacts/templates/contacts/includes/company_avatar.html](../contacts/templates/contacts/includes/company_avatar.html)
- [contacts/templates/contacts/includes/company_avatar_icon.html](../contacts/templates/contacts/includes/company_avatar_icon.html)
- [contacts/templates/contacts/includes/company_photo_editor.html](../contacts/templates/contacts/includes/company_photo_editor.html)
- [contacts/templates/contacts/includes/contact_create_modals.html](../contacts/templates/contacts/includes/contact_create_modals.html)
- [contacts/templates/contacts/includes/contact_status_badge.html](../contacts/templates/contacts/includes/contact_status_badge.html)
- [contacts/templates/contacts/includes/contacts_secondary_menu.html](../contacts/templates/contacts/includes/contacts_secondary_menu.html)
- [contacts/templates/contacts/user_directory.html](../contacts/templates/contacts/user_directory.html)
- [contacts/templates/contacts/view_company.html](../contacts/templates/contacts/view_company.html)
- [contacts/templates/contacts/view_contact.html](../contacts/templates/contacts/view_contact.html)

### dashboard

- [dashboard/templates/dashboard/filters/base.html](../dashboard/templates/dashboard/filters/base.html)
- [dashboard/templates/dashboard/filters/directory.html](../dashboard/templates/dashboard/filters/directory.html)
- [dashboard/templates/dashboard/filters/favorite.html](../dashboard/templates/dashboard/filters/favorite.html)
- [dashboard/templates/dashboard/filters/form.html](../dashboard/templates/dashboard/filters/form.html)
- [dashboard/templates/dashboard/filters/index.html](../dashboard/templates/dashboard/filters/index.html)
- [dashboard/templates/dashboard/filters/manage.html](../dashboard/templates/dashboard/filters/manage.html)
- [dashboard/templates/dashboard/filters/results.html](../dashboard/templates/dashboard/filters/results.html)
- [dashboard/templates/dashboard/filters/row_actions.html](../dashboard/templates/dashboard/filters/row_actions.html)
- [dashboard/templates/dashboard/filters/search.html](../dashboard/templates/dashboard/filters/search.html)
- [dashboard/templates/dashboard/filters/search_results.html](../dashboard/templates/dashboard/filters/search_results.html)
- [dashboard/templates/dashboard/filters/sidebar.html](../dashboard/templates/dashboard/filters/sidebar.html)
- [dashboard/templates/dashboard/filters/sidebar_navigation.html](../dashboard/templates/dashboard/filters/sidebar_navigation.html)
- [dashboard/templates/dashboard/filters/sidebar_picker.html](../dashboard/templates/dashboard/filters/sidebar_picker.html)
- [dashboard/templates/dashboard/filters/sidebar_row.html](../dashboard/templates/dashboard/filters/sidebar_row.html)
- [dashboard/templates/dashboard/for_you.html](../dashboard/templates/dashboard/for_you.html)
- [dashboard/templates/dashboard/home.html](../dashboard/templates/dashboard/home.html)
- [dashboard/templates/dashboard/includes/notification_controls.html](../dashboard/templates/dashboard/includes/notification_controls.html)
- [dashboard/templates/dashboard/includes/notification_list.html](../dashboard/templates/dashboard/includes/notification_list.html)
- [dashboard/templates/dashboard/includes/notification_pagination.html](../dashboard/templates/dashboard/includes/notification_pagination.html)
- [dashboard/templates/dashboard/includes/settings_row.html](../dashboard/templates/dashboard/includes/settings_row.html)
- [dashboard/templates/dashboard/includes/work_progress.html](../dashboard/templates/dashboard/includes/work_progress.html)
- [dashboard/templates/dashboard/pulpits/actions.html](../dashboard/templates/dashboard/pulpits/actions.html)
- [dashboard/templates/dashboard/pulpits/base.html](../dashboard/templates/dashboard/pulpits/base.html)
- [dashboard/templates/dashboard/pulpits/canvas.html](../dashboard/templates/dashboard/pulpits/canvas.html)
- [dashboard/templates/dashboard/pulpits/catalog.html](../dashboard/templates/dashboard/pulpits/catalog.html)
- [dashboard/templates/dashboard/pulpits/catalog_preview.html](../dashboard/templates/dashboard/pulpits/catalog_preview.html)
- [dashboard/templates/dashboard/pulpits/detail.html](../dashboard/templates/dashboard/pulpits/detail.html)
- [dashboard/templates/dashboard/pulpits/directory.html](../dashboard/templates/dashboard/pulpits/directory.html)
- [dashboard/templates/dashboard/pulpits/edit.html](../dashboard/templates/dashboard/pulpits/edit.html)
- [dashboard/templates/dashboard/pulpits/fields.html](../dashboard/templates/dashboard/pulpits/fields.html)
- [dashboard/templates/dashboard/pulpits/form.html](../dashboard/templates/dashboard/pulpits/form.html)
- [dashboard/templates/dashboard/pulpits/gadget.html](../dashboard/templates/dashboard/pulpits/gadget.html)
- [dashboard/templates/dashboard/pulpits/gadget_preview.html](../dashboard/templates/dashboard/pulpits/gadget_preview.html)
- [dashboard/templates/dashboard/pulpits/gadgets.html](../dashboard/templates/dashboard/pulpits/gadgets.html)
- [dashboard/templates/dashboard/pulpits/index.html](../dashboard/templates/dashboard/pulpits/index.html)
- [dashboard/templates/dashboard/pulpits/layout_preview.html](../dashboard/templates/dashboard/pulpits/layout_preview.html)
- [dashboard/templates/dashboard/pulpits/manage.html](../dashboard/templates/dashboard/pulpits/manage.html)
- [dashboard/templates/dashboard/pulpits/row_actions.html](../dashboard/templates/dashboard/pulpits/row_actions.html)
- [dashboard/templates/dashboard/pulpits/search_results.html](../dashboard/templates/dashboard/pulpits/search_results.html)
- [dashboard/templates/dashboard/pulpits/sidebar_navigation.html](../dashboard/templates/dashboard/pulpits/sidebar_navigation.html)
- [dashboard/templates/dashboard/pulpits/sidebar_picker.html](../dashboard/templates/dashboard/pulpits/sidebar_picker.html)
- [dashboard/templates/dashboard/pulpits/sidebar_row.html](../dashboard/templates/dashboard/pulpits/sidebar_row.html)
- [dashboard/templates/dashboard/settings.html](../dashboard/templates/dashboard/settings.html)

### planner

- [planner/templates/planner/includes/color_filters.html](../planner/templates/planner/includes/color_filters.html)
- [planner/templates/planner/index.html](../planner/templates/planner/index.html)

### documents

- [documents/templates/documents/filter_sort.html](../documents/templates/documents/filter_sort.html)
- [documents/templates/documents/form.html](../documents/templates/documents/form.html)
- [documents/templates/documents/includes/color_field.html](../documents/templates/documents/includes/color_field.html)
- [documents/templates/documents/includes/drag_attributes.html](../documents/templates/documents/includes/drag_attributes.html)
- [documents/templates/documents/includes/drive_icon.html](../documents/templates/documents/includes/drive_icon.html)
- [documents/templates/documents/includes/file_icon.html](../documents/templates/documents/includes/file_icon.html)
- [documents/templates/documents/includes/file_icon_shape.html](../documents/templates/documents/includes/file_icon_shape.html)
- [documents/templates/documents/includes/files_empty.html](../documents/templates/documents/includes/files_empty.html)
- [documents/templates/documents/includes/files_grid.html](../documents/templates/documents/includes/files_grid.html)
- [documents/templates/documents/includes/folder_icon.html](../documents/templates/documents/includes/folder_icon.html)
- [documents/templates/documents/includes/libraries_empty.html](../documents/templates/documents/includes/libraries_empty.html)
- [documents/templates/documents/includes/libraries_grid.html](../documents/templates/documents/includes/libraries_grid.html)
- [documents/templates/documents/includes/library_actions.html](../documents/templates/documents/includes/library_actions.html)
- [documents/templates/documents/includes/library_avatar.html](../documents/templates/documents/includes/library_avatar.html)
- [documents/templates/documents/includes/move_action.html](../documents/templates/documents/includes/move_action.html)
- [documents/templates/documents/includes/row_actions.html](../documents/templates/documents/includes/row_actions.html)
- [documents/templates/documents/includes/row_menu.html](../documents/templates/documents/includes/row_menu.html)
- [documents/templates/documents/libraries.html](../documents/templates/documents/libraries.html)
- [documents/templates/documents/library.html](../documents/templates/documents/library.html)
- [documents/templates/documents/modal_host.html](../documents/templates/documents/modal_host.html)
- [documents/templates/documents/office/actions.html](../documents/templates/documents/office/actions.html)
- [documents/templates/documents/office/board_frame.html](../documents/templates/documents/office/board_frame.html)
- [documents/templates/documents/office/create_card.html](../documents/templates/documents/office/create_card.html)
- [documents/templates/documents/office/editor.html](../documents/templates/documents/office/editor.html)
- [documents/templates/documents/office/index.html](../documents/templates/documents/office/index.html)
- [documents/templates/documents/office/name.html](../documents/templates/documents/office/name.html)
- [documents/templates/documents/office/suite.html](../documents/templates/documents/office/suite.html)
- [documents/templates/documents/preview.html](../documents/templates/documents/preview.html)
- [documents/templates/documents/return_filters.html](../documents/templates/documents/return_filters.html)
- [documents/templates/documents/sidebar.html](../documents/templates/documents/sidebar.html)
- [documents/templates/documents/toolbar.html](../documents/templates/documents/toolbar.html)

### resources

- [resources/templates/resources/form.html](../resources/templates/resources/form.html)
- [resources/templates/resources/index.html](../resources/templates/resources/index.html)

### spaces

- [spaces/templates/spaces/avatar.html](../spaces/templates/spaces/avatar.html)
- [spaces/templates/spaces/avatar_picker.html](../spaces/templates/spaces/avatar_picker.html)
- [spaces/templates/spaces/backlog.html](../spaces/templates/spaces/backlog.html)
- [spaces/templates/spaces/backlog_header_details.html](../spaces/templates/spaces/backlog_header_details.html)
- [spaces/templates/spaces/backlog_move_form.html](../spaces/templates/spaces/backlog_move_form.html)
- [spaces/templates/spaces/base.html](../spaces/templates/spaces/base.html)
- [spaces/templates/spaces/board_order_form.html](../spaces/templates/spaces/board_order_form.html)
- [spaces/templates/spaces/card.html](../spaces/templates/spaces/card.html)
- [spaces/templates/spaces/configuration.html](../spaces/templates/spaces/configuration.html)
- [spaces/templates/spaces/detail.html](../spaces/templates/spaces/detail.html)
- [spaces/templates/spaces/directory.html](../spaces/templates/spaces/directory.html)
- [spaces/templates/spaces/directory_row_actions.html](../spaces/templates/spaces/directory_row_actions.html)
- [spaces/templates/spaces/form.html](../spaces/templates/spaces/form.html)
- [spaces/templates/spaces/form_page.html](../spaces/templates/spaces/form_page.html)
- [spaces/templates/spaces/index.html](../spaces/templates/spaces/index.html)
- [spaces/templates/spaces/issue_type.html](../spaces/templates/spaces/issue_type.html)
- [spaces/templates/spaces/item_actions.html](../spaces/templates/spaces/item_actions.html)
- [spaces/templates/spaces/item_list.html](../spaces/templates/spaces/item_list.html)
- [spaces/templates/spaces/item_planning.html](../spaces/templates/spaces/item_planning.html)
- [spaces/templates/spaces/item_toolbar.html](../spaces/templates/spaces/item_toolbar.html)
- [spaces/templates/spaces/manage.html](../spaces/templates/spaces/manage.html)
- [spaces/templates/spaces/pagination.html](../spaces/templates/spaces/pagination.html)
- [spaces/templates/spaces/row.html](../spaces/templates/spaces/row.html)
- [spaces/templates/spaces/search_results.html](../spaces/templates/spaces/search_results.html)
- [spaces/templates/spaces/sidebar_navigation.html](../spaces/templates/spaces/sidebar_navigation.html)
- [spaces/templates/spaces/sidebar_picker.html](../spaces/templates/spaces/sidebar_picker.html)
- [spaces/templates/spaces/sidebar_row.html](../spaces/templates/spaces/sidebar_row.html)
- [spaces/templates/spaces/sprint_card.html](../spaces/templates/spaces/sprint_card.html)
- [spaces/templates/spaces/sprint_header_details.html](../spaces/templates/spaces/sprint_header_details.html)
- [spaces/templates/spaces/subtask_modal.html](../spaces/templates/spaces/subtask_modal.html)
- [spaces/templates/spaces/summary.html](../spaces/templates/spaces/summary.html)
- [spaces/templates/spaces/tags.html](../spaces/templates/spaces/tags.html)
- [spaces/templates/spaces/task_attachments.html](../spaces/templates/spaces/task_attachments.html)
- [spaces/templates/spaces/task_comment.html](../spaces/templates/spaces/task_comment.html)
- [spaces/templates/spaces/task_detail.html](../spaces/templates/spaces/task_detail.html)
- [spaces/templates/spaces/team.html](../spaces/templates/spaces/team.html)
- [spaces/templates/spaces/team_avatar.html](../spaces/templates/spaces/team_avatar.html)
- [spaces/templates/spaces/teams.html](../spaces/templates/spaces/teams.html)
- [spaces/templates/spaces/template_picker.html](../spaces/templates/spaces/template_picker.html)

## 7. Zasoby frontendowe

### css

- [static/css/base/fonts.css](../static/css/base/fonts.css)
- [static/css/base/reset.css](../static/css/base/reset.css)
- [static/css/base/variables.css](../static/css/base/variables.css)
- [static/css/calendar.css](../static/css/calendar.css)
- [static/css/components/alerts.css](../static/css/components/alerts.css)
- [static/css/components/attachments.css](../static/css/components/attachments.css)
- [static/css/components/auth.css](../static/css/components/auth.css)
- [static/css/components/buttons.css](../static/css/components/buttons.css)
- [static/css/components/cards.css](../static/css/components/cards.css)
- [static/css/components/checkboxes.css](../static/css/components/checkboxes.css)
- [static/css/components/contacts.css](../static/css/components/contacts.css)
- [static/css/components/dashboard.css](../static/css/components/dashboard.css)
- [static/css/components/dialogs.css](../static/css/components/dialogs.css)
- [static/css/components/documents.css](../static/css/components/documents.css)
- [static/css/components/dropdown-layer.css](../static/css/components/dropdown-layer.css)
- [static/css/components/file-upload.css](../static/css/components/file-upload.css)
- [static/css/components/forms.css](../static/css/components/forms.css)
- [static/css/components/global-search.css](../static/css/components/global-search.css)
- [static/css/components/modal-system.css](../static/css/components/modal-system.css)
- [static/css/components/modals.css](../static/css/components/modals.css)
- [static/css/components/notifications-panel.css](../static/css/components/notifications-panel.css)
- [static/css/components/notifications.css](../static/css/components/notifications.css)
- [static/css/components/office.css](../static/css/components/office.css)
- [static/css/components/profile.css](../static/css/components/profile.css)
- [static/css/components/pulpits.css](../static/css/components/pulpits.css)
- [static/css/components/resources.css](../static/css/components/resources.css)
- [static/css/components/settings.css](../static/css/components/settings.css)
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
- [static/js/project-templates.js](../static/js/project-templates.js)
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
- [static/js/task-work-log.js](../static/js/task-work-log.js)
- [static/js/tasks.js](../static/js/tasks.js)
- [static/js/workplace-avatars.js](../static/js/workplace-avatars.js)
- [static/js/workplace-team.js](../static/js/workplace-team.js)

### img

- [static/img/empty-states/README.md](../static/img/empty-states/README.md)
- [static/img/empty-states/dashboard-empty.webp](../static/img/empty-states/dashboard-empty.webp)
- [static/img/empty-states/for-you-assigned-empty.webp](../static/img/empty-states/for-you-assigned-empty.webp)
- [static/img/empty-states/for-you-starred-empty.webp](../static/img/empty-states/for-you-starred-empty.webp)
- [static/img/empty-states/for-you-tasks-empty.webp](../static/img/empty-states/for-you-tasks-empty.webp)
- [static/img/empty-states/for-you-viewed-empty.webp](../static/img/empty-states/for-you-viewed-empty.webp)
- [static/img/empty-states/for-you-worked-empty.webp](../static/img/empty-states/for-you-worked-empty.webp)
- [static/img/empty-states/gadget-column-empty.webp](../static/img/empty-states/gadget-column-empty.webp)
- [static/img/empty-states/spaces-empty.webp](../static/img/empty-states/spaces-empty.webp)
- [static/img/favicon-ancore-large.png](../static/img/favicon-ancore-large.png)
- [static/img/logo-ancore.png](../static/img/logo-ancore.png)
- [static/img/pulpits/README.md](../static/img/pulpits/README.md)
- [static/img/pulpits/assigned.svg](../static/img/pulpits/assigned.svg)
- [static/img/pulpits/statistics.svg](../static/img/pulpits/statistics.svg)
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

## 8. Testy

Liczby dotyczą definicji metod, nie uruchomionych przypadków.

### core/test_comment_images.py

Źródło: [core/test_comment_images.py](../core/test_comment_images.py).

- `CommentImageTests`: 16 metod testowych.

### core/test_file_lifecycle.py

Źródło: [core/test_file_lifecycle.py](../core/test_file_lifecycle.py).

- `FileLifecycleTests`: 5 metod testowych.
- `PublicMediaTests`: 1 metod testowych.

### core/test_status_updates.py

Źródło: [core/test_status_updates.py](../core/test_status_updates.py).

- `StatusUpdateTests`: 3 metod testowych.
- `ConcurrentStatusUpdateTests`: 1 metod testowych.

### core/test_task_integrity.py

Źródło: [core/test_task_integrity.py](../core/test_task_integrity.py).

- `TaskIdentityTests`: 12 metod testowych.
- `ConcurrentTaskNumberTests`: 2 metod testowych.

### core/test_task_number_migrations.py

Źródło: [core/test_task_number_migrations.py](../core/test_task_number_migrations.py).

- `TaskNumberMigrationTests`: 1 metod testowych.

### core/tests.py

Źródło: [core/tests.py](../core/tests.py).

- `UploadValidationTests`: 3 metod testowych.
- `SidebarActiveStateTests`: 11 metod testowych.

### accounts/test_avatars.py

Źródło: [accounts/test_avatars.py](../accounts/test_avatars.py).

- `UserAvatarTests`: 9 metod testowych.

### accounts/test_email_identity.py

Źródło: [accounts/test_email_identity.py](../accounts/test_email_identity.py).

- `EmailIdentityTests`: 9 metod testowych.
- `EmailIdentityMigrationTests`: 1 metod testowych.

### accounts/test_login_redirects.py

Źródło: [accounts/test_login_redirects.py](../accounts/test_login_redirects.py).

- `LoginRedirectTests`: 9 metod testowych.

### accounts/tests.py

Źródło: [accounts/tests.py](../accounts/tests.py).

- `UserRegistrationFormTests`: 2 metod testowych.
- `AuthPageViewTests`: 2 metod testowych.
- `ProfileViewTests`: 13 metod testowych.
- `AccountSwitcherTests`: 11 metod testowych.

### workplaces/test_avatars.py

Źródło: [workplaces/test_avatars.py](../workplaces/test_avatars.py).

- `WorkplaceAvatarTests`: 8 metod testowych.

### workplaces/test_defaults.py

Źródło: [workplaces/test_defaults.py](../workplaces/test_defaults.py).

- `DefaultWorkplaceTests`: 6 metod testowych.
- `ConcurrentDefaultWorkplaceTests`: 1 metod testowych.

### workplaces/test_identifiers.py

Źródło: [workplaces/test_identifiers.py](../workplaces/test_identifiers.py).

- `WorkspaceIdentifierTests`: 10 metod testowych.
- `WorkspaceIdentifierMigrationTests`: 1 metod testowych.

### workplaces/test_invitation_candidates.py

Źródło: [workplaces/test_invitation_candidates.py](../workplaces/test_invitation_candidates.py).

- `InvitationCandidateTests`: 9 metod testowych.

### workplaces/test_management.py

Źródło: [workplaces/test_management.py](../workplaces/test_management.py).

- `WorkspaceManagementTests`: 16 metod testowych.

### workplaces/test_team.py

Źródło: [workplaces/test_team.py](../workplaces/test_team.py).

- `TeamAccessTests`: 21 metod testowych.
- `TeamSlugMigrationTests`: 1 metod testowych.

### workplaces/tests.py

Źródło: [workplaces/tests.py](../workplaces/tests.py).

- `WorkplaceSelectionTests`: 43 metod testowych.

### tasks/test_direct_sharing_migration.py

Źródło: [tasks/test_direct_sharing_migration.py](../tasks/test_direct_sharing_migration.py).

- `DirectSharingMigrationTests`: 1 metod testowych.

### tasks/test_directory_tabs.py

Źródło: [tasks/test_directory_tabs.py](../tasks/test_directory_tabs.py).

- `DirectoryTabsTests`: 21 metod testowych.

### tasks/test_group_directory.py

Źródło: [tasks/test_group_directory.py](../tasks/test_group_directory.py).

- `ProjectGroupDirectoryTests`: 3 metod testowych.

### tasks/test_legacy_time_migration.py

Źródło: [tasks/test_legacy_time_migration.py](../tasks/test_legacy_time_migration.py).

- `LegacyTaskTimeMigrationTests`: 2 metod testowych.

### tasks/test_project_field_retirement.py

Źródło: [tasks/test_project_field_retirement.py](../tasks/test_project_field_retirement.py).

- `ProjectFieldRetirementTests`: 3 metod testowych.
- `ProjectFieldRemovalMigrationTests`: 1 metod testowych.

### tasks/test_project_invitations.py

Źródło: [tasks/test_project_invitations.py](../tasks/test_project_invitations.py).

- `ProjectTeamTests`: 10 metod testowych.
- `ProjectMembershipMigrationTests`: 1 metod testowych.

### tasks/test_project_observer.py

Źródło: [tasks/test_project_observer.py](../tasks/test_project_observer.py).

- `ProjectObserverTests`: 11 metod testowych.

### tasks/test_project_sharing.py

Źródło: [tasks/test_project_sharing.py](../tasks/test_project_sharing.py).

- `ProjectSharingTests`: 12 metod testowych.

### tasks/test_project_templates.py

Źródło: [tasks/test_project_templates.py](../tasks/test_project_templates.py).

- `ProjectTemplateTests`: 29 metod testowych.

### tasks/test_project_visibility.py

Źródło: [tasks/test_project_visibility.py](../tasks/test_project_visibility.py).

- `ProjectVisibilityTests`: 18 metod testowych.
- `ProjectVisibilityMigrationTests`: 1 metod testowych.

### tasks/test_retirement.py

Źródło: [tasks/test_retirement.py](../tasks/test_retirement.py).

- `RetiredTasksTests`: 8 metod testowych.

### tasks/test_section_sharing.py

Źródło: [tasks/test_section_sharing.py](../tasks/test_section_sharing.py).

- `SectionSharingTests`: 17 metod testowych.
- `SectionSharingMigrationTests`: 1 metod testowych.

### tasks/test_status_pagination.py

Źródło: [tasks/test_status_pagination.py](../tasks/test_status_pagination.py).

- `TaskStatusPaginationTests`: 7 metod testowych.

### tasks/test_tag_retirement.py

Źródło: [tasks/test_tag_retirement.py](../tasks/test_tag_retirement.py).

- `LegacyTagRetirementTests`: 8 metod testowych.

### tasks/test_task_moves.py

Źródło: [tasks/test_task_moves.py](../tasks/test_task_moves.py).

- `TaskLocationEditTests`: 10 metod testowych.

### tasks/test_task_sharing.py

Źródło: [tasks/test_task_sharing.py](../tasks/test_task_sharing.py).

- `TaskSharingTests`: 17 metod testowych.
- `TaskSharingMigrationTests`: 1 metod testowych.

### tasks/test_unassigned_creation.py

Źródło: [tasks/test_unassigned_creation.py](../tasks/test_unassigned_creation.py).

- `UnassignedTaskCreationTests`: 8 metod testowych.

### tasks/test_work_logs.py

Źródło: [tasks/test_work_logs.py](../tasks/test_work_logs.py).

- `TaskWorkLogTests`: 21 metod testowych.

### tasks/test_write_locking.py

Źródło: [tasks/test_write_locking.py](../tasks/test_write_locking.py).

- `ProjectTemplateWriteLockTests`: 1 metod testowych.

### tasks/tests.py

Źródło: [tasks/tests.py](../tasks/tests.py).

- `TaskProjectControlStyleTests`: 19 metod testowych.
- `TaskProjectCreationTests`: 101 metod testowych.

### kanban/test_retirement.py

Źródło: [kanban/test_retirement.py](../kanban/test_retirement.py).

- `RetiredKanbanTests`: 6 metod testowych.

### kanban/test_sharing.py

Źródło: [kanban/test_sharing.py](../kanban/test_sharing.py).

- `KanbanSharingMigrationTests`: 1 metod testowych.

### kanban/tests.py

Źródło: [kanban/tests.py](../kanban/tests.py).

- `LegacyKanbanModelTests`: 2 metod testowych.

### contacts/tests.py

Źródło: [contacts/tests.py](../contacts/tests.py).

- `RetiredContactRoutesTests`: 2 metod testowych.
- `RetiredContactDirectoryTests`: 4 metod testowych.

### dashboard/test_collaboration.py

Źródło: [dashboard/test_collaboration.py](../dashboard/test_collaboration.py).

- `CollaborationTests`: 20 metod testowych.

### dashboard/test_default_pulpit.py

Źródło: [dashboard/test_default_pulpit.py](../dashboard/test_default_pulpit.py).

- `DefaultPulpitTests`: 7 metod testowych.

### dashboard/test_filters.py

Źródło: [dashboard/test_filters.py](../dashboard/test_filters.py).

- `TaskFilterTests`: 25 metod testowych.

### dashboard/test_for_you.py

Źródło: [dashboard/test_for_you.py](../dashboard/test_for_you.py).

- `ForYouTests`: 29 metod testowych.

### dashboard/test_notifications.py

Źródło: [dashboard/test_notifications.py](../dashboard/test_notifications.py).

- `NotificationCenterTests`: 26 metod testowych.

### dashboard/test_overview.py

Źródło: [dashboard/test_overview.py](../dashboard/test_overview.py).

- `DashboardOverviewTests`: 10 metod testowych.

### dashboard/test_pulpit_catalog.py

Źródło: [dashboard/test_pulpit_catalog.py](../dashboard/test_pulpit_catalog.py).

- `GadgetCatalogTests`: 5 metod testowych.

### dashboard/test_pulpit_editor.py

Źródło: [dashboard/test_pulpit_editor.py](../dashboard/test_pulpit_editor.py).

- `PulpitEditorTests`: 7 metod testowych.

### dashboard/test_pulpit_group_retirement.py

Źródło: [dashboard/test_pulpit_group_retirement.py](../dashboard/test_pulpit_group_retirement.py).

- `PulpitGroupRetirementTests`: 3 metod testowych.
- `PulpitGroupRemovalMigrationTests`: 1 metod testowych.

### dashboard/test_pulpit_management.py

Źródło: [dashboard/test_pulpit_management.py](../dashboard/test_pulpit_management.py).

- `PulpitManagementTests`: 12 metod testowych.

### dashboard/test_pulpit_navigation.py

Źródło: [dashboard/test_pulpit_navigation.py](../dashboard/test_pulpit_navigation.py).

- `PulpitNavigationTests`: 8 metod testowych.

### dashboard/test_pulpit_urls.py

Źródło: [dashboard/test_pulpit_urls.py](../dashboard/test_pulpit_urls.py).

- `PulpitUrlTests`: 6 metod testowych.
- `PulpitSlugConcurrencyTests`: 1 metod testowych.
- `PulpitSlugMigrationTests`: 1 metod testowych.

### dashboard/test_pulpits.py

Źródło: [dashboard/test_pulpits.py](../dashboard/test_pulpits.py).

- `PulpitTests`: 32 metod testowych.

### dashboard/test_reminders.py

Źródło: [dashboard/test_reminders.py](../dashboard/test_reminders.py).

- `TaskReminderTests`: 8 metod testowych.

### dashboard/test_search_regressions.py

Źródło: [dashboard/test_search_regressions.py](../dashboard/test_search_regressions.py).

- `GlobalSearchRegressionTests`: 13 metod testowych.

### dashboard/test_work_progress_migration.py

Źródło: [dashboard/test_work_progress_migration.py](../dashboard/test_work_progress_migration.py).

- `WorkProgressMigrationTests`: 1 metod testowych.

### dashboard/test_workspace_invitations.py

Źródło: [dashboard/test_workspace_invitations.py](../dashboard/test_workspace_invitations.py).

- `WorkspaceInvitationNotificationTests`: 10 metod testowych.

### dashboard/tests.py

Źródło: [dashboard/tests.py](../dashboard/tests.py).

- `DashboardViewTests`: 7 metod testowych.
- `GlobalSearchTests`: 5 metod testowych.

### planner/test_task_calendar.py

Źródło: [planner/test_task_calendar.py](../planner/test_task_calendar.py).

- `TaskCalendarTests`: 4 metod testowych.

### planner/tests.py

Źródło: [planner/tests.py](../planner/tests.py).

- `CalendarEventTests`: 3 metod testowych.

### documents/test_colors.py

Źródło: [documents/test_colors.py](../documents/test_colors.py).

- `IconColorTests`: 6 metod testowych.

### documents/test_drive_folders.py

Źródło: [documents/test_drive_folders.py](../documents/test_drive_folders.py).

- `DriveFolderTests`: 7 metod testowych.

### documents/test_drive_office.py

Źródło: [documents/test_drive_office.py](../documents/test_drive_office.py).

- `DriveOfficeTests`: 14 metod testowych.

### documents/test_folder_icons.py

Źródło: [documents/test_folder_icons.py](../documents/test_folder_icons.py).

- `FolderIconTestsMixin`: 3 metod testowych.
- `DriveFolderIconTests`: 0 metod testowych.

### documents/test_library_photos.py

Źródło: [documents/test_library_photos.py](../documents/test_library_photos.py).

- `LibraryPhotoTests`: 8 metod testowych.

### documents/test_migrations.py

Źródło: [documents/test_migrations.py](../documents/test_migrations.py).

- `LibraryMigrationTests`: 4 metod testowych.

### documents/test_moves.py

Źródło: [documents/test_moves.py](../documents/test_moves.py).

- `CatalogMoveTests`: 8 metod testowych.
- `DriveMoveTests`: 4 metod testowych.
- `ConcurrentMoveTests`: 1 metod testowych.

### documents/test_office.py

Źródło: [documents/test_office.py](../documents/test_office.py).

- `RichTextTests`: 3 metod testowych.
- `OfficeTests`: 20 metod testowych.

### documents/test_office_extras.py

Źródło: [documents/test_office_extras.py](../documents/test_office_extras.py).

- `OfficeExtrasTests`: 16 metod testowych.

### documents/test_office_folders.py

Źródło: [documents/test_office_folders.py](../documents/test_office_folders.py).

- `OfficeFlatCatalogTests`: 6 metod testowych.

### documents/test_office_query.py

Źródło: [documents/test_office_query.py](../documents/test_office_query.py).

- `OfficeQueryTests`: 9 metod testowych.

### documents/test_previews.py

Źródło: [documents/test_previews.py](../documents/test_previews.py).

- `PreviewParserTests`: 9 metod testowych.
- `DocumentPreviewTests`: 9 metod testowych.

### documents/test_query.py

Źródło: [documents/test_query.py](../documents/test_query.py).

- `DocumentQueryTests`: 11 metod testowych.

### documents/test_rename.py

Źródło: [documents/test_rename.py](../documents/test_rename.py).

- `EditorRenameTests`: 5 metod testowych.

### documents/test_suite.py

Źródło: [documents/test_suite.py](../documents/test_suite.py).

- `FullEditorTests`: 19 metod testowych.
- `SceneValidationTests`: 2 metod testowych.

### documents/tests.py

Źródło: [documents/tests.py](../documents/tests.py).

- `DocumentLibraryTests`: 39 metod testowych.

### resources/tests.py

Źródło: [resources/tests.py](../resources/tests.py).

- `ResourceTests`: 19 metod testowych.

### spaces/test_avatars.py

Źródło: [spaces/test_avatars.py](../spaces/test_avatars.py).

- `SpaceAvatarTests`: 11 metod testowych.

### spaces/test_backlog_drag.py

Źródło: [spaces/test_backlog_drag.py](../spaces/test_backlog_drag.py).

- `BacklogDragTests`: 18 metod testowych.

### spaces/test_backlog_ordering.py

Źródło: [spaces/test_backlog_ordering.py](../spaces/test_backlog_ordering.py).

- `BacklogOrderingTests`: 7 metod testowych.

### spaces/test_backlog_planning.py

Źródło: [spaces/test_backlog_planning.py](../spaces/test_backlog_planning.py).

- `BacklogPlanningTests`: 22 metod testowych.

### spaces/test_board_order.py

Źródło: [spaces/test_board_order.py](../spaces/test_board_order.py).

- `BoardOrderTests`: 17 metod testowych.

### spaces/test_independent_tasks.py

Źródło: [spaces/test_independent_tasks.py](../spaces/test_independent_tasks.py).

- `IndependentTaskTests`: 23 metod testowych.
- `IndependentMigrationTests`: 1 metod testowych.

### spaces/test_issue_types.py

Źródło: [spaces/test_issue_types.py](../spaces/test_issue_types.py).

- `IssueTypeTests`: 10 metod testowych.

### spaces/test_management.py

Źródło: [spaces/test_management.py](../spaces/test_management.py).

- `SpaceManagementTests`: 9 metod testowych.

### spaces/test_navigation.py

Źródło: [spaces/test_navigation.py](../spaces/test_navigation.py).

- `SpaceNavigationTests`: 6 metod testowych.

### spaces/test_summary.py

Źródło: [spaces/test_summary.py](../spaces/test_summary.py).

- `SpaceSummaryTests`: 10 metod testowych.

### spaces/test_tags.py

Źródło: [spaces/test_tags.py](../spaces/test_tags.py).

- `SpaceTagTests`: 14 metod testowych.
- `SpaceTagMigrationTests`: 1 metod testowych.

### spaces/test_task_autosave.py

Źródło: [spaces/test_task_autosave.py](../spaces/test_task_autosave.py).

- `TaskAutosaveTests`: 10 metod testowych.

### spaces/test_task_detail_parity.py

Źródło: [spaces/test_task_detail_parity.py](../spaces/test_task_detail_parity.py).

- `DetailParityTests`: 15 metod testowych.

### spaces/test_urls.py

Źródło: [spaces/test_urls.py](../spaces/test_urls.py).

- `SpaceUrlTests`: 8 metod testowych.
- `ConcurrentSpaceSlugTests`: 1 metod testowych.
- `SpaceSlugMigrationTests`: 1 metod testowych.

### spaces/test_write_access.py

Źródło: [spaces/test_write_access.py](../spaces/test_write_access.py).

- `SpaceWriteAccessRaceTests`: 5 metod testowych.

### spaces/tests.py

Źródło: [spaces/tests.py](../spaces/tests.py).

- `SpaceTests`: 33 metod testowych.
- `ImportTests`: 1 metod testowych.

## 9. Migracje obecne lokalnie

Obecność na tej liście nie oznacza śledzenia w Git lub zastosowania w bazie.

### accounts

- [accounts/migrations/0001_initial.py](../accounts/migrations/0001_initial.py)
- [accounts/migrations/0005_backfill_public_usernames.py](../accounts/migrations/0005_backfill_public_usernames.py)
- [accounts/migrations/0006_user_last_seen_auto_presence.py](../accounts/migrations/0006_user_last_seen_auto_presence.py)
- [accounts/migrations/0007_alter_user_profile_photo.py](../accounts/migrations/0007_alter_user_profile_photo.py)
- [accounts/migrations/0008_user_email_case_insensitive.py](../accounts/migrations/0008_user_email_case_insensitive.py)
- [accounts/migrations/0009_user_avatar.py](../accounts/migrations/0009_user_avatar.py)
- [accounts/migrations/0010_user_avatar_thirty.py](../accounts/migrations/0010_user_avatar_thirty.py)

### workplaces

- [workplaces/migrations/0001_initial.py](../workplaces/migrations/0001_initial.py)
- [workplaces/migrations/0002_backfill_default_workplaces.py](../workplaces/migrations/0002_backfill_default_workplaces.py)
- [workplaces/migrations/0003_workplace_workplace_photo.py](../workplaces/migrations/0003_workplace_workplace_photo.py)
- [workplaces/migrations/0004_workplace_code_workplace_description_and_more.py](../workplaces/migrations/0004_workplace_code_workplace_description_and_more.py)
- [workplaces/migrations/0005_backfill_workplace_codes.py](../workplaces/migrations/0005_backfill_workplace_codes.py)
- [workplaces/migrations/0006_sidebarfavorite.py](../workplaces/migrations/0006_sidebarfavorite.py)
- [workplaces/migrations/0007_sidebarfavorite_position.py](../workplaces/migrations/0007_sidebarfavorite_position.py)
- [workplaces/migrations/0008_team_invitations.py](../workplaces/migrations/0008_team_invitations.py)
- [workplaces/migrations/0009_workplace_avatar.py](../workplaces/migrations/0009_workplace_avatar.py)
- [workplaces/migrations/0010_random_workspace_identifiers.py](../workplaces/migrations/0010_random_workspace_identifiers.py)

### tasks

- [tasks/migrations/0001_initial.py](../tasks/migrations/0001_initial.py)
- [tasks/migrations/0002_taskproject_tasksection_task_section.py](../tasks/migrations/0002_taskproject_tasksection_task_section.py)
- [tasks/migrations/0003_alter_taskproject_code.py](../tasks/migrations/0003_alter_taskproject_code.py)
- [tasks/migrations/0004_taskproject_icon.py](../tasks/migrations/0004_taskproject_icon.py)
- [tasks/migrations/0005_taskproject_description.py](../tasks/migrations/0005_taskproject_description.py)
- [tasks/migrations/0006_tasksection_icon.py](../tasks/migrations/0006_tasksection_icon.py)
- [tasks/migrations/0007_allow_blank_task_icons.py](../tasks/migrations/0007_allow_blank_task_icons.py)
- [tasks/migrations/0008_extend_task_priority_choices.py](../tasks/migrations/0008_extend_task_priority_choices.py)
- [tasks/migrations/0009_tasksection_description.py](../tasks/migrations/0009_tasksection_description.py)
- [tasks/migrations/0010_tasktag_task_tags_tasktag_unique_task_tag_per_user.py](../tasks/migrations/0010_tasktag_task_tags_tasktag_unique_task_tag_per_user.py)
- [tasks/migrations/0011_tasktag_description.py](../tasks/migrations/0011_tasktag_description.py)
- [tasks/migrations/0012_unique_task_project_code_per_user.py](../tasks/migrations/0012_unique_task_project_code_per_user.py)
- [tasks/migrations/0013_task_time_spent.py](../tasks/migrations/0013_task_time_spent.py)
- [tasks/migrations/0014_ensure_time_spent_columns.py](../tasks/migrations/0014_ensure_time_spent_columns.py)
- [tasks/migrations/0015_task_parent.py](../tasks/migrations/0015_task_parent.py)
- [tasks/migrations/0016_relax_legacy_time_spent.py](../tasks/migrations/0016_relax_legacy_time_spent.py)
- [tasks/migrations/0017_taskactivity.py](../tasks/migrations/0017_taskactivity.py)
- [tasks/migrations/0018_project_code_numbering.py](../tasks/migrations/0018_project_code_numbering.py)
- [tasks/migrations/0019_tasktag_code.py](../tasks/migrations/0019_tasktag_code.py)
- [tasks/migrations/0020_global_project_codes.py](../tasks/migrations/0020_global_project_codes.py)
- [tasks/migrations/0021_random_project_codes.py](../tasks/migrations/0021_random_project_codes.py)
- [tasks/migrations/0022_task_due_at.py](../tasks/migrations/0022_task_due_at.py)
- [tasks/migrations/0023_alter_task_section_cascade.py](../tasks/migrations/0023_alter_task_section_cascade.py)
- [tasks/migrations/0024_extend_lucide_icon_names.py](../tasks/migrations/0024_extend_lucide_icon_names.py)
- [tasks/migrations/0025_taskproject_priority_due_at_company.py](../tasks/migrations/0025_taskproject_priority_due_at_company.py)
- [tasks/migrations/0026_extend_taskproject_priority_choices.py](../tasks/migrations/0026_extend_taskproject_priority_choices.py)
- [tasks/migrations/0027_tasksection_priority.py](../tasks/migrations/0027_tasksection_priority.py)
- [tasks/migrations/0028_taskproject_responsible_user.py](../tasks/migrations/0028_taskproject_responsible_user.py)
- [tasks/migrations/0029_task_task_section_parent_idx_and_more.py](../tasks/migrations/0029_task_task_section_parent_idx_and_more.py)
- [tasks/migrations/0030_base36_hierarchy_codes.py](../tasks/migrations/0030_base36_hierarchy_codes.py)
- [tasks/migrations/0031_base36_tag_codes.py](../tasks/migrations/0031_base36_tag_codes.py)
- [tasks/migrations/0032_task_crm_fields.py](../tasks/migrations/0032_task_crm_fields.py)
- [tasks/migrations/0033_taskproject_budget_amount_taskproject_currency_and_more.py](../tasks/migrations/0033_taskproject_budget_amount_taskproject_currency_and_more.py)
- [tasks/migrations/0034_remove_tasktag_unique_task_tag_per_user_and_more.py](../tasks/migrations/0034_remove_tasktag_unique_task_tag_per_user_and_more.py)
- [tasks/migrations/0035_tasktag_automation_rules_tasktag_category_and_more.py](../tasks/migrations/0035_tasktag_automation_rules_tasktag_category_and_more.py)
- [tasks/migrations/0036_taskprojectnote.py](../tasks/migrations/0036_taskprojectnote.py)
- [tasks/migrations/0037_tasksectionnote.py](../tasks/migrations/0037_tasksectionnote.py)
- [tasks/migrations/0038_tasktagnote.py](../tasks/migrations/0038_tasktagnote.py)
- [tasks/migrations/0039_remove_taskproject_unique_task_project_code_and_more.py](../tasks/migrations/0039_remove_taskproject_unique_task_project_code_and_more.py)
- [tasks/migrations/0040_note_edited_at.py](../tasks/migrations/0040_note_edited_at.py)
- [tasks/migrations/0041_taskprojectfieldoption.py](../tasks/migrations/0041_taskprojectfieldoption.py)
- [tasks/migrations/0042_remove_task_task_user_company_status_idx_and_more.py](../tasks/migrations/0042_remove_task_task_user_company_status_idx_and_more.py)
- [tasks/migrations/0043_retire_entity_icons.py](../tasks/migrations/0043_retire_entity_icons.py)
- [tasks/migrations/0044_taskprojectdeadlinerule.py](../tasks/migrations/0044_taskprojectdeadlinerule.py)
- [tasks/migrations/0045_project_specific_deadline_rules.py](../tasks/migrations/0045_project_specific_deadline_rules.py)
- [tasks/migrations/0046_project_source_options.py](../tasks/migrations/0046_project_source_options.py)
- [tasks/migrations/0047_task_unique_tasks_number_per_workspace.py](../tasks/migrations/0047_task_unique_tasks_number_per_workspace.py)
- [tasks/migrations/0048_taskprojecttemplate.py](../tasks/migrations/0048_taskprojecttemplate.py)
- [tasks/migrations/0049_taskprojecttemplate_template_name.py](../tasks/migrations/0049_taskprojecttemplate_template_name.py)
- [tasks/migrations/0050_task_work_log.py](../tasks/migrations/0050_task_work_log.py)
- [tasks/migrations/0051_legacy_logged_seconds_default.py](../tasks/migrations/0051_legacy_logged_seconds_default.py)
- [tasks/migrations/0052_comment_images.py](../tasks/migrations/0052_comment_images.py)
- [tasks/migrations/0053_comment_attachment_size.py](../tasks/migrations/0053_comment_attachment_size.py)
- [tasks/migrations/0054_project_visibility.py](../tasks/migrations/0054_project_visibility.py)
- [tasks/migrations/0055_project_sharing.py](../tasks/migrations/0055_project_sharing.py)
- [tasks/migrations/0056_project_invitations.py](../tasks/migrations/0056_project_invitations.py)
- [tasks/migrations/0057_project_observer.py](../tasks/migrations/0057_project_observer.py)
- [tasks/migrations/0058_section_sharing.py](../tasks/migrations/0058_section_sharing.py)
- [tasks/migrations/0059_direct_sharing.py](../tasks/migrations/0059_direct_sharing.py)
- [tasks/migrations/0060_task_sharing.py](../tasks/migrations/0060_task_sharing.py)
- [tasks/migrations/0061_directory_favorites.py](../tasks/migrations/0061_directory_favorites.py)
- [tasks/migrations/0062_task_favorites.py](../tasks/migrations/0062_task_favorites.py)
- [tasks/migrations/0063_remove_project_field_settings.py](../tasks/migrations/0063_remove_project_field_settings.py)
- [tasks/migrations/0064_space_tags.py](../tasks/migrations/0064_space_tags.py)
- [tasks/migrations/0065_space_tag_data.py](../tasks/migrations/0065_space_tag_data.py)
- [tasks/migrations/0066_task_space_archived_taskproject_space_archived.py](../tasks/migrations/0066_task_space_archived_taskproject_space_archived.py)

### kanban

- [kanban/migrations/0001_initial.py](../kanban/migrations/0001_initial.py)
- [kanban/migrations/0002_taskproject_tasksection_task_section.py](../kanban/migrations/0002_taskproject_tasksection_task_section.py)
- [kanban/migrations/0003_alter_taskproject_code.py](../kanban/migrations/0003_alter_taskproject_code.py)
- [kanban/migrations/0004_taskproject_icon.py](../kanban/migrations/0004_taskproject_icon.py)
- [kanban/migrations/0005_taskproject_description.py](../kanban/migrations/0005_taskproject_description.py)
- [kanban/migrations/0006_tasksection_icon.py](../kanban/migrations/0006_tasksection_icon.py)
- [kanban/migrations/0007_allow_blank_task_icons.py](../kanban/migrations/0007_allow_blank_task_icons.py)
- [kanban/migrations/0008_extend_task_priority_choices.py](../kanban/migrations/0008_extend_task_priority_choices.py)
- [kanban/migrations/0009_tasksection_description.py](../kanban/migrations/0009_tasksection_description.py)
- [kanban/migrations/0010_tasktag_task_tags_tasktag_unique_task_tag_per_user.py](../kanban/migrations/0010_tasktag_task_tags_tasktag_unique_task_tag_per_user.py)
- [kanban/migrations/0011_tasktag_description.py](../kanban/migrations/0011_tasktag_description.py)
- [kanban/migrations/0012_unique_task_project_code_per_user.py](../kanban/migrations/0012_unique_task_project_code_per_user.py)
- [kanban/migrations/0013_task_time_spent.py](../kanban/migrations/0013_task_time_spent.py)
- [kanban/migrations/0014_ensure_time_spent_columns.py](../kanban/migrations/0014_ensure_time_spent_columns.py)
- [kanban/migrations/0015_task_parent.py](../kanban/migrations/0015_task_parent.py)
- [kanban/migrations/0016_relax_legacy_time_spent.py](../kanban/migrations/0016_relax_legacy_time_spent.py)
- [kanban/migrations/0017_taskactivity.py](../kanban/migrations/0017_taskactivity.py)
- [kanban/migrations/0018_project_code_numbering.py](../kanban/migrations/0018_project_code_numbering.py)
- [kanban/migrations/0019_tasktag_code.py](../kanban/migrations/0019_tasktag_code.py)
- [kanban/migrations/0020_kanbanboardcolumn_alter_kanban_status.py](../kanban/migrations/0020_kanbanboardcolumn_alter_kanban_status.py)
- [kanban/migrations/0021_board_columns_belong_to_sections.py](../kanban/migrations/0021_board_columns_belong_to_sections.py)
- [kanban/migrations/0022_alter_kanbanactivity_action.py](../kanban/migrations/0022_alter_kanbanactivity_action.py)
- [kanban/migrations/0023_global_project_codes.py](../kanban/migrations/0023_global_project_codes.py)
- [kanban/migrations/0024_random_workspace_codes.py](../kanban/migrations/0024_random_workspace_codes.py)
- [kanban/migrations/0025_extend_lucide_icon_names.py](../kanban/migrations/0025_extend_lucide_icon_names.py)
- [kanban/migrations/0026_base36_tag_codes.py](../kanban/migrations/0026_base36_tag_codes.py)
- [kanban/migrations/0027_remove_kanbantag_unique_kanban_tag_per_user_and_more.py](../kanban/migrations/0027_remove_kanbantag_unique_kanban_tag_per_user_and_more.py)
- [kanban/migrations/0028_prepare_shared_task_tags.py](../kanban/migrations/0028_prepare_shared_task_tags.py)
- [kanban/migrations/0029_use_shared_task_tags.py](../kanban/migrations/0029_use_shared_task_tags.py)
- [kanban/migrations/0030_kanbanprojectnote.py](../kanban/migrations/0030_kanbanprojectnote.py)
- [kanban/migrations/0031_remove_kanbantag_unique_kanban_tag_code_and_more.py](../kanban/migrations/0031_remove_kanbantag_unique_kanban_tag_code_and_more.py)
- [kanban/migrations/0032_kanbanprojectnote_edited_at.py](../kanban/migrations/0032_kanbanprojectnote_edited_at.py)
- [kanban/migrations/0033_retire_entity_icons.py](../kanban/migrations/0033_retire_entity_icons.py)
- [kanban/migrations/0034_kanban_unique_kanban_number_per_workspace.py](../kanban/migrations/0034_kanban_unique_kanban_number_per_workspace.py)
- [kanban/migrations/0035_kanban_due_at.py](../kanban/migrations/0035_kanban_due_at.py)
- [kanban/migrations/0036_comment_images.py](../kanban/migrations/0036_comment_images.py)
- [kanban/migrations/0037_comment_attachment_size.py](../kanban/migrations/0037_comment_attachment_size.py)
- [kanban/migrations/0038_directory_favorites.py](../kanban/migrations/0038_directory_favorites.py)
- [kanban/migrations/0039_sharing.py](../kanban/migrations/0039_sharing.py)

### contacts

- [contacts/migrations/0001_initial.py](../contacts/migrations/0001_initial.py)
- [contacts/migrations/0002_contactactivity.py](../contacts/migrations/0002_contactactivity.py)
- [contacts/migrations/0003_company_contact_company_record_companymembership_and_more.py](../contacts/migrations/0003_company_contact_company_record_companymembership_and_more.py)
- [contacts/migrations/0004_alter_contact_options_contact_middle_name.py](../contacts/migrations/0004_alter_contact_options_contact_middle_name.py)
- [contacts/migrations/0005_company_company_photo.py](../contacts/migrations/0005_company_company_photo.py)
- [contacts/migrations/0006_shareditemlink.py](../contacts/migrations/0006_shareditemlink.py)
- [contacts/migrations/0007_alter_shareditem_permission_and_more.py](../contacts/migrations/0007_alter_shareditem_permission_and_more.py)
- [contacts/migrations/0008_remove_company_unique_company_name_per_owner_and_more.py](../contacts/migrations/0008_remove_company_unique_company_name_per_owner_and_more.py)

### dashboard

- [dashboard/migrations/0001_initial.py](../dashboard/migrations/0001_initial.py)
- [dashboard/migrations/0002_taskreminder_and_more.py](../dashboard/migrations/0002_taskreminder_and_more.py)
- [dashboard/migrations/0003_notificationstate_is_deleted.py](../dashboard/migrations/0003_notificationstate_is_deleted.py)
- [dashboard/migrations/0004_mentions_and_following.py](../dashboard/migrations/0004_mentions_and_following.py)
- [dashboard/migrations/0005_project_invitations.py](../dashboard/migrations/0005_project_invitations.py)
- [dashboard/migrations/0006_section_sharing.py](../dashboard/migrations/0006_section_sharing.py)
- [dashboard/migrations/0007_dashboard_dashboardgadget_and_more.py](../dashboard/migrations/0007_dashboard_dashboardgadget_and_more.py)
- [dashboard/migrations/0008_dashboardgroup.py](../dashboard/migrations/0008_dashboardgroup.py)
- [dashboard/migrations/0009_remove_dashboard_groups.py](../dashboard/migrations/0009_remove_dashboard_groups.py)
- [dashboard/migrations/0010_work_progress_gadget.py](../dashboard/migrations/0010_work_progress_gadget.py)
- [dashboard/migrations/0011_default_dashboard.py](../dashboard/migrations/0011_default_dashboard.py)
- [dashboard/migrations/0012_dashboard_slugs.py](../dashboard/migrations/0012_dashboard_slugs.py)
- [dashboard/migrations/0013_remove_notificationstate_notification_exactly_one_source_and_more.py](../dashboard/migrations/0013_remove_notificationstate_notification_exactly_one_source_and_more.py)
- [dashboard/migrations/0014_savedtaskfilter.py](../dashboard/migrations/0014_savedtaskfilter.py)

### planner

- [planner/migrations/0001_initial.py](../planner/migrations/0001_initial.py)
- [planner/migrations/0002_calendarevent_workplace.py](../planner/migrations/0002_calendarevent_workplace.py)

### documents

- [documents/migrations/0001_initial.py](../documents/migrations/0001_initial.py)
- [documents/migrations/0002_documentlibrary_and_more.py](../documents/migrations/0002_documentlibrary_and_more.py)
- [documents/migrations/0003_documentlibrary_photo.py](../documents/migrations/0003_documentlibrary_photo.py)
- [documents/migrations/0004_workspacedocumentfolder_workspacedocument_and_more.py](../documents/migrations/0004_workspacedocumentfolder_workspacedocument_and_more.py)
- [documents/migrations/0005_workspacedocument_office_key_and_more.py](../documents/migrations/0005_workspacedocument_office_key_and_more.py)
- [documents/migrations/0006_workspacedocument_tags.py](../documents/migrations/0006_workspacedocument_tags.py)
- [documents/migrations/0007_workspacedocumentfolder_is_starred.py](../documents/migrations/0007_workspacedocumentfolder_is_starred.py)
- [documents/migrations/0008_folder_is_starred.py](../documents/migrations/0008_folder_is_starred.py)
- [documents/migrations/0009_drive_office_editor.py](../documents/migrations/0009_drive_office_editor.py)
- [documents/migrations/0010_icon_colors.py](../documents/migrations/0010_icon_colors.py)
- [documents/migrations/0011_workspacedocument_is_pdf_form_and_more.py](../documents/migrations/0011_workspacedocument_is_pdf_form_and_more.py)

### resources

- [resources/migrations/0001_initial.py](../resources/migrations/0001_initial.py)

### spaces

- [spaces/migrations/0001_initial.py](../spaces/migrations/0001_initial.py)
- [spaces/migrations/0002_unify_work.py](../spaces/migrations/0002_unify_work.py)
- [spaces/migrations/0003_space_avatar_space_avatar_photo.py](../spaces/migrations/0003_space_avatar_space_avatar_photo.py)
- [spaces/migrations/0004_issue_types.py](../spaces/migrations/0004_issue_types.py)
- [spaces/migrations/0005_space_slugs.py](../spaces/migrations/0005_space_slugs.py)
- [spaces/migrations/0006_independent_space_tasks.py](../spaces/migrations/0006_independent_space_tasks.py)
- [spaces/migrations/0007_archive_import_sources.py](../spaces/migrations/0007_archive_import_sources.py)
- [spaces/migrations/0008_spacetask_reminder_at_spacetask_task_type_and_more.py](../spaces/migrations/0008_spacetask_reminder_at_spacetask_task_type_and_more.py)
- [spaces/migrations/0009_import_task_membership_dates.py](../spaces/migrations/0009_import_task_membership_dates.py)
