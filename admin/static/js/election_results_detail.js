// Get template data
const templateData = JSON.parse(document.getElementById('template-data').textContent);
const csrfToken = templateData.csrfToken || document.querySelector('meta[name="csrf-token"]')?.getAttribute('content') || '';

// Initialize event listeners
document.addEventListener('DOMContentLoaded', function() {
    // Initialize tally button
    const tallyBtn = document.getElementById('tallyVotesBtn');
    if (tallyBtn) {
        tallyBtn.addEventListener('click', tallyVotes);
    }

    // Initialize refresh button
    const refreshBtn = document.getElementById('refreshResultsBtn');
    if (refreshBtn) {
        refreshBtn.addEventListener('click', refreshResults);
    }

    // NOTE: Export button now uses direct link, no JavaScript needed
    // The export button in HTML is now an <a> tag, not handled by JS

    // Initialize notification styles
    initializeNotificationStyles();
});

// Tally Votes Function
async function tallyVotes() {
    const electionId = templateData.electionId;
    const tallyBtn = document.getElementById('tallyVotesBtn');
    const originalText = tallyBtn.innerHTML;
    const isTallied = templateData.isTallied;
    
    const message = isTallied 
        ? '⚠️ RE-TALLY CONFIRMATION\n\nAre you sure you want to re-tally all votes?'
        : '✅ OFFICIAL TALLY CONFIRMATION\n\nAre you ready to officially tally the votes?';
    
    if (!confirm(message)) {
        return;
    }
    
    // Show loading
    tallyBtn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Tallying Votes...';
    tallyBtn.disabled = true;
    
    try {
        showNotification('info', isTallied ? 'Re-tallying votes...' : 'Starting official vote tally process...');
        
        const response = await fetch(`/admin/results/${electionId}/tally`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRF-Token': csrfToken
            },
            body: JSON.stringify({ force: true })
        });
        
        const result = await response.json();
        
        if (result.success) {
            showNotification('success', `✅ ${isTallied ? 'Re-tally complete!' : 'Official tally complete!'}`);
            
            setTimeout(() => {
                window.location.reload();
            }, 2000);
            
        } else {
            showNotification('error', `❌ ${result.message || 'Failed to tally votes.'}`);
            tallyBtn.innerHTML = originalText;
            tallyBtn.disabled = false;
        }
        
    } catch (error) {
        console.error('Error tallying votes:', error);
        showNotification('error', '❌ Network error. Please try again.');
        tallyBtn.innerHTML = originalText;
        tallyBtn.disabled = false;
    }
}

// Refresh Results
function refreshResults() {
    const refreshBtn = document.querySelector('.refresh-btn');
    const originalText = refreshBtn.innerHTML;
    
    refreshBtn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Refreshing...';
    refreshBtn.disabled = true;
    
    window.location.reload();
}

// Notification Function
function showNotification(type, message) {
    const existing = document.querySelector('.custom-notification');
    if (existing) existing.remove();
    
    const notification = document.createElement('div');
    notification.className = `custom-notification ${type}`;
    
    let icon = 'fa-info-circle';
    if (type === 'success') icon = 'fa-check-circle';
    if (type === 'error') icon = 'fa-exclamation-circle';
    
    notification.innerHTML = `
        <i class="fa-solid ${icon}"></i>
        <span>${message}</span>
        <button onclick="this.parentElement.remove()">
            <i class="fa-solid fa-times"></i>
        </button>
    `;
    
    document.body.appendChild(notification);
    
    setTimeout(() => {
        if (notification.parentElement) {
            notification.remove();
        }
    }, 5000);
}

// Initialize notification styles
function initializeNotificationStyles() {
    if (!document.querySelector('#notification-styles')) {
        const style = document.createElement('style');
        style.id = 'notification-styles';
        style.textContent = `
            .custom-notification {
                position: fixed;
                top: 20px;
                right: 20px;
                padding: 15px 20px;
                border-radius: 8px;
                display: flex;
                align-items: center;
                gap: 12px;
                z-index: 10000;
                box-shadow: 0 4px 12px rgba(0,0,0,0.15);
                animation: slideIn 0.3s ease;
                max-width: 500px;
                min-width: 300px;
            }
            .custom-notification.success {
                background: #d4edda;
                color: #155724;
                border-left: 4px solid #28a745;
            }
            .custom-notification.error {
                background: #f8d7da;
                color: #721c24;
                border-left: 4px solid #dc3545;
            }
            .custom-notification.info {
                background: #d1ecf1;
                color: #0c5460;
                border-left: 4px solid #17a2b8;
            }
            .custom-notification button {
                background: none;
                border: none;
                color: inherit;
                cursor: pointer;
                padding: 0;
                margin-left: auto;
                opacity: 0.7;
            }
            .custom-notification button:hover {
                opacity: 1;
            }
            @keyframes slideIn {
                from { transform: translateX(100%); opacity: 0; }
                to { transform: translateX(0); opacity: 1; }
            }
        `;
        document.head.appendChild(style);
    }
}