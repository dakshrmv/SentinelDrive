// Utility JavaScript functions for the Drowsiness Detection Web UI

const DrowsyUtils = {
    // Format a UNIX timestamp to human-readable string
    formatDate: function(ts) {
        const d = new Date(ts * 1000);
        return d.toLocaleString();
    },

    // Update metric display zones (if used)
    updateMetrics: function({ status, ear, mar, gaze, fatigue }) {
        if (document.getElementById('metricStatus')) {
            document.getElementById('metricStatus').innerText = status || 'Idle';
        }
        if (document.getElementById('metricEAR')) {
            document.getElementById('metricEAR').innerText = ear ? ear.toFixed(2) : '--';
        }
        if (document.getElementById('metricMAR')) {
            document.getElementById('metricMAR').innerText = mar ? mar.toFixed(2) : '--';
        }
        if (document.getElementById('metricGaze')) {
            document.getElementById('metricGaze').innerText = gaze ? gaze.toFixed(2) : '--';
        }
        if (document.getElementById('metricFatigue')) {
            document.getElementById('metricFatigue').innerText = fatigue !== undefined ? `${fatigue}/10` : '0/10';
        }
    },

    // Show toast alert (Bootstrap 5 style)
    showToast: function(message, type = 'info') {
        // You can implement a toast here, or use alert for simplicity
        alert(message);
    }
};

// Usage example (in detection-ui.js or logs page):
// DrowsyUtils.updateMetrics({ status: 'Awake', ear: 0.31, fatigue: 2 });
