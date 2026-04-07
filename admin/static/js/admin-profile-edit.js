// admin-profile-edit.js - Profile Edit & Email Change

let originalProfileValues = {};

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

let emailChangeRequestId = null;
let pollInterval = null;
let isSendingEmail = false;
let resendCountdownInterval = null;

function sendEmailChangeVerification(oldEmail, newEmail) {
    if (isSendingEmail) {
        console.log('Already sending email, skipping duplicate request...');
        return;
    }
    
    const resendBtn = document.getElementById('resendEmailBtn');
    const timerText = document.getElementById('timerText');
    
    if (resendBtn) {
        resendBtn.disabled = true;
        resendBtn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Sending...';
    }
    if (timerText) timerText.textContent = 'Sending verification email...';
    
    isSendingEmail = true;
    
    fetch('/ctumoalboal-comelec/send-email-change-verification', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ old_email: oldEmail, new_email: newEmail })
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            emailChangeRequestId = data.request_id;
            console.log('Email change request ID:', emailChangeRequestId);
            startPolling();
            showNotification('Verification email sent! Please check your inbox.', 'success');
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
    })
    .finally(() => {
        isSendingEmail = false;
    });
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

function startPolling() {
    if (pollInterval) clearInterval(pollInterval);
    pollInterval = setInterval(checkEmailConfirmationStatus, 3000);
}

function stopPolling() {
    if (pollInterval) {
        clearInterval(pollInterval);
        pollInterval = null;
    }
}

function checkEmailConfirmationStatus() {
    if (!emailChangeRequestId) return;
    
    fetch(`/ctumoalboal-comelec/email-change-status/${emailChangeRequestId}`, {
        headers: { 'Content-Type': 'application/json' }
    })
    .then(response => response.json())
    .then(data => {
        if (data.status === 'confirmed') {
            console.log('Email confirmation received!');
            stopPolling();
            document.getElementById('waitingForConfirmation').style.display = 'none';
            document.getElementById('otpVerification').style.display = 'block';
            sendOtpToNewEmail();
        } else if (data.status === 'rejected') {
            stopPolling();
            showNotification('Email change was rejected. Please try again.', 'error');
            closeEmailModal();
        }
    })
    .catch(error => console.error('Error checking status:', error));
}

function sendOtpToNewEmail() {
    const newEmail = window.pendingProfileData?.newEmail;
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
        body: JSON.stringify({ email: newEmail, request_id: emailChangeRequestId })
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            showNotification('Verification code sent to your new email!', 'success');
            if (data.code) {
                console.log('OTP code (dev mode):', data.code);
                sessionStorage.setItem('otpCode', data.code);
                sessionStorage.setItem('otpExpiry', Date.now() + 600000);
            }
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
    emailChangeRequestId = null;
    isSendingEmail = false;
    window.pendingProfileData = null;
    
    const resendBtn = document.getElementById('resendEmailBtn');
    if (resendBtn) {
        resendBtn.disabled = false;
        resendBtn.innerHTML = 'Resend Verification Email';
    }
    if (resendCountdownInterval) {
        clearInterval(resendCountdownInterval);
        resendCountdownInterval = null;
    }
    const timerText = document.getElementById('timerText');
    if (timerText) timerText.textContent = '';
    
    const otpInput = document.getElementById('simpleOtpInput');
    if (otpInput) otpInput.value = '';
    
    const otpError = document.getElementById('otpError');
    if (otpError) otpError.textContent = '';
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
            console.log('emailChangeRequestId:', emailChangeRequestId);
            console.log('pendingProfileData:', window.pendingProfileData);
            
            if (!enteredCode || enteredCode.length !== 6) {
                document.getElementById('otpError').textContent = 'Please enter a valid 6-digit code';
                return;
            }
            
            verifyOtpBtn.disabled = true;
            verifyOtpBtn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Verifying...';
            
            fetch('/ctumoalboal-comelec/verify-otp-code', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ 
                    otp: enteredCode,
                    request_id: emailChangeRequestId,
                    email: window.pendingProfileData?.newEmail
                })
            })
            .then(response => response.json())
            .then(data => {
                console.log('OTP verification response:', data);
                
                if (data.success) {
                    console.log('✅ OTP VERIFICATION SUCCESSFUL!');
                    showNotification('Code verified! Updating profile...', 'success');
                    
                    // Store the pending data before closing modal
                    const pendingData = window.pendingProfileData;
                    
                    closeEmailModal();
                    
                    // Check if performProfileUpdate exists
                    console.log('Checking if window.performProfileUpdate exists:', typeof window.performProfileUpdate);
                    console.log('Pending data:', pendingData);
                    
                    // 🔥 CRITICAL FIX: Call the profile update with verification flags
                    if (pendingData && typeof window.performProfileUpdate === 'function') {
                        console.log('Calling performProfileUpdate with:', pendingData.username, pendingData.newEmail, true);
                        window.performProfileUpdate(
                            pendingData.username,
                            pendingData.newEmail,
                            true  // This indicates email was verified
                        );
                    } else {
                        console.error('ERROR: performProfileUpdate not available or pendingData missing!');
                        console.log('performProfileUpdate type:', typeof window.performProfileUpdate);
                        console.log('pendingData:', pendingData);
                        showNotification('Error: Could not update profile', 'error');
                    }
                    
                    window.pendingProfileData = null;
                } else {
                    console.log('❌ OTP VERIFICATION FAILED:', data.message);
                    document.getElementById('otpError').textContent = data.message || 'Invalid verification code';
                    otpInput.value = '';
                    verifyOtpBtn.disabled = false;
                    verifyOtpBtn.innerHTML = 'Verify';
                }
            })
            .catch(error => {
                console.error('Error verifying OTP:', error);
                document.getElementById('otpError').textContent = 'Error verifying code. Please try again.';
                verifyOtpBtn.disabled = false;
                verifyOtpBtn.innerHTML = 'Verify';
            });
        };
    }
    
    if (resendBtn) {
        resendBtn.onclick = function() {
            if (isSendingEmail) {
                showNotification('Already sending, please wait...', 'warning');
                return;
            }
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
    if (typeof window.showNotification === 'function') {
        window.showNotification(message, type);
    } else {
        alert(message);
    }
}