// admin-profile-edit.js - DATABASE-BACKED VERSION (Works on PythonAnywhere)

let originalProfileValues = {};
let pollInterval = null;
let adminEmailChangeToken = null;
let adminPendingNewEmail = null;
let resendCountdownInterval = null;

document.addEventListener('DOMContentLoaded', function() {
    initializeProfileEdit();
    initializeEmailChangeModal();
});

function initializeProfileEdit() {
    const editBtn = document.getElementById('editProfileBtn');
    const cancelBtn = document.getElementById('cancelEditBtn');
    const editForm = document.getElementById('editProfileForm');
    
    if (editBtn) {
        editBtn.onclick = toggleProfileEdit;
    }
    
    if (cancelBtn) {
        cancelBtn.onclick = cancelProfileEdit;
    }
    
    if (editForm) {
        editForm.onsubmit = function(e) {
            e.preventDefault();
            if (typeof window.saveProfileChanges === 'function') {
                window.saveProfileChanges();
            } else if (typeof performProfileUpdate === 'function') {
                const username = document.getElementById('newUsername').value.trim();
                const email = document.getElementById('newEmail').value.trim();
                performProfileUpdate(username, email, true);
            }
        };
    }
}

window.toggleProfileEdit = function() {
    const usernameInput = document.getElementById('newUsername');
    const emailInput = document.getElementById('newEmail');
    const passwordBtn = document.getElementById('forgotPasswordBtn');
    const editBtn = document.getElementById('editProfileBtn');
    const profileActions = document.getElementById('profileActions');
    const displayMode = document.getElementById('profileDisplayMode');
    const editMode = document.getElementById('profileEditMode');
    
    if (!usernameInput || !emailInput) return;
    
    const currentUsername = document.getElementById('currentUsername');
    const currentEmail = document.getElementById('currentEmail');
    
    originalProfileValues = {
        username: currentUsername ? currentUsername.textContent.trim() : usernameInput.value,
        email: currentEmail ? currentEmail.textContent.trim() : emailInput.value
    };
    
    usernameInput.value = originalProfileValues.username;
    emailInput.value = originalProfileValues.email;
    
    usernameInput.disabled = false;
    emailInput.disabled = false;
    if (passwordBtn) passwordBtn.disabled = false;
    
    if (displayMode) displayMode.style.display = 'none';
    if (editMode) editMode.style.display = 'block';
    
    if (editBtn) {
        editBtn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Loading...';
        editBtn.disabled = true;
        setTimeout(() => {
            editBtn.innerHTML = '<i class="fa-solid fa-pencil"></i> Edit Profile';
            editBtn.disabled = false;
        }, 500);
    }
    
    if (profileActions) profileActions.style.display = 'flex';
    usernameInput.focus();
};

window.cancelProfileEdit = function() {
    const usernameInput = document.getElementById('newUsername');
    const emailInput = document.getElementById('newEmail');
    const passwordBtn = document.getElementById('forgotPasswordBtn');
    const editBtn = document.getElementById('editProfileBtn');
    const profileActions = document.getElementById('profileActions');
    const displayMode = document.getElementById('profileDisplayMode');
    const editMode = document.getElementById('profileEditMode');
    
    if (!usernameInput || !emailInput) return;
    
    usernameInput.value = originalProfileValues.username;
    emailInput.value = originalProfileValues.email;
    
    usernameInput.disabled = true;
    emailInput.disabled = true;
    if (passwordBtn) passwordBtn.disabled = true;
    
    if (displayMode) displayMode.style.display = 'block';
    if (editMode) editMode.style.display = 'none';
    
    if (editBtn) editBtn.innerHTML = '<i class="fa-solid fa-pencil"></i> Edit Profile';
    if (profileActions) profileActions.style.display = 'none';
};

// ==================== FORGOT PASSWORD ====================
window.handleForgotPassword = function() {
    const btn = document.getElementById('forgotPasswordBtn');
    if (!btn) return;
    
    if (!confirm('Send password reset instructions to your email?')) return;
    
    const originalText = btn.innerHTML;
    btn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Sending...';
    btn.disabled = true;
    
    const currentEmail = document.getElementById('currentEmail').textContent.trim();
    
    fetch('/ctumoalboal-comelec/forgot-password', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email: currentEmail })
    })
    .then(response => response.json())
    .then(data => {
        showNotification(data.message || (data.success ? 'Reset link sent!' : 'Failed to send'), data.success ? 'success' : 'error');
    })
    .catch(error => {
        console.error('Error:', error);
        showNotification('Network error. Please try again.', 'error');
    })
    .finally(() => {
        btn.innerHTML = originalText;
        btn.disabled = false;
    });
};

