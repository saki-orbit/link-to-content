---
name: podcast-to-feishu
description: "把小宇宙等播客链接整理成逐字稿、结构化精华、思维导图和飞书文档。适用于 podcast transcript、播客总结、播客内容沉淀、Xiaoyuzhou to Feishu。"
---

# 播客精华沉淀到飞书

用户给出播客单集链接，希望得到文字稿、精华或飞书文档时使用。默认一次完成“听取内容—整理—形成可回看的文档”。

## 默认交付

本地标准素材与飞书文档包含：

1. `transcript.md`：清理口头填充词后的完整文字稿，保留事实、观点和语气。
2. `subtitles.srt`：带时间戳字幕。
3. `metadata.json` 使用统一字段：`title`、`platform`、`source_url`、`creator`、`published_at`、`duration_seconds`、`language`、`engines`。未知字段设为 `null`。
4. 飞书文档：结构化精华、重要观点的时间戳和 Mermaid 思维导图。

## 执行方式

开始处理前检查本 Skill 需要的本机工具；缺少时运行本目录下的 scripts/setup.sh，完成后继续，不要求用户手动配置模型。

1. 优先调用 `multi-platform-media-transcript` Skill 中的 `scripts/process_media.py` 转写本集。它只返回状态和路径；不要读取旧播客或旧任务记录。
2. 若链接无法下载，解析音频到本地，再以 `file` 清单调用共享脚本。共享脚本未安装时沿用本 Skill 的本地转写流程。
3. 用户要求精华或飞书文档时，只读取本集逐字稿来整理；校对稿和摘要不能冒充逐字稿。摘要中的事实和引用必须有原文依据。
4. 用户要求写入飞书时，使用当前可用的飞书连接。没有写入工具时，生成 Markdown 文件和思维导图，并说明文件位置。
5. 完成后回传文档链接和本地文件位置。只要求转写时，不生成摘要或飞书文档。
