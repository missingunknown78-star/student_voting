/**
 * Elections Available Page JavaScript
 * Handles countdown timers, flash messages, and interactive elements
 */

document.addEventListener('DOMContentLoaded', function() {
    // =============== LOG STUDENT INFO FOR DEBUGGING ===============
    if (window.studentData) {
        console.log('Student Year (numeric):', window.studentData.year);
        console.log('Student Year (display):', window.studentData.yearDisplay);
        console.log('Total Elections:', window.studentData.electionCount);
    }

    // =============== FLASH MESSAGES AUTO-DISMISS ===============
    const flashMessages = document.querySelectorAll('.alert-auto-dismiss');
    flashMessages.forEach(message => {
        setTimeout(() => {
            message.style.transition = 'opacity 0.5s ease, transform 0.5s ease';
            message.style.opacity = '0';
            message.style.transform = 'translateY(-10px)';
            
            // Remove from DOM after fade out
            setTimeout(() => {
                if (message.parentNode) {
                    message.parentNode.removeChild(message);
                }
            }, 500);
        }, 5000); // 5 seconds
    });

    // =============== RIPPLE EFFECT FOR VOTE BUTTONS ===============
    const voteNowButtons = document.querySelectorAll('.vote-button:not(.btn-success):not(.btn-disabled)');
    voteNowButtons.forEach(button => {
        button.addEventListener('click', function(e) {
            // Only add ripple effect to active "Vote Now" buttons
            if (this.classList.contains('btn-success') || this.disabled || this.classList.contains('btn-disabled')) return;
            
            // Create ripple element
            const ripple = document.createElement('span');
            const rect = this.getBoundingClientRect();
            const size = Math.max(rect.width, rect.height);
            const x = e.clientX - rect.left - size / 2;
            const y = e.clientY - rect.top - size / 2;
            
            // Style the ripple
            ripple.style.cssText = `
                position: absolute;
                border-radius: 50%;
                background: rgba(255, 255, 255, 0.7);
                transform: scale(0);
                animation: ripple 0.6s linear;
                width: ${size}px;
                height: ${size}px;
                top: ${y}px;
                left: ${x}px;
                pointer-events: none;
            `;
            
            // Add ripple to button
            this.style.position = 'relative';
            this.style.overflow = 'hidden';
            this.appendChild(ripple);
            
            // Remove ripple after animation
            setTimeout(() => {
                if (ripple.parentNode === this) {
                    this.removeChild(ripple);
                }
            }, 600);
        });
    });

    // =============== COUNTDOWN TIMER FUNCTION ===============
    function updateCountdowns() {
        document.querySelectorAll('.countdown').forEach(el => {
            const start = new Date(el.dataset.start);
            const end = new Date(el.dataset.end);
            const now = new Date();
            const electionId = el.dataset.id;
            const display = document.getElementById(`countdown-${electionId}`);
            const voteBtn = document.getElementById(`vote-btn-${electionId}`);
            const electionCard = el.closest('.election-card');
            const votingInstructions = electionCard ? electionCard.querySelector('.voting-instructions') : null;
            const ineligibleMessage = electionCard ? electionCard.querySelector('.ineligible-message') : null;
            const isEligible = !ineligibleMessage; // If no ineligible message, student is eligible

            if (!display) return;

            if (now < start) {
                // Election hasn't started yet
                display.textContent = "Starts in " + formatTime(start - now);
                
                if (voteBtn) {
                    voteBtn.style.pointerEvents = "none";
                    voteBtn.style.opacity = "0.6";
                    voteBtn.innerHTML = '<span class="btn-icon">⏳</span> Not Started';
                    voteBtn.classList.remove('btn-primary');
                    voteBtn.classList.add('btn-secondary');
                }
                
                // Hide voting instructions if election hasn't started
                if (votingInstructions) {
                    votingInstructions.style.display = 'none';
                }
            } else if (now >= start && now <= end) {
                // Election is active
                display.textContent = "Ends in " + formatTime(end - now);
                
                if (voteBtn && isEligible) {
                    voteBtn.style.pointerEvents = "auto";
                    voteBtn.style.opacity = "1";
                    voteBtn.innerHTML = '<span class="btn-icon">✓</span> Vote Now';
                    voteBtn.classList.add('btn-primary');
                    voteBtn.classList.remove('btn-secondary');
                }
                
                // Show voting instructions if eligible
                if (votingInstructions && isEligible) {
                    votingInstructions.style.display = 'block';
                }
            } else {
                // Election has ended
                display.textContent = "Election ended";
                
                if (voteBtn) {
                    voteBtn.style.pointerEvents = "none";
                    voteBtn.style.opacity = "0.6";
                    voteBtn.innerHTML = '<span class="btn-icon">📋</span> Ended';
                    voteBtn.classList.remove('btn-primary');
                    voteBtn.classList.add('btn-secondary');
                }
                
                // Also update any "Voted" buttons to "Election Ended"
                const votedButton = electionCard ? electionCard.querySelector('.btn-success.vote-button') : null;
                if (votedButton) {
                    votedButton.innerHTML = '<span class="btn-icon">📋</span> Election Ended';
                    votedButton.classList.remove('btn-success');
                    votedButton.classList.add('btn-secondary');
                    
                    // Update the voted message
                    const votedMessage = electionCard.querySelector('.voted-message');
                    if (votedMessage) {
                        votedMessage.innerHTML = '<span class="detail-icon">📋</span> Election has ended';
                        votedMessage.style.color = 'var(--gray)';
                    }
                }
                
                // Hide voting instructions when election ends
                if (votingInstructions) {
                    votingInstructions.style.display = 'none';
                }
            }
        });
    }

    // =============== FORMAT TIME FUNCTION ===============
    function formatTime(ms) {
        if (ms <= 0) return "0d 00h 00m 00s";
        
        let totalSeconds = Math.floor(ms / 1000);
        const days = Math.floor(totalSeconds / 86400);
        totalSeconds %= 86400;
        const hours = Math.floor(totalSeconds / 3600);
        totalSeconds %= 3600;
        const minutes = Math.floor(totalSeconds / 60);
        const seconds = totalSeconds % 60;

        if (days > 0) {
            return `${days}d ${pad(hours)}h ${pad(minutes)}m`;
        } else if (hours > 0) {
            return `${hours}h ${pad(minutes)}m ${pad(seconds)}s`;
        } else {
            return `${minutes}m ${pad(seconds)}s`;
        }
    }

    // =============== PAD FUNCTION ===============
    function pad(num) {
        return num.toString().padStart(2, '0');
    }

    // =============== INITIALIZE ===============
    updateCountdowns();
    
    // Update every second
    setInterval(updateCountdowns, 1000);
    
    // Auto-refresh page every 30 seconds to update vote counts and status
    setTimeout(() => {
        location.reload();
    }, 30000);
});

// =============== ADD CSS FOR RIPPLE ANIMATION ===============
const style = document.createElement('style');
style.textContent = `
    @keyframes ripple {
        to {
            transform: scale(4);
            opacity: 0;
        }
    }
    
    .btn-success {
        cursor: default !important;
    }
    
    .btn-success:hover {
        transform: none !important;
    }
    
    .btn-disabled {
        cursor: not-allowed !important;
    }
    
    .btn-disabled:hover {
        transform: none !important;
        box-shadow: none !important;
    }
`;
document.head.appendChild(style);