// Get template data
const templateData = JSON.parse(document.getElementById('template-data').textContent);
// CSRF token removed - CSRF protection disabled

// ==================== VOTE BADGE TRACKING ====================
let previousCandidateVotes = {}; // Store per-candidate vote counts
let previousTotalVoters = 0;
let newVotesCheckInterval = null;
let activeBadges = {}; // Track active badges and their timeouts

// Store vote counts when page loads
document.addEventListener('DOMContentLoaded', function() {
    // Store initial per-candidate vote counts from data attributes
    const candidateRows = document.querySelectorAll('.candidate-row');
    candidateRows.forEach((row, index) => {
        const candidateId = row.dataset.candidateId;
        const candidateName = row.dataset.candidateName;
        const candidatePosition = row.dataset.candidatePosition;
        const voteCount = parseInt(row.dataset.voteCount) || 0;
        
        if (candidateId) {
            previousCandidateVotes[candidateId] = {
                id: candidateId,
                name: candidateName,
                position: candidatePosition,
                votes: voteCount,
                index: index,
                row: row
            };
        }
    });
    
    console.log('Initial candidate votes:', previousCandidateVotes);
    
    // Store total voters
    const totalVotersElement = document.querySelector('.summary-card.voters .summary-number');
    if (totalVotersElement) {
        previousTotalVoters = parseInt(totalVotersElement.textContent) || 0;
    }
    
    // Check for new votes every 10 seconds only if not tallied
    if (!templateData.isTallied) {
        // Clear any existing interval
        if (newVotesCheckInterval) {
            clearInterval(newVotesCheckInterval);
        }
        // Check immediately
        checkForNewVotes();
        // Then set interval
        newVotesCheckInterval = setInterval(checkForNewVotes, 10000); // Check every 10 seconds
    }
});

function checkForNewVotes() {
    const electionId = templateData.electionId;
    
    console.log('Checking for new votes...');
    
    fetch(`/ctumoalboal-comelec/results/${electionId}/check-new-votes`, {
        method: 'GET',
        headers: {
            'X-Requested-With': 'XMLHttpRequest'
            // REMOVED: 'X-CSRFToken': csrfToken
        }
    })
    .then(response => response.json())
    .then(data => {
        console.log('Received data:', data);
        
        if (data.success) {
            const currentTotalVoters = data.total_voters;
            const newVotes = currentTotalVoters - previousTotalVoters;
            
            if (newVotes > 0) {
                // Find which candidates got new votes
                const candidatesWithNewVotes = [];
                
                if (data.candidate_results) {
                    data.candidate_results.forEach(currentCandidate => {
                        const prevCandidate = previousCandidateVotes[currentCandidate.id];
                        
                        if (prevCandidate) {
                            const newVotesForCandidate = currentCandidate.vote_count - prevCandidate.votes;
                            
                            if (newVotesForCandidate > 0) {
                                candidatesWithNewVotes.push({
                                    id: currentCandidate.id,
                                    name: prevCandidate.name,
                                    position: prevCandidate.position,
                                    new_votes: newVotesForCandidate
                                });
                            }
                        }
                    });
                }
                
                console.log('Candidates with new votes:', candidatesWithNewVotes);
                
                // Show vote badges on candidate profiles
                showVoteBadges(candidatesWithNewVotes);
                
                // Update the stored counts
                previousTotalVoters = currentTotalVoters;
                
                // Update the display without page reload
                updateLiveResults(data);
                
                // Update stored candidate votes
                updateStoredCandidateVotes(data.candidate_results);
            }
        }
    })
    .catch(error => console.error('Error checking for new votes:', error));
}

function showVoteBadges(candidatesWithNewVotes) {
    candidatesWithNewVotes.forEach(candidate => {
        const badgeContainer = document.getElementById(`vote-badge-${candidate.id}`);
        
        if (badgeContainer) {
            // Clear any existing badge and its timeout
            if (activeBadges[candidate.id]) {
                clearTimeout(activeBadges[candidate.id].timeout);
                badgeContainer.innerHTML = '';
            }
            
            // Create new badge
            const badge = document.createElement('div');
            badge.className = 'vote-badge';
            badge.innerHTML = `+${candidate.new_votes}`;
            
            // Add to container
            badgeContainer.appendChild(badge);
            
            // Trigger animation
            setTimeout(() => {
                badge.classList.add('show');
            }, 10);
            
            // Set timeout to remove after 20 seconds
            const timeout = setTimeout(() => {
                badge.classList.remove('show');
                badge.classList.add('hide');
                
                // Remove from DOM after animation
                setTimeout(() => {
                    if (badgeContainer) {
                        badgeContainer.innerHTML = '';
                    }
                    delete activeBadges[candidate.id];
                }, 300);
            }, 20000); // 20 seconds
            
            // Store active badge and timeout
            activeBadges[candidate.id] = {
                element: badge,
                timeout: timeout
            };
        }
    });
}

