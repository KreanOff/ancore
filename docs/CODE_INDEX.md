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
| [core](../core) | 17 | 0 | 9 | 58 |
| [accounts](../accounts) | 15 | 5 | 8 | 34 |
| [workplaces](../workplaces) | 18 | 8 | 10 | 78 |
| [tasks](../tasks) | 22 | 53 | 33 | 230 |
| [kanban](../kanban) | 10 | 37 | 9 | 73 |
| [contacts](../contacts) | 10 | 8 | 11 | 28 |
| [dashboard](../dashboard) | 17 | 4 | 7 | 91 |
| [planner](../planner) | 9 | 2 | 2 | 7 |
| [documents](../documents) | 37 | 11 | 31 | 203 |

## 2. Modele i relacje

## Modele: core

Brak zadeklarowanych modeli domenowych w tym pliku.

## Modele: accounts

### `User`

Źródło: [accounts/models.py](../accounts/models.py).

Pola zadeklarowane tutaj: `email` (EmailField), `first_name` (CharField), `middle_name` (CharField), `last_name` (CharField), `profile_photo` (FileField), `phone_number` (CharField), `job_title` (CharField), `bio` (TextField), `presence_status` (CharField), `last_seen_at` (DateTimeField).

Metody/properties: `presence_status_class`, `get_full_name`, `__str__`.

## Modele: workplaces

### `Workplace`

Źródło: [workplaces/models.py](../workplaces/models.py).

Pola zadeklarowane tutaj: `name` (CharField), `description` (TextField), `code` (CharField), `slug` (SlugField), `workplace_photo` (FileField), `owner` (ForeignKey), `members` (ManyToManyField), `created_at` (DateTimeField), `updated_at` (DateTimeField).

| Relacja | Cel | Ustawienia |
| --- | --- | --- |
| `owner` | `settings.AUTH_USER_MODEL` | on_delete=models.CASCADE; related_name='owned_workplaces' |
| `members` | `settings.AUTH_USER_MODEL` | related_name='workplaces'; through='WorkplaceMembership' |

Metody/properties: `_base_slug`, `_unique_slug`, `_base_code`, `_unique_code`, `save`, `initials`, `ensure_owner_membership`, `__str__`.

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

Pola zadeklarowane tutaj: `name` (CharField), `description` (TextField), `code` (CharField), `next_section_code_number` (PositiveIntegerField), `icon` (CharField), `priority` (CharField), `status` (CharField), `stage` (CharField), `health` (CharField), `start_at` (DateField), `due_at` (DateField), `use_custom_deadline_rules` (BooleanField), `budget_amount` (DecimalField), `currency` (CharField), `source` (CharField), `company` (ForeignKey), `responsible_user` (ForeignKey), `user` (ForeignKey), `workplace` (ForeignKey), `created_at` (DateTimeField).

| Relacja | Cel | Ustawienia |
| --- | --- | --- |
| `company` | `'contacts.Company'` | on_delete=models.SET_NULL; related_name='task_projects'; null=True |
| `responsible_user` | `settings.AUTH_USER_MODEL` | on_delete=models.SET_NULL; related_name='responsible_task_projects'; null=True |
| `user` | `settings.AUTH_USER_MODEL` | on_delete=models.CASCADE; related_name='task_projects' |
| `workplace` | `'workplaces.Workplace'` | on_delete=models.CASCADE; related_name='task_projects'; null=True |

Metody/properties: `_code_scope_models`, `_code_exists`, `_generate_unique_code`, `save`, `__str__`, `_field_option_display`, `get_status_display`, `get_stage_display`, `get_health_display`.

### `TaskProjectTemplate`

Źródło: [tasks/models.py](../tasks/models.py).

Pola zadeklarowane tutaj: `user` (ForeignKey), `workplace` (ForeignKey), `name` (CharField), `template_name` (CharField), `description` (TextField), `structure` (JSONField), `created_at` (DateTimeField).

| Relacja | Cel | Ustawienia |
| --- | --- | --- |
| `user` | `settings.AUTH_USER_MODEL` | on_delete=models.CASCADE |
| `workplace` | `'workplaces.Workplace'` | on_delete=models.CASCADE; null=True |

Metody/properties: `__str__`.

### `TaskProjectDeadlineRule`

Źródło: [tasks/models.py](../tasks/models.py).

Pola zadeklarowane tutaj: `owner` (ForeignKey), `workplace` (ForeignKey), `project` (ForeignKey), `days` (PositiveIntegerField), `color` (CharField), `is_active` (BooleanField).

| Relacja | Cel | Ustawienia |
| --- | --- | --- |
| `owner` | `settings.AUTH_USER_MODEL` | on_delete=models.CASCADE |
| `workplace` | `'workplaces.Workplace'` | on_delete=models.CASCADE; null=True |
| `project` | `TaskProject` | on_delete=models.CASCADE; related_name='deadline_rules'; null=True |

Metody/properties: `for_scope`, `active_for_scope`, `color_for_date`.

### `TaskProjectFieldOption`

Źródło: [tasks/models.py](../tasks/models.py).

Pola zadeklarowane tutaj: `owner` (ForeignKey), `workplace` (ForeignKey), `field_type` (CharField), `value` (SlugField), `label` (CharField), `color` (CharField), `position` (PositiveSmallIntegerField), `is_active` (BooleanField), `created_at` (DateTimeField).

| Relacja | Cel | Ustawienia |
| --- | --- | --- |
| `owner` | `settings.AUTH_USER_MODEL` | on_delete=models.CASCADE; related_name='task_project_field_options' |
| `workplace` | `'workplaces.Workplace'` | on_delete=models.CASCADE; related_name='task_project_field_options'; null=True |

Metody/properties: `__str__`, `save`, `project_value`, `for_scope`, `ensure_defaults`, `active_for_scope`, `unique_value_for_label`, `is_used`.

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

