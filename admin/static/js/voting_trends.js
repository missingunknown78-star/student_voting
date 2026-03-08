// Voting Trends Chart - Fixed Version with School Year Support

class VotingTrends {
    constructor() {
        this.chart = null;
        this.currentElectionId = 'all';
        this.currentSchoolYear = this.getCurrentSchoolYear();
        this.init();
    }

    getCurrentSchoolYear() {
        const schoolYearSelect = document.getElementById('schoolYearSelect');
        return schoolYearSelect ? schoolYearSelect.value : '';
    }

    async init() {
        console.log("VotingTrends initialized with school year:", this.currentSchoolYear);
        this.showLoading();
        await this.loadElections();
        
        // Listen for school year changes
        const schoolYearSelect = document.getElementById('schoolYearSelect');
        if (schoolYearSelect) {
            schoolYearSelect.addEventListener('change', (e) => {
                this.currentSchoolYear = e.target.value;
                this.refreshData();
            });
        }
    }

    showLoading() {
        const container = document.querySelector('.chart-container');
        if (container) {
            container.innerHTML = `
                <div class="chart-loading">
                    <div class="spinner"></div>
                    <p style="margin-top: 10px; color: #64748b;">Loading voting data...</p>
                </div>
            `;
        }
    }

    async refreshData() {
        console.log("Refreshing data with school year:", this.currentSchoolYear);
        this.showLoading();
        await this.loadElections();
    }

    buildApiUrl(endpoint, electionId = null) {
        let url = endpoint;
        const params = new URLSearchParams();
        
        if (electionId !== null) {
            params.append('election_id', electionId);
        }
        
        if (this.currentSchoolYear) {
            params.append('school_year', this.currentSchoolYear);
        }
        
        const queryString = params.toString();
        if (queryString) {
            url += '?' + queryString;
        }
        
        return url;
    }

    async loadElections() {
        try {
            console.log("Fetching voting trends...");
            const url = this.buildApiUrl('/admin/api/voting-trends', this.currentElectionId);
            console.log("Fetching from:", url);
            
            const response = await fetch(url);
            console.log("Response status:", response.status);
            
            const data = await response.json();
            console.log("Received data:", data);
            
            if (!data.success) {
                throw new Error(data.error || 'Failed to load');
            }
            
            this.renderFilterButtons(data.elections);
            
            // Check if we have any votes
            const hasVotes = data.data.some(v => v > 0);
            console.log("Has votes:", hasVotes);
            
            this.renderChart(data.labels, data.data);
            await this.loadElectionStats(this.currentElectionId);
            
        } catch (error) {
            console.error('Error:', error);
            this.showError(error.message);
        }
    }

    renderFilterButtons(elections) {
        const container = document.getElementById('electionFilters');
        if (!container) {
            console.error("Election filters container not found");
            return;
        }

        let html = '';
        elections.forEach(election => {
            // Add emoji based on scope
            let emoji = '📊';
            if (election.scope === 'campus') emoji = '🏛️';
            if (election.scope === 'department') emoji = '📚';
            
            // Add status indicator
            const statusIndicator = election.status_emoji || '';
            
            html += `
                <button class="election-filter-btn ${this.currentElectionId == election.id ? 'active' : ''}" 
                        data-election-id="${election.id}">
                    ${statusIndicator} ${emoji} ${election.name}
                    <span class="vote-count-badge">${election.total_votes} votes</span>
                </button>
            `;
        });
        container.innerHTML = html;
        
        // Add click event listeners
        container.querySelectorAll('.election-filter-btn').forEach(btn => {
            btn.addEventListener('click', () => {
                const electionId = btn.dataset.electionId;
                this.switchElection(electionId, btn);
            });
        });
    }

    async switchElection(electionId, button) {
        console.log("Switching to election:", electionId);
        
        // Update active button
        document.querySelectorAll('.election-filter-btn').forEach(btn => {
            btn.classList.remove('active');
        });
        button.classList.add('active');
        
        this.currentElectionId = electionId;
        this.showLoading();
        
        try {
            const url = this.buildApiUrl('/admin/api/voting-trends', electionId);
            const response = await fetch(url);
            const data = await response.json();
            
            this.renderChart(data.labels, data.data);
            await this.loadElectionStats(electionId);
            
        } catch (error) {
            console.error('Error switching:', error);
            this.showError(error.message);
        }
    }

    async loadElectionStats(electionId) {
        try {
            const url = this.buildApiUrl(`/admin/api/election-stats/${electionId}`, electionId);
            const response = await fetch(url);
            const stats = await response.json();
            console.log("Stats received:", stats);
            
            if (stats.success) {
                document.getElementById('totalVotes').textContent = stats.total_votes || 0;
                document.getElementById('eligibleVoters').textContent = stats.total_eligible || 0;
                document.getElementById('turnoutPercent').textContent = stats.turnout || '0%';
                
                let titleText = stats.election_title || 'All Elections Combined';
                if (stats.election_scope) {
                    titleText += ` (${stats.election_scope})`;
                }
                if (stats.election_status) {
                    const statusEmoji = stats.election_status === 'Open' ? '🟢' : 
                                       stats.election_status === 'Upcoming' ? '🟡' : '🔴';
                    titleText += ` ${statusEmoji} ${stats.election_status}`;
                }
                
                // Add school year to title if filtered
                if (this.currentSchoolYear) {
                    titleText += ` | School Year: ${this.currentSchoolYear}`;
                }
                
                document.getElementById('currentElectionTitle').textContent = titleText;
            }
        } catch (error) {
            console.error('Error loading stats:', error);
        }
    }

