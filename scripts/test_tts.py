from __future__ import annotations

import argparse
import sys
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from backend.boson_client import BosonClient  # noqa: E402
from backend.audio_utils import prepare_reference_audio  # noqa: E402


def main() -> int:
    load_dotenv(ROOT / ".env")
    parser = argparse.ArgumentParser(description="直接调用 Boson TTS，测试 higgs-tts-3 是否可用。")
    parser.add_argument("--text", default="你好，这是一个 Boson TTS API 测试。", help="要转成语音的文本。")
    parser.add_argument("--output", default=ROOT / "outputs" / "tts_test.mp3", type=Path, help="输出音频路径。")
    parser.add_argument("--model", default="higgs-tts-3", help="TTS 模型 ID。")
    parser.add_argument("--voice", default="default", help="预设音色；不传参考音频时使用。")
    parser.add_argument(
        "--format",
        default="mp3",
        choices=["mp3", "opus", "pcm", "wav", "aac", "flac"],
        help="输出音频格式。",
    )
    parser.add_argument("--reference-audio", type=Path, help="可选：参考音频路径，用于测试一次性声音克隆。")
    parser.add_argument("--reference-text", default="", help="可选：参考音频对应文本。")
    args = parser.parse_args()

    output_path = args.output
    if output_path.suffix.lower().lstrip(".") != args.format:
        output_path = output_path.with_suffix(f".{args.format}")

    client = BosonClient()
    reference_audio = (
        prepare_reference_audio(args.reference_audio, ROOT / "outputs" / "converted_audio")
        if args.reference_audio
        else None
    )
    result = client.create_speech(
        text=args.text,
        output_path=output_path,
        model=args.model,
        voice=args.voice,
        response_format=args.format,
        reference_audio=reference_audio,
        reference_text=args.reference_text,
    )
    print(f"TTS 生成完成：{result}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
