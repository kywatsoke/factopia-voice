"""All HTTP the app does.

- Programs on this computer (the app's own server, llama-server, Ollama) are
  reached directly, never through a proxy: a proxy set in the system settings
  would otherwise receive them, because Python only bypasses plain host
  names, not 127.0.0.1.
- Everything on the internet (model downloads, the update check) is checked
  against the certificates the operating system trusts (macOS Keychain,
  Windows certificate store) through truststore. The Python inside the
  installed app has no certificate list of its own that it can rely on, and
  the system store also covers networks that use their own certificates
  (company or school networks). certifi's list is the fallback.
"""
import ssl
import urllib.request
from urllib.parse import urlparse

LOCAL_HOSTS = {"127.0.0.1", "localhost", "::1"}
_DIRECT = urllib.request.build_opener(urllib.request.ProxyHandler({}))
_INTERNET = None
TRUST = "not set up"            # which certificates internet requests use, for the self-test and logs


def https_context():
    """An SSL context that trusts what the operating system trusts."""
    global TRUST
    try:
        import truststore
        TRUST = "system certificates (truststore)"
        return truststore.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
    except Exception as e:                       # pragma: no cover - depends on the system
        first = f"{type(e).__name__}: {e}"
    try:
        import certifi
        TRUST = f"certifi (system store unavailable: {first})"
        return ssl.create_default_context(cafile=certifi.where())
    except Exception:                            # pragma: no cover
        TRUST = f"Python default (system store unavailable: {first})"
        return ssl.create_default_context()


def _internet():
    global _INTERNET
    if _INTERNET is None:
        _INTERNET = urllib.request.build_opener(urllib.request.HTTPSHandler(context=https_context()))
    return _INTERNET


def trust():
    """Set up internet requests if needed; say which certificates they use."""
    _internet()
    return TRUST


def open_url(request, timeout=None):
    """urlopen() for this app: direct for this computer, system-trusted HTTPS for the internet."""
    url = request.full_url if isinstance(request, urllib.request.Request) else request
    if urlparse(url).hostname in LOCAL_HOSTS:
        return _DIRECT.open(request, timeout=timeout)
    return _internet().open(request, timeout=timeout)