// ==================== PROFILE UPDATE FUNCTION ====================
window.performProfileUpdate = async function(username, email, emailVerified) {
    console.log('=== performProfileUpdate called ===');
    console.log('Username:', username);
    console.log('Email:', email);
    console.log('Email Verified:', emailVerified);
    
    const editForm = document.getElementById('editProfileForm');
    if (!editForm) return;
    
    const saveBtn = document.querySelector('#profileActions .btn-primary');
    if (saveBtn) {
        saveBtn.disabled = true;
        saveBtn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Saving...';
    }
    
    try {
        const response = await fetch('/ctumoalboal-comelec/settings/profile/update', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                username: username,
                email: email,
                old_email_verified: emailVerified,
                new_email_verified: emailVerified
            })
        });
        
        const data = await response.json();
        
        if (data.success) {
            showNotification('Profile updated successfully!', 'success');
            
            // Update displayed values
            const currentUsername = document.getElementById('currentUsername');
            const currentEmail = document.getElementById('currentEmail');
            
            if (currentUsername) currentUsername.textContent = data.new_username || username;
            if (currentEmail) currentEmail.textContent = data.new_email || email;
            
            // Switch back to display mode
            cancelProfileEdit();
            
            setTimeout(() => {
                location.reload();
            }, 1500);
        } else {
            showNotification(data.message || 'Failed to update profile', 'error');
        }
    } catch (error) {
        console.error('Error updating profile:', error);
        showNotification('Network error. Please try again.', 'error');
    } finally {
        if (saveBtn) {
            saveBtn.disabled = false;
            saveBtn.innerHTML = '<i class="fa-solid fa-save"></i> Save Changes';
        }
    }
};

// ==================== EMAIL CHANGE MODAL FUNCTIONS ====================
function showEmailChangeModal(username, newEmail) {
    console.log('=== showEmailChangeModal called ===');
    console.log('Username:', username);
    console.log('New Email:', newEmail);
    
    const modal = document.getElementById('emailChangeModal');
    const waitingDiv = document.getElementById('waitingForConfirmation');
    const otpDiv = document.getElementById('otpVerification');
    const oldEmailDisplay = document.getElementById('oldEmailDisplay');
    const currentEmail = document.getElementById('currentEmail').textContent.trim();
    
    const maskedEmail = maskEmail(currentEmail);
    if (oldEmailDisplay) oldEmailDisplay.textContent = maskedEmail;
    
    if (waitingDiv) waitingDiv.style.display = 'block';
    if (otpDiv) otpDiv.style.display = 'none';
    
    const otpError = document.getElementById('otpError');
    if (otpError) otpError.textContent = '';
    
    window.pendingProfileData = { username: username, newEmail: newEmail };
    console.log('window.pendingProfileData set:', window.pendingProfileData);
    
    if (modal) modal.style.display = 'flex';
    
    sendEmailChangeVerification(currentEmail, newEmail);
}

function maskEmail(email) {
    if (!email || !email.includes('@')) return email;
    const [name, domain] = email.split('@');
    if (name.length <= 2) return email;
    return name[0] + '***' + name.slice(-1) + '@' + domain;
}

function sendEmailChangeVerification(oldEmail, newEmail) {
    const resendBtn = document.getElementById('resendEmailBtn');
    const timerText = document.getElementById('timerText');
    
    if (resendBtn) {
        resendBtn.disabled = true;
        resendBtn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Sending...';
    }
    if (timerText) timerText.textContent = 'Sending verification email...';
    
    fetch('/ctumoalboal-comelec/send-email-change-verification', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ old_email: oldEmail, new_email: newEmail })
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            console.log('Verification email sent successfully');
            showNotification('Verification email sent! Please check your inbox.', 'success');
            startCheckingConfirmation();
            startResendCooldown();
        } else {
            showNotification(data.error || 'Failed to send verification email', 'error');
            if (resendBtn) {
                resendBtn.disabled = false;
                resendBtn.innerHTML = 'Resend Verification Email';
            }
            if (timerText) timerText.textContent = '';
        }
    })
    .catch(error => {
        console.error('Error:', error);
        showNotification('Failed to send verification email', 'error');
        if (resendBtn) {
            resendBtn.disabled = false;
            resendBtn.innerHTML = 'Resend Verification Email';
        }
        if (timerText) timerText.textContent = '';
    });
}

