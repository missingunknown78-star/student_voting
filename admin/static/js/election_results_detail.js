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

    // Initialize print button
    const printBtn = document.getElementById('printResultsBtn');
    if (printBtn) {
        printBtn.addEventListener('click', () => window.print());
    }

    // Initialize notification styles
    initializeNotificationStyles();
});

// Tally Votes Function
async function tallyVotes() {
    const electionId = templateData.electionId;
    const tallyBtn = document.getElementById('tallyVotesBtn');
    const originalText = tallyBtn.innerHTML;
    const isTallied = templateData.isTallied;
    
    // Confirmation dialog based on state
    const message = isTallied 
        ? '⚠️ RE-TALLY CONFIRMATION\n\nAre you sure you want to re-tally all votes?\n\nThis will recount all encrypted votes and update the official results.\n\nNote: This is only necessary if you suspect tally errors.'
        : '✅ OFFICIAL TALLY CONFIRMATION\n\nAre you ready to officially tally the votes?\n\nThis will:\n1. Decrypt and count all votes from the Vote table\n2. Store final results in the TallyVote table\n3. Mark results as "Officially Tallied"\n\nMake sure the election has ended before proceeding.';
    
    if (!confirm(message)) {
        return;
    }
    
    // Check if election is active
    const electionStatus = templateData.status;
    if (electionStatus === 'Active' && !isTallied) {
        const forceConfirm = confirm('⚠️ ELECTION IS STILL ACTIVE!\n\nVoting is still ongoing. Are you sure you want to tally votes now?\n\nThis will create official results while voting continues, which is not recommended.\n\nPress OK to force tally, Cancel to abort.');
        if (!forceConfirm) {
            return;
        }
    }
    
    // Show loading
    tallyBtn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Tallying Votes...';
    tallyBtn.disabled = true;
    
    try {
        showNotification('info', isTallied ? 'Re-tallying votes...' : 'Starting official vote tally process...');
        
        // Call API
        const response = await fetch(`/admin/results/${electionId}/tally`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRF-Token': csrfToken
            },
            body: JSON.stringify({
                force: true
            })
        });
        
        const result = await response.json();
        
        if (result.success) {
            const details = result.data ? 
                `Processed ${result.data.total_votes} votes for ${result.data.candidates_tallied} candidates.` : 
                'Votes tallied successfully.';
            
            showNotification('success', `✅ ${isTallied ? 'Re-tally complete!' : 'Official tally complete!'} ${details}`);
            
            // Update display immediately
            const tallyStatusElement = document.getElementById('tallyStatus');
            tallyStatusElement.textContent = 'Officially Tallied';
            tallyStatusElement.style.color = '#28a745';
            
            // Update button text
            tallyBtn.innerHTML = '<i class="fa-solid fa-calculator"></i> Re-tally Votes';
            
            // Refresh page to show final results state
            showNotification('info', 'Page will refresh to show official results...');
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
        showNotification('error', '❌ Network error. Please check your connection and try again.');
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
    
    const isTallied = templateData.isTallied;
    showNotification('info', isTallied ? 'Refreshing official results...' : 'Refreshing live results...');
    
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
    if (type === 'info') icon = 'fa-info-circle';
    
    notification.innerHTML = `
        <i class="fa-solid ${icon}"></i>
        <span>${message}</span>
        <button onclick="this.parentElement.remove()">
            <i class="fa-solid fa-times"></i>
        </button>
    `;
    
    document.body.appendChild(notification);
    
    const duration = type === 'error' ? 8000 : 5000;
    setTimeout(() => {
        if (notification.parentElement) {
            notification.remove();
        }
    }, duration);
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
                transition: opacity 0.2s;
            }
            
            .custom-notification button:hover {
                opacity: 1;
            }
            
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
            
            /* Additional CSS for voter turnout */
            .turnout-breakdown {
                display: flex;
                justify-content: space-between;
                margin-top: 15px;
                padding-top: 15px;
                border-top: 1px solid #e2e8f0;
            }
            
            .turnout-item {
                text-align: center;
                flex: 1;
            }
            
            .turnout-label {
                display: block;
                font-size: 12px;
                color: #718096;
                margin-bottom: 4px;
            }
            
            .turnout-value {
                display: block;
                font-weight: 600;
                color: #2d3748;
            }
            
            .pending-text {
                color: #6c757d;
                font-style: italic;
                font-size: 18px;
            }
            
            .tally-status-text {
                color: ${templateData.isTallied ? '#28a745' : '#17a2b8'};
            }
            
            /* Print-specific styles */
            @media print {
                .back-button,
                .tally-control-section,
                .export-actions,
                .refresh-btn,
                .tally-btn {
                    display: none !important;
                }
                
                .results-detail-container {
                    padding: 0;
                    margin: 0;
                }
                
                .election-header {
                    text-align: center;
                    border-bottom: 2px solid #000;
                    padding-bottom: 20px;
                    margin-bottom: 20px;
                }
                
                .encryption-note,
                .live-results-note {
                    background: #f8f9fa;
                    border: 1px solid #dee2e6;
                    padding: 10px;
                    margin: 10px 0;
                    font-size: 12px;
                }
                
                .results-summary {
                    display: flex;
                    justify-content: space-between;
                    margin: 20px 0;
                }
                
                .summary-card {
                    text-align: center;
                    flex: 1;
                }
                
                .candidates-table {
                    font-size: 11px;
                }
                
                .candidate-photo,
                .default-avatar {
                    display: none;
                }
            }
        `;
        document.head.appendChild(style);
    }
}