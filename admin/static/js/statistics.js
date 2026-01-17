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

    if (sortBy === 'date') return elections.sort((a, b) => new Date(b.end_date) - new Date(a.end_date));
    if (sortBy === 'date-oldest') return elections.sort((a, b) => new Date(a.end_date) - new Date(b.end_date));
    if (sortBy === 'votes') return elections.sort((a, b) => (b.total_voters || 0) - (a.total_voters || 0));
    if (sortBy === 'margin') return elections.sort((a, b) => (a.winning_percentage || 100) - (b.winning_percentage || 100));

    return elections;
}

/* ------------------ KPI ------------------ */
function updateKPIs(elections) {
    document.getElementById('totalElections').textContent = elections.length;

    const totalVoters = elections.reduce((sum, e) => sum + (e.total_voters || 0), 0);
    document.getElementById('totalVotedStudents').textContent = totalVoters;
    document.getElementById('votedStudentsChange').textContent = `${totalVoters} students`;

    const avgParticipation = elections.length ? (totalVoters / elections.length).toFixed(1) : 0;
    document.getElementById('avgParticipation').textContent = `${avgParticipation}%`;
}

/* ------------------ GLOBAL CHARTS ------------------ */
function updateCharts(elections) {
    if (typeChart) typeChart.destroy();
    if (trendChart) trendChart.destroy();
    if (!elections.length) return;

    const typeCounts = {};
    elections.forEach(e => typeCounts[e.election_type] = (typeCounts[e.election_type] || 0) + 1);

    typeChart = new Chart(document.getElementById('typeDistributionChart'), {
        type: 'doughnut',
        data: {
            labels: Object.keys(typeCounts),
            datasets: [{ data: Object.values(typeCounts) }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            cutout: '70%',
            plugins: { legend: { position: 'bottom' } }
        }
    });

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
                label: 'Voted Students',
                data: months.map(m => monthly[m]),
                fill: true,
                tension: 0.4
            }]
        },
        options: { responsive: true, maintainAspectRatio: false }
    });
}

/* ------------------ DETAILED BAR CHARTS ------------------ */
function renderBarCharts(elections) {
    BAR_CHARTS.forEach(c => c.destroy());
    BAR_CHARTS = [];

    // Color mapping per position
    const roleColors = {
        "President": "#4dabf7",
        "Vice President": "#20c997",
        "Secretary": "#ff922b",
        "Treasurer": "#e64980",
        "Auditor": "#845ef7",
        "Councilor": "#15aabf",
        "Other": "#adb5bd"
    };
    

    document.querySelectorAll('.chart-container canvas').forEach(canvas => {
        const idx = parseInt(canvas.dataset.electionIndex);
        const election = ALL_ELECTIONS[idx];
        if (!election) return;

        const candidateRoles = election.candidate_roles || {};
        const labels = Object.keys(election.votes);
        const data = Object.values(election.votes);

        // Map bar colors by candidate position
        const colors = labels.map(name => roleColors[candidateRoles[name]] || roleColors['Other']);

        // Add legend container if not exists
        let legendContainer = canvas.parentNode.querySelector('.bar-legend');
        if (!legendContainer) {
            legendContainer = document.createElement('div');
            legendContainer.classList.add('bar-legend');
            legendContainer.style.display = 'flex';
            legendContainer.style.flexWrap = 'wrap';
            legendContainer.style.marginBottom = '10px';
            canvas.parentNode.insertBefore(legendContainer, canvas);
        }
        legendContainer.innerHTML = '';

        Object.entries(roleColors).forEach(([role, color]) => {
            const item = document.createElement('div');
            item.style.display = 'flex';
            item.style.alignItems = 'center';
            item.style.marginRight = '10px';
            item.style.fontSize = '12px';

            const swatch = document.createElement('span');
            swatch.style.display = 'inline-block';
            swatch.style.width = '12px';
            swatch.style.height = '12px';
            swatch.style.backgroundColor = color;
            swatch.style.marginRight = '4px';
            swatch.style.borderRadius = '2px';

            item.appendChild(swatch);
            item.appendChild(document.createTextNode(role));
            legendContainer.appendChild(item);
        });

        const chart = new Chart(canvas, {
            type: 'bar',
            data: { labels, datasets: [{ data, backgroundColor: colors }] },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: { legend: { display: false } },
                scales: { y: { beginAtZero: true } }
            }
        });

        BAR_CHARTS.push(chart);
    });
}

/* ------------------ INSIGHTS ------------------ */
function updateInsights(elections) {
    if (!elections.length) return;

    const months = {};
    elections.forEach(e => {
        const m = e.end_date.substring(0, 7);
        months[m] = (months[m] || 0) + 1;
    });

    document.getElementById('mostActiveMonth').textContent =
        Object.entries(months).sort((a, b) => b[1] - a[1])[0][0];

    const largest = elections.reduce((a, b) => (a.total_voters || 0) > (b.total_voters || 0) ? a : b);
    document.getElementById('largestElection').textContent = largest.title;

    const margins = elections
        .filter(e => e.winning_percentage !== undefined)
        .map(e => 100 - e.winning_percentage);

    const closest = margins.length ? Math.min(...margins).toFixed(1) : 0;
    document.getElementById('closestMarginKPI').textContent = `${closest}%`;
    document.getElementById('closestMarginInsight').textContent = `${closest}%`;

    const avgCandidates = elections.length
        ? (elections.reduce((s, e) => s + Object.keys(e.votes).length, 0) / elections.length).toFixed(1)
        : 0;
    document.getElementById('avgCandidates').textContent = avgCandidates;
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
    html2canvas(document.querySelector('.stats-page'), { scale: 2 })
        .then(canvas => {
            const pdf = new jspdf.jsPDF('p', 'mm', 'a4');
            const w = pdf.internal.pageSize.getWidth();
            const h = (canvas.height * w) / canvas.width;
            pdf.addImage(canvas, 'PNG', 0, 0, w, h);
            pdf.save('election_statistics.pdf');
        });
}
