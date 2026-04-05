// profile-edit.js

// ==================== CSRF TOKEN HELPER - REMOVED ====================
// CSRF protection has been disabled - removed getCsrfToken() function

document.addEventListener('DOMContentLoaded', function() {
    const displayMode = document.getElementById('profileDisplayMode');
    const editMode = document.getElementById('profileEditMode');
    const editBtn = document.getElementById('editProfileBtn');
    const cancelBtn = document.getElementById('cancelEditBtn');
    const editForm = document.getElementById('editProfileForm');
    
    // Modal elements
    const modal = document.getElementById('emailChangeModal');
    const closeBtn = document.querySelector('.close');
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
    
    // Toast elements
    const toast = document.getElementById('toast');
    const toastReject = document.getElementById('toastReject');
    
    let originalEmail = document.getElementById('currentEmail').textContent.trim();
    let pendingNewEmail = '';
    let changeRequestId = null;
    let pollInterval = null;
    let resendCooldown = false;
    
    // CSRF Token Helper Function - REMOVED (CSRF protection disabled)
    
    // Toggle edit mode
    function showEditMode() {
        displayMode.style.display = 'none';
        editMode.style.display = 'block';
        window.scrollTo({
            top: document.getElementById('profileFormCard').offsetTop - 20,
            behavior: 'smooth'
        });
    }
    
    function showDisplayMode() {
        displayMode.style.display = 'block';
        editMode.style.display = 'none';
        editForm.reset();
    }
    
    // Edit button click handler
    if (editBtn) editBtn.addEventListener('click', showEditMode);
    if (cancelBtn) cancelBtn.addEventListener('click', showDisplayMode);
    
    // Handle form submission
    editForm.addEventListener('submit', async function(e) {
        e.preventDefault();
        
        const newEmail = document.getElementById('newEmail').value.trim();
        
        if (newEmail !== originalEmail) {
            // Show waiting for confirmation modal
            pendingNewEmail = newEmail;
            
            // Mask email for display
            const maskedEmail = maskEmail(originalEmail);
            oldEmailDisplay.textContent = maskedEmail;
            
            waitingForConfirmation.style.display = 'block';
            otpVerification.style.display = 'none';
            modal.style.display = 'flex';
            
            // Send verification email
            await sendVerificationEmail();
            
            // Start polling for confirmation
            startPolling();
        } else {
            submitForm();
        }
    });
    
    // Mask email for privacy
    function maskEmail(email) {
        if (!email) return email;
        const [name, domain] = email.split('@');
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
            const response = await fetch('/student/send-email-change-verification', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                    // REMOVED: 'X-CSRFToken': getCsrfToken()
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
            alert('Failed to send verification email: ' + error.message);
        }
    }
    
    // Start resend cooldown
    function startResendCooldown() {
        if (resendCooldown) return;
        
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
    resendEmailBtn.addEventListener('click', async function(e) {
        e.preventDefault();
        if (resendEmailBtn.disabled) return;
        await sendVerificationEmail();
    });
    
    // Cancel change button
    cancelChangeBtn.addEventListener('click', function(e) {
        e.preventDefault();
        modal.style.display = 'none';
        stopPolling();
    });
    
    // Close modal when clicking X
    if (closeBtn) {
        closeBtn.addEventListener('click', function() {
            modal.style.display = 'none';
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
            const response = await fetch(`/student/email-change-status/${changeRequestId}`, {
                headers: {
                    'Content-Type': 'application/json'
                    // REMOVED: 'X-CSRFToken': getCsrfToken()
                }
            });
            const data = await response.json();
            
            if (data.status === 'confirmed') {
                // Show success toast
                toast.style.display = 'block';
                stopPolling();
                
                setTimeout(() => {
                    toast.style.display = 'none';
                    
                    // Hide waiting screen, show OTP input
                    waitingForConfirmation.style.display = 'none';
                    otpVerification.style.display = 'block';
                    
                    // Now send OTP to new email
                    sendOtpToNewEmail();
                }, 1500);
                
            } else if (data.status === 'rejected') {
                // Show reject toast
                toastReject.style.display = 'block';
                stopPolling();
                
                setTimeout(() => {
                    toastReject.style.display = 'none';
                    modal.style.display = 'none';
                }, 2000);
            }
        } catch (error) {
            console.error('Error checking status:', error);
        }
    }
    
    // Send OTP to new email (CSRF header removed)
    async function sendOtpToNewEmail() {
        try {
            const response = await fetch('/student/send-otp-to-new-email', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                    // REMOVED: 'X-CSRFToken': getCsrfToken()
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
            
            // Store OTP for verification
            sessionStorage.setItem('otpCode', data.code);
            sessionStorage.setItem('otpExpiry', Date.now() + 600000); // 10 minutes
            
        } catch (error) {
            alert('Failed to send OTP: ' + error.message);
        }
    }
    
    // Verify OTP
    verifyOtpBtn.addEventListener('click', function() {
        const enteredCode = simpleOtpInput.value.trim();
        const storedCode = sessionStorage.getItem('otpCode');
        const expiry = parseInt(sessionStorage.getItem('otpExpiry'));
        
        if (!storedCode || Date.now() > expiry) {
            otpError.textContent = 'OTP has expired. Please request a new one.';
            return;
        }
        
        if (enteredCode === storedCode) {
            // OTP verified - submit the form
            modal.style.display = 'none';
            
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
            simpleOtpInput.value = '';
            otpError.textContent = '';
        } else {
            otpError.textContent = 'Invalid OTP code';
            simpleOtpInput.value = '';
        }
    });
    
    // Cancel OTP button
    cancelOtpBtn.addEventListener('click', function() {
        modal.style.display = 'none';
        waitingForConfirmation.style.display = 'block';
        otpVerification.style.display = 'none';
        simpleOtpInput.value = '';
        otpError.textContent = '';
    });
    
    // Close modal when clicking outside
    window.addEventListener('click', function(e) {
        if (e.target === modal) {
            modal.style.display = 'none';
            stopPolling();
        }
    });
    
    // Submit form function (CSRF header removed)
    function submitForm() {
        const formData = new FormData(editForm);
        
        fetch(editForm.action, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
                // REMOVED: 'X-CSRFToken': getCsrfToken()
            },
            body: formData
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                alert('Profile updated successfully!');
                document.getElementById('currentUsername').textContent = data.new_username || document.getElementById('currentUsername').textContent;
                document.getElementById('currentEmail').textContent = data.new_email || pendingNewEmail || originalEmail;
                document.getElementById('currentCourse').textContent = data.new_course || document.getElementById('currentCourse').textContent;
                document.getElementById('currentYear').textContent = data.new_year || document.getElementById('currentYear').textContent;
                
                showDisplayMode();
                
                setTimeout(() => {
                    location.reload();
                }, 1000);
            } else {
                alert('Error: ' + data.error);
            }
        })
        .catch(error => {
            alert('An error occurred: ' + error.message);
        });
    }
});