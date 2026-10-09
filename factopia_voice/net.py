"""HTTP to programs on this computer (the app's own server, llama-server,
Ollama). These calls never go through a proxy: a proxy set in the system
settings would otherwise receive them, because Python only bypasses plain
host names, not 127.0.0.1."""
import urllib.request
from urllib.parse import urlparse

_DIRECT = urllib.request.build_opener(urllib.request.ProxyHandler({}))
LOCAL_HOSTS = {"127.0.0.1", "localhost", "::1"}


def open_url(request, timeout=None):
    """urlopen() that goes direct for this computer and normally for anything else."""
    url = request.full_url if isinstance(request, urllib.request.Request) else request
    if urlparse(url).hostname in LOCAL_HOSTS:
        return _DIRECT.open(request, timeout=timeout)
    return urllib.request.urlopen(request, timeout=timeout)
