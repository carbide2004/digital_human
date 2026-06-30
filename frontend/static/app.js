const form = document.querySelector("#generate-form");
const button = document.querySelector("#submit-button");
const statusText = document.querySelector("#status");
const preview = document.querySelector("#preview");
const download = document.querySelector("#download");

let timer = null;

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  clearInterval(timer);
  preview.hidden = true;
  download.hidden = true;
  button.disabled = true;
  statusText.textContent = "正在提交任务。";

  try {
    const response = await fetch("/api/generate", {
      method: "POST",
      body: new FormData(form),
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
      button.disabled = false;
      preview.src = task.video_url;
      preview.hidden = false;
      download.href = `/api/tasks/${taskId}/video`;
      download.hidden = false;
      download.textContent = "下载 MP4";
    }
    if (task.status === "failed") {
      clearInterval(timer);
      button.disabled = false;
    }
  }, 3000);
}
