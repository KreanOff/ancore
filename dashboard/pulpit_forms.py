from django import forms

from spaces.services import visible_spaces
from tasks.models import Task
from workplaces.services import workplace_people
from .models import Dashboard, DashboardGadget, DashboardGroup
from .pulpits import AVAILABLE_GADGET_KINDS, personal_groups, visible_dashboards


def style_fields(form):
    for field in form.fields.values():
        field.widget.attrs['class'] = 'form-select' if isinstance(field.widget, forms.Select) else 'form-input'


class DashboardForm(forms.ModelForm):
    class Meta:
        model = Dashboard
        fields = ['name', 'description', 'visibility', 'shared_with', 'layout']
        widgets = {'description': forms.Textarea(attrs={'rows': 3})}
        labels = {'shared_with': 'Osoby z dostępem'}

    def __init__(self, *args, request, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['shared_with'].queryset = workplace_people(request.workplace, request.user).exclude(pk=request.user.pk)
        self.fields['shared_with'].label_from_instance = lambda user: user.get_full_name() or user.email
        self.fields['shared_with'].help_text = 'Wybierz osoby dla widoczności „Wybrane osoby”. Dostęp do danych nadal zależy od ich uprawnień.'
        self.fields['visibility'].help_text = 'Tylko twórca może zmieniać pulpit i jego gadżety.'
        style_fields(self)

    def clean(self):
        data = super().clean()
        if data.get('visibility') == Dashboard.Visibility.SELECTED and not data.get('shared_with'):
            self.add_error('shared_with', 'Wybierz co najmniej jedną osobę.')
        elif data.get('visibility') != Dashboard.Visibility.SELECTED:
            data['shared_with'] = self.fields['shared_with'].queryset.none()
        return data


class GadgetForm(forms.ModelForm):
    status = forms.ChoiceField(label='Status', required=False, choices=[('', 'Wszystkie statusy'), *Task.STATUS_CHOICES])
    assignee = forms.ChoiceField(label='Przypisanie', choices=[('all', 'Wszyscy'), ('me', 'Przypisane do oglądającego'), ('unassigned', 'Bez wykonawcy')])
    group_by = forms.ChoiceField(label='Grupowanie statystyk', choices=[('status', 'Status'), ('priority', 'Priorytet'), ('assignee', 'Wykonawca')])
    limit = forms.TypedChoiceField(label='Liczba wyników', coerce=int, choices=[(5, '5'), (10, '10'), (20, '20')])

    class Meta:
        model = DashboardGadget
        fields = ['kind', 'title', 'space', 'status', 'assignee', 'group_by', 'limit']

    def __init__(self, *args, request, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['kind'].choices = [('', '---------'), *[(kind, kind.label) for kind in AVAILABLE_GADGET_KINDS]]
        self.fields['space'].queryset = visible_spaces(request)
        self.fields['space'].empty_label = 'Wszystkie dostępne przestrzenie'
        self.fields['space'].label_from_instance = lambda space: space.project.name
        self.fields['title'].help_text = 'Puste pole używa nazwy gadżetu.'
        self.fields['kind'].help_text = 'Przypisane do mnie pokazuje otwarte zadania osoby oglądającej pulpit.'
        if self.instance.pk and self.instance.kind not in AVAILABLE_GADGET_KINDS:
            self.fields['kind'].help_text = 'Ten rodzaj nie jest już dostępny. Wybierz „Przypisane do mnie” albo „Statystyki zadań”.'
        self.fields['group_by'].help_text = 'Dotyczy gadżetu „Statystyki zadań”.'
        self.fields['limit'].help_text = 'Dotyczy gadżetu „Przypisane do mnie”.'
        if self.instance.space_id and not self.fields['space'].queryset.filter(pk=self.instance.space_id).exists():
            self.fields['space'].help_text = 'Ta przestrzeń jest już niedostępna. Wybierz dostępne źródło danych.'
        style_fields(self)


class DashboardGroupForm(forms.ModelForm):
    class Meta:
        model = DashboardGroup
        fields = ['name', 'dashboards']

    def __init__(self, *args, request, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['dashboards'].queryset = visible_dashboards(request)
        self.request = request
        self.fields['dashboards'].help_text = 'Twoja osobista grupa. Dodanie pulpitu nie zmienia jego widoczności.'
        style_fields(self)

    def clean_name(self):
        name = self.cleaned_data['name'].strip()
        if personal_groups(self.request).filter(name__iexact=name).exclude(pk=self.instance.pk).exists():
            raise forms.ValidationError('Masz już grupę o tej nazwie.')
        return name


class DashboardGroupsForm(forms.Form):
    groups = forms.ModelMultipleChoiceField(label='Twoje grupy', queryset=DashboardGroup.objects.none(), required=False)

    def __init__(self, *args, request, dashboard, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['groups'].queryset = personal_groups(request)
        self.fields['groups'].initial = list(personal_groups(request).filter(dashboards=dashboard).values_list('pk', flat=True))
        self.fields['groups'].help_text = 'Pulpit może należeć do kilku Twoich grup. Pusty wybór usuwa go z grup.'
        style_fields(self)
