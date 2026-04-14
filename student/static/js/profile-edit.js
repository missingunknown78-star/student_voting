// profile-edit.js - MANUAL EMAIL SENDING VERSION

document.addEventListener('DOMContentLoaded', function() {
    const displayMode = document.getElementById('profileDisplayMode');
    const editMode = document.getElementById('profileEditMode');
    const editBtn = document.getElementById('editProfileBtn');
    const cancelBtn = document.getElementById('cancelEditBtn');
    const editForm = document.getElementById('editProfileForm');
    const saveChangesBtn = editForm ? editForm.querySelector('button[type="submit"]') : null;
    
    // Modal elements
    const modal = document.getElementById('emailChangeModal');
    const closeBtn = document.querySelector('#emailChangeModal .close');
    
    // Step 1 elements
    const step1Div = document.getElementById('step1WaitingForConfirmation');
    const step2Div = document.getElementById('step2WaitingForConfirmation');
    const otpVerification = document.getElementById('otpVerification');
    
    const oldEmailDisplay = document.getElementById('oldEmailDisplay');
    const oldEmailDisplay2 = document.getElementById('oldEmailDisplay2');
    const sendVerificationBtn = document.getElementById('sendVerificationEmailBtn');
    const resendEmailBtn2 = document.getElementById('resendEmailBtn2');
    const cancelChangeStep1Btn = document.getElementById('cancelChangeStep1Btn');
    const cancelChangeStep2Btn = document.getElementById('cancelChangeStep2Btn');
    
    const simpleOtpInput = document.getElementById('simpleOtpInput');
    const verifyOtpBtn = document.getElementById('verifyOtpBtn');
    const cancelOtpBtn = document.getElementById('cancelOtpBtn');
    const otpError = document.getElementById('otpError');
    const timerText2 = document.getElementById('timerText2');
    const sendTimerText = document.getElementById('sendTimerText');
    
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
    
    // Handle Save Changes button
    if (editForm) {
        editForm.addEventListener('submit', async function(e) {
            e.preventDefault();
            
            const newEmail = document.getElementById('newEmail').value.trim();
            
            if (newEmail !== originalEmail) {
                // Show modal - Step 1 (manual send)
                pendingNewEmail = newEmail;
                
                // Mask email for display
                const maskedEmail = maskEmail(originalEmail);
                oldEmailDisplay.textContent = maskedEmail;
                oldEmailDisplay2.textContent = maskedEmail;
                
                // Reset modal to Step 1
                step1Div.style.display = 'block';
                step2Div.style.display = 'none';
                otpVerification.style.display = 'none';
                modal.style.display = 'flex';
                
                // Clear any existing polling
                stopPolling();
                
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
    
    // Send verification email (manual button click)
    async function sendVerificationEmail() {
        if (!sendVerificationBtn) return;
        
        try {
            setButtonLoading(sendVerificationBtn, true, 'Sending...');
            
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
            
            // Move to Step 2 (waiting for confirmation)
            step1Div.style.display = 'none';
            step2Div.style.display = 'block';
            
            // Show success toast
            toast.textContent = '✓ Verification email sent! Please check your inbox.';
            toast.style.display = 'block';
            setTimeout(() => {
                toast.style.display = 'none';
            }, 3000);
            
            // Start resend cooldown for Step 2
            startResendCooldown();
            
            // Start polling for confirmation
            startPolling();
            
        } catch (error) {
            toastReject.textContent = '❌ Error: ' + error.message;
            toastReject.style.display = 'block';
            setTimeout(() => {
                toastReject.style.display = 'none';
            }, 3000);
        } finally {
            setButtonLoading(sendVerificationBtn, false);
        }
    }
    
    // Start resend cooldown for Step 2
    function startResendCooldown() {
        if (resendCooldown || !resendEmailBtn2) return;
        
        resendCooldown = true;
        let seconds = 30;
        
        // Disable and style button
        resendEmailBtn2.disabled = true;
        resendEmailBtn2.style.background = '#adb5bd';
        resendEmailBtn2.style.cursor = 'not-allowed';
        
        const countdown = setInterval(() => {
            if (seconds > 0) {
                resendEmailBtn2.innerHTML = `⏳ Wait ${seconds}s`;
                timerText2.textContent = `Please wait ${seconds} seconds before requesting another email.`;
                seconds--;
            } else {
                clearInterval(countdown);
                resendEmailBtn2.disabled = false;
                resendEmailBtn2.style.background = '#6c757d';
                resendEmailBtn2.style.cursor = 'pointer';
                resendEmailBtn2.innerHTML = 'Resend Verification Email';
                timerText2.textContent = 'You can now request another verification email.';
                resendCooldown = false;
            }
        }, 1000);
    }
    
    // Send verification button (Step 1)
    if (sendVerificationBtn) {
        sendVerificationBtn.addEventListener('click', sendVerificationEmail);
    }
    
    // Resend email button (Step 2)
    if (resendEmailBtn2) {
        resendEmailBtn2.addEventListener('click', async function(e) {
            e.preventDefault();
            if (resendEmailBtn2.disabled || resendCooldown) return;
            
            try {
                setButtonLoading(resendEmailBtn2, true, 'Sending...');
                
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
                
                toast.textContent = '✓ Verification email resent! Please check your inbox.';
                toast.style.display = 'block';
                setTimeout(() => {
                    toast.style.display = 'none';
                }, 3000);
                
                // Restart cooldown
                startResendCooldown();
                
                // Restart polling
                stopPolling();
                startPolling();
                
            } catch (error) {
                toastReject.textContent = '❌ Error: ' + error.message;
                toastReject.style.display = 'block';
                setTimeout(() => {
                    toastReject.style.display = 'none';
                }, 3000);
            } finally {
                setButtonLoading(resendEmailBtn2, false);
            }
        });
    }
    
    // Cancel buttons
    if (cancelChangeStep1Btn) {
        cancelChangeStep1Btn.addEventListener('click', function(e) {
            e.preventDefault();
            modal.style.display = 'none';
            stopPolling();
        });
    }
    
    if (cancelChangeStep2Btn) {
        cancelChangeStep2Btn.addEventListener('click', function(e) {
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
                toast.textContent = '✓ Old email confirmed! Sending verification code to new email...';
                toast.style.display = 'block';
                stopPolling();
                
                setTimeout(() => {
                    toast.style.display = 'none';
                    
                    // Hide step 2, show OTP input
                    step2Div.style.display = 'none';
                    otpVerification.style.display = 'block';
                    
                    // Send OTP to new email
                    sendOtpToNewEmail();
                }, 1500);
                
            } else if (data.status === 'rejected') {
                // Show reject toast
                toastReject.textContent = '❌ Email change rejected';
                toastReject.style.display = 'block';
                stopPolling();
                
                setTimeout(() => {
                    toastReject.style.display = 'none';
                    modal.style.display = 'none';
                    // Reset to step 1
                    step1Div.style.display = 'block';
                    step2Div.style.display = 'none';
                    otpVerification.style.display = 'none';
                }, 2000);
            } else if (data.status === 'expired') {
                toastReject.textContent = '❌ Verification link expired. Please request again.';
                toastReject.style.display = 'block';
                stopPolling();
                
                setTimeout(() => {
                    toastReject.style.display = 'none';
                    modal.style.display = 'none';
                    // Reset to step 1
                    step1Div.style.display = 'block';
                    step2Div.style.display = 'none';
                    otpVerification.style.display = 'none';
                }, 2000);
            }
        } catch (error) {
            console.error('Error checking status:', error);
        }
    }
    
    // Send OTP to new email
    async function sendOtpToNewEmail() {
        if (verifyOtpBtn) setButtonLoading(verifyOtpBtn, true, 'Sending OTP...');
        
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
            
            toast.textContent = '✓ Verification code sent to your new email!';
            toast.style.display = 'block';
            setTimeout(() => {
                toast.style.display = 'none';
            }, 2000);
            
        } catch (error) {
            alert('Failed to send OTP: ' + error.message);
        } finally {
            if (verifyOtpBtn) setButtonLoading(verifyOtpBtn, false);
        }
    }
    
    // Verify OTP code
    if (verifyOtpBtn) {
        verifyOtpBtn.addEventListener('click', async function() {
            const enteredCode = simpleOtpInput.value.trim();
            
            if (!enteredCode || enteredCode.length !== 6) {
                otpError.textContent = 'Please enter a valid 6-digit code';
                return;
            }
            
            // Set loading state
            setButtonLoading(verifyOtpBtn, true, 'Verifying...');
            
            try {
                const response = await fetch('/student/verify-otp-code', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({ 
                        otp: enteredCode,
                        request_id: changeRequestId,
                        email: pendingNewEmail
                    })
                });
                
                const data = await response.json();
                
                if (data.success) {
                    // OTP verified successfully
                    toast.textContent = '✓ Code verified! Updating profile...';
                    toast.style.display = 'block';
                    
                    // Close modal
                    modal.style.display = 'none';
                    
                    // Add verification flags to form
                    let oldVerifiedInput = editForm.querySelector('input[name="old_email_verified"]');
                    let newVerifiedInput = editForm.querySelector('input[name="new_email_verified"]');
                    
                    if (!oldVerifiedInput) {
                        oldVerifiedInput = document.createElement('input');
                        oldVerifiedInput.type = 'hidden';
                        oldVerifiedInput.name = 'old_email_verified';
                        editForm.appendChild(oldVerifiedInput);
                    }
                    oldVerifiedInput.value = 'true';
                    
                    if (!newVerifiedInput) {
                        newVerifiedInput = document.createElement('input');
                        newVerifiedInput.type = 'hidden';
                        newVerifiedInput.name = 'new_email_verified';
                        editForm.appendChild(newVerifiedInput);
                    }
                    newVerifiedInput.value = 'true';
                    
                    // Clear OTP input
                    simpleOtpInput.value = '';
                    otpError.textContent = '';
                    
                    // Submit the form
                    if (saveChangesBtn) setButtonLoading(saveChangesBtn, true, 'Saving...');
                    await submitForm();
                    if (saveChangesBtn) setButtonLoading(saveChangesBtn, false);
                    
                } else {
                    otpError.textContent = data.message || 'Invalid verification code';
                    simpleOtpInput.value = '';
                }
                
            } catch (error) {
                console.error('Error verifying OTP:', error);
                otpError.textContent = 'Error verifying code. Please try again.';
            } finally {
                setButtonLoading(verifyOtpBtn, false);
            }
        });
    }
    
    // Cancel OTP button
    if (cancelOtpBtn) {
        cancelOtpBtn.addEventListener('click', function() {
            modal.style.display = 'none';
            step1Div.style.display = 'block';
            step2Div.style.display = 'none';
            otpVerification.style.display = 'none';
            simpleOtpInput.value = '';
            otpError.textContent = '';
            stopPolling();
        });
    }
    
    // Close modal when clicking outside
    window.addEventListener('click', function(e) {
        if (e.target === modal) {
            modal.style.display = 'none';
            stopPolling();
            // Reset to step 1
            step1Div.style.display = 'block';
            step2Div.style.display = 'none';
            otpVerification.style.display = 'none';
        }
    });
    
    // Submit form function
    async function submitForm() {
        const formData = new FormData(editForm);
        
        try {
            const response = await fetch(editForm.action, {
                method: 'POST',
                body: formData
            });
            
            const data = await response.json();
            
            if (data.success) {
                toast.textContent = '✅ Profile updated successfully!';
                toast.style.display = 'block';
                
                setTimeout(() => {
                    toast.style.display = 'none';
                }, 3000);
                
                // Update displayed values
                document.getElementById('currentUsername').textContent = data.new_username || document.getElementById('currentUsername').textContent;
                document.getElementById('currentEmail').textContent = data.new_email || pendingNewEmail || originalEmail;
                const currentCourse = document.getElementById('currentCourse');
                if (currentCourse && data.new_course) currentCourse.textContent = data.new_course;
                const currentYear = document.getElementById('currentYear');
                if (currentYear && data.new_year) currentYear.textContent = data.new_year;
                
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
    
    // Device trust button with loading
    if (trustForm && trustButton) {
        trustForm.addEventListener('submit', async function(e) {
            e.preventDefault();
            
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