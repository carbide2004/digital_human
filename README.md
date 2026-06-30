# Boson 数字人视频 MVP

这个项目用 Boson AI 的 `higgs-avatar` 和 `higgs-tts-3` 做最小闭环：输入一张人脸图片、一段示例语音和朗读文本，生成单图数字人朗读视频。

默认生成流程是两步：先单独调用 TTS 生成 MP3，再用 MP3 驱动 Avatar 生成带声音的视频。这样可以绕开 `input_tts` 内部流式 TTS 的限流问题。

## 准备环境

```powershell
conda env create -f environment.yml
conda activate digital-human
Copy-Item .env.example .env
```

如果 `conda env create` 很慢，可以先创建基础环境，再用清华 PyPI 源安装 Python 依赖：

```powershell
conda create -n digital-human python=3.12 pip -y
conda activate digital-human
python -m pip install -i https://pypi.tuna.tsinghua.edu.cn/simple -r requirements.txt
Copy-Item .env.example .env
```

如果 conda 包下载本身很慢，建议先在本机配置 conda 镜像源，再重新执行上面的命令。

如果环境已经创建过，但缺少音频转换依赖，可以补装：

```powershell
python -m pip install imageio-ffmpeg
```

编辑 `.env`：

```text
BOSON_API_KEY=你的 Boson API Key
BOSON_BASE_URL=https://api.boson.ai/v1
```

## 命令行生成

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
- 图片会以内联 data URI 发送，注意官方文档中的图片大小限制。
- 默认最长等待 900 秒，可通过 `--timeout` 调整。

如果已经有生成好的音频，可以绕过 Boson 的 `input_tts`，直接用音频驱动视频：

```powershell
python .\scripts\generate_video_from_audio.py `
  --face-image .\samples\face.jpg `
  --audio .\outputs\tts_clone_test.mp3 `
  --size 480x640 `
  --output .\outputs\video_from_audio.mp4
```

这个脚本会直接下载 Boson 返回的 MP4。

## 单独测试 TTS

如果视频生成失败里出现 `tts stream failed: 429`，可以先单独测试 TTS 接口：

```powershell
python .\scripts\test_tts.py `
  --text "你好，这是一个 Boson TTS API 测试。" `
  --output .\outputs\tts_test.mp3
```

如果要测试参考音频声音克隆：

```powershell
python .\scripts\test_tts.py `
  --text "你好，这是一个参考音频声音克隆测试。" `
  --reference-audio .\samples\voice.wav `
  --reference-text "示例语音中的原文" `
  --output .\outputs\tts_clone_test.mp3
```

如果这个脚本也返回 `429 rate_limit_exceeded`，说明 TTS 模型本身已经被当前账号、API Key 或共享免费额度限流，不是 Avatar 视频接口的问题。

## 转换 m4a 音频

Boson 的参考音频接口可能不接受 `.m4a` 容器。项目会在视频生成和 TTS 克隆测试时自动把 `.m4a` 转成 `.mp3`，也可以手动转换：

```powershell
python .\scripts\convert_audio.py .\uploads\7ec7593ad08340df9b086e531cdb6a19\reference.m4a
```

默认输出到：

```text
outputs/converted_audio/reference.mp3
```

## 启动 Web 后端

```powershell
uvicorn backend.app:app --reload --host 127.0.0.1 --port 8000
```

打开：

```text
http://127.0.0.1:8000
```

页面会提交后台任务并轮询状态，完成后展示视频和下载链接。

## 服务器部署

服务器上建议用 conda 创建环境，`.env` 只在服务器本地配置，不提交到 git：

```bash
git clone <your-repo-url> digital_human
cd digital_human
conda env create -f environment.yml
conda activate digital-human
cp .env.example .env
```

编辑 `.env` 填入 `BOSON_API_KEY`，然后启动：

```bash
uvicorn backend.app:app --host 0.0.0.0 --port 8000
```

如果要长期运行，可以先用 systemd 或进程管理工具托管这个命令，再在前面接 Nginx 反向代理。生产环境不要把 `uploads/`、`outputs/` 和 `.env` 提交到仓库。

## 当前边界

- 任务状态暂存在内存里，服务重启后任务记录会丢失。
- 文件只保存在本地 `uploads/` 和 `outputs/`。
- 没有做用户鉴权、队列、限流重试和历史记录。
- 需要自行确认图片、声音和文本素材的授权。
