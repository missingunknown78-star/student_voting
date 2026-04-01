// ==================== INSIGHT CHARTS - Grouped by Position ====================
// Render single bar chart with candidates grouped by position, sorted by position ID

// Predefined color palette - Primary colors first, then secondary
const COLOR_PALETTE = [
    '#3b82f6', '#ef4444', '#10b981', '#f59e0b', '#8b5cf6', '#ec489a', '#06b6d4',
    '#84cc16', '#f97316', '#d946ef', '#14b8a6', '#6366f1', '#a855f7', '#2dd4bf', '#eab308',
    '#2563eb', '#dc2626', '#059669', '#d97706', '#7c3aed', '#db2777', '#0891b2',
    '#65a30d', '#ea580c', '#c026d3', '#0d9488', '#4f46e5', '#9333ea', '#10b981', '#ca8a04'
];

function getPositionColorByOrder(index) {
    return COLOR_PALETTE[index % COLOR_PALETTE.length];
}

function renderGroupedVoteChart() {
    // Extract all candidates grouped by position
    const positionsData = extractCandidatesGroupedByPosition();
    
    if (!positionsData || positionsData.length === 0) {
        console.log('No candidates found for chart');
        return;
    }
    
    // Filter out any "Unknown" positions (positions with id 0 or no ID)
    const validPositions = positionsData.filter(pos => pos.id > 0 && pos.name !== 'Unknown');
    
    if (validPositions.length === 0) {
        console.log('No valid positions found');
        return;
    }
    
    // Sort positions by ID (ascending)
    validPositions.sort((a, b) => a.id - b.id);
    
    const allCandidates = [];
    const positionColors = {};
    
    // Generate a color for each position based on order
    validPositions.forEach((position, posIndex) => {
        const color = getPositionColorByOrder(posIndex);
        positionColors[position.name] = color;
        
        // Sort candidates within position by vote count (highest first)
        const sortedCandidates = [...position.candidates].sort((a, b) => b.votes - a.votes);
        
        // Add each candidate with this color
        sortedCandidates.forEach(candidate => {
            candidate.color = color;
            candidate.positionColor = color;
            allCandidates.push(candidate);
        });
    });
    
    // Update total candidates count
    const totalCandidatesSpan = document.getElementById('totalCandidatesCount');
    if (totalCandidatesSpan) {
        totalCandidatesSpan.textContent = allCandidates.length;
    }
    
    const candidateCount = allCandidates.length;
    console.log(`Total candidates: ${candidateCount}`);
    
    // Prepare data for chart
    const candidateNames = allCandidates.map(c => `${c.name}`);
    const voteCounts = allCandidates.map(c => c.votes);
    const colors = allCandidates.map(c => c.color);
    
    const canvas = document.getElementById('overallVoteChart');
    if (!canvas) {
        console.log('Canvas not found');
        return;
    }
    
    const ctx = canvas.getContext('2d');
    const maxVotes = Math.max(...voteCounts, 1);
    
    // Destroy existing chart if it exists
    if (canvas.chart) {
        canvas.chart.destroy();
    }
    
    // Configure Chart.js for dark mode
    const isDarkMode = document.documentElement.classList.contains('dark-mode');
    
    // Calculate dynamic height based on number of candidates
    const baseHeight = 400;
    const extraHeightPerCandidate = 35;
    const dynamicHeight = Math.max(baseHeight, candidateCount * extraHeightPerCandidate);
    const finalHeight = Math.min(dynamicHeight, 1800);
    
    // Set chart container height
    const chartWrapper = document.querySelector('.chart-wrapper');
    if (chartWrapper) {
        chartWrapper.style.height = `${finalHeight}px`;
        chartWrapper.style.minHeight = `${finalHeight}px`;
        console.log(`Set chart height to ${finalHeight}px for ${candidateCount} candidates`);
    }
    
    // Create new chart
    canvas.chart = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: candidateNames,
            datasets: [{
                label: 'Votes',
                data: voteCounts,
                backgroundColor: colors,
                borderColor: colors.map(c => c),
                borderWidth: 1,
                borderRadius: 4,
                barPercentage: 0.7,
                categoryPercentage: 0.85
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    display: false
                },
                tooltip: {
                    backgroundColor: isDarkMode ? '#2d2d2d' : '#ffffff',
                    titleColor: isDarkMode ? '#f0f0f0' : '#1e293b',
                    bodyColor: isDarkMode ? '#b0b0b0' : '#64748b',
                    borderColor: isDarkMode ? '#404040' : '#e2e8f0',
                    borderWidth: 1,
                    callbacks: {
                        label: function(context) {
                            const votes = context.raw;
                            const candidate = allCandidates[context.dataIndex];
                            
                            // Get eligible voters for this position
                            const eligibleVoters = candidate.eligibleVoters || 0;
                            
                            // Calculate percentage based on eligible voters
                            const percentage = eligibleVoters > 0 ? 
                                ((candidate.votes / eligibleVoters) * 100).toFixed(1) : 0;
                            
                            return [
                                `Votes: ${votes.toLocaleString()}`,
                                `Percentage: ${percentage}%`,
                                `Position: ${candidate.position}`
                            ];
                        },
                        title: function(context) {
                            return allCandidates[context[0].dataIndex].name;
                        }
                    }
                }
            },
            scales: {
                y: {
                    beginAtZero: true,
                    title: {
                        display: true,
                        text: 'Number of Votes',
                        color: isDarkMode ? '#f0f0f0' : '#1e293b',
                        font: { weight: 'bold', size: 12 }
                    },
                    ticks: {
                        stepSize: calculateStepSize(maxVotes),
                        callback: function(value) {
                            return value.toLocaleString();
                        },
                        color: isDarkMode ? '#f0f0f0' : '#1e293b'
                    },
                    grid: {
                        color: isDarkMode ? '#404040' : '#e2e8f0'
                    }
                },
                x: {
                    title: {
                        display: true,
                        text: 'Candidates',
                        color: isDarkMode ? '#f0f0f0' : '#1e293b',
                        font: { weight: 'bold', size: 12 }
                    },
                    ticks: {
                        maxRotation: 45,
                        minRotation: 45,
                        font: { size: 11, weight: 'normal' },
                        autoSkip: false,
                        color: isDarkMode ? '#f0f0f0' : '#1e293b'
                    },
                    grid: { display: false }
                }
            },
            layout: {
                padding: { top: 10, bottom: 5, left: 10, right: 10 }
            },
            onClick: function(event, activeElements) {
                if (activeElements && activeElements.length > 0) {
                    const index = activeElements[0].index;
                    const candidate = allCandidates[index];
                    showCandidateDetails(candidate);
                }
            }
        }
    });
    
    // Update the legend
    updatePositionLegend(validPositions, positionColors);
}

