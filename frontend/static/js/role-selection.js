// Enhanced Role Selection with Advanced Animations
function selectRole(role) {
    const card = event.currentTarget;
    const ripple = card.querySelector('.btn-ripple');

    // Create click ripple effect
    createRippleEffect(card, event);

    // Add selection animation
    card.style.transform = 'scale(0.95)';
    card.style.filter = 'brightness(1.2)';

    // Play selection sound (if audio is enabled)
    playSelectionSound();

    setTimeout(() => {
        card.style.transform = 'translateY(-10px) scale(1.02)';
        card.style.filter = 'brightness(1)';

        // Show loading state
        showLoadingState(card);

        setTimeout(() => {
            // Redirect to login page with role parameter
            if (role === 'fraud-analyst') {
                window.location.href = '/login/?role=fraud-analyst';
            } else if (role === 'auditor') {
                window.location.href = '/login/?role=auditor';
            }
        }, 1000);
    }, 150);
}

function createRippleEffect(element, event) {
    const ripple = document.createElement('div');
    const rect = element.getBoundingClientRect();
    const size = Math.max(rect.width, rect.height);
    const x = event.clientX - rect.left - size / 2;
    const y = event.clientY - rect.top - size / 2;

    ripple.style.cssText = `
        position: absolute;
        width: ${size}px;
        height: ${size}px;
        left: ${x}px;
        top: ${y}px;
        background: radial-gradient(circle, rgba(255,255,255,0.3) 0%, transparent 70%);
        border-radius: 50%;
        transform: scale(0);
        animation: ripple-animation 0.6s ease-out;
        pointer-events: none;
        z-index: 1000;
    `;

    element.appendChild(ripple);

    setTimeout(() => {
        ripple.remove();
    }, 600);
}

function showLoadingState(card) {
    const button = card.querySelector('.role-button');
    const originalText = button.innerHTML;

    button.innerHTML = `
        <span class="btn-content">
            <span class="loading-spinner"></span>
            <span class="btn-text">Connecting...</span>
        </span>
    `;

    // Add loading spinner styles
    const style = document.createElement('style');
    style.textContent = `
        .loading-spinner {
            width: 16px;
            height: 16px;
            border: 2px solid rgba(255,255,255,0.3);
            border-top: 2px solid white;
            border-radius: 50%;
            animation: spin 1s linear infinite;
        }
        @keyframes spin {
            0% { transform: rotate(0deg); }
            100% { transform: rotate(360deg); }
        }
    `;
    document.head.appendChild(style);
}

function playSelectionSound() {
    // Create a subtle audio feedback (optional)
    const audioContext = new (window.AudioContext || window.webkitAudioContext)();
    const oscillator = audioContext.createOscillator();
    const gainNode = audioContext.createGain();

    oscillator.connect(gainNode);
    gainNode.connect(audioContext.destination);

    oscillator.frequency.setValueAtTime(800, audioContext.currentTime);
    oscillator.frequency.exponentialRampToValueAtTime(400, audioContext.currentTime + 0.1);

    gainNode.gain.setValueAtTime(0.1, audioContext.currentTime);
    gainNode.gain.exponentialRampToValueAtTime(0.01, audioContext.currentTime + 0.1);

    oscillator.start(audioContext.currentTime);
    oscillator.stop(audioContext.currentTime + 0.1);
}

// Enhanced hover effects and interactions
document.addEventListener('DOMContentLoaded', function () {
    const roleCards = document.querySelectorAll('.role-card');
    const particles = document.querySelectorAll('.particle');

    // Enhanced card interactions
    roleCards.forEach((card, index) => {
        // Mouse move parallax effect
        card.addEventListener('mousemove', function (e) {
            const rect = card.getBoundingClientRect();
            const x = e.clientX - rect.left;
            const y = e.clientY - rect.top;

            const centerX = rect.width / 2;
            const centerY = rect.height / 2;

            const rotateX = (y - centerY) / 10;
            const rotateY = (centerX - x) / 10;

            card.style.transform = `
                translateY(-10px) 
                scale(1.02) 
                rotateX(${rotateX}deg) 
                rotateY(${rotateY}deg)
                perspective(1000px)
            `;
        });

        card.addEventListener('mouseleave', function () {
            card.style.transform = 'translateY(0) scale(1) rotateX(0) rotateY(0)';
        });

        // Add floating animation with delay
        card.style.animationDelay = `${index * 0.5}s`;
    });

    // Particle interaction with mouse
    document.addEventListener('mousemove', function (e) {
        const mouseX = e.clientX / window.innerWidth;
        const mouseY = e.clientY / window.innerHeight;

        particles.forEach((particle, index) => {
            const speed = (index + 1) * 0.5;
            const x = mouseX * speed;
            const y = mouseY * speed;

            particle.style.transform = `translate(${x}px, ${y}px)`;
        });
    });

    // Add scroll-triggered animations
    const observerOptions = {
        threshold: 0.1,
        rootMargin: '0px 0px -50px 0px'
    };

    const observer = new IntersectionObserver(function (entries) {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                entry.target.style.opacity = '1';
                entry.target.style.transform = 'translateY(0)';
            }
        });
    }, observerOptions);

    // Observe elements for scroll animations
    roleCards.forEach(card => {
        card.style.opacity = '0';
        card.style.transform = 'translateY(50px)';
        card.style.transition = 'opacity 0.6s ease, transform 0.6s ease';
        observer.observe(card);
    });

    // Add keyboard navigation
    document.addEventListener('keydown', function (e) {
        if (e.key === '1') {
            selectRole('fraud-analyst');
        } else if (e.key === '2') {
            selectRole('auditor');
        }
    });

    // Add dynamic particle colors based on scroll
    window.addEventListener('scroll', function () {
        const scrollPercent = window.scrollY / (document.body.scrollHeight - window.innerHeight);
        const hue = scrollPercent * 360;

        particles.forEach(particle => {
            particle.style.background = `hsl(${hue}, 70%, 60%)`;
        });
    });
});

// Add CSS animation keyframes dynamically
const style = document.createElement('style');
style.textContent = `
    @keyframes ripple-animation {
        to {
            transform: scale(2);
            opacity: 0;
        }
    }
    
    @keyframes card-entrance {
        from {
            opacity: 0;
            transform: translateY(100px) scale(0.8);
        }
        to {
            opacity: 1;
            transform: translateY(0) scale(1);
        }
    }
`;
document.head.appendChild(style);