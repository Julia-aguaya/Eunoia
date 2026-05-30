from django.shortcuts import redirect
from django.urls import reverse


class MustChangePasswordMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.user.is_authenticated and request.user.must_change_password:
            allowed_paths = {
                reverse('login'),
                reverse('logout'),
                reverse('change-password-required'),
            }
            if request.path not in allowed_paths and not request.path.startswith('/admin/login'):
                return redirect(reverse('change-password-required'))

        return self.get_response(request)
