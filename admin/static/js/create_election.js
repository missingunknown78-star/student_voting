// ================================
// CREATE/MANAGE ELECTIONS PAGE JAVASCRIPT
// ALL ORIGINAL FUNCTIONALITY PRESERVED
// ================================

// Ripple effect function
function createRipple(event, element) {
    const ripple = document.createElement('span');
    ripple.classList.add('ripple');
    
    const rect = element.getBoundingClientRect();
    const size = Math.max(rect.width, rect.height);
    const x = event.clientX - rect.left - size / 2;
    const y = event.clientY - rect.top - size / 2;
    
    ripple.style.width = ripple.style.height = `${size}px`;
    ripple.style.left = `${x}px`;
    ripple.style.top = `${y}px`;
    
    element.appendChild(ripple);
    
    setTimeout(() => {
        ripple.remove();
    }, 600);
}

// Add ripple effect to all create election buttons
function addRippleEffect() {
    const buttons = document.querySelectorAll('.create-election-btn');
    buttons.forEach(button => {
        button.addEventListener('click', function(e) {
            createRipple(e, this);
            this.classList.add('spinning');
            setTimeout(() => {
                this.classList.remove('spinning');
            }, 500);
        });
    });
}

// Modal functionality
const modal = document.getElementById('electionModal');
const openModalBtn = document.getElementById('openModalBtn');
const closeModalBtn = document.getElementById('closeModalBtn');
const emptyStateCreateBtn = document.getElementById('emptyStateCreateBtn');
const submitElectionBtn = document.getElementById('submitElectionBtn');

function openModal() {
    modal.classList.add('active');
    document.body.style.overflow = 'hidden';
    if (openModalBtn) {
        openModalBtn.classList.add('spinning');
        setTimeout(() => {
            openModalBtn.classList.remove('spinning');
        }, 500);
    }
}

function closeModal() {
    modal.classList.remove('active');
    document.body.style.overflow = '';
    resetForm();
}

// Toggle fields based on scope
function toggleFields() {
    const scope = document.getElementById('scope').value;
    const departmentRow = document.getElementById('department_row');
    const yearLevelRow = document.getElementById('year_level_row');
    const departmentSelect = document.getElementById('department_id');
    const yearCheckboxes = document.querySelectorAll('input[name="year_levels"]');
    
    if (scope === 'department') {
        departmentRow.style.display = 'block';
        yearLevelRow.style.display = 'none';
        departmentSelect.required = true;
        departmentSelect.disabled = false;
        
        yearCheckboxes.forEach(cb => {
            cb.disabled = true;
            cb.checked = false;
        });
    } else if (scope === 'campus') {
        departmentRow.style.display = 'none';
        yearLevelRow.style.display = 'block';
        departmentSelect.required = false;
        departmentSelect.disabled = true;
        departmentSelect.value = '';
        
        yearCheckboxes.forEach(cb => {
            cb.disabled = false;
        });
    } else {
        departmentRow.style.display = 'none';
        yearLevelRow.style.display = 'none';
        departmentSelect.required = false;
        departmentSelect.disabled = true;
        departmentSelect.value = '';
        
        yearCheckboxes.forEach(cb => {
            cb.disabled = true;
            cb.checked = false;
        });
    }
}

// Reset form
function resetForm() {
    const form = document.getElementById('electionForm');
    if (form) {
        form.reset();
    }
    toggleFields();
}

// Validate form
function validateForm() {
    const scope = document.getElementById('scope').value;
    const startDateInput = document.getElementById('start_date').value;
    const endDateInput = document.getElementById('end_date').value;
    
    if (!startDateInput || !endDateInput) {
        alert('Please select both start and end dates.');
        return false;
    }
    
    const startDate = new Date(startDateInput);
    const endDate = new Date(endDateInput);
    
    if (endDate <= startDate) {
        alert('End date must be later than start date.');
        return false;
    }
    
    if (scope === 'department') {
        const departmentId = document.getElementById('department_id').value;
        if (!departmentId) {
            alert('Please select a department for departmental election.');
            return false;
        }
    }
    
    if (scope === 'campus') {
        const yearCheckboxes = document.querySelectorAll('input[name="year_levels"]:checked');
        if (yearCheckboxes.length === 0) {
            if (!confirm('No year levels selected. This election will be available to ALL students. Continue?')) {
                return false;
            }
        }
    }
    
    return true;
}

// Handle form submission with circular spinner
function handleFormSubmit(e) {
    if (!validateForm()) {
        e.preventDefault();
        return;
    }
    
    if (submitElectionBtn) {
        submitElectionBtn.classList.add('submitting');
        submitElectionBtn.innerHTML = '<span class="spinner"></span> Creating Election...';
        submitElectionBtn.disabled = true;
    }
    
    return true;
}

