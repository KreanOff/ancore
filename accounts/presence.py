from datetime import timedelta

from django.conf import settings
from django.contrib.auth import get_user_model
from django.db.models import Q
from django.utils import timezone


DEFAULT_IDLE_SECONDS = 120
DEFAULT_WRITE_THROTTLE_SECONDS = 25


def idle_seconds():
    return getattr(settings, 'USER_PRESENCE_IDLE_SECONDS', DEFAULT_IDLE_SECONDS)


def heartbeat_seconds():
    return getattr(settings, 'USER_PRESENCE_HEARTBEAT_SECONDS', 30)


def write_throttle_seconds():
    return getattr(settings, 'USER_PRESENCE_WRITE_THROTTLE_SECONDS', DEFAULT_WRITE_THROTTLE_SECONDS)


def _auto_statuses(user_model):
    return {
        user_model.PresenceStatus.ACTIVE,
        user_model.PresenceStatus.INACTIVE,
    }


def _model_for_user(user):
    return user._meta.model


def _sync_user_instance(user, **fields):
    for field, value in fields.items():
        setattr(user, field, value)


def mark_user_seen(user, now=None, force=False):
    if not getattr(user, 'is_authenticated', False):
        return None

    now = now or timezone.now()
    user_model = _model_for_user(user)
    update_values = {}
    current_status = user.presence_status
    last_seen_at = getattr(user, 'last_seen_at', None)
    throttle = timedelta(seconds=write_throttle_seconds())

    if current_status in _auto_statuses(user_model):
        update_values['presence_status'] = user_model.PresenceStatus.ACTIVE

    if force or not last_seen_at or now - last_seen_at >= throttle:
        update_values['last_seen_at'] = now

    if not update_values:
        return current_status

    user_model.objects.filter(pk=user.pk).update(**update_values)
    _sync_user_instance(user, **update_values)
    return user.presence_status


def mark_user_inactive(user, force=False):
    if not getattr(user, 'is_authenticated', False):
        return None

    user_model = _model_for_user(user)
    if not force and user.presence_status not in _auto_statuses(user_model):
        return user.presence_status

    status = user_model.PresenceStatus.INACTIVE
    user_model.objects.filter(pk=user.pk).update(presence_status=status)
    _sync_user_instance(user, presence_status=status)
    return status


def sync_stale_presence_statuses(now=None):
    now = now or timezone.now()
    user_model = get_user_model()
    cutoff = now - timedelta(seconds=idle_seconds())

    return (
        user_model.objects
        .filter(presence_status=user_model.PresenceStatus.ACTIVE)
        .filter(Q(last_seen_at__isnull=True) | Q(last_seen_at__lt=cutoff))
        .update(presence_status=user_model.PresenceStatus.INACTIVE)
    )
