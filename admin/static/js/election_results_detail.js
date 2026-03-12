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

    // Initialize PDF export button with direct download
    const pdfBtn = document.getElementById('exportPdfBtn');
    if (pdfBtn) {
        pdfBtn.addEventListener('click', function(e) {
            e.preventDefault();
            exportToPDF();
        });
    }

    // Initialize notification styles
    initializeNotificationStyles();
});

// In your election_results_detail.js
function exportToPDF() {
    const electionId = templateData.electionId;
    const isTallied = templateData.isTallied; // Make sure this is passed from template
    
    // Check if tallied first
    if (!isTallied) {
        showNotification('error', '❌ PDF results are only available after official tally. Please tally the votes first.');
        return;
    }
    
    const pdfBtn = document.getElementById('exportPdfBtn');
    const originalText = pdfBtn.innerHTML;
    
    // Show loading state
    pdfBtn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Generating PDF...';
    pdfBtn.disabled = true;
    
    // Show loading overlay
    const overlay = document.getElementById('pdfLoadingOverlay');
    if (overlay) overlay.style.display = 'flex';
    
    // Fetch PDF
    fetch(`/admin/results/${electionId}/pdf`, {
        method: 'GET',
        headers: {
            'X-Requested-With': 'XMLHttpRequest'
        }
    })
    .then(response => {
        if (!response.ok) {
            if (response.status === 403) {
                throw new Error('PDF not available until election is tallied');
            }
            throw new Error('Network response was not ok');
        }
        return response.blob();
    })
    .then(blob => {
        // Download PDF (same as before)
        const url = window.URL.createObjectURL(blob);
        const link = document.createElement('a');
        link.href = url;
        link.download = `${templateData.electionTitle.replace(/[^a-z0-9]/gi, '_')}_Official_Results.pdf`;
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
        
        setTimeout(() => window.URL.revokeObjectURL(url), 100);
        
        showNotification('success', '✅ Official results PDF downloaded successfully!');
    })
    .catch(error => {
        console.error('Error:', error);
        showNotification('error', error.message || '❌ Failed to generate PDF.');
    })
    .finally(() => {
        pdfBtn.innerHTML = originalText;
        pdfBtn.disabled = false;
        if (overlay) overlay.style.display = 'none';
    });
}

// Tally Votes Function
async function tallyVotes() {
    const electionId = templateData.electionId;
    const tallyBtn = document.getElementById('tallyVotesBtn');
    const originalText = tallyBtn.innerHTML;
    const isTallied = templateData.isTallied;
    
    const message = isTallied 
        ? '⚠️ RE-TALLY CONFIRMATION\n\nAre you sure you want to re-tally all votes? This will update the official results.'
        : '✅ OFFICIAL TALLY CONFIRMATION\n\nAre you ready to officially tally the votes? This action cannot be undone.';
    
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
                to { transform: translateX(0%); opacity: 1; }
            }
            
            /* PDF Loading Overlay */
            .pdf-loading-overlay {
                display: none;
                position: fixed;
                top: 0;
                left: 0;
                width: 100%;
                height: 100%;
                background: rgba(0, 0, 0, 0.8);
                z-index: 9999;
                justify-content: center;
                align-items: center;
            }
            
            .pdf-loading-content {
                background: white;
                padding: 30px 40px;
                border-radius: 12px;
                text-align: center;
                box-shadow: 0 10px 40px rgba(0,0,0,0.2);
                animation: fadeIn 0.3s ease;
            }
            
            .pdf-loading-spinner {
                border: 4px solid #f3f3f3;
                border-top: 4px solid #3498db;
                border-right: 4px solid #3498db;
                border-radius: 50%;
                width: 50px;
                height: 50px;
                animation: spin 1s linear infinite;
                margin: 0 auto 20px;
            }
            
            .pdf-loading-content p {
                color: #2c3e50;
                font-size: 16px;
                margin: 0;
                font-weight: 500;
            }
            
            @keyframes spin {
                0% { transform: rotate(0deg); }
                100% { transform: rotate(360deg); }
            }
            
            @keyframes fadeIn {
                from { opacity: 0; transform: translateY(-20px); }
                to { opacity: 1; transform: translateY(0); }
            }
        `;
        document.head.appendChild(style);
    }
}