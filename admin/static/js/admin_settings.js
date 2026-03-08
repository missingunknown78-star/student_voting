// Settings navigation
document.addEventListener('DOMContentLoaded', function() {
    // Initialize settings navigation
    initializeSettingsNav();
    
    // Initialize 2FA if on that section
    initialize2FA();
    
    // Check for URL hash
    if (window.location.hash === '#logs') {
        setTimeout(() => {
            const logsNav = document.querySelector('[data-section="logs"]');
            if (logsNav) logsNav.click();
        }, 100);
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

// General Settings Functions
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
    
    fetch('/admin/settings/save', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
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

// 2FA Functions
function initialize2FA() {
    // Check if 2FA setup elements exist
    const setupCard = document.getElementById('twofaSetupCard');
    if (setupCard) {
        // Add any initialization needed
    }
}

function show2FASetup() {
    const setupCard = document.getElementById('twofaSetupCard');
    if (setupCard) {
        setupCard.style.display = 'block';
        setupCard.scrollIntoView({ behavior: 'smooth' });
    }
}

function toggleManualEntry() {
    const manualEntry = document.getElementById('manualEntry');
    if (manualEntry) {
        if (manualEntry.style.display === 'none') {
            manualEntry.style.display = 'block';
        } else {
            manualEntry.style.display = 'none';
        }
    }
}

function verify2FA() {
    const code = document.getElementById('twofaCode');
    const secret = document.getElementById('totpSecret');
    const messageDiv = document.getElementById('twofaMessage');
    
    if (!code || !secret) return false;
    
    if (code.value.length !== 6 || !/^\d+$/.test(code.value)) {
        if (messageDiv) {
            messageDiv.innerHTML = '<p class="error-msg">Please enter a valid 6-digit code</p>';
        }
        return false;
    }
    
    // Send verification to backend
    fetch('/admin/2fa/verify', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({
            secret: secret.value,
            code: code.value
        })
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            if (messageDiv) {
                messageDiv.innerHTML = '<p class="success-msg">2FA enabled successfully!</p>';
            }
            
            // Update status badge
            update2FAStatus(true);
            
            // Hide enable button
            const enableBtn = document.querySelector('#twofactor .btn-primary');
            if (enableBtn) enableBtn.style.display = 'none';
            
            // Reload page to show backup codes
            setTimeout(() => {
                location.reload();
            }, 2000);
        } else {
            if (messageDiv) {
                messageDiv.innerHTML = '<p class="error-msg">' + (data.message || 'Invalid code. Please try again.') + '</p>';
            }
        }
    })
    .catch(error => {
        console.error('Error:', error);
        if (messageDiv) {
            messageDiv.innerHTML = '<p class="error-msg">Error verifying code. Please try again.</p>';
        }
    });
    
    return false;
}

function disable2FA() {
    if (confirm('Are you sure you want to disable Two-Factor Authentication? This will make your account less secure.')) {
        fetch('/admin/2fa/disable', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
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

function save2FASettings() {
    const smsBackup = document.getElementById('smsBackup');
    const emailBackup = document.getElementById('emailBackup');
    const backupPhone = document.getElementById('backupPhone');
    
    fetch('/admin/2fa/settings', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({
            sms_backup: smsBackup ? smsBackup.checked : false,
            email_backup: emailBackup ? emailBackup.checked : false,
            backup_phone: backupPhone ? backupPhone.value : ''
        })
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            showNotification('2FA settings saved successfully!', 'success');
        } else {
            showNotification('Error saving settings: ' + data.message, 'error');
        }
    })
    .catch(error => {
        console.error('Error:', error);
        showNotification('Error saving settings. Please try again.', 'error');
    });
}

function generateNewBackupCodes() {
    if (confirm('Generating new backup codes will invalidate your old ones. Continue?')) {
        fetch('/admin/2fa/backup-codes', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
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

// Trusted Devices Functions
function trustCurrentDevice() {
    const button = event.target.closest('button');
    const originalText = button.innerHTML;
    button.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Processing...';
    button.disabled = true;
    
    fetch('/admin/trusted-devices/add', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
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

// FIXED revokeTrustedDevice function
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
    
    // Send the request
    fetch(`/admin/trusted-devices/remove/${deviceId}`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-Requested-With': 'XMLHttpRequest'
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
            // Show success message using notification system
            showNotification(data.message || 'Device removal email sent successfully! Please check your email.', 'success');
            
            // Update button to show pending state
            button.innerHTML = '<i class="fa-solid fa-clock"></i> Pending Confirmation';
            button.style.background = '#f59e0b';
            button.style.borderColor = '#f59e0b';
            button.disabled = true;
            
            // Add a small note that they need to check email
            const deviceItem = button.closest('.device-item');
            if (deviceItem) {
                const pendingNote = document.createElement('div');
                pendingNote.className = 'pending-note';
                pendingNote.innerHTML = '<small style="color: #f59e0b; display: block; margin-top: 5px;"><i class="fa-solid fa-envelope"></i> Check email to confirm removal</small>';
                deviceItem.querySelector('.device-actions').appendChild(pendingNote);
            }
        } else {
            // Show error message
            showNotification(data.message || 'Failed to remove device', 'error');
            
            // Restore button state
            button.innerHTML = originalText;
            button.disabled = false;
        }
    })
    .catch(error => {
        console.error('Fetch error:', error);
        showNotification('Network error occurred. Please try again.', 'error');
        
        // Restore button state
        button.innerHTML = originalText;
        button.disabled = false;
    });
}

// Alternative simpler version
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
    
    fetch(`/admin/trusted-devices/test-remove/${deviceId}`, {
        method: 'POST'
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

// Audit Log Functions
function applyAuditFilters() {
    const form = document.getElementById('auditFilterForm');
    if (!form) return false;
    
    const formData = new FormData(form);
    const params = new URLSearchParams(formData).toString();
    
    window.location.href = window.location.pathname + '?' + params + '#logs';
    return false;
}


function clearAuditFilters() {
    const form = document.getElementById('auditFilterForm');
    if (form) {
        form.querySelectorAll('input').forEach(input => {
            if (input.type !== 'button' && input.type !== 'submit') {
                input.value = '';
            }
        });
    }
    
    window.location.href = '/admin/audit-logs#logs';
}

function loadAuditPage(page) {
    const form = document.getElementById('auditFilterForm');
    if (!form) return false;
    
    const formData = new FormData(form);
    const params = new URLSearchParams(formData).toString();
    
    window.location.href = '/admin/audit-logs?page=' + page + '&' + params + '#logs';
    return false;
}

// Notification System
function showNotification(message, type = 'info') {
    // Create notification container if it doesn't exist
    let container = document.querySelector('.notification-container');
    if (!container) {
        container = document.createElement('div');
        container.className = 'notification-container';
        document.body.appendChild(container);
        
        // Add styles for notifications
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
    
    // Create notification
    const notification = document.createElement('div');
    notification.className = `notification ${type}`;
    
    // Add icon based on type
    let icon = 'fa-info-circle';
    if (type === 'success') icon = 'fa-check-circle';
    if (type === 'error') icon = 'fa-exclamation-circle';
    if (type === 'warning') icon = 'fa-exclamation-triangle';
    
    notification.innerHTML = `
        <i class="fa-solid ${icon}"></i>
        <span>${message}</span>
    `;
    
    container.appendChild(notification);
    
    // Auto remove after 5 seconds
    setTimeout(() => {
        notification.style.animation = 'slideOut 0.3s ease forwards';
        setTimeout(() => notification.remove(), 300);
    }, 5000);
}


