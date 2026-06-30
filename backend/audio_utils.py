from __future__ import annotations

import shutil
import subprocess
from pathlib import Path


SUPPORTED_DIRECT_AUDIO_SUFFIXES = {".aac", ".wav", ".mp3", ".flac", ".opus"}


class AudioConversionError(RuntimeError):
    pass


def prepare_reference_audio(path: Path, output_dir: Path | None = None) -> Path:
    if path.suffix.lower() in SUPPORTED_DIRECT_AUDIO_SUFFIXES:
        return path
    if path.suffix.lower() == ".m4a":
        target_dir = output_dir or path.parent
        return convert_to_mp3(path, target_dir / f"{path.stem}.boson.mp3")
    return path


def convert_to_mp3(input_path: Path, output_path: Path) -> Path:
    ffmpeg = find_ffmpeg()
    if not ffmpeg:
        raise AudioConversionError(
            "需要 ffmpeg 才能转换 .m4a。请先运行：python -m pip install imageio-ffmpeg"
        )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    command = [
        ffmpeg,
        "-y",
        "-i",
        str(input_path),
        "-vn",
        "-acodec",
        "libmp3lame",
        "-ar",
        "24000",
        "-ac",
        "1",
        "-b:a",
        "128k",
        str(output_path),
    ]
    result = subprocess.run(command, capture_output=True, text=True, encoding="utf-8", errors="replace")
    if result.returncode != 0:
        raise AudioConversionError(f"音频转换失败：{result.stderr[-1000:]}")
    return output_path


def find_ffmpeg() -> str | None:
    ffmpeg = shutil.which("ffmpeg")
    if ffmpeg:
        return ffmpeg
    try:
        import imageio_ffmpeg
    except ImportError:
        return None
    return imageio_ffmpeg.get_ffmpeg_exe()
