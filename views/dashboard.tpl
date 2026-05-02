<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>J7-C USB Tester Dashboard</title>
<script src="https://cdn.jsdelivr.net/npm/chart.js@4/dist/chart.umd.min.js"></script>
<link rel="stylesheet" href="/static/style.css">
</head>
<body>
<h1>&#9889; J7-C USB Tester &mdash; Live Dashboard</h1>
<div class="stats">
  <div class="stat-card">
    <div class="stat-label">Voltage</div>
    <div class="stat-value"><span id="v-val">--</span> <span class="stat-unit">V</span></div>
  </div>
  <div class="stat-card">
    <div class="stat-label">Current</div>
    <div class="stat-value"><span id="a-val">--</span> <span class="stat-unit">A</span></div>
  </div>
  <div class="stat-card">
    <div class="stat-label">Power</div>
    <div class="stat-value"><span id="w-val">--</span> <span class="stat-unit">W</span></div>
  </div>
  <div class="stat-card">
    <div class="stat-label">Energy</div>
    <div class="stat-value"><span id="wh-val">--</span> <span class="stat-unit">Wh</span></div>
  </div>
  <div class="stat-card">
    <div class="stat-label">Capacity</div>
    <div class="stat-value"><span id="mah-val">--</span> <span class="stat-unit">mAh</span></div>
  </div>
  <div class="stat-card">
    <div class="stat-label">Temperature</div>
    <div class="stat-value"><span id="temp-val">--</span> <span class="stat-unit">&deg;C</span></div>
  </div>
</div>
<div class="charts">
  <div class="chart-box">
    <div class="placeholder" id="ph-volt">Waiting for data...</div>
    <canvas id="chart-voltage"></canvas>
  </div>
  <div class="chart-box">
    <div class="placeholder" id="ph-curr">Waiting for data...</div>
    <canvas id="chart-current"></canvas>
  </div>
  <div class="chart-box">
    <div class="placeholder" id="ph-power">Waiting for data...</div>
    <canvas id="chart-power"></canvas>
  </div>
  <div class="chart-box">
    <div class="placeholder" id="ph-energ">Waiting for data...</div>
    <canvas id="chart-energy"></canvas>
  </div>
</div>
<script src="/static/app.js"></script>
</body>
</html>