function startCheckingConfirmation() {
    if (pollInterval) clearInterval(pollInterval);
    
    pollInterval = setInterval(async () => {
        try {
            const response = await fetch('/ctumoalboal-comelec/check-email-confirmation', {
                headers: { 'Content-Type': 'application/json' }
            });
            const data = await response.json();
            
            if (data.confirmed) {
                // Old email confirmed!
                adminEmailChangeToken = data.token;
                adminPendingNewEmail = data.new_email;
                
                showNotification('✓ Old email confirmed! Sending verification code to new email...', 'success');
                stopPolling();
                
                setTimeout(() => {
                    const waitingDiv = document.getElementById('waitingForConfirmation');
                    const otpDiv = document.getElementById('otpVerification');
                    if (waitingDiv) waitingDiv.style.display = 'none';
                    if (otpDiv) otpDiv.style.display = 'block';
                    sendOtpToNewEmail();
                }, 1500);
            }
        } catch (error) {
            console.error('Error checking confirmation:', error);
        }
    }, 3000);
    
    // Auto-stop after 5 minutes
    setTimeout(() => {
        if (pollInterval) {
            stopPolling();
            const waitingDiv = document.getElementById('waitingForConfirmation');
            if (waitingDiv && waitingDiv.style.display !== 'none') {
                showNotification('Verification link expired. Please request again.', 'error');
                closeEmailModal();
            }
        }
    }, 5 * 60 * 1000);
}

function stopPolling() {
    if (pollInterval) {
        clearInterval(pollInterval);
        pollInterval = null;
    }
}

function startResendCooldown() {
    const resendBtn = document.getElementById('resendEmailBtn');
    const timerText = document.getElementById('timerText');
    let seconds = 30;
    
    if (!resendBtn) return;
    
    if (resendCountdownInterval) clearInterval(resendCountdownInterval);
    
    resendBtn.disabled = true;
    resendBtn.innerHTML = `Wait ${seconds}s`;
    
    resendCountdownInterval = setInterval(() => {
        seconds--;
        if (seconds <= 0) {
            clearInterval(resendCountdownInterval);
            resendCountdownInterval = null;
            resendBtn.disabled = false;
            resendBtn.innerHTML = 'Resend Verification Email';
            if (timerText) timerText.textContent = '';
        } else {
            resendBtn.innerHTML = `Wait ${seconds}s`;
            if (timerText) timerText.textContent = `Resend available in ${seconds} seconds`;
        }
    }, 1000);
}

function sendOtpToNewEmail() {
    const newEmail = adminPendingNewEmail || window.pendingProfileData?.newEmail;
    if (!newEmail) return;
    
    console.log('Sending OTP to new email:', newEmail);
    
    const verifyBtn = document.getElementById('verifyOtpBtn');
    if (verifyBtn) {
        verifyBtn.disabled = true;
        verifyBtn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Sending OTP...';
    }
    
    fetch('/ctumoalboal-comelec/send-otp-to-new-email', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ 
            email: newEmail, 
            token: adminEmailChangeToken 
        })
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            showNotification('Verification code sent to your new email!', 'success');
        } else {
            showNotification(data.error || 'Failed to send verification code', 'error');
        }
    })
    .catch(error => {
        console.error('Error sending OTP:', error);
        showNotification('Failed to send verification code', 'error');
    })
    .finally(() => {
        if (verifyBtn) {
            verifyBtn.disabled = false;
            verifyBtn.innerHTML = 'Verify';
        }
    });
}

function closeEmailModal() {
    const modal = document.getElementById('emailChangeModal');
    if (modal) modal.style.display = 'none';
    stopPolling();
    
    if (resendCountdownInterval) {
        clearInterval(resendCountdownInterval);
        resendCountdownInterval = null;
    }
    
    window.pendingProfileData = null;
    adminEmailChangeToken = null;
    adminPendingNewEmail = null;
    
    const timerText = document.getElementById('timerText');
    if (timerText) timerText.textContent = '';
    
    const otpInput = document.getElementById('simpleOtpInput');
    if (otpInput) otpInput.value = '';
    
    const otpError = document.getElementById('otpError');
    if (otpError) otpError.textContent = '';
    
    const waitingDiv = document.getElementById('waitingForConfirmation');
    const otpDiv = document.getElementById('otpVerification');
    if (waitingDiv) waitingDiv.style.display = 'block';
    if (otpDiv) otpDiv.style.display = 'none';
}

