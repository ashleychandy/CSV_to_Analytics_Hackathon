// Global variables
let currentPage = 1;
let totalPages = 1;
let tenderChart = null;
let storeChart = null;

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

// Load transaction data
function loadData(page = 1) {
  fetch(`/api/data?page=${page}`)
    .then((response) => response.json())
    .then((data) => {
      currentPage = data.page;
      totalPages = data.total_pages;

      // Update table
      const tbody = document.getElementById("data-body");
      tbody.innerHTML = "";

      data.data.forEach((record) => {
        const row = document.createElement("tr");
        row.innerHTML = `
                    <td>${record.store_display_name}</td>
                    <td>${new Date(record.trans_date).toLocaleDateString()}</td>
                    <td>${record.trans_time}</td>
                    <td>${record.trans_no}</td>
                    <td>${record.net_sales_header_values.toFixed(2)}</td>
                    <td>${record.quantity}</td>
                    <td>${record.tender || "N/A"}</td>
                `;
        tbody.appendChild(row);
      });

      // Update pagination
      document.getElementById(
        "page-info"
      ).textContent = `Page ${page} of ${data.total_pages}`;
    })
    .catch((error) => console.error("Error loading data:", error));
}

// Load analytics
function loadAnalytics() {
  fetch("/api/analytics")
    .then((response) => response.json())
    .then((data) => {
      // Update summary cards
      document.getElementById(
        "total-sales"
      ).textContent = `$${data.total_sales.toFixed(2)}`;
      document.getElementById("total-transactions").textContent =
        data.total_transactions;
      document.getElementById(
        "avg-transaction"
      ).textContent = `$${data.average_transaction_value.toFixed(2)}`;

      // Update charts
      updateTenderChart(data.sales_by_tender);
      updateStoreChart(data.sales_by_store);
    })
    .catch((error) => console.error("Error loading analytics:", error));
}

// Update tender type chart
function updateTenderChart(data) {
  const ctx = document.getElementById("tenderChart").getContext("2d");

  if (tenderChart) {
    tenderChart.destroy();
  }

  tenderChart = new Chart(ctx, {
    type: "pie",
    data: {
      labels: data.map((item) => item.tender),
      datasets: [
        {
          data: data.map((item) => item.total),
          backgroundColor: [
            "#FF6384",
            "#36A2EB",
            "#FFCE56",
            "#4BC0C0",
            "#9966FF",
          ],
        },
      ],
    },
    options: {
      responsive: true,
      plugins: {
        legend: {
          position: "right",
        },
      },
    },
  });
}

// Update store chart
function updateStoreChart(data) {
  const ctx = document.getElementById("storeChart").getContext("2d");

  if (storeChart) {
    storeChart.destroy();
  }

  storeChart = new Chart(ctx, {
    type: "bar",
    data: {
      labels: data.map((item) => item.store_code),
      datasets: [
        {
          label: "Sales",
          data: data.map((item) => item.total),
          backgroundColor: "#36A2EB",
        },
      ],
    },
    options: {
      responsive: true,
      scales: {
        y: {
          beginAtZero: true,
        },
      },
    },
  });
}

// Pagination handlers
function previousPage() {
  if (currentPage > 1) {
    loadData(currentPage - 1);
  }
}

function nextPage() {
  if (currentPage < totalPages) {
    loadData(currentPage + 1);
  }
}

// Export data
function exportData() {
  fetch("/api/export")
    .then((response) => response.json())
    .then((data) => {
      // Convert to CSV
      const headers = Object.keys(data[0]);
      const csv = [
        headers.join(","),
        ...data.map((row) =>
          headers.map((header) => JSON.stringify(row[header])).join(",")
        ),
      ].join("\n");

      // Download file
      const blob = new Blob([csv], { type: "text/csv" });
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `transactions_${new Date().toISOString().split("T")[0]}.csv`;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);
    })
    .catch((error) => {
      console.error("Error exporting data:", error);
      alert("Error exporting data: " + error.message);
    });
}

// Run ETL process
function runETL() {
  fetch("/api/process", { method: "POST" })
    .then((response) => response.json())
    .then((data) => {
      console.log("ETL process started:", data);
      updateStatus();
      loadData();
      loadAnalytics();
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
      loadData();
      loadAnalytics();
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

// Initial load
updateStatus();
loadData();
loadAnalytics();
