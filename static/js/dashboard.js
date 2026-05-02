const chart = new Chart(document.getElementById('chart'), {
    type: 'scatter',
    data: {
        datasets: [
            {
                label: 'Voltage (V)',
                data: [],
                borderColor: '#3b82f6',
                backgroundColor: 'transparent',
                yAxisID: 'yL',
                pointRadius: 0,
                borderWidth: 2,
                showLine: true,
            },
            {
                label: 'Current (A)',
                data: [],
                borderColor: '#ef4444',
                backgroundColor: 'transparent',
                yAxisID: 'yL',
                pointRadius: 0,
                borderWidth: 2,
                showLine: true,
            },
            {
                label: 'Power (W)',
                data: [],
                borderColor: '#f59e0b',
                backgroundColor: 'transparent',
                yAxisID: 'yR',
                pointRadius: 0,
                borderWidth: 2,
                showLine: true,
            },
            {
                label: 'Energy (Wh)',
                data: [],
                borderColor: '#22c55e',
                backgroundColor: 'transparent',
                yAxisID: 'yL',
                pointRadius: 0,
                borderWidth: 2,
                showLine: true,
            },
        ],
    },
    options: {
        animation: false,
        responsive: true,
        interaction: { mode: 'index', intersect: false },
        plugins: {
            legend: {
                labels: { color: '#94a3b8', usePointStyle: true, pointStyleWidth: 12 },
            },
            tooltip: {
                backgroundColor: '#1e293b',
                titleColor: '#f8fafc',
                bodyColor: '#cbd5e1',
                borderColor: '#475569',
                borderWidth: 1,
            },
        },
        scales: {
            x: {
                type: 'linear',
                title: { display: true, text: 'time, minutes', color: '#94a3b8' },
                ticks: { color: '#64748b' },
                grid: { color: '#334155' },
            },
            yL: {
                type: 'linear',
                position: 'left',
                title: { display: true, text: 'voltage (V), current (A), energy (Wh)', color: '#94a3b8' },
                ticks: { color: '#64748b' },
                grid: { color: '#334155' },
                min: 0,
            },
            yR: {
                type: 'linear',
                position: 'right',
                title: { display: true, text: 'power (W)', color: '#94a3b8' },
                ticks: { color: '#64748b' },
                grid: { drawOnChartArea: false },
                min: 0,
            },
        },
    },
});

let lastIdx = parseInt(document.querySelector('meta[name="initial-idx"]').content, 10) || 0;

function fmtDur(s) {
    const h = Math.floor(s / 3600);
    const m = Math.floor((s % 3600) / 60);
    const sec = Math.floor(s % 60);
    return h > 0
        ? h + ':' + String(m).padStart(2, '0') + ':' + String(sec).padStart(2, '0')
        : String(m).padStart(2, '0') + ':' + String(sec).padStart(2, '0');
}

async function poll() {
    try {
        const res = await fetch('/api/data?from=' + lastIdx);
        if (!res.ok) throw new Error(res.status);
        const j = await res.json();
        if (j.readings.length > 0) {
            for (const r of j.readings) {
                const t = r.duration / 60;
                chart.data.datasets[0].data.push({ x: t, y: r.voltage });
                chart.data.datasets[1].data.push({ x: t, y: r.current });
                chart.data.datasets[2].data.push({ x: t, y: r.power });
                chart.data.datasets[3].data.push({ x: t, y: r.Wh });
            }
            lastIdx = j.total;
            chart.update('none');
            const r = j.readings.at(-1);
            document.getElementById('m-voltage').textContent  = r.voltage.toFixed(2);
            document.getElementById('m-current').textContent  = r.current.toFixed(2);
            document.getElementById('m-power').textContent    = r.power.toFixed(2);
            document.getElementById('m-wh').textContent       = r.Wh.toFixed(2);
            document.getElementById('m-mah').textContent      = r.mAh;
            document.getElementById('m-dplus').textContent    = r['D+'].toFixed(1);
            document.getElementById('m-dminus').textContent   = r['D-'].toFixed(1);
            document.getElementById('m-temp').textContent     = r.temperature;
            document.getElementById('m-duration').textContent = fmtDur(r.duration);
            document.getElementById('status').textContent     = j.total + ' readings';
        }
    } catch (e) {
        document.getElementById('status').textContent = 'Connection error, retrying…';
    }
    setTimeout(poll, 1000);
}

poll();
