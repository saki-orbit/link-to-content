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

1. 优先调用 `multi-platform-media-transcript` Skill 中的 `scripts/process_media.py`，传入单条 URL 清单。脚本会下载、转写、保存元数据，只返回状态和路径。
2. 链接无法由脚本下载时，再用本 Skill 已配置的方式下载到本地，并以 `file` 清单调用该脚本。若共享脚本未安装，沿用本 Skill 的本地转写流程。
3. 不要为了确认成功而读取逐字稿或字幕；只回传文件位置。用户明确要求摘要、校对或引用时，再读取相关内容。
4. 视频无音频时，保留帖子中可读的文字，并说明没有可转写的人声。
