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
            
            // Find all theme toggle buttons
            this.findButtons();
            
            // Add click listeners to all buttons
            this.addClickListeners();
            
            // Update all buttons to match current theme
            this.updateAllButtons();
            
            // Listen for system theme changes
            this.listenForSystemChanges();
            
            // Mark as initialized
            window.themeManagerInitialized = true;
            
            console.log(`ThemeManager initialized with ${this.buttons.length} buttons`);
        }
        
        findButtons() {
            // Find sidebar button
            const sidebarBtn = document.getElementById('floatingThemeBtn');
            if (sidebarBtn) this.buttons.push(sidebarBtn);
            
            // Find header button (if on dashboard)
            const headerBtn = document.getElementById('headerThemeBtn');
            if (headerBtn) this.buttons.push(headerBtn);
            
            // Find any other theme buttons
            document.querySelectorAll('.theme-toggle-btn, [data-theme-toggle]').forEach(btn => {
                if (!this.buttons.includes(btn)) this.buttons.push(btn);
            });
        }
        
        addClickListeners() {
            this.buttons.forEach(btn => {
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
    console.log('ThemeManager already initialized, skipping...');
}