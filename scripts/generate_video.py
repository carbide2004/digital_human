from __future__ import annotations

import argparse
import sys
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from backend.pipeline import GenerateVideoRequest, generate_avatar_video  # noqa: E402


def main() -> int:
    load_dotenv(ROOT / ".env")
    parser = argparse.ArgumentParser(description="使用 Boson AI 生成单图数字人朗读视频。")
    parser.add_argument("--face-image", required=True, type=Path, help="人脸图片路径，支持 PNG/JPEG/WEBP。")
    parser.add_argument("--reference-audio", required=True, type=Path, help="示例语音路径。")
    parser.add_argument("--text", required=True, help="要朗读的文本。")
    parser.add_argument("--reference-text", default="", help="示例语音对应文本，建议填写以提升声音克隆稳定性。")
    parser.add_argument("--size", default="480x640", help="视频尺寸，例如 480x640、640x640、640x480。")
    parser.add_argument("--output", default=ROOT / "outputs" / "result.mp4", type=Path, help="输出 MP4 路径。")
    parser.add_argument("--poll-interval", default=5.0, type=float, help="轮询间隔秒数。")
    parser.add_argument("--timeout", default=900, type=int, help="最长等待秒数。")
    args = parser.parse_args()

    result = generate_avatar_video(
        GenerateVideoRequest(
            face_image=args.face_image,
            reference_audio=args.reference_audio,
            text=args.text,
            reference_text=args.reference_text,
            size=args.size,
        ),
        output_path=args.output,
        poll_interval=args.poll_interval,
        timeout_seconds=args.timeout,
    )
    print(f"生成完成：video_id={result.video_id} status={result.status} output={result.output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
