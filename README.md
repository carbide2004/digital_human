# Boson 数字人视频 MVP

这个项目基于 Boson AI 的 `higgs-tts-3` 和 `higgs-avatar` 做数字人视频生成：上传人脸图片，录制或上传参考声音，输入朗读文本，生成单图数字人朗读视频。

默认流程是：先调用 TTS 生成 MP3，再用 MP3 驱动 Avatar 生成带声音的 MP4。这样比直接使用 Avatar 的 `input_tts` 路径更容易定位 TTS、音频格式和视频生成问题。

请在北京时间的白天运行该项目，晚上由于调用 API 的请求过多常返回 `504 Gateway Time-out` 报错。

## 快速开始

### 1. 获取 Boson API Key

1. 打开 Boson AI 控制台并注册/登录账号。
2. 进入 Workspace 的 `API Keys` 页面。
3. 创建一个新的 API key，通常形如 `bai-...`。
4. 只把 key 填到本地 `.env`，不要提交到 git。

相关入口：

- Boson 文档：https://docs.boson.ai/overview
- Boson Workspace：https://www.boson.ai/workspace

### 2. 创建环境

默认使用 conda：

```powershell
conda env create -f environment.yml
conda activate digital-human
```

如果下载很慢，可以改用清华 PyPI 源安装 Python 依赖：

```powershell
conda create -n digital-human python=3.12 pip -y
conda activate digital-human
python -m pip install -i https://pypi.tuna.tsinghua.edu.cn/simple -r requirements.txt
```

如果 conda 包下载本身很慢，先配置 conda 镜像源，再重新执行上面的命令。

### 3. 配置 `.env`

复制 `.env.example` 为 `.env`，或直接新建 `.env`，然后填入：

```text
BOSON_API_KEY=你的 Boson API Key
BOSON_BASE_URL=https://api.boson.ai/v1
```

### 4. 启动网页

```powershell
uvicorn backend.app:app --reload --host 127.0.0.1 --port 8000
```

打开：

```text
http://127.0.0.1:8000
```

页面上按顺序操作：

1. 上传人脸图片。
2. 录制参考声音，或上传已有音频。
3. 输入希望数字人朗读的文本。
4. 可选：在右侧 `朗读文本 Tags` 面板点击情绪、韵律、风格、音效标签，标签会插入到朗读文本光标位置。
5. 点击 `生成视频`，等待任务完成后预览或下载 MP4。

## 前端使用说明

### 参考声音

- `录音`：浏览器申请麦克风权限，录制完成后上传参考音频。
- `上传音频`：上传本地音频文件作为参考声音。

浏览器录音通常是 `.webm` 或 `.ogg`，后端会自动转成 `.mp3` 后再调用 Boson。部署到服务器后，如果要使用浏览器录音，页面通常需要通过 HTTPS 访问；`localhost` 本地测试不受这个限制。

### 录音模式

- `朗读示例文本`：页面展示固定示例文本，并自动把这段文本作为 `reference_text` 传给后端。录音少于 15 秒会被拦截，建议录制 20-40 秒。
- `自由说话`：不传 `reference_text`，适合用户随便说几句话。

### 上传音频模式

上传音频时不会再选择“说话模式”，而是选择是否提供“与参考音频对应的文本内容”：

- `无文本`：不传 `reference_text`。
- `有文本`：填写上传音频中实际朗读或说出的内容。

### 朗读文本 Tags

右侧 `朗读文本 Tags` 面板按 Boson 官方分类列出标签：

- `情绪`：例如愉悦、热情、悲伤、愤怒。
- `韵律`：例如慢速、快速、停顿、长停顿、高音调。
- `风格`：例如歌唱、喊话、低声。
- `音效`：例如笑声、叹气、咳嗽、喷嚏。

点击按钮会把原始 tag 插入到朗读文本当前光标位置，例如：

```text
<|emotion:elation|>大家好，欢迎来到今天的演示。
```

## 命令行用法

### 生成视频

```powershell
python .\scripts\generate_video.py `
  --face-image .\samples\face.jpg `
  --reference-audio .\samples\voice.wav `
  --reference-text "示例语音中的原文" `
  --text "你好，这是一个数字人视频生成测试。" `
  --size 480x640 `
  --output .\outputs\demo.mp4
```

