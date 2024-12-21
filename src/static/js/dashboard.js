// Update status periodically
function updateStatus() {
  fetch("/api/status")
    .then((response) => response.json())
    .then((data) => {
      document.getElementById("status").textContent = data.status;
      document.getElementById("processed-count").textContent =
        data.processed_count;
      document.getElementById("processing-time").textContent =
        data.processing_time + "s";
      document.getElementById("last-update").textContent = data.last_update
        ? new Date(data.last_update).toLocaleString()
        : "Never";
    })
    .catch((error) => console.error("Error fetching status:", error));
}

// Run ETL process
function runETL() {
  fetch("/api/process", { method: "POST" })
    .then((response) => response.json())
    .then((data) => {
      console.log("ETL process started:", data);
      updateStatus();
    })
    .catch((error) => {
      console.error("Error starting ETL process:", error);
      alert("Error starting ETL process: " + error.message);
    });
}

// Handle file upload
document.getElementById("upload-form").addEventListener("submit", function (e) {
  e.preventDefault();

  const fileInput = document.getElementById("csv-file");
  const file = fileInput.files[0];

  if (!file) {
    alert("Please select a file to upload");
    return;
  }

  const formData = new FormData();
  formData.append("file", file);

  document.getElementById("upload-status").textContent = "Uploading...";

  fetch("/api/upload", {
    method: "POST",
    body: formData,
  })
    .then((response) => response.json())
    .then((data) => {
      document.getElementById("upload-status").textContent =
        "Upload successful!";
      updateStatus();
      fileInput.value = ""; // Clear the file input
    })
    .catch((error) => {
      console.error("Error uploading file:", error);
      document.getElementById("upload-status").textContent =
        "Upload failed: " + error.message;
    });
});

// Update status every 5 seconds
setInterval(updateStatus, 5000);

// Initial status update
updateStatus();
