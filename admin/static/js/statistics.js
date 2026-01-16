document.addEventListener('DOMContentLoaded', function() {
    // Load election data
    const electionData = JSON.parse(document.getElementById('electionData').textContent);
    
    // Initialize all components
    initKPIStats(electionData);
    initCharts(electionData);
    initFilters();
    initExportButton();
    initPeriodSelector();
    initSorting();
    calculateInsights(electionData);
});

function initKPIStats(elections) {
    if (elections.length === 0) return;
    
    // Calculate total votes
    const totalVotes = elections.reduce((sum, election) => {
        return sum + Object.values(election.votes).reduce((a, b) => a + b, 0);
    }, 0);
    
    document.querySelectorAll('.vote-progress-bar').forEach(bar => {
        bar.style.width = bar.dataset.width + "%";
    });
    

    // Calculate average participation (simulated)
    const avgParticipation = Math.round(elections.length > 0 ? 
        (elections.reduce((sum, election) => {
            const votes = Object.values(election.votes).reduce((a, b) => a + b, 0);
            return sum + (votes / 100); // Simplified participation rate
        }, 0) / elections.length) : 0);
    
    document.getElementById('avgParticipation').textContent = avgParticipation + '%';
    
    // Calculate closest margin
    let closestMargin = 100;
    elections.forEach(election => {
        const votes = Object.values(election.votes);
        const total = votes.reduce((a, b) => a + b, 0);
        if (total > 0) {
            const winnerVotes = election.votes[election.winner];
            const margin = ((winnerVotes / total) * 100).toFixed(1);
            if (margin < closestMargin) {
                closestMargin = margin;
            }
        }
    });
    
    document.getElementById('closestMargin').textContent = closestMargin + '%';
    
    // Update change indicators
    document.getElementById('votesChange').textContent = `+${totalVotes} total votes`;
    document.getElementById('participationChange').textContent = avgParticipation > 50 ? '+Good' : '-Needs Improvement';
    document.getElementById('marginChange').textContent = closestMargin < 10 ? '+Very Competitive' : '-Clear Wins';
}

