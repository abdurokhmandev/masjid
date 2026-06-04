// script.js – Mosque finder & Prayer Times Bot
// Dependencies: Leaflet, fetch API, Nominatim (geocoding), Overpass API, Aladhan API

// ==== Configuration ==== //
const OVERPASS_ENDPOINT = "https://overpass-api.de/api/interpreter";
const NOMINATIM_ENDPOINT = "https://nominatim.openstreetmap.org/search";
const ALADHAN_ENDPOINT = "https://api.aladhan.com/v1/timings";

// UI elements
const mapDiv = document.getElementById("map");
const prayerBtn = document.getElementById("prayerBtn");
const modal = document.getElementById("prayerModal");
const modalContent = document.getElementById("prayerContent");
const closeBtn = document.querySelector(".close");

let map; // Leaflet map instance
let userLatLng; // {lat, lon}

// ---- Helper Functions ---- //
function initMap(lat, lon) {
  if (map) map.remove();
  map = L.map("map").setView([lat, lon], 13);
  L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
    attribution: '&copy; OpenStreetMap contributors'
  }).addTo(map);
}

function showLoading(message) {
  const loader = document.getElementById("loader");
  loader.textContent = message;
  loader.style.display = "block";
}
function hideLoading() {
  const loader = document.getElementById("loader");
  loader.style.display = "none";
}

function fetchJSON(url) {
  return fetch(url).then(r => {
    if (!r.ok) throw new Error(`HTTP ${r.status}`);
    return r.json();
  });
}

function geocodeAddress(address) {
  const params = new URLSearchParams({
    q: address,
    format: "json",
    limit: 1,
    addressdetails: 1
  });
  return fetchJSON(`${NOMINATIM_ENDPOINT}?${params}`);
}

function getNearbyMosques(lat, lon) {
  // Overpass query: amenity=mosque within 5km radius
  const query = `[
    out:json][timeout:25];
    (node[\"amenity\"=\"mosque\"](around:5000,${lat},${lon});
    way[\"amenity\"=\"mosque\"](around:5000,${lat},${lon});
    relation[\"amenity\"=\"mosque\"](around:5000,${lat},${lon});
  );
  out center;`;
  const body = new URLSearchParams({ data: query });
  return fetch(OVERPASS_ENDPOINT, {
    method: "POST",
    body
  }).then(r => r.json());
}

function addMosqueMarkers(data) {
  const markers = [];
  data.elements.forEach(el => {
    let lat, lon, name;
    if (el.type === "node") {
      lat = el.lat; lon = el.lon;
    } else if (el.type === "way" || el.type === "relation") {
      lat = el.center.lat; lon = el.center.lon;
    }
    name = el.tags && el.tags.name ? el.tags.name : "Mosque";
    const marker = L.marker([lat, lon]).addTo(map)
      .bindPopup(`<b>${name}</b>`);
    markers.push(marker);
  });
  if (markers.length) {
    const group = L.featureGroup(markers);
    map.fitBounds(group.getBounds().pad(0.2));
  }
}

function fetchPrayerTimes(lat, lon) {
  const params = new URLSearchParams({
    latitude: lat,
    longitude: lon,
    method: 2 // Islamic Society of North America (adjustable)
  });
  return fetchJSON(`${ALADHAN_ENDPOINT}?${params}`);
}

function renderPrayerTimes(data) {
  const timings = data.data.timings;
  const table = document.createElement("table");
  table.className = "prayer-table";
  const tbody = document.createElement("tbody");
  Object.entries(timings).forEach(([name, time]) => {
    const tr = document.createElement("tr");
    const td1 = document.createElement("td"); td1.textContent = name;
    const td2 = document.createElement("td"); td2.textContent = time;
    tr.appendChild(td1); tr.appendChild(td2);
    tbody.appendChild(tr);
  });
  table.appendChild(tbody);
  modalContent.innerHTML = ""; // clear
  modalContent.appendChild(table);
  modal.style.display = "block";
}

function openModal() {
  modal.style.display = "block";
}
function closeModal() {
  modal.style.display = "none";
}

// ---- Main Flow ---- //
function init() {
  // Try browser geolocation first
  if (navigator.geolocation) {
    navigator.geolocation.getCurrentPosition(pos => {
      userLatLng = { lat: pos.coords.latitude, lon: pos.coords.longitude };
      initMap(userLatLng.lat, userLatLng.lon);
      loadMosques();
    }, err => {
      // fallback to manual address
      promptAddress();
    });
  } else {
    promptAddress();
  }
}

function promptAddress() {
  const address = prompt("Manzilingizni kiriting (masalan, Toshkent, Uzbekistan):");
  if (!address) {
    alert("Manzil kiritilmagan, iltimos sahifani qayta yuklang.");
    return;
  }
  showLoading("Geocoding address…");
  geocodeAddress(address).then(res => {
    if (!res.length) throw new Error("Location not found");
    const loc = res[0];
    userLatLng = { lat: parseFloat(loc.lat), lon: parseFloat(loc.lon) };
    initMap(userLatLng.lat, userLatLng.lon);
    hideLoading();
    loadMosques();
  }).catch(e => {
    hideLoading();
    alert("Geocoding xatosi: " + e.message);
  });
}

function loadMosques() {
  showLoading("Yaqin masjidlarni qidirish…");
  getNearbyMosques(userLatLng.lat, userLatLng.lon)
    .then(data => {
      hideLoading();
      addMosqueMarkers(data);
    })
    .catch(e => {
      hideLoading();
      alert("Masjidlarni olishda xato: " + e.message);
    });
}

// Button handlers
prayerBtn.addEventListener("click", () => {
  if (!userLatLng) { alert("Joylashuv aniqlanmagan!"); return; }
  showLoading("Namoz vaqtlarini yuklash…");
  fetchPrayerTimes(userLatLng.lat, userLatLng.lon)
    .then(data => {
      hideLoading();
      renderPrayerTimes(data);
    })
    .catch(e => {
      hideLoading();
      alert("Namoz vaqtlarini olishda xato: " + e.message);
    });
});

closeBtn.addEventListener("click", closeModal);
window.addEventListener("click", e => {
  if (e.target === modal) closeModal();
});

// Initialize on DOM ready
document.addEventListener("DOMContentLoaded", init);
