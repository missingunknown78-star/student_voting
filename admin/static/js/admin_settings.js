// admin_settings.js - All settings functionality moved here

// ==================== CSRF TOKEN HELPER ====================
function getCsrfToken() {
    const metaTag = document.querySelector('meta[name="csrf-token"]');
    return metaTag ? metaTag.getAttribute('content') : '';
}

// ==================== SETTINGS NAVIGATION ====================
document.addEventListener('DOMContentLoaded', function() {
    // Initialize settings navigation
    initializeSettingsNav();
    
    // Initialize 2FA if on that section
    initialize2FA();
    
    // Initialize audit logs variables
    initializeAuditLogs();
    
    // Check for URL hash
    if (window.location.hash === '#logs') {
        setTimeout(() => {
            const logsNav = document.querySelector('[data-section="logs"]');
            if (logsNav) logsNav.click();
        }, 100);
    }
    
    // Add enter key handler for search
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

function initializeSettingsNav() {
    const navItems = document.querySelectorAll('.settings-nav-item');
    
    navItems.forEach(item => {
        item.addEventListener('click', function(e) {
            e.preventDefault();
            
            // Remove active class from all nav items and sections
            document.querySelectorAll('.settings-nav-item').forEach(nav => nav.classList.remove('active'));
            document.querySelectorAll('.settings-section').forEach(section => section.classList.remove('active'));
            
            // Add active class to clicked nav item
            this.classList.add('active');
            
            // Show corresponding section
            const sectionId = this.getAttribute('data-section');
            const targetSection = document.getElementById(sectionId);
            if (targetSection) {
                targetSection.classList.add('active');
            }
            
            // Save to localStorage
            localStorage.setItem('lastSettingsSection', sectionId);
            
            // Update URL hash without scrolling
            history.pushState(null, null, '#' + sectionId);
        });
    });
    
    // Restore last section from localStorage
    const lastSection = localStorage.getItem('lastSettingsSection');
    if (lastSection) {
        const targetNav = document.querySelector(`[data-section="${lastSection}"]`);
        if (targetNav) {
            targetNav.click();
        }
    }
}

// ==================== GENERAL SETTINGS FUNCTIONS ====================
function saveSettings(section) {
    const settings = {};
    const sectionElement = document.getElementById(section);
    const inputs = sectionElement.querySelectorAll('input, select, textarea');
    
    inputs.forEach(input => {
        if (input.type === 'checkbox') {
            settings[input.id] = input.checked;
        } else if (input.type === 'radio') {
            if (input.checked) {
                settings[input.name] = input.value;
            }
        } else {
            settings[input.id] = input.value;
        }
    });
    
    console.log('Saving settings for', section, settings);
    
    // FIXED: Added /ctumoalboal-comelec prefix
    fetch('/ctumoalboal-comelec/settings/save', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': getCsrfToken()
        },
        body: JSON.stringify({
            section: section,
            settings: settings
        })
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            showNotification('Settings saved successfully!', 'success');
        } else {
            showNotification('Error saving settings: ' + data.message, 'error');
        }
    })
    .catch(error => {
        console.error('Error:', error);
        showNotification('Error saving settings. Please try again.', 'error');
    });
}

function resetSettings(section) {
    if (confirm('Reset all settings in this section to default values?')) {
        console.log('Resetting section:', section);
        showNotification('Settings reset to defaults', 'info');
    }
}

