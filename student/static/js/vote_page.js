// vote_page.js - Handles voting page interactions

// Set cast timestamp and click timestamp when form is submitted
document.addEventListener('DOMContentLoaded', function() {
    const voteForm = document.getElementById('voteForm');
    if (voteForm) {
        voteForm.onsubmit = function() {
            // Record the exact click time in SECONDS (not milliseconds)
            const clickTimeSeconds = new Date().getTime() / 1000;
            document.getElementById('click-timestamp').value = clickTimeSeconds;
            
            // Get current time in Manila timezone
            const now = new Date();
            
            // Format as ISO string WITHOUT the Z (which indicates UTC)
            const year = now.getFullYear();
            const month = String(now.getMonth() + 1).padStart(2, '0');
            const day = String(now.getDate()).padStart(2, '0');
            const hours = String(now.getHours()).padStart(2, '0');
            const minutes = String(now.getMinutes()).padStart(2, '0');
            const seconds = String(now.getSeconds()).padStart(2, '0');
            
            // Format: YYYY-MM-DD HH:MM:SS (Manila local time)
            const manilaTimeStr = `${year}-${month}-${day}T${hours}:${minutes}:${seconds}`;
            
            document.getElementById('cast-timestamp').value = manilaTimeStr;
            
            // Show loading overlay
            document.getElementById('loadingOverlay').style.display = 'flex';
            
            // Disable submit button to prevent double submission
            document.getElementById('submitBtn').disabled = true;
            
            return true; // Allow form to submit
        };
    }

    // Countdown Timer
    const deadline = new Date(window.electionEndDate).getTime();
    const countdownEl = document.getElementById("countdown");
    const submitBtn = document.getElementById("submitBtn");

    function updateCountdown() {
        const now = new Date().getTime();
        const distance = deadline - now;

        if (distance > 0) {
            const days = Math.floor(distance / (1000*60*60*24));
            const hours = Math.floor((distance % (1000*60*60*24)) / (1000*60*60));
            const minutes = Math.floor((distance % (1000*60*60)) / (1000*60));
            const seconds = Math.floor((distance % (1000*60)) / 1000);
            countdownEl.innerHTML = `${days}d ${hours}h ${minutes}m ${seconds}s`;
        } else {
            countdownEl.innerHTML = "Voting period has ended ⏰";
            if(submitBtn) {
                submitBtn.disabled = true;
                submitBtn.textContent = "Voting Closed";
                submitBtn.style.backgroundColor = "#999";
            }
            
            // Disable all radio buttons
            document.querySelectorAll('.candidate-radio').forEach(radio => {
                radio.disabled = true;
            });
            
            // Hide loading overlay if shown
            document.getElementById('loadingOverlay').style.display = 'none';
        }
    }

    updateCountdown();
    const timer = setInterval(updateCountdown, 1000);

    // Hide loading overlay if it was showing from previous page load
    document.getElementById('loadingOverlay').style.display = 'none';

    // Initialize selection counters
    initializeAllCounters();

    // Add visual feedback when selecting candidates
    document.querySelectorAll('.candidate-row').forEach(row => {
        const radio = row.querySelector('.candidate-radio');
        
        if (radio) {
            radio.addEventListener('change', function(e) {
                const positionGroup = this.closest('.position-group');
                const maxVotes = parseInt(positionGroup.dataset.maxVotes);
                const positionId = positionGroup.dataset.positionId;
                
                if (this.type === 'radio') {
                    positionGroup.querySelectorAll('.candidate-row').forEach(r => {
                        r.classList.remove('selected');
                    });
                    if (this.checked) {
                        row.classList.add('selected');
                    }
                } else {
                    if (this.checked) {
                        row.classList.add('selected-multi');
                    } else {
                        row.classList.remove('selected-multi');
                    }
                    
                    const checkboxes = positionGroup.querySelectorAll('input[type="checkbox"]:checked');
                    if (checkboxes.length > maxVotes) {
                        this.checked = false;
                        row.classList.remove('selected-multi');
                        alert(`You can only select up to ${maxVotes} candidates for this position.`);
                    }
                    
                    updateSelectionCounter(positionId, maxVotes);
                }
                
                e.stopPropagation();
            });
        }
        
        row.addEventListener('click', function(e) {
            if (e.target.tagName !== 'INPUT' && e.target.tagName !== 'LABEL') {
                const radio = this.querySelector('.candidate-radio');
                if (radio && !radio.disabled) {
                    e.preventDefault();
                    if (radio.type === 'radio') {
                        radio.checked = true;
                    } else {
                        radio.checked = !radio.checked;
                    }
                    const event = new Event('change', { bubbles: true });
                    radio.dispatchEvent(event);
                }
            }
        });
    });
});

// Update selection counter
function updateSelectionCounter(positionId, maxVotes) {
    const checkboxes = document.querySelectorAll(`input[name="position_${positionId}"]:checked`);
    const counter = document.getElementById(`counter-${positionId}`);
    
    if (counter) {
        const countSpan = counter.querySelector('.selected-count');
        countSpan.textContent = checkboxes.length;
    }
}

// Initialize counters
function initializeCounter(positionId, maxVotes) {
    updateSelectionCounter(positionId, maxVotes);
}

// Initialize all counters
function initializeAllCounters() {
    document.querySelectorAll('.position-group[data-max-votes]').forEach(group => {
        const positionId = group.dataset.positionId;
        const maxVotes = parseInt(group.dataset.maxVotes);
        updateSelectionCounter(positionId, maxVotes);
    });
}

// Validate vote
function validateVote() {
    const positionGroups = document.querySelectorAll('.position-group');
    let allPositionsVoted = true;
    
    positionGroups.forEach(group => {
        const maxVotes = parseInt(group.dataset.maxVotes);
        
        if (maxVotes === 1) {
            const radios = group.querySelectorAll('input[type="radio"]:checked');
            if (radios.length === 0) {
                allPositionsVoted = false;
                group.style.border = "2px solid #e53e3e";
                group.style.borderRadius = "8px";
                group.style.padding = "10px";
            } else {
                group.style.border = "";
                group.style.padding = "";
            }
        } else {
            const checkboxes = group.querySelectorAll('input[type="checkbox"]:checked');
            if (checkboxes.length === 0) {
                allPositionsVoted = false;
                group.style.border = "2px solid #e53e3e";
                group.style.borderRadius = "8px";
                group.style.padding = "10px";
            } else {
                group.style.border = "";
                group.style.padding = "";
            }
        }
    });
    
    if (!allPositionsVoted) {
        alert("Please select candidates for all positions before submitting your vote.");
        return false;
    }
    
    return confirm("Are you sure you want to submit your vote?\n\nYour vote will be encrypted and cannot be changed.");
}

// Make functions globally available
window.updateSelectionCounter = updateSelectionCounter;
window.initializeCounter = initializeCounter;
window.validateVote = validateVote;