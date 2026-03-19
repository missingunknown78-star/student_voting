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
    
    // Toast elements (reuse existing notification system)
    let originalEmail = document.getElementById('currentEmail')?.textContent.trim() || '';
    let pendingNewEmail = '';
    let changeRequestId = null;
    let pollInterval = null;
    let resendCooldown = false;
    
    // CSRF Token Helper Function
    function getCsrfToken() {
        const metaTag = document.querySelector('meta[name="csrf-token"]');
        return metaTag ? metaTag.getAttribute('content') : '';
    }
    
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
            
            const newEmail = document.getElementById('newEmail')?.value.trim();
            
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
    
    // Send verification email with CSRF token
    async function sendVerificationEmail() {
        try {
            const response = await fetch('/ctumoalboal-comelec/send-email-change-verification', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': getCsrfToken()
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
            resendEmailBtn.textContent = `Resend available in ${seconds}s`;
            timerText.textContent = 'Please wait before requesting another email.';
            seconds--;
            
            if (seconds < 0) {
                clearInterval(countdown);
                resendEmailBtn.disabled = false;
                resendEmailBtn.textContent = 'Resend Verification Email';
                timerText.textContent = 'You can now request another verification email.';
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
    
    // Check email confirmation status
    async function checkEmailConfirmationStatus() {
        if (!changeRequestId) return;
        
        try {
            const response = await fetch(`/ctumoalboal-comelec/email-change-status/${changeRequestId}`, {
                headers: {
                    'X-CSRFToken': getCsrfToken()
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
    
    // Send OTP to new email with CSRF token
    async function sendOtpToNewEmail() {
        try {
            const response = await fetch('/ctumoalboal-comelec/send-otp-to-new-email', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': getCsrfToken()
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
            
        } catch (error) {
            showNotification('Failed to send OTP: ' + error.message, 'error');
        }
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
    
    // Submit form function
    function submitForm() {
        const formData = new FormData(editForm);
        
        fetch(editForm.action, {
            method: 'POST',
            headers: {
                'X-CSRFToken': getCsrfToken()
            },
            body: formData
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                showNotification('Profile updated successfully!', 'success');
                
                // Update displayed values
                const currentUsername = document.getElementById('currentUsername');
                const currentEmail = document.getElementById('currentEmail');
                
                if (currentUsername) currentUsername.textContent = data.new_username || currentUsername.textContent;
                if (currentEmail) {
                    currentEmail.textContent = data.new_email || pendingNewEmail || originalEmail;
                    originalEmail = data.new_email || pendingNewEmail || originalEmail;
                }
                
                showDisplayMode();
                
                setTimeout(() => {
                    location.reload();
                }, 1000);
            } else {
                showNotification('Error: ' + data.error, 'error');
            }
        })
        .catch(error => {
            showNotification('An error occurred: ' + error.message, 'error');
        });
    }
    
    // Show notification (reuse existing system)
    function showNotification(message, type = 'info') {
        if (typeof window.showNotification === 'function') {
            window.showNotification(message, type);
        } else {
            alert(message);
        }
    }
});


// ==================== FORGOT PASSWORD HANDLER ====================

// Make functions globally available
window.toggleProfileEdit = function() {
    showEditMode();
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
        showNotification('Could not find your email address', 'error');
        btn.innerHTML = originalText;
        btn.disabled = false;
        return;
    }
    
    fetch('/ctumoalboal-comelec/forgot-password', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': getCsrfToken()
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
            showNotification('Password reset link sent to your email!', 'success');
        } else {
            showNotification(data.message || 'Failed to send reset link', 'error');
        }
    })
    .catch(error => {
        console.error('Error:', error);
        showNotification('Network error. Please try again.', 'error');
    })
    .finally(() => {
        btn.innerHTML = originalText;
        btn.disabled = false;
    });
}

// Also expose getCsrfToken globally if not already
if (typeof window.getCsrfToken !== 'function') {
    window.getCsrfToken = getCsrfToken;
}