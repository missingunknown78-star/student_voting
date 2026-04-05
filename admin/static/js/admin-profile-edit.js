// admin-profile-edit.js - Email change functionality for admin

document.addEventListener('DOMContentLoaded', function() {
    // Elements
    const displayMode = document.getElementById('profileDisplayMode');
    const editMode = document.getElementById('profileEditMode');
    const editBtn = document.getElementById('editProfileBtn');
    const cancelBtn = document.getElementById('cancelEditBtn');
    const editForm = document.getElementById('editProfileForm');
    
    // Modal elements
    const modal = document.getElementById('emailChangeModal');
    const closeBtn = document.querySelector('#emailChangeModal .close');
    const waitingForConfirmation = document.getElementById('waitingForConfirmation');
    const otpVerification = document.getElementById('otpVerification');
    const oldEmailDisplay = document.getElementById('oldEmailDisplay');
    const resendEmailBtn = document.getElementById('resendEmailBtn');
    const cancelChangeBtn = document.getElementById('cancelChangeBtn');
    const simpleOtpInput = document.getElementById('simpleOtpInput');
    const verifyOtpBtn = document.getElementById('verifyOtpBtn');
    const cancelOtpBtn = document.getElementById('cancelOtpBtn');
    const otpError = document.getElementById('otpError');
    const timerText = document.getElementById('timerText');
    
    // New resend OTP text element
    const resendOtpText = document.createElement('div');
    resendOtpText.className = 'resend-otp-text';
    resendOtpText.style.cssText = 'text-align: center; margin-top: 15px;';
    resendOtpText.innerHTML = '<a href="#" id="resendOtpLink" style="color: #2563eb; text-decoration: none; font-size: 0.95rem;">Resend verification code</a>';
    
    // Add it after the buttons in otpVerification
    if (otpVerification) {
        otpVerification.appendChild(resendOtpText);
    }
    
    const resendOtpLink = document.getElementById('resendOtpLink');
    
    // Toast elements (reuse existing notification system)
    let originalEmail = document.getElementById('currentEmail')?.textContent.trim() || '';
    let pendingNewEmail = '';
    let changeRequestId = null;
    let pollInterval = null;
    let resendCooldown = false;
    
    // ==================== CSRF TOKEN HELPER - REMOVED ====================
    // CSRF protection has been disabled - removed getCsrfToken function
    
    // Toggle edit mode
    function showEditMode() {
        if (displayMode && editMode) {
            displayMode.style.display = 'none';
            editMode.style.display = 'block';
            window.scrollTo({
                top: document.getElementById('profileFormCard')?.offsetTop - 20,
                behavior: 'smooth'
            });
        }
    }
    
    function showDisplayMode() {
        if (displayMode && editMode) {
            displayMode.style.display = 'block';
            editMode.style.display = 'none';
            if (editForm) editForm.reset();
        }
    }
    
    // Edit button click handler
    if (editBtn) editBtn.addEventListener('click', showEditMode);
    if (cancelBtn) cancelBtn.addEventListener('click', showDisplayMode);
    
    // Handle form submission
    if (editForm) {
        editForm.addEventListener('submit', async function(e) {
            e.preventDefault();
            
            const newUsername = document.getElementById('newUsername')?.value.trim();
            const newEmail = document.getElementById('newEmail')?.value.trim();
            
            // Check if email is being changed
            if (newEmail && newEmail !== originalEmail) {
                // Show waiting for confirmation modal
                pendingNewEmail = newEmail;
                
                // Mask email for display
                const maskedEmail = maskEmail(originalEmail);
                if (oldEmailDisplay) oldEmailDisplay.textContent = maskedEmail;
                
                if (waitingForConfirmation) waitingForConfirmation.style.display = 'block';
                if (otpVerification) otpVerification.style.display = 'none';
                if (modal) modal.style.display = 'flex';
                
                // Send verification email
                await sendVerificationEmail();
                
                // Start polling for confirmation
                startPolling();
            } else {
                // Only username change or no changes - submit directly
                submitForm();
            }
        });
    }
    
    // Mask email for privacy
    function maskEmail(email) {
        if (!email) return email;
        const parts = email.split('@');
        if (parts.length !== 2) return email;
        
        const [name, domain] = parts;
        if (name.length > 2) {
            return name[0] + '*'.repeat(name.length - 2) + name[name.length - 1] + '@' + domain;
        } else if (name.length === 2) {
            return name[0] + '*@' + domain;
        }
        return email;
    }
    
    // Send verification email (CSRF header removed)
    async function sendVerificationEmail() {
        try {
            const response = await fetch('/ctumoalboal-comelec/send-email-change-verification', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ 
                    old_email: originalEmail,
                    new_email: pendingNewEmail
                })
            });
            
            const data = await response.json();
            if (!response.ok) {
                throw new Error(data.error || 'Failed to send email');
            }
            
            changeRequestId = data.request_id;
            startResendCooldown();
            
        } catch (error) {
            showNotification('Failed to send verification email: ' + error.message, 'error');
        }
    }
    
    // Start resend cooldown
    function startResendCooldown() {
        if (resendCooldown || !resendEmailBtn || !timerText) return;
        
        resendCooldown = true;
        resendEmailBtn.disabled = true;
        let seconds = 30;
        
        const countdown = setInterval(() => {
            if (resendEmailBtn) {
                resendEmailBtn.textContent = `Resend available in ${seconds}s`;
            }
            if (timerText) {
                timerText.textContent = 'Please wait before requesting another email.';
            }
            seconds--;
            
            if (seconds < 0) {
                clearInterval(countdown);
                if (resendEmailBtn) {
                    resendEmailBtn.disabled = false;
                    resendEmailBtn.textContent = 'Resend Verification Email';
                }
                if (timerText) {
                    timerText.textContent = 'You can now request another verification email.';
                }
                resendCooldown = false;
            }
        }, 1000);
    }
    
    // Resend email button
    if (resendEmailBtn) {
        resendEmailBtn.addEventListener('click', async function(e) {
            e.preventDefault();
            if (resendEmailBtn.disabled) return;
            await sendVerificationEmail();
        });
    }
    
    // Cancel change button
    if (cancelChangeBtn) {
        cancelChangeBtn.addEventListener('click', function(e) {
            e.preventDefault();
            if (modal) modal.style.display = 'none';
            stopPolling();
        });
    }
    
    // Close modal when clicking X
    if (closeBtn) {
        closeBtn.addEventListener('click', function() {
            if (modal) modal.style.display = 'none';
            stopPolling();
        });
    }
    
    // Start polling for email confirmation status
    function startPolling() {
        if (pollInterval) clearInterval(pollInterval);
        
        pollInterval = setInterval(() => {
            checkEmailConfirmationStatus();
        }, 3000);
    }
    
    function stopPolling() {
        if (pollInterval) {
            clearInterval(pollInterval);
            pollInterval = null;
        }
    }
    
    // Check email confirmation status (CSRF header removed)
    async function checkEmailConfirmationStatus() {
        if (!changeRequestId) return;
        
        try {
            const response = await fetch(`/ctumoalboal-comelec/email-change-status/${changeRequestId}`, {
                headers: {
                    'Content-Type': 'application/json'
                }
            });
            const data = await response.json();
            
            if (data.status === 'confirmed') {
                // Show success toast
                showNotification('Old email confirmed!', 'success');
                stopPolling();
                
                setTimeout(() => {
                    // Hide waiting screen, show OTP input
                    if (waitingForConfirmation) waitingForConfirmation.style.display = 'none';
                    if (otpVerification) otpVerification.style.display = 'block';
                    
                    // Now send OTP to new email
                    sendOtpToNewEmail();
                }, 1500);
                
            } else if (data.status === 'rejected') {
                // Show reject toast
                showNotification('Email change was rejected', 'error');
                stopPolling();
                
                setTimeout(() => {
                    if (modal) modal.style.display = 'none';
                }, 2000);
            }
        } catch (error) {
            console.error('Error checking status:', error);
        }
    }
    
    // Send OTP to new email (CSRF header removed)
    async function sendOtpToNewEmail() {
        try {
            const response = await fetch('/ctumoalboal-comelec/send-otp-to-new-email', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ 
                    email: pendingNewEmail,
                    request_id: changeRequestId
                })
            });
            
            const data = await response.json();
            if (!response.ok) {
                throw new Error(data.error || 'Failed to send OTP');
            }
            
            // Store OTP for verification (in development mode)
            if (data.code) {
                sessionStorage.setItem('otpCode', data.code);
                sessionStorage.setItem('otpExpiry', Date.now() + 600000); // 10 minutes
            }
            
            // Reset resend link
            if (resendOtpLink) {
                resendOtpLink.style.pointerEvents = 'auto';
                resendOtpLink.style.opacity = '1';
                resendOtpLink.innerHTML = 'Resend verification code';
            }
            
        } catch (error) {
            showNotification('Failed to send OTP: ' + error.message, 'error');
        }
    }
    
    // Resend OTP handler (CSRF header removed)
    if (resendOtpLink) {
        resendOtpLink.addEventListener('click', async function(e) {
            e.preventDefault();
            
            // Change to spinning
            const originalText = this.innerHTML;
            this.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Sending...';
            this.style.pointerEvents = 'none';
            this.style.opacity = '0.7';
            
            try {
                const response = await fetch('/ctumoalboal-comelec/send-otp-to-new-email', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({ 
                        email: pendingNewEmail,
                        request_id: changeRequestId
                    })
                });
                
                const data = await response.json();
                if (!response.ok) {
                    throw new Error(data.error || 'Failed to send OTP');
                }
                
                // Store new OTP if in development
                if (data.code) {
                    sessionStorage.setItem('otpCode', data.code);
                    sessionStorage.setItem('otpExpiry', Date.now() + 600000);
                }
                
                showNotification('Verification code resent!', 'success');
                
                // Reset after 2 seconds
                setTimeout(() => {
                    this.innerHTML = 'Resend verification code';
                    this.style.pointerEvents = 'auto';
                    this.style.opacity = '1';
                }, 2000);
                
            } catch (error) {
                showNotification('Failed to resend OTP: ' + error.message, 'error');
                
                // Reset on error
                this.innerHTML = 'Resend verification code';
                this.style.pointerEvents = 'auto';
                this.style.opacity = '1';
            }
        });
    }
    
    // Verify OTP
    if (verifyOtpBtn) {
        verifyOtpBtn.addEventListener('click', function() {
            const enteredCode = simpleOtpInput?.value.trim();
            const storedCode = sessionStorage.getItem('otpCode');
            const expiry = parseInt(sessionStorage.getItem('otpExpiry') || '0');
            
            if (!storedCode || Date.now() > expiry) {
                if (otpError) otpError.textContent = 'OTP has expired. Please request a new one.';
                return;
            }
            
            if (enteredCode === storedCode) {
                // OTP verified - submit the form
                if (modal) modal.style.display = 'none';
                
                const oldVerifiedInput = document.createElement('input');
                oldVerifiedInput.type = 'hidden';
                oldVerifiedInput.name = 'old_email_verified';
                oldVerifiedInput.value = 'true';
                editForm.appendChild(oldVerifiedInput);
                
                const newVerifiedInput = document.createElement('input');
                newVerifiedInput.type = 'hidden';
                newVerifiedInput.name = 'new_email_verified';
                newVerifiedInput.value = 'true';
                editForm.appendChild(newVerifiedInput);
                
                submitForm();
                if (simpleOtpInput) simpleOtpInput.value = '';
                if (otpError) otpError.textContent = '';
            } else {
                if (otpError) otpError.textContent = 'Invalid OTP code';
                if (simpleOtpInput) simpleOtpInput.value = '';
            }
        });
    }
    
    // Cancel OTP button
    if (cancelOtpBtn) {
        cancelOtpBtn.addEventListener('click', function() {
            if (modal) modal.style.display = 'none';
            if (waitingForConfirmation) waitingForConfirmation.style.display = 'block';
            if (otpVerification) otpVerification.style.display = 'none';
            if (simpleOtpInput) simpleOtpInput.value = '';
            if (otpError) otpError.textContent = '';
        });
    }
    
    // Close modal when clicking outside
    window.addEventListener('click', function(e) {
        if (e.target === modal) {
            if (modal) modal.style.display = 'none';
            stopPolling();
        }
    });
    
    // ==================== FIXED SUBMIT FORM FUNCTION ====================
    // Submit form function - FIXED: Removed incorrect Content-Type header
    function submitForm() {
        const formData = new FormData(editForm);
        
        // Don't set Content-Type header - let the browser set it automatically for FormData
        fetch(editForm.action, {
            method: 'POST',
            // REMOVED: 'Content-Type': 'application/json' - This was causing the issue!
            body: formData
        })
        .then(response => {
            if (!response.ok) {
                return response.json().then(err => Promise.reject(err));
            }
            return response.json();
        })
        .then(data => {
            if (data.success) {
                showNotification('Profile updated successfully!', 'success');
                
                // Update displayed values
                const currentUsername = document.getElementById('currentUsername');
                const currentEmail = document.getElementById('currentEmail');
                
                if (currentUsername && data.new_username) {
                    currentUsername.textContent = data.new_username;
                }
                if (currentEmail && data.new_email) {
                    currentEmail.textContent = data.new_email;
                    originalEmail = data.new_email;
                } else if (currentEmail && pendingNewEmail) {
                    currentEmail.textContent = pendingNewEmail;
                    originalEmail = pendingNewEmail;
                }
                
                // Update form input values
                const usernameInput = document.getElementById('newUsername');
                const emailInput = document.getElementById('newEmail');
                if (usernameInput && data.new_username) usernameInput.value = data.new_username;
                if (emailInput && data.new_email) emailInput.value = data.new_email;
                
                showDisplayMode();
                
                // Reload after 1.5 seconds to refresh any dependent data
                setTimeout(() => {
                    location.reload();
                }, 1500);
            } else {
                showNotification('Error: ' + (data.error || data.message || 'Unknown error'), 'error');
            }
        })
        .catch(error => {
            console.error('Fetch error:', error);
            showNotification('An error occurred: ' + (error.error || error.message || 'Please try again'), 'error');
        });
    }
    
    // Show notification (reuse existing system)
    function showNotification(message, type = 'info') {
        if (typeof window.showNotification === 'function') {
            window.showNotification(message, type);
        } else {
            // Create a temporary notification if the global function doesn't exist
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
            notification.innerHTML = `<i class="fa-solid ${type === 'success' ? 'fa-check-circle' : type === 'error' ? 'fa-exclamation-circle' : 'fa-info-circle'}"></i> ${message}`;
            document.body.appendChild(notification);
            
            setTimeout(() => {
                notification.style.animation = 'slideOut 0.3s ease forwards';
                setTimeout(() => notification.remove(), 300);
            }, 3000);
        }
    }
});