Pola zadeklarowane tutaj: `project` (ForeignKey), `title` (CharField), `description` (TextField), `code` (CharField), `code_number` (PositiveIntegerField), `next_task_code_number` (PositiveIntegerField), `priority` (CharField), `status` (CharField), `kind` (CharField), `icon` (CharField), `owner` (ForeignKey), `due_at` (DateField), `wip_limit` (PositiveIntegerField), `order` (PositiveIntegerField), `created_at` (DateTimeField).

| Relacja | Cel | Ustawienia |
| --- | --- | --- |
| `project` | `TaskProject` | on_delete=models.CASCADE; related_name='sections' |
| `owner` | `settings.AUTH_USER_MODEL` | on_delete=models.SET_NULL; related_name='owned_task_sections'; null=True |

Metody/properties: `_claim_next_code_number`, `save`, `full_code`, `__str__`.

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

Pola zadeklarowane tutaj: `name` (CharField), `description` (TextField), `code` (CharField), `category` (CharField), `color` (CharField), `icon` (CharField), `priority` (CharField), `scope` (CharField), `owner_label` (CharField), `status` (CharField), `usage_notes` (TextField), `automation_rules` (TextField), `user` (ForeignKey), `workplace` (ForeignKey), `related_tags` (ManyToManyField), `created_at` (DateTimeField).

| Relacja | Cel | Ustawienia |
| --- | --- | --- |
| `user` | `settings.AUTH_USER_MODEL` | on_delete=models.CASCADE; related_name='task_tags' |
| `workplace` | `'workplaces.Workplace'` | on_delete=models.CASCADE; related_name='task_tags'; null=True |
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

Pola zadeklarowane tutaj: `task_id` (PositiveIntegerField), `code_number` (PositiveIntegerField), `title` (CharField), `description` (TextField), `priority` (CharField), `status` (CharField), `is_completed` (BooleanField), `created_at` (DateTimeField), `completion_date` (DateTimeField), `due_at` (DateTimeField), `reminder_at` (DateTimeField), `estimated_minutes` (PositiveIntegerField), `time_spent_hours` (PositiveIntegerField), `time_spent_minutes` (PositiveIntegerField), `task_type` (CharField), `blocked_reason` (TextField), `user` (ForeignKey), `workplace` (ForeignKey), `assignee` (ForeignKey), `section` (ForeignKey), `tags` (ManyToManyField), `parent` (ForeignKey).

| Relacja | Cel | Ustawienia |
| --- | --- | --- |
| `user` | `settings.AUTH_USER_MODEL` | on_delete=models.CASCADE; related_name='tasks' |
| `workplace` | `'workplaces.Workplace'` | on_delete=models.CASCADE; related_name='tasks'; null=True |
| `assignee` | `settings.AUTH_USER_MODEL` | on_delete=models.SET_NULL; related_name='assigned_tasks'; null=True |
| `section` | `TaskSection` | on_delete=models.CASCADE; related_name='tasks'; null=True |
| `tags` | `TaskTag` | related_name='tasks' |
| `parent` | `'self'` | on_delete=models.CASCADE; related_name='subtasks'; null=True |

Metody/properties: `_claim_next_code_number`, `save`, `delete`, `_renumber_user_tasks`, `__str__`, `code`, `full_code`, `_activity_datetime`, `_activity_time_spent`, `has_time_spent`, `time_spent_label`, `due_urgency`, `get_file_extension`.

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

Pola zadeklarowane tutaj: `name` (CharField), `description` (TextField), `code` (CharField), `icon` (CharField), `priority` (CharField), `status` (CharField), `stage` (CharField), `health` (CharField), `start_at` (DateField), `due_at` (DateField), `budget_amount` (DecimalField), `currency` (CharField), `source` (CharField), `company` (ForeignKey), `responsible_user` (ForeignKey), `user` (ForeignKey), `workplace` (ForeignKey), `created_at` (DateTimeField).

| Relacja | Cel | Ustawienia |
| --- | --- | --- |
| `company` | `'contacts.Company'` | on_delete=models.SET_NULL; related_name='kanban_projects'; null=True |
| `responsible_user` | `settings.AUTH_USER_MODEL` | on_delete=models.SET_NULL; related_name='responsible_kanban_projects'; null=True |
| `user` | `settings.AUTH_USER_MODEL` | on_delete=models.CASCADE; related_name='kanban_projects' |
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

Pola zadeklarowane tutaj: `project` (ForeignKey), `title` (CharField), `description` (TextField), `kind` (CharField), `icon` (CharField), `order` (PositiveIntegerField), `created_at` (DateTimeField).

| Relacja | Cel | Ustawienia |
| --- | --- | --- |
| `project` | `KanbanProject` | on_delete=models.CASCADE; related_name='sections' |

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

Pola zadeklarowane tutaj: `user` (ForeignKey), `task_activity` (ForeignKey), `kanban_activity` (ForeignKey), `invitation` (ForeignKey), `reminder` (ForeignKey), `is_read` (BooleanField), `is_archived` (BooleanField), `is_deleted` (BooleanField).

| Relacja | Cel | Ustawienia |
| --- | --- | --- |
| `user` | `settings.AUTH_USER_MODEL` | on_delete=models.CASCADE |
| `task_activity` | `'tasks.TaskActivity'` | on_delete=models.CASCADE; null=True |
| `kanban_activity` | `'kanban.KanbanActivity'` | on_delete=models.CASCADE; null=True |
| `invitation` | `'workplaces.WorkplaceInvitation'` | on_delete=models.CASCADE; null=True |
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

## 3. Formularze

Wypisane są deklaracje klas, także bazowe klasy i widgety.

### core

Źródło: [core/forms.py](../core/forms.py).


### accounts

Źródło: [accounts/forms.py](../accounts/forms.py).

