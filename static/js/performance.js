/* ====== PERFORMANCE OPTIMIZATIONS ====== */

// Lazy load animations
const observerOptions = {
    threshold: 0.1,
    rootMargin: '50px'
};

const observer = new IntersectionObserver((entries) => {
    entries.forEach(entry => {
        if (entry.isIntersecting) {
            entry.target.classList.add('animate');
            observer.unobserve(entry.target);
        }
    });
}, observerOptions);

document.addEventListener('DOMContentLoaded', () => {
    document.querySelectorAll('.fade-in, .glass-card, .metric-card, .screenshot-card').forEach(el => {
        observer.observe(el);
    });
});

// FPS Monitor
let frameCount = 0;
let lastTime = Date.now();

function updateFPS() {
    frameCount++;
    const now = Date.now();
    if (now - lastTime >= 1000) {
        const fpsEl = document.getElementById('fpsCounter');
        if (fpsEl) fpsEl.textContent = frameCount;
        frameCount = 0;
        lastTime = now;
    }
    requestAnimationFrame(updateFPS);
}

requestAnimationFrame(updateFPS);

// Memory Monitor
if (performance.memory) {
    setInterval(() => {
        const used = (performance.memory.usedJSHeapSize / 1048576).toFixed(1);
        const memEl = document.getElementById('memoryCounter');
        if (memEl) memEl.textContent = used + 'MB';
    }, 1000);
}

// Latency Monitor
function checkLatency() {
    const start = performance.now();
    fetch('/api/metrics').then(() => {
        const end = performance.now();
        const latency = (end - start).toFixed(0);
        const latEl = document.getElementById('latencyCounter');
        if (latEl) latEl.textContent = latency + 'ms';
    }).catch(() => {});
}

setInterval(checkLatency, 2000);

// Theme Toggle
document.getElementById('themeToggle')?.addEventListener('click', () => {
    document.body.classList.toggle('dark-mode');
    localStorage.setItem('theme', document.body.classList.contains('dark-mode') ? 'dark' : 'light');
});

// Load saved theme
if (localStorage.getItem('theme') === 'dark') {
    document.body.classList.add('dark-mode');
    const btn = document.getElementById('themeToggle');
    if (btn) btn.textContent = '☀️';
}

// Debounce helper
function debounce(func, wait) {
    let timeout;
    return function executedFunction(...args) {
        const later = () => {
            clearTimeout(timeout);
            func(...args);
        };
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
    };
}
