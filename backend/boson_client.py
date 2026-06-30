from __future__ import annotations

import base64
import mimetypes
import os
import time
from pathlib import Path
from typing import Any

import requests


DONE_STATUSES = {"completed", "succeeded", "success", "done"}
FAILED_STATUSES = {"failed", "error", "cancelled", "canceled"}


class BosonApiError(RuntimeError):
    pass


class BosonClient:
    def __init__(self, api_key: str | None = None, base_url: str | None = None) -> None:
        self.api_key = api_key or os.getenv("BOSON_API_KEY")
        self.base_url = (base_url or os.getenv("BOSON_BASE_URL") or "https://api.boson.ai/v1").rstrip("/")
        if not self.api_key:
            raise BosonApiError("缺少 BOSON_API_KEY，请在 .env 或环境变量中配置。")

    @property
    def headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

    def create_avatar_video(
        self,
        *,
        face_image: Path,
        text: str,
        reference_audio: Path,
        reference_text: str = "",
        size: str = "480x640",
        avatar_model: str = "higgs-avatar",
        tts_model: str = "higgs-tts-3",
    ) -> dict[str, Any]:
        input_tts: dict[str, Any] = {
            "model": tts_model,
            "input": text,
            "ref_audio": file_to_data_uri(reference_audio),
        }
        if reference_text.strip():
            input_tts["ref_text"] = reference_text.strip()

        payload = {
            "model": avatar_model,
            "ref_image": file_to_data_uri(face_image),
            "input_tts": input_tts,
            "size": size,
        }

        response = requests.post(
            f"{self.base_url}/videos",
            headers=self.headers,
            json=payload,
            timeout=60,
        )
        return self._json_response(response, "创建视频任务失败")

    def create_avatar_video_from_audio(
        self,
        *,
        face_image: Path,
        driving_audio: Path,
        size: str = "480x640",
        avatar_model: str = "higgs-avatar",
    ) -> dict[str, Any]:
        payload = {
            "model": avatar_model,
            "ref_image": file_to_data_uri(face_image),
            "input": file_to_data_uri(driving_audio),
            "size": size,
        }

        response = requests.post(
            f"{self.base_url}/videos",
            headers=self.headers,
            json=payload,
            timeout=60,
        )
        return self._json_response(response, "创建音频驱动视频任务失败")

    def create_speech(
        self,
        *,
        text: str,
        output_path: Path,
        model: str = "higgs-tts-3",
        voice: str = "default",
        response_format: str = "mp3",
        reference_audio: Path | None = None,
        reference_text: str = "",
    ) -> Path:
        payload: dict[str, Any] = {
            "input": text,
            "model": model,
            "response_format": response_format,
            "stream": False,
        }
        if reference_audio:
            payload["ref_audio"] = file_to_data_uri(reference_audio)
            if reference_text.strip():
                payload["ref_text"] = reference_text.strip()
        else:
            payload["voice"] = voice

        response = requests.post(
            f"{self.base_url}/audio/speech",
            headers=self.headers,
            json=payload,
            timeout=120,
        )
        if response.status_code >= 400:
            raise BosonApiError(f"TTS 生成失败：HTTP {response.status_code} {response.text[:1000]}")

        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_bytes(response.content)
        return output_path

    def retrieve_video(self, video_id: str) -> dict[str, Any]:
        response = requests.get(
            f"{self.base_url}/videos/{video_id}",
            headers={"Authorization": f"Bearer {self.api_key}"},
            timeout=30,
        )
        return self._json_response(response, "查询视频任务失败")

    def wait_for_video(
        self,
        video_id: str,
        *,
        poll_interval: float = 5.0,
        timeout_seconds: int = 900,
    ) -> dict[str, Any]:
        deadline = time.monotonic() + timeout_seconds
        latest: dict[str, Any] = {}

        while time.monotonic() < deadline:
            latest = self.retrieve_video(video_id)
            status = extract_status(latest)
            if status in DONE_STATUSES:
                return latest
            if status in FAILED_STATUSES:
                raise BosonApiError(f"视频任务失败：{latest}")
            time.sleep(poll_interval)

        raise BosonApiError(f"等待视频任务超时：video_id={video_id}, latest={latest}")

    def download_video(self, video_id: str, output_path: Path) -> Path:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        response = requests.get(
            f"{self.base_url}/videos/{video_id}/content",
            headers={"Authorization": f"Bearer {self.api_key}"},
            timeout=120,
        )
        if response.status_code >= 400:
            raise BosonApiError(f"下载视频失败：HTTP {response.status_code} {response.text[:500]}")
        output_path.write_bytes(response.content)
        return output_path

    @staticmethod
    def _json_response(response: requests.Response, message: str) -> dict[str, Any]:
        if response.status_code >= 400:
            raise BosonApiError(f"{message}：HTTP {response.status_code} {response.text[:500]}")
        try:
            data = response.json()
        except ValueError as exc:
            raise BosonApiError(f"{message}：响应不是 JSON：{response.text[:500]}") from exc
        if not isinstance(data, dict):
            raise BosonApiError(f"{message}：响应结构异常：{data!r}")
        return data


def file_to_data_uri(path: Path) -> str:
    mime_type = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
    encoded = base64.b64encode(path.read_bytes()).decode("ascii")
    return f"data:{mime_type};base64,{encoded}"


def extract_video_id(data: dict[str, Any]) -> str:
    candidates = [
        data.get("id"),
        data.get("video_id"),
        data.get("video", {}).get("id") if isinstance(data.get("video"), dict) else None,
        data.get("data", {}).get("id") if isinstance(data.get("data"), dict) else None,
        data.get("data", {}).get("video_id") if isinstance(data.get("data"), dict) else None,
    ]
    for value in candidates:
        if isinstance(value, str) and value:
            return value
    raise BosonApiError(f"无法从响应中读取 video_id：{data}")


def extract_status(data: dict[str, Any]) -> str:
    candidates = [
        data.get("status"),
        data.get("video", {}).get("status") if isinstance(data.get("video"), dict) else None,
        data.get("data", {}).get("status") if isinstance(data.get("data"), dict) else None,
    ]
    for value in candidates:
        if isinstance(value, str) and value:
            return value.lower()
    return "unknown"
