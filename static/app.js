(function() {
  var chartOptions = {
    responsive: true,
    maintainAspectRatio: false,
    animation: { duration: 200 },
    plugins: {
      legend: { display: false },
      tooltip: {
        mode: 'index', intersect: false,
        backgroundColor: '#161b22',
        titleColor: '#c9d1d9',
        bodyColor: '#c9d1d9',
        borderColor: '#30363d',
        borderWidth: 1,
        callbacks: {
          title: function(items) {
            var s = items[0].raw.x;
            var h = Math.floor(s / 3600);
            var m = Math.floor((s % 3600) / 60);
            var sec = s % 60;
            return (h > 0 ? h + 'h ' : '') + String(m).padStart(2, '0') + 'm ' + String(sec).padStart(2, '0') + 's';
          }
        }
      }
    },
    scales: {
      x: {
        type: 'linear',
        title: { display: true, text: 'Elapsed', color: '#8b949e' },
        ticks: {
          color: '#8b949e',
          callback: function(v) {
            var m = Math.floor(v / 60);
            var s = v % 60;
            return String(m).padStart(2, '0') + ':' + String(s).padStart(2, '0');
          }
        },
        grid: { color: '#21262d' }
      },
      y: {
        title: { display: true, color: '#8b949e' },
        ticks: { color: '#8b949e' },
        grid: { color: '#21262d' },
        beginAtZero: true
      }
    },
    elements: {
      point: { radius: 0, hoverRadius: 4 },
      line: { borderWidth: 1.5, tension: 0.2 }
    }
  };

  function makeOptions(label) {
    var opts = JSON.parse(JSON.stringify(chartOptions));
    opts.scales.y.title.text = label;
    return opts;
  }

  var chartVolt = new Chart(document.getElementById('chart-voltage').getContext('2d'), {
    type: 'line',
    data: { datasets: [{ label: 'Voltage', borderColor: '#58a6ff', data: [] }] },
    options: makeOptions('Voltage (V)')
  });

  var chartCurr = new Chart(document.getElementById('chart-current').getContext('2d'), {
    type: 'line',
    data: { datasets: [{ label: 'Current', borderColor: '#3fb950', data: [] }] },
    options: makeOptions('Current (A)')
  });

  var chartPower = new Chart(document.getElementById('chart-power').getContext('2d'), {
    type: 'line',
    data: { datasets: [{ label: 'Power', borderColor: '#d29922', data: [] }] },
    options: makeOptions('Power (W)')
  });

  var chartEnergy = new Chart(document.getElementById('chart-energy').getContext('2d'), {
    type: 'line',
    data: { datasets: [
      { label: 'Energy', borderColor: '#f78166', data: [], yAxisID: 'y' },
      { label: 'Capacity', borderColor: '#bc8cff', data: [], yAxisID: 'y1', borderDash: [4, 2] }
    ]},
    options: (function() {
      var opts = JSON.parse(JSON.stringify(chartOptions));
      opts.scales.y = {
        type: 'linear', position: 'left',
        title: { display: true, text: 'Energy (Wh)', color: '#f78166' },
        ticks: { color: '#8b949e' },
        grid: { color: '#21262d' },
        beginAtZero: true
      };
      opts.scales.y1 = {
        type: 'linear', position: 'right',
        title: { display: true, text: 'Capacity (mAh)', color: '#bc8cff' },
        ticks: { color: '#8b949e' },
        grid: { drawOnChartArea: false },
        beginAtZero: true
      };
      return opts;
    })()
  });

  var startTime = null;

  function updateUI(latest) {
    document.getElementById('v-val').textContent = latest.voltage.toFixed(2);
    document.getElementById('a-val').textContent = latest.current.toFixed(2);
    document.getElementById('w-val').textContent = (latest.voltage * latest.current).toFixed(2);
    document.getElementById('wh-val').textContent = latest.Wh.toFixed(2);
    document.getElementById('mah-val').textContent = latest.mAh;
    document.getElementById('temp-val').textContent = latest.temperature;
  }

  function updateCharts(data) {
    if (!data.length) return;

    if (!startTime) {
      startTime = new Date(data[0].timestamp);
    }

    var voltData = [], currData = [], powerData = [], energyData = [], mahData = [];
    for (var i = 0; i < data.length; i++) {
      var d = data[i];
      var elapsed = (new Date(d.timestamp) - startTime) / 1000;
      voltData.push({ x: elapsed, y: d.voltage });
      currData.push({ x: elapsed, y: d.current });
      powerData.push({ x: elapsed, y: d.voltage * d.current });
      energyData.push({ x: elapsed, y: d.Wh });
      mahData.push({ x: elapsed, y: d.mAh });
    }

    chartVolt.data.datasets[0].data = voltData;
    chartCurr.data.datasets[0].data = currData;
    chartPower.data.datasets[0].data = powerData;
    chartEnergy.data.datasets[0].data = energyData;
    chartEnergy.data.datasets[1].data = mahData;

    chartVolt.update('none');
    chartCurr.update('none');
    chartPower.update('none');
    chartEnergy.update('none');

    updateUI(data[data.length - 1]);
  }

  function hidePlaceholders() {
    ['ph-volt', 'ph-curr', 'ph-power', 'ph-energ'].forEach(function(id) {
      var el = document.getElementById(id);
      if (el) el.style.display = 'none';
    });
  }

  function fetchData() {
    fetch('/api/data')
      .then(function(r) { return r.json(); })
      .then(function(resp) {
        if (resp.data && resp.data.length) {
          hidePlaceholders();
          updateCharts(resp.data);
        }
      })
      .catch(function(e) { console.error(e); });
  }

  fetchData();
  setInterval(fetchData, 1000);
})();
