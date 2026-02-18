// ==================== ADMIN BASE JAVASCRIPT ====================
// Theme Toggle Functionality - Floating button only
document.addEventListener('DOMContentLoaded', function() {
    const floatingThemeBtn = document.getElementById('floatingThemeBtn');
    const floatingThemeIcon = floatingThemeBtn.querySelector('i');
    const mainContent = document.querySelector('.main-content');
    const body = document.body;
    
    // Ensure theme-applied class is added
    if (mainContent && !mainContent.classList.contains('theme-applied')) {
        mainContent.classList.add('theme-applied');
    }
    
    // Check current state from localStorage first
    const savedTheme = localStorage.getItem('theme');
    
    // If no theme saved, check system preference
    if (!savedTheme) {
        const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
        if (prefersDark) {
            // Apply to BOTH
            body.classList.add('dark-mode');
            mainContent.classList.add('dark-mode');
            localStorage.setItem('theme', 'dark');
        } else {
            // Remove from BOTH
            body.classList.remove('dark-mode');
            mainContent.classList.remove('dark-mode');
            localStorage.setItem('theme', 'light');
        }
    } else {
        // Apply saved theme to BOTH
        if (savedTheme === 'dark') {
            body.classList.add('dark-mode');
            mainContent.classList.add('dark-mode');
        } else {
            body.classList.remove('dark-mode');
            mainContent.classList.remove('dark-mode');
        }
    }
    
    // Now update button state
    const isDarkMode = mainContent.classList.contains('dark-mode');
    
    if (isDarkMode) {
        // Dark mode is active
        floatingThemeIcon.className = 'fa-solid fa-sun';
        floatingThemeBtn.title = 'Switch to Light Mode';
    } else {
        // Light mode is active
        floatingThemeIcon.className = 'fa-solid fa-moon';
        floatingThemeBtn.title = 'Switch to Dark Mode';
    }
    
    // Toggle theme on floating button click
    floatingThemeBtn.addEventListener('click', function() {
        toggleTheme();
    });
    
    function toggleTheme() {
        if (mainContent.classList.contains('dark-mode')) {
            enableLightMode();
        } else {
            enableDarkMode();
        }
    }
    
    function enableDarkMode() {
        // Apply to BOTH body and main-content
        body.classList.add('dark-mode');
        mainContent.classList.add('dark-mode');
        floatingThemeIcon.className = 'fa-solid fa-sun';
        floatingThemeBtn.title = 'Switch to Light Mode';
        localStorage.setItem('theme', 'dark');
    }
    
    function enableLightMode() {
        // Remove from BOTH body and main-content
        body.classList.remove('dark-mode');
        mainContent.classList.remove('dark-mode');
        floatingThemeIcon.className = 'fa-solid fa-moon';
        floatingThemeBtn.title = 'Switch to Dark Mode';
        localStorage.setItem('theme', 'light');
    }
    
    // Listen for system theme changes (only if user hasn't set preference)
    window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', e => {
        if (!localStorage.getItem('theme')) {
            if (e.matches) {
                enableDarkMode();
            } else {
                enableLightMode();
            }
        }
    });
    
    // =============== SIDEBAR SCROLL POSITION REMEMBER ===============
    
    const sidebar = document.getElementById('sidebar');
    
    // Save scroll position when clicking any sidebar link (except logout)
    const sidebarLinks = document.querySelectorAll('.sidebar-nav a:not([href*="logout"])');
    
    sidebarLinks.forEach(link => {
        link.addEventListener('click', function(e) {
            // Don't save for disabled links
            if (this.classList.contains('disabled-link')) return;
            
            // Save current scroll position to localStorage
            localStorage.setItem('sidebarScrollPosition', sidebar.scrollTop);
            
            // Also save which link was clicked (for good measure)
            localStorage.setItem('lastClickedLink', this.href);
        });
    });
    
    // Restore scroll position when page loads
    function restoreSidebarScroll() {
        const savedPosition = localStorage.getItem('sidebarScrollPosition');
        if (savedPosition && sidebar) {
            // Use a small delay to ensure DOM is fully rendered
            setTimeout(() => {
                sidebar.scrollTop = parseInt(savedPosition);
            }, 50);
        }
    }
    
    // Restore on page load
    restoreSidebarScroll();
    
    // Also restore when page is fully loaded (in case images or other content loads later)
    window.addEventListener('load', function() {
        // Small additional delay to account for any late-loading content
        setTimeout(restoreSidebarScroll, 100);
    });
    
    // =============== REMEMBER ACTIVE LINK VISIBILITY ===============
    
    // Function to ensure active link is visible
    function scrollToActiveLink() {
        const activeLink = document.querySelector('.sidebar-nav a.active');
        if (activeLink && sidebar) {
            // Calculate the position of the active link relative to the sidebar
            const linkTop = activeLink.offsetTop;
            const linkHeight = activeLink.offsetHeight;
            const sidebarHeight = sidebar.clientHeight;
            
            // If the link is not in view, scroll to it
            if (linkTop < sidebar.scrollTop || linkTop + linkHeight > sidebar.scrollTop + sidebarHeight) {
                // Scroll to make the active link centered if possible
                const scrollToPosition = linkTop - (sidebarHeight / 2) + (linkHeight / 2);
                sidebar.scrollTop = Math.max(0, scrollToPosition);
            }
        }
    }
    
    // Try to scroll to active link on page load
    setTimeout(scrollToActiveLink, 200);
});

// =============== EXPOSE FUNCTIONS GLOBALLY IF NEEDED ===============
// Make theme functions available globally for other scripts if needed
window.AdminBase = {
    enableDarkMode: function() {
        const mainContent = document.querySelector('.main-content');
        const body = document.body;
        const floatingThemeIcon = document.querySelector('#floatingThemeBtn i');
        const floatingThemeBtn = document.getElementById('floatingThemeBtn');
        
        // Apply to BOTH
        body.classList.add('dark-mode');
        mainContent.classList.add('dark-mode');
        if (floatingThemeIcon) floatingThemeIcon.className = 'fa-solid fa-sun';
        if (floatingThemeBtn) floatingThemeBtn.title = 'Switch to Light Mode';
        localStorage.setItem('theme', 'dark');
    },
    
    enableLightMode: function() {
        const mainContent = document.querySelector('.main-content');
        const body = document.body;
        const floatingThemeIcon = document.querySelector('#floatingThemeBtn i');
        const floatingThemeBtn = document.getElementById('floatingThemeBtn');
        
        // Remove from BOTH
        body.classList.remove('dark-mode');
        mainContent.classList.remove('dark-mode');
        if (floatingThemeIcon) floatingThemeIcon.className = 'fa-solid fa-moon';
        if (floatingThemeBtn) floatingThemeBtn.title = 'Switch to Dark Mode';
        localStorage.setItem('theme', 'light');
    },
    
    toggleTheme: function() {
        const mainContent = document.querySelector('.main-content');
        if (mainContent.classList.contains('dark-mode')) {
            this.enableLightMode();
        } else {
            this.enableDarkMode();
        }
    },
    
    restoreSidebarScroll: function() {
        const sidebar = document.getElementById('sidebar');
        const savedPosition = localStorage.getItem('sidebarScrollPosition');
        if (savedPosition && sidebar) {
            sidebar.scrollTop = parseInt(savedPosition);
        }
    },
    
    scrollToActiveLink: function() {
        const sidebar = document.getElementById('sidebar');
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
};