function extractCandidatesGroupedByPosition() {
    const positionsMap = new Map();
    
    const candidateRows = document.querySelectorAll('#resultsContent .candidate-row');
    
    console.log(`Found ${candidateRows.length} candidate rows`);
    
    // Get eligible voters data from backend (passed via template)
    const eligibleVotersData = window.positionEligibleVoters || {};
    
    candidateRows.forEach((row) => {
        const nameElement = row.querySelector('.candidate-name');
        const candidateName = nameElement ? nameElement.textContent.trim() : 'Unknown';
        
        const positionElement = row.querySelector('.candidate-position');
        const position = positionElement ? positionElement.textContent.trim() : 'Unknown';
        
        let positionId = parseInt(row.dataset.positionId);
        
        if (isNaN(positionId) || positionId === 0) {
            const positionIdAttr = row.getAttribute('data-position-id');
            if (positionIdAttr) {
                positionId = parseInt(positionIdAttr);
            }
        }
        
        if (isNaN(positionId) || positionId === 0) {
            console.warn(`Skipping candidate ${candidateName} - no valid position ID`);
            return;
        }
        
        const voteCountElement = row.querySelector('.vote-count');
        let voteCount = 0;
        if (voteCountElement) {
            voteCount = parseInt(voteCountElement.textContent.replace(/,/g, '')) || 0;
        }
        
        // Get the percentage displayed in the table (this is already correct from backend)
        let percentage = 0;
        const percentageElement = row.querySelector('.vote-percentage');
        if (percentageElement) {
            percentage = parseFloat(percentageElement.textContent) || 0;
        }
        
        const statusCell = row.querySelector('.status-cell');
        const isWinner = statusCell && statusCell.textContent.includes('Winner');
        
        const candidateId = row.dataset.candidateId;
        
        // Get eligible voters for this position from backend data
        const eligibleVoters = eligibleVotersData[positionId] ? eligibleVotersData[positionId].count : 0;
        
        const mapKey = `${positionId}_${position}`;
        
        if (!positionsMap.has(mapKey)) {
            positionsMap.set(mapKey, {
                id: positionId,
                name: position,
                candidates: [],
                totalVotes: 0,
                totalEligibleVoters: eligibleVoters,
                winnerCount: 0
            });
        }
        
        const positionData = positionsMap.get(mapKey);
        positionData.candidates.push({
            id: candidateId,
            name: candidateName,
            position: position,
            votes: voteCount,
            percentage: percentage,
            isWinner: isWinner,
            eligibleVoters: eligibleVoters
        });
        positionData.totalVotes += voteCount;
        if (isWinner) positionData.winnerCount++;
    });
    
    const positionsArray = Array.from(positionsMap.values()).filter(pos => pos.candidates.length > 0);
    
    positionsArray.forEach(position => {
        position.candidates.sort((a, b) => b.votes - a.votes);
        position.candidates.forEach(candidate => {
            candidate.positionTotalVotes = position.totalVotes;
            candidate.eligibleVoters = position.totalEligibleVoters;
        });
    });
    
    console.log(`Extracted ${positionsArray.length} positions`);
    const totalCandidates = positionsArray.reduce((sum, p) => sum + p.candidates.length, 0);
    console.log(`Total candidates: ${totalCandidates}`);
    
    return positionsArray;
}

