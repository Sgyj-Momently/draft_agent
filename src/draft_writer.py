from __future__ import annotations

import json
import os
from typing import Any
from urllib import request

DEFAULT_DRAFT_MODEL = "qwen2.5:32b"
DEFAULT_OLLAMA_BASE_URL = "http://localhost:11434"
DEFAULT_OLLAMA_TIMEOUT_SECONDS = 180


def create_draft(payload: dict[str, Any]) -> dict[str, Any]:
    outline = payload.get("outline") or {}
    title = _text(outline.get("title")) or "사진으로 남긴 하루"
    sections = outline.get("sections") or []
    photos_by_id = {
        photo.get("photo_id"): photo
        for photo in payload.get("photos", [])
        if photo.get("photo_id")
    }
    hero_by_group = {
        hero.get("group_id"): hero.get("hero_photo_id")
        for hero in payload.get("hero_photos", [])
        if hero.get("group_id") and hero.get("hero_photo_id")
    }

    if not sections:
        markdown, section_count = _template_draft(title, sections, photos_by_id, hero_by_group)
        return {
            "draft_status": "ok",
            "title": title,
            "markdown": markdown,
            "section_count": max(section_count, 1),
        }

    try:
        markdown = _llm_draft(payload, title, sections, photos_by_id, hero_by_group)
        section_count = len(sections) or 1
    except Exception:
        markdown, section_count = _template_draft(title, sections, photos_by_id, hero_by_group)

    return {
        "draft_status": "ok",
        "title": title,
        "markdown": markdown,
        "section_count": max(section_count, 1),
    }


