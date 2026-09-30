---
name: x-bilibili-transcript
description: "把 X/Twitter 或 B 站单条视频链接快速变成逐字稿和字幕。适用于帖子视频转文字、X video transcript、Bilibili transcription、复制链接取稿。"
---

# X / B 站单条视频转写

用户提供一条 X（Twitter）或 B 站视频链接并要求转写时使用。目标是“链接进来，逐字稿出来”，不要求用户先下载文件或指定参数。

## 默认交付

- 保留原语言的逐字稿，保存为 `transcript.md`。
- 生成带时间戳的 SRT 字幕，保存为 `subtitles.srt`。
- `metadata.json` 使用统一字段：`title`、`platform`、`source_url`、`creator`、`published_at`、`duration_seconds`、`language`、`engines`。未知字段设为 `null`。
- 每条链接单独建立结果目录，默认保存在当前项目的“转写结果”目录。

## 执行方式

开始处理前检查本 Skill 需要的本机工具；缺少时运行本目录下的 scripts/setup.sh，完成后继续，不要求用户手动配置模型。

1. 用本机 yt-dlp 解析并下载用户给出的单条公开视频；避免把播放列表扩成一批任务。
2. 视频无音频时，保留帖子正文或可读文字，并说明没有可转写的人声。
3. 有音频时，优先用 MLX Whisper large-v3-turbo 本地转写；不支持 MLX 的环境使用 faster-whisper。本地转写工具缺失时，自动准备本地工具后继续。
4. 转写要保留口语表达与原意，添加合理标点和时间戳，不把逐字稿改成摘要。
5. 完成后直接给出逐字稿文件和字幕文件的位置，并用一句话确认结果。不要让用户理解下载器或模型细节。