- `UserRegistrationForm` — Meta.fields: `('first_name', 'middle_name', 'last_name', 'email')`
- `UserProfileForm` — Meta.fields: `('profile_photo', 'first_name', 'middle_name', 'last_name', 'email', 'username', 'phone_number', 'job_title', 'bio', 'presence_status')`

### workplaces

Źródło: [workplaces/forms.py](../workplaces/forms.py).

- `WorkplaceForm` — Meta.fields: `['workplace_photo', 'name', 'code', 'description']`

### tasks

Źródło: [tasks/forms.py](../tasks/forms.py).

- `LenientModelChoiceField`
- `DateTimeLocalInput`
- `MultipleFileInput`
- `TaskForm` — Meta.fields: `['title', 'parent', 'section', 'tags', 'description', 'task_type', 'assignee', 'priority', 'status', 'due_at', 'reminder_at']`
- `TaskWorkLogForm` — Meta.fields: `['started_at', 'ended_at', 'description']`
- `TaskProjectBaseForm`
- `TaskProjectDeadlineRuleForm` — Meta.fields: `['days', 'color']`
- `TaskProjectFieldOptionForm` — Meta.fields: `['label', 'color']`
- `TaskProjectTemplateNameForm` — Meta.fields: `('template_name',)`
- `TaskProjectForm` — Meta.fields: `['name', 'template', 'code', 'section_title', 'section_code', 'description', 'company', 'responsible_user', 'status', 'stage', 'health', 'priority', 'start_at', 'due_at', 'source']`
- `TaskProjectRenameForm` — Meta.fields: `['name', 'code', 'description', 'company', 'responsible_user', 'status', 'stage', 'health', 'priority', 'start_at', 'due_at', 'source']`
- `TaskSectionForm` — Meta.fields: `['title', 'code', 'description', 'kind', 'status', 'owner', 'priority', 'due_at', 'wip_limit']`
- `TaskSectionRenameForm` — Meta.fields: `['title', 'code', 'description', 'kind', 'status', 'owner', 'priority', 'due_at', 'wip_limit']`
- `TaskTagForm` — Meta.fields: `['name', 'description', 'category', 'color', 'icon', 'priority', 'scope', 'owner_label', 'status', 'usage_notes', 'automation_rules', 'related_tags']`
- `QuickTaskForm` — Meta.fields: `['title']`
- `TaskModalForm` — Meta.fields: `['title', 'section', 'tags', 'description', 'task_type', 'assignee', 'priority', 'status', 'due_at', 'reminder_at']`
- `SubTaskModalForm` — Meta.fields: `['title', 'description', 'status', 'due_at']`

### kanban

Źródło: [kanban/forms.py](../kanban/forms.py).

- `LenientModelChoiceField`
- `TwoDigitNumberInput`
- `DynamicStatusFormMixin`
- `MultipleFileInput`
- `KanbanForm` — Meta.fields: `['title', 'parent', 'section', 'tags', 'description', 'priority', 'status', 'due_at', 'time_spent_hours', 'time_spent_minutes']`
- `KanbanProjectBaseForm`
- `KanbanProjectForm` — Meta.fields: `['name', 'section_title', 'description', 'company', 'responsible_user', 'status', 'stage', 'health', 'priority', 'start_at', 'due_at', 'budget_amount', 'currency', 'source']`
- `KanbanProjectRenameForm` — Meta.fields: `['name', 'description', 'company', 'responsible_user', 'status', 'stage', 'health', 'priority', 'start_at', 'due_at', 'budget_amount', 'currency', 'source']`
- `KanbanSectionForm` — Meta.fields: `['title', 'description']`
- `KanbanSectionRenameForm` — Meta.fields: `['title', 'description']`
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

## 4. Routing

Ścieżki modułowe są względne wobec include'a w głównym routingu.

### ancore/urls.py

Źródło: [ancore/urls.py](../ancore/urls.py).

| Ścieżka / regex | Widok / include | Nazwa |
| --- | --- | --- |
| `'drive-office-service/<uuid:pk>/source/'` | `suite_views.source` | 'drive-office-service-source' |
| `'drive-office-service/<uuid:pk>/callback/'` | `suite_views.callback` | 'drive-office-service-callback' |
| `'office-service/<uuid:pk>/source/'` | `suite_views.source` | 'office-service-source' |
| `'office-service/<uuid:pk>/callback/'` | `suite_views.callback` | 'office-service-callback' |
| `'admin/'` | `admin.site.urls` | — |
| `''` | `include('dashboard.urls')` | — |
| `'accounts/'` | `include('accounts.urls')` | — |
| `'^workplaces/[-a-zA-Z0-9_]+/tasks/'` | `include((tasks_urls.urlpatterns, 'workplace_tasks'), namespace='workplace_tasks')` | — |
| `'^workplaces/[-a-zA-Z0-9_]+/kanban/'` | `include((kanban_urls.urlpatterns, 'workplace_kanban'), namespace='workplace_kanban')` | — |
| `'^workplaces/[-a-zA-Z0-9_]+/contacts/'` | `include((contacts_urls.urlpatterns, 'workplace_contacts'), namespace='workplace_contacts')` | — |
| `'^workplaces/[-a-zA-Z0-9_]+/calendar/'` | `include((planner_urls.urlpatterns, 'workplace_planner'), namespace='workplace_planner')` | — |
| `'^workplaces/[-a-zA-Z0-9_]+/documents/'` | `include((documents_urls.urlpatterns, 'workplace_documents'), namespace='workplace_documents')` | — |
| `'^workplaces/[-a-zA-Z0-9_]+/office/'` | `include((office_urls.urlpatterns, 'workplace_office'), namespace='workplace_office')` | — |
| `'workplaces/'` | `include('workplaces.urls')` | — |
| `'documents/'` | `include('documents.urls')` | — |
| `'office/'` | `include('documents.workspace_urls')` | — |
| `'tasks/'` | `include('tasks.urls')` | — |
| `'kanban/'` | `include('kanban.urls')` | — |
| `'contacts/'` | `include('contacts.urls')` | — |
| `'calendar/'` | `include('planner.urls')` | — |

