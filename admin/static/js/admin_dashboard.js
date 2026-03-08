document.addEventListener('DOMContentLoaded', () => {
    setupModal();
    // Profile menu removed
});

/* ------------------ MODAL ------------------ */
function setupModal() {
    const modal = document.getElementById('recentElectionsModal');
    const btn = document.getElementById('seeMoreBtn');
    const close = document.querySelector('.close');

    if (btn) {
        btn.onclick = () => {
            modal.style.display = 'block';
            document.body.classList.add('modal-open');
        };
    }
    
    if (close) {
        close.onclick = () => {
            modal.style.display = 'none';
            document.body.classList.remove('modal-open');
        };
    }

    window.addEventListener('click', e => {
        if (e.target === modal) {
            modal.style.display = 'none';
            document.body.classList.remove('modal-open');
        }
    });
}

/* Profile menu function removed */