// ==================== FORGOT PASSWORD HANDLER ====================

// Make functions globally available
window.toggleProfileEdit = function() {
    // This function is called from HTML onclick
    const displayMode = document.getElementById('profileDisplayMode');
    const editMode = document.getElementById('profileEditMode');
    if (displayMode && editMode) {
        displayMode.style.display = 'none';
        editMode.style.display = 'block';
        window.scrollTo({
            top: document.getElementById('profileFormCard')?.offsetTop - 20,
            behavior: 'smooth'
        });
    }
};

window.handleForgotPassword = function() {
    console.log('handleForgotPassword called');
    
    // Check if button exists first
    const btn = document.getElementById('forgotPasswordBtn');
    console.log('Button found:', btn);
    
    if (!btn) {
        console.error('forgotPasswordBtn not found in DOM');
        // Try to find it by other means
        const possibleBtn = document.querySelector('.btn-forgot-password');
        if (possibleBtn) {
            console.log('Found by class name instead:', possibleBtn);
            // Call the function with the found button
            handleForgotPasswordWithButton(possibleBtn);
        } else {
            alert('Error: Could not find the change password button. Please refresh the page.');
        }
        return;
    }
    
    handleForgotPasswordWithButton(btn);
};

function handleForgotPasswordWithButton(btn) {
    if (!confirm('Send password reset instructions to your email?')) {
        return;
    }
    
    const originalText = btn.innerHTML;
    btn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Sending...';
    btn.disabled = true;
    
    // Get current email from display - try multiple selectors
    const currentEmailEl = document.getElementById('currentEmail') || 
                          document.querySelector('#profileDisplayMode .info-value') ||
                          document.querySelector('[id="currentEmail"]');
    
    console.log('Email element found:', currentEmailEl);
    
    let currentEmail = '';
    if (currentEmailEl) {
        currentEmail = currentEmailEl.textContent.trim();
    }
    
    // Fallback to email input if display not found
    if (!currentEmail) {
        const emailInput = document.getElementById('email') || document.getElementById('newEmail');
        if (emailInput) {
            currentEmail = emailInput.value.trim();
        }
    }
    
    console.log('Current email:', currentEmail);
    
    if (!currentEmail) {
        showNotificationFallback('Could not find your email address', 'error');
        btn.innerHTML = originalText;
        btn.disabled = false;
        return;
    }
    
    // CSRF header removed from this fetch
    fetch('/ctumoalboal-comelec/forgot-password', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({
            email: currentEmail
        })
    })
    .then(response => {
        console.log('Response status:', response.status);
        return response.json();
    })
    .then(data => {
        console.log('Response data:', data);
        if (data.success) {
            showNotificationFallback('Password reset link sent to your email!', 'success');
        } else {
            showNotificationFallback(data.message || 'Failed to send reset link', 'error');
        }
    })
    .catch(error => {
        console.error('Error:', error);
        showNotificationFallback('Network error. Please try again.', 'error');
    })
    .finally(() => {
        btn.innerHTML = originalText;
        btn.disabled = false;
    });
}

function showNotificationFallback(message, type = 'info') {
    // Check if global notification function exists
    if (typeof window.showNotification === 'function') {
        window.showNotification(message, type);
    } else {
        // Fallback notification
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
        notification.innerHTML = `<i class="fa-solid ${type === 'success' ? 'fa-check-circle' : type === 'error' ? 'fa-exclamation-circle' : 'fa-info-circle'}"></i> ${message}`;
        document.body.appendChild(notification);
        
        setTimeout(() => {
            notification.style.animation = 'slideOut 0.3s ease forwards';
            setTimeout(() => notification.remove(), 300);
        }, 3000);
    }
}

// Add animation styles if they don't exist
if (!document.querySelector('#notification-styles')) {
    const style = document.createElement('style');
    style.id = 'notification-styles';
    style.textContent = `
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
    `;
    document.head.appendChild(style);
}