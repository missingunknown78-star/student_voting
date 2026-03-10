// Theme management class
class ThemeManager {
    constructor() {
        this.themeToggle = document.getElementById('themeToggle');
        this.themeStatus = document.getElementById('themeStatus');
        this.toggleIcon = document.querySelector('.toggle-icon');
        this.toggleText = document.querySelector('.toggle-text');
        this.themeOptions = document.querySelectorAll('.theme-option');
        
        this.init();
    }
    
    init() {
        // Load saved theme or use system preference
        this.loadTheme();
        
        // Add event listeners
        this.themeToggle.addEventListener('click', () => this.cycleTheme());
        
        // Theme option buttons
        this.themeOptions.forEach(option => {
            option.addEventListener('click', (e) => {
                const theme = e.target.dataset.theme;
                this.setTheme(theme);
            });
        });
        
        // Listen for system theme changes
        window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', (e) => {
            this.handleSystemThemeChange(e);
        });
        
        // Update active state of theme options
        this.updateActiveOption();
    }
    
    loadTheme() {
        // Check for saved theme preference
        const savedTheme = localStorage.getItem('theme');
        
        if (savedTheme) {
            // Apply saved theme
            this.applyTheme(savedTheme);
            this.updateUI(savedTheme);
        } else {
            // Use system preference
            this.applyTheme('system');
            this.updateUI('system');
        }
    }
    
    applyTheme(theme) {
        const root = document.documentElement;
        const systemDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
        
        // Remove all theme classes first
        root.classList.remove('dark-mode', 'light-mode');
        
        switch(theme) {
            case 'dark':
                root.classList.add('dark-mode');
                break;
            case 'light':
                root.classList.add('light-mode');
                break;
            case 'system':
                // No class added - let CSS media query handle it
                // But we need to ensure we're not forcing a mode
                if (systemDark) {
                    // System is dark, but we don't add class
                    // This allows media query to work
                }
                break;
        }
        
        // Save preference
        if (theme === 'system') {
            localStorage.removeItem('theme');
        } else {
            localStorage.setItem('theme', theme);
        }
    }
    
    updateUI(theme) {
        // Update status text
        const systemDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
        let displayTheme = theme;
        
        if (theme === 'system') {
            displayTheme = systemDark ? 'Dark (System)' : 'Light (System)';
        } else {
            displayTheme = theme.charAt(0).toUpperCase() + theme.slice(1);
        }
        
        this.themeStatus.textContent = displayTheme;
        
        // Update toggle button icon and text
        const currentTheme = this.getCurrentTheme();
        if (currentTheme === 'dark') {
            this.toggleIcon.textContent = '☀️';
            this.toggleText.textContent = 'Light Mode';
        } else {
            this.toggleIcon.textContent = '🌙';
            this.toggleText.textContent = 'Dark Mode';
        }
        
        // Update active state of theme options
        this.updateActiveOption();
    }
    
    getCurrentTheme() {
        const root = document.documentElement;
        const systemDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
        
        if (root.classList.contains('dark-mode')) {
            return 'dark';
        } else if (root.classList.contains('light-mode')) {
            return 'light';
        } else {
            return systemDark ? 'dark' : 'light';
        }
    }
    
    cycleTheme() {
        const currentTheme = this.getCurrentTheme();
        const savedTheme = localStorage.getItem('theme');
        
        // Determine next theme
        if (savedTheme === 'dark') {
            this.setTheme('light');
        } else if (savedTheme === 'light') {
            this.setTheme('system');
        } else {
            // System mode or no saved theme
            if (currentTheme === 'dark') {
                this.setTheme('light');
            } else {
                this.setTheme('dark');
            }
        }
    }
    
    setTheme(theme) {
        this.applyTheme(theme);
        this.updateUI(theme);
    }
    
    handleSystemThemeChange(e) {
        const savedTheme = localStorage.getItem('theme');
        
        // Only auto-update if using system theme
        if (!savedTheme || savedTheme === 'system') {
            this.applyTheme('system');
            this.updateUI('system');
        }
    }
    
    updateActiveOption() {
        const savedTheme = localStorage.getItem('theme') || 'system';
        
        this.themeOptions.forEach(option => {
            const theme = option.dataset.theme;
            if (theme === savedTheme) {
                option.classList.add('active');
            } else {
                option.classList.remove('active');
            }
        });
    }
}

// Initialize theme manager when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    new ThemeManager();
});