from django.shortcuts import redirect
from django.urls import reverse
from django.contrib import messages

class BusinessRequiredMiddleware:
    """
    - Bloqueia usuário sem empresa
    - Bloqueia empresa inativa
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):

        if request.user.is_authenticated:
            user = request.user

            if not user.business:
                messages.error(request, 'Usuário sem empresa vinculada.')
                return redirect(reverse('logout'))

            if not user.business.active:
                messages.error(request, 'Empresa inativa. Contate o suporte.')
                return redirect(reverse('logout'))

        return self.get_response(request)
