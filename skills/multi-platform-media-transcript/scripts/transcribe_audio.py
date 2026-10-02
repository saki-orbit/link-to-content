#!/usr/bin/env python3
"""Run Link2Content's fixed local transcription pipeline.

Apple silicon follows the same ffmpeg -> mlx_whisper CLI path used by DSH.
Other platforms use the Skill's installed faster-whisper CPU backend.
"""

from __future__ import annotations

import argparse
import json
import os
import platform
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path


MLX_MODEL = "mlx-community/whisper-large-v3-turbo"
FASTER_MODEL = "large-v3-turbo"


def cache_root() -> Path:
    if os.name == "nt":
        local_app_data = os.environ.get("LOCALAPPDATA")
        if not local_app_data:
            raise RuntimeError("找不到 LOCALAPPDATA；请先运行 Skill 的安装脚本。")
        return Path(local_app_data) / "Link2Content"
    cache_home = os.environ.get("XDG_CACHE_HOME") or Path.home() / ".cache"
    return Path(cache_home) / "link2content"


def venv_paths() -> tuple[Path, Path]:
    root = cache_root() / "venv"
    if os.name == "nt":
        return root / "Scripts" / "python.exe", root / "Scripts" / "mlx_whisper.exe"
    return root / "bin" / "python", root / "bin" / "mlx_whisper"


def ensure_skill_python() -> None:
    """Re-launch through the Skill venv so agents cannot pick another Python."""
    expected_python, _ = venv_paths()
    if not expected_python.is_file():
        raise RuntimeError("Link2Content 本地环境不存在；先运行 Skill 自带的 scripts/setup.sh 或 setup.ps1。")

    try:
        running_prefix = Path(sys.prefix).resolve()
        expected_prefix = expected_python.parent.parent.resolve()
    except OSError:
        return

    if running_prefix == expected_prefix or os.environ.get("LINK2CONTENT_VENV_READY") == "1":
        return

    env = os.environ.copy()
    env["LINK2CONTENT_VENV_READY"] = "1"
    os.execve(str(expected_python), [str(expected_python), str(Path(__file__).resolve()), *sys.argv[1:]], env)


def run_with_heartbeat(command: list[str]) -> None:
    print("[Link2Content] 正在调用本地 Whisper CLI；模型运行在本机。", flush=True)
    print("[Link2Content] 转写耗时取决于音频长度和电脑负载，请保持此任务运行。", flush=True)
    process = subprocess.Popen(command)
    started = time.monotonic()
    next_heartbeat = started + 60

    while process.poll() is None:
        time.sleep(2)
        now = time.monotonic()
        if now >= next_heartbeat:
            elapsed = int(now - started)
            print(f"[Link2Content] 本地转写仍在进行，已运行 {elapsed // 60} 分 {elapsed % 60} 秒。", flush=True)
            next_heartbeat = now + 60

    if process.returncode != 0:
        raise subprocess.CalledProcessError(process.returncode, command)


def transcribe_mlx(audio_wav: Path, output_dir: Path, language: str | None) -> None:
    _, mlx_cli = venv_paths()
    if not mlx_cli.is_file():
        raise RuntimeError("本机 MLX Whisper 命令不存在；请重新运行 Skill 的安装脚本。")

    command = [
        str(mlx_cli),
        str(audio_wav),
        "--model",
        MLX_MODEL,
        "--output-dir",
        str(output_dir),
        "--output-name",
        "transcript",
        "--output-format",
        "all",
        "--verbose",
        "False",
    ]
    if language:
        command.extend(["--language", language])

    print("[Link2Content] 转写后端：MLX Whisper CLI（DSH 同一路径）。", flush=True)
    run_with_heartbeat(command)


