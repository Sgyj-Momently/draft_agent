import unittest
from unittest.mock import patch

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

    def test_llm_failure_falls_back_to_template_with_sections(self) -> None:
        payload = {
            "outline": {
                "title": "카페 산책",
                "sections": [
                    {
                        "heading": "입구",
                        "bullets": ["가게 앞에서 시작했다"],
                        "supporting_photo_ids": ["file:a.jpg"],
                    },
                    {
                        "heading": "테이블",
                        "bullets": [],
                        "group_id": "g-1",
                    },
                ],
            },
            "photos": [{"photo_id": "file:a.jpg", "file_name": "a.jpg", "summary": "카페 입구"}],
            "hero_photos": [{"group_id": "g-1", "hero_photo_id": "file:missing.jpg"}],
            "content_type": "음식후기",
            "writing_instructions": "담백하게 써줘",
        }

        with patch("src.draft_writer.request.urlopen", side_effect=RuntimeError("ollama down")):
            result = create_draft(payload)

        self.assertEqual(result["draft_status"], "ok")
        self.assertIn("## 입구", result["markdown"])
        self.assertIn("![카페 입구](a.jpg)", result["markdown"])
        self.assertIn("- 가게 앞에서 시작했다", result["markdown"])
        self.assertIn("이 장면은 여행의 흐름을 자연스럽게 이어준다.", result["markdown"])


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
