// server.js – Express backend with SQLite, Socket.io, and scheduled jobs

const express = require('express');
const http = require('http');
const path = require('path');
const cors = require('cors');
const socketIo = require('socket.io');
const fetch = require('node-fetch');
const cron = require('node-cron');

// Local helpers
const { addOrUpdateUser, getUser, getAllUsers } = require('./db');
const { notifyAdmin } = require('./telegram');

const app = express();
const server = http.createServer(app);
const io = socketIo(server, { cors: { origin: "*" } });

app.use(cors());
app.use(express.json());
// Serve static files (frontend) from the project root
app.use(express.static(__dirname));

// ---------- API ----------
// Register or update user location (called from client)
app.post('/api/register', (req, res) => {
  const { id, lat, lon } = req.body;
  if (!id) return res.status(400).json({ error: 'Missing user id' });

  addOrUpdateUser(id, lat, lon);

  // Check if this is a brand‑new user (created_at == now)
  const user = getUser(id);
  const now = new Date().toISOString();
  // If created_at is within last few seconds, treat as new
  if (new Date(user.created_at).getTime() >= Date.now() - 5000) {
    const msg = `🆕 Yangi foydalanuvchi: ${id}\nLokatsiya: ${lat?.toFixed(4)} , ${lon?.toFixed(4)}`;
    notifyAdmin(msg);
    io.of('/admin').emit('new_user', { id, lat, lon, created_at: now });
  }

  res.json({ success: true });
});

// Admin endpoint – list all users (JSON)
app.get('/admin/users', (req, res) => {
  const rows = getAllUsers();
  res.json(rows);
});

// Serve admin dashboard page
app.get('/admin', (req, res) => {
  res.sendFile(path.join(__dirname, 'admin.html'));
});

// ---------- Socket.io ----------
// Admin namespace – receives real‑time notifications
io.of('/admin').on('connection', socket => {
  console.log('Admin connected:', socket.id);
});

// User namespace – optional future direct pushes
io.of('/user').on('connection', socket => {
  console.log('User socket connected:', socket.id);
  socket.on('register', data => {
    socket.userId = data.id; // store for possible direct messages
  });
});

// ---------- Helper: fetch prayer times from Aladhan ----------
async function fetchPrayerTimes(lat, lon) {
  const url = `https://api.aladhan.com/v1/timings?latitude=${lat}&longitude=${lon}&method=2`;
  const resp = await fetch(url);
  const json = await resp.json();
  return json.data.timings; // object {Fajr:..., Dhuhr:..., ...}
}

// ---------- Scheduler: 15‑minute reminder ----------
cron.schedule('* * * * *', async () => {
  const now = new Date();
  const users = getAllUsers().filter(u => u.lat && u.lon);
  for (const user of users) {
    try {
      const timings = await fetchPrayerTimes(user.lat, user.lon);
      const prayers = ['Fajr', 'Dhuhr', 'Asr', 'Maghrib', 'Isha'];
      for (const p of prayers) {
        const [h, m] = timings[p].split(':').map(Number);
        const prayerDate = new Date(now.getFullYear(), now.getMonth(), now.getDate(), h, m);
        const diffMin = Math.round((prayerDate - now) / 60000);
        if (diffMin === 15) {
          const txt = `⏰ ${p} namoziga 15 daqiqa qoldi (${timings[p]})`;
          io.of('/admin').emit('prayer_reminder', { userId: user.id, prayer: p, time: timings[p] });
          notifyAdmin(txt + ` – foydalanuvchi ${user.id}`);
        }
      }
    } catch (e) {
      console.error('Reminder error for', user.id, e);
    }
  }
});

// ---------- Scheduler: daily summary at 08:00 ----------
cron.schedule('0 8 * * *', async () => {
  const users = getAllUsers().filter(u => u.lat && u.lon);
  for (const user of users) {
    try {
      const timings = await fetchPrayerTimes(user.lat, user.lon);
      const summary = Object.entries(timings)
        .map(([k, v]) => `${k}: ${v}`)
        .join('\n');
      const txt = `📅 Bugungi namoz vaqtlari (foydalanuvchi ${user.id}):\n${summary}`;
      io.of('/admin').emit('daily_summary', { userId: user.id, summary });
      notifyAdmin(txt);
    } catch (e) {
      console.error('Daily summary error for', user.id, e);
    }
  }
});

// ---------- Start server ----------
const PORT = process.env.PORT || 3000;
server.listen(PORT, () => {
  console.log(`Server listening on http://localhost:${PORT}`);
});
