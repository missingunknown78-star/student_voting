document.addEventListener('DOMContentLoaded', () => {
    setupModal();
    setupProfileMenu();
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
    
    close.onclick = () => {
        modal.style.display = 'none';
        document.body.classList.remove('modal-open');
    };

    window.addEventListener('click', e => {
        if (e.target === modal) {
            modal.style.display = 'none';
            document.body.classList.remove('modal-open');
        }
    });
}

/* ------------------ PROFILE MENU ------------------ */
function setupProfileMenu() {
    const pic = document.getElementById('profilePic');
    const menu = document.getElementById('profileMenu');

    if (pic && menu) {
        pic.addEventListener('click', e => {
            e.stopPropagation();
            menu.style.display =
                menu.style.display === 'block' ? 'none' : 'block';
        });

        window.addEventListener('click', () => {
            menu.style.display = 'none';
        });
    }
}