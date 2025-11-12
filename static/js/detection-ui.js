/* ====== DETECTION UI WITH PERFORMANCE OPTIMIZATIONS ====== */

let detectionActive = false;
let frameInterval = null;
let metricsInterval = null;
let sessionStart = null;
let alertCount = 0;

const detectionUI = {
    init: () => {
        document.getElementById('startBtn')?.addEventListener('click', detectionUI.startDetection);
        document.getElementById('stopBtn')?.addEventListener('click', detectionUI.stopDetection);
        document.getElementById('exportBtn')?.addEventListener('click', detectionUI.exportSession);
        Notification.requestPermission();
    },

    startDetection: async () => {
        try {
            const response = await fetch('/api/start-detection', { method: 'POST' });
            if (response.ok) {
                document.getElementById('startBtn').disabled = true;
                document.getElementById('stopBtn').disabled = false;
                document.getElementById('status').innerText = "⏳ Calibrating... (5 sec)";
                detectionActive = true;
                sessionStart = Date.now();
                
                setTimeout(() => {
                    document.getElementById('status').innerText = "✅ Live Detection Active";
                    detectionUI.updateFrame();
                    detectionUI.updateMetrics();
                }, 5000);
            }
        } catch (err) {
            document.getElementById('status').innerText = "❌ Error starting detection";
        }
    },

    stopDetection: async () => {
        try {
            const response = await fetch('/api/stop-detection', { method: 'POST' });
            if (response.ok) {
                document.getElementById('startBtn').disabled = false;
                document.getElementById('stopBtn').disabled = true;
                document.getElementById('status').innerText = "⏹ Detection Stopped";
                detectionActive = false;
                clearInterval(frameInterval);
                clearInterval(metricsInterval);
            }
        } catch (err) {}
    },

    updateFrame: () => {
        frameInterval = setInterval(async () => {
            if (!detectionActive) { clearInterval(frameInterval); return; }
            try {
                const response = await fetch('/api/frame-b64');
                const data = await response.json();
                if (data.frame) {
                    const canvas = document.getElementById('videoCanvas');
                    const ctx = canvas.getContext('2d');
                    const img = new Image();
                    img.onload = () => {
                        ctx.drawImage(img, 0, 0, canvas.width, canvas.height);
                    };
                    img.src = 'data:image/jpeg;base64,' + data.frame;
                }
            } catch (err) {}
        }, 150);
    },

    updateMetrics: () => {
        metricsInterval = setInterval(async () => {
            if (!detectionActive) { clearInterval(metricsInterval); return; }
            try {
                const response = await fetch('/api/metrics');
                const metrics = await response.json();
                detectionUI.updateDashboardMetrics(metrics);
                detectionUI.updateStatus(metrics);
            } catch (err) {}
        }, 350);
    },

    updateDashboardMetrics: (metrics) => {
        document.getElementById('metricEAR').textContent = metrics.ear ?? "--";
        document.getElementById('metricMAR').textContent = metrics.mar ?? "--";
        document.getElementById('metricGaze').textContent = metrics.gaze ?? "--";
        document.getElementById('metricFatigue').textContent = `${metrics.fatigue ?? 0}/10`;
    },

    updateStatus: (metrics) => {
        const statusElement = document.getElementById('metricStatus');
        if (!statusElement) return;
        
        let color = "#00ff88";
        let status = "AWAKE ✅";
        
        if (metrics.fatigue >= 8) {
            color = "#ff3333";
            status = "🚨 CRITICAL";
            if (alertCount < 1 || alertCount % 10 === 0) {
                detectionUI.sendNotification('🚨 CRITICAL ALERT', 'Driver is extremely drowsy!');
            }
            alertCount++;
        } else if (metrics.fatigue >= 5) {
            color = "#ffcc00";
            status = "⚠️ WARNING";
        } else if (metrics.ear < 0.2) {
            color = "#ff6b6b";
            status = "👀 Eyes Closed";
        } else if (metrics.mar > 0.2) {
            color = "#ff9999";
            status = "😴 Yawning";
        }
        
        statusElement.textContent = status;
        statusElement.style.color = color;
        document.getElementById('alertCount').textContent = alertCount;
    },

    sendNotification: (title, message) => {
        if ('Notification' in window && Notification.permission === 'granted') {
            new Notification(title, {
                body: message,
                icon: '🛡️',
                tag: 'sentineldrive-alert'
            });
        }
    },

    exportSession: () => {
        const sessionDuration = Math.floor((Date.now() - sessionStart) / 1000);
        const data = {
            timestamp: new Date().toISOString(),
            alertCount: alertCount,
            sessionDuration: `${Math.floor(sessionDuration / 60)}m ${sessionDuration % 60}s`,
            exportTime: new Date().toLocaleString()
        };
        
        const json = JSON.stringify(data, null, 2);
        const blob = new Blob([json], { type: 'application/json' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `session_${new Date().toISOString().slice(0, 10)}.json`;
        a.click();
        URL.revokeObjectURL(url);
    }
};

// Keyboard Shortcuts
document.addEventListener('keydown', (e) => {
    if (e.code === 'Space' && e.target === document.body) {
        e.preventDefault();
        document.getElementById('startBtn')?.click();
    }
    if (e.code === 'Escape') {
        document.getElementById('stopBtn')?.click();
    }
});

document.addEventListener('DOMContentLoaded', detectionUI.init);