// Auto-dismiss flash messages
function setupFlashMessages() {
    const flashMessages = document.querySelectorAll('.flash-message');
    
    flashMessages.forEach(message => {
        setTimeout(() => {
            if (message.parentElement) {
                message.style.animation = 'fadeOut 0.5s ease forwards';
                setTimeout(() => {
                    if (message.parentElement) {
                        message.remove();
                    }
                }, 500);
            }
        }, 7000);
        
        const closeBtn = message.querySelector('.close-btn');
        if (closeBtn) {
            closeBtn.addEventListener('click', function() {
                message.style.animation = 'fadeOut 0.5s ease forwards';
                setTimeout(() => {
                    if (message.parentElement) {
                        message.remove();
                    }
                }, 500);
            });
        }
    });
}

// Theme synchronization
function applyThemeToMainContent() {
    const mainContent = document.querySelector('.main-content');
    if (!mainContent) return;
    
    const savedTheme = localStorage.getItem('theme');
    const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
    const isDark = savedTheme === 'dark' || (!savedTheme && prefersDark);
    
    if (isDark) {
        mainContent.classList.add('dark-mode');
        document.documentElement.classList.add('dark-mode');
    } else {
        mainContent.classList.remove('dark-mode');
        document.documentElement.classList.remove('dark-mode');
    }
    
    mainContent.classList.add('theme-applied');
}

// Highlight sidebar link
function highlightCreateElectionLink() {
    const sidebarLinks = document.querySelectorAll('.sidebar-menu a, .nav-link, .sidebar a, .menu a');
    
    sidebarLinks.forEach(link => {
        link.classList.remove('active', 'current', 'selected', 'is-active');
        
        const parentLi = link.closest('li');
        if (parentLi) {
            parentLi.classList.remove('active', 'current', 'selected');
        }
    });
    
    sidebarLinks.forEach(link => {
        const href = link.getAttribute('href');
        const text = link.textContent || link.innerText;
        
        if (href && (href.includes('create_election') || href.includes('manage-elections') || href.includes('elections'))) {
            link.classList.add('active');
            
            const parentLi = link.closest('li');
            if (parentLi) {
                parentLi.classList.add('active');
            }
            
            const submenu = link.closest('.submenu, .dropdown-menu');
            if (submenu) {
                submenu.style.display = 'block';
                const parentToggle = submenu.previousElementSibling;
                if (parentToggle) {
                    parentToggle.classList.add('expanded', 'active');
                }
            }
        } else if (text.toLowerCase().includes('create election') || text.toLowerCase().includes('manage elections')) {
            link.classList.add('active');
            
            const parentLi = link.closest('li');
            if (parentLi) {
                parentLi.classList.add('active');
            }
            
            const submenu = link.closest('.submenu, .dropdown-menu');
            if (submenu) {
                submenu.style.display = 'block';
                const parentToggle = submenu.previousElementSibling;
                if (parentToggle) {
                    parentToggle.classList.add('expanded', 'active');
                }
            }
        }
    });
}

// Tab functionality
function initTabs() {
    const tabBtns = document.querySelectorAll('.tab-btn');
    const tabPanes = document.querySelectorAll('.tab-pane');

    tabBtns.forEach(btn => {
        btn.addEventListener('click', function() {
            const tabName = this.getAttribute('data-tab');
            
            tabBtns.forEach(b => b.classList.remove('active'));
            tabPanes.forEach(p => p.classList.remove('active'));
            
            this.classList.add('active');
            document.getElementById(`${tabName}-tab`).classList.add('active');
        });
    });
}

// Initialize on DOM ready
document.addEventListener('DOMContentLoaded', function() {
    applyThemeToMainContent();
    toggleFields();
    setupFlashMessages();
    addRippleEffect();
    initTabs();
    
    setTimeout(highlightCreateElectionLink, 50);
    
    const form = document.getElementById('electionForm');
    if (form) {
        form.addEventListener('submit', handleFormSubmit);
    }
    
    if (openModalBtn) openModalBtn.addEventListener('click', openModal);
    if (closeModalBtn) closeModalBtn.addEventListener('click', closeModal);
    
    if (emptyStateCreateBtn) {
        emptyStateCreateBtn.addEventListener('click', function(e) {
            createRipple(e, this);
            this.classList.add('spinning');
            setTimeout(() => {
                this.classList.remove('spinning');
            }, 500);
            openModal();
        });
    }
    
    // Close modal when clicking outside
    if (modal) {
        modal.addEventListener('click', function(e) {
            if (e.target === modal) {
                closeModal();
            }
        });
    }
    
    // Close modal on ESC key
    document.addEventListener('keydown', function(e) {
        if (e.key === 'Escape' && modal && modal.classList.contains('active')) {
            closeModal();
        }
    });
    
    const flashMessages = document.querySelectorAll('.flash-message.success, .flash-message.election-success');
    if (flashMessages.length > 0) {
        closeModal();
        if (submitElectionBtn) {
            submitElectionBtn.classList.remove('submitting');
            submitElectionBtn.innerHTML = '<span class="btn-icon"></span> Create Election';
            submitElectionBtn.disabled = false;
        }
    }
    
    window.addEventListener('pageshow', highlightCreateElectionLink);
    window.addEventListener('popstate', highlightCreateElectionLink);
});

window.addEventListener('load', highlightCreateElectionLink);