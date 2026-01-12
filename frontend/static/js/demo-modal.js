// Demo Modal Functions
function openDemoModal() {
    document.getElementById('demoModal').style.display = 'flex';
    document.body.style.overflow = 'hidden';
}

function closeDemoModal() {
    document.getElementById('demoModal').style.display = 'none';
    document.body.style.overflow = 'auto';
    document.getElementById('demoForm').reset();
    document.getElementById('demoForm').style.display = 'block';
    document.getElementById('successMessage').style.display = 'none';
}

// Video Modal Functions
function openVideoModal() {
    const modal = document.getElementById('videoModal');
    if (modal) {
        modal.style.display = 'flex';
        document.body.style.overflow = 'hidden';
    }
}

function closeVideoModal() {
    const modal = document.getElementById('videoModal');
    if (modal) {
        modal.style.display = 'none';
        document.body.style.overflow = 'auto';
        // Stop video by resetting iframe src
        const iframe = modal.querySelector('iframe');
        if (iframe) {
            const src = iframe.src;
            iframe.src = src;
        }
    }
}

// Close modal when clicking outside
window.onclick = function (event) {
    const demoModal = document.getElementById('demoModal');
    const videoModal = document.getElementById('videoModal');

    if (event.target == demoModal) {
        closeDemoModal();
    }
    if (event.target == videoModal) {
        closeVideoModal();
    }
}

// Form submission
document.addEventListener('DOMContentLoaded', () => {
    document.getElementById('demoForm').addEventListener('submit', function (e) {
        e.preventDefault();
        const btn = this.querySelector('button[type="submit"]');
        const btnText = btn.querySelector('.btn-text');
        const btnLoader = btn.querySelector('.btn-loader');

        // Show loader
        btnText.style.display = 'none';
        btnLoader.style.display = 'inline';
        btn.disabled = true;

        // Get form data
        const formData = new FormData(this);
        const data = Object.fromEntries(formData);

        console.log('Demo Request:', data);
        // TODO: Send to backend API
        // fetch('/api/demo-request', { method: 'POST', body: JSON.stringify(data) })

        // Simulate API call
        setTimeout(() => {
            document.getElementById('demoForm').style.display = 'none';
            document.getElementById('successMessage').style.display = 'block';

            // Auto close after 3 seconds
            setTimeout(() => {
                closeDemoModal();
            }, 3000);
        }, 1500);
    });
});
