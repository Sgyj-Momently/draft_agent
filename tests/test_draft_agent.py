import unittest

from fastapi.testclient import TestClient

from src.api_server import app
from src.draft_writer import create_draft


class DraftWriterTest(unittest.TestCase):
    def test_create_draft_uses_outline_and_supporting_photo(self) -> None:
        result = create_draft(
            {
                "outline": {
                    "title": "카페 산책",
                    "sections": [
                        {
                            "heading": "입구",
                            "bullets": ["가게 앞에서 시작했다"],
                            "supporting_photo_ids": ["file:a.jpg"],
                        }
                    ],
                },
                "photos": [{"photo_id": "file:a.jpg", "file_name": "a.jpg", "summary": "카페 입구"}],
                "hero_photos": [],
            }
        )

        self.assertEqual(result["draft_status"], "ok")
        self.assertIn("# 카페 산책", result["markdown"])
        self.assertIn("![카페 입구](a.jpg)", result["markdown"])

    def test_empty_outline_still_returns_usable_draft(self) -> None:
        result = create_draft({"outline": {}, "photos": []})

        self.assertEqual(result["section_count"], 1)
        self.assertIn("## 기록", result["markdown"])


class DraftApiTest(unittest.TestCase):
    def test_health(self) -> None:
        response = TestClient(app).get("/health")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"status": "ok"})

    def test_create_draft_endpoint(self) -> None:
        response = TestClient(app).post(
            "/api/v1/drafts",
            json={
                "project_id": "sample",
                "outline": {"title": "제목", "sections": []},
                "photos": [],
            },
        )

        body = response.json()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(body["project_id"], "sample")
        self.assertEqual(body["draft_status"], "ok")


if __name__ == "__main__":
    unittest.main()
