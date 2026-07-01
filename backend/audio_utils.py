from __future__ import annotations

import shutil
import subprocess
import re
from pathlib import Path


SUPPORTED_DIRECT_AUDIO_SUFFIXES = {".aac", ".wav", ".mp3", ".flac", ".opus"}
CONVERT_TO_MP3_SUFFIXES = {".m4a", ".webm", ".ogg", ".oga"}


class AudioConversionError(RuntimeError):
    pass


class AudioValidationError(RuntimeError):
    pass


def prepare_reference_audio(path: Path, output_dir: Path | None = None) -> Path:
    if path.suffix.lower() in SUPPORTED_DIRECT_AUDIO_SUFFIXES:
        validate_audio(path)
        return path
    if path.suffix.lower() in CONVERT_TO_MP3_SUFFIXES:
        target_dir = output_dir or path.parent
        converted = convert_to_mp3(path, target_dir / f"{path.stem}.boson.mp3")
        validate_audio(converted)
        return converted
    return path


def convert_to_mp3(input_path: Path, output_path: Path) -> Path:
    ffmpeg = find_ffmpeg()
    if not ffmpeg:
        raise AudioConversionError(
            "需要 ffmpeg 才能转换参考音频。请先运行：python -m pip install imageio-ffmpeg"
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


def validate_audio(path: Path, min_duration_seconds: float = 1.0) -> None:
    duration = get_audio_duration_seconds(path)
    if duration < min_duration_seconds:
        raise AudioValidationError(f"参考音频太短或无法读取：{path.name}, duration={duration:.2f}s")


def get_audio_duration_seconds(path: Path) -> float:
    ffmpeg = find_ffmpeg()
    if not ffmpeg:
        raise AudioValidationError("需要 ffmpeg 才能检查音频。请先运行：python -m pip install imageio-ffmpeg")

    result = subprocess.run(
        [ffmpeg, "-hide_banner", "-i", str(path)],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    output = result.stderr + result.stdout
    match = re.search(r"Duration:\s*(\d+):(\d+):(\d+(?:\.\d+)?)", output)
    if not match:
        raise AudioValidationError(f"无法读取参考音频时长：{path.name}")
    hours, minutes, seconds = match.groups()
    return int(hours) * 3600 + int(minutes) * 60 + float(seconds)


def find_ffmpeg() -> str | None:
    ffmpeg = shutil.which("ffmpeg")
    if ffmpeg:
        return ffmpeg
    try:
        import imageio_ffmpeg
    except ImportError:
        return None
    return imageio_ffmpeg.get_ffmpeg_exe()