function updateLiveResults(data) {
    // Update total voters in summary
    const totalVotersElement = document.querySelector('.summary-card.voters .summary-number');
    if (totalVotersElement) {
        totalVotersElement.textContent = data.total_voters;
    }
    
    // Update turnout percentage
    const turnoutElement = document.querySelector('.summary-card.turnout .summary-number');
    if (turnoutElement) {
        turnoutElement.textContent = data.voter_turnout + '%';
    }
    
    // Update turnout bar
    const turnoutBar = document.querySelector('.turnout-bar');
    if (turnoutBar) {
        turnoutBar.style.width = data.voter_turnout + '%';
    }
    
    // Update voted count
    const votedElement = document.querySelector('.turnout-stat.voted .number');
    if (votedElement) {
        votedElement.textContent = data.total_voters;
    }
    
    // Update not voted count
    const notVotedElement = document.querySelector('.turnout-stat.absent .number');
    if (notVotedElement) {
        notVotedElement.textContent = data.students_not_voted;
    }
    
    // Update candidate percentages and data attributes - FIXED: Match by candidate ID, not index
    if (data.candidate_results) {
        const rows = document.querySelectorAll('.candidate-row');
        
        // Create a map for quick lookup by candidate ID
        const rowMap = {};
        rows.forEach(row => {
            const candidateId = row.dataset.candidateId;
            if (candidateId) {
                rowMap[candidateId] = row;
            }
        });
        
        // Update each candidate by matching ID
        data.candidate_results.forEach((candidate) => {
            const row = rowMap[candidate.id];
            if (row) {
                // Update the data-vote-count attribute
                row.dataset.voteCount = candidate.vote_count;
                
                // Update percentage display
                const percentageSpan = row.querySelector('.vote-percentage');
                if (percentageSpan) {
                    percentageSpan.textContent = candidate.voter_percentage + '%';
                }
                
                // Update progress bar
                const voteBar = row.querySelector('.vote-bar');
                if (voteBar) {
                    voteBar.style.width = candidate.voter_percentage + '%';
                }
            }
        });
    }
}

function updateStoredCandidateVotes(candidateResults) {
    candidateResults.forEach(currentCandidate => {
        if (previousCandidateVotes[currentCandidate.id]) {
            previousCandidateVotes[currentCandidate.id].votes = currentCandidate.vote_count;
        }
    });
}

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

    // Initialize PDF export button with modal
    const pdfBtn = document.getElementById('exportPdfBtn');
    if (pdfBtn) {
        // Remove any existing listeners and add our modal listener
        pdfBtn.replaceWith(pdfBtn.cloneNode(true));
        const newPdfBtn = document.getElementById('exportPdfBtn');
        newPdfBtn.addEventListener('click', function(e) {
            e.preventDefault();
            showComelecModal();
        });
    }

    // Initialize vote badge styles
    initializeBadgeStyles();

    // Initialize file input for PDF upload
    const fileInput = document.getElementById('pdfFile');
    if (fileInput) {
        fileInput.addEventListener('change', handleFileInputChange);
    }

    // Initialize upload form
    const uploadForm = document.getElementById('uploadPdfForm');
    if (uploadForm) {
        uploadForm.addEventListener('submit', uploadPdfResult);
    }
});

