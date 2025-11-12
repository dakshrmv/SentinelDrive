/* ====== PARTICLE SYSTEM ====== */
class ParticleSystem {
    constructor() {
        this.particles = [];
        this.particleCount = 50;
        this.init();
        window.addEventListener('mousemove', (e) => this.addParticle(e));
    }

    init() {
        // Create initial particles
        for (let i = 0; i < this.particleCount; i++) {
            this.createParticle(
                Math.random() * window.innerWidth,
                Math.random() * window.innerHeight
            );
        }
        this.animate();
    }

    createParticle(x, y) {
        const particle = document.createElement('div');
        particle.className = 'particle';
        
        const size = Math.random() * 3 + 1;
        const colors = ['#ff4466', '#ff6b9d', '#ff3333'];
        const color = colors[Math.floor(Math.random() * colors.length)];
        
        particle.style.cssText = `
            width: ${size}px;
            height: ${size}px;
            left: ${x}px;
            top: ${y}px;
            background: ${color};
            border-radius: 50%;
            box-shadow: 0 0 ${size * 2}px ${color};
            opacity: 0.8;
        `;
        
        document.body.appendChild(particle);
        
        const particleObj = {
            element: particle,
            x: x,
            y: y,
            vx: (Math.random() - 0.5) * 2,
            vy: (Math.random() - 0.5) * 2 - 0.5,
            life: 100,
            maxLife: 100,
            size: size
        };
        
        this.particles.push(particleObj);
    }

    addParticle(e) {
        if (Math.random() > 0.8) {
            this.createParticle(e.clientX, e.clientY);
        }
    }

    animate() {
        this.particles = this.particles.filter(p => p.life > 0);
        
        this.particles.forEach(p => {
            p.x += p.vx;
            p.y += p.vy;
            p.vy += 0.1; // gravity
            p.life -= 1;
            
            p.element.style.left = p.x + 'px';
            p.element.style.top = p.y + 'px';
            p.element.style.opacity = p.life / p.maxLife * 0.8;
            
            if (p.life <= 0) {
                p.element.remove();
            }
        });
        
        requestAnimationFrame(() => this.animate());
    }
}

// Initialize particle system
new ParticleSystem();

/* ====== SCREEN SHAKE ON ALERT ====== */
function triggerScreenShake() {
    document.body.classList.add('alert-shake');
    setTimeout(() => {
        document.body.classList.remove('alert-shake');
    }, 600);
}

/* ====== PAGE TRANSITION EFFECT ====== */
function addPageTransition() {
    const links = document.querySelectorAll('a[href^="/"]');
    links.forEach(link => {
        link.addEventListener('click', (e) => {
            if (!link.target) {
                e.preventDefault();
                const main = document.querySelector('main');
                main.style.animation = 'none';
                setTimeout(() => {
                    main.style.animation = 'pageTransitionIn 0.8s ease-out';
                    window.location.href = link.href;
                }, 100);
            }
        });
    });
}

// Initialize page transitions
addPageTransition();

/* ====== METRIC COUNTER ANIMATION ====== */
class CounterAnimation {
    constructor(element, target, duration = 2000) {
        this.element = element;
        this.target = target;
        this.duration = duration;
        this.current = 0;
        this.animate();
    }

    animate() {
        const step = this.target / (this.duration / 16);
        const counter = setInterval(() => {
            this.current += step;
            if (this.current >= this.target) {
                this.current = this.target;
                clearInterval(counter);
            }
            this.element.textContent = this.current.toFixed(2);
        }, 16);
    }
}

/* ====== GLITCH TEXT INITIALIZATION ====== */
function initGlitchText() {
    const glitchElements = document.querySelectorAll('.glitch');
    glitchElements.forEach(el => {
        el.setAttribute('data-text', el.textContent);
    });
}

// Initialize glitch text on page load
document.addEventListener('DOMContentLoaded', initGlitchText);

/* ====== EXPORT FUNCTIONS FOR DETECTION PAGE ====== */
window.AdvancedEffects = {
    shake: triggerScreenShake,
    updateMetric: (element, value) => {
        element.textContent = value.toFixed(2);
    }
};