### accounts/urls.py

Źródło: [accounts/urls.py](../accounts/urls.py).

| Ścieżka / regex | Widok / include | Nazwa |
| --- | --- | --- |
| `'login/'` | `auth_views.LoginView.as_view(template_name='accounts/login.html')` | 'login' |
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
| `'comment-images/<int:image_id>/'` | `tasks.comment_image` | 'comment_image' |
| `'follow/<str:kind>/<int:object_id>/'` | `follow_object` | 'follow_object' |
| `''` | `tasks.tasks` | 'tasks' |
| `'templates/'` | `project_templates` | 'project_templates' |
| `'templates/<int:template_id>/edit/'` | `edit_project_template` | 'edit_project_template' |
| `'groups/<int:section_id>/'` | `tasks.task_group` | 'task_group' |
| `'view-task/<int:task_id>/'` | `tasks.view_task` | 'view-task' |
| `'view-subtask/<int:task_id>/'` | `tasks.view_subtask` | 'view-subtask' |
| `'update/<int:task_id>/'` | `tasks.update_task_status` | 'update_task_status' |
| `'attachments/<int:attachment_id>/download/'` | `tasks.download_attachment` | 'download_attachment' |
| `'delete-attachment/<int:attachment_id>/'` | `tasks.delete_attachment` | 'delete_attachment' |
| `'delete/<int:task_id>/'` | `tasks.delete_task` | 'delete_task' |
| `'delete/'` | `tasks.delete_tasks` | 'delete_tasks' |
| `'bulk-update-status/'` | `tasks.bulk_update_status` | 'bulk_update_status' |

### kanban/urls.py

Źródło: [kanban/urls.py](../kanban/urls.py).

| Ścieżka / regex | Widok / include | Nazwa |
| --- | --- | --- |
| `'comment-images/<int:image_id>/'` | `tasks.comment_image` | 'comment_image' |
| `'follow/<str:kind>/<int:object_id>/'` | `follow_object` | 'follow_object' |
| `''` | `tasks.tasks` | 'tasks' |
| `'groups/<int:section_id>/'` | `tasks.task_group` | 'task_group' |
| `'view-task/<int:task_id>/'` | `tasks.view_task` | 'view-task' |
| `'view-subtask/<int:task_id>/'` | `tasks.view_subtask` | 'view-subtask' |
| `'update/<int:task_id>/'` | `tasks.update_task_status` | 'update_task_status' |
| `'groups/<int:section_id>/reorder-columns/'` | `tasks.reorder_board_columns` | 'reorder_board_columns' |
| `'attachments/<int:attachment_id>/download/'` | `tasks.download_attachment` | 'download_attachment' |
| `'delete-attachment/<int:attachment_id>/'` | `tasks.delete_attachment` | 'delete_attachment' |
| `'delete/<int:task_id>/'` | `tasks.delete_task` | 'delete_task' |
| `'delete/'` | `tasks.delete_tasks` | 'delete_tasks' |
| `'bulk-update-status/'` | `tasks.bulk_update_status` | 'bulk_update_status' |

### contacts/urls.py

Źródło: [contacts/urls.py](../contacts/urls.py).

| Ścieżka / regex | Widok / include | Nazwa |
| --- | --- | --- |
| `''` | `views.contacts` | 'contacts' |
| `'users/'` | `views.user_directory` | 'user-directory' |
| `'users/lookup/'` | `views.lookup_ancore_login` | 'lookup-ancore-login' |
| `'users/<int:user_id>/add/'` | `views.add_user_contact` | 'add-user-contact' |
| `'companies/'` | `views.companies` | 'companies' |
| `'companies/<int:company_id>/'` | `views.view_company` | 'view-company' |
| `'companies/<int:company_id>/edit/'` | `views.edit_company` | 'edit-company' |
| `'companies/<int:company_id>/delete/'` | `views.delete_company` | 'delete-company' |
| `'guests/'` | `views.guest_contacts` | 'guests' |
| `'view-contact/<int:contact_id>/'` | `views.view_contact` | 'view-contact' |
| `'view-contact/<int:contact_id>/edit/'` | `views.edit_contact` | 'edit-contact' |
| `'delete/<int:contact_id>/'` | `views.delete_contact` | 'delete' |

### dashboard/urls.py

Źródło: [dashboard/urls.py](../dashboard/urls.py).

| Ścieżka / regex | Widok / include | Nazwa |
| --- | --- | --- |
| `'global-search/'` | `views.global_search` | 'global_search' |
| `'settings/'` | `views.settings` | 'settings' |
| `'settings/project-fields/'` | `project_field_settings` | 'project_field_settings' |
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
- [core/comment_images.py](../core/comment_images.py) — `comment_image_storage`, `comment_image_path`, `CommentImage`, `delete_comment_image_file`, `save_comment`, `comment_image_response`
- [core/forms.py](../core/forms.py)
- [core/media.py](../core/media.py) — `public_media`
- [core/models.py](../core/models.py)
- [core/task_numbering.py](../core/task_numbering.py) — `lock_task_numbers`, `renumber_tasks`
- [core/task_requests.py](../core/task_requests.py) — `task_detail_lookup`, `task_primary_keys`
- [core/upload_validation.py](../core/upload_validation.py) — `validate_image_bytes`, `validate_image_crop`, `validate_image_upload`, `validate_attachment_upload`, `validate_comment_attachments`, `attachment_download_response`
- [core/views/__init__.py](../core/views/__init__.py)

### accounts

