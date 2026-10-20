"""Aller chercher une URL sans se faire retourner contre soi-même.

Une source est configurée par un administrateur, mais une URL
d'administrateur reste une URL : si quelqu'un obtient un accès à l'admin, ou
si une source renvoie une redirection choisie par elle, le serveur peut être
amené à interroger `http://169.254.169.254/` (les identifiants de la machine
chez la plupart des hébergeurs) ou un service interne. C'est une SSRF, et
elle se prévient ici, pas dans l'adaptateur.

Trois règles :

1. http(s) uniquement — pas de `file://`, `gopher://`, `ftp://`.
2. L'hôte est résolu, et **chaque** adresse obtenue doit être publique.
3. Les redirections sont suivies à la main, chacune revalidée. Laisser
   `urllib` les suivre reviendrait à ne contrôler que la première.

La réponse est bornée en taille : un flux qui renvoie dix gigaoctets ne doit
pas remplir le disque du compte mutualisé.
"""
import ipaddress
import socket
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import Request, urlopen

MAX_REDIRECTS = 3
MAX_BYTES = 8 * 1024 * 1024
TIMEOUT_SECONDS = 20
USER_AGENT = "NogoyaBot/1.0 (+https://binogoya.com; import d'annonces autorise)"


class UnsafeUrl(Exception):
    """L'URL vise une adresse que le serveur ne doit pas interroger."""


class FetchFailed(Exception):
    """La source n'a pas répondu, ou a répondu une erreur."""


def _addresses(host):
    try:
        infos = socket.getaddrinfo(host, None)
    except socket.gaierror as exc:
        raise UnsafeUrl(f"Hôte introuvable : {host}") from exc
    return {info[4][0] for info in infos}


def assert_public_url(url):
    """Lève `UnsafeUrl` si l'URL ne vise pas un hôte public en http(s)."""
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https"):
        raise UnsafeUrl(f"Schéma refusé : {parsed.scheme or '(aucun)'}")
    if not parsed.hostname:
        raise UnsafeUrl("URL sans hôte.")

    for address in _addresses(parsed.hostname):
        ip = ipaddress.ip_address(address)
        # `is_global` couvre d'un coup la boucle locale, les réseaux privés,
        # le lien-local (dont 169.254.169.254), les adresses réservées et
        # les multicast — en IPv4 comme en IPv6.
        if not ip.is_global:
            raise UnsafeUrl(f"{parsed.hostname} résout vers une adresse non publique ({address}).")
    return parsed


def fetch(url, *, headers=None, timeout=TIMEOUT_SECONDS, max_bytes=MAX_BYTES):
    """Télécharge une URL publique et renvoie ses octets.

    Les redirections sont suivies une par une, chacune revalidée.
    """
    final_headers = {"User-Agent": USER_AGENT, "Accept": "*/*", **(headers or {})}

    for _ in range(MAX_REDIRECTS + 1):
        assert_public_url(url)
        request = Request(url, headers=final_headers, method="GET")
        try:
            # `urlopen` suivrait les redirections tout seul ; on les coupe
            # pour revalider chaque saut.
            with _NoRedirect.opener().open(request, timeout=timeout) as response:
                if response.status in (301, 302, 303, 307, 308):
                    location = response.headers.get("Location")
                    if not location:
                        raise FetchFailed("Redirection sans destination.")
                    url = _absolute(url, location)
                    continue
                return response.read(max_bytes + 1)[:max_bytes]
        except HTTPError as exc:
            if exc.code in (301, 302, 303, 307, 308):
                location = exc.headers.get("Location")
                if not location:
                    raise FetchFailed("Redirection sans destination.") from exc
                url = _absolute(url, location)
                continue
            raise FetchFailed(f"HTTP {exc.code} sur {url}") from exc
        except URLError as exc:
            raise FetchFailed(f"Injoignable : {exc.reason}") from exc

    raise FetchFailed("Trop de redirections.")


def _absolute(base, location):
    from urllib.parse import urljoin

    return urljoin(base, location)


class _NoRedirect:
    """Un ouvreur urllib qui rend la redirection au lieu de la suivre."""

    _opener = None

    @classmethod
    def opener(cls):
        if cls._opener is None:
            from urllib.request import HTTPRedirectHandler, build_opener

            class Passthrough(HTTPRedirectHandler):
                def redirect_request(self, *args, **kwargs):
                    return None

            cls._opener = build_opener(Passthrough)
        return cls._opener
