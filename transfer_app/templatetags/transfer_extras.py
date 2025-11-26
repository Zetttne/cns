from django import template
from django.utils import timezone

register = template.Library()

@register.filter
def relative_time(dt):
    if not dt:
        return ''
    now = timezone.now()
    diff = now - dt
    seconds = int(diff.total_seconds())
    minutes = seconds // 60
    hours = minutes // 60
    days = diff.days
    if seconds < 60:
        return f"{seconds}s trước"
    if minutes < 60:
        return f"{minutes} phút trước"
    if hours < 24:
        return f"{hours} giờ trước"
    if days < 30:
        return f"{days} ngày trước"
    months = days // 30
    return f"{months} tháng trước"

@register.filter
def is_old(dt):
    """Return True if age >= 30 days"""
    if not dt:
        return False
    return (timezone.now() - dt).days >= 30