function initializeEmailChangeModal() {
    const modal = document.getElementById('emailChangeModal');
    const closeBtn = document.querySelector('#emailChangeModal .close');
    const cancelChangeBtn = document.getElementById('cancelChangeBtn');
    const verifyOtpBtn = document.getElementById('verifyOtpBtn');
    const cancelOtpBtn = document.getElementById('cancelOtpBtn');
    const resendBtn = document.getElementById('resendEmailBtn');
    
    if (closeBtn) closeBtn.onclick = closeEmailModal;
    if (cancelChangeBtn) cancelChangeBtn.onclick = closeEmailModal;
    if (cancelOtpBtn) cancelOtpBtn.onclick = closeEmailModal;
    
    if (verifyOtpBtn) {
        verifyOtpBtn.onclick = function() {
            const otpInput = document.getElementById('simpleOtpInput');
            const enteredCode = otpInput ? otpInput.value.trim() : '';
            
            console.log('=== VERIFY OTP BUTTON CLICKED ===');
            console.log('Entered OTP:', enteredCode);
            
            if (!enteredCode || enteredCode.length !== 6) {
                const otpError = document.getElementById('otpError');
                if (otpError) otpError.textContent = 'Please enter a valid 6-digit code';
                return;
            }
            
            verifyOtpBtn.disabled = true;
            verifyOtpBtn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Verifying...';
            
            fetch('/ctumoalboal-comelec/verify-otp-code', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ 
                    otp: enteredCode,
                    email: adminPendingNewEmail || window.pendingProfileData?.newEmail
                })
            })
            .then(response => response.json())
            .then(data => {
                console.log('OTP verification response:', data);
                
                if (data.success) {
                    console.log('✅ OTP VERIFICATION SUCCESSFUL!');
                    showNotification('Code verified! Updating profile...', 'success');
                    
                    const pendingData = window.pendingProfileData;
                    closeEmailModal();
                    
                    if (pendingData && typeof window.performProfileUpdate === 'function') {
                        window.performProfileUpdate(
                            pendingData.username,
                            pendingData.newEmail,
                            true
                        );
                    }
                    
                    window.pendingProfileData = null;
                } else {
                    console.log('❌ OTP VERIFICATION FAILED:', data.message);
                    const otpError = document.getElementById('otpError');
                    if (otpError) otpError.textContent = data.message || 'Invalid verification code';
                    if (otpInput) otpInput.value = '';
                    verifyOtpBtn.disabled = false;
                    verifyOtpBtn.innerHTML = 'Verify';
                }
            })
            .catch(error => {
                console.error('Error verifying OTP:', error);
                const otpError = document.getElementById('otpError');
                if (otpError) otpError.textContent = 'Error verifying code. Please try again.';
                verifyOtpBtn.disabled = false;
                verifyOtpBtn.innerHTML = 'Verify';
            });
        };
    }
    
    if (resendBtn) {
        resendBtn.onclick = function() {
            const currentEmail = document.getElementById('currentEmail').textContent.trim();
            const newEmail = window.pendingProfileData?.newEmail;
            if (currentEmail && newEmail) {
                sendEmailChangeVerification(currentEmail, newEmail);
            }
        };
    }
    
    window.onclick = function(e) {
        if (e.target === modal) closeEmailModal();
    };
}

function showNotification(message, type = 'info') {
    // Check if global showNotification exists
    if (typeof window.showNotification === 'function') {
        window.showNotification(message, type);
    } else {
        // Create temporary notification
        const notification = document.createElement('div');
        notification.style.cssText = `
            position: fixed;
            top: 20px;
            right: 20px;
            background: ${type === 'success' ? '#10b981' : type === 'error' ? '#ef4444' : '#3b82f6'};
            color: white;
            padding: 12px 20px;
            border-radius: 8px;
            z-index: 10000;
            font-weight: 500;
            box-shadow: 0 4px 12px rgba(0,0,0,0.15);
            animation: slideIn 0.3s ease;
        `;
        notification.textContent = message;
        document.body.appendChild(notification);
        
        setTimeout(() => {
            notification.style.animation = 'slideOut 0.3s ease forwards';
            setTimeout(() => notification.remove(), 300);
        }, 3000);
    }
}

// Add animation styles if not present
if (!document.querySelector('#notification-styles')) {
    const style = document.createElement('style');
    style.id = 'notification-styles';
    style.textContent = `
        @keyframes slideIn {
            from { transform: translateX(100%); opacity: 0; }
            to { transform: translateX(0); opacity: 1; }
        }
        @keyframes slideOut {
            from { transform: translateX(0); opacity: 1; }
            to { transform: translateX(100%); opacity: 0; }
        }
    `;
    document.head.appendChild(style);
}