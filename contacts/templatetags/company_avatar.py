from django import template

from accounts.avatar import avatar_color_class, avatar_color_style_from_seed


register = template.Library()


def company_avatar_seed(company):
    if company is not None and getattr(company, 'pk', None) is not None:
        try:
            return int(company.pk)
        except (TypeError, ValueError):
            pass

    color_basis = 'company'
    if company is not None:
        color_basis = str(getattr(company, 'name', '') or getattr(company, 'website', '') or 'company')

    return sum((index + 1) * ord(char) for index, char in enumerate(color_basis))


@register.simple_tag
def company_avatar(company):
    seed = company_avatar_seed(company)
    photo_url = ''

    if company is not None and getattr(company, 'company_photo', None):
        try:
            photo_url = company.company_photo.url
        except ValueError:
            photo_url = ''

    return {
        'color_class': avatar_color_class(seed),
        'photo_url': photo_url,
        **avatar_color_style_from_seed(seed),
    }
