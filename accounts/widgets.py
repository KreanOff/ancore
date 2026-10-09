from django import forms

from .avatar import account_avatar


class UserSelect(forms.Select):
    """Show existing account avatars through the shared select's previews."""

    template_name = 'accounts/widgets/user_select.html'

    def create_option(self, name, value, label, selected, index, subindex=None, attrs=None):
        option = super().create_option(name, value, label, selected, index, subindex, attrs)
        user = getattr(value, 'instance', None)
        if user is not None:
            field_id = (attrs or {}).get('id', name)
            preview_id = f'{field_id}_user_preview_{user.pk}'
            option['attrs']['data-ancore-option-preview'] = preview_id
            option['preview_id'] = preview_id
            option['avatar'] = account_avatar(user)
            option['person_title'] = f'{label} · {user.email}' if user.email else label
        return option


class UserChoiceField(forms.ModelChoiceField):
    widget = UserSelect

    def label_from_instance(self, user):
        return user.get_full_name() or user.email or user.username
