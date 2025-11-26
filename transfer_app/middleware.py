from django.utils import timezone
from django.conf import settings

class TimezoneActivationMiddleware:
    """Activate configured TIME_ZONE for each request.
    This ensures template localtime filter displays expected local time (Asia/Ho_Chi_Minh).
    """
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        timezone.activate(settings.TIME_ZONE)
        response = self.get_response(request)
        return response
