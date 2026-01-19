document.addEventListener('DOMContentLoaded', () => {
    const elections = JSON.parse(
        document.getElementById('dashboardElectionData').textContent
    );

    initDashboard(elections);
});

/* ------------------ GLOBALS ------------------ */
let activeBar = null;
const hiddenPositionsMap = {};

/* ------------------ INIT ------------------ */
function initDashboard(elections) {
    setupElectionDropdown(elections);
    drawMain(elections[0], 0);
    setupModal();
    setupProfileMenu();
}

/* ------------------ COLORS ------------------ */
const positionColors = {
    "President": "#36A2EB",
    "Vice President": "#FF69B4",
    "Secretary": "#FFA500",
    "Treasurer": "#32CD32",
    "Auditor": "#8A2BE2",
    "PIO": "#FF4500",
    "PRO": "#00CED1"
};

/* ------------------ DATA LABEL PLUGIN ------------------ */
const dataLabelsPlugin = {
    id: 'dataLabels',
    afterDatasetsDraw(chart) {
        const { ctx, data } = chart;
        const meta = chart.getDatasetMeta(0);

        ctx.save();
        meta.data.forEach((bar, index) => {
            const value = data.datasets[0].data[index];
            if (value === 0) return;

            const x = bar.x;
            const y = bar.y - 8;
            const text = value.toString();
            const width = ctx.measureText(text).width;

            ctx.fillStyle = 'rgba(0,0,0,0.7)';
            ctx.fillRect(x - width / 2 - 6, y - 16, width + 12, 20);

            ctx.fillStyle = '#fff';
            ctx.font = 'bold 12px Arial';
            ctx.textAlign = 'center';
            ctx.fillText(text, x, y - 6);
        });
        ctx.restore();
    }
};

/* ------------------ MAIN CHART ------------------ */
function drawMain(election, index) {
    const overlay = document.getElementById('noVotesOverlay');

    if (activeBar) activeBar.destroy();

    if (!hiddenPositionsMap[index]) {
        hiddenPositionsMap[index] = {};
        [...new Set(election.positions)].forEach(p => {
            hiddenPositionsMap[index][p] = false;
        });
    }

    const displayedVotes = election.positions.map((pos, i) =>
        hiddenPositionsMap[index][pos] ? 0 : election.votes[i]
    );

    overlay.style.display =
        displayedVotes.every(v => v === 0) ? 'flex' : 'none';

    activeBar = new Chart(document.getElementById('mainBar'), {
        type: 'bar',
        data: {
            labels: election.labels,
            datasets: [{
                data: displayedVotes,
                backgroundColor: election.positions.map(
                    p => positionColors[p] || "#888"
                ),
                borderRadius: 4
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            scales: { y: { beginAtZero: true } },
            plugins: { legend: { display: false } }
        },
        plugins: [dataLabelsPlugin]
    });

    document.getElementById('activeChartTitle').textContent = election.title;
    renderLegend(election, index);
}

/* ------------------ LEGEND ------------------ */
function renderLegend(election, index) {
    const legend = document.getElementById('colorLegend');
    legend.innerHTML = '';

    [...new Set(election.positions)].forEach(pos => {
        const item = document.createElement('span');
        item.style.cursor = 'pointer';
        item.style.marginRight = '10px';
        item.style.opacity = hiddenPositionsMap[index][pos] ? '0.4' : '1';

        item.innerHTML = `
            <span class="color-box"
                  style="background:${positionColors[pos] || '#888'}"></span>
            ${pos}
        `;

        item.onclick = () => {
            hiddenPositionsMap[index][pos] = !hiddenPositionsMap[index][pos];
            drawMain(election, index);
        };

        legend.appendChild(item);
    });
}

/* ------------------ DROPDOWN ------------------ */
function setupElectionDropdown(elections) {
    document
        .getElementById('electionSelect')
        .addEventListener('change', e => {
            const index = parseInt(e.target.value);
            drawMain(elections[index], index);
        });
}

/* ------------------ MODAL ------------------ */
function setupModal() {
    const modal = document.getElementById('recentElectionsModal');
    const btn = document.getElementById('seeMoreBtn');
    const close = document.querySelector('.close');

    if (btn) btn.onclick = () => modal.style.display = 'block';
    close.onclick = () => modal.style.display = 'none';

    window.addEventListener('click', e => {
        if (e.target === modal) modal.style.display = 'none';
    });
}

/* ------------------ PROFILE MENU ------------------ */
function setupProfileMenu() {
    const pic = document.getElementById('profilePic');
    const menu = document.getElementById('profileMenu');

    pic.addEventListener('click', e => {
        e.stopPropagation();
        menu.style.display =
            menu.style.display === 'block' ? 'none' : 'block';
    });

    window.addEventListener('click', () => {
        menu.style.display = 'none';
    });
}
