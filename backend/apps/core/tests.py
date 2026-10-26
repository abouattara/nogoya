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


class PurgeDataTests(TestCase):
    """Une suppression en production ne se rattrape pas.

    Ces tests portent surtout sur ce que la commande **ne** supprime pas :
    c'est là que se jouent les dégâts irréversibles.
    """

    def setUp(self):
        from apps.catalog.models import Category, Product

        self.category = Category.objects.create(name="Tentes")
        self.demo = User.objects.create_user(
            phone="+22670010001", password="pw", role=User.Role.SUPPLIER
        )
        self.reel = User.objects.create_user(
            phone="+22677470000", password="pw", role=User.Role.SUPPLIER
        )
        self.demo_product = Product.objects.create(
            supplier=self.demo.supplier_profile, category=self.category,
            title="Annonce de démonstration", price=1000, city="Ouagadougou",
        )
        self.real_product = Product.objects.create(
            supplier=self.reel.supplier_profile, category=self.category,
            title="Vraie annonce", price=2000, city="Ouagadougou",
        )

    def _run(self, *args):
        from io import StringIO

        from django.core.management import call_command

        out = StringIO()
        call_command("purge_data", *args, stdout=out)
        return out.getvalue()

    def test_the_dry_run_is_the_default_and_writes_nothing(self):
        from apps.catalog.models import Product

        output = self._run()
        self.assertIn("Simulation", output)
        self.assertEqual(User.objects.count(), 2)
        self.assertEqual(Product.objects.count(), 2)

    def test_the_demo_scope_leaves_real_accounts_and_listings_alone(self):
        from apps.catalog.models import Product

        self._run("--yes")
        self.assertFalse(User.objects.filter(phone="+22670010001").exists())
        self.assertTrue(User.objects.filter(phone="+22677470000").exists())
        self.assertEqual([p.title for p in Product.objects.all()], ["Vraie annonce"])

    def test_a_staff_account_is_never_deleted_even_if_it_is_a_demo_number(self):
        """Se verrouiller dehors de son propre site ne s'annule pas."""
        from apps.catalog.models import Product

        self.demo.is_staff = True
        self.demo.save(update_fields=["is_staff"])

        output = self._run("--yes")
        self.assertIn("Comptes d'équipe conservés", output)
        self.assertTrue(User.objects.filter(phone="+22670010001").exists())
        # Et ses annonces restent : elles appartiennent à un compte vivant.
        self.assertEqual(Product.objects.count(), 2)

    def test_a_superuser_is_protected_the_same_way(self):
        self.demo.is_superuser = True
        self.demo.save(update_fields=["is_superuser"])

        self._run("--yes")
        self.assertTrue(User.objects.filter(phone="+22670010001").exists())

    def test_an_extra_account_can_be_named_explicitly(self):
        self._run("--phone", "+22677470000", "--yes")
        self.assertFalse(User.objects.filter(phone="+22677470000").exists())

    def test_the_all_scope_empties_the_catalogue_but_keeps_the_structure(self):
        from apps.catalog.models import Category, Product

        self._run("--scope", "all", "--yes")
        self.assertEqual(Product.objects.count(), 0)
        # Les comptes et la taxonomie sont la structure du site, pas son
        # contenu de test : les supprimer obligerait à tout recréer.
        self.assertEqual(User.objects.count(), 2)
        self.assertTrue(Category.objects.filter(name="Tentes").exists())

    def test_the_report_names_what_would_go(self):
        output = self._run("--scope", "all")
        self.assertIn("Annonces", output)
        self.assertIn("TOTAL", output)

    def test_it_reminds_that_image_files_survive_the_rows(self):
        output = self._run("--yes")
        self.assertIn("prune_media", output)