function initializeBadgeStyles() {
    if (!document.querySelector('#badge-styles')) {
        const style = document.createElement('style');
        style.id = 'badge-styles';
        style.textContent = `
            .candidate-photo-container {
                position: relative;
                display: inline-block;
            }
            
            .vote-badge-container {
                position: absolute;
                top: -5px;
                right: -5px;
                z-index: 10;
                pointer-events: none;
            }
            
            .vote-badge {
                color: #f59e0b;
                font-weight: 700;
                font-size: 18px;
                padding: 2px 4px;
                min-width: 20px;
                text-align: center;
                transform: scale(0);
                opacity: 0;
                transition: transform 0.2s ease, opacity 0.2s ease;
                text-shadow: 0 1px 2px rgba(0,0,0,0.1);
                font-family: 'Arial', sans-serif;
                letter-spacing: -0.5px;
            }
            
            .vote-badge.show {
                transform: scale(1);
                opacity: 1;
            }
            
            .vote-badge.hide {
                transform: scale(0);
                opacity: 0;
            }
            
            /* Dark mode support */
            :root.dark-mode .vote-badge {
                color: #fbbf24;
                text-shadow: 0 1px 2px rgba(0,0,0,0.3);
            }
        `;
        document.head.appendChild(style);
    }
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
        
        const response = await fetch(`/ctumoalboal-comelec/results/${electionId}/tally`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
                // REMOVED: 'X-CSRFToken': csrfToken
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

// ==================== COMELEC CHAIRMAN MODAL FUNCTIONS ====================

function showComelecModal() {
    const modal = document.getElementById('comelecModal');
    if (modal) {
        modal.style.display = 'flex';
        // Clear any previous value
        document.getElementById('chairmanName').value = '';
        // Focus on input
        setTimeout(() => {
            document.getElementById('chairmanName').focus();
        }, 100);
    }
}

function closeComelecModal() {
    const modal = document.getElementById('comelecModal');
    if (modal) {
        modal.style.display = 'none';
    }
}

function submitChairmanName() {
    const chairmanName = document.getElementById('chairmanName').value.trim();
    
    if (!chairmanName) {
        showNotification('error', '❌ Please enter the COMELEC Chairman\'s name');
        document.getElementById('chairmanName').focus();
        return;
    }
    
    // Close modal
    closeComelecModal();
    
    // Generate PDF with chairman name
    exportToPDFWithChairman(chairmanName);
}

function exportToPDFWithChairman(chairmanName) {
    const electionId = templateData.electionId;
    const isTallied = templateData.isTallied;
    
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
    
    // Include chairman name in the request
    const url = `/ctumoalboal-comelec/results/${electionId}/pdf?chairman=${encodeURIComponent(chairmanName)}`;
    
    // Fetch PDF
    fetch(url, {
        method: 'GET',
        headers: {
            'X-Requested-With': 'XMLHttpRequest'
            // REMOVED: 'X-CSRFToken': csrfToken
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
        // Download PDF
        const url = window.URL.createObjectURL(blob);
        const link = document.createElement('a');
        link.href = url;
        
        // Create filename with chairman name
        const safeTitle = templateData.electionTitle.replace(/[^a-z0-9]/gi, '_');
        const safeChairman = chairmanName.replace(/[^a-z0-9]/gi, '_').substring(0, 30);
        link.download = `${safeTitle}_${safeChairman}_Official_Results.pdf`;
        
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

// Close modal when clicking outside
window.addEventListener('click', function(event) {
    const modal = document.getElementById('comelecModal');
    if (event.target === modal) {
        closeComelecModal();
    }
});

// Close modal with Escape key
document.addEventListener('keydown', function(event) {
    if (event.key === 'Escape') {
        closeComelecModal();
    }
});

// ==================== NOTIFICATION FUNCTIONS ====================

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

// ==================== PDF UPLOAD FUNCTIONS ====================

function handleFileInputChange(e) {
    const fileNameDisplay = document.getElementById('fileNameDisplay');
    if (this.files.length > 0) {
        const file = this.files[0];
        if (file.type === 'application/pdf') {
            fileNameDisplay.innerHTML = `<i class="fa-solid fa-check" style="color: #10b981;"></i> ${file.name} (${formatFileSize(file.size)})`;
            fileNameDisplay.style.color = '#10b981';
        } else {
            fileNameDisplay.innerHTML = '❌ Please select a valid PDF file';
            fileNameDisplay.style.color = '#ef4444';
            this.value = ''; // Clear the input
        }
    } else {
        fileNameDisplay.innerHTML = 'No file chosen';
        fileNameDisplay.style.color = 'var(--text-secondary)';
    }
}

function formatFileSize(bytes) {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
}

async function uploadPdfResult(e) {
    e.preventDefault();
    
    const electionId = templateData.electionId;
    const fileInput = document.getElementById('pdfFile');
    const uploadBtn = document.getElementById('uploadPdfBtn');
    const originalBtnText = uploadBtn.innerHTML;
    
    if (!fileInput.files.length) {
        showNotification('error', '❌ Please select a PDF file to upload.');
        return;
    }
    
    const file = fileInput.files[0];
    if (file.type !== 'application/pdf') {
        showNotification('error', '❌ Only PDF files are allowed.');
        return;
    }
    
    // Check file size (max 10MB)
    if (file.size > 10 * 1024 * 1024) {
        showNotification('error', '❌ File size exceeds 10MB limit.');
        return;
    }
    
    // Optional: Add description prompt
    const description = prompt('Enter a description for this PDF (optional):', '');
    
    // Check if user cancelled the prompt
    if (description === null) {
        showNotification('info', '📄 Upload cancelled.');
        return;
    }
    
    // Create form data (CSRF token removed)
    const formData = new FormData();
    formData.append('pdf_file', file);
    // REMOVED: formData.append('csrf_token', csrfToken);
    
    if (description.trim() !== '') {
        formData.append('description', description.trim());
    }
    
    // Show loading state
    uploadBtn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Uploading...';
    uploadBtn.disabled = true;
    
    try {
        const response = await fetch(`/ctumoalboal-comelec/results/${electionId}/upload-pdf`, {
            method: 'POST'
            // REMOVED: headers with CSRF - FormData sets its own Content-Type
            // REMOVED: 'X-CSRFToken': csrfToken
        });
        
        const result = await response.json();
        
        if (result.success) {
            showNotification('success', '✅ PDF uploaded successfully!');
            
            // Clear file input
            fileInput.value = '';
            document.getElementById('fileNameDisplay').innerHTML = 'No file chosen';
            document.getElementById('fileNameDisplay').style.color = 'var(--text-secondary)';
            
            // Reload the page after 1 second to show the new PDF
            setTimeout(() => {
                window.location.reload();
            }, 1000);
        } else {
            showNotification('error', `❌ ${result.message || 'Failed to upload PDF.'}`);
        }
    } catch (error) {
        console.error('Error uploading PDF:', error);
        showNotification('error', '❌ Network error. Please try again.');
    } finally {
        uploadBtn.innerHTML = originalBtnText;
        uploadBtn.disabled = false;
    }
}

async function deletePdfResult(pdfId) {
    if (!confirm('⚠️ Are you sure you want to delete this PDF? This action cannot be undone.')) {
        return;
    }
    
    const deleteBtn = document.querySelector(`#pdf-item-${pdfId} .pdf-delete-btn`);
    const originalHtml = deleteBtn.innerHTML;
    
    // Show loading
    deleteBtn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i>';
    deleteBtn.disabled = true;
    
    try {
        const response = await fetch(`/ctumoalboal-comelec/pdf-result/${pdfId}/delete`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
                // REMOVED: 'X-CSRFToken': csrfToken
            },
            body: JSON.stringify({})
        });
        
        const result = await response.json();
        
        if (result.success) {
            showNotification('success', '✅ PDF deleted successfully!');
            
            // Remove the PDF item from DOM with animation
            const pdfItem = document.getElementById(`pdf-item-${pdfId}`);
            pdfItem.style.transition = 'all 0.3s ease';
            pdfItem.style.opacity = '0';
            pdfItem.style.transform = 'translateX(20px)';
            
            setTimeout(() => {
                pdfItem.remove();
                
                // Check if there are no more PDFs
                const pdfList = document.querySelector('.pdf-list');
                if (pdfList && pdfList.children.length === 0) {
                    const existingPdfs = document.querySelector('.existing-pdfs');
                    if (existingPdfs) {
                        existingPdfs.remove();
                    }
                }
            }, 300);
        } else {
            showNotification('error', `❌ ${result.message || 'Failed to delete PDF.'}`);
        }
    } catch (error) {
        console.error('Error deleting PDF:', error);
        showNotification('error', '❌ Network error. Please try again.');
    } finally {
        deleteBtn.innerHTML = originalHtml;
        deleteBtn.disabled = false;
    }
}

// Make delete function globally available
window.deletePdfResult = deletePdfResult;

// Clean up interval when page unloads
window.addEventListener('beforeunload', function() {
    if (newVotesCheckInterval) {
        clearInterval(newVotesCheckInterval);
    }
    
    // Clear all active badge timeouts
    Object.values(activeBadges).forEach(badge => {
        if (badge.timeout) {
            clearTimeout(badge.timeout);
        }
    });
});


// ==================== INITIALIZE INSIGHT CHARTS ====================
document.addEventListener('DOMContentLoaded', function() {
    // Only render if we're in tallied state
    const isTallied = templateData.isTallied;
    
    if (isTallied) {
        console.log('📊 Initializing vote distribution chart');
        // Small delay to ensure DOM is fully loaded
        setTimeout(() => {
            if (typeof renderGroupedVoteChart === 'function') {
                renderGroupedVoteChart();
            } else {
                console.error('vote_insights.js not loaded properly');
            }
        }, 200);
    }
});

// Update position eligible voters function
function updatePositionEligibleVoters(data) {
    // If the backend sends updated position eligibility data, update it
    if (data.position_eligible_counts) {
        window.positionEligibleVoters = data.position_eligible_counts;
        console.log('Updated position eligible voters:', window.positionEligibleVoters);
    }
}