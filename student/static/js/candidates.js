// candidates.js

document.addEventListener('DOMContentLoaded', function() {
    initializeFilters();
    initializePhotoModal();
    updateStats(); // Initial stats update
});

function initializeFilters() {
    // DOM Elements
    const filterHeader = document.getElementById('filterHeader');
    const filterContent = document.getElementById('filterContent');
    const filterToggle = document.getElementById('filterToggle');
    const filterClose = document.getElementById('filterClose');
    const filterContainer = document.querySelector('.filter-container');
    const applyBtn = document.getElementById('applyFilters');
    const resetBtn = document.getElementById('resetFilters');
    
    // Filter elements
    const positionFilters = document.querySelectorAll('.position-filter');
    const electionFilters = document.querySelectorAll('.election-filter');

    // Toggle filter on header click
    filterHeader.addEventListener('click', function(e) {
        if (!e.target.closest('.filter-toggle')) {
            toggleFilter();
        }
    });

    // Toggle filter on arrow click
    filterToggle.addEventListener('click', function(e) {
        e.stopPropagation();
        toggleFilter();
    });

    // Close filter on X button click
    filterClose.addEventListener('click', function(e) {
        e.stopPropagation();
        closeFilter();
    });

    // Close filter when clicking outside
    document.addEventListener('click', function(e) {
        if (!filterContainer.contains(e.target) && filterContent.classList.contains('show')) {
            closeFilter();
        }
    });

    // Position filters click handlers
    positionFilters.forEach(filter => {
        filter.addEventListener('click', function(e) {
            e.stopPropagation();
            const radio = this.querySelector('input[type="radio"]');
            radio.checked = true;
            
            positionFilters.forEach(f => f.classList.remove('active'));
            this.classList.add('active');
            
            applyCurrentFilters();
        });
    });

    // Election filters click handlers
    electionFilters.forEach(filter => {
        filter.addEventListener('click', function(e) {
            e.stopPropagation();
            const radio = this.querySelector('input[type="radio"]');
            radio.checked = true;
            
            electionFilters.forEach(f => f.classList.remove('active'));
            this.classList.add('active');
            
            applyCurrentFilters();
        });
    });

    // Apply Filters button
    applyBtn.addEventListener('click', function(e) {
        e.stopPropagation();
        applyCurrentFilters();
        closeFilter();
    });

    // Reset Filters button
    resetBtn.addEventListener('click', function(e) {
        e.stopPropagation();
        resetAllFilters();
    });

    // Initialize with all filters applied
    applyCurrentFilters();
}

// Filter Functions
function toggleFilter() {
    const filterContent = document.getElementById('filterContent');
    const toggleIcon = document.querySelector('.toggle-icon');
    
    filterContent.classList.toggle('show');
    toggleIcon.textContent = filterContent.classList.contains('show') ? '▲' : '▼';
}

function closeFilter() {
    const filterContent = document.getElementById('filterContent');
    const toggleIcon = document.querySelector('.toggle-icon');
    
    filterContent.classList.remove('show');
    toggleIcon.textContent = '▼';
}

function applyCurrentFilters() {
    // Get active filters
    const activePosition = document.querySelector('.position-filter.active');
    const activeElection = document.querySelector('.election-filter.active');
    
    const positionValue = activePosition ? activePosition.dataset.position : 'all';
    const electionValue = activeElection ? activeElection.dataset.election : 'all';
    
    // Apply filters
    filterCandidates(positionValue, electionValue);
    
    // Update stats based on visible candidates
    updateStats();
    
    // Update filter count display
    updateFilterCount();
}

function filterCandidates(position, election) {
    const electionSections = document.querySelectorAll('.election-section');
    
    electionSections.forEach(section => {
        let sectionHasVisibleGroups = false;
        const positionGroups = section.querySelectorAll('.position-group');
        
        positionGroups.forEach(group => {
            const groupPosition = group.dataset.position;
            const sectionElection = section.dataset.election;
            
            // Check if this position group should be visible
            const positionMatch = position === 'all' || groupPosition === position;
            const electionMatch = election === 'all' || sectionElection === election;
            
            if (positionMatch && electionMatch) {
                group.style.display = 'block';
                sectionHasVisibleGroups = true;
            } else {
                group.style.display = 'none';
            }
        });
        
        // Show/hide entire election section based on whether it has visible groups
        section.style.display = sectionHasVisibleGroups ? 'block' : 'none';
    });
}

function resetAllFilters() {
    // Reset position filter to All
    const allPositionFilter = document.querySelector('.position-filter[data-position="all"]');
    const positionFilters = document.querySelectorAll('.position-filter');
    
    allPositionFilter.querySelector('input[type="radio"]').checked = true;
    positionFilters.forEach(f => f.classList.remove('active'));
    allPositionFilter.classList.add('active');
    
    // Reset election filter to All if exists
    const allElectionFilter = document.querySelector('.election-filter[data-election="all"]');
    if (allElectionFilter) {
        const electionFilters = document.querySelectorAll('.election-filter');
        allElectionFilter.querySelector('input[type="radio"]').checked = true;
        electionFilters.forEach(f => f.classList.remove('active'));
        allElectionFilter.classList.add('active');
    }
    
    // Apply filters
    applyCurrentFilters();
    closeFilter();
}

