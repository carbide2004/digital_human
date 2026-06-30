from __future__ import annotations

import shutil
import uuid
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Literal

from dotenv import load_dotenv
from fastapi import BackgroundTasks, FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from .boson_client import BosonApiError
from .pipeline import GenerateVideoRequest, generate_avatar_video


load_dotenv()

ROOT = Path(__file__).resolve().parent.parent
UPLOAD_DIR = ROOT / "uploads"
OUTPUT_DIR = ROOT / "outputs"
FRONTEND_DIR = ROOT / "frontend"

UPLOAD_DIR.mkdir(exist_ok=True)
OUTPUT_DIR.mkdir(exist_ok=True)

TaskStatus = Literal["queued", "running", "completed", "failed"]


@dataclass
class TaskRecord:
    task_id: str
    status: TaskStatus
    message: str = ""
    video_id: str = ""
    video_url: str = ""


TASKS: dict[str, TaskRecord] = {}

app = FastAPI(title="Digital Human Boson MVP")
app.mount("/outputs", StaticFiles(directory=OUTPUT_DIR), name="outputs")
app.mount("/static", StaticFiles(directory=FRONTEND_DIR / "static"), name="static")


@app.get("/")
def index() -> FileResponse:
    return FileResponse(FRONTEND_DIR / "index.html")


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok", "generation_mode": "tts_then_avatar_audio_input"}


@app.post("/api/generate")
def create_task(
    background_tasks: BackgroundTasks,
    face_image: UploadFile = File(...),
    reference_audio: UploadFile = File(...),
    text: str = Form(...),
    reference_text: str = Form(""),
    size: str = Form("480x640"),
) -> dict[str, str]:
    if not text.strip():
        raise HTTPException(status_code=400, detail="朗读文本不能为空。")

    task_id = uuid.uuid4().hex
    task_dir = UPLOAD_DIR / task_id
    task_dir.mkdir(parents=True, exist_ok=True)

    face_path = save_upload(face_image, task_dir / f"face{suffix_of(face_image.filename)}")
    audio_path = save_upload(reference_audio, task_dir / f"reference{suffix_of(reference_audio.filename)}")

    TASKS[task_id] = TaskRecord(task_id=task_id, status="queued", message="任务已创建。")
    background_tasks.add_task(
        run_task,
        task_id,
        face_path,
        audio_path,
        text.strip(),
        reference_text.strip(),
        size,
    )
    return {"task_id": task_id, "status_url": f"/api/tasks/{task_id}"}


@app.get("/api/tasks/{task_id}")
def get_task(task_id: str) -> dict[str, str]:
    task = TASKS.get(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在。")
    return asdict(task)


@app.get("/api/tasks/{task_id}/video")
def get_task_video(task_id: str) -> FileResponse:
    task = TASKS.get(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在。")
    output_path = OUTPUT_DIR / f"{task_id}.mp4"
    if task.status != "completed" or not output_path.exists():
        raise HTTPException(status_code=409, detail="视频尚未生成完成。")
    return FileResponse(output_path, media_type="video/mp4", filename=f"{task_id}.mp4")


def run_task(
    task_id: str,
    face_path: Path,
    audio_path: Path,
    text: str,
    reference_text: str,
    size: str,
) -> None:
    task = TASKS[task_id]
    task.status = "running"
    task.message = "正在生成语音并调用 Boson AI 生成视频。"
    output_path = OUTPUT_DIR / f"{task_id}.mp4"

    try:
        result = generate_avatar_video(
            GenerateVideoRequest(
                face_image=face_path,
                reference_audio=audio_path,
                text=text,
                reference_text=reference_text,
                size=size,
            ),
            output_path=output_path,
        )
    except BosonApiError as exc:
        task.status = "failed"
        task.message = str(exc)
        return
    except Exception as exc:  # noqa: BLE001
        task.status = "failed"
        task.message = f"生成失败：{exc}"
        return

    task.status = "completed"
    task.video_id = result.video_id
    task.video_url = f"/outputs/{task_id}.mp4"
    task.message = "视频生成完成。"


def save_upload(upload: UploadFile, destination: Path) -> Path:
    with destination.open("wb") as file:
        shutil.copyfileobj(upload.file, file)
    return destination


def suffix_of(filename: str | None) -> str:
    if not filename:
        return ""
    suffix = Path(filename).suffix.lower()
    return suffix if suffix else ""
