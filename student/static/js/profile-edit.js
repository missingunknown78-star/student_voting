// profile-edit.js

// ==================== CSRF TOKEN HELPER - REMOVED ====================
// CSRF protection has been disabled - removed getCsrfToken() function

document.addEventListener('DOMContentLoaded', function() {
    const displayMode = document.getElementById('profileDisplayMode');
    const editMode = document.getElementById('profileEditMode');
    const editBtn = document.getElementById('editProfileBtn');
    const cancelBtn = document.getElementById('cancelEditBtn');
    const editForm = document.getElementById('editProfileForm');
    const saveChangesBtn = editForm ? editForm.querySelector('button[type="submit"]') : null;
    
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
    
    // Device Trust Form
    const trustForm = document.querySelector('.trust-form');
    const trustButton = trustForm ? trustForm.querySelector('button') : null;
    
    let originalEmail = document.getElementById('currentEmail').textContent.trim();
    let pendingNewEmail = '';
    let changeRequestId = null;
    let pollInterval = null;
    let resendCooldown = false;
    
    // Helper function to show loading state on a button
    function setButtonLoading(button, isLoading, loadingText = 'Processing...') {
        if (!button) return;
        if (isLoading) {
            button.disabled = true;
            button.dataset.originalText = button.innerHTML;
            button.innerHTML = `<span class="spinner"></span> ${loadingText}`;
            // Add spinner CSS if not exists
            if (!document.querySelector('#spinner-styles')) {
                const styles = document.createElement('style');
                styles.id = 'spinner-styles';
                styles.textContent = `
                    .spinner {
                        display: inline-block;
                        width: 14px;
                        height: 14px;
                        border: 2px solid rgba(255,255,255,0.3);
                        border-radius: 50%;
                        border-top-color: white;
                        animation: spin 0.6s linear infinite;
                        margin-right: 6px;
                        vertical-align: middle;
                    }
                    @keyframes spin {
                        to { transform: rotate(360deg); }
                    }
                    button:disabled {
                        opacity: 0.7;
                        cursor: not-allowed;
                    }
                `;
                document.head.appendChild(styles);
            }
        } else {
            button.disabled = false;
            if (button.dataset.originalText) {
                button.innerHTML = button.dataset.originalText;
                delete button.dataset.originalText;
            }
        }
    }
    
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
    
    // Handle Save Changes button with loading state
    if (editForm) {
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
                
                // Send verification email with loading state
                await sendVerificationEmail();
                
                // Start polling for confirmation
                startPolling();
            } else {
                // Set loading state on save button
                if (saveChangesBtn) setButtonLoading(saveChangesBtn, true, 'Saving...');
                await submitForm();
                if (saveChangesBtn) setButtonLoading(saveChangesBtn, false);
            }
        });
    }
    
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
    
    // Send verification email with loading state
    async function sendVerificationEmail() {
        if (!resendEmailBtn) return;
        
        // Save original button text
        const originalText = resendEmailBtn.innerHTML;
        
        try {
            setButtonLoading(resendEmailBtn, true, 'Sending...');
            
            const response = await fetch('/student/send-email-change-verification', {
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
            alert('Failed to send verification email: ' + error.message);
            setButtonLoading(resendEmailBtn, false);
            resendEmailBtn.innerHTML = originalText;
        } finally {
            setButtonLoading(resendEmailBtn, false);
        }
    }
    
    // Start resend cooldown with visual feedback
    function startResendCooldown() {
        if (resendCooldown || !resendEmailBtn) return;
        
        resendCooldown = true;
        let seconds = 30;
        
        // Disable and style button
        resendEmailBtn.disabled = true;
        resendEmailBtn.style.background = '#adb5bd';
        resendEmailBtn.style.cursor = 'not-allowed';
        
        const countdown = setInterval(() => {
            if (seconds > 0) {
                resendEmailBtn.innerHTML = `⏳ Wait ${seconds}s`;
                timerText.textContent = `Please wait ${seconds} seconds before requesting another email.`;
                seconds--;
            } else {
                clearInterval(countdown);
                resendEmailBtn.disabled = false;
                resendEmailBtn.style.background = '#6c757d';
                resendEmailBtn.style.cursor = 'pointer';
                resendEmailBtn.innerHTML = 'Resend Verification Email';
                timerText.textContent = 'You can now request another verification email.';
                resendCooldown = false;
            }
        }, 1000);
    }
    
    // Resend email button with loading
    if (resendEmailBtn) {
        resendEmailBtn.addEventListener('click', async function(e) {
            e.preventDefault();
            if (resendEmailBtn.disabled || resendCooldown) return;
            await sendVerificationEmail();
        });
    }
    
    // Cancel change button
    if (cancelChangeBtn) {
        cancelChangeBtn.addEventListener('click', function(e) {
            e.preventDefault();
            modal.style.display = 'none';
            stopPolling();
        });
    }
    
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
    
    // Check email confirmation status
    async function checkEmailConfirmationStatus() {
        if (!changeRequestId) return;
        
        try {
            const response = await fetch(`/student/email-change-status/${changeRequestId}`, {
                headers: {
                    'Content-Type': 'application/json'
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
    
    // Send OTP to new email with loading
    async function sendOtpToNewEmail() {
        if (verifyOtpBtn) setButtonLoading(verifyOtpBtn, true, 'Sending...');
        
        try {
            const response = await fetch('/student/send-otp-to-new-email', {
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
            
            // Store OTP for verification
            sessionStorage.setItem('otpCode', data.code);
            sessionStorage.setItem('otpExpiry', Date.now() + 600000); // 10 minutes
            
        } catch (error) {
            alert('Failed to send OTP: ' + error.message);
        } finally {
            if (verifyOtpBtn) setButtonLoading(verifyOtpBtn, false);
        }
    }
    
    // Verify OTP with loading
    if (verifyOtpBtn) {
        verifyOtpBtn.addEventListener('click', function() {
            const enteredCode = simpleOtpInput.value.trim();
            const storedCode = sessionStorage.getItem('otpCode');
            const expiry = parseInt(sessionStorage.getItem('otpExpiry'));
            
            if (!storedCode || Date.now() > expiry) {
                otpError.textContent = 'OTP has expired. Please request a new one.';
                return;
            }
            
            if (enteredCode === storedCode) {
                // Set loading on verify button
                setButtonLoading(verifyOtpBtn, true, 'Verifying...');
                
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
                
                // Set loading on save button before submitting
                if (saveChangesBtn) setButtonLoading(saveChangesBtn, true, 'Saving...');
                
                submitForm().finally(() => {
                    setButtonLoading(verifyOtpBtn, false);
                    if (saveChangesBtn) setButtonLoading(saveChangesBtn, false);
                });
                
                simpleOtpInput.value = '';
                otpError.textContent = '';
            } else {
                otpError.textContent = 'Invalid OTP code';
                simpleOtpInput.value = '';
            }
        });
    }
    
    // Cancel OTP button
    if (cancelOtpBtn) {
        cancelOtpBtn.addEventListener('click', function() {
            modal.style.display = 'none';
            waitingForConfirmation.style.display = 'block';
            otpVerification.style.display = 'none';
            simpleOtpInput.value = '';
            otpError.textContent = '';
        });
    }
    
    // Close modal when clicking outside
    window.addEventListener('click', function(e) {
        if (e.target === modal) {
            modal.style.display = 'none';
            stopPolling();
        }
    });
    
    // Submit form function with loading state
    async function submitForm() {
        const formData = new FormData(editForm);
        
        try {
            const response = await fetch(editForm.action, {
                method: 'POST',
                body: formData
            });
            
            const data = await response.json();
            
            if (data.success) {
                // Show success toast
                toast.textContent = '✅ Profile updated successfully!';
                toast.style.display = 'block';
                
                setTimeout(() => {
                    toast.style.display = 'none';
                }, 3000);
                
                document.getElementById('currentUsername').textContent = data.new_username || document.getElementById('currentUsername').textContent;
                document.getElementById('currentEmail').textContent = data.new_email || pendingNewEmail || originalEmail;
                document.getElementById('currentCourse').textContent = data.new_course || document.getElementById('currentCourse').textContent;
                document.getElementById('currentYear').textContent = data.new_year || document.getElementById('currentYear').textContent;
                
                // Update original email reference
                if (data.new_email) originalEmail = data.new_email;
                
                showDisplayMode();
                
                setTimeout(() => {
                    location.reload();
                }, 1500);
            } else {
                toastReject.textContent = '❌ Error: ' + data.error;
                toastReject.style.display = 'block';
                setTimeout(() => {
                    toastReject.style.display = 'none';
                }, 3000);
            }
        } catch (error) {
            toastReject.textContent = '❌ An error occurred: ' + error.message;
            toastReject.style.display = 'block';
            setTimeout(() => {
                toastReject.style.display = 'none';
            }, 3000);
        }
    }
    
    // ============ DEVICE TRUST BUTTON WITH LOADING ============
    if (trustForm && trustButton) {
        trustForm.addEventListener('submit', async function(e) {
            e.preventDefault();
            
            // Set loading state on trust button
            const originalText = trustButton.innerHTML;
            setButtonLoading(trustButton, true, 
                trustButton.innerHTML.includes('Remove') ? 'Removing...' : 'Trusting...');
            
            try {
                const response = await fetch(trustForm.action, {
                    method: 'POST',
                    body: new FormData(trustForm)
                });
                
                const data = await response.json();
                
                if (data.success) {
                    // Show success toast
                    toast.textContent = '✓ Device trust updated successfully!';
                    toast.style.display = 'block';
                    setTimeout(() => {
                        toast.style.display = 'none';
                        location.reload();
                    }, 1500);
                } else {
                    throw new Error(data.error || 'Failed to update device trust');
                }
            } catch (error) {
                toastReject.textContent = '❌ Error: ' + error.message;
                toastReject.style.display = 'block';
                setTimeout(() => {
                    toastReject.style.display = 'none';
                }, 3000);
                setButtonLoading(trustButton, false);
                trustButton.innerHTML = originalText;
            }
        });
    }
});