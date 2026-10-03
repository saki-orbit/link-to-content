---
name: multi-platform-media-transcript
description: "整理视频、播客、文章和图文链接，生成本地逐字稿、字幕、正文、OCR 和来源信息。"
---

# Link2Content

用户直接发链接即可。默认只保存原文和来源信息；只有用户提出时，才摘要、翻译或分析。

## 视频和播客

固定转写由本地脚本完成。批量时一次提交全部链接，不要逐条下载、运行转写、读取全文或把全文贴回对话。

1. 写一个短 JSON 清单，只放本次链接和必要元数据：

   ```json
   {"items": [{"url": "https://example.com/video", "language": "zh"}]}
   ```

   也可用 `file` 指向本地音视频。每项只能有 `url` 或 `file`。可选字段：`title`、`platform`、`source_url`、`creator`、`published_at`、`duration_seconds`、`language`。

2. 调用本 Skill 的 `scripts/process_media.py`：

   ```bash
   python "$SKILL_DIR/scripts/process_media.py" --manifest "/path/to/links.json"
   ```

   Windows 使用 Skill 环境中的 Python 启动同一脚本。默认结果在当前目录的 `转写结果/`；可用 `--output-root` 指定位置。

3. 脚本逐条下载和转写。完整内容保存在本地，只返回总数、结果目录和失败项；批次摘要也保存在本地。不要打开逐字稿或字幕来确认成功；脚本会检查文件。下载失败时，使用平台已配置的下载方式取得本地文件，再将 `file` 写入清单重试。

默认产物：`transcript.md`、`subtitles.srt`、`transcript.json`、`metadata.json`。原始媒体会在临时目录中自动清理；需要保留时加 `--keep-media`。

**不要自动读取旧逐字稿、旧任务记录或 Memory。** 用户明确要求摘要、问答、校对或记忆时，只读取相关内容或片段。

## 文章和图文

- 文章正文用已安装的 Crawl4AI 读取；图片文字用本地 RapidOCR。
- 正文和 OCR 结果保存为本地文件。默认只把文件路径和处理状态交回对话。
- 小红书主页批量归档交给 `xiaohongshu-creator-archive` Skill。

元数据统一使用 `title`、`platform`、`source_url`、`creator`、`published_at`、`duration_seconds`、`language`、`engines`；未知值写为 `null`。

## 安装

首次使用或本地环境缺失时，先运行安装脚本：

- macOS / Linux：`bash scripts/setup.sh`
- Windows：`powershell -ExecutionPolicy Bypass -File scripts/setup.ps1`

本 Skill 的脚本可缩短它加入对话的内容，但不能更改飞书 Harness 对旧聊天记录的保留策略。
