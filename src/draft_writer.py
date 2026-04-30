from __future__ import annotations

from typing import Any


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
    return {
        "draft_status": "ok",
        "title": title,
        "markdown": markdown,
        "section_count": max(section_count, 1),
    }


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