function initCharts(elections) {
    if (elections.length === 0) {
        document.querySelectorAll('.chart-wrapper').forEach(wrapper => {
            wrapper.innerHTML = '<div class="no-data">No data available for charts</div>';
        });
        return;
    }
    
    // Election Type Distribution Chart
    const typeCtx = document.getElementById('typeDistributionChart').getContext('2d');
    const typeCounts = {};
    
    elections.forEach(election => {
        const type = election.election_type;
        typeCounts[type] = (typeCounts[type] || 0) + 1;
    });
    
    new Chart(typeCtx, {
        type: 'doughnut',
        data: {
            labels: Object.keys(typeCounts),
            datasets: [{
                data: Object.values(typeCounts),
                backgroundColor: ['#4dabf7', '#20c997', '#ff922b', '#e64980'],
                borderWidth: 2,
                borderColor: '#fff'
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            cutout: '70%',
            plugins: {
                legend: {
                    position: 'bottom',
                    labels: {
                        padding: 20,
                        font: { size: 12 }
                    }
                },
                tooltip: {
                    callbacks: {
                        label: function(context) {
                            return `${context.label}: ${context.raw} elections`;
                        }
                    }
                }
            }
        }
    });
    
    // Participation Trend Chart
    const trendCtx = document.getElementById('participationChart').getContext('2d');
    
    // Group by month
    const monthlyData = {};
    elections.forEach(election => {
        const month = election.end_date.substring(0, 7); // YYYY-MM
        const votes = Object.values(election.votes).reduce((a, b) => a + b, 0);
        monthlyData[month] = (monthlyData[month] || 0) + votes;
    });
    
    const sortedMonths = Object.keys(monthlyData).sort();
    
    new Chart(trendCtx, {
        type: 'line',
        data: {
            labels: sortedMonths,
            datasets: [{
                label: 'Votes Cast',
                data: sortedMonths.map(month => monthlyData[month]),
                borderColor: '#4dabf7',
                backgroundColor: 'rgba(77, 171, 247, 0.1)',
                borderWidth: 3,
                fill: true,
                tension: 0.4
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: { display: false }
            },
            scales: {
                y: {
                    beginAtZero: true,
                    title: {
                        display: true,
                        text: 'Number of Votes'
                    }
                },
                x: {
                    title: {
                        display: true,
                        text: 'Month'
                    }
                }
            }
        }
    });
    
    // Individual election charts
    document.querySelectorAll('.chart-container canvas').forEach((canvas, index) => {
        const election = elections[index];
        if (!election) return;
        
        const labels = Object.keys(election.votes);
        const data = Object.values(election.votes);
        const winner = election.winner;
        
        const colors = labels.map(label => {
            return label === winner ? 'rgba(241, 196, 15, 0.8)' : 'rgba(77, 171, 247, 0.7)';
        });
        
        new Chart(canvas.getContext('2d'), {
            type: 'bar',
            data: {
                labels: labels,
                datasets: [{
                    label: 'Votes',
                    data: data,
                    backgroundColor: colors,
                    borderColor: '#2c7be5',
                    borderWidth: 1
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                scales: {
                    y: {
                        beginAtZero: true,
                        ticks: { stepSize: 1 }
                    }
                },
                plugins: {
                    legend: { display: false },
                    tooltip: {
                        callbacks: {
                            label: function(context) {
                                const total = data.reduce((a, b) => a + b, 0);
                                const percentage = total > 0 ? ((context.raw / total) * 100).toFixed(1) : 0;
                                return `${context.label}: ${context.raw} votes (${percentage}%)`;
                            }
                        }
                    }
                }
            }
        });
    });
}

function initFilters() {
    const filterType = document.getElementById('filter-election-type');
    const filterDept = document.getElementById('filter-department');
    
    filterType.addEventListener('change', function() {
        const selected = this.value;
        
        if (selected === 'Department') {
            filterDept.style.display = 'inline-block';
        } else {
            filterDept.style.display = 'none';
            filterDept.value = 'all';
        }
        
        applyFilter();
    });
    
    filterDept.addEventListener('change', applyFilter);
    
    function applyFilter() {
        const type = filterType.value;
        const dept = filterDept.value;
        
        document.querySelectorAll('.stat-card').forEach(card => {
            const cardType = card.getAttribute('data-election-type');
            const cardDept = card.getAttribute('data-department');
            
            let show = false;
            
            if (type === 'all') {
                show = true;
            } else if (type === 'Wide' && cardType.toLowerCase() === 'ssg') {
                show = true;
            } else if (type === 'Department' && cardType === 'Department') {
                if (dept === 'all' || dept === cardDept) show = true;
            }
            
            card.style.display = show ? 'block' : 'none';
        });
        
        // Update KPI based on filtered results
        const visibleCards = document.querySelectorAll('.stat-card[style="display: block"]');
        updateFilteredKPI(visibleCards);
    }
}

function updateFilteredKPI(cards) {
    const total = cards.length;
    document.getElementById('totalElections').textContent = total;
    
    // Calculate filtered totals
    let totalVotes = 0;
    cards.forEach(card => {
        totalVotes += parseInt(card.getAttribute('data-total-votes') || 0);
    });
    
    document.getElementById('totalVotes').textContent = totalVotes.toLocaleString();
    document.getElementById('electionChange').textContent = `Showing ${total} elections`;
    document.getElementById('votesChange').textContent = `Showing ${totalVotes} votes`;
}

function initExportButton() {
    const exportBtn = document.getElementById('exportReport');
    
    exportBtn.addEventListener('click', function() {
        const originalHTML = this.innerHTML;
        
        // Show loading state
        this.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Generating Report...';
        this.disabled = true;
        
        // Simulate report generation
        setTimeout(() => {
            // Create downloadable report
            const reportData = {
                generatedAt: new Date().toISOString(),
                totalElections: document.getElementById('totalElections').textContent,
                totalVotes: document.getElementById('totalVotes').textContent,
                avgParticipation: document.getElementById('avgParticipation').textContent,
                closestMargin: document.getElementById('closestMargin').textContent
            };
            
            const blob = new Blob([JSON.stringify(reportData, null, 2)], { type: 'application/json' });
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `election-report-${new Date().toISOString().split('T')[0]}.json`;
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
            URL.revokeObjectURL(url);
            
            // Show success message
            const alert = document.createElement('div');
            alert.className = 'alert alert-success';
            alert.innerHTML = '<i class="fas fa-check-circle"></i> Report downloaded successfully!';
            alert.style.cssText = `
                position: fixed;
                top: 20px;
                right: 20px;
                padding: 15px 20px;
                background: #20c997;
                color: white;
                border-radius: 8px;
                z-index: 1000;
                box-shadow: 0 5px 15px rgba(0,0,0,0.2);
            `;
            document.body.appendChild(alert);
            
            setTimeout(() => {
                document.body.removeChild(alert);
            }, 3000);
            
            // Reset button
            this.innerHTML = originalHTML;
            this.disabled = false;
        }, 1500);
    });
}

function initPeriodSelector() {
    const periodBtns = document.querySelectorAll('.period-btn');
    
    periodBtns.forEach(btn => {
        btn.addEventListener('click', function() {
            periodBtns.forEach(b => b.classList.remove('active'));
            this.classList.add('active');
            
            // Filter cards by period (simplified - in real app would filter by date)
            const period = this.dataset.period;
            filterByPeriod(period);
        });
    });
}

function filterByPeriod(period) {
    const cards = document.querySelectorAll('.stat-card');
    const now = new Date();
    
    cards.forEach(card => {
        const endDateStr = card.getAttribute('data-end-date');
        if (!endDateStr) return;
        
        const endDate = new Date(endDateStr);
        let show = false;
        
        switch(period) {
            case 'all':
                show = true;
                break;
            case 'year':
                const oneYearAgo = new Date();
                oneYearAgo.setFullYear(now.getFullYear() - 1);
                show = endDate >= oneYearAgo;
                break;
            case 'month':
                const oneMonthAgo = new Date();
                oneMonthAgo.setMonth(now.getMonth() - 1);
                show = endDate >= oneMonthAgo;
                break;
            case 'week':
                const oneWeekAgo = new Date();
                oneWeekAgo.setDate(now.getDate() - 7);
                show = endDate >= oneWeekAgo;
                break;
        }
        
        card.style.display = show ? 'block' : 'none';
    });
    
    // Update KPI for filtered period
    const visibleCards = document.querySelectorAll('.stat-card[style="display: block"]');
    updateFilteredKPI(visibleCards);
}

function initSorting() {
    const sortSelect = document.getElementById('sort-by');
    
    sortSelect.addEventListener('change', function() {
        const container = document.querySelector('.detailed-stats');
        const cards = Array.from(document.querySelectorAll('.stat-card'));
        
        cards.sort((a, b) => {
            switch(this.value) {
                case 'date':
                    return new Date(b.getAttribute('data-end-date')) - new Date(a.getAttribute('data-end-date'));
                case 'date-oldest':
                    return new Date(a.getAttribute('data-end-date')) - new Date(b.getAttribute('data-end-date'));
                case 'votes':
                    return parseInt(b.getAttribute('data-total-votes')) - parseInt(a.getAttribute('data-total-votes'));
                case 'margin':
                    // Simplified margin calculation
                    const aVotes = parseInt(a.getAttribute('data-total-votes'));
                    const bVotes = parseInt(b.getAttribute('data-total-votes'));
                    const aCandidates = parseInt(a.getAttribute('data-candidate-count'));
                    const bCandidates = parseInt(b.getAttribute('data-candidate-count'));
                    const aAvg = aVotes / aCandidates;
                    const bAvg = bVotes / bCandidates;
                    return aAvg - bAvg; // Lower average = more competitive
            }
            return 0;
        });
        
        // Reorder cards in DOM
        cards.forEach(card => {
            container.appendChild(card);
        });
    });
}

function calculateInsights(elections) {
    if (elections.length === 0) return;
    
    // Most active month
    const monthCounts = {};
    elections.forEach(election => {
        const month = election.end_date.substring(0, 7); // YYYY-MM
        monthCounts[month] = (monthCounts[month] || 0) + 1;
    });
    
    let mostActiveMonth = '--';
    let maxCount = 0;
    Object.entries(monthCounts).forEach(([month, count]) => {
        if (count > maxCount) {
            maxCount = count;
            mostActiveMonth = month;
        }
    });
    
    document.getElementById('mostActiveMonth').textContent = mostActiveMonth;
    
    // Largest election
    let largestElection = '--';
    let maxVotes = 0;
    elections.forEach(election => {
        const votes = Object.values(election.votes).reduce((a, b) => a + b, 0);
        if (votes > maxVotes) {
            maxVotes = votes;
            largestElection = election.title;
        }
    });
    
    document.getElementById('largestElection').textContent = largestElection;
    
    // Average margin
    let totalMargin = 0;
    let count = 0;
    
    elections.forEach(election => {
        const votes = Object.values(election.votes);
        const total = votes.reduce((a, b) => a + b, 0);
        if (total > 0 && election.winner) {
            const winnerVotes = election.votes[election.winner];
            const margin = ((winnerVotes / total) * 100);
            totalMargin += margin;
            count++;
        }
    });
    
    const avgMargin = count > 0 ? (totalMargin / count).toFixed(1) : 0;
    document.getElementById('avgMargin').textContent = avgMargin + '%';
    
    // Average candidates
    const totalCandidates = elections.reduce((sum, election) => {
        return sum + Object.keys(election.votes).length;
    }, 0);
    
    const avgCandidates = (totalCandidates / elections.length).toFixed(1);
    document.getElementById('avgCandidates').textContent = avgCandidates;
}

// Add some utility styles dynamically
document.head.insertAdjacentHTML('beforeend', `
<style>
.alert {
    animation: slideIn 0.3s ease-out;
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

.fa-spin {
    animation: fa-spin 1s infinite linear;
}

@keyframes fa-spin {
    0% { transform: rotate(0deg); }
    100% { transform: rotate(360deg); }
}
</style>
`);