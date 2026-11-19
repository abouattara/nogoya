"""Chaque recherche est retenue une fois, avec sa provenance."""
import csv
import io
import tempfile
from datetime import timedelta
from pathlib import Path

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.urls import reverse
from rest_framework.test import APITestCase

from apps.catalog.models import Category, Product
from apps.suppliers.models import SupplierProfile

from .models import SearchEvent

User = get_user_model()


class SearchRecordingTests(APITestCase):
    def setUp(self):
        self.category = Category.objects.create(name="Tentes")
        supplier = User.objects.create_user(
            phone="+22670092001", password="pw", role=User.Role.SUPPLIER
        )
        self.member = User.objects.create_user(
            phone="+22670092002", password="pw", role=User.Role.VISITOR
        )
        profile = SupplierProfile.objects.get(user=supplier)
        for i in range(30):
            Product.objects.create(
                supplier=profile, category=self.category, title=f"Tente {i}",
                price=1000, city="Bobo", status=Product.Status.APPROVED,
            )
        self.url = reverse("api:product-list")
        self.vid = "b" * 32

    def search(self, **params):
        headers = params.pop("headers", {})
        return self.client.get(self.url, params, HTTP_X_VISITOR_ID=self.vid, **headers)

    def test_a_visitor_search_is_recorded_with_its_result_count(self):
        self.search(search="tente")
        event = SearchEvent.objects.get()
        self.assertEqual(event.normalized_query, "tente")
        self.assertEqual(event.visitor_id, self.vid)
        self.assertIsNone(event.user)
        self.assertEqual(event.results_count, 30)

    def test_a_member_search_is_attributed_to_the_member(self):
        self.client.force_authenticate(self.member)
        self.search(search="tente")
        event = SearchEvent.objects.get()
        self.assertEqual(event.user, self.member)
        self.assertEqual(event.visitor_id, "")

    def test_a_search_with_no_result_is_kept(self):
        # Ce sont les plus utiles : ce qu'on cherche et que le site n'a pas.
        self.search(search="projecteur")
        self.assertEqual(SearchEvent.objects.get().results_count, 0)

    def test_scrolling_to_the_next_pages_is_not_a_new_search(self):
        self.search(search="tente")
        self.search(search="tente", page=2)
        self.search(search="tente", page=3)
        self.assertEqual(SearchEvent.objects.count(), 1)

    def test_typing_letter_by_letter_makes_one_search(self):
        for typed in ["t", "te", "ten", "tent", "tente"]:
            self.search(search=typed)
        self.assertEqual(
            list(SearchEvent.objects.values_list("normalized_query", flat=True)), ["tente"]
        )

    def test_erasing_a_letter_stays_the_same_search(self):
        self.search(search="tentes")
        self.search(search="tente")
        self.assertEqual(SearchEvent.objects.count(), 1)
        self.assertEqual(SearchEvent.objects.get().normalized_query, "tente")

    def test_a_different_search_is_a_new_search(self):
        self.search(search="tente")
        self.search(search="moto")
        self.assertEqual(SearchEvent.objects.count(), 2)

    def test_the_same_words_later_count_again(self):
        self.search(search="tente")
        SearchEvent.objects.update(created_at=SearchEvent.objects.get().created_at - timedelta(minutes=5))
        self.search(search="tente")
        self.assertEqual(SearchEvent.objects.count(), 2)

    def test_changing_a_filter_is_a_new_search(self):
        self.search(search="tente")
        self.search(search="tente", city="Bobo")
        self.assertEqual(SearchEvent.objects.count(), 2)

    def test_two_visitors_typing_the_same_thing_are_two_searches(self):
        self.search(search="tente")
        self.client.get(self.url, {"search": "tente"}, HTTP_X_VISITOR_ID="c" * 32)
        self.assertEqual(SearchEvent.objects.count(), 2)

    def test_the_channel_is_recorded_when_announced(self):
        self.search(search="tente", headers={"HTTP_X_CLIENT": "android"})
        self.assertEqual(SearchEvent.objects.get().channel, "android")

    def test_an_unknown_channel_is_not_stored(self):
        # L'en-tete vient du client : on ne garde que les valeurs prevues.
        self.search(search="tente", headers={"HTTP_X_CLIENT": "<script>"})
        self.assertEqual(SearchEvent.objects.get().channel, "")

    def test_a_supplier_listing_their_own_products_is_not_a_search(self):
        self.search(search="tente", mine="true")
        self.assertFalse(SearchEvent.objects.exists())

    def test_the_bare_catalogue_is_not_a_search(self):
        self.search()
        self.assertFalse(SearchEvent.objects.exists())


class SearchReportTests(APITestCase):
    def setUp(self):
        for query, results in [("tente", 4), ("tente", 2), ("projecteur", 0), ("projecteur", 0), ("moto", 1)]:
            SearchEvent.objects.create(
                query=query, normalized_query=query, results_count=results,
                visitor_id=query[0] * 32, channel="web",
            )

    def test_report_lists_frequent_and_unserved_searches(self):
        out = io.StringIO()
        call_command("search_report", "--days", "7", stdout=out)
        text = out.getvalue()
        self.assertIn("5 recherches", text)
        frequent, unserved = text.split("sans résultat")
        self.assertIn("tente", frequent)
        self.assertIn("projecteur", unserved)
        self.assertNotIn("tente", unserved)

    def test_csv_export_has_one_line_per_search_and_no_phone(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "recherches.csv"
            call_command("search_report", "--csv", str(path), stdout=io.StringIO())
            rows = list(csv.reader(path.open(encoding="utf-8-sig"), delimiter=";"))
        self.assertEqual(rows[0][:3], ["date", "recherche", "criteres"])
        self.assertEqual(len(rows), 6)
        self.assertNotIn("+226", path.name + "".join(";".join(r) for r in rows))
