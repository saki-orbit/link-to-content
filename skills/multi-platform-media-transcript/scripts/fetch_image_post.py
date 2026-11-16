#!/usr/bin/env python3
"""Fetch a Xiaohongshu image post: unified metadata plus per-image OCR text.

Renders the note locally, reads the metadata out of the embedded initial
state, downloads the note images and OCRs them with the local RapidOCR
engine. Results go to ``metadata.json`` and ``ocr.md``; the conversation only
receives a short status line.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import re
import sys
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Any

from process_media import safe_folder_name, use_skill_python

DEFAULT_USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
)
INITIAL_STATE = re.compile(r"window\.__INITIAL_STATE__\s*=\s*(\{.*?\})\s*</script>", re.S)
IMAGE_SUFFIXES = {"image/webp": ".webp", "image/jpeg": ".jpg", "image/png": ".png"}


async def render_html(url: str, timeout: int) -> str:
    from crawl4ai import AsyncWebCrawler, BrowserConfig, CacheMode, CrawlerRunConfig

    browser = BrowserConfig(
        headless=True,
        user_agent=DEFAULT_USER_AGENT,
        viewport_width=1440,
        viewport_height=2000,
    )
    run = CrawlerRunConfig(
        cache_mode=CacheMode.BYPASS,
        page_timeout=timeout * 1000,
        wait_for="css:img, #noteContainer",
        delay_before_return_html=3.0,
    )
    async with AsyncWebCrawler(config=browser) as crawler:
        result = await crawler.arun(url=url, config=run)
        if not result.success:
            raise RuntimeError(f"渲染失败：{result.error_message}")
        return result.html or ""


def note_from_html(html: str) -> dict[str, Any]:
    match = INITIAL_STATE.search(html)
    if not match:
        raise RuntimeError("页面里找不到 __INITIAL_STATE__；可能被登录墙或风控拦住，请重试后重新发送链接。")
    # 页面里的 initial state 带裸 undefined，不是合法 JSON，先改写再解析。
    data = json.loads(match.group(1).replace("undefined", "null"))
    details = (data.get("note") or {}).get("noteDetailMap") or {}
    if not details:
        raise RuntimeError("页面里没有 noteDetailMap；请确认链接是单篇笔记详情页。")
    first = next(iter(details.values()))
    note = first.get("note") or first
    if not note.get("noteId"):
        raise RuntimeError("initial state 里没有笔记主体，可能页面没有加载完成。")
    return note


def image_urls(note: dict[str, Any]) -> list[str]:
    """Collect full-size image URLs.

    ``urlDefault`` already points at the rendered full-size asset. Do not append
    ``!nd_dft_*`` style suffixes: those requests come back as 403.
    """
    urls: list[str] = []
    for image in note.get("imageList") or []:
        candidates = [image.get("urlDefault")]
        candidates.extend(info.get("url") for info in image.get("infoList") or [])
        url = next((value for value in candidates if value), "")
        if url and url not in urls:
            urls.append(url)
    return urls


def download_images(urls: list[str], folder: Path) -> list[Path]:
    import requests

    folder.mkdir(parents=True, exist_ok=True)
    session = requests.Session()
    session.headers.update(
        {"User-Agent": DEFAULT_USER_AGENT, "Referer": "https://www.xiaohongshu.com/"}
    )
    paths: list[Path] = []
    for index, url in enumerate(urls, start=1):
        failure = ""
        for _ in range(3):
            try:
                response = session.get(url, timeout=60)
            except requests.RequestException as error:
                failure = str(error)
                continue
            if response.ok and response.content:
                content_type = response.headers.get("Content-Type", "").split(";")[0].strip()
                suffix = IMAGE_SUFFIXES.get(content_type, ".jpg")
                path = folder / f"{index:02d}{suffix}"
                path.write_bytes(response.content)
                paths.append(path)
                break
            failure = f"HTTP {response.status_code}"
        else:
            raise RuntimeError(f"第 {index} 张图片下载失败：{failure}")
    return paths


def group_lines(
    boxes: list[Any], texts: list[str], scores: list[float], min_score: float
) -> list[str]:
    """Rebuild reading order from OCR boxes.

    RapidOCR returns boxes without any layout information, so lines are rebuilt
    by clustering boxes that share a baseline (within 0.55 of the taller box
    height) and then sorting each line left to right.
    """
    items = []
    for box, text, score in zip(boxes, texts, scores):
        text = str(text).strip()
        if not text or float(score) < min_score:
            continue
        ys = [point[1] for point in box]
        xs = [point[0] for point in box]
        items.append(
            {
                "y": sum(ys) / len(ys),
                "x": min(xs),
                "h": max(ys) - min(ys),
                "text": text,
            }
        )
    if not items:
        return []
    lines: list[list[dict[str, Any]]] = []
    for item in sorted(items, key=lambda entry: entry["y"]):
        for line in lines:
            reference = line[0]
            if abs(reference["y"] - item["y"]) <= max(reference["h"], item["h"]) * 0.55:
                line.append(item)
                break
        else:
            lines.append([item])
    lines.sort(key=lambda line: min(entry["y"] for entry in line))
    return [
        " ".join(entry["text"] for entry in sorted(line, key=lambda entry: entry["x"]))
        for line in lines
    ]


def as_sequence(value: Any) -> list[Any]:
    """RapidOCR hands back numpy arrays, so ``value or []`` would be ambiguous."""
    return [] if value is None else list(value)


def ocr_images(paths: list[Path], min_score: float) -> dict[str, list[str]]:
    from rapidocr import RapidOCR

    engine = RapidOCR()
    results: dict[str, list[str]] = {}
    for path in paths:
        raw = engine(str(path))
        results[path.stem] = group_lines(
            as_sequence(getattr(raw, "boxes", None)),
            as_sequence(getattr(raw, "txts", None)),
            as_sequence(getattr(raw, "scores", None)),
            min_score,
        )
    return results


def build_metadata(
    note: dict[str, Any], source_url: str, image_count: int
) -> dict[str, Any]:
    interact = note.get("interactInfo") or {}
    published_at = None
    published = note.get("time")
    if isinstance(published, (int, float)) and published > 0:
        seconds = published / 1000 if published > 10**11 else published
        published_at = datetime.fromtimestamp(seconds).strftime("%Y-%m-%d")
    return {
        "title": note.get("title") or note.get("noteId"),
        "platform": "xiaohongshu",
        "source_url": source_url,
        "creator": (note.get("user") or {}).get("nickname"),
        "published_at": published_at,
        "duration_seconds": None,
        "language": "zh",
        "engines": ["crawl4ai", "rapidocr"],
        "extra": {
            "id": note.get("noteId"),
            "type": note.get("type"),
            "images": image_count,
            "tags": [tag.get("name") for tag in note.get("tagList") or [] if tag.get("name")],
            "liked": interact.get("likedCount"),
            "collected": interact.get("collectedCount"),
            "comment": interact.get("commentCount"),
            "share": interact.get("shareCount"),
        },
    }


def write_markdown(path: Path, metadata: dict[str, Any], texts: dict[str, list[str]]) -> None:
    lines = [
        f"# {metadata['title']}",
        "",
        f"- 来源：{metadata['source_url']}",
        f"- 平台：{metadata['platform']}",
        f"- 作者：{metadata['creator'] or '未知'}",
        f"- 发布：{metadata['published_at'] or '未知'}",
        f"- 引擎：{', '.join(metadata['engines'])}",
    ]
    for stem in sorted(texts):
        lines.extend(["", f"## 图片 {stem}", ""])
        body = texts[stem]
        lines.extend(body if body else ["（未识别到文字）"])
    path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")


def main() -> int:
    use_skill_python()
    parser = argparse.ArgumentParser(description="提取小红书图文笔记的元数据和图片文字")
    parser.add_argument("--url", required=True, help="小红书笔记链接")
    parser.add_argument("--out", type=Path, default=None, help="结果目录，默认当前目录下的 图文结果/<标题>")
    parser.add_argument("--keep-images", action="store_true", help="在结果目录保留下载的原图")
    parser.add_argument("--timeout", type=int, default=60, help="页面渲染超时秒数，默认 60")
    parser.add_argument("--min-score", type=float, default=0.35, help="OCR 结果置信度下限，默认 0.35")
    args = parser.parse_args()

    note = note_from_html(asyncio.run(render_html(args.url, args.timeout)))
    if str(note.get("type") or "") != "normal":
        print(
            f"[Link2Content] 这条笔记的 type 是 {note.get('type')}；视频笔记请改用 scripts/process_media.py。",
            file=sys.stderr,
            flush=True,
        )
    urls = image_urls(note)
    if not urls:
        raise RuntimeError("这条笔记没有可下载的图片；如果是视频笔记，请改用 scripts/process_media.py。")

    out_dir = args.out.expanduser() if args.out else (
        Path("图文结果") / safe_folder_name(str(note.get("title") or note.get("noteId")))
    )
    out_dir.mkdir(parents=True, exist_ok=True)

    if args.keep_images:
        texts = ocr_images(download_images(urls, out_dir / "images"), args.min_score)
    else:
        with tempfile.TemporaryDirectory(prefix="link2content-") as temp_dir:
            texts = ocr_images(download_images(urls, Path(temp_dir)), args.min_score)

    metadata = build_metadata(note, args.url, len(urls))
    (out_dir / "metadata.json").write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    write_markdown(out_dir / "ocr.md", metadata, texts)

    print(
        json.dumps(
            {
                "status": "ok",
                "output": str(out_dir),
                "images": len(urls),
                "ocr_lines": sum(len(lines) for lines in texts.values()),
                "files": ["metadata.json", "ocr.md"],
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, RuntimeError, ValueError, json.JSONDecodeError) as error:
        print(json.dumps({"status": "failed", "error": str(error)}, ensure_ascii=False), file=sys.stderr)
        raise SystemExit(2)