def transcribe_faster(audio_wav: Path, output_dir: Path, language: str | None) -> None:
    from faster_whisper import WhisperModel

    print("[Link2Content] 转写后端：faster-whisper（CPU int8）。", flush=True)
    model = WhisperModel(FASTER_MODEL, device="cpu", compute_type="int8")
    segments, info = model.transcribe(str(audio_wav), language=language, vad_filter=True)

    text_parts: list[str] = []
    srt_parts: list[str] = []
    json_segments: list[dict[str, object]] = []
    for index, segment in enumerate(segments, start=1):
        text = segment.text.strip()
        if not text:
            continue
        text_parts.append(text)
        srt_parts.extend(
            [
                str(index),
                f"{format_srt_time(segment.start)} --> {format_srt_time(segment.end)}",
                text,
                "",
            ]
        )
        json_segments.append({"start": segment.start, "end": segment.end, "text": text})

    (output_dir / "transcript.txt").write_text("\n".join(text_parts).strip() + "\n", encoding="utf-8")
    (output_dir / "transcript.srt").write_text("\n".join(srt_parts), encoding="utf-8")
    (output_dir / "transcript.json").write_text(
        json.dumps({"language": info.language, "duration": info.duration, "segments": json_segments}, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def format_srt_time(seconds: float) -> str:
    milliseconds = round(seconds * 1000)
    hours, milliseconds = divmod(milliseconds, 3_600_000)
    minutes, milliseconds = divmod(milliseconds, 60_000)
    secs, milliseconds = divmod(milliseconds, 1000)
    return f"{hours:02}:{minutes:02}:{secs:02},{milliseconds:03}"


def write_markdown_outputs(output_dir: Path) -> None:
    text_path = output_dir / "transcript.txt"
    srt_path = output_dir / "transcript.srt"
    if not text_path.is_file() or not srt_path.is_file():
        raise RuntimeError("Whisper 没有生成逐字稿和 SRT；请检查上方转写错误信息。")

    transcript = text_path.read_text(encoding="utf-8").strip()
    if not transcript:
        raise RuntimeError("Whisper 返回了空逐字稿；没有写入结果文件。")
    (output_dir / "transcript.md").write_text(transcript + "\n", encoding="utf-8")
    shutil.copy2(srt_path, output_dir / "subtitles.srt")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="用 Link2Content 固定的本地 Whisper 流程生成逐字稿和字幕。")
    parser.add_argument("--input", required=True, type=Path, help="已下载的音频或视频文件")
    parser.add_argument("--output-dir", required=True, type=Path, help="本条内容的结果目录")
    parser.add_argument("--language", help="语音语言代码；中文传 zh，不指定时自动识别")
    parser.add_argument("--keep-audio", action="store_true", help="在结果目录保留转换后的 16 kHz 单声道 WAV")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    ensure_skill_python()
    source = args.input.expanduser().resolve()
    output_dir = args.output_dir.expanduser().resolve()

    if not source.is_file():
        raise RuntimeError(f"找不到输入媒体文件：{source}")
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        raise RuntimeError("找不到 ffmpeg；请运行 Skill 的安装脚本，或重新打开 Agent 后再试。")

    output_dir.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=".link2content-", dir=output_dir) as temp_name:
        work_dir = Path(temp_name)
        stage_dir = work_dir / "whisper-output"
        stage_dir.mkdir()
        audio_wav = work_dir / "audio.wav"

        print("[Link2Content] 正在用 FFmpeg 将媒体转成 16 kHz 单声道 WAV。", flush=True)
        subprocess.run(
            [ffmpeg, "-y", "-v", "error", "-i", str(source), "-vn", "-ac", "1", "-ar", "16000", str(audio_wav)],
            check=True,
        )

        is_apple_silicon = platform.system() == "Darwin" and platform.machine().lower() in {"arm64", "aarch64"}
        if is_apple_silicon:
            transcribe_mlx(audio_wav, stage_dir, args.language)
        else:
            transcribe_faster(audio_wav, stage_dir, args.language)

        write_markdown_outputs(stage_dir)
        deliverables = ["transcript.md", "subtitles.srt", "transcript.json"]
        for name in deliverables:
            artifact = stage_dir / name
            if artifact.is_file():
                shutil.copy2(artifact, output_dir / name)
        if args.keep_audio:
            shutil.copy2(audio_wav, output_dir / "audio.wav")

    print(f"[Link2Content] 完成：{output_dir / 'transcript.md'}", flush=True)
    print(f"[Link2Content] 完成：{output_dir / 'subtitles.srt'}", flush=True)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, RuntimeError, subprocess.CalledProcessError) as error:
        print(f"[Link2Content] 转写失败：{error}", file=sys.stderr, flush=True)
        raise SystemExit(1)
