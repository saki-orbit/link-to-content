#!/usr/bin/env python3
"""Download and transcribe a batch without returning transcript text to the agent."""

from __future__ import annotations

import argparse
import json
import os
import platform
import re
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from urllib.parse import urlparse


SCRIPT_DIR = Path(__file__).resolve().parent
TRANSCRIBE_SCRIPT = SCRIPT_DIR / "transcribe_audio.py"


def skill_python() -> Path:
    if os.name == "nt":
        app_data = os.environ.get("LOCALAPPDATA")
        if not app_data:
            raise RuntimeError("找不到 LOCALAPPDATA；请先运行 Skill 安装脚本。")
        return Path(app_data) / "Link2Content" / "venv" / "Scripts" / "python.exe"
    cache_home = Path(os.environ.get("XDG_CACHE_HOME", Path.home() / ".cache"))
    return cache_home / "link2content" / "venv" / "bin" / "python"


def use_skill_python() -> None:
    expected = skill_python()
    if not expected.is_file():
        raise RuntimeError("Link2Content 环境不存在；请先运行 scripts/setup.sh 或 setup.ps1。")
    if os.environ.get("LINK2CONTENT_VENV_READY") == "1":
        return
    if Path(sys.prefix).resolve() == expected.parent.parent.resolve():
        return
    env = os.environ.copy()
    env["LINK2CONTENT_VENV_READY"] = "1"
    os.execve(str(expected), [str(expected), str(Path(__file__).resolve()), *sys.argv[1:]], env)


def load_manifest(path: Path) -> list[dict[str, object]]:
    data = json.loads(path.expanduser().read_text(encoding="utf-8"))
    items = data.get("items") if isinstance(data, dict) else data
    if not isinstance(items, list) or not items:
        raise ValueError("清单必须是非空数组，或包含非空 items 数组的对象。")
    for index, item in enumerate(items, start=1):
        if not isinstance(item, dict) or bool(item.get("url")) == bool(item.get("file")):
            raise ValueError(f"第 {index} 条必须且只能填写 url 或 file。")
    return items


def download_url(url: str, folder: Path) -> tuple[Path, dict[str, object]]:
    from yt_dlp import YoutubeDL

    options = {
        "format": "bestaudio/best",
        "outtmpl": str(folder / "%(id)s.%(ext)s"),
        "noplaylist": True,
        "quiet": True,
        "no_warnings": True,
    }
    with YoutubeDL(options) as ydl:
        info = ydl.extract_info(url, download=True)
        if not isinstance(info, dict):
            raise RuntimeError("下载器没有返回媒体信息。")
        candidates = [info.get("_filename")]
        candidates.extend(
            entry.get("filepath")
            for entry in (info.get("requested_downloads") or [])
            if isinstance(entry, dict)
        )
        candidates.append(ydl.prepare_filename(info))

    for candidate in candidates:
        if candidate and Path(str(candidate)).is_file():
            return Path(str(candidate)), info
    files = [file for file in folder.rglob("*") if file.is_file() and not file.name.endswith(".part")]
    if len(files) == 1:
        return files[0], info
    raise RuntimeError("下载完成后没有找到唯一的媒体文件。")


def safe_folder_name(title: str) -> str:
    name = re.sub(r"[^\w\- ]+", "", title, flags=re.UNICODE).strip().replace(" ", "-")
    return (name[:64].strip("-_") or "media")


def published_date(value: object) -> str | None:
    if not value:
        return None
    text = str(value)
    if re.fullmatch(r"\d{8}", text):
        return f"{text[:4]}-{text[4:6]}-{text[6:8]}"
    return text


def transcription_engine() -> str:
    if platform.system() == "Darwin" and platform.machine().lower() in {"arm64", "aarch64"}:
        return "mlx-whisper"
    return "faster-whisper"


def run_transcription(source: Path, output_dir: Path, language: str | None, log_path: Path) -> None:
    command = [
        sys.executable,
        str(TRANSCRIBE_SCRIPT),
        "--input",
        str(source),
        "--output-dir",
        str(output_dir),
    ]
    if language:
        command.extend(["--language", language])

    started = time.monotonic()
    with log_path.open("w", encoding="utf-8") as log:
        process = subprocess.Popen(command, stdout=log, stderr=subprocess.STDOUT, text=True)
        last_notice = 0
        while process.poll() is None:
            time.sleep(5)
            elapsed = int(time.monotonic() - started)
            if elapsed >= 60 and elapsed // 60 > last_notice:
                last_notice = elapsed // 60
                print(f"[Link2Content] 本批转写仍在运行（{elapsed // 60} 分钟）。", file=sys.stderr, flush=True)
    if process.returncode != 0:
        details = log_path.read_text(encoding="utf-8", errors="replace")[-1200:].strip()
        raise RuntimeError(details or f"转写脚本退出码：{process.returncode}")


