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
const socket = io("http://localhost:3000");

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

function displayAlert(alert) {
  const alertsDiv = document.getElementById("alerts");
  const alertBox = document.createElement("div");
  alertBox.className = `alert-box ${alert.severity ? alert.severity.toLowerCase() : ''}`;

  alertBox.innerHTML = `
    <strong>Place:</strong> ${alert.place || 'Unknown'}<br>
    <strong>Type:</strong> ${alert.type || 'Not specified'}<br>
    <strong>Severity:</strong> ${alert.severity || 'Normal'}
  `;

  alertsDiv.prepend(alertBox);
}
