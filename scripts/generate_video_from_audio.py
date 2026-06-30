from __future__ import annotations

import argparse
import sys
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from backend.audio_utils import prepare_reference_audio  # noqa: E402
from backend.boson_client import BosonClient, extract_status, extract_video_id  # noqa: E402


def main() -> int:
    load_dotenv(ROOT / ".env")
    parser = argparse.ArgumentParser(description="使用已有音频驱动 Boson Avatar 生成视频。")
    parser.add_argument("--face-image", required=True, type=Path, help="人脸图片路径。")
    parser.add_argument("--audio", required=True, type=Path, help="驱动音频路径，建议 MP3/WAV。")
    parser.add_argument("--size", default="480x640", help="视频尺寸，例如 480x640、640x640、640x480。")
    parser.add_argument("--output", default=ROOT / "outputs" / "video_from_audio.mp4", type=Path, help="输出 MP4 路径。")
    parser.add_argument("--poll-interval", default=5.0, type=float, help="轮询间隔秒数。")
    parser.add_argument("--timeout", default=900, type=int, help="最长等待秒数。")
    args = parser.parse_args()

    client = BosonClient()
    driving_audio = prepare_reference_audio(args.audio, ROOT / "outputs" / "converted_audio")
    created = client.create_avatar_video_from_audio(
        face_image=args.face_image,
        driving_audio=driving_audio,
        size=args.size,
    )
    video_id = extract_video_id(created)
    final_state = client.wait_for_video(
        video_id,
        poll_interval=args.poll_interval,
        timeout_seconds=args.timeout,
    )
    client.download_video(video_id, args.output)
    print(f"生成完成：video_id={video_id} status={extract_status(final_state)} output={args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
