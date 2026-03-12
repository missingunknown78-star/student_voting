// ==================== SINGLE THEME MANAGER ====================

// Check if already initialized
if (!window.themeManagerInitialized) {
    
    class ThemeManager {
        constructor() {
            this.html = document.documentElement;
            this.buttons = [];
            this.init();
        }
        
        init() {
            console.log('ThemeManager initializing...');
            
            // Apply saved theme immediately
            this.applySavedTheme();
            
            // Find all theme toggle buttons
            this.findButtons();
            
            // Add click listeners to all buttons
            this.addClickListeners();
            
            // Update all buttons to match current theme
            this.updateAllButtons();
            
            // Listen for system theme changes
            this.listenForSystemChanges();
            
            // Listen for page navigation (for SPA-like behavior)
            this.listenForPageChanges();
            
            // Mark as initialized
            window.themeManagerInitialized = true;
            
            console.log(`ThemeManager initialized with ${this.buttons.length} buttons`);
        }
        
        applySavedTheme() {
            // Get theme from localStorage or default to dark
            const savedTheme = localStorage.getItem('theme') || 'dark';
            
            // Apply theme
            if (savedTheme === 'dark') {
                this.html.classList.add('dark-mode');
                this.html.classList.remove('light-mode');
            } else {
                this.html.classList.remove('dark-mode');
                this.html.classList.add('light-mode');
            }
            
            // Update color scheme
            this.html.style.colorScheme = savedTheme === 'dark' ? 'dark' : 'light';
            
            console.log('Applied saved theme:', savedTheme);
        }
        
        findButtons() {
            // Clear existing buttons array
            this.buttons = [];
            
            // Find sidebar button
            const sidebarBtn = document.getElementById('floatingThemeBtn');
            if (sidebarBtn) this.buttons.push(sidebarBtn);
            
            // Find header button (if on dashboard)
            const headerBtn = document.getElementById('headerThemeBtn');
            if (headerBtn) this.buttons.push(headerBtn);
            
            // Find content button in settings page
            const contentBtn = document.getElementById('contentThemeBtn');
            if (contentBtn) this.buttons.push(contentBtn);
            
            // Find any other theme buttons
            document.querySelectorAll('.theme-toggle-btn, [data-theme-toggle]').forEach(btn => {
                if (!this.buttons.includes(btn)) this.buttons.push(btn);
            });
        }
        
        addClickListeners() {
            this.buttons.forEach(btn => {
                if (!btn) return;
                
                // Remove any existing listeners by cloning
                const newBtn = btn.cloneNode(true);
                btn.parentNode.replaceChild(newBtn, btn);
                
                // Add fresh listener
                newBtn.addEventListener('click', (e) => {
                    e.preventDefault();
                    this.toggleTheme();
                });
                
                // Update reference
                const index = this.buttons.indexOf(btn);
                this.buttons[index] = newBtn;
            });
        }
        
        toggleTheme() {
            console.log('Toggling theme...');
            
            // Temporarily disable transitions
            this.html.classList.add('no-transition');
            
            // Toggle theme
            if (this.html.classList.contains('dark-mode')) {
                this.setTheme('light');
            } else {
                this.setTheme('dark');
            }
            
            // Re-enable transitions after a tiny delay
            setTimeout(() => {
                this.html.classList.remove('no-transition');
            }, 50);
        }
        
        setTheme(theme) {
            // Apply theme
            if (theme === 'dark') {
                this.html.classList.add('dark-mode');
                this.html.classList.remove('light-mode');
                localStorage.setItem('theme', 'dark');
            } else {
                this.html.classList.remove('dark-mode');
                this.html.classList.add('light-mode');
                localStorage.setItem('theme', 'light');
            }
            
            // Update color scheme
            this.html.style.colorScheme = theme === 'dark' ? 'dark' : 'light';
            
            // Update all buttons
            this.updateAllButtons();
            
            // Dispatch event for other components
            document.dispatchEvent(new CustomEvent('themeChanged', { 
                detail: { mode: theme } 
            }));
        }
        
        updateAllButtons() {
            const isDark = this.html.classList.contains('dark-mode');
            const icon = isDark ? 'fa-solid fa-moon' : 'fa-solid fa-sun';
            const title = isDark ? 'Switch to Light Mode' : 'Switch to Dark Mode';
            
            this.buttons.forEach(btn => {
                if (btn) {
                    btn.innerHTML = `<i class="${icon}"></i>`;
                    btn.title = title;
                }
            });
        }
        
        listenForSystemChanges() {
            window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', (e) => {
                // Only auto-update if user hasn't set a preference
                if (!localStorage.getItem('theme')) {
                    this.setTheme(e.matches ? 'dark' : 'light');
                }
            });
        }
        
        listenForPageChanges() {
            // Listen for popstate (back/forward navigation)
            window.addEventListener('popstate', () => {
                setTimeout(() => this.refresh(), 100);
            });
            
            // Listen for page show (when coming from cache/back button)
            window.addEventListener('pageshow', (event) => {
                if (event.persisted) {
                    setTimeout(() => this.refresh(), 100);
                }
            });
        }
        
        // Method to refresh theme manager (call when new content is loaded)
        refresh() {
            console.log('Refreshing ThemeManager...');
            this.findButtons();
            this.addClickListeners();
            this.updateAllButtons();
        }
    }

    // Initialize when DOM is ready
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', () => {
            window.themeManager = new ThemeManager();
        });
    } else {
        window.themeManager = new ThemeManager();
    }
} else {
    console.log('ThemeManager already initialized, refreshing...');
    // If already initialized, just refresh the buttons
    if (window.themeManager) {
        window.themeManager.refresh();
    }
}