说明：

- `--reference-text` 建议填写，能提高参考音色复刻稳定性。
- 图片会以内联 data URI 发送，需要注意官方文档中的图片大小限制。
- 默认最长等待 900 秒，可通过 `--timeout` 调整。

如果已经有生成好的音频，可以绕过 TTS，直接用音频驱动视频：

```powershell
python .\scripts\generate_video_from_audio.py `
  --face-image .\samples\face.jpg `
  --audio .\outputs\tts_clone_test.mp3 `
  --size 480x640 `
  --output .\outputs\video_from_audio.mp4
```

## 单独测试 TTS

普通 TTS：

```powershell
python .\scripts\test_tts.py `
  --text "你好，这是一个 Boson TTS API 测试。" `
  --output .\outputs\tts_test.mp3
```

参考音频声音克隆：

```powershell
python .\scripts\test_tts.py `
  --text "你好，这是一个参考音频声音克隆测试。" `
  --reference-audio .\samples\voice.wav `
  --reference-text "示例语音中的原文" `
  --output .\outputs\tts_clone_test.mp3
```

如果这个脚本也返回 `429 rate_limit_exceeded`，说明 TTS 模型本身已经被当前账号、API Key 或共享免费额度限流，不是 Avatar 视频接口的问题。

如果 TTS 返回 `504 Gateway Time-out`，通常是 Boson 服务端处理超时，也可能和参考音频太短、录音质量差、`reference_text` 与音频内容不匹配有关。朗读示例文本模式需要完整朗读示例文本；如果只说几秒钟，建议切换到 `自由说话` 模式。

## 音频格式和转换

后端会自动处理常见音频：

- 直接支持：`.aac`、`.wav`、`.mp3`、`.flac`、`.opus`
- 自动转 MP3：`.m4a`、`.webm`、`.ogg`、`.oga`

也可以手动转换：

```powershell
python .\scripts\convert_audio.py .\uploads\example\reference.m4a
```

默认输出到：

```text
outputs/converted_audio/reference.mp3
```

如果环境已经创建过，但缺少音频转换依赖，可以补装：

```powershell
python -m pip install imageio-ffmpeg
```

## 服务器部署

服务器上建议仍然用 conda 创建环境，`.env` 只在服务器本地配置，不提交到 git：

```bash
git clone <your-repo-url> digital_human
cd digital_human
conda env create -f environment.yml
conda activate digital-human
```

复制 `.env.example` 为 `.env`，或直接新建 `.env`，填入 `BOSON_API_KEY`，然后启动：

```bash
uvicorn backend.app:app --host 0.0.0.0 --port 8000
```

如果要长期运行，可以用 systemd 或进程管理工具托管这个命令，再在前面接 Nginx 反向代理。生产环境不要把 `uploads/`、`outputs/` 和 `.env` 提交到仓库。

## 技术细节

### 后端流程

1. 保存上传的人脸图片和参考音频。
2. 检查/转换参考音频，必要时转成 MP3。
3. 调用 Boson TTS 生成朗读音频。
4. 调用 Boson Avatar，用生成的音频驱动人脸图片。
5. 下载 Boson 返回的 MP4，前端轮询任务状态并展示结果。

### 当前边界

- 任务状态暂存在内存里，服务重启后任务记录会丢失。
- 文件只保存在本地 `uploads/` 和 `outputs/`。
- 没有做用户鉴权、队列、限流重试和历史记录。
- 浏览器录音在公网部署时通常需要 HTTPS。
- 需要自行确认图片、声音和文本素材的授权。

## License

本项目代码计划使用 MIT License 开源。代码许可不覆盖 Boson AI 的 API、模型服务、额度、服务条款，也不代表生成内容或上传素材自动获得授权。

## 致谢

感谢 Boson AI 提供 `higgs-tts-3`、`higgs-avatar` 等多模态 API 能力，让这个数字人视频生成 MVP 可以用较少代码完成端到端验证。

感谢 Codex 在需求梳理、代码实现、调试排查和文档整理中的协助。