- [accounts/__init__.py](../accounts/__init__.py)
- [accounts/admin.py](../accounts/admin.py) — `CustomUserAdmin`
- [accounts/apps.py](../accounts/apps.py) — `AccountsConfig`
- [accounts/avatar.py](../accounts/avatar.py) — `avatar_color_seed`, `avatar_color_style`, `avatar_color_style_from_seed`, `avatar_color_class`, `account_avatar`
- [accounts/context_processors.py](../accounts/context_processors.py) — `current_account_avatar`
- [accounts/forms.py](../accounts/forms.py) — `UserRegistrationForm`, `UserProfileForm`
- [accounts/middleware.py](../accounts/middleware.py) — `UserPresenceMiddleware`
- [accounts/models.py](../accounts/models.py) — `User`, `normalize_public_username`, `default_public_username`, `unique_public_username`
- [accounts/presence.py](../accounts/presence.py) — `idle_seconds`, `heartbeat_seconds`, `write_throttle_seconds`, `mark_user_seen`, `mark_user_inactive`, `sync_stale_presence_statuses`
- [accounts/templatetags/__init__.py](../accounts/templatetags/__init__.py)
- [accounts/templatetags/account_avatar.py](../accounts/templatetags/account_avatar.py) — `user_avatar`
- [accounts/urls.py](../accounts/urls.py)
- [accounts/views.py](../accounts/views.py) — `AccountLogoutView`, `register`, `profile`, `update_presence_status`, `add_account`, `switch_account`, `remove_account`, `presence_ping`

### workplaces

- [workplaces/__init__.py](../workplaces/__init__.py)
- [workplaces/admin.py](../workplaces/admin.py) — `WorkplaceMembershipInline`, `WorkplaceAdmin`, `WorkplaceMembershipAdmin`, `SidebarFavoriteAdmin`
- [workplaces/apps.py](../workplaces/apps.py) — `WorkplacesConfig`
- [workplaces/context_processors.py](../workplaces/context_processors.py) — `current_workplace`
- [workplaces/forms.py](../workplaces/forms.py) — `WorkplaceForm`
- [workplaces/middleware.py](../workplaces/middleware.py) — `ActiveWorkplaceMiddleware`
- [workplaces/models.py](../workplaces/models.py) — `Workplace`, `WorkplaceMembership`, `invitation_expiry`, `WorkplaceInvitation`, `SidebarFavorite`, `create_workplace_for_user`
- [workplaces/navigation.py](../workplaces/navigation.py) — `sidebar_favorite_catalog`, `sidebar_favorite_is_active`, `sidebar_favorites_for_request`
- [workplaces/services.py](../workplaces/services.py) — `workplace_management_url`, `pending_invitations_for_user`, `workplaces_for_user`, `workplace_role`, `can_manage_team`, `workspace_owner`, `workplace_people`, `ensure_default_workplace`, `set_active_workplace`, `backfill_legacy_records_for_workplace`, `enable_workspace_url_scope`, `workspace_url_scope_enabled`, `scoped_workplace_app_path`, `legacy_app_path_to_scoped`, `get_active_workplace`
- [workplaces/team_views.py](../workplaces/team_views.py) — `InvitationForm`, `team`, `team_context`, `invitation_response`, `member_update`, `invitation_cancel`
- [workplaces/templatetags/__init__.py](../workplaces/templatetags/__init__.py)
- [workplaces/templatetags/sidebar_favorites.py](../workplaces/templatetags/sidebar_favorites.py) — `sidebar_favorite_toggle`
- [workplaces/templatetags/workplace_avatar.py](../workplaces/templatetags/workplace_avatar.py) — `workplace_avatar_seed`, `workplace_avatar`
- [workplaces/urls.py](../workplaces/urls.py)
- [workplaces/views.py](../workplaces/views.py) — `workplaces`, `render_workplaces`, `switch_workplace`, `toggle_sidebar_favorite`, `reorder_sidebar_favorites`, `workplace_home`, `update_workplace`, `delete_workplace`

### tasks

- [tasks/__init__.py](../tasks/__init__.py)
- [tasks/admin.py](../tasks/admin.py) — `TaskAttachmentInline`, `TaskAdmin`, `TaskSectionInline`, `TaskProjectAdmin`, `TaskProjectFieldOptionAdmin`, `TaskSectionAdmin`, `TaskTagAdmin`, `TaskAttachmentAdmin`
- [tasks/apps.py](../tasks/apps.py) — `TasksConfig`
- [tasks/forms.py](../tasks/forms.py) — `LenientModelChoiceField`, `DateTimeLocalInput`, `MultipleFileInput`, `TaskForm`, `TaskWorkLogForm`, `TaskProjectBaseForm`, `TaskProjectDeadlineRuleForm`, `TaskProjectFieldOptionForm`, `TaskProjectTemplateNameForm`, `TaskProjectForm`, `TaskProjectRenameForm`, `TaskSectionForm`, `TaskSectionRenameForm`, `TaskTagForm`, `QuickTaskForm`, `TaskModalForm`, `SubTaskModalForm`
- [tasks/models.py](../tasks/models.py) — `format_base36`, `parse_hierarchy_code_number`, `TaskProject`, `TaskProjectTemplate`, `TaskProjectDeadlineRule`, `TaskProjectFieldOption`, `TaskProjectNote`, `TaskSection`, `TaskSectionNote`, `TaskTag`, `TaskTagNote`, `Task`, `TaskWorkLog`, `TaskAttachment`, `TaskActivity`, `TaskCommentImage`, `auto_delete_file_on_delete`, `create_task_activity_on_create`
- [tasks/project_template_forms.py](../tasks/project_template_forms.py) — `style_fields`, `TemplateDetailsForm`, `TemplateSectionForm`, `TemplateTaskForm`
- [tasks/project_templates.py](../tasks/project_templates.py) — `template_descendants`, `update_template_item`, `delete_template_item`, `save_project_template`, `populate_project_from_template`
- [tasks/urls.py](../tasks/urls.py)
- [tasks/views/__init__.py](../tasks/views/__init__.py)
- [tasks/views/project_settings.py](../tasks/views/project_settings.py) — `project_field_settings`
- [tasks/views/project_templates.py](../tasks/views/project_templates.py) — `project_templates`, `edit_project_template`
- [tasks/views/tasks.py](../tasks/views/tasks.py) — `tasks`, `task_group`, `create_share_link`, `revoke_share_link`, `accept_share_link`, `update_task_status`, `delete_task`, `delete_attachment`, `download_attachment`, `delete_tasks`, `bulk_update_status`, `view_task`, `view_subtask`, `comment_image`
- [tasks/views.py](../tasks/views.py)

