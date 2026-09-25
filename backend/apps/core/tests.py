from django.contrib.auth import get_user_model
from django.test import RequestFactory, TestCase
from django.urls import reverse

from .throttling import VisitorRateThrottle, VisitorScopedRateThrottle

User = get_user_model()


class CoreSmokeTests(TestCase):
    def test_health_endpoint(self):
        resp = self.client.get(reverse("core:health"))
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json(), {"status": "ok"})

    def test_ready_endpoint_reports_dependencies(self):
        resp = self.client.get(reverse("core:ready"))
        self.assertEqual(resp.status_code, 200)
        body = resp.json()
        self.assertEqual(body["status"], "ok")
        # names of the checks only — never versions, paths or credentials
        self.assertEqual(set(body["checks"]), {"database", "cache"})


class VisitorRateThrottleTests(TestCase):
    """Anonymous traffic is counted per browser, not per IP.

    With server-side rendering every anonymous request reaches Django from
    the frontend server, so an IP-keyed throttle would rate-limit the whole
    site at once.
    """

    def setUp(self):
        self.factory = RequestFactory()
        self.throttle = VisitorRateThrottle()

    def _request(self, visitor_id="", user=None):
        request = self.factory.get("/api/v1/products/")
        request.visitor_id = visitor_id
        request.user = user
        return request

    def test_two_browsers_behind_one_ip_get_separate_budgets(self):
        first = self.throttle.get_cache_key(self._request("a" * 32), view=None)
        second = self.throttle.get_cache_key(self._request("b" * 32), view=None)
        self.assertIsNotNone(first)
        self.assertNotEqual(first, second)

    def test_same_browser_shares_one_budget(self):
        key = self.throttle.get_cache_key(self._request("c" * 32), view=None)
        self.assertEqual(key, self.throttle.get_cache_key(self._request("c" * 32), view=None))

    def test_signed_in_traffic_is_left_to_the_user_throttle(self):
        user = User.objects.create_user(phone="+22670099001", password="pw")
        self.assertIsNone(self.throttle.get_cache_key(self._request("d" * 32, user), view=None))

    def test_falls_back_to_the_address_when_no_visitor_id(self):
        key = self.throttle.get_cache_key(self._request(""), view=None)
        self.assertIsNotNone(key)


class VisitorScopedRateThrottleTests(TestCase):
    """`auth` and `search` budgets follow the browser, not the hop.

    Login goes through the Next.js BFF, so every attempt reaches Django from
    the frontend server: an IP-keyed budget would be shared by everyone.
    """

    def setUp(self):
        self.factory = RequestFactory()
        self.throttle = VisitorScopedRateThrottle()
        self.throttle.scope = "auth"

    def _request(self, visitor_id="", user=None):
        request = self.factory.post("/api/v1/auth/login/")
        request.visitor_id = visitor_id
        request.user = user
        return request

    def test_two_browsers_sharing_the_bff_address_are_counted_apart(self):
        first = self.throttle.get_cache_key(self._request("a" * 32), view=None)
        second = self.throttle.get_cache_key(self._request("b" * 32), view=None)
        self.assertNotEqual(first, second)
        self.assertIn("auth", first)

    def test_signed_in_requests_are_keyed_on_the_account(self):
        user = User.objects.create_user(phone="+22670099002", password="pw")
        key = self.throttle.get_cache_key(self._request("e" * 32, user), view=None)
        self.assertIn(str(user.pk), key)
