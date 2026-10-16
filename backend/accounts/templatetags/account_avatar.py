from django import template

from accounts.avatar import account_avatar


register = template.Library()


@register.simple_tag
def user_avatar(user):
    return account_avatar(user)
