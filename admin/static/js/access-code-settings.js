// access-code-settings.js - Access Code Management (Simplified)

// ==================== CSRF TOKEN HELPER ====================
function getCsrfToken() {
    const metaTag = document.querySelector('meta[name="csrf-token"]');
    return metaTag ? metaTag.getAttribute('content') : '';
}

// ==================== ACCESS CODE MANAGER ====================
const AccessCodeManager = {
    // State
    isCodeVisible: false,
    
    // Initialize
    init: function() {
        console.log('AccessCodeManager initializing...');
        this.loadCurrentCode();
        this.setupEventListeners();
    },
    
    // Setup event listeners
    setupEventListeners: function() {
        // Real-time code matching
        const newCode = document.getElementById('newAccessCode');
        const confirmCode = document.getElementById('confirmAccessCode');
        
        if (newCode && confirmCode) {
            newCode.addEventListener('input', () => {
                this.checkCodeMatch();
            });
            confirmCode.addEventListener('input', () => this.checkCodeMatch());
        }
    },
    
    // Load current code from hidden element
    loadCurrentCode: function() {
        const actualCodeElement = document.getElementById('actualAccessCode');
        if (actualCodeElement && actualCodeElement.textContent) {
            window.actualAccessCode = actualCodeElement.textContent;
        }
    },
    
    // Toggle code visibility
    toggleVisibility: function() {
        const codeDisplay = document.getElementById('currentAccessCode');
        const icon = document.getElementById('codeVisibilityIcon');
        const actualCode = window.actualAccessCode || '';
        
        if (!codeDisplay || !icon) return;
        
        this.isCodeVisible = !this.isCodeVisible;
        
        if (this.isCodeVisible) {
            // Show actual code
            codeDisplay.textContent = actualCode || 'No code set';
            icon.className = 'fa-solid fa-eye-slash';
        } else {
            // Show masked code
            if (actualCode) {
                const masked = '*'.repeat(actualCode.length - 4) + actualCode.slice(-4);
                codeDisplay.textContent = masked;
            } else {
                codeDisplay.textContent = 'No access code set';
            }
            icon.className = 'fa-solid fa-eye';
        }
    },
    
    // Check if codes match in real-time
    checkCodeMatch: function() {
        const newCode = document.getElementById('newAccessCode');
        const confirmCode = document.getElementById('confirmAccessCode');
        const messageDiv = document.getElementById('codeMatchMessage');
        
        if (!newCode || !confirmCode || !messageDiv) return;
        
        const newVal = newCode.value.trim();
        const confirmVal = confirmCode.value.trim();
        
        if (confirmVal.length === 0) {
            messageDiv.innerHTML = '';
            messageDiv.className = 'validation-message';
            return;
        }
        
        if (newVal === confirmVal) {
            messageDiv.innerHTML = '<i class="fa-solid fa-check-circle"></i> Codes match!';
            messageDiv.className = 'validation-message success';
        } else {
            messageDiv.innerHTML = '<i class="fa-solid fa-exclamation-circle"></i> Codes do not match';
            messageDiv.className = 'validation-message error';
        }
    },
    
    // Update access code
    updateCode: async function(event) {
        event.preventDefault();
        
        const newCode = document.getElementById('newAccessCode');
        const confirmCode = document.getElementById('confirmAccessCode');
        const updateBtn = document.getElementById('updateAccessCodeBtn');
        
        // Validate
        if (!newCode.value.trim() || !confirmCode.value.trim()) {
            this.showNotification('Please fill in all fields', 'error');
            return false;
        }
        
        if (newCode.value.trim() !== confirmCode.value.trim()) {
            this.showNotification('Access codes do not match', 'error');
            return false;
        }
        
        if (newCode.value.trim().length < 4) {
            this.showNotification('Access code must be at least 4 characters long', 'error');
            return false;
        }
        
        // Show loading state
        const originalText = updateBtn.innerHTML;
        updateBtn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Updating...';
        updateBtn.disabled = true;
        
        // Prepare data
        const data = {
            access_code: newCode.value.trim()
        };
        
        try {
            // 🔴 FIXED: Added /ctumoalboal-comelec prefix
            const url = '/ctumoalboal-comelec/settings/access-code/update';
            console.log('Fetching URL:', url);
            
            const response = await fetch(url, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': getCsrfToken()
                },
                body: JSON.stringify(data)
            });
            
            const result = await response.json();
            
            if (result.success) {
                this.showNotification(result.message || 'Access code updated successfully!', 'success');
                
                // Update displayed code
                window.actualAccessCode = newCode.value.trim();
                this.isCodeVisible = false; // Reset to masked
                
                // Update the display
                const codeDisplay = document.getElementById('currentAccessCode');
                const icon = document.getElementById('codeVisibilityIcon');
                if (codeDisplay && icon) {
                    const masked = '*'.repeat(newCode.value.trim().length - 4) + newCode.value.trim().slice(-4);
                    codeDisplay.textContent = masked;
                    icon.className = 'fa-solid fa-eye';
                }
                
                // Clear form
                this.clearForm();
            } else {
                this.showNotification(result.message || 'Failed to update access code', 'error');
            }
        } catch (error) {
            console.error('Error updating access code:', error);
            this.showNotification('Network error. Please try again.', 'error');
        } finally {
            // Restore button
            updateBtn.innerHTML = originalText;
            updateBtn.disabled = false;
        }
        
        return false;
    },
    
    // Clear form
    clearForm: function() {
        const newCode = document.getElementById('newAccessCode');
        const confirmCode = document.getElementById('confirmAccessCode');
        const messageDiv = document.getElementById('codeMatchMessage');
        
        if (newCode) newCode.value = '';
        if (confirmCode) confirmCode.value = '';
        if (messageDiv) {
            messageDiv.innerHTML = '';
            messageDiv.className = 'validation-message';
        }
    },
    
    // Show notification
    showNotification: function(message, type = 'info') {
        // Use existing notification system or create one
        if (typeof window.showNotification === 'function') {
            window.showNotification(message, type);
        } else {
            alert(message); // Fallback
        }
    }
};

// ==================== GLOBAL FUNCTIONS FOR HTML CALLS ====================

// Toggle code visibility
function toggleCodeVisibility() {
    AccessCodeManager.toggleVisibility();
}

// Update access code
function updateAccessCode(event) {
    return AccessCodeManager.updateCode(event);
}

// Clear form
function clearAccessCodeForm() {
    AccessCodeManager.clearForm();
}

// Initialize on page load
document.addEventListener('DOMContentLoaded', function() {
    // Add to window for global access
    window.accessCodeManager = AccessCodeManager;
    AccessCodeManager.init();
});

// Export for module usage if needed
if (typeof module !== 'undefined' && module.exports) {
    module.exports = AccessCodeManager;
}