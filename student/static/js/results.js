// results.js - All JavaScript functionality for the results page

document.addEventListener('DOMContentLoaded', function() {
    initializeElectionSelector();
    initializeRefreshButton();
    initializeVerifyButton();
    initializePhotoModal();
    
    // Auto-refresh for live results if needed
    const templateData = getTemplateData();
    if (templateData.resultsStatus && templateData.resultsStatus.includes('LIVE')) {
        // Optional: Add auto-refresh logic here if needed
    }
});

// ==================== CSRF HELPER FUNCTION ====================

function getCsrfToken() {
    const metaTag = document.querySelector('meta[name="csrf-token"]');
    return metaTag ? metaTag.getAttribute('content') : '';
}

// ==================== HELPER FUNCTIONS ====================

function getTemplateData() {
    const script = document.getElementById('template-data');
    if (script) {
        try {
            return JSON.parse(script.textContent);
        } catch (e) {
            console.error('Error parsing template data:', e);
        }
    }
    return { recentElectionId: null, resultsStatus: '' };
}

// ==================== ELECTION SELECTOR ====================

function initializeElectionSelector() {
    const electionSelect = document.getElementById('election-select');
    if (electionSelect) {
        electionSelect.addEventListener('change', function() {
            const electionId = this.value;
            window.location.href = `/student/results/${electionId}`;
        });
    }
}

// ==================== REFRESH FUNCTION ====================

let isRefreshing = false;

function initializeRefreshButton() {
    const refreshBtn = document.getElementById('refreshBtn');
    if (refreshBtn) {
        refreshBtn.addEventListener('click', refreshResults);
    }
}

function refreshResults() {
    if (isRefreshing) return;
    
    const refreshBtn = document.getElementById('refreshBtn');
    const loadingOverlay = document.getElementById('results-loading');
    const templateData = getTemplateData();
    const electionId = templateData.recentElectionId;
    
    if (!electionId) {
        console.error('No election ID available');
        return;
    }
    
    // Show loading state
    isRefreshing = true;
    refreshBtn.classList.add('refreshing');
    refreshBtn.innerHTML = '<span class="loading-spinner"></span> Refreshing...';
    loadingOverlay.classList.add('active');
    
    // Update last updated text
    document.getElementById('last-updated').textContent = 'updating...';
    
    // Fetch fresh results via AJAX
    fetch(`/student/api/refresh-results/${electionId}`, {
        headers: {
            'X-CSRFToken': getCsrfToken()  // ADD CSRF TOKEN
        }
    })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                // Update the results container
                document.getElementById('results-container').innerHTML = data.html;
                
                // Update summary stats
                if (data.summary) {
                    document.getElementById('total-votes').textContent = data.summary.total_votes;
                    document.getElementById('voter-turnout').textContent = data.summary.voter_turnout + '%';
                    document.getElementById('votes-cast').textContent = data.summary.total_votes;
                    
                    // Update turnout chart
                    document.getElementById('turnout-bar').style.width = data.summary.voter_turnout + '%';
                    document.getElementById('current-percentage').textContent = data.summary.voter_turnout + '% Current';
                }
                
                // Update last updated time
                const now = new Date();
                const timeStr = now.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' });
                document.getElementById('last-updated').textContent = timeStr;
            } else {
                console.error('Refresh failed:', data.message);
                document.getElementById('last-updated').textContent = 'refresh failed';
            }
        })
        .catch(error => {
            console.error('Refresh error:', error);
            document.getElementById('last-updated').textContent = 'error';
        })
        .finally(() => {
            // Hide loading state
            isRefreshing = false;
            refreshBtn.classList.remove('refreshing');
            refreshBtn.innerHTML = '<i class="fa fa-sync-alt"></i> Refresh Results';
            loadingOverlay.classList.remove('active');
        });
}

// ==================== VOTE VERIFICATION ====================

let isVerifying = false;

function initializeVerifyButton() {
    const verifyBtn = document.getElementById('verifyBtn');
    if (verifyBtn) {
        verifyBtn.addEventListener('click', verifyVote);
    }
}