// ==================== 2FA FUNCTIONS - SIMPLIFIED ====================
function initialize2FA() {
    // Check if 2FA setup elements exist
    const setupCard = document.getElementById('twofaSetupCard');
    if (setupCard) {
        // Add any initialization needed
    }
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
        
        // FIXED: Added /ctumoalboal-comelec prefix
        fetch('/ctumoalboal-comelec/2fa/setup-data', {
            method: 'GET',
            headers: {
                'X-Requested-With': 'XMLHttpRequest'
            }
        })
        .then(response => response.json())
        .then(data => {
            if (loadingState) loadingState.style.display = 'none';
            
            if (data.success) {
                const setupHTML = generateQRCodeHTML(data);
                if (setupFormContainer) setupFormContainer.innerHTML = setupHTML;
                
                // Refresh theme manager for new content
                if (window.themeManager) {
                    window.themeManager.refresh();
                }
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
                <strong>After scanning:</strong> The 2FA will be automatically enabled. You'll be prompted to enter a code from your authenticator app every time you log in.
            </div>
        </div>
    `;
}

function disable2FA() {
    if (confirm('Are you sure you want to disable Two-Factor Authentication? This will make your account less secure.')) {
        // FIXED: Added /ctumoalboal-comelec prefix
        fetch('/ctumoalboal-comelec/2fa/disable', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCsrfToken()
            }
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                update2FAStatus(false);
                showNotification('2FA has been disabled.', 'success');
                setTimeout(() => location.reload(), 1500);
            } else {
                showNotification('Error disabling 2FA: ' + data.message, 'error');
            }
        })
        .catch(error => {
            console.error('Error:', error);
            showNotification('Error disabling 2FA. Please try again.', 'error');
        });
    }
}

function update2FAStatus(enabled) {
    const statusBadge = document.querySelector('#twofactor .badge');
    if (statusBadge) {
        if (enabled) {
            statusBadge.innerHTML = '<i class="fa-solid fa-circle-check"></i> Enabled';
            statusBadge.style.background = 'rgba(16, 185, 129, 0.15)';
            statusBadge.style.color = '#10b981';
            statusBadge.style.borderColor = '#10b981';
        } else {
            statusBadge.innerHTML = '<i class="fa-solid fa-circle-xmark"></i> Disabled';
            statusBadge.style.background = 'rgba(239, 68, 68, 0.15)';
            statusBadge.style.color = '#ef4444';
            statusBadge.style.borderColor = '#ef4444';
        }
    }
}

function generateNewBackupCodes() {
    if (confirm('Generating new backup codes will invalidate your old ones. Continue?')) {
        // FIXED: Added /ctumoalboal-comelec prefix
        fetch('/ctumoalboal-comelec/2fa/backup-codes', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCsrfToken()
            }
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
    
    // FIXED: Added /ctumoalboal-comelec prefix
    fetch('/ctumoalboal-comelec/trusted-devices/add', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': getCsrfToken()
        }
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
    console.log('Revoke function called for device:', deviceId);
    
    // Get the button that was clicked
    const button = event ? event.target.closest('button') : document.querySelector(`button[onclick*="${deviceId}"]`);
    
    if (!button) {
        console.error('Button not found');
        showNotification('Error: Could not find the device button', 'error');
        return;
    }
    
    if (!confirm('Are you sure you want to remove this trusted device? A confirmation email will be sent to your email address.')) {
        return;
    }
    
    // Show loading state
    const originalText = button.innerHTML;
    button.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Sending...';
    button.disabled = true;
    
    // FIXED: Added /ctumoalboal-comelec prefix
    fetch(`/ctumoalboal-comelec/trusted-devices/remove/${deviceId}`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-Requested-With': 'XMLHttpRequest',
            'X-CSRFToken': getCsrfToken()
        },
        body: JSON.stringify({})
    })
    .then(response => {
        console.log('Response status:', response.status);
        return response.json().then(data => {
            console.log('Response data:', data);
            return { status: response.status, data: data };
        });
    })
    .then(({ status, data }) => {
        if (data.success) {
            showNotification(data.message || 'Device removal email sent successfully! Please check your email.', 'success');
            
            button.innerHTML = '<i class="fa-solid fa-clock"></i> Pending Confirmation';
            button.style.background = '#f59e0b';
            button.style.borderColor = '#f59e0b';
            button.disabled = true;
            
            const deviceItem = button.closest('.device-item');
            if (deviceItem) {
                const pendingNote = document.createElement('div');
                pendingNote.className = 'pending-note';
                pendingNote.innerHTML = '<small style="color: #f59e0b; display: block; margin-top: 5px;"><i class="fa-solid fa-envelope"></i> Check email to confirm removal</small>';
                deviceItem.querySelector('.device-actions').appendChild(pendingNote);
            }
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

function simpleRevokeDevice(deviceId) {
    console.log('Simple revoke for device:', deviceId);
    
    if (!confirm('Remove this device?')) {
        return;
    }
    
    const button = document.querySelector(`.device-item[data-device-id="${deviceId}"] .btn-icon`);
    if (!button) return;
    
    const originalText = button.innerHTML;
    button.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i>';
    button.disabled = true;
    
    // FIXED: Added /ctumoalboal-comelec prefix
    fetch(`/ctumoalboal-comelec/trusted-devices/test-remove/${deviceId}`, {
        method: 'POST',
        headers: {
            'X-CSRFToken': getCsrfToken()
        }
    })
    .then(response => response.json())
    .then(data => {
        showNotification(data.message, data.success ? 'success' : 'error');
        if (data.success) {
            setTimeout(() => location.reload(), 1500);
        } else {
            button.innerHTML = originalText;
            button.disabled = false;
        }
    })
    .catch(error => {
        alert('Error: ' + error);
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
    
    // FIXED: Added /ctumoalboal-comelec prefix
    let url = `/ctumoalboal-comelec/audit-logs-ajax?page=${page}`;
    if (search) url += `&search=${encodeURIComponent(search)}`;
    if (startDate) url += `&start_date=${startDate}`;
    if (endDate) url += `&end_date=${endDate}`;
    
    fetch(url, {
        headers: {
            'X-Requested-With': 'XMLHttpRequest'
        }
    })
    .then(response => response.text())
    .then(html => {
        tableContainer.innerHTML = html;
        
        if (window.themeManager) {
            window.themeManager.refresh();
        }
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
            
            .notification.success {
                border-left-color: #10b981;
            }
            
            .notification.error {
                border-left-color: #ef4444;
            }
            
            .notification.info {
                border-left-color: #3b82f6;
            }
            
            .notification.warning {
                border-left-color: #f59e0b;
            }
            
            @keyframes slideIn {
                from {
                    transform: translateX(100%);
                    opacity: 0;
                }
                to {
                    transform: translateX(0);
                    opacity: 1;
                }
            }
            
            @keyframes slideOut {
                from {
                    transform: translateX(0);
                    opacity: 1;
                }
                to {
                    transform: translateX(100%);
                    opacity: 0;
                }
            }
            
            .dark-mode .notification {
                background: #1e293b;
                color: #f1f5f9;
            }
        `;
        document.head.appendChild(style);
    }
    
    const notification = document.createElement('div');
    notification.className = `notification ${type}`;
    
    let icon = 'fa-info-circle';
    if (type === 'success') icon = 'fa-check-circle';
    if (type === 'error') icon = 'fa-exclamation-circle';
    if (type === 'warning') icon = 'fa-exclamation-triangle';
    
    notification.innerHTML = `
        <i class="fa-solid ${icon}"></i>
        <span>${message}</span>
    `;
    
    container.appendChild(notification);
    
    setTimeout(() => {
        notification.style.animation = 'slideOut 0.3s ease forwards';
        setTimeout(() => notification.remove(), 300);
    }, 5000);
}

// ==================== UTILITY FUNCTIONS ====================
function applyAuditFilters() {
    const form = document.getElementById('auditFilterForm');
    if (!form) return false;
    
    const formData = new FormData(form);
    const params = new URLSearchParams(formData).toString();
    
    window.location.href = window.location.pathname + '?' + params + '#logs';
    return false;
}

// ==================== PROFILE MANAGEMENT FUNCTIONS ====================

function saveGeneralSettings() {
    const username = document.getElementById('username')?.value;
    const email = document.getElementById('email')?.value;
    
    if (!username || !email) {
        showNotification('Username and email are required', 'error');
        return;
    }
    
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    if (!emailRegex.test(email)) {
        showNotification('Please enter a valid email address', 'error');
        return;
    }
    
    const settings = {
        username: username,
        email: email
    };
    
    const saveBtn = document.querySelector('#general .btn-primary');
    const originalText = saveBtn.innerHTML;
    saveBtn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Saving...';
    saveBtn.disabled = true;
    
    // FIXED: Added /ctumoalboal-comelec prefix
    fetch('/ctumoalboal-comelec/settings/save', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': getCsrfToken()
        },
        body: JSON.stringify({
            section: 'profile',
            settings: settings
        })
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            showNotification('Profile settings saved successfully!', 'success');
        } else {
            showNotification('Error saving settings: ' + data.message, 'error');
        }
    })
    .catch(error => {
        console.error('Error:', error);
        showNotification('Error saving settings. Please try again.', 'error');
    })
    .finally(() => {
        saveBtn.innerHTML = originalText;
        saveBtn.disabled = false;
    });
}