### kanban

- [kanban/__init__.py](../kanban/__init__.py)
- [kanban/admin.py](../kanban/admin.py) — `KanbanAttachmentInline`, `TaskAdmin`, `KanbanSectionInline`, `KanbanBoardColumnInline`, `KanbanProjectNoteInline`, `KanbanProjectAdmin`, `KanbanProjectNoteAdmin`, `KanbanSectionAdmin`, `KanbanBoardColumnAdmin`, `KanbanAttachmentAdmin`
- [kanban/apps.py](../kanban/apps.py) — `KanbanConfig`
- [kanban/forms.py](../kanban/forms.py) — `LenientModelChoiceField`, `TwoDigitNumberInput`, `board_column_status_choices`, `DynamicStatusFormMixin`, `MultipleFileInput`, `KanbanForm`, `KanbanProjectBaseForm`, `KanbanProjectForm`, `KanbanProjectRenameForm`, `KanbanSectionForm`, `KanbanSectionRenameForm`, `KanbanTagForm`, `KanbanBoardColumnForm`, `QuickKanbanForm`, `KanbanModalForm`, `SubKanbanModalForm`
- [kanban/models.py](../kanban/models.py) — `KanbanProject`, `KanbanProjectNote`, `KanbanSection`, `KanbanBoardColumn`, `Kanban`, `KanbanAttachment`, `KanbanActivity`, `KanbanCommentImage`, `auto_delete_file_on_delete`, `create_task_activity_on_create`
- [kanban/urls.py](../kanban/urls.py)
- [kanban/views/__init__.py](../kanban/views/__init__.py)
- [kanban/views/tasks.py](../kanban/views/tasks.py) — `tasks`, `task_group`, `reorder_board_columns`, `update_task_status`, `delete_task`, `delete_attachment`, `download_attachment`, `delete_tasks`, `bulk_update_status`, `view_task`, `view_subtask`, `comment_image`

### contacts

- [contacts/__init__.py](../contacts/__init__.py)
- [contacts/admin.py](../contacts/admin.py) — `CompanyMembershipInline`, `CompanyAdmin`, `ContactAdmin`, `UserContactAdmin`, `ContactActivityAdmin`, `SharedItemAdmin`, `SharedItemLinkAdmin`
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
- [dashboard/models.py](../dashboard/models.py) — `ObjectFollow`, `ActivityInterest`, `TaskReminder`, `NotificationState`
- [dashboard/notification_service.py](../dashboard/notification_service.py) — `notification_filters`, `notification_sources`, `filtered_sources`, `notification_summary`, `notification_page`, `change_notification_state`
- [dashboard/overview.py](../dashboard/overview.py) — `dashboard_overview`
- [dashboard/reminders.py](../dashboard/reminders.py) — `reminders_for_user`
- [dashboard/urls.py](../dashboard/urls.py)
- [dashboard/views.py](../dashboard/views.py) — `global_search`, `settings`, `home`, `notifications`, `notification_action`

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

## 6. Szablony

### core

- [core/templates/core/base.html](../core/templates/core/base.html)
- [core/templates/core/includes/attachment_icon.html](../core/templates/core/includes/attachment_icon.html)
- [core/templates/core/includes/attachment_upload_icon.html](../core/templates/core/includes/attachment_upload_icon.html)
- [core/templates/core/includes/bootstrap.html](../core/templates/core/includes/bootstrap.html)
- [core/templates/core/includes/icon_credit.html](../core/templates/core/includes/icon_credit.html)
- [core/templates/core/includes/photo_crop_dialog.html](../core/templates/core/includes/photo_crop_dialog.html)
- [core/templates/core/includes/priority_icon.html](../core/templates/core/includes/priority_icon.html)
- [core/templates/core/includes/settings_secondary_menu.html](../core/templates/core/includes/settings_secondary_menu.html)
- [core/templates/core/includes/trash_icon.html](../core/templates/core/includes/trash_icon.html)

### accounts

- [accounts/templates/accounts/add_account.html](../accounts/templates/accounts/add_account.html)
- [accounts/templates/accounts/auth_base.html](../accounts/templates/accounts/auth_base.html)
- [accounts/templates/accounts/includes/presence_status_icon.html](../accounts/templates/accounts/includes/presence_status_icon.html)
- [accounts/templates/accounts/includes/user_avatar.html](../accounts/templates/accounts/includes/user_avatar.html)
- [accounts/templates/accounts/includes/user_avatar_icon.html](../accounts/templates/accounts/includes/user_avatar_icon.html)
- [accounts/templates/accounts/login.html](../accounts/templates/accounts/login.html)
- [accounts/templates/accounts/profile.html](../accounts/templates/accounts/profile.html)
- [accounts/templates/accounts/register.html](../accounts/templates/accounts/register.html)

### workplaces

