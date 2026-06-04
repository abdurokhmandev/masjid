const Database = require('better-sqlite3');
const path = require('path');

// Ensure data directory exists
const fs = require('fs');
const dataDir = path.join(__dirname, 'data');
if (!fs.existsSync(dataDir)) {
  fs.mkdirSync(dataDir);
}

const dbPath = path.join(dataDir, 'mosque_bot.db');
const db = new Database(dbPath);

// Initialize tables
db.exec(`
  CREATE TABLE IF NOT EXISTS users (
    id TEXT PRIMARY KEY,
    lat REAL,
    lon REAL,
    created_at TEXT DEFAULT (datetime('now')),
    last_active TEXT DEFAULT (datetime('now'))
  );
`);

function addOrUpdateUser(id, lat, lon) {
  const now = new Date().toISOString();
  const stmt = db.prepare(`
    INSERT INTO users (id, lat, lon, created_at, last_active)
    VALUES (?, ?, ?, ?, ?)
    ON CONFLICT(id) DO UPDATE SET
      lat = excluded.lat,
      lon = excluded.lon,
      last_active = excluded.last_active;
  `);
  stmt.run(id, lat, lon, now, now);
}

function getUser(id) {
  return db.prepare('SELECT * FROM users WHERE id = ?').get(id);
}

function getAllUsers() {
  return db.prepare('SELECT * FROM users').all();
}

module.exports = { addOrUpdateUser, getUser, getAllUsers };