function verifyVote() {
    if (isVerifying) return;
    
    const candidateSelect = document.getElementById('candidateSelect');
    const secretCode = document.getElementById('secretCode');
    const verifyBtn = document.getElementById('verifyBtn');
    const resultDiv = document.getElementById('verificationResult');
    const templateData = getTemplateData();
    const electionId = templateData.recentElectionId;
    
    // Validate inputs
    if (!candidateSelect.value) {
        showResult('error', '❌ No Candidate Selected', 'Please select which candidate you voted for.');
        candidateSelect.focus();
        return;
    }
    
    if (!secretCode.value.trim()) {
        showResult('error', '❌ Missing Secret Code', 'Please enter your secret receipt code.');
        secretCode.focus();
        return;
    }
    
    if (!electionId) {
        showResult('error', '❌ Error', 'Election information not available.');
        return;
    }
    
    // Get selected candidate info
    const selectedOption = candidateSelect.options[candidateSelect.selectedIndex];
    const candidateId = candidateSelect.value;
    const candidateName = selectedOption.text.split(' (')[0].trim();
    
    // Show loading state
    isVerifying = true;
    verifyBtn.disabled = true;
    verifyBtn.innerHTML = '<span class="loading-spinner"></span> Verifying...';
    
    resultDiv.className = 'verification-result show';
    resultDiv.innerHTML = `
        <div class="result-icon">⏳</div>
        <div class="result-title">Verifying Your Vote...</div>
        <div class="result-details">
            <p><strong>${candidateName}</strong></p>
            <p>Code: ${secretCode.value.substring(0, 8)}...</p>
            <p><small>Checking blockchain records...</small></p>
        </div>
    `;
    
    // Make AJAX call to verify endpoint
    fetch('/student/verify-my-vote', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': getCsrfToken()  // ADD CSRF TOKEN HERE
        },
        body: JSON.stringify({
            election_id: electionId,
            candidate_id: candidateId,
            secret_code: secretCode.value.trim()
        })
    })
    .then(response => {
        if (!response.ok) {
            throw new Error('Network response was not ok');
        }
        return response.json();
    })
    .then(data => {
        if (data.success) {
            showResult('success', 'VOTE VERIFIED!', 
                `Your vote for <strong>${data.candidate_name || candidateName}</strong> has been verified!`,
                data);
        } else {
            showResult('error', 'VERIFICATION FAILED', 
                data.message || 'No matching record found. Please check your code and try again.');
        }
    })
    .catch(error => {
        console.error('Verification error:', error);
        showResult('error', 'Verification Error', 
            'An error occurred. Please try again later.');
    })
    .finally(() => {
        isVerifying = false;
        verifyBtn.disabled = false;
        verifyBtn.innerHTML = '<i class="fa fa-check-circle"></i> Verify My Vote';
    });
}

function showResult(type, title, message, data = null) {
    const resultDiv = document.getElementById('verificationResult');
    
    let icon = type === 'success' ? '✅' : '❌';
    
    let html = `
        <div class="result-icon">${icon}</div>
        <div class="result-title">${title}</div>
        <div class="result-details">${message}</div>
    `;
    
    if (type === 'success' && data) {
        html += `
            <div class="result-hash">
                <small>Transaction ID:</small><br>
                ${data.hash || 'Verified'}
            </div>
            <div class="result-footer">
                <i class="fa fa-lock"></i> Verified at ${data.timestamp || new Date().toLocaleTimeString()}
            </div>
        `;
    }
    
    resultDiv.className = `verification-result show ${type}`;
    resultDiv.innerHTML = html;
    
    // Scroll to result
    resultDiv.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
}

// ==================== PHOTO MODAL ====================

function initializePhotoModal() {
    // Close modal with close button
    const closeBtn = document.getElementById('closePhotoModalBtn');
    if (closeBtn) {
        closeBtn.addEventListener('click', closePhotoModal);
    }
    
    // Close modal with Escape key
    document.addEventListener('keydown', function(e) {
        if (e.key === 'Escape') {
            closePhotoModal();
        }
    });
    
    // Close modal when clicking outside
    const modal = document.getElementById('photoModal');
    if (modal) {
        modal.addEventListener('click', function(e) {
            if (e.target === this) {
                closePhotoModal();
            }
        });
    }
}

function openCandidatePhoto(element) {
    const modal = document.getElementById('photoModal');
    const modalImg = document.getElementById('photoModalImg');
    const modalCaption = document.getElementById('photoModalCaption');
    
    const photoUrl = element.getAttribute('data-photo-url');
    const candidateName = element.getAttribute('data-candidate-name');
    
    modalImg.src = photoUrl;
    modalCaption.textContent = candidateName;
    
    modal.style.display = 'flex';
    document.body.style.overflow = 'hidden';
}

function closePhotoModal() {
    const modal = document.getElementById('photoModal');
    modal.style.display = 'none';
    document.body.style.overflow = 'auto';
}

// Make functions available globally for onclick handlers
window.openCandidatePhoto = openCandidatePhoto;
window.closePhotoModal = closePhotoModal;