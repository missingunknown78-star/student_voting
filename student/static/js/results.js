// results.js - All JavaScript functionality for the results page

document.addEventListener('DOMContentLoaded', function() {
    initializeElectionSelector();
    initializeRefreshButton();
    initializeVerifyButton();
    initializePhotoModal();
});

// ==================== HELPER FUNCTIONS ====================

function getTemplateData() {
    // This function expects a script tag with id 'template-data' to exist
    // If not, return default values
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
            if (electionId) {
                window.location.href = `/student/results/${electionId}`;
            }
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
        // Optional: show user feedback
        if (refreshBtn) {
            const originalText = refreshBtn.innerHTML;
            refreshBtn.innerHTML = '<i class="fa fa-exclamation-triangle"></i> No Election Selected';
            setTimeout(() => {
                refreshBtn.innerHTML = originalText;
            }, 2000);
        }
        return;
    }
    
    // Show loading state
    isRefreshing = true;
    if (refreshBtn) {
        refreshBtn.classList.add('refreshing');
        refreshBtn.innerHTML = '<span class="loading-spinner"></span> Refreshing...';
    }
    if (loadingOverlay) loadingOverlay.classList.add('active');
    
    // Update last updated text
    const lastUpdated = document.getElementById('last-updated');
    if (lastUpdated) lastUpdated.textContent = 'updating...';
    
    // Fetch fresh results via AJAX
    fetch(`/student/api/refresh-results/${electionId}`)
        .then(response => {
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}`);
            }
            return response.json();
        })
        .then(data => {
            if (data.success) {
                // Update the results container
                const resultsContainer = document.getElementById('results-container');
                if (resultsContainer) resultsContainer.innerHTML = data.html;
                
                // Update summary stats
                if (data.summary) {
                    const totalVotes = document.getElementById('total-votes');
                    const voterTurnout = document.getElementById('voter-turnout');
                    const votesCast = document.getElementById('votes-cast');
                    const turnoutBar = document.getElementById('turnout-bar');
                    const currentPercentage = document.getElementById('current-percentage');
                    
                    if (totalVotes) totalVotes.textContent = data.summary.total_votes;
                    if (voterTurnout) voterTurnout.textContent = data.summary.voter_turnout + '%';
                    if (votesCast) votesCast.textContent = data.summary.total_votes;
                    if (turnoutBar) turnoutBar.style.width = data.summary.voter_turnout + '%';
                    if (currentPercentage) currentPercentage.textContent = data.summary.voter_turnout + '% Current';
                }
                
                // Update last updated time
                const now = new Date();
                const timeStr = now.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' });
                if (lastUpdated) lastUpdated.textContent = timeStr;
            } else {
                console.error('Refresh failed:', data.message);
                if (lastUpdated) lastUpdated.textContent = 'refresh failed';
            }
        })
        .catch(error => {
            console.error('Refresh error:', error);
            if (lastUpdated) lastUpdated.textContent = 'error';
        })
        .finally(() => {
            // Hide loading state
            isRefreshing = false;
            if (refreshBtn) {
                refreshBtn.classList.remove('refreshing');
                refreshBtn.innerHTML = '<i class="fa fa-sync-alt"></i> Refresh Results';
            }
            if (loadingOverlay) loadingOverlay.classList.remove('active');
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
    if (!candidateSelect || !candidateSelect.value) {
        showResult('error', '❌ No Candidate Selected', 'Please select which candidate you voted for.');
        if (candidateSelect) candidateSelect.focus();
        return;
    }
    
    if (!secretCode || !secretCode.value.trim()) {
        showResult('error', '❌ Missing Secret Code', 'Please enter your secret receipt code.');
        if (secretCode) secretCode.focus();
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
    if (verifyBtn) {
        verifyBtn.disabled = true;
        verifyBtn.innerHTML = '<span class="loading-spinner"></span> Verifying...';
    }
    
    if (resultDiv) {
        resultDiv.className = 'verification-result show';
        resultDiv.innerHTML = `
            <div class="result-icon">⏳</div>
            <div class="result-title">Verifying Your Vote...</div>
            <div class="result-details">
                <p><strong>${escapeHtml(candidateName)}</strong></p>
                <p>Code: ${escapeHtml(secretCode.value.substring(0, 8))}...</p>
                <p><small>Checking blockchain records...</small></p>
            </div>
        `;
    }
    
    // Make AJAX call to verify endpoint
    fetch('/student/verify-my-vote', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
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
                `Your vote for <strong>${escapeHtml(data.candidate_name || candidateName)}</strong> has been verified!`,
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
        if (verifyBtn) {
            verifyBtn.disabled = false;
            verifyBtn.innerHTML = '<i class="fa fa-check-circle"></i> Verify My Vote';
        }
    });
}

function showResult(type, title, message, data = null) {
    const resultDiv = document.getElementById('verificationResult');
    if (!resultDiv) return;
    
    let icon = type === 'success' ? '✅' : '❌';
    
    let html = `
        <div class="result-icon">${icon}</div>
        <div class="result-title">${escapeHtml(title)}</div>
        <div class="result-details">${message}</div>
    `;
    
    if (type === 'success' && data) {
        html += `
            <div class="result-hash">
                <small>Transaction ID:</small><br>
                ${escapeHtml(data.hash || 'Verified')}
            </div>
            <div class="result-footer">
                <i class="fa fa-lock"></i> Verified at ${escapeHtml(data.timestamp || new Date().toLocaleTimeString())}
            </div>
        `;
    }
    
    resultDiv.className = `verification-result show ${type}`;
    resultDiv.innerHTML = html;
    
    // Scroll to result
    resultDiv.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
}

// Helper function to escape HTML
function escapeHtml(text) {
    if (!text) return '';
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
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
    
    if (!modal || !modalImg) return;
    
    const photoUrl = element.getAttribute('data-photo-url');
    const candidateName = element.getAttribute('data-candidate-name');
    
    modalImg.src = photoUrl;
    if (modalCaption) modalCaption.textContent = candidateName;
    
    modal.style.display = 'flex';
    document.body.style.overflow = 'hidden';
}

function closePhotoModal() {
    const modal = document.getElementById('photoModal');
    if (modal) {
        modal.style.display = 'none';
    }
    document.body.style.overflow = 'auto';
}

// Make functions available globally for onclick handlers
window.openCandidatePhoto = openCandidatePhoto;
window.closePhotoModal = closePhotoModal;