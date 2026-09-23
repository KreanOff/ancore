import json
from urllib.parse import urlencode

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import Func, Q, TextField, Value
from django.db.models.functions import Lower
from django.http import Http404, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.template.loader import render_to_string
from django.views.decorators.http import require_http_methods

from workplaces.services import scoped_workplace_app_path, workspace_owner
from ..forms import TaskProjectTemplateNameForm
from ..models import Task, TaskProjectTemplate, TaskSection
from ..project_template_forms import TemplateDetailsForm, TemplateSectionForm, TemplateTaskForm
from ..project_templates import delete_template_item, update_template_item


TEMPLATE_PAGE_SIZES = (25, 50, 100)
TEMPLATE_SORT_FIELDS = (
    {'value': 'template_name', 'label': 'Nazwa szablonu', 'icon': 'copy'},
    {'value': 'name', 'label': 'Nazwa projektu', 'icon': 'briefcase-business'},
    {'value': 'description', 'label': 'Opis', 'icon': 'align-left'},
    {'value': 'created_at', 'label': 'Data utworzenia', 'icon': 'calendar-days'},
)


def _template_text(field):
    # Polish case folding also works on databases using the C locale.
    return Lower(Func(field, Value('ĄĆĘŁŃÓŚŹŻ'), Value('ąćęłńóśźż'), function='TRANSLATE', output_field=TextField()))


@login_required
@require_http_methods(['GET', 'POST'])
def project_templates(request):
    workplace = request.workplace
    templates = TaskProjectTemplate.objects.filter(user=workspace_owner(request), workplace=workplace)
    base_url = scoped_workplace_app_path(workplace, 'tasks')
    rename_form = TaskProjectTemplateNameForm()
    rename_template_id = None
    if request.method == 'POST':
        template_id = request.POST.get('template_id', '')
        if not template_id.isdecimal() or len(template_id) > 18:
            raise Http404
        template = get_object_or_404(templates, pk=int(template_id))
        action = request.POST.get('action', 'delete')
        if action == 'rename':
            rename_form = TaskProjectTemplateNameForm(request.POST, instance=template)
            if rename_form.is_valid():
                template.template_name = rename_form.cleaned_data['template_name']
                template.save(update_fields=['template_name'])
                messages.success(request, 'Nazwa szablonu zapisana.')
                return redirect(base_url + 'templates/')
            rename_template_id = template.pk
        elif action == 'delete':
            template.delete()
            messages.success(request, 'Szablon usunięty. Utworzone projekty pozostają bez zmian.')
            return redirect(base_url + 'templates/')
        else:
            raise Http404
    return render(request, 'tasks/project_templates.html', {
        **_directory_context(request),
        'rename_form': rename_form, 'rename_template_id': rename_template_id,
    })


def _directory_context(request):
    templates = TaskProjectTemplate.objects.filter(user=workspace_owner(request), workplace=request.workplace)
    base_url = scoped_workplace_app_path(request.workplace, 'tasks')
    query = request.GET.get('q', '').strip()[:200]
    description_filter = request.GET.get('description_filter', '')
    if description_filter not in {'with', 'without'}:
        description_filter = ''
    if query:
        templates = templates.alias(search_name=_template_text('name'), search_description=_template_text('description'),
                                    search_template_name=_template_text('template_name')).filter(
            Q(search_name__contains=query.lower()) | Q(search_description__contains=query.lower())
            | Q(search_template_name__contains=query.lower()),
        )
    if description_filter == 'with':
        templates = templates.exclude(description='')
    elif description_filter == 'without':
        templates = templates.filter(description='')

    sort = request.GET.get('sort', 'created_at_desc')
    valid_sorts = {f"{field['value']}_{direction}" for field in TEMPLATE_SORT_FIELDS for direction in ('asc', 'desc')}
    if sort not in valid_sorts:
        sort = 'created_at_desc'
    sort_field, sort_direction = sort.rsplit('_', 1)
    if sort_field in {'template_name', 'name', 'description'}:
        expression = _template_text(sort_field)
        templates = templates.order_by(expression.desc() if sort_direction == 'desc' else expression.asc(), 'pk')
    else:
        templates = templates.order_by(('-' if sort_direction == 'desc' else '') + sort_field, 'pk')
    try:
        page_size = int(request.GET.get('page_size', 25))
    except (TypeError, ValueError):
        page_size = 25
    if page_size not in TEMPLATE_PAGE_SIZES:
        page_size = 25
    page = Paginator(templates, page_size).get_page(request.GET.get('page'))
    for template in page:
        template.section_count = len(template.structure.get('sections', []))
        template.task_count = len(template.structure.get('tasks', []))
    params = {'q': query, 'description_filter': description_filter, 'sort': sort, 'page_size': page_size}
    params = {key: value for key, value in params.items() if value != ''}
    templates_url = base_url + 'templates/'
    label = next(field['label'] for field in TEMPLATE_SORT_FIELDS if field['value'] == sort_field)
    direction_label = ('Z–A' if sort_direction == 'desc' else 'A–Z') if sort_field != 'created_at' else ('malejąco' if sort_direction == 'desc' else 'rosnąco')
    return {
        'templates': page, 'tasks_url': base_url, 'templates_url': templates_url,
        'query': query, 'description_filter': description_filter,
        'description_filter_options': ({'value': 'with', 'label': 'Z opisem'}, {'value': 'without', 'label': 'Bez opisu'}),
        'has_active_filters': bool(query or description_filter),
        'sort_param': '' if sort == 'created_at_desc' else sort,
        'default_sort': 'created_at_desc', 'sort_field': sort_field, 'sort_direction': sort_direction,
        'sort_label': f'{label} {direction_label}', 'sort_fields': TEMPLATE_SORT_FIELDS,
        'template_window': {
            'page': page.number, 'total_pages': page.paginator.num_pages,
            'page_size': page_size, 'page_size_options': TEMPLATE_PAGE_SIZES,
            'has_previous': page.has_previous(), 'has_next': page.has_next(),
            'previous_url': templates_url + '?' + urlencode({**params, 'page': page.previous_page_number()}) if page.has_previous() else '',
            'next_url': templates_url + '?' + urlencode({**params, 'page': page.next_page_number()}) if page.has_next() else '',
            'compact_summary': f'{page.start_index()}–{page.end_index()} z {page.paginator.count}',
            'summary': f'Pokazano {page.start_index()}–{page.end_index()} z {page.paginator.count} szablonów',
        },
    }


