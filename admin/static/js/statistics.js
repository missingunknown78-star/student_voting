document.addEventListener('DOMContentLoaded', () => {
    const elections = JSON.parse(document.getElementById('electionData').textContent);
    ALL_ELECTIONS = elections;

    recalculateDashboard();

    document.getElementById('filter-election-type').addEventListener('change', onFilterChange);
    document.getElementById('filter-department').addEventListener('change', recalculateDashboard);
    document.getElementById('sort-by').addEventListener('change', recalculateDashboard);
    document.getElementById('exportReport').addEventListener('click', exportPDF);
});

let ALL_ELECTIONS = [];
let BAR_CHARTS = [];
let typeChart = null;
let trendChart = null;
let TOTAL_ELIGIBLE_VOTERS = 5000; // This should come from your backend

/* ------------------ FILTER HANDLING ------------------ */
function onFilterChange() {
    const type = document.getElementById('filter-election-type').value;
    const deptEl = document.getElementById('filter-department');

    if (type === 'Department') {
        deptEl.style.display = 'inline-block';
    } else {
        deptEl.style.display = 'none';
        deptEl.value = 'all';
    }

    recalculateDashboard();
}

/* ------------------ MAIN DASHBOARD ------------------ */
function recalculateDashboard() {
    let elections = getFilteredElections();
    elections = sortElections(elections);

    updateKPIs(elections);
    updateCharts(elections);
    updateInsights(elections);
    updateWinnersList(elections);
    updatePositionStats(elections);
    updateElectionCards(elections);
    renderBarCharts(elections);
}

/* ------------------ FILTERED ELECTIONS ------------------ */
function getFilteredElections() {
    const type = document.getElementById('filter-election-type').value;
    const dept = document.getElementById('filter-department').value;

    return ALL_ELECTIONS.filter(e => {
        if (type === 'General') return !e.department;
        if (type === 'Department') {
            if (!e.department) return false;
            if (dept !== 'all' && e.department !== dept) return false;
            return true;
        }
        return true;
    });
}

/* ------------------ SORTING ------------------ */
function sortElections(elections) {
    const sortBy = document.getElementById('sort-by').value;
    const sorted = [...elections];

    if (sortBy === 'date') {
        return sorted.sort((a, b) => new Date(b.end_date) - new Date(a.end_date));
    }
    if (sortBy === 'date-oldest') {
        return sorted.sort((a, b) => new Date(a.end_date) - new Date(b.end_date));
    }
    if (sortBy === 'votes') {
        return sorted.sort((a, b) => (b.total_voters || 0) - (a.total_voters || 0));
    }
    if (sortBy === 'margin') {
        return sorted.sort((a, b) => (a.winning_percentage || 100) - (b.winning_percentage || 100));
    }

    return sorted;
}

/* ------------------ KPI UPDATES ------------------ */
function updateKPIs(elections) {
    // Total Elections
    document.getElementById('totalElections').textContent = elections.length;

    // Total Votes Cast
    const totalVoters = elections.reduce((sum, e) => sum + (e.total_voters || 0), 0);
    document.getElementById('totalVotedStudents').textContent = totalVoters.toLocaleString();

    // Voter Turnout (if you have total eligible voters)
    const turnout = ((totalVoters / TOTAL_ELIGIBLE_VOTERS) * 100).toFixed(1);
    document.getElementById('voterTurnout').textContent = `${turnout}%`;
    document.getElementById('turnoutBar').style.width = `${turnout}%`;

    // Average Participation
    const avgParticipation = elections.length ? (totalVoters / elections.length).toFixed(1) : 0;
    document.getElementById('avgTurnout').textContent = `${avgParticipation}`;
}

