from django.test import TestCase
from django.urls import reverse


class HomeViewTests(TestCase):
    def test_home_renders(self):
        response = self.client.get(reverse("app:home"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "TeamPulse")
        self.assertContains(response, "Iniciar sesión")

    def test_home_link_login(self):
        response = self.client.get(reverse("app:home"))
        self.assertContains(response, reverse("cuentas:login"))
