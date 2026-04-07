// admin_settings.js - Settings Navigation, 2FA, Trusted Devices, Audit Logs

// ==================== SETTINGS NAVIGATION ====================
document.addEventListener('DOMContentLoaded', function() {
    initializeSettingsNav();
    initialize2FA();
    initializeAuditLogs();
    
    if (window.location.hash === '#logs') {
        setTimeout(() => {
            const logsNav = document.querySelector('[data-section="logs"]');
            if (logsNav) logsNav.click();
        }, 100);
    }
    
    const searchInput = document.getElementById('searchInput');
    if (searchInput) {
        searchInput.addEventListener('keypress', function(e) {
            if (e.key === 'Enter') {
                e.preventDefault();
                loadAuditLogs(1);
            }
        });
    }
});

// ==================== SETTINGS NAVIGATION ====================
function initializeSettingsNav() {
    const navItems = document.querySelectorAll('.settings-nav-item');
    
    navItems.forEach(item => {
        item.addEventListener('click', function(e) {
            e.preventDefault();
            
            document.querySelectorAll('.settings-nav-item').forEach(nav => nav.classList.remove('active'));
            document.querySelectorAll('.settings-section').forEach(section => section.classList.remove('active'));
            
            this.classList.add('active');
            
            const sectionId = this.getAttribute('data-section');
            const targetSection = document.getElementById(sectionId);
            if (targetSection) {
                targetSection.classList.add('active');
            }
            
            localStorage.setItem('lastSettingsSection', sectionId);
            history.pushState(null, null, '#' + sectionId);
        });
    });
    
    const lastSection = localStorage.getItem('lastSettingsSection');
    if (lastSection) {
        const targetNav = document.querySelector(`[data-section="${lastSection}"]`);
        if (targetNav) {
            targetNav.click();
        }
    }
}

// ==================== 2FA FUNCTIONS ====================
function initialize2FA() {
    const setupCard = document.getElementById('twofaSetupCard');
    if (setupCard) {}
}

function show2FASetup() {
    const setupCard = document.getElementById('twofaSetupCard');
    const loadingState = document.getElementById('loadingState');
    const setupFormContainer = document.getElementById('setupFormContainer');
    
    if (setupCard) {
        setupCard.style.display = 'block';
        if (loadingState) loadingState.style.display = 'block';
        if (setupFormContainer) setupFormContainer.innerHTML = '';
        
        setupCard.scrollIntoView({ behavior: 'smooth' });
        
        fetch('/ctumoalboal-comelec/2fa/setup-data', {
            method: 'GET',
            headers: { 'X-Requested-With': 'XMLHttpRequest' }
        })
        .then(response => response.json())
        .then(data => {
            if (loadingState) loadingState.style.display = 'none';
            if (data.success) {
                const setupHTML = generateQRCodeHTML(data);
                if (setupFormContainer) setupFormContainer.innerHTML = setupHTML;
                if (window.themeManager) window.themeManager.refresh();
            } else {
                if (setupFormContainer) {
                    setupFormContainer.innerHTML = `<p class="error-msg">Error: ${data.message || 'Failed to load 2FA setup'}</p>`;
                }
            }
        })
        .catch(error => {
            console.error('Error:', error);
            if (loadingState) loadingState.style.display = 'none';
            if (setupFormContainer) {
                setupFormContainer.innerHTML = '<p class="error-msg">Error loading 2FA setup. Please try again.</p>';
            }
        });
    }
}

function generateQRCodeHTML(data) {
    const totpUri = data.totp_uri;
    const qrUrl = `https://api.qrserver.com/v1/create-qr-code/?size=250x250&data=${encodeURIComponent(totpUri)}`;
    
    return `
        <div class="qr-code-container">
            <h3>Setup Two-Factor Authentication</h3>
            <p style="color: var(--text-secondary); margin-bottom: 20px;">
                Scan this QR code with your Google Authenticator app or any TOTP authenticator app.
            </p>
            <img src="${qrUrl}" alt="2FA QR Code" style="max-width: 250px; border: 2px solid var(--border-color); border-radius: 12px; padding: 10px; background: white; box-shadow: 0 4px 12px rgba(0,0,0,0.1); margin: 20px auto;">
            <div class="qr-note" style="background: rgba(16, 185, 129, 0.1); border-left: 4px solid #10b981; padding: 15px; border-radius: 6px; margin-top: 20px; font-size: 0.9rem;">
                <i class="fa-solid fa-circle-info"></i>
                <strong>After scanning:</strong> The 2FA will be automatically enabled.
            </div>
        </div>
    `;
}