/* ------------------ GLOBAL CHARTS ------------------ */
function updateCharts(elections) {
    if (typeChart) typeChart.destroy();
    if (trendChart) trendChart.destroy();
    if (!elections.length) return;

    // Election Types Chart
    const typeCounts = {};
    elections.forEach(e => {
        typeCounts[e.election_type] = (typeCounts[e.election_type] || 0) + 1;
    });

    typeChart = new Chart(document.getElementById('typeDistributionChart'), {
        type: 'doughnut',
        data: {
            labels: Object.keys(typeCounts),
            datasets: [{
                data: Object.values(typeCounts),
                backgroundColor: ['#4dabf7', '#20c997', '#ff922b']
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            cutout: '70%',
            plugins: {
                legend: { position: 'bottom' }
            }
        }
    });

    // Voting Trend Chart
    const monthly = {};
    elections.forEach(e => {
        const m = e.end_date.substring(0, 7);
        monthly[m] = (monthly[m] || 0) + (e.total_voters || 0);
    });

    const months = Object.keys(monthly).sort();

    trendChart = new Chart(document.getElementById('participationChart'), {
        type: 'line',
        data: {
            labels: months,
            datasets: [{
                label: 'Votes Cast',
                data: months.map(m => monthly[m]),
                fill: true,
                tension: 0.4,
                borderColor: '#4dabf7',
                backgroundColor: 'rgba(77, 171, 247, 0.1)'
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                tooltip: {
                    callbacks: {
                        label: (context) => `${context.raw} votes`
                    }
                }
            }
        }
    });
}

/* ------------------ WINNERS LIST (NEW) ------------------ */
function updateWinnersList(elections) {
    const winnersList = document.getElementById('winnersList');
    if (!winnersList) return;

    // Get last 4 elections
    const recentElections = [...elections]
        .sort((a, b) => new Date(b.end_date) - new Date(a.end_date))
        .slice(0, 4);

    if (recentElections.length === 0) {
        winnersList.innerHTML = '<div class="no-data">No winners yet</div>';
        return;
    }

    winnersList.innerHTML = recentElections.map(election => {
        const winner = election.winner || 'No winner';
        const winnerVotes = election.votes[winner] || 0;
        const totalVotes = Object.values(election.votes).reduce((a, b) => a + b, 0);
        const margin = election.winning_percentage || 0;

        return `
            <div class="winner-card">
                <h4>${election.title}</h4>
                <div class="winner-name">${winner}</div>
                <div class="winner-meta">
                    <span class="winner-votes">${winnerVotes} votes</span>
                    <span class="winner-margin">${margin}% margin</span>
                </div>
            </div>
        `;
    }).join('');
}

/* ------------------ POSITION STATISTICS (NEW) ------------------ */
function updatePositionStats(elections) {
    const positionStats = document.getElementById('positionStats');
    if (!positionStats) return;

    const positionData = {};

    elections.forEach(election => {
        Object.entries(election.candidate_roles || {}).forEach(([candidate, position]) => {
            if (!positionData[position]) {
                positionData[position] = {
                    totalVotes: 0,
                    candidates: new Set(),
                    elections: new Set()
                };
            }
            positionData[position].totalVotes += election.votes[candidate] || 0;
            positionData[position].candidates.add(candidate);
            positionData[position].elections.add(election.title);
        });
    });

    if (Object.keys(positionData).length === 0) {
        positionStats.innerHTML = '<div class="no-data">No position data</div>';
        return;
    }

    // Sort by total votes and take top 6
    const topPositions = Object.entries(positionData)
        .sort((a, b) => b[1].totalVotes - a[1].totalVotes)
        .slice(0, 6);

    positionStats.innerHTML = topPositions.map(([position, data]) => {
        const avgVotes = (data.totalVotes / data.elections.size).toFixed(0);
        return `
            <div class="position-stat-item">
                <div class="position-name">${position}</div>
                <div class="position-votes">${data.totalVotes.toLocaleString()}</div>
                <div class="position-candidates">
                    ${data.candidates.size} candidates • ${avgVotes} avg per election
                </div>
            </div>
        `;
    }).join('');
}

/* ------------------ DETAILED BAR CHARTS ------------------ */
function renderBarCharts(elections) {
    BAR_CHARTS.forEach(c => c.destroy());
    BAR_CHARTS = [];

    document.querySelectorAll('.chart-container canvas').forEach(canvas => {
        const idx = parseInt(canvas.dataset.electionIndex);
        const election = ALL_ELECTIONS[idx];
        if (!election) return;

        const candidateRoles = election.candidate_roles || {};
        const candidateRolesWithId = election.candidate_roles_with_id || {};
        const labels = Object.keys(election.votes);
        const data = Object.values(election.votes);

        // Create array of candidates with their details
        const candidates = labels.map(name => ({
            name: name,
            votes: election.votes[name],
            role: candidateRoles[name],
            positionId: candidateRolesWithId[name]?.position_id || 999,
            color: candidateRolesWithId[name]?.color || '#adb5bd'
        }));

        // Sort candidates by position ID, then alphabetically
        candidates.sort((a, b) => {
            if (a.positionId !== b.positionId) {
                return a.positionId - b.positionId;
            }
            return a.name.localeCompare(b.name);
        });

        const sortedLabels = candidates.map(c => c.name);
        const sortedData = candidates.map(c => c.votes);
        const sortedColors = candidates.map(c => c.color);

        // Add/update legend (simplified - only show once)
        let legendContainer = canvas.parentNode.querySelector('.bar-legend');
        if (!legendContainer) {
            legendContainer = document.createElement('div');
            legendContainer.classList.add('bar-legend');
            legendContainer.style.display = 'flex';
            legendContainer.style.flexWrap = 'wrap';
            legendContainer.style.marginBottom = '10px';
            legendContainer.style.gap = '10px';
            canvas.parentNode.insertBefore(legendContainer, canvas);
        }
        
        // Only show legend for first chart to save space
        if (idx === 0) {
            const positionMap = new Map();
            candidates.forEach(c => {
                if (!positionMap.has(c.role)) {
                    positionMap.set(c.role, {
                        name: c.role,
                        color: c.color
                    });
                }
            });

            legendContainer.innerHTML = Array.from(positionMap.values())
                .map(({ name, color }) => `
                    <div style="display:flex; align-items:center; gap:5px; padding:2px 8px; background:rgba(0,0,0,0.03); border-radius:4px;">
                        <span style="display:inline-block; width:12px; height:12px; background:${color}; border-radius:3px;"></span>
                        <span style="font-size:11px;">${name}</span>
                    </div>
                `).join('');
        } else {
            legendContainer.innerHTML = ''; // Hide legends for other charts
        }

        const chart = new Chart(canvas, {
            type: 'bar',
            data: {
                labels: sortedLabels,
                datasets: [{
                    data: sortedData,
                    backgroundColor: sortedColors,
                    borderColor: sortedColors.map(c => c + '80'),
                    borderWidth: 1,
                    borderRadius: 4
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: { display: false },
                    tooltip: {
                        callbacks: {
                            label: (context) => {
                                const candidate = candidates[context.dataIndex];
                                return [
                                    `Votes: ${context.raw}`,
                                    `Position: ${candidate.role}`
                                ];
                            }
                        }
                    }
                },
                scales: {
                    y: {
                        beginAtZero: true,
                        title: {
                            display: true,
                            text: 'Votes'
                        }
                    }
                }
            }
        });

        BAR_CHARTS.push(chart);
    });
}

/* ------------------ INSIGHTS (Simplified) ------------------ */
function updateInsights(elections) {
    if (!elections.length) return;

    // Largest Election
    const largest = elections.reduce((a, b) => (a.total_voters || 0) > (b.total_voters || 0) ? a : b);
    document.getElementById('largestElection').textContent = largest.title;

    // Closest Margin
    const margins = elections
        .filter(e => e.winning_percentage !== undefined)
        .map(e => 100 - e.winning_percentage);

    const closest = margins.length ? Math.min(...margins).toFixed(1) : 0;
    document.getElementById('closestMarginInsight').textContent = `${closest}%`;
}

/* ------------------ CARD VISIBILITY ------------------ */
function updateElectionCards(elections) {
    document.querySelectorAll('.stat-card').forEach(card => {
        const title = card.querySelector('h3').textContent;
        card.style.display = elections.some(e => e.title === title) ? 'block' : 'none';
    });
}

/* ------------------ EXPORT ------------------ */
function exportPDF() {
    html2canvas(document.querySelector('.stats-page'), {
        scale: 2,
        backgroundColor: null,
        logging: false
    }).then(canvas => {
        const pdf = new jspdf.jsPDF('p', 'mm', 'a4');
        const imgWidth = pdf.internal.pageSize.getWidth();
        const imgHeight = (canvas.height * imgWidth) / canvas.width;
        
        pdf.addImage(canvas.toDataURL('image/png'), 'PNG', 0, 0, imgWidth, imgHeight);
        pdf.save('election_statistics.pdf');
    });
}