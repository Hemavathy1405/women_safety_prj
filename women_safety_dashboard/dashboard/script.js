// -------- Login function --------
function login() {
  const user = document.getElementById('userid').value;
  const pass = document.getElementById('password').value;

  if (user === "police" && pass === "1234") {
    alert("Login successful!");
    document.getElementById('login-section').style.display = "none";
    document.getElementById('dashboard').style.display = "block";
  } else {
    alert("Wrong ID or password!");
  }
}

// -------- Real-time alert handling --------
// This connects to your live backend server
const socket = io("https://backend1-ixbn.onrender.com");

socket.on("all_alerts", (allAlerts) => {
  const alertsDiv = document.getElementById("alerts");
  alertsDiv.innerHTML = "";
  allAlerts.forEach(alert => {
    displayAlert(alert);
  });
});

socket.on("new_alert", (alert) => {
  displayAlert(alert);
});

//
// --- MODIFIED FUNCTION ---
// This function now handles all your new data fields
//
function displayAlert(alert) {
  const alertsDiv = document.getElementById("alerts");
  const alertBox = document.createElement("div");
  let htmlContent = ""; // We will build the HTML content here

  // First, check if there is a video/photo snippet URL
  let mediaLink = "";
  if (alert.snippetUrl) {
    mediaLink = `<a href="${alert.snippetUrl}" target="_blank">View Snippet (Video/Photo)</a><br>`;
  }

  // Check if it's an SOS alert (it has a 'battery' property)
  if (alert.battery) {
    alertBox.className = 'alert-box high'; // All SOS alerts are high severity
    htmlContent = `
      <strong>Type:</strong> 🚨 SOS APP ALERT 🚨<br>
      <strong>Location:</strong> ${alert.location || 'Unknown'}<br>
      <strong>Battery:</strong> ${alert.battery || 'N/A'}<br>
      ${mediaLink}
    `;
  }
  // Otherwise, it's a Camera alert
  else {
    alertBox.className = `alert-box ${alert.severity ? alert.severity.toLowerCase() : 'normal'}`;
    htmlContent = `
      <strong>Type:</strong> ${alert.type || 'Camera Alert'}<br>
      <strong>Place:</strong> ${alert.place || 'Unknown'}<br>
      <strong>Monitor:</strong> ${alert.location_monitor || 'N/A'}<br>
      <strong>Severity:</strong> ${alert.severity || 'Normal'}<br>
      ${mediaLink}
    `;
  }

  alertBox.innerHTML = htmlContent;
  alertsDiv.prepend(alertBox);
}