    renderChart(labels, data) {
        console.log("Rendering chart with:", {labels, data});
        
        const container = document.querySelector('.chart-container');
        if (!container) return;
        
        // Check if we have any data points with votes
        const hasVotes = data.some(v => v > 0);
        
        if (!hasVotes) {
            const totalVotes = data.reduce((a, b) => a + b, 0);
            container.innerHTML = `
                <div class="no-data-message">
                    <i class="fa-solid fa-chart-line fa-2x" style="margin-bottom: 10px; opacity: 0.5;"></i>
                    <p>No votes cast in the last 24 hours</p>
                    <p style="font-size: 0.8rem; margin-top: 5px;">
                        Total votes in selected period: ${totalVotes}
                        ${this.currentSchoolYear ? `<br>School Year: ${this.currentSchoolYear}` : ''}
                    </p>
                </div>
            `;
            return;
        }

        // Ensure container has canvas
        if (!container.querySelector('canvas')) {
            container.innerHTML = '<canvas id="votingTrendsChart"></canvas>';
        }

        const canvas = document.getElementById('votingTrendsChart');
        if (!canvas) return;
        
        const ctx = canvas.getContext('2d');
        
        // Destroy existing chart
        if (this.chart) {
            this.chart.destroy();
        }

        // Find the maximum value for better y-axis scaling
        const maxVotes = Math.max(...data);
        const yMax = maxVotes + 1; // Add 1 for better visualization

        // Create gradient
        const gradient = ctx.createLinearGradient(0, 0, 0, 300);
        gradient.addColorStop(0, 'rgba(59, 130, 246, 0.5)');
        gradient.addColorStop(1, 'rgba(59, 130, 246, 0.0)');

        // Create chart
        this.chart = new Chart(ctx, {
            type: 'line',
            data: {
                labels: labels,
                datasets: [{
                    label: 'Votes Cast',
                    data: data,
                    borderColor: '#3b82f6',
                    backgroundColor: gradient,
                    borderWidth: 3,
                    pointBackgroundColor: '#3b82f6',
                    pointBorderColor: 'white',
                    pointBorderWidth: 2,
                    pointRadius: 4,
                    pointHoverRadius: 6,
                    pointStyle: 'circle',
                    tension: 0.3,
                    fill: true
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
                        backgroundColor: '#0f172a',
                        titleColor: '#e2e8f0',
                        bodyColor: '#94a3b8',
                        borderColor: '#334155',
                        borderWidth: 1,
                        padding: 10,
                        displayColors: false,
                        callbacks: {
                            label: (context) => {
                                const value = context.raw;
                                return `${value} vote${value !== 1 ? 's' : ''}`;
                            }
                        }
                    }
                },
                scales: {
                    y: {
                        beginAtZero: true,
                        max: yMax,
                        grid: {
                            color: '#e2e8f0',
                            drawBorder: false
                        },
                        ticks: {
                            stepSize: 1,
                            callback: function(value) {
                                return Number.isInteger(value) ? value : '';
                            }
                        },
                        title: {
                            display: true,
                            text: 'Number of Votes',
                            color: '#64748b',
                            font: {
                                size: 10
                            }
                        }
                    },
                    x: {
                        grid: {
                            display: false
                        },
                        ticks: {
                            maxRotation: 45,
                            minRotation: 45,
                            maxTicksLimit: 12,
                            font: {
                                size: 10
                            }
                        },
                        title: {
                            display: true,
                            text: 'Time (Last 24 Hours)',
                            color: '#64748b',
                            font: {
                                size: 10
                            }
                        }
                    }
                }
            }
        });
    }

    showError(message) {
        const container = document.querySelector('.chart-container');
        if (container) {
            container.innerHTML = `
                <div class="no-data-message">
                    <i class="fa-solid fa-exclamation-triangle fa-2x" style="color: #ef4444; margin-bottom: 10px;"></i>
                    <p>Error loading voting trends</p>
                    <p style="font-size: 0.8rem;">${message || 'Please try refreshing the page'}</p>
                    ${this.currentSchoolYear ? `<p style="font-size: 0.8rem; margin-top: 5px;">School Year: ${this.currentSchoolYear}</p>` : ''}
                </div>
            `;
        }
    }
}

// Initialize when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    // Check if we're on a page with voting trends
    const chartContainer = document.querySelector('.chart-container');
    const chartCanvas = document.getElementById('votingTrendsChart');
    
    if (chartContainer || chartCanvas) {
        console.log("Initializing VotingTrends");
        window.votingTrends = new VotingTrends();
    }
});

// Also re-initialize if the page loads via TurboLinks or similar
document.addEventListener('turbolinks:load', () => {
    if (document.querySelector('.chart-container') || document.getElementById('votingTrendsChart')) {
        if (!window.votingTrends) {
            window.votingTrends = new VotingTrends();
        }
    }
});