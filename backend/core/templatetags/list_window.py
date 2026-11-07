from django import template

from core.list_window import window_url


register = template.Library()


@register.simple_tag(takes_context=True)
def load_more_url(context, page):
    return window_url(context['request'], page) if page is not None else ''
