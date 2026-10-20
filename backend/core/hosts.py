"""Validate hosts for a deployment accessed through an unspecified server IP."""
from ipaddress import ip_address
from urllib.parse import urlsplit

from django.conf import settings
from django.core.exceptions import DisallowedHost


class ServerAddressMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if settings.ALLOW_IP_HOSTS:
            host = urlsplit('http://' + request.get_host()).hostname
            if host != 'localhost':
                try:
                    ip_address(host)
                except ValueError as error:
                    raise DisallowedHost('Dostęp wymaga adresu IP serwera lub skonfigurowanej nazwy hosta.') from error
        return self.get_response(request)