function updateStats() {
    const statsContainer = document.querySelector('.election-stats');
    if (!statsContainer) return;
    
    const totalElections = statsContainer.dataset.totalElections || 
                          document.querySelectorAll('.election-section').length;
    
    // Count visible candidates
    let visibleCandidates = 0;
    const visiblePositions = new Set();
    
    // Get all candidate cards
    const allCandidates = document.querySelectorAll('.candidate-card');
    
    // Count only visible candidates
    allCandidates.forEach(candidate => {
        const positionGroup = candidate.closest('.position-group');
        const electionSection = candidate.closest('.election-section');
        
        // Check if both parent elements are visible
        if (positionGroup && electionSection) {
            const positionDisplay = window.getComputedStyle(positionGroup).display;
            const electionDisplay = window.getComputedStyle(electionSection).display;
            
            if (positionDisplay !== 'none' && electionDisplay !== 'none') {
                visibleCandidates++;
                
                // Add to visible positions set
                if (positionGroup.dataset.position) {
                    visiblePositions.add(positionGroup.dataset.position);
                }
            }
        }
    });
    
    // Update stats in the UI
    updateStatsDisplay(visibleCandidates, visiblePositions.size, totalElections);
}

function updateStatsDisplay(candidates, positions, elections) {
    const statsContainer = document.querySelector('.election-stats');
    if (!statsContainer) return;
    
    const statsElements = statsContainer.querySelectorAll('.stat');
    
    if (statsElements.length >= 3) {
        // Update candidates (dynamic)
        const candidatesStat = statsElements[0];
        const candidatesNumber = candidatesStat.querySelector('.stat-number');
        const candidatesLabel = candidatesStat.querySelector('.stat-label');
        candidatesNumber.textContent = candidates;
        candidatesLabel.textContent = candidates === 1 ? 'Candidate' : 'Candidates';
        
        // Update positions (dynamic)
        const positionsStat = statsElements[1];
        const positionsNumber = positionsStat.querySelector('.stat-number');
        const positionsLabel = positionsStat.querySelector('.stat-label');
        positionsNumber.textContent = positions;
        positionsLabel.textContent = positions === 1 ? 'Position' : 'Positions';
    }
}

function updateFilterCount() {
    const activePosition = document.querySelector('.position-filter.active span');
    const activeElection = document.querySelector('.election-filter.active span');
    
    const positionText = activePosition ? activePosition.textContent : 'All Positions';
    const electionText = activeElection ? activeElection.textContent : 'All Elections';
    
    const countEl = document.getElementById('activeFilterCount');
    
    if (positionText === 'All Positions' && electionText === 'All Elections') {
        countEl.textContent = '';
    } else {
        countEl.textContent = `${positionText} · ${electionText}`;
    }
}

// Photo Modal Functions
function initializePhotoModal() {
    const modal = document.getElementById('photoModal');
    if (!modal) return;
    
    document.addEventListener('keydown', function(e) {
        if (e.key === 'Escape') {
            closePhotoModal();
        }
    });

    modal.addEventListener('click', function(e) {
        if (e.target === this) {
            closePhotoModal();
        }
    });

    const modalContent = document.querySelector('.photo-modal-content');
    if (modalContent) {
        modalContent.addEventListener('click', function(e) {
            e.stopPropagation();
        });
    }
}

function openCandidatePhoto(element) {
    const modal = document.getElementById('photoModal');
    const modalImg = document.getElementById('photoModalImg');
    const modalCaption = document.getElementById('photoModalCaption');
    
    if (!modal || !modalImg || !modalCaption) return;
    
    const photoUrl = element.getAttribute('data-photo-url');
    const candidateCard = element.closest('.candidate-card');
    const candidateName = candidateCard ? candidateCard.querySelector('.candidate-name').textContent : 'Candidate';
    
    modalImg.src = photoUrl;
    modalCaption.textContent = candidateName + ' - Profile Photo';
    
    modal.style.display = 'flex';
    document.body.style.overflow = 'hidden';
}

function closePhotoModal() {
    const modal = document.getElementById('photoModal');
    if (modal) {
        modal.style.display = 'none';
        document.body.style.overflow = 'auto';
    }
}

// Remove or comment out the conflicting showCandidateProfile function
// The modal functionality is now handled by openCandidateProfileModal in the HTML

// Close all modals function
function closeAllModals() {
    closePhotoModal();
    if (document.getElementById('candidateProfileModal')) {
        document.getElementById('candidateProfileModal').classList.remove('show');
        document.body.style.overflow = 'auto';
    }
    if (document.getElementById('filterContent')?.classList.contains('show')) {
        closeFilter();
    }
}

// Add meta tags for static URLs
function addStaticUrlMetaTags() {
    if (!document.querySelector('meta[name="admin-static-url"]')) {
        const meta = document.createElement('meta');
        meta.name = 'admin-static-url';
        meta.content = '/admin/static/';
        document.head.appendChild(meta);
    }
    if (!document.querySelector('meta[name="student-static-url"]')) {
        const meta = document.createElement('meta');
        meta.name = 'student-static-url';
        meta.content = '/student/static/';
        document.head.appendChild(meta);
    }
}

// Initialize meta tags on load
addStaticUrlMetaTags();