// ==================== ADMIN BASE JAVASCRIPT ====================
// Only sidebar functionality - NO THEME CODE

document.addEventListener('DOMContentLoaded', function() {
    const sidebar = document.getElementById('sidebar');
    
    // =============== SIDEBAR SCROLL POSITION REMEMBER ===============
    const sidebarLinks = document.querySelectorAll('.sidebar-nav a:not([href*="logout"])');
    
    sidebarLinks.forEach(link => {
        link.addEventListener('click', function(e) {
            if (this.classList.contains('disabled-link')) return;
            localStorage.setItem('sidebarScrollPosition', sidebar.scrollTop);
        });
    });
    
    function restoreSidebarScroll() {
        const savedPosition = localStorage.getItem('sidebarScrollPosition');
        if (savedPosition && sidebar) {
            setTimeout(() => {
                sidebar.scrollTop = parseInt(savedPosition);
            }, 50);
        }
    }
    
    restoreSidebarScroll();
    
    window.addEventListener('load', function() {
        setTimeout(restoreSidebarScroll, 100);
    });
    
    // =============== SCROLL TO ACTIVE LINK ===============
    function scrollToActiveLink() {
        const activeLink = document.querySelector('.sidebar-nav a.active');
        if (activeLink && sidebar) {
            const linkTop = activeLink.offsetTop;
            const linkHeight = activeLink.offsetHeight;
            const sidebarHeight = sidebar.clientHeight;
            
            if (linkTop < sidebar.scrollTop || linkTop + linkHeight > sidebar.scrollTop + sidebarHeight) {
                const scrollToPosition = linkTop - (sidebarHeight / 2) + (linkHeight / 2);
                sidebar.scrollTop = Math.max(0, scrollToPosition);
            }
        }
    }
    
    setTimeout(scrollToActiveLink, 200);
});