function resetGeneralSettings() {
    if (confirm('Reset all changes to original values?')) {
        location.reload();
    }
}

// ==================== PROFILE EDIT TOGGLE FUNCTIONS ====================

let originalProfileValues = {};

function toggleProfileEdit() {
    const usernameInput = document.getElementById('username');
    const emailInput = document.getElementById('email');
    const passwordBtn = document.getElementById('forgotPasswordBtn');
    const editBtn = document.getElementById('editProfileBtn');
    const profileActions = document.getElementById('profileActions');
    const usernameLock = document.getElementById('usernameLockIcon');
    const emailLock = document.getElementById('emailLockIcon');
    
    if (!usernameInput || !emailInput) return;
    
    originalProfileValues = {
        username: usernameInput.value,
        email: emailInput.value
    };
    
    usernameInput.disabled = false;
    emailInput.disabled = false;
    passwordBtn.disabled = false;
    
    if (usernameLock) {
        usernameLock.className = 'fa-solid fa-lock-open input-lock-icon';
    }
    if (emailLock) {
        emailLock.className = 'fa-solid fa-lock-open input-lock-icon';
    }
    
    editBtn.innerHTML = '<i class="fa-solid fa-pencil"></i> Editing...';
    editBtn.style.background = 'var(--primary-gradient)';
    editBtn.style.color = 'white';
    editBtn.style.borderColor = 'transparent';
    
    profileActions.style.display = 'flex';
    usernameInput.focus();
}

