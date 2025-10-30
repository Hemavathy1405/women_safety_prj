const express = require('express');
const http = require('http');
const { Server } = require('socket.io');
const cors = require('cors');
const path = require('path');

const app = express();
const server = http.createServer(app);
const io = new Server(server, { 
  cors: { origin: "*", methods: ["GET", "POST"] } 
});


// Serve dashboard
app.use(express.static(path.join(__dirname, '../dashboard')));

// ✅ Serve snippets folder from Python directory
app.use('/snippets', express.static(path.join(__dirname, '../python/snippets')));

app.use(cors());
app.use(express.json());

// ✅ Security key
const API_KEY = "secure_key_123";

// ✅ Serve dashboard + image snippets
app.use(express.static('../dashboard'));
app.use('/snippets', express.static(path.join(__dirname, '../python/snippets')));

// Store alerts
const alerts = [];
const MAX_ALERTS = 100;

// WebSocket connection
io.on('connection', (socket) => {
  console.log('✅ Dashboard connected:', socket.id);
  socket.emit('all_alerts', alerts);
  socket.on('disconnect', () => console.log('❌ Dashboard disconnected:', socket.id));
});

// Receive alerts from model
app.post('/send-alert', (req, res) => {
  const apiKey = req.headers['x-api-key'];
  if (apiKey !== API_KEY) {
    return res.status(403).json({ success: false, message: "Unauthorized: Invalid API key" });
  }
  app.post('/mark-safe', (req, res) => {
  const { id } = req.body;
  if (!id) return res.status(400).json({ success: false, message: "Missing id" });

  const alert = alerts.find(a => a.id === id && a.status === 'active');
  if (!alert) return res.status(404).json({ success: false, message: "Not found" });

  alert.status = 'resolved';
  alert.resolvedAt = new Date().toISOString();

  io.emit('alert_resolved', alert);
  res.json({ success: true, alert });
});


  const a = req.body;
  const alert = {
    severity: (a.severity || 'MEDIUM').toUpperCase(),
    place: a.place || 'Unknown',
    type: a.type || 'Safety Alert',
    cameraId: a.cameraId || 'CAM-000',
    description: a.description || 'No details',
    lat: a.lat || 11.1085,
    lng: a.lng || 77.3411,
    time: a.time || new Date().toISOString(),
    image: a.image || null,
    menCount: a.menCount || 0,
    womenCount: a.womenCount || 0,
    lighting: a.lighting || 'Unknown',
    receivedAt: new Date().toISOString()
  };

  alerts.unshift(alert);
  if (alerts.length > MAX_ALERTS) alerts.pop();
  io.emit('new_alert', alert);

  console.log(`🚨 NEW ALERT [${alert.severity}] ${alert.place} - ${alert.type}`);
  res.status(200).json({ success: true, alert });
});

// Other routes (same as before)
app.get('/alerts', (req, res) => res.json({ success: true, count: alerts.length, alerts }));
app.post('/clear-alerts', (req, res) => { alerts.length = 0; io.emit('alerts_cleared'); res.json({ success: true }); });
app.get('/health', (req, res) => res.json({ status: 'running', uptime: process.uptime(), alertCount: alerts.length }));

// Start server
const PORT = process.env.PORT || 3000;
server.listen(PORT, () => {
  console.log('\n' + '='.repeat(60));
  console.log('  🚨 WOMEN SAFETY MONITORING - SECURE BACKEND');
  console.log('='.repeat(60));
  console.log(`✅ Running on http://localhost:${PORT}`);
  console.log(`🖼️ Serving snippets from /snippets`);
  console.log('='.repeat(60));
});
