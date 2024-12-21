async function runETL() {
  const button = document.querySelector(".actions button");
  button.disabled = true;
  button.textContent = "Processing...";

  try {
    const response = await fetch("/api/v1/etl/run", {
      method: "POST",
    });
    const data = await response.json();

    document.getElementById("status").textContent = data.message;
  } catch (error) {
    document.getElementById("status").textContent = `Error: ${error.message}`;
  } finally {
    button.disabled = false;
    button.textContent = "Run ETL Process";
  }
}

// Update status and metrics every 5 seconds
setInterval(async () => {
  const response = await fetch("/api/v1/status");
  const data = await response.json();

  document.getElementById("status").textContent = data.status;
  document.getElementById("processed-count").textContent = data.processed_count;
  document.getElementById(
    "processing-time"
  ).textContent = `${data.processing_time.toFixed(2)}s`;
  document.getElementById("last-update").textContent = data.last_update
    ? new Date(data.last_update).toLocaleString()
    : "Never";
}, 5000);

document.getElementById("upload-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  const fileInput = document.getElementById("csv-file");
  const file = fileInput.files[0];
  if (!file) {
    document.getElementById("upload-status").textContent =
      "Please select a file";
    return;
  }

  const formData = new FormData();
  formData.append("file", file);

  try {
    const response = await fetch("/api/v1/transactions/upload", {
      method: "POST",
      body: formData,
    });
    const data = await response.json();
    document.getElementById("upload-status").textContent = data.message;
  } catch (error) {
    document.getElementById(
      "upload-status"
    ).textContent = `Upload failed: ${error.message}`;
  }
});