def metadata_for(item: dict[str, object], info: dict[str, object], source: Path) -> dict[str, object]:
    source_url = item.get("source_url") or item.get("url") or info.get("webpage_url")
    host = urlparse(str(source_url)).hostname if source_url else None
    platform_name = item.get("platform") or info.get("extractor_key") or info.get("extractor") or host
    return {
        "title": item.get("title") or info.get("title") or source.stem,
        "platform": platform_name,
        "source_url": source_url,
        "creator": item.get("creator") or info.get("uploader") or info.get("channel") or info.get("artist"),
        "published_at": item.get("published_at") or published_date(info.get("upload_date")),
        "duration_seconds": item.get("duration_seconds") or item.get("duration") or info.get("duration"),
        "language": item.get("language") or info.get("language"),
        "engines": ["yt-dlp", "ffmpeg", transcription_engine()] if item.get("url") else ["ffmpeg", transcription_engine()],
    }


def process_item(index: int, item: dict[str, object], output_root: Path, keep_media: bool) -> dict[str, object]:
    fallback_title = str(item.get("title") or f"item-{index:03}")
    output_dir = output_root / f"{index:03}-{safe_folder_name(fallback_title)}"
    try:
        with tempfile.TemporaryDirectory(prefix="link2content-") as temp_name:
            temp_dir = Path(temp_name)
            info: dict[str, object] = {}
            if item.get("url"):
                source, info = download_url(str(item["url"]), temp_dir)
            else:
                source = Path(str(item["file"])).expanduser().resolve()
                if not source.is_file():
                    raise FileNotFoundError(f"找不到媒体文件：{source}")

            title = str(item.get("title") or info.get("title") or source.stem)
            output_dir = output_root / f"{index:03}-{safe_folder_name(title)}"
            output_dir.mkdir(parents=True, exist_ok=True)
            run_transcription(source, output_dir, str(item["language"]) if item.get("language") else None, output_dir / "process.log")

            required = ["transcript.md", "subtitles.srt", "transcript.json"]
            missing = [name for name in required if not (output_dir / name).is_file()]
            if missing:
                raise RuntimeError(f"转写结束，但缺少结果文件：{', '.join(missing)}")
            if keep_media and item.get("url"):
                shutil.copy2(source, output_dir / source.name)

            metadata = metadata_for(item, info, source)
            (output_dir / "metadata.json").write_text(
                json.dumps(metadata, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
            )
            return {
                "index": index,
                "status": "success",
                "title": metadata["title"],
                "output_dir": str(output_dir),
                "files": [*required, "metadata.json"],
            }
    except Exception as error:
        output_dir.mkdir(parents=True, exist_ok=True)
        (output_dir / "error.txt").write_text(f"{type(error).__name__}: {error}\n", encoding="utf-8")
        return {
            "index": index,
            "status": "failed",
            "title": fallback_title,
            "output_dir": str(output_dir),
            "error": f"{type(error).__name__}: {error}"[:400],
        }


def main() -> int:
    parser = argparse.ArgumentParser(description="批量下载并转写媒体；完整文本保存在本地，只输出状态和文件路径。")
    parser.add_argument("--manifest", required=True, type=Path, help="含 items 数组的 JSON 清单")
    parser.add_argument("--output-root", type=Path, default=Path("转写结果"), help="结果目录，默认当前目录下的转写结果")
    parser.add_argument("--keep-media", action="store_true", help="在结果目录保留下载的原始媒体")
    args = parser.parse_args()

    use_skill_python()
    items = load_manifest(args.manifest)
    output_root = args.output_root.expanduser().resolve()
    output_root.mkdir(parents=True, exist_ok=True)
    results = [process_item(index, item, output_root, args.keep_media) for index, item in enumerate(items, start=1)]
    summary = {
        "total": len(results),
        "succeeded": sum(item["status"] == "success" for item in results),
        "failed": sum(item["status"] == "failed" for item in results),
        "output_root": str(output_root),
        "items": results,
    }
    summary_path = output_root / f"batch-summary-{time.strftime('%Y%m%d-%H%M%S')}-{os.getpid()}.json"
    summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    response: dict[str, object] = {
        "total": summary["total"],
        "succeeded": summary["succeeded"],
        "failed": summary["failed"],
        "output_root": str(output_root),
        "summary_file": str(summary_path),
    }
    failures = [item for item in results if item["status"] == "failed"]
    if failures:
        response["failed_items"] = [
            {"index": item["index"], "title": item["title"], "error": str(item["error"])[:160]}
            for item in failures[:10]
        ]
        if len(failures) > 10:
            response["more_failures_in_summary"] = len(failures) - 10
    elif len(results) <= 5:
        response["results"] = [
            {"title": item["title"], "output_dir": item["output_dir"]}
            for item in results
        ]

    print(json.dumps(response, ensure_ascii=False, indent=2))
    return 0 if summary["failed"] == 0 else 1


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, RuntimeError, ValueError, json.JSONDecodeError) as error:
        print(json.dumps({"status": "failed", "error": str(error)}, ensure_ascii=False), file=sys.stderr)
        raise SystemExit(2)