function cancelProfileEdit() {
    const usernameInput = document.getElementById('username');
    const emailInput = document.getElementById('email');
    const passwordBtn = document.getElementById('forgotPasswordBtn');
    const editBtn = document.getElementById('editProfileBtn');
    const profileActions = document.getElementById('profileActions');
    const usernameLock = document.getElementById('usernameLockIcon');
    const emailLock = document.getElementById('emailLockIcon');
    
    if (!usernameInput || !emailInput) return;
    
    if (originalProfileValues.username) {
        usernameInput.value = originalProfileValues.username;
    }
    if (originalProfileValues.email) {
        emailInput.value = originalProfileValues.email;
    }
    
    usernameInput.disabled = true;
    emailInput.disabled = true;
    passwordBtn.disabled = true;
    
    if (usernameLock) {
        usernameLock.className = 'fa-solid fa-lock input-lock-icon';
    }
    if (emailLock) {
        emailLock.className = 'fa-solid fa-lock input-lock-icon';
    }
    
    editBtn.innerHTML = '<i class="fa-solid fa-pencil"></i> Edit Profile';
    editBtn.style.background = '';
    editBtn.style.color = '';
    editBtn.style.borderColor = '';
    
    profileActions.style.display = 'none';
}

// 🔴 THIS IS THE CRITICAL FUNCTION - MAKE SURE IT HAS THE CORRECT URL
function saveProfileChanges() {
    const usernameInput = document.getElementById('username');
    const emailInput = document.getElementById('email');
    const saveBtn = document.querySelector('#profileActions .btn-primary');
    
    if (!usernameInput || !emailInput) {
        showNotification('Form inputs not found', 'error');
        return;
    }
    
    const username = usernameInput.value.trim();
    const email = emailInput.value.trim();
    
    console.log('Saving profile:', { username, email });
    
    if (!username || !email) {
        showNotification('Username and email are required', 'error');
        return;
    }
    
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    if (!emailRegex.test(email)) {
        showNotification('Please enter a valid email address', 'error');
        return;
    }
    
    const originalText = saveBtn.innerHTML;
    saveBtn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Saving...';
    saveBtn.disabled = true;
    
    // 🔴 FIXED: This MUST be /ctumoalboal-comelec/settings/profile/update
    const url = '/ctumoalboal-comelec/settings/profile/update';
    console.log('Fetching URL:', url);
    
    fetch(url, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': getCsrfToken()
        },
        body: JSON.stringify({
            username: username,
            email: email
        })
    })
    .then(async response => {
        console.log('Response status:', response.status);
        const text = await response.text();
        console.log('Response text:', text);
        
        try {
            return JSON.parse(text);
        } catch (e) {
            console.error('Failed to parse JSON. Response was HTML:', text.substring(0, 200));
            throw new Error('Server returned HTML instead of JSON. The URL might be wrong.');
        }
    })
    .then(data => {
        if (data.success) {
            showNotification('Profile updated successfully!', 'success');
            originalProfileValues = {
                username: username,
                email: email
            };
            cancelProfileEdit();
        } else {
            showNotification(data.message || 'Failed to update profile', 'error');
        }
    })
    .catch(error => {
        console.error('Error:', error);
        showNotification('Network error: ' + error.message, 'error');
    })
    .finally(() => {
        saveBtn.innerHTML = originalText;
        saveBtn.disabled = false;
    });
}