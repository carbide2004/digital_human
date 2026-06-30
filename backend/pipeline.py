from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .audio_utils import prepare_reference_audio
from .boson_client import BosonClient, extract_status, extract_video_id


@dataclass(frozen=True)
class GenerateVideoRequest:
    face_image: Path
    reference_audio: Path
    text: str
    reference_text: str = ""
    size: str = "480x640"


@dataclass(frozen=True)
class GenerateVideoResult:
    video_id: str
    status: str
    output_path: Path


def generate_avatar_video(
    request: GenerateVideoRequest,
    *,
    output_path: Path,
    client: BosonClient | None = None,
    poll_interval: float = 5.0,
    timeout_seconds: int = 900,
) -> GenerateVideoResult:
    active_client = client or BosonClient()
    reference_audio = prepare_reference_audio(request.reference_audio, output_path.parent / "converted_audio")

    speech_path = output_path.parent / "generated_audio" / f"{output_path.stem}.mp3"
    active_client.create_speech(
        text=request.text,
        output_path=speech_path,
        reference_audio=reference_audio,
        reference_text=request.reference_text,
        response_format="mp3",
    )

    created = active_client.create_avatar_video_from_audio(
        face_image=request.face_image,
        size=request.size,
        driving_audio=speech_path,
    )
    video_id = extract_video_id(created)
    final_state = active_client.wait_for_video(
        video_id,
        poll_interval=poll_interval,
        timeout_seconds=timeout_seconds,
    )
    active_client.download_video(video_id, output_path)
    return GenerateVideoResult(
        video_id=video_id,
        status=extract_status(final_state),
        output_path=output_path,
    )
