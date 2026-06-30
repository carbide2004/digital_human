from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from backend.audio_utils import convert_to_mp3  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="把音频转成 Boson 更稳定支持的 MP3 格式。")
    parser.add_argument("input", type=Path, help="输入音频路径，例如 reference.m4a。")
    parser.add_argument("--output", type=Path, help="输出 MP3 路径，默认写到 outputs/converted_audio。")
    args = parser.parse_args()

    output = args.output or ROOT / "outputs" / "converted_audio" / f"{args.input.stem}.mp3"
    result = convert_to_mp3(args.input, output)
    print(f"转换完成：{result}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
