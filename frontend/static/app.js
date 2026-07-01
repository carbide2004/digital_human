const form = document.querySelector("#generate-form");
const button = document.querySelector("#submit-button");
const statusText = document.querySelector("#status");
const preview = document.querySelector("#preview");
const download = document.querySelector("#download");
const sampleSection = document.querySelector("#sample-section");
const freeSection = document.querySelector("#free-section");
const sampleText = document.querySelector("#sample-text");
const speechModeSection = document.querySelector("#speech-mode-section");
const recordSection = document.querySelector("#record-section");
const uploadSection = document.querySelector("#upload-section");
const uploadReferenceTextSection = document.querySelector("#upload-reference-text-section");
const uploadReferenceTextField = document.querySelector("#upload-reference-text-field");
const uploadReferenceTextInput = document.querySelector("#upload-reference-text-input");
const fileInput = document.querySelector("#reference-audio-file");
const recordButton = document.querySelector("#record-button");
const stopButton = document.querySelector("#stop-button");
const resetRecordingButton = document.querySelector("#reset-recording-button");
const recordingStatus = document.querySelector("#recording-status");
const recordingPreview = document.querySelector("#recording-preview");

let timer = null;
let mediaRecorder = null;
let recordingChunks = [];
let recordingBlob = null;
let recordingUrl = null;
let recordingDurationSeconds = 0;
let recordingStartedAt = 0;

form.addEventListener("change", (event) => {
  if (event.target.name === "audio_source") {
    updateAudioSource();
  }
  if (event.target.name === "speech_mode") {
    updateSpeechMode();
  }
  if (event.target.name === "reference_text_mode") {
    updateReferenceTextMode();
  }
});

recordButton.addEventListener("click", async () => {
  try {
    const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    recordingChunks = [];
    recordingBlob = null;
    revokeRecordingUrl();

    const mimeType = pickRecordingMimeType();
    mediaRecorder = new MediaRecorder(stream, mimeType ? { mimeType } : undefined);
    mediaRecorder.addEventListener("dataavailable", (event) => {
      if (event.data.size > 0) {
        recordingChunks.push(event.data);
      }
    });
    mediaRecorder.addEventListener("stop", () => {
      const type = mediaRecorder.mimeType || "audio/webm";
      recordingBlob = new Blob(recordingChunks, { type });
      recordingDurationSeconds = Math.max(0, (Date.now() - recordingStartedAt) / 1000);
      recordingUrl = URL.createObjectURL(recordingBlob);
      recordingPreview.src = recordingUrl;
      recordingPreview.hidden = false;
      resetRecordingButton.disabled = false;
      recordingStatus.textContent = `录音完成，时长 ${recordingDurationSeconds.toFixed(1)} 秒，可回放确认。`;
      stream.getTracks().forEach((track) => track.stop());
    });

    recordingStartedAt = Date.now();
    mediaRecorder.start();
    recordButton.disabled = true;
    stopButton.disabled = false;
    resetRecordingButton.disabled = true;
    recordingPreview.hidden = true;
    recordingStatus.textContent = "正在录音。";
  } catch (error) {
    recordingStatus.textContent = `无法开始录音：${error.message}`;
  }
});

stopButton.addEventListener("click", () => {
  if (mediaRecorder && mediaRecorder.state === "recording") {
    mediaRecorder.stop();
  }
  recordButton.disabled = false;
  stopButton.disabled = true;
});

resetRecordingButton.addEventListener("click", () => {
  recordingBlob = null;
  recordingDurationSeconds = 0;
  recordingChunks = [];
  revokeRecordingUrl();
  recordingPreview.hidden = true;
  resetRecordingButton.disabled = true;
  recordingStatus.textContent = "尚未录音。";
});

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  clearInterval(timer);
  preview.hidden = true;
  download.hidden = true;
  button.disabled = true;
  statusText.textContent = "正在提交任务。";

  try {
    const payload = buildPayload();
    const response = await fetch("/api/generate", {
      method: "POST",
      body: payload,
    });
    const data = await response.json();
    if (!response.ok) {
      throw new Error(data.detail || "提交失败。");
    }
    statusText.textContent = `任务已提交：${data.task_id}`;
    pollTask(data.task_id);
  } catch (error) {
    statusText.textContent = error.message;
    button.disabled = false;
  }
});

