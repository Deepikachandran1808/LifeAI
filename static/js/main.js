/* ========================================================
   LifeAI - Main Application JavaScript
   ======================================================== */

document.addEventListener('DOMContentLoaded', () => {
    // 1. Mobile Sidebar Toggle
    const sidebar = document.getElementById('sidebar');
    const sidebarOpenBtn = document.getElementById('sidebarOpenBtn');
    const sidebarCloseBtn = document.getElementById('sidebarCloseBtn');

    if (sidebarOpenBtn && sidebar) {
        sidebarOpenBtn.addEventListener('click', () => {
            sidebar.classList.add('open');
        });
    }

    if (sidebarCloseBtn && sidebar) {
        sidebarCloseBtn.addEventListener('click', () => {
            sidebar.classList.remove('open');
        });
    }

    // 2. Theme Toggle (Dark / Light)
    const themeToggleBtn = document.getElementById('themeToggleBtn');
    if (themeToggleBtn) {
        themeToggleBtn.addEventListener('click', () => {
            const html = document.documentElement;
            const currentTheme = html.getAttribute('data-theme') || 'dark';
            const newTheme = currentTheme === 'dark' ? 'light' : 'dark';
            html.setAttribute('data-theme', newTheme);
            localStorage.setItem('lifeai_theme', newTheme);
        });
    }

    // Check saved theme
    const savedTheme = localStorage.getItem('lifeai_theme');
    if (savedTheme) {
        document.documentElement.setAttribute('data-theme', savedTheme);
    }
});

// Modal Helpers
function openModal(modalId) {
    const modal = document.getElementById(modalId);
    if (modal) {
        modal.classList.add('active');
    }
}

function closeModal(modalId) {
    const modal = document.getElementById(modalId);
    if (modal) {
        modal.classList.remove('active');
    }
}

// Global Toast/Alert Helper
function showToast(message, type = 'success') {
    let container = document.querySelector('.alerts-container');
    if (!container) {
        container = document.createElement('div');
        container.className = 'alerts-container';
        document.body.prepend(container);
    }

    const alert = document.createElement('div');
    alert.className = `alert alert-${type}`;
    alert.innerHTML = `
        <span class="alert-icon">${type === 'success' ? '✓' : 'ℹ'}</span>
        <span class="alert-text">${message}</span>
        <button class="alert-close" onclick="this.parentElement.remove()">✕</button>
    `;
    container.appendChild(alert);

    setTimeout(() => {
        if (alert.parentElement) {
            alert.remove();
        }
    }, 4500);
}
