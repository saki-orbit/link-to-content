---
name: multi-platform-media-transcript
description: "Link2Content 通用入口。用户直接发来小红书（Xiaohongshu / RedNote）、抖音（Douyin）、快手（Kuaishou）、B站（Bilibili）、微博（Weibo）、豆瓣（Douban）、知乎（Zhihu）、微信公众号、X（Twitter）、YouTube、播客等一条或多条内容链接时，自动识别平台和内容类型，整理成本地逐字稿、SRT 字幕、OCR 和来源信息。用户不需要选择平台或指定 Skill。"
---

# Link2Content：链接进来，本地素材出来

这是 Link2Content 的通用入口。用户可能只发来一个 URL，或说“帮我整理一下这个链接”。直接根据 URL 判断平台、内容类型和处理方式，不要要求用户先选择平台或 Skill。

## 默认交付

每条链接单独建立结果目录，保存到当前项目的“转写结果”目录：

- 视频或播客：`transcript.md`、`subtitles.srt`、`metadata.json`。
- 图文笔记或文章：正文与 `metadata.json`；有图片时另生成 `ocr.md`。
- 小红书博主主页：每篇作品单独归档，另生成 `index.csv` 和失败清单。

`metadata.json` 使用统一字段：`title`、`platform`、`source_url`、`creator`、`published_at`、`duration_seconds`、`language`、`engines`。无法获取的值写为 `null`。

多条链接按用户给出的顺序处理，每条分别保存。某条失败时继续处理其他链接，最后汇报成功和失败的数量与文件位置。

## 自动选择处理流程

用户不需要知道下面这些流程，也不需要指定其中任何一个。根据链接在内部选择合适的处理方式：

1. **视频链接**（例如抖音、快手、B 站、微博、X、YouTube 等）：使用本机 `yt-dlp` 解析和下载媒体；用 `ffmpeg` 提取音频；Apple 芯片 Mac 使用本地 MLX Whisper，其他环境使用本地 faster-whisper。保留原语言、说话顺序和合理标点，生成逐字稿与 SRT。
2. **播客单集链接**：从单集页面解析音频并下载，再按视频流程在本机转写。默认交付逐字稿、SRT 和来源信息。只有用户提出时，才进一步整理摘要、精华、思维导图或飞书文档。
3. **小红书单篇笔记**：直接读取用户给出的作品内容，不要求用户先找另一种 Skill。视频按音视频流程转写；图文提取正文和图片 OCR，生成 `ocr.md`。
4. **小红书博主主页**：使用本机已配置的小红书链接桥/API 获取主页中可访问的作品链接，再逐篇按上面的流程整理。单条内容链接不需要登录；只有主页批量归档需要登录态。批量流程使用了针对性优化，建议用小号。
5. **微信公众号文章**：支持单篇文章链接和合集。合集按其中可访问的文章逐篇整理；没有合集且文章数量不多时，让用户逐条发送文章链接。读取正文，有图片时进行 OCR，并保留来源信息。
6. **其他文章或图文页面**（例如豆瓣、知乎）：使用本机 Crawl4AI 读取正文；图片 OCR 使用本机 RapidOCR + ONNX Runtime，保留来源信息。

## 执行步骤

开始处理前检查本 Skill 需要的本机工具；缺少时自动运行本 Skill 的安装脚本并继续，不要求用户挑选平台、下载媒体或手动设置模型：

- macOS / Linux：`bash scripts/setup.sh`
- Windows：`powershell -ExecutionPolicy Bypass -File scripts/setup.ps1`

安装脚本会准备独立的 Link2Content Python 环境、FFmpeg、网页解析浏览器、Whisper 转写依赖和 RapidOCR 中文模型，并预下载 Whisper 权重。Apple 芯片 Mac 使用 MLX Whisper；其他设备使用 faster-whisper。模型保存在用户本机缓存中，不在 Git 仓库里；模型下载只需做一次。

本地运行环境位置：

- macOS / Linux：`${XDG_CACHE_HOME:-$HOME/.cache}/link2content/venv`
- Windows：`%LOCALAPPDATA%\Link2Content\venv`

### 视频和播客的固定转写路径

这段流程已经写进随 Skill 安装的脚本。**必须调用它，不要自己临时写 `transcribe.py`，不要改用 Agent 的语音识别或临时调用 Python API。**

1. 用该平台已配置的解析方式下载用户给出的媒体，记录下载到的本地文件路径。
2. 找到当前 Skill 的安装目录，将其绝对路径记为 `SKILL_DIR`。为这条内容建立结果目录 `OUTPUT_DIR`。
3. 调用随 Skill 安装的固定转写脚本：

   macOS / Linux：

   ```bash
   python "$SKILL_DIR/scripts/transcribe_audio.py" \
     --input "/absolute/path/to/downloaded-media" \
     --output-dir "/absolute/path/to/output-dir" \
     --language zh
   ```

   中文内容传 `--language zh`；已知其他语言时传对应语言代码；语言不确定时省略 `--language` 让模型自动识别。Windows 使用同一个参数格式，通过 `py` 或本地 Python 启动脚本。

4. 等脚本返回成功后，检查 `OUTPUT_DIR/transcript.md` 和 `OUTPUT_DIR/subtitles.srt` 已生成。将可获取的标题、平台、原始链接、作者、发布时间和时长写入 `metadata.json`；取不到的字段写 `null`。

Apple 芯片 Mac 上，脚本按 DSH 已验证的命令行路径运行：FFmpeg 转为 16 kHz 单声道 WAV，再调用 Skill 本机环境中的 `mlx_whisper`，使用 `mlx-community/whisper-large-v3-turbo` 和 `--output-format all`。权重在安装时下载到本机缓存，转写时由本机进程加载。其他设备由同一脚本调用已安装的 faster-whisper CPU int8 后端。两种情况都不需要 Agent 自己拼接转写程序。

图片 OCR 使用本地 RapidOCR，读取返回的 `txts` 并按识别顺序写入 `ocr.md`。文件保留原始识别内容；用户要求时再让 Agent 校对或加工。

1. 根据 URL 判断它是单条媒体、文章、图文笔记、播客，还是小红书博主主页；不确定时先尝试读取链接，不要让用户重新分类。
2. 只处理用户提供的链接或明确要求归档的主页内容。网页正文和媒体分别使用适合的解析方式。
3. 视频和播客严格按上面的固定脚本转写。脚本正在运行时不要重复启动第二份转写进程；较长音频等待期间会定时输出运行状态。
4. 默认只整理原始内容和标准元数据。保留原意，不凭空补写；听不清的片段标为“听不清”。用户提出时再做摘要、内容拆解或二次创作。
5. 将每条内容保存到单独目录，完成后直接给出结果位置和处理情况。

如果某个链接暂时无法读取，说明具体是哪一条及遇到的情况，再继续处理其他链接；不要编造成功结果。
