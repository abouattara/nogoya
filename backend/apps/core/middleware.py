import re
import uuid

VISITOR_COOKIE = "nogoya_vid"
VISITOR_HEADER = "HTTP_X_VISITOR_ID"
VISITOR_ID_RE = re.compile(r"^[0-9a-f]{32}$")
VISITOR_COOKIE_MAX_AGE = 60 * 60 * 24 * 365  # 1 year


class VisitorCookieMiddleware:
    """Assign every client a random, non-identifying visitor id.

    Used to personalise anonymous browsing (recent searches, recently viewed
    products, view-count deduplication) without collecting personal data.
    The cookie holds a random UUID only — never an IP, user agent or
    fingerprint derivative.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # The frontend owns this id: pages are server-rendered, so a cookie we
        # set here would only ever reach the Next.js server, never the browser.
        # It arrives as a header, which we validate rather than trust (it is
        # attacker-controlled, so it is only ever used as an opaque bucket key
        # and never as an identity).
        header_id = request.META.get(VISITOR_HEADER, "")
        visitor_id = header_id if VISITOR_ID_RE.match(header_id or "") else request.COOKIES.get(VISITOR_COOKIE)
        is_new = not visitor_id
        if is_new:
            visitor_id = uuid.uuid4().hex
        request.visitor_id = visitor_id

        response = self.get_response(request)

        # Only direct API clients (no frontend) still need the cookie.
        if is_new:
            response.set_cookie(
                VISITOR_COOKIE,
                visitor_id,
                max_age=VISITOR_COOKIE_MAX_AGE,
                httponly=True,
                samesite="Lax",
            )
        return response