function updatePositionLegend(positionsData, positionColors) {
    const legendContainer = document.getElementById('overallChartLegend');
    
    if (!legendContainer) return;
    
    legendContainer.innerHTML = '';
    
    const verticalContainer = document.createElement('div');
    verticalContainer.className = 'legend-grid';
    
    const sortedPositions = [...positionsData].sort((a, b) => a.id - b.id);
    
    sortedPositions.forEach(position => {
        const legendItem = document.createElement('div');
        legendItem.className = 'legend-item';
        
        const colorBox = document.createElement('div');
        colorBox.className = 'legend-color';
        colorBox.style.backgroundColor = positionColors[position.name];
        
        const positionNameSpan = document.createElement('span');
        positionNameSpan.className = 'legend-name';
        positionNameSpan.textContent = position.name;
        
        const statsContainer = document.createElement('div');
        statsContainer.className = 'legend-stats';
        
        const candidateCountSpan = document.createElement('span');
        candidateCountSpan.className = 'legend-badge';
        candidateCountSpan.innerHTML = `<i class="fa-solid fa-user"></i> ${position.candidates.length} candidate${position.candidates.length !== 1 ? 's' : ''}`;
        statsContainer.appendChild(candidateCountSpan);
        
        if (position.winnerCount > 0) {
            const winnerSpan = document.createElement('span');
            winnerSpan.className = 'legend-badge winner';
            winnerSpan.innerHTML = `<i class="fa-solid fa-trophy"></i> ${position.winnerCount} winner${position.winnerCount > 1 ? 's' : ''}`;
            statsContainer.appendChild(winnerSpan);
        }
        
        legendItem.appendChild(colorBox);
        legendItem.appendChild(positionNameSpan);
        legendItem.appendChild(statsContainer);
        
        verticalContainer.appendChild(legendItem);
    });
    
    legendContainer.appendChild(verticalContainer);
    
    const checkScrollNeeded = () => {
        const hasHorizontalScroll = legendContainer.scrollWidth > legendContainer.clientWidth;
        const existingHint = legendContainer.querySelector('.scroll-hint');
        
        if (hasHorizontalScroll && !existingHint) {
            const scrollHint = document.createElement('div');
            scrollHint.className = 'scroll-hint';
            scrollHint.innerHTML = '<i class="fa-solid fa-arrow-left"></i> Scroll horizontally to see all positions <i class="fa-solid fa-arrow-right"></i>';
            legendContainer.appendChild(scrollHint);
        } else if (!hasHorizontalScroll && existingHint) {
            existingHint.remove();
        }
    };
    
    setTimeout(checkScrollNeeded, 100);
    window.addEventListener('resize', () => setTimeout(checkScrollNeeded, 100));
}

function calculateStepSize(maxValue) {
    if (maxValue <= 10) return 2;
    if (maxValue <= 20) return 5;
    if (maxValue <= 50) return 10;
    if (maxValue <= 100) return 20;
    if (maxValue <= 200) return 50;
    if (maxValue <= 500) return 100;
    if (maxValue <= 1000) return 200;
    if (maxValue <= 5000) return 500;
    return Math.ceil(maxValue / 6);
}

function showCandidateDetails(candidate) {
    const eligibleVoters = candidate.eligibleVoters || 0;
    const percentage = eligibleVoters > 0 ? ((candidate.votes / eligibleVoters) * 100).toFixed(1) : 0;
    
    const message = [
        `🏆 ${candidate.name}`,
        `📌 Position: ${candidate.position}`,
        `📊 Votes: ${candidate.votes.toLocaleString()}`,
        `📈 Percentage: ${percentage}%`,
        candidate.isWinner ? '✨ WINNER ✨' : ''
    ].filter(m => m).join('\n');
    
    alert(message);
}

const observer = new MutationObserver(function(mutations) {
    mutations.forEach(function(mutation) {
        if (mutation.attributeName === 'class') {
            const canvas = document.getElementById('overallVoteChart');
            if (canvas && canvas.chart) {
                renderGroupedVoteChart();
            }
        }
    });
});

document.addEventListener('DOMContentLoaded', function() {
    const htmlElement = document.documentElement;
    observer.observe(htmlElement, { attributes: true });
    
    // Initial render
    renderGroupedVoteChart();
});