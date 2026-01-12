/**
 * Global Animation Utilities for All Pages
 * Handles scroll-triggered animations, staggered animations, and more
 */

// Intersection Observer for scroll animations
const animationObserver = new IntersectionObserver((entries) => {
    entries.forEach(entry => {
        if (entry.isIntersecting) {
            entry.target.classList.add('animated');
            // If element has data-delay attribute, apply it
            const delay = entry.target.dataset.delay || 0;
            if (delay > 0) {
                setTimeout(() => {
                    entry.target.classList.add('animated');
                }, delay);
            }
        }
    });
}, {
    threshold: 0.1,
    rootMargin: '0px 0px -50px 0px'
});

/**
 * Initialize scroll animations on elements with .animate-on-scroll class
 */
function initScrollAnimations() {
    document.querySelectorAll('.animate-on-scroll').forEach((el, index) => {
        // Add staggered delay
        const delay = index * 50; // 50ms between each element
        el.style.transitionDelay = `${delay}ms`;
        animationObserver.observe(el);
    });
}

/**
 * Initialize staggered animations (for lists, tables, etc.)
 */
function initStaggerAnimations() {
    document.querySelectorAll('.stagger-animation').forEach((el, index) => {
        const delay = index * 100; // 100ms between each element
        el.style.transitionDelay = `${delay}ms`;
        animationObserver.observe(el);
    });
}

/**
 * Animate table rows when they appear
 */
function animateTableRows() {
    const tableRows = document.querySelectorAll('.data-table tbody tr');
    tableRows.forEach((row, index) => {
        row.style.animationDelay = `${index * 50}ms`;
        row.classList.add('stagger-animation');
    });
    initStaggerAnimations();
}

/**
 * Animate number counters
 * @param {HTMLElement} element - Element containing the number
 * @param {number} target - Target number to count to
 * @param {number} duration - Duration in milliseconds
 * @param {string} prefix - Optional prefix (e.g., '$')
 * @param {string} suffix - Optional suffix (e.g., '%')
 */
function animateCounter(element, target, duration = 2000, prefix = '', suffix = '') {
    const start = 0;
    const startTime = performance.now();
    const isPercent = suffix === '%';
    const isDecimal = target.toString().includes('.');
    
    function update(currentTime) {
        const elapsed = currentTime - startTime;
        const progress = Math.min(elapsed / duration, 1);
        
        // Easing function (ease-out)
        const easeOut = 1 - Math.pow(1 - progress, 3);
        let current = start + (target - start) * easeOut;
        
        if (isPercent) {
            element.textContent = `${prefix}${current.toFixed(2)}${suffix}`;
        } else if (isDecimal) {
            element.textContent = `${prefix}${current.toFixed(1)}${suffix}`;
        } else {
            element.textContent = `${prefix}${Math.floor(current)}${suffix}`;
        }
        
        if (progress < 1) {
            requestAnimationFrame(update);
        } else {
            // Ensure final value is exact
            if (isPercent) {
                element.textContent = `${prefix}${target.toFixed(2)}${suffix}`;
            } else if (isDecimal) {
                element.textContent = `${prefix}${target}${suffix}`;
            } else {
                element.textContent = `${prefix}${target}${suffix}`;
            }
        }
    }
    
    requestAnimationFrame(update);
}

/**
 * Animate counter elements with data-target attribute
 */
function initCounters() {
    document.querySelectorAll('[data-counter]').forEach(el => {
        const target = parseFloat(el.dataset.counter);
        const prefix = el.dataset.prefix || '';
        const suffix = el.dataset.suffix || '';
        const duration = parseInt(el.dataset.duration) || 2000;
        
        // Only animate if element is in viewport
        const counterObserver = new IntersectionObserver((entries) => {
            entries.forEach(entry => {
                if (entry.isIntersecting) {
                    animateCounter(entry.target, target, duration, prefix, suffix);
                    counterObserver.unobserve(entry.target); // Only animate once
                }
            });
        }, { threshold: 0.5 });
        
        counterObserver.observe(el);
    });
}

/**
 * Add ripple effect to buttons
 */
function initRippleEffect() {
    document.querySelectorAll('.ripple-button, button, .btn-hero-primary, .btn-hero-secondary').forEach(button => {
        button.addEventListener('click', function(e) {
            const ripple = document.createElement('span');
            const rect = this.getBoundingClientRect();
            const size = Math.max(rect.width, rect.height);
            const x = e.clientX - rect.left - size / 2;
            const y = e.clientY - rect.top - size / 2;
            
            ripple.style.width = ripple.style.height = size + 'px';
            ripple.style.left = x + 'px';
            ripple.style.top = y + 'px';
            ripple.classList.add('ripple');
            
            // Add ripple styles
            ripple.style.position = 'absolute';
            ripple.style.borderRadius = '50%';
            ripple.style.background = 'rgba(255, 255, 255, 0.6)';
            ripple.style.transform = 'scale(0)';
            ripple.style.animation = 'ripple 0.6s ease-out';
            ripple.style.pointerEvents = 'none';
            
            this.style.position = 'relative';
            this.style.overflow = 'hidden';
            this.appendChild(ripple);
            
            setTimeout(() => {
                ripple.remove();
            }, 600);
        });
    });
}

/**
 * Animate elements when they enter viewport (for live feeds, new items, etc.)
 */
function animateNewElement(element) {
    element.style.opacity = '0';
    element.style.transform = 'translateY(20px)';
    element.style.transition = 'opacity 0.4s ease-out, transform 0.4s ease-out';
    
    // Trigger animation
    requestAnimationFrame(() => {
        element.style.opacity = '1';
        element.style.transform = 'translateY(0)';
    });
}

/**
 * Shake animation for error states
 */
function shakeElement(element) {
    element.style.animation = 'shake 0.5s ease-in-out';
    setTimeout(() => {
        element.style.animation = '';
    }, 500);
}

/**
 * Pulse animation for important elements
 */
function pulseElement(element) {
    element.style.animation = 'pulse 1s ease-in-out';
    setTimeout(() => {
        element.style.animation = '';
    }, 1000);
}

/**
 * Initialize all animations when DOM is loaded
 */
function initAllAnimations() {
    // Wait for DOM to be ready
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', () => {
            initScrollAnimations();
            initStaggerAnimations();
            initCounters();
            initRippleEffect();
            animateTableRows();
        });
    } else {
        initScrollAnimations();
        initStaggerAnimations();
        initCounters();
        initRippleEffect();
        animateTableRows();
    }
}

// Auto-initialize on load
initAllAnimations();

// Export functions for use in other scripts
if (typeof window !== 'undefined') {
    window.AnimationUtils = {
        animateCounter,
        animateNewElement,
        shakeElement,
        pulseElement,
        initScrollAnimations,
        initStaggerAnimations,
        initCounters,
        initRippleEffect
    };
}

