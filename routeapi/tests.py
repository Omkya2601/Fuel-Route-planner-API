from django.test import TestCase, Client

class RouteAPITest(TestCase):
    def test_post_requires_json(self):
        c = Client()
        resp = c.post("/api/route/", data="notjson", content_type="application/json")
        self.assertEqual(resp.status_code, 400)