function buildPayload() {
  const formData = new FormData(form);
  const source = getCheckedValue("audio_source");

  formData.delete("audio_source");
  formData.delete("speech_mode");
  formData.delete("reference_text_mode");
  formData.delete("reference_audio");
  formData.delete("reference_text");

  if (source === "record") {
    const mode = getCheckedValue("speech_mode");
    formData.set("reference_text", mode === "sample" ? sampleText.textContent.trim() : "");

    if (!recordingBlob) {
      throw new Error("请先完成录音。");
    }
    if (recordingBlob.size === 0) {
      throw new Error("录音文件为空，请重录。");
    }
    if (mode === "sample" && recordingDurationSeconds < 15) {
      throw new Error("朗读示例文本的录音太短，请完整朗读示例文本，建议录制 20-40 秒。");
    }
    if (mode === "free" && recordingDurationSeconds < 2) {
      throw new Error("自由说话录音太短，请至少录制 2 秒。");
    }
    const extension = recordingBlob.type.includes("ogg") ? "ogg" : "webm";
    formData.set("reference_audio", recordingBlob, `recording.${extension}`);
    return formData;
  }

  if (!fileInput.files.length) {
    throw new Error("请上传参考音频。");
  }

  if (getCheckedValue("reference_text_mode") === "text") {
    const referenceText = uploadReferenceTextInput.value.trim();
    if (!referenceText) {
      throw new Error("请输入参考音频对应文本，或选择无参考文本。");
    }
    formData.set("reference_text", referenceText);
  } else {
    formData.set("reference_text", "");
  }

  formData.set("reference_audio", fileInput.files[0]);
  return formData;
}

function pollTask(taskId) {
  timer = setInterval(async () => {
    const response = await fetch(`/api/tasks/${taskId}`);
    const task = await response.json();
    if (!response.ok) {
      statusText.textContent = task.detail || "查询任务失败。";
      clearInterval(timer);
      button.disabled = false;
      return;
    }

    statusText.textContent = `${task.status}：${task.message}`;
    if (task.status === "completed") {
      clearInterval(timer);
      timer = null;
      button.disabled = false;
      preview.src = task.video_url;
      preview.hidden = false;
      download.href = `/api/tasks/${taskId}/video`;
      download.hidden = false;
      download.textContent = "下载 MP4";
    }
    if (task.status === "failed") {
      clearInterval(timer);
      timer = null;
      button.disabled = false;
    }
  }, 3000);
}

function updateAudioSource() {
  const source = getCheckedValue("audio_source");
  const recording = source === "record";
  speechModeSection.hidden = !recording;
  recordSection.hidden = !recording;
  uploadSection.hidden = recording;
  uploadReferenceTextSection.hidden = recording;
  uploadReferenceTextField.hidden = recording || getCheckedValue("reference_text_mode") !== "text";
  updateSpeechMode();
}

function updateSpeechMode() {
  if (getCheckedValue("audio_source") !== "record") {
    sampleSection.hidden = true;
    freeSection.hidden = true;
    return;
  }
  const sample = getCheckedValue("speech_mode") === "sample";
  sampleSection.hidden = !sample;
  freeSection.hidden = sample;
}

function updateReferenceTextMode() {
  uploadReferenceTextField.hidden =
    getCheckedValue("audio_source") !== "upload" || getCheckedValue("reference_text_mode") !== "text";
}

function getCheckedValue(name) {
  return form.querySelector(`input[name="${name}"]:checked`).value;
}

function pickRecordingMimeType() {
  const candidates = ["audio/webm;codecs=opus", "audio/webm", "audio/ogg;codecs=opus", "audio/ogg"];
  return candidates.find((type) => MediaRecorder.isTypeSupported(type)) || "";
}

function revokeRecordingUrl() {
  if (recordingUrl) {
    URL.revokeObjectURL(recordingUrl);
    recordingUrl = null;
  }
}

updateAudioSource();
updateSpeechMode();
updateReferenceTextMode();
