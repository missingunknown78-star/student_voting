// student_validation.js - Student validation for candidate management

// CSRF Token Helper Function
function getCsrfToken() {
    const metaTag = document.querySelector('meta[name="csrf-token"]');
    return metaTag ? metaTag.getAttribute('content') : '';
}

// Initialize student validation
function initStudentValidation() {
    console.log("Student validation initialized");
    
    const firstNameInput = document.getElementById('add_first_name');
    const lastNameInput = document.getElementById('add_last_name');
    const courseSelect = document.getElementById('add_course');
    
    if (firstNameInput) {
        firstNameInput.addEventListener('blur', validateStudent);
        firstNameInput.addEventListener('input', clearValidationMessage);
    }
    
    if (lastNameInput) {
        lastNameInput.addEventListener('blur', validateStudent);
        lastNameInput.addEventListener('input', clearValidationMessage);
    }
    
    if (courseSelect) {
        courseSelect.addEventListener('change', validateStudent);
    }
}

// Clear validation message when user starts typing again
function clearValidationMessage() {
    // Remove any floating notifications
    const existingNotification = document.querySelector('.floating-validation-notification');
    if (existingNotification) {
        existingNotification.remove();
    }
}

// Validate student existence in database
function validateStudent() {
    const firstName = document.getElementById('add_first_name')?.value.trim();
    const lastName = document.getElementById('add_last_name')?.value.trim();
    const courseId = document.getElementById('add_course')?.value;
    
    // Remove any existing floating notifications
    const existingNotification = document.querySelector('.floating-validation-notification');
    if (existingNotification) {
        existingNotification.remove();
    }
    
    // Only validate if we have at least first name and last name
    if (!firstName || !lastName) {
        return Promise.resolve(null);
    }
    
    // Build URL with query parameters
    let url = `/admin/validate-student?first_name=${encodeURIComponent(firstName)}&last_name=${encodeURIComponent(lastName)}`;
    if (courseId) {
        url += `&course_id=${courseId}`;
    }
    
    return fetch(url, {
        method: 'GET',
        headers: {
            'X-Requested-With': 'XMLHttpRequest',
            'X-CSRFToken': getCsrfToken()
        }
    })
    .then(res => {
        if (!res.ok) {
            throw new Error('Network response was not ok');
        }
        return res.json();
    })
    .then(data => {
        if (data.exists) {
            // Student exists - show floating success message
            showFloatingNotification('✓ Student verified!', 'success');
            return true;
        } else {
            // Student doesn't exist - show simple error message
            showFloatingNotification('✗ Student not found in registered student database. They should register first.', 'error');
            return false;
        }
    })
    .catch(err => {
        console.error('Error validating student:', err);
        showFloatingNotification('Error validating student', 'error');
        return false;
    });
}

// Show floating notification above the modal
function showFloatingNotification(message, type) {
    // Remove any existing floating notifications
    const existingNotification = document.querySelector('.floating-validation-notification');
    if (existingNotification) {
        existingNotification.remove();
    }
    
    // Create floating notification element
    const notification = document.createElement('div');
    notification.className = `floating-validation-notification ${type}`;
    
    // Add icon based on type
    const icon = type === 'success' ? 'fa-check-circle' : 'fa-exclamation-circle';
    
    notification.innerHTML = `
        <div class="notification-content">
            <i class="fa ${icon}"></i>
            <div class="notification-message">${message}</div>
            <button class="notification-close" onclick="this.parentElement.parentElement.remove()">
                <i class="fa fa-times"></i>
            </button>
        </div>
    `;
    
    // Style the notification
    notification.style.cssText = `
        position: fixed;
        top: 80px;
        left: 50%;
        transform: translateX(-50%);
        z-index: 10000;
        min-width: 300px;
        max-width: 400px;
        animation: slideDown 0.3s ease-out;
        box-shadow: 0 10px 25px rgba(0,0,0,0.2);
        border-radius: 8px;
        overflow: hidden;
    `;
    
    // Style the content based on type
    const colors = type === 'success' 
        ? { bg: 'linear-gradient(135deg, #00c851, #00a844)', border: '#007e33' }
        : { bg: 'linear-gradient(135deg, #ff4444, #cc0000)', border: '#a70000' };
    
    notification.querySelector('.notification-content').style.cssText = `
        display: flex;
        align-items: center;
        gap: 12px;
        padding: 12px 20px;
        background: ${colors.bg};
        color: white;
        font-size: 0.95rem;
        font-weight: 500;
        border-left: 5px solid ${colors.border};
        text-shadow: 0 1px 2px rgba(0,0,0,0.1);
    `;
    
    // Style the close button
    const closeBtn = notification.querySelector('.notification-close');
    closeBtn.style.cssText = `
        background: none;
        border: none;
        color: white;
        cursor: pointer;
        font-size: 1.2rem;
        margin-left: auto;
        padding: 0 5px;
        opacity: 0.8;
        transition: opacity 0.2s;
    `;
    closeBtn.onmouseover = () => closeBtn.style.opacity = '1';
    closeBtn.onmouseout = () => closeBtn.style.opacity = '0.8';
    
    // Style the icon
    notification.querySelector('i:first-child').style.cssText = `
        font-size: 1.3rem;
        filter: drop-shadow(0 2px 4px rgba(0,0,0,0.2));
    `;
    
    // Style the message
    notification.querySelector('.notification-message').style.cssText = `
        flex: 1;
        line-height: 1.4;
    `;
    
    document.body.appendChild(notification);
    
    // Auto hide after 3 seconds
    setTimeout(() => {
        if (notification.parentNode) {
            notification.style.animation = 'slideUp 0.3s ease-out forwards';
            setTimeout(() => {
                if (notification.parentNode) {
                    notification.remove();
                }
            }, 300);
        }
    }, 3000);
}

// Validate before form submission
async function validateBeforeSubmit() {
    const result = await validateStudent();
    if (result === false) {
        showFloatingNotification('Student must register first before becoming a candidate', 'error');
        return false;
    }
    return true;
}

// Add animation styles if they don't exist
(function addAnimationStyles() {
    if (document.getElementById('floating-notification-styles')) {
        return;
    }
    
    const style = document.createElement('style');
    style.id = 'floating-notification-styles';
    style.textContent = `
        @keyframes slideDown {
            from {
                transform: translate(-50%, -20px);
                opacity: 0;
            }
            to {
                transform: translate(-50%, 0);
                opacity: 1;
            }
        }
        
        @keyframes slideUp {
            from {
                transform: translate(-50%, 0);
                opacity: 1;
            }
            to {
                transform: translate(-50%, -20px);
                opacity: 0;
            }
        }
        
        .floating-validation-notification {
            pointer-events: all;
        }
        
        .floating-validation-notification .notification-content {
            backdrop-filter: blur(5px);
        }
    `;
    document.head.appendChild(style);
})();

// Make functions available globally
window.initStudentValidation = initStudentValidation;
window.validateBeforeSubmit = validateBeforeSubmit;
window.validateStudent = validateStudent;

// Auto-initialize when DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    // Small delay to ensure manage_candidates.js has loaded first
    setTimeout(initStudentValidation, 500);
});