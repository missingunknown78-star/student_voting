// deletion-request.js
document.addEventListener('DOMContentLoaded', function() {
    const deletionBtn = document.getElementById('requestDeletionBtn');
    const deletionModal = document.getElementById('deletionModal');
    
    // Check if elements exist before proceeding
    if (!deletionModal) {
        console.error('Deletion modal not found');
        return;
    }
    
    const closeBtn = deletionModal.querySelector('.close');
    const cancelBtn = document.getElementById('cancelDeletionBtn');
    const deletionForm = document.getElementById('deletionForm');
    const deletionReason = document.getElementById('deletionReason');
    const submitBtn = document.getElementById('submitDeletionBtn');
    const charCount = document.getElementById('charCount');
    const toast = document.getElementById('toast');
    const toastReject = document.getElementById('toastReject');
    
    const MAX_CHARS = 5000;
    const MIN_CHARS_FOR_SUBMIT = 10; // At least 10 characters to enable submit

    // Format number with commas
    function formatNumber(num) {
        return num.toString().replace(/\B(?=(\d{3})+(?!\d))/g, ",");
    }

    // Update character count and validation
    function updateCharCount() {
        if (!deletionReason || !charCount || !submitBtn) return;
        
        const length = deletionReason.value.length;
        charCount.textContent = formatNumber(length);
        
        // Enable submit button if at least 10 characters and not exceeding max
        if (length >= MIN_CHARS_FOR_SUBMIT && length <= MAX_CHARS) {
            submitBtn.disabled = false;
            deletionReason.classList.add('valid');
        } else {
            submitBtn.disabled = true;
            deletionReason.classList.remove('valid');
        }
        
        // Change border color if exceeding max
        if (length > MAX_CHARS) {
            deletionReason.style.borderColor = '#e53935';
        } else if (length >= MIN_CHARS_FOR_SUBMIT) {
            deletionReason.style.borderColor = '#16a34a';
        } else {
            deletionReason.style.borderColor = '#dee2e6';
        }
    }

    if (deletionReason) {
        deletionReason.addEventListener('input', updateCharCount);
        
        // Prevent pasting more than max characters
        deletionReason.addEventListener('paste', function(e) {
            e.preventDefault();
            const pastedText = (e.clipboardData || window.clipboardData).getData('text');
            const currentLength = this.value.length;
            const availableSpace = MAX_CHARS - currentLength;
            
            if (availableSpace > 0) {
                const textToAdd = pastedText.slice(0, availableSpace);
                this.value = this.value + textToAdd;
                updateCharCount();
            }
        });
        
        // Prevent typing more than max characters
        deletionReason.addEventListener('keydown', function(e) {
            const currentLength = this.value.length;
            if (currentLength >= MAX_CHARS && e.key !== 'Backspace' && e.key !== 'Delete' && !e.ctrlKey && !e.metaKey) {
                e.preventDefault();
                showToast(`Maximum ${formatNumber(MAX_CHARS)} characters reached`, 'error');
            }
        });
    }

    // Open modal
    if (deletionBtn) {
        deletionBtn.addEventListener('click', function() {
            if (deletionBtn.disabled) return;
            
            deletionModal.style.display = 'flex';
            document.body.classList.add('has-modal');
            document.body.style.overflow = 'hidden';
            
            if (deletionReason) {
                deletionReason.value = '';
                updateCharCount();
                
                setTimeout(() => {
                    deletionReason.focus();
                }, 100);
            }
        });
    }

    // Close modal functions
    function closeDeletionModal() {
        if (!deletionModal) return;
        
        deletionModal.style.display = 'none';
        document.body.classList.remove('has-modal');
        document.body.style.overflow = '';
        
        if (deletionForm) {
            deletionForm.reset();
        }
        updateCharCount();
    }

    if (closeBtn) {
        closeBtn.addEventListener('click', closeDeletionModal);
    }
    
    if (cancelBtn) {
        cancelBtn.addEventListener('click', closeDeletionModal);
    }

    // Close when clicking outside
    window.addEventListener('click', function(e) {
        if (e.target === deletionModal) {
            closeDeletionModal();
        }
    });

    // Handle form submission
    if (deletionForm) {
        deletionForm.addEventListener('submit', async function(e) {
            e.preventDefault();

            if (!deletionReason) return;
            
            const reason = deletionReason.value.trim();

            if (reason.length < MIN_CHARS_FOR_SUBMIT) {
                showToast(`Please provide at least ${MIN_CHARS_FOR_SUBMIT} characters`, 'error');
                return;
            }
            
            if (reason.length > MAX_CHARS) {
                showToast(`Maximum ${formatNumber(MAX_CHARS)} characters allowed`, 'error');
                return;
            }

            // Show confirmation modal
            showConfirmationModal(reason);
        });
    }
    
    async function submitDeletionRequest(reason) {
        if (!submitBtn) return;
        
        submitBtn.disabled = true;
        submitBtn.innerHTML = '<span class="button-icon"><span class="spinner"></span> <span>Submitting...</span></span>';

        try {
            const response = await fetch('/student/request-deletion', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    reason: reason
                })
            });

            const data = await response.json();

            if (response.ok) {
                showToast('Deletion request submitted successfully!', 'success');
                closeDeletionModal();
                
                // Update button state
                if (deletionBtn) {
                    deletionBtn.innerHTML = '<span class="btn-icon">⏳</span> Waiting for Deletion Approval';
                    deletionBtn.classList.add('disabled');
                    deletionBtn.disabled = true;
                }
                
                // Add status message
                const statusMsg = document.createElement('p');
                statusMsg.style.cssText = 'text-align: center; color: #f59e0b; font-size: 0.8rem; margin-top: 10px; padding: 8px; background: #fff3e0; border-radius: 6px;';
                statusMsg.textContent = 'Your deletion request is pending admin approval.';
                
                if (deletionBtn && deletionBtn.parentElement && deletionBtn.parentElement.parentElement) {
                    deletionBtn.parentElement.parentElement.appendChild(statusMsg);
                }
                
            } else {
                showToast(data.error || 'Failed to submit request', 'error');
            }
        } catch (error) {
            showToast('An error occurred. Please try again.', 'error');
            console.error('Error:', error);
        } finally {
            if (submitBtn) {
                submitBtn.disabled = false;
                submitBtn.innerHTML = '<span class="button-icon"><span>🗑️</span><span>Submit Request</span></span>';
            }
        }
    }

    function showConfirmationModal(reason) {
        const confirmModal = document.createElement('div');
        confirmModal.className = 'confirm-modal';
        confirmModal.innerHTML = `
            <div class="confirm-content">
                <div class="confirm-icon">⚠️</div>
                <h4 class="confirm-title">Confirm Deletion</h4>
                <p class="confirm-message">Are you absolutely sure you want to request account deletion? This action cannot be undone.</p>
                <div class="confirm-buttons">
                    <button id="confirmYes" class="btn-confirm-yes">Yes, Proceed</button>
                    <button id="confirmNo" class="btn-confirm-no">Cancel</button>
                </div>
            </div>
        `;
        
        document.body.appendChild(confirmModal);
        
        document.getElementById('confirmYes').addEventListener('click', async function() {
            confirmModal.remove();
            await submitDeletionRequest(reason);
        });
        
        document.getElementById('confirmNo').addEventListener('click', function() {
            confirmModal.remove();
        });
    }

    function showToast(message, type) {
        const toastElement = type === 'success' ? toast : toastReject;
        if (!toastElement) return;
        
        toastElement.textContent = (type === 'success' ? '✅ ' : '❌ ') + message;
        toastElement.style.display = 'block';
        
        if (window.innerWidth <= 768) {
            toastElement.style.left = '50%';
            toastElement.style.transform = 'translateX(-50%)';
            toastElement.style.right = 'auto';
        }
        
        setTimeout(() => {
            toastElement.style.display = 'none';
        }, 4000);
    }

    // Handle orientation change
    window.addEventListener('orientationchange', function() {
        if (deletionModal && deletionModal.style.display === 'flex') {
            deletionModal.scrollTop = 0;
        }
    });
});