@login_required
@require_http_methods(['GET', 'POST'])
@transaction.atomic
def edit_project_template(request, template_id):
    templates = TaskProjectTemplate.objects.filter(user=workspace_owner(request), workplace=request.workplace)
    if request.method == 'POST':
        templates = templates.select_for_update()
    template = get_object_or_404(templates, pk=template_id)
    structure = template.structure
    modal_request = request.headers.get('X-Template-Modal') == 'true'
    saved = False
    templates_url = scoped_workplace_app_path(request.workplace, 'tasks', 'templates/')
    editor_url = f'{templates_url}{template.pk}/edit/'
    if request.method == 'GET' and not modal_request:
        return redirect(templates_url)
    details = {field: getattr(template, field) for field in ('template_name', 'name', 'description')}
    details['template_name'] = str(template)
    forms = {
        'details': TemplateDetailsForm(initial=details, prefix='details'),
        'section': TemplateSectionForm(prefix='section'),
        'task': TemplateTaskForm(structure=structure, prefix='task'),
    }
    defaults = {kind: json.dumps({field.name: field.value() for field in form}) for kind, form in forms.items()}
    active_modal = ''
    if request.method == 'POST':
        action = request.POST.get('action')
        if action == 'save_details':
            form = forms['details'] = TemplateDetailsForm(request.POST, prefix='details')
            if form.is_valid():
                for field, value in form.cleaned_data.items():
                    setattr(template, field, value)
                template.save(update_fields=['template_name', 'name', 'description'])
            else:
                active_modal = 'details'
        elif action in {'save_section', 'save_task', 'delete_section', 'delete_task'}:
            operation, kind = action.split('_')
            key = 'sections' if kind == 'section' else 'tasks'
            raw_id = request.POST.get(f'{kind}-item_id' if operation == 'save' else 'item_id', '')
            if raw_id:
                if not raw_id.isdecimal() or len(raw_id) > 18:
                    raise Http404
                if not any(item['id'] == int(raw_id) for item in structure.get(key, [])):
                    raise Http404
            elif operation == 'delete':
                raise Http404
            if operation == 'delete':
                delete_template_item(structure, kind, int(raw_id))
            else:
                form = forms[kind] = (TemplateSectionForm(request.POST, prefix=kind) if kind == 'section'
                                     else TemplateTaskForm(request.POST, structure=structure, prefix=kind))
                if form.is_valid():
                    update_template_item(structure, kind, form.cleaned_data)
                else:
                    active_modal = kind
            if not active_modal:
                template.save(update_fields=['structure'])
        else:
            raise Http404
        if not active_modal:
            if not modal_request:
                messages.success(request, 'Szablon zapisany.')
                return redirect(templates_url)
            saved = True
            forms = {
                'details': TemplateDetailsForm(instance=template, prefix='details'),
                'section': TemplateSectionForm(prefix='section'),
                'task': TemplateTaskForm(structure=structure, prefix='task'),
            }
            defaults = {kind: json.dumps({field.name: field.value() for field in form}) for kind, form in forms.items()}

    sections = []
    section_names = {item['id']: item['title'] for item in structure.get('sections', [])}
    task_names = {item['id']: item['title'] for item in structure.get('tasks', [])}
    for item in structure.get('sections', []):
        sections.append({**item, 'values': json.dumps({**item, 'item_id': item['id']}),
                         'task_values': json.dumps({'section': item['id']}),
                         'kind_label': dict(TaskSection.KIND_CHOICES).get(item['kind'], item['kind'])})
    tasks = []
    for item in structure.get('tasks', []):
        tasks.append({**item, 'values': json.dumps({**item, 'item_id': item['id']}),
                      'subtask_values': json.dumps({'section': item['section'], 'parent': item['id']}),
                      'section_name': section_names.get(item['section'], ''),
                      'parent_name': task_names.get(item['parent'], ''),
                      'priority_label': dict(Task.PRIORITY_CHOICES).get(item['priority'], item['priority'])})
    context = {
        'template': template, 'templates_url': templates_url, 'editor_url': editor_url,
        'sections': sections, 'template_tasks': tasks, 'details_form': forms['details'],
        'editor_modals': [
            {'kind': kind, 'form': form, 'active': active_modal == kind, 'title': title, 'defaults': defaults[kind]}
            for kind, title in [('section', 'Grupa szablonu'), ('task', 'Zadanie szablonu')]
            for form in [forms[kind]]
        ],
    }
    if modal_request:
        return JsonResponse({
            'html': render_to_string('tasks/project_template_edit.html', context, request=request),
            'saved': saved,
        })
    return render(request, 'tasks/project_templates.html', {**_directory_context(request), **context})
