let currentTemperature = null;

function getTemperature() {
  fetch('/temperature')
    .then(res => res.json())
    .then(data => {
      currentTemperature = data.temperature;
      updateGauge(currentTemperature);
    });
}

function setTemperature(newTemp) {
  fetch('/set', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ value: String(newTemp) })
  })
  .then(() => {
    currentTemperature = newTemp;
    updateGauge(newTemp);
  })
  .catch(error => console.error('Error:', error));
}


function updateGauge(temp) {
  const clampedTemp = Math.max(0, Math.min(50, temp)); 
  const percentage = clampedTemp / 50;
  const dashOffset = 126 * (1 - percentage);
  
  document.getElementById('gauge-fill').style.strokeDashoffset = dashOffset;
  document.getElementById('current-temperature').textContent = temp;
}

document.addEventListener('DOMContentLoaded', () => {
  const increaseBtn = document.getElementById('increase');
  const decreaseBtn = document.getElementById('decrease');

  getTemperature();

  increaseBtn.addEventListener('click', () => {
    if (currentTemperature !== null && currentTemperature < 50) {
      const newTemp = currentTemperature + 1;
      setTemperature(newTemp);
    }
  });

  decreaseBtn.addEventListener('click', () => {
    if (currentTemperature !== null && currentTemperature > 0) {
      const newTemp = currentTemperature - 1;
      setTemperature(newTemp);
    }
  });
});