- [workplaces/templates/workplaces/includes/invitation_filter.html](../workplaces/templates/workplaces/includes/invitation_filter.html)
- [workplaces/templates/workplaces/includes/invitation_response_modal.html](../workplaces/templates/workplaces/includes/invitation_response_modal.html)
- [workplaces/templates/workplaces/includes/management_toolbar.html](../workplaces/templates/workplaces/includes/management_toolbar.html)
- [workplaces/templates/workplaces/includes/received_invitations.html](../workplaces/templates/workplaces/includes/received_invitations.html)
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
- [tasks/templates/tasks/includes/directory_filter_aggregate.html](../tasks/templates/tasks/includes/directory_filter_aggregate.html)
- [tasks/templates/tasks/includes/directory_members.html](../tasks/templates/tasks/includes/directory_members.html)
- [tasks/templates/tasks/includes/directory_pagination_toolbar.html](../tasks/templates/tasks/includes/directory_pagination_toolbar.html)
- [tasks/templates/tasks/includes/directory_sort_builder.html](../tasks/templates/tasks/includes/directory_sort_builder.html)
- [tasks/templates/tasks/includes/follow_button.html](../tasks/templates/tasks/includes/follow_button.html)
- [tasks/templates/tasks/includes/group_directory_filter_builder.html](../tasks/templates/tasks/includes/group_directory_filter_builder.html)
- [tasks/templates/tasks/includes/project_choice_filter_detail.html](../tasks/templates/tasks/includes/project_choice_filter_detail.html)
- [tasks/templates/tasks/includes/project_deadline_settings.html](../tasks/templates/tasks/includes/project_deadline_settings.html)
- [tasks/templates/tasks/includes/project_directory_filter_sort.html](../tasks/templates/tasks/includes/project_directory_filter_sort.html)
- [tasks/templates/tasks/includes/project_info_modal.html](../tasks/templates/tasks/includes/project_info_modal.html)
- [tasks/templates/tasks/includes/project_note_item.html](../tasks/templates/tasks/includes/project_note_item.html)
- [tasks/templates/tasks/includes/project_text_filter_detail.html](../tasks/templates/tasks/includes/project_text_filter_detail.html)
- [tasks/templates/tasks/includes/section_notes_thread.html](../tasks/templates/tasks/includes/section_notes_thread.html)
- [tasks/templates/tasks/includes/status_pagination.html](../tasks/templates/tasks/includes/status_pagination.html)
- [tasks/templates/tasks/includes/tag_notes_thread.html](../tasks/templates/tasks/includes/tag_notes_thread.html)
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

- [dashboard/templates/dashboard/home.html](../dashboard/templates/dashboard/home.html)
- [dashboard/templates/dashboard/includes/notification_controls.html](../dashboard/templates/dashboard/includes/notification_controls.html)
- [dashboard/templates/dashboard/includes/notification_list.html](../dashboard/templates/dashboard/includes/notification_list.html)
- [dashboard/templates/dashboard/includes/notification_pagination.html](../dashboard/templates/dashboard/includes/notification_pagination.html)
- [dashboard/templates/dashboard/includes/settings_row.html](../dashboard/templates/dashboard/includes/settings_row.html)
- [dashboard/templates/dashboard/project_field_settings.html](../dashboard/templates/dashboard/project_field_settings.html)
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

## 7. Zasoby frontendowe

### css

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
- [static/css/components/settings.css](../static/css/components/settings.css)
- [static/css/components/sticky-note.css](../static/css/components/sticky-note.css)
- [static/css/components/tables.css](../static/css/components/tables.css)
- [static/css/components/task-edit.css](../static/css/components/task-edit.css)
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
- [static/js/flaticon-icons.js](../static/js/flaticon-icons.js)
- [static/js/global-search.js](../static/js/global-search.js)
- [static/js/layout.js](../static/js/layout.js)
- [static/js/modal.js](../static/js/modal.js)
- [static/js/notifications-panel.js](../static/js/notifications-panel.js)
- [static/js/notifications.js](../static/js/notifications.js)
- [static/js/office-suite.js](../static/js/office-suite.js)
- [static/js/office.js](../static/js/office.js)
- [static/js/presence.js](../static/js/presence.js)
- [static/js/profile.js](../static/js/profile.js)
- [static/js/project-templates.js](../static/js/project-templates.js)
- [static/js/row-actions.js](../static/js/row-actions.js)
- [static/js/settings.js](../static/js/settings.js)
- [static/js/sticky-note.js](../static/js/sticky-note.js)
- [static/js/task-work-log.js](../static/js/task-work-log.js)
- [static/js/tasks.js](../static/js/tasks.js)
- [static/js/workplace-team.js](../static/js/workplace-team.js)

### img

- [static/img/favicon-ancore-large.png](../static/img/favicon-ancore-large.png)
- [static/img/logo-ancore.png](../static/img/logo-ancore.png)

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

- `TaskIdentityTests`: 10 metod testowych.
- `ConcurrentTaskNumberTests`: 2 metod testowych.

### core/test_task_number_migrations.py

Źródło: [core/test_task_number_migrations.py](../core/test_task_number_migrations.py).

- `TaskNumberMigrationTests`: 1 metod testowych.

### core/tests.py

Źródło: [core/tests.py](../core/tests.py).

- `UploadValidationTests`: 3 metod testowych.
- `SidebarActiveStateTests`: 16 metod testowych.

### accounts/test_email_identity.py

Źródło: [accounts/test_email_identity.py](../accounts/test_email_identity.py).

- `EmailIdentityTests`: 5 metod testowych.
- `EmailIdentityMigrationTests`: 1 metod testowych.

### accounts/tests.py

Źródło: [accounts/tests.py](../accounts/tests.py).

- `UserRegistrationFormTests`: 2 metod testowych.
- `AuthPageViewTests`: 2 metod testowych.
- `ProfileViewTests`: 13 metod testowych.
- `AccountSwitcherTests`: 11 metod testowych.

### workplaces/test_management.py

Źródło: [workplaces/test_management.py](../workplaces/test_management.py).

- `WorkspaceManagementTests`: 12 metod testowych.

### workplaces/test_team.py