function disable2FA() {
    if (confirm('Are you sure you want to disable Two-Factor Authentication? A confirmation email will be sent to your email address.')) {
        const button = event.target.closest('button');
        const originalText = button.innerHTML;
        button.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Sending email...';
        button.disabled = true;
        
        fetch('/ctumoalboal-comelec/2fa/disable', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' }
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                showNotification(data.message || 'Confirmation email sent! Please check your email.', 'success');
                button.innerHTML = '<i class="fa-solid fa-envelope"></i> Email Sent';
                setTimeout(() => {
                    button.innerHTML = originalText;
                    button.disabled = false;
                }, 30000);
            } else {
                showNotification('Error: ' + data.message, 'error');
                button.innerHTML = originalText;
                button.disabled = false;
            }
        })
        .catch(error => {
            console.error('Error:', error);
            showNotification('Error sending confirmation email. Please try again.', 'error');
            button.innerHTML = originalText;
            button.disabled = false;
        });
    }
}

function generateNewBackupCodes() {
    if (confirm('Generating new backup codes will invalidate your old ones. Continue?')) {
        fetch('/ctumoalboal-comelec/2fa/backup-codes', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' }
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                showNotification('New backup codes generated!', 'success');
                setTimeout(() => location.reload(), 1500);
            } else {
                showNotification('Error generating backup codes: ' + data.message, 'error');
            }
        })
        .catch(error => {
            console.error('Error:', error);
            showNotification('Error generating backup codes. Please try again.', 'error');
        });
    }
}

// ==================== TRUSTED DEVICES FUNCTIONS ====================
function trustCurrentDevice() {
    const button = event.target.closest('button');
    const originalText = button.innerHTML;
    button.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Processing...';
    button.disabled = true;
    
    fetch('/ctumoalboal-comelec/trusted-devices/add', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' }
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            showNotification('Device added to trusted devices successfully!', 'success');
            setTimeout(() => location.reload(), 1500);
        } else {
            showNotification('Error: ' + data.message, 'error');
            button.innerHTML = originalText;
            button.disabled = false;
        }
    })
    .catch(error => {
        console.error('Error:', error);
        showNotification('Error adding device. Please try again.', 'error');
        button.innerHTML = originalText;
        button.disabled = false;
    });
}

