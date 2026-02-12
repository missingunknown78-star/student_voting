// Theme Toggle Functionality

// PREVENT FOUC - Apply theme IMMEDIATELY
(function() {
    const savedTheme = localStorage.getItem('theme');
    const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
    
    if (savedTheme === 'dark' || (!savedTheme && prefersDark)) {
        document.documentElement.classList.add('dark-mode');
    }
})();


document.addEventListener('DOMContentLoaded', function() {
    const themeToggle = document.getElementById('themeToggle');
    const themeLabel = document.getElementById('themeLabel');
    const body = document.body;
    
    // Check for saved theme or prefer-color-scheme
    const savedTheme = localStorage.getItem('theme');
    const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
    
    // Set initial theme
    if (savedTheme === 'dark' || (!savedTheme && prefersDark)) {
        enableDarkMode();
    } else {
        enableLightMode();
    }
    
    // Toggle theme on button click
    themeToggle.addEventListener('click', function() {
        if (body.classList.contains('dark-mode')) {
            enableLightMode();
        } else {
            enableDarkMode();
        }
    });
    
    function enableDarkMode() {
        body.classList.add('dark-mode');
        if (themeLabel) {
            themeLabel.textContent = 'Dark Mode';
        }
        localStorage.setItem('theme', 'dark');
        
        // Dispatch event for charts or other components
        document.dispatchEvent(new CustomEvent('themeChanged', { detail: { mode: 'dark' } }));
    }
    
    function enableLightMode() {
        body.classList.remove('dark-mode');
        if (themeLabel) {
            themeLabel.textContent = 'Light Mode';
        }
        localStorage.setItem('theme', 'light');
        
        // Dispatch event for charts or other components
        document.dispatchEvent(new CustomEvent('themeChanged', { detail: { mode: 'light' } }));
    }
    
    // Listen for system theme changes
    window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', e => {
        if (!localStorage.getItem('theme')) {
            if (e.matches) {
                enableDarkMode();
            } else {
                enableLightMode();
            }
        }
    });
});