Źródło: [workplaces/test_team.py](../workplaces/test_team.py).

- `TeamAccessTests`: 21 metod testowych.
- `TeamSlugMigrationTests`: 1 metod testowych.

### workplaces/tests.py

Źródło: [workplaces/tests.py](../workplaces/tests.py).

- `WorkplaceSelectionTests`: 44 metod testowych.

### tasks/test_group_directory.py

Źródło: [tasks/test_group_directory.py](../tasks/test_group_directory.py).

- `ProjectGroupDirectoryTests`: 3 metod testowych.

### tasks/test_legacy_time_migration.py

Źródło: [tasks/test_legacy_time_migration.py](../tasks/test_legacy_time_migration.py).

- `LegacyTaskTimeMigrationTests`: 2 metod testowych.

### tasks/test_project_deadline_overrides.py

Źródło: [tasks/test_project_deadline_overrides.py](../tasks/test_project_deadline_overrides.py).

- `ProjectDeadlineOverrideTests`: 11 metod testowych.

### tasks/test_project_deadlines.py

Źródło: [tasks/test_project_deadlines.py](../tasks/test_project_deadlines.py).

- `DeadlineColorTests`: 2 metod testowych.
- `ProjectDeadlineSettingsTests`: 6 metod testowych.

### tasks/test_project_sources.py

Źródło: [tasks/test_project_sources.py](../tasks/test_project_sources.py).

- `ProjectSourceTests`: 12 metod testowych.

### tasks/test_project_templates.py

Źródło: [tasks/test_project_templates.py](../tasks/test_project_templates.py).

- `ProjectTemplateTests`: 29 metod testowych.

### tasks/test_status_pagination.py

Źródło: [tasks/test_status_pagination.py](../tasks/test_status_pagination.py).

- `TaskStatusPaginationTests`: 6 metod testowych.

### tasks/test_work_logs.py

Źródło: [tasks/test_work_logs.py](../tasks/test_work_logs.py).

- `TaskWorkLogTests`: 21 metod testowych.

### tasks/tests.py

Źródło: [tasks/tests.py](../tasks/tests.py).

- `TaskProjectControlStyleTests`: 19 metod testowych.
- `TaskProjectCreationTests`: 119 metod testowych.

### kanban/test_deadlines.py

Źródło: [kanban/test_deadlines.py](../kanban/test_deadlines.py).

- `KanbanDeadlineTests`: 2 metod testowych.

### kanban/tests.py

Źródło: [kanban/tests.py](../kanban/tests.py).

- `KanbanProjectCreationTests`: 71 metod testowych.

### contacts/tests.py

Źródło: [contacts/tests.py](../contacts/tests.py).

- `ContactDirectoryStyleTests`: 1 metod testowych.
- `ContactCollaborationTests`: 27 metod testowych.

### dashboard/test_collaboration.py

Źródło: [dashboard/test_collaboration.py](../dashboard/test_collaboration.py).

- `CollaborationTests`: 21 metod testowych.

### dashboard/test_notifications.py

Źródło: [dashboard/test_notifications.py](../dashboard/test_notifications.py).

- `NotificationCenterTests`: 23 metod testowych.

### dashboard/test_overview.py

Źródło: [dashboard/test_overview.py](../dashboard/test_overview.py).

- `DashboardOverviewTests`: 10 metod testowych.

### dashboard/test_reminders.py

Źródło: [dashboard/test_reminders.py](../dashboard/test_reminders.py).

- `TaskReminderTests`: 8 metod testowych.

### dashboard/test_search_regressions.py

Źródło: [dashboard/test_search_regressions.py](../dashboard/test_search_regressions.py).

- `GlobalSearchRegressionTests`: 6 metod testowych.

### dashboard/test_workspace_invitations.py

Źródło: [dashboard/test_workspace_invitations.py](../dashboard/test_workspace_invitations.py).

- `WorkspaceInvitationNotificationTests`: 10 metod testowych.

### dashboard/tests.py

Źródło: [dashboard/tests.py](../dashboard/tests.py).

- `DashboardViewTests`: 8 metod testowych.
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

## 9. Migracje obecne lokalnie

Obecność na tej liście nie oznacza śledzenia w Git lub zastosowania w bazie.

### accounts

- [accounts/migrations/0001_initial.py](../accounts/migrations/0001_initial.py)
- [accounts/migrations/0005_backfill_public_usernames.py](../accounts/migrations/0005_backfill_public_usernames.py)
- [accounts/migrations/0006_user_last_seen_auto_presence.py](../accounts/migrations/0006_user_last_seen_auto_presence.py)
- [accounts/migrations/0007_alter_user_profile_photo.py](../accounts/migrations/0007_alter_user_profile_photo.py)
- [accounts/migrations/0008_user_email_case_insensitive.py](../accounts/migrations/0008_user_email_case_insensitive.py)

### workplaces

- [workplaces/migrations/0001_initial.py](../workplaces/migrations/0001_initial.py)
- [workplaces/migrations/0002_backfill_default_workplaces.py](../workplaces/migrations/0002_backfill_default_workplaces.py)
- [workplaces/migrations/0003_workplace_workplace_photo.py](../workplaces/migrations/0003_workplace_workplace_photo.py)
- [workplaces/migrations/0004_workplace_code_workplace_description_and_more.py](../workplaces/migrations/0004_workplace_code_workplace_description_and_more.py)
- [workplaces/migrations/0005_backfill_workplace_codes.py](../workplaces/migrations/0005_backfill_workplace_codes.py)
- [workplaces/migrations/0006_sidebarfavorite.py](../workplaces/migrations/0006_sidebarfavorite.py)
- [workplaces/migrations/0007_sidebarfavorite_position.py](../workplaces/migrations/0007_sidebarfavorite_position.py)
- [workplaces/migrations/0008_team_invitations.py](../workplaces/migrations/0008_team_invitations.py)

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