function revokeTrustedDevice(deviceId, event) {
    const button = event ? event.target.closest('button') : document.querySelector(`button[onclick*="${deviceId}"]`);
    
    if (!button) {
        showNotification('Error: Could not find the device button', 'error');
        return;
    }
    
    if (!confirm('Are you sure you want to remove this trusted device? A confirmation email will be sent to your email address.')) {
        return;
    }
    
    const originalText = button.innerHTML;
    button.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Sending...';
    button.disabled = true;
    
    fetch(`/ctumoalboal-comelec/trusted-devices/remove/${deviceId}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'X-Requested-With': 'XMLHttpRequest' },
        body: JSON.stringify({})
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            showNotification(data.message || 'Device removal email sent successfully! Please check your email.', 'success');
            button.innerHTML = '<i class="fa-solid fa-clock"></i> Pending Confirmation';
            button.style.background = '#f59e0b';
            button.disabled = true;
        } else {
            showNotification(data.message || 'Failed to remove device', 'error');
            button.innerHTML = originalText;
            button.disabled = false;
        }
    })
    .catch(error => {
        console.error('Fetch error:', error);
        showNotification('Network error occurred. Please try again.', 'error');
        button.innerHTML = originalText;
        button.disabled = false;
    });
}

// ==================== AUDIT LOG FUNCTIONS ====================
let currentPage = 1;
let currentSearch = '';
let currentStartDate = '';
let currentEndDate = '';

function initializeAuditLogs() {
    currentSearch = document.getElementById('searchInput')?.value || '';
    currentStartDate = document.getElementById('startDateInput')?.value || '';
    currentEndDate = document.getElementById('endDateInput')?.value || '';
    
    const urlParams = new URLSearchParams(window.location.search);
    currentPage = parseInt(urlParams.get('page')) || 1;
}

function loadAuditLogs(page = 1) {
    const search = document.getElementById('searchInput').value;
    const startDate = document.getElementById('startDateInput').value;
    const endDate = document.getElementById('endDateInput').value;
    
    currentSearch = search;
    currentStartDate = startDate;
    currentEndDate = endDate;
    currentPage = page;
    
    const tableContainer = document.getElementById('auditTableContainer');
    tableContainer.innerHTML = `
        <div class="audit-card" style="text-align: center; padding: 40px;">
            <div class="loading-spinner"></div>
            <p style="color: var(--text-secondary); margin-top: 15px;">Loading audit logs...</p>
        </div>
    `;
    
    let url = `/ctumoalboal-comelec/audit-logs-ajax?page=${page}`;
    if (search) url += `&search=${encodeURIComponent(search)}`;
    if (startDate) url += `&start_date=${startDate}`;
    if (endDate) url += `&end_date=${endDate}`;
    
    fetch(url, { headers: { 'X-Requested-With': 'XMLHttpRequest' } })
    .then(response => response.text())
    .then(html => {
        tableContainer.innerHTML = html;
        if (window.themeManager) window.themeManager.refresh();
    })
    .catch(error => {
        console.error('Error:', error);
        tableContainer.innerHTML = `
            <div class="audit-card" style="text-align: center; padding: 40px;">
                <p class="error-msg">Error loading audit logs. Please try again.</p>
                <button class="audit-btn" onclick="loadAuditLogs(${currentPage})">Retry</button>
            </div>
        `;
    });
    
    return false;
}

function loadAuditPage(page) {
    return loadAuditLogs(page);
}

function clearAuditFilters() {
    document.getElementById('searchInput').value = '';
    document.getElementById('startDateInput').value = '';
    document.getElementById('endDateInput').value = '';
    loadAuditLogs(1);
}

// ==================== NOTIFICATION SYSTEM ====================
function showNotification(message, type = 'info') {
    let container = document.querySelector('.notification-container');
    if (!container) {
        container = document.createElement('div');
        container.className = 'notification-container';
        document.body.appendChild(container);
        
        const style = document.createElement('style');
        style.textContent = `
            .notification-container {
                position: fixed;
                top: 20px;
                right: 20px;
                z-index: 9999;
            }
            .notification {
                background: white;
                border-radius: 8px;
                padding: 15px 20px;
                margin-bottom: 10px;
                box-shadow: 0 4px 12px rgba(0,0,0,0.15);
                display: flex;
                align-items: center;
                gap: 10px;
                animation: slideIn 0.3s ease;
                border-left: 4px solid;
                min-width: 300px;
            }
            .notification.success { border-left-color: #10b981; }
            .notification.error { border-left-color: #ef4444; }
            .notification.info { border-left-color: #3b82f6; }
            .notification.warning { border-left-color: #f59e0b; }
            @keyframes slideIn {
                from { transform: translateX(100%); opacity: 0; }
                to { transform: translateX(0); opacity: 1; }
            }
            @keyframes slideOut {
                from { transform: translateX(0); opacity: 1; }
                to { transform: translateX(100%); opacity: 0; }
            }
            .dark-mode .notification { background: #1e293b; color: #f1f5f9; }
        `;
        document.head.appendChild(style);
    }
    
    const notification = document.createElement('div');
    notification.className = `notification ${type}`;
    
    let icon = 'fa-info-circle';
    if (type === 'success') icon = 'fa-check-circle';
    if (type === 'error') icon = 'fa-exclamation-circle';
    if (type === 'warning') icon = 'fa-exclamation-triangle';
    
    notification.innerHTML = `<i class="fa-solid ${icon}"></i><span>${message}</span>`;
    container.appendChild(notification);
    
    setTimeout(() => {
        notification.style.animation = 'slideOut 0.3s ease forwards';
        setTimeout(() => notification.remove(), 300);
    }, 5000);
}

// ==================== PROFILE FUNCTIONS ====================

// This is the main save function that gets called when user clicks Save
window.saveProfileChanges = function() {
    const usernameInput = document.getElementById('newUsername');
    const emailInput = document.getElementById('newEmail');
    
    if (!usernameInput || !emailInput) {
        showNotification('Form inputs not found', 'error');
        return;
    }
    
    const username = usernameInput.value.trim();
    const newEmail = emailInput.value.trim();
    
    if (!username || !newEmail) {
        showNotification('Username and email are required', 'error');
        return;
    }
    
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    if (!emailRegex.test(newEmail)) {
        showNotification('Please enter a valid email address', 'error');
        return;
    }
    
    const currentEmail = document.getElementById('currentEmail').textContent.trim();
    const isEmailChanged = (newEmail !== currentEmail);
    
    // If email changed, show modal first
    if (isEmailChanged) {
        window.pendingProfileData = {
            username: username,
            newEmail: newEmail
        };
        showEmailChangeModal(username, newEmail);
        return;
    }
    
    // If email not changed, proceed with normal update
    window.performProfileUpdate(username, newEmail, false);
};

// This is the function that actually calls the API to update the profile
window.performProfileUpdate = function(username, email, isEmailVerified = false) {
    console.log('=== performProfileUpdate called ===');
    console.log('Username:', username);
    console.log('Email:', email);
    console.log('isEmailVerified:', isEmailVerified);
    console.log('isEmailVerified type:', typeof isEmailVerified);
    
    const currentEmail = document.getElementById('currentEmail').textContent.trim();
    console.log('Current email from DOM:', currentEmail);
    
    const requestBody = {
        username: username,
        email: email
    };
    
    // Add verification flags ONLY if this is an email change that was verified
    if (email !== currentEmail && isEmailVerified === true) {
        requestBody.old_email_verified = 'true';
        requestBody.new_email_verified = 'true';
        console.log('✅ Adding verification flags to request');
    } else if (email !== currentEmail && !isEmailVerified) {
        console.log('⚠️ WARNING: Email changed but isEmailVerified is false!');
    } else {
        console.log('No email change detected');
    }
    
    console.log('Final request body:', requestBody);
    
    // Disable save button
    const saveBtn = document.querySelector('#profileActions .btn-primary');
    const cancelBtn = document.querySelector('#profileActions .btn-secondary');
    const originalText = saveBtn ? saveBtn.innerHTML : '';
    
    if (saveBtn) {
        saveBtn.disabled = true;
        saveBtn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Saving...';
    }
    if (cancelBtn) cancelBtn.disabled = true;
    
    fetch('/ctumoalboal-comelec/settings/profile/update', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(requestBody)
    })
    .then(response => response.json())
    .then(data => {
        console.log('Server response:', data);
        
        if (data.success) {
            showNotification('Profile updated successfully!', 'success');
            
            // Update the displayed values
            document.getElementById('currentUsername').textContent = username;
            document.getElementById('currentEmail').textContent = email;
            
            // Reset verification flags
            window.oldEmailVerified = null;
            window.newEmailVerified = null;
            window.pendingProfileData = null;
            
            // Close edit mode
            if (typeof window.cancelProfileEdit === 'function') {
                window.cancelProfileEdit();
            }
            
            // Reload page after 2 seconds to show fresh data
            setTimeout(() => {
                location.reload();
            }, 1500);
        } else {
            showNotification(data.message || 'Failed to update profile', 'error');
        }
    })
    .catch(error => {
        console.error('Fetch error:', error);
        showNotification('Network error. Please try again.', 'error');
    })
    .finally(() => {
        if (saveBtn) {
            saveBtn.disabled = false;
            saveBtn.innerHTML = originalText;
        }
        if (cancelBtn) cancelBtn.disabled = false;
    });
};

// ==================== UTILITY FUNCTIONS ====================
function applyAuditFilters() {
    const form = document.getElementById('auditFilterForm');
    if (!form) return false;
    const formData = new FormData(form);
    const params = new URLSearchParams(formData).toString();
    window.location.href = window.location.pathname + '?' + params + '#logs';
    return false;
}