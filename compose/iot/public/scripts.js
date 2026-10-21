// HVAC Control Panel – TechCorp BMS
// Arc geometry: path from (20,105) to (180,105), radius 90
// Total arc length ≈ 283px (π * 90)
const ARC_LENGTH = 283;

let currentTemperature = null;

/* ── Clock ────────────────────────────────────────────────────────────── */
function updateClock() {
  const now = new Date();
  const pad = n => String(n).padStart(2, '0');
  document.getElementById('clock').textContent =
    `${pad(now.getHours())}:${pad(now.getMinutes())}:${pad(now.getSeconds())}`;
}
setInterval(updateClock, 1000);
updateClock();

/* ── Gauge needle + arc ───────────────────────────────────────────────── */
function getStrokeColor(temp) {
  if (temp <= 18) return '#0077b6';   // cold – blue
  if (temp <= 26) return '#00b4d8';   // normal – cyan
  if (temp <= 32) return '#f4a261';   // warm – amber
  return '#e63946';                    // hot – red
}

function updateGauge(temp) {
  const clampedTemp = Math.max(0, Math.min(50, temp));
  const pct = clampedTemp / 50;

  // Arc fill (stroke-dashoffset: 283 = empty, 0 = full)
  const arcFill = document.getElementById('arc-fill');
  arcFill.style.strokeDashoffset = ARC_LENGTH * (1 - pct);
  arcFill.style.stroke = getStrokeColor(clampedTemp);

  // Needle rotates from -90° (0°C) to +90° (50°C)
  const angle = -90 + pct * 180;
  document.getElementById('needle').style.transform = `rotate(${angle}deg)`;

  // Digital readout
  const dispEl = document.getElementById('current-temperature');
  dispEl.textContent = temp;
  dispEl.style.color = getStrokeColor(clampedTemp);
}

/* ── API calls ────────────────────────────────────────────────────────── */
function fetchTemperature() {
  fetch('/temperature')
    .then(r => r.json())
    .then(data => {
      currentTemperature = data.temperature;
      updateGauge(currentTemperature);
      document.getElementById('setpoint-display').textContent = `${currentTemperature}°C`;
    })
    .catch(err => console.error('Fetch error:', err));
}

function setTemperature(newTemp) {
  fetch('/set', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ value: String(newTemp) }),
  })
    .then(() => {
      currentTemperature = newTemp;
      updateGauge(newTemp);
      document.getElementById('setpoint-display').textContent = `${newTemp}°C`;
    })
    .catch(err => console.error('Set error:', err));
}

/* ── Event listeners ──────────────────────────────────────────────────── */
document.addEventListener('DOMContentLoaded', () => {
  fetchTemperature();
  setInterval(fetchTemperature, 5000);

  document.getElementById('increase').addEventListener('click', () => {
    if (currentTemperature !== null && currentTemperature < 50) {
      setTemperature(currentTemperature + 1);
    }
  });

  document.getElementById('decrease').addEventListener('click', () => {
    if (currentTemperature !== null && currentTemperature > 0) {
      setTemperature(currentTemperature - 1);
    }
  });

  // Mode buttons toggle
  document.querySelectorAll('.mode-btn').forEach(btn => {
    btn.addEventListener('click', () => {
      document.querySelectorAll('.mode-btn').forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
    });
  });
});