def _llm_draft(
    payload: dict[str, Any],
    title: str,
    sections: list[Any],
    photos_by_id: dict[str, Any],
    hero_by_group: dict[str, Any],
) -> str:
    model_name = os.getenv("DRAFT_MODEL", DEFAULT_DRAFT_MODEL)
    base_url = os.getenv("OLLAMA_BASE_URL", DEFAULT_OLLAMA_BASE_URL)
    timeout_seconds = int(os.getenv("OLLAMA_TIMEOUT_SECONDS", str(DEFAULT_OLLAMA_TIMEOUT_SECONDS)))

    photo_summaries = [
        {"photo_id": p.get("photo_id"), "summary": p.get("summary"), "file_name": p.get("file_name")}
        for p in payload.get("photos", [])
        if p.get("photo_id")
    ]

    outline_for_prompt = {
        "title": title,
        "sections": sections,
    }

    # Build image placement hints so the LLM knows which filename to embed per section
    image_hints: list[dict[str, str]] = []
    for section in sections:
        supporting = section.get("supporting_photo_ids") if isinstance(section.get("supporting_photo_ids"), list) else []
        hero_photo_id = _first_existing_photo_id(supporting, photos_by_id) or hero_by_group.get(section.get("group_id"))
        if hero_photo_id and hero_photo_id in photos_by_id:
            photo = photos_by_id[hero_photo_id]
            image_hints.append({
                "section_heading": _text(section.get("heading")) or "",
                "photo_id": hero_photo_id,
                "file_name": photo.get("file_name", ""),
                "summary": _text(photo.get("summary")) or "",
            })

    voice_profile = payload.get("voice_profile") or {}
    style_prompt = _text(voice_profile.get("style_prompt")) or ""
    voice_section = (
        f"\n사용자 말투 프로필:\n{style_prompt}\n"
        if style_prompt
        else ""
    )
    content_type = _text(payload.get("content_type")) or "블로그"
    writing_instructions = _text(payload.get("writing_instructions")) or ""
    instruction_section = (
        f"\n사용자가 원하는 글 종류와 작성 방향:\n- 글 종류: {content_type}\n- 추가 요청: {writing_instructions}\n"
        if writing_instructions or content_type
        else ""
    )

    prompt = f"""당신은 한국어 블로그 작가이다. 아래 개요(outline)와 사진 요약을 바탕으로 자연스러운 한국어 블로그 글을 마크다운 형식으로 작성하라.
{voice_section}
{instruction_section}
개요:
{json.dumps(outline_for_prompt, ensure_ascii=False, indent=2)}

사진 요약:
{json.dumps(photo_summaries, ensure_ascii=False, indent=2)}

이미지 배치 힌트 (섹션별 삽입할 사진 파일명):
{json.dumps(image_hints, ensure_ascii=False, indent=2)}

작성 규칙:
- 제목은 `# {title}` 형식으로 시작한다.
- 각 섹션은 `## 섹션제목` 형식의 heading을 유지한다.
- 사진은 `![사진 설명](파일명)` 형식으로 섹션 heading 바로 아래에 삽입한다. 이미지 배치 힌트를 반드시 참고하라.
- 불릿 리스트(-) 형식은 절대 사용하지 말고, 자연스러운 산문(prose) 문단으로 작성한다.
- 각 섹션마다 2~4문장의 산문 단락을 작성한다.
- 사실을 지어내거나 과장하지 말고, 개요와 사진 요약에 있는 내용만 바탕으로 작성한다.
- 사용자가 요청한 글 종류와 작성 방향이 있으면 전체 구성과 표현에 반영한다.
- 글의 마지막에는 `## 마무리` 섹션을 추가하여 전체 흐름을 자연스럽게 마무리한다.
- 사용자 말투 프로필이 있으면 그 문체 지시를 최우선으로 따른다.
- 마크다운 외에 다른 설명이나 메타 텍스트는 출력하지 말 것.
"""

    body = {
        "model": model_name,
        "prompt": prompt,
        "stream": False,
    }
    http_request = request.Request(
        url=f"{base_url.rstrip('/')}/api/generate",
        data=json.dumps(body, ensure_ascii=False).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with request.urlopen(http_request, timeout=timeout_seconds) as response:
        response_payload = json.loads(response.read().decode("utf-8"))
    return response_payload["response"].strip() + "\n"


def _template_draft(
    title: str,
    sections: list[Any],
    photos_by_id: dict[str, Any],
    hero_by_group: dict[str, Any],
) -> tuple[str, int]:
    lines = [f"# {title}", ""]
    section_count = 0
    for index, section in enumerate(sections, start=1):
        heading = _text(section.get("heading")) or f"장면 {index}"
        bullets = section.get("bullets") if isinstance(section.get("bullets"), list) else []
        supporting = section.get("supporting_photo_ids") if isinstance(section.get("supporting_photo_ids"), list) else []
        hero_photo_id = _first_existing_photo_id(supporting, photos_by_id) or hero_by_group.get(section.get("group_id"))
        lines.extend([f"## {heading}", ""])
        if hero_photo_id in photos_by_id:
            photo = photos_by_id[hero_photo_id]
            alt = _text(photo.get("summary")) or heading
            lines.extend([f"![{alt}]({photo.get('file_name')})", ""])
        for bullet in bullets:
            text = _text(bullet)
            if text:
                lines.append(f"- {text}")
        if not bullets:
            lines.append("이 장면은 여행의 흐름을 자연스럽게 이어준다.")
        lines.append("")
        section_count += 1

    if section_count == 0:
        lines.extend(["## 기록", "", "사진 속 장면들을 바탕으로 여행의 흐름을 정리했다.", ""])

    lines.extend(["## 마무리", "", "작은 장면들이 모여 하루의 분위기를 완성했다."])
    markdown = "\n".join(lines).strip() + "\n"
    return markdown, section_count


def _first_existing_photo_id(photo_ids: list[Any], photos_by_id: dict[str, dict[str, Any]]) -> str | None:
    for raw in photo_ids:
        photo_id = _text(raw)
        if photo_id in photos_by_id:
            return photo_id
    return None


def _text(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None
