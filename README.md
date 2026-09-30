# 给一个链接，拿到本地内容素材

看到一条值得留下的视频或播客？把链接发给 Agent，快速得到可搜索、可复用的文字素材。

**不用自己找下载器、抽音轨、转格式、跑转写。链接进来，逐字稿和字幕出来。**

- **速度快**：本地模型处理音频。作者实测，2 分 48 秒中文口播约 25 秒完成转写。
- **少花 Token**：语音转写在本机完成，减少云端转写和 Token 消耗。
- **素材可复用**：逐字稿、带时间戳字幕和来源信息，方便搜索、复盘、剪辑和二次创作。

## 选择一个 Skill

### 小红书博主作品归档

给一个博主主页，把公开作品整理进本地素材库：视频生成逐字稿和字幕，图文提取文字，并生成可搜索索引。

主页批量抓取需要小红书登录态。批量流程针对请求和采集做了优化；为稳妥起见，建议使用小号。作者自用大号测试至今没有遇到封禁。单条作品链接不需要登录。

Skill：[xiaohongshu-creator-archive](https://github.com/saki-orbit/link-to-content/tree/main/skills/xiaohongshu-creator-archive)

### X / B 站单条视频转写

复制一条 X 或 B 站视频链接，得到逐字稿、带时间戳字幕和来源信息。单条链接处理不需要登录。

Skill：[x-bilibili-transcript](https://github.com/saki-orbit/link-to-content/tree/main/skills/x-bilibili-transcript)

### 多平台链接转文字

给一个或多个可访问的 YouTube、X、B 站或其他媒体链接，分别生成逐字稿、字幕和来源信息。单条链接处理不需要登录。

Skill：[multi-platform-media-transcript](https://github.com/saki-orbit/link-to-content/tree/main/skills/multi-platform-media-transcript)

### 播客精华进飞书

给小宇宙单集链接，生成全文、结构化精华、时间戳和思维导图，并整理进飞书文档。这是单独的播客工作流；其他 Skill 默认专注于标准化文字素材。

Skill：[podcast-to-feishu](https://github.com/saki-orbit/link-to-content/tree/main/skills/podcast-to-feishu)

## 标准产物

- 原语言逐字稿
- 带时间戳字幕
- 标题、平台、来源链接和时长等基本信息
- 小红书主页归档：作品目录、`index.csv` 和逐条处理结果

自动分析、钩子提取等内容加工可以在拿到文字后按需提示 Agent；它们不改变默认转写流程。

## 三步开始使用

### 1. 选一个 Skill

每个 Skill 目录都能单独安装。比如只想转写 X 或 B 站视频，就选 `x-bilibili-transcript`。

### 2. 把 Skill 网页地址发给 Agent

发布后，打开对应 Skill 的 GitHub 页面，复制浏览器地址。地址格式如下：

```text
https://github.com/saki-orbit/link-to-content/tree/main/skills/x-bilibili-transcript
```

把地址粘贴给 Codex、WorkBuddy 或 DeepSeek Harness，并发送：

> 请安装并启用这个 Skill。安装完成后告诉我怎么调用。

### 3. 直接发内容链接

安装好后，像聊天一样把视频、播客或博主主页链接发给 Agent。例如：

> 帮我把这个视频转成逐字稿和带时间戳的字幕：`<视频链接>`

也可以说“归档这个小红书博主的公开作品”或“把这期播客整理进飞书”，再贴对应链接。

### 各 Agent 的安装入口

- **Codex**：发送 `$skill-installer install https://github.com/saki-orbit/link-to-content/tree/main/skills/x-bilibili-transcript`。安装后重启 Codex，让它加载新 Skill。
- **WorkBuddy**：在“技能”中选择“添加技能”，导入 Skill 包；也可以先把 GitHub Skill 地址发给 Agent，按它提示完成安装。官方说明：[WorkBuddy 技能使用指南](https://www.workbuddy.cn/docs/workbuddy/From-Beginner-to-Expert-Guide/Function-Description/Skills-Market)。
- **DeepSeek Harness**：把仓库地址发给 Agent，请它安装所需 Skill；也可以在下载后的仓库目录运行 `bash scripts/install-to-dsh.sh x-bilibili-transcript`。

## 作者实测

2 分 48 秒的中文口播视频，使用本地模型约 25 秒完成转写。实际速度会随素材长度和设备变化。

## 仓库结构

每个目录都是独立 Skill，可按需安装：

- `skills/xiaohongshu-creator-archive`
- `skills/x-bilibili-transcript`
- `skills/multi-platform-media-transcript`
- `skills/podcast-to-feishu`
