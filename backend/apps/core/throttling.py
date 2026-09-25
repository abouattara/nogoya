"""Rate limiting that survives server-side rendering.

DRF's `AnonRateThrottle` keys on the client IP. That is wrong here: pages
are rendered by Next.js, so every anonymous request reaches Django from the
frontend server's single address — one visitor hitting the limit would
throttle the whole site. We key on the anonymous visitor id instead (see
`apps.core.middleware`), which identifies a browser rather than a hop.

A visitor id is client-supplied, so rotating it defeats this, exactly as
rotating IPs defeats an IP limit. It shapes ordinary abuse; real protection
against a determined attacker belongs at the edge (Cloudflare), see
DEPLOYMENT.md.
"""
from rest_framework.throttling import ScopedRateThrottle, SimpleRateThrottle


class VisitorRateThrottle(SimpleRateThrottle):
    """Per-browser limit for anonymous traffic."""

    scope = "visitor"

    def get_cache_key(self, request, view):
        if request.user and request.user.is_authenticated:
            return None  # signed-in traffic is handled by UserRateThrottle
        ident = getattr(request, "visitor_id", "") or self.get_ident(request)
        return self.cache_format % {"scope": self.scope, "ident": ident}


class VisitorScopedRateThrottle(ScopedRateThrottle):
    """`throttle_scope` limits, counted per browser instead of per IP.

    Same reason as above, and it matters most for the `auth` scope: login
    goes through the Next.js BFF route, so *every* attempt reaches Django
    from the frontend server. Keyed on the IP, 20 attempts a minute would be
    the budget of the entire site — annoying for users and useless against
    an attacker, who would simply lock everyone else out.

    The BFF forwards `X-Visitor-Id` on those calls so the bucket follows the
    browser that is actually trying to sign in.
    """

    def get_cache_key(self, request, view):
        if request.user and request.user.is_authenticated:
            ident = request.user.pk
        else:
            ident = getattr(request, "visitor_id", "") or self.get_ident(request)
        return self.cache_format % {"scope": self.scope, "ident": ident}
