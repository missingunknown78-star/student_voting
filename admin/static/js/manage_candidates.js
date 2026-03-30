/* PHOTO LIGHTBOX */
// manage_candidates.js - Updated with school year support and platform field
// All notifications now float above the modal

// CSRF Token Helper Function
function getCsrfToken() {
    const metaTag = document.querySelector('meta[name="csrf-token"]');
    return metaTag ? metaTag.getAttribute('content') : '';
}

document.addEventListener('DOMContentLoaded', function() {
    console.log("Manage Candidates JS loaded");
    
    // Display school year info if filtered
    displaySchoolYearInfo();
    
    // Initialize modals
    initModals();
    
    // Initialize filters
    initFilters();
    
    // Initialize search
    initSearch();
    
    // Initialize delete buttons
    initDeleteButtons();
    
    // Initialize edit buttons
    initEditButtons();
    
    // Initialize photo click handlers
    initPhotoClick();
    
    // Initialize add candidate button
    initAddCandidate();
    
    // Initialize scope toggle in add modal
    const addScope = document.getElementById('add_scope');
    if (addScope) {
        addScope.addEventListener('change', function() {
            filterElectionsByScope('add');
        });
    }
    
    // Initialize scope toggle in edit modal
    const editScope = document.getElementById('edit_scope');
    if (editScope) {
        editScope.addEventListener('change', function() {
            filterElectionsByScope('edit');
        });
    }
    
    // Initialize election filter in add modal
    const addElection = document.getElementById('add_election');
    if (addElection) {
        addElection.addEventListener('change', function() {
            filterPositionsByElection('add');
        });
    }
    
    // Initialize election filter in edit modal
    const editElection = document.getElementById('edit_election');
    if (editElection) {
        editElection.addEventListener('change', function() {
            filterPositionsByElection('edit');
        });
    }
    
    // Initialize department change for course loading
    const addDepartment = document.getElementById('add_department');
    if (addDepartment) {
        addDepartment.addEventListener('change', function() {
            loadCourses('add', this.value);
        });
    }
    
    const editDepartment = document.getElementById('edit_department');
    if (editDepartment) {
        editDepartment.addEventListener('change', function() {
            loadCourses('edit', this.value);
        });
    }
    
    // Initialize reset button
    const resetBtn = document.getElementById('reset_filter');
    if (resetBtn) {
        resetBtn.addEventListener('click', function() {
            resetFilters();
        });
    }
    
    // FIX: Re-attach edit button listeners after AJAX updates
    // Use MutationObserver to detect when new edit buttons are added
    const observer = new MutationObserver(function(mutations) {
        mutations.forEach(function(mutation) {
            if (mutation.type === 'childList' && mutation.addedNodes.length > 0) {
                // Check if any added nodes contain edit buttons
                attachEditButtonListeners();
            }
        });
    });
    
    // Start observing the table body for changes
    const tableBody = document.getElementById('candidatesTableBody');
    if (tableBody) {
        observer.observe(tableBody, { childList: true, subtree: true });
    }
});

// Function to attach edit button listeners to all edit buttons
function attachEditButtonListeners() {
    document.querySelectorAll('.openEditModal').forEach(btn => {
        // Remove existing listeners to prevent duplicates
        btn.removeEventListener('click', handleEditClick);
        btn.addEventListener('click', handleEditClick);
    });
}

// Handle edit button click - WITH PLATFORM HANDLING
function handleEditClick(e) {
    e.preventDefault();
    
    // Reset the edit button state before opening modal
    resetEditButtonState();
    
    const btn = this;
    const id = btn.dataset.id;
    document.getElementById('edit_id').value = id;
    document.getElementById('edit_first').value = btn.dataset.first;
    document.getElementById('edit_last').value = btn.dataset.last;
    document.getElementById('edit_party_list').value = btn.dataset.party || '';
    
    // Set year level if available
    if (btn.dataset.year_level_id) {
        document.getElementById('edit_year_level').value = btn.dataset.year_level_id;
    }
    
    // Set platform if available - FIXED: Handle platform correctly
    if (btn.dataset.platform) {
        document.getElementById('edit_platform').value = btn.dataset.platform;
    } else {
        document.getElementById('edit_platform').value = '';
    }
    
    document.getElementById('edit_position').value = btn.dataset.position;
    
    // Handle scope and department
    const scope = btn.dataset.scope || 'campus';
    document.getElementById('edit_scope').value = scope;
    
    // Set department
    document.getElementById('edit_department').value = btn.dataset.department_id || '';
    
    // Load courses for the department
    if (btn.dataset.department_id) {
        // Set a timeout to ensure courses are loaded before setting the value
        loadCourses('edit', btn.dataset.department_id).then(() => {
            // Set course after courses are loaded
            if (btn.dataset.course_id) {
                setTimeout(() => {
                    document.getElementById('edit_course').value = btn.dataset.course_id;
                }, 100);
            }
        });
    } else {
        // Clear course dropdown if no department
        const courseSelect = document.getElementById('edit_course');
        courseSelect.innerHTML = '<option value="">Select course</option>';
    }
    
    // Get the election select element
    const editElection = document.getElementById('edit_election');
    
    // First, hide all options
    for (let i = 0; i < editElection.options.length; i++) {
        editElection.options[i].style.display = 'none';
    }
    
    // Show the placeholder option
    for (let i = 0; i < editElection.options.length; i++) {
        if (editElection.options[i].value === "") {
            editElection.options[i].style.display = 'block';
            break;
        }
    }
    
    if (scope === 'department') {
        // Show only department elections for the selected department
        const departmentId = btn.dataset.department_id;
        if (departmentId) {
            for (let i = 0; i < editElection.options.length; i++) {
                const option = editElection.options[i];
                if (option.value === "") continue;
                
                const optionScope = option.getAttribute('data-scope');
                const optionDept = option.getAttribute('data-department');
                
                if (optionScope === 'department' && optionDept === departmentId) {
                    option.style.display = 'block';
                }
            }
        }
    } else {
        // Show only campus elections
        for (let i = 0; i < editElection.options.length; i++) {
            const option = editElection.options[i];
            if (option.value === "") {
                option.style.display = 'block'; // Keep placeholder visible
                continue;
            }
            
            const optionScope = option.getAttribute('data-scope');
            if (optionScope === 'campus') {
                option.style.display = 'block';
            }
        }
    }
    
    // Set the election value after filtering
    document.getElementById('edit_election').value = btn.dataset.election;

    // Hide any existing notifications in edit modal
    const editNotification = document.getElementById('editCandidateNotification');
    if (editNotification) {
        editNotification.style.display = 'none';
    }
    
    document.getElementById('editCandidateModal').style.display = 'flex';
}

// Display school year info if filtered
function displaySchoolYearInfo() {
    // Check if there's a school year badge already in the DOM
    const existingBadge = document.querySelector('.school-year-badge');
    if (existingBadge) {
        console.log("School year filter active:", existingBadge.textContent);
    }
}

// Initialize functions (placeholders - implement as needed)
function initModals() {}
function initFilters() {}
function initSearch() {}
function initDeleteButtons() {}
function initEditButtons() {
    attachEditButtonListeners();
}
function initPhotoClick() {}
function initAddCandidate() {}

/* PHOTO LIGHTBOX */
document.querySelectorAll('.clickable-photo').forEach(img => {
    img.onclick = () => {
        document.getElementById('lightbox').style.display = 'flex';
        document.getElementById('lightbox-img').src = img.src;
    };
});

function closeLightbox() {
    document.getElementById('lightbox').style.display = 'none';
}

/* ADD MODAL */
const openAddBtn = document.getElementById('openAddCandidate');
if (openAddBtn) {
    openAddBtn.onclick = e => {
        e.preventDefault();
        document.getElementById('addCandidateModal').style.display = 'flex';
        
        // Reset form and clear any notifications
        document.getElementById('addCandidateForm').reset();
        
        // Hide any existing notifications
        const addNotification = document.getElementById('addCandidateNotification');
        if (addNotification) {
            addNotification.style.display = 'none';
        }
        
        // Clear course dropdown
        const addCourse = document.getElementById('add_course');
        addCourse.innerHTML = '<option value="">Select course</option>';
        
        // Clear platform field
        const addPlatform = document.getElementById('add_platform');
        if (addPlatform) {
            addPlatform.value = '';
        }
        
        // Hide ALL election options initially
        const addElection = document.getElementById('add_election');
        for (let i = 0; i < addElection.options.length; i++) {
            addElection.options[i].style.display = 'none';
        }
        
        // Show the placeholder option only
        for (let i = 0; i < addElection.options.length; i++) {
            if (addElection.options[i].value === "") {
                addElection.options[i].style.display = 'block';
                break;
            }
        }
    };
}

function closeAddCandidateModal() {
    document.getElementById('addCandidateModal').style.display = 'none';
    document.getElementById('addCandidateForm').reset();
    
    // Clear any notification
    const addNotification = document.getElementById('addCandidateNotification');
    if (addNotification) {
        addNotification.style.display = 'none';
    }
}

/* EDIT MODAL - REMOVED OLD EVENT LISTENERS, using new handleEditClick function */

// Helper function to reset edit button state
function resetEditButtonState() {
    const editSubmitBtn = document.getElementById('editCandidateSubmitBtn');
    if (editSubmitBtn) {
        editSubmitBtn.disabled = false;
        const buttonText = editSubmitBtn.querySelector('.button-text');
        const spinner = editSubmitBtn.querySelector('.loading-spinner');
        if (buttonText) {
            buttonText.innerHTML = 'Update Candidate';
            buttonText.style.opacity = '1';
        }
        if (spinner) spinner.style.display = 'none';
    }
}

function closeEditModal() {
    document.getElementById('editCandidateModal').style.display = 'none';
    document.getElementById('editCandidateForm').reset();
    
    // Clear any notification
    const editNotification = document.getElementById('editCandidateNotification');
    if (editNotification) {
        editNotification.style.display = 'none';
    }
    
    // Reset the edit button state
    resetEditButtonState();
}

/* Function to load courses based on department selection */
function loadCourses(mode, departmentId) {
    return new Promise((resolve, reject) => {
        const courseSelect = document.getElementById(mode + '_course');
        
        // Clear current options
        courseSelect.innerHTML = '<option value="">Select course</option>';
        
        if (!departmentId) {
            resolve();
            return;
        }
        
        // Show loading state
        const loadingOption = document.createElement('option');
        loadingOption.value = '';
        loadingOption.textContent = 'Loading courses...';
        loadingOption.disabled = true;
        courseSelect.appendChild(loadingOption);
        
        // FIXED: Use the correct endpoint with slashes, not hyphens
        fetch(`/ctumoalboal-comelec/courses/by_department/${departmentId}`, {
            headers: {
                'X-CSRFToken': getCsrfToken()
            }
        })
            .then(response => {
                if (!response.ok) {
                    throw new Error('Network response was not ok');
                }
                return response.json();
            })
            .then(data => {
                // Clear loading option
                courseSelect.innerHTML = '<option value="">Select course</option>';
                
                if (data.courses && data.courses.length > 0) {
                    data.courses.forEach(course => {
                        const option = document.createElement('option');
                        option.value = course.id;
                        option.textContent = course.course_name + (course.course_code ? ` (${course.course_code})` : '');
                        courseSelect.appendChild(option);
                    });
                }
                resolve();
            })
            .catch(err => {
                console.error('Error loading courses:', err);
                courseSelect.innerHTML = '<option value="">Error loading courses</option>';
                reject(err);
            });
    });
}

/* Filter elections by scope */
function filterElectionsByScope(mode) {
    const scope = document.getElementById(mode + '_scope').value;
    const electionSelect = document.getElementById(mode + '_election');
    const options = electionSelect.options;
    
    // First, hide all options
    for (let i = 0; i < options.length; i++) {
        options[i].style.display = 'none';
    }
    
    // Show the placeholder option
    for (let i = 0; i < options.length; i++) {
        if (options[i].value === "") {
            options[i].style.display = 'block';
            break;
        }
    }
    
    if (scope === 'department') {
        // Get selected department
        const departmentId = document.getElementById(mode + '_department').value;
        
        if (departmentId) {
            // Show only department elections for the selected department
            for (let i = 0; i < options.length; i++) {
                const option = options[i];
                if (option.value === "") continue;
                
                const optionScope = option.getAttribute('data-scope');
                const optionDept = option.getAttribute('data-department');
                
                if (optionScope === 'department' && optionDept === departmentId) {
                    option.style.display = 'block';
                }
            }
        }
    } else if (scope === 'campus') {
        // Show only campus elections
        for (let i = 0; i < options.length; i++) {
            const option = options[i];
            if (option.value === "") {
                option.style.display = 'block'; // Keep placeholder visible
                continue;
            }
            
            const optionScope = option.getAttribute('data-scope');
            if (optionScope === 'campus') {
                option.style.display = 'block';
            }
        }
    }
}

/* Validate department and course before submission - REQUIRED FOR ALL */
function validateDepartmentAndCourse(mode) {
    const deptSelect = document.getElementById(mode + '_department');
    const courseSelect = document.getElementById(mode + '_course');
    
    if (!deptSelect.value) {
        showFloatingNotification('Please select a department', 'error');
        deptSelect.focus();
        return false;
    }
    if (!courseSelect.value) {
        showFloatingNotification('Please select a course', 'error');
        courseSelect.focus();
        return false;
    }
    
    return true;
}

// Add change listeners for department dropdowns
document.addEventListener('DOMContentLoaded', function() {
    // Add department change listener
    const addDept = document.getElementById('add_department');
    if (addDept) {
        addDept.addEventListener('change', function() {
            const scope = document.getElementById('add_scope').value;
            if (scope === 'department') {
                filterElectionsByScope('add');
            }
            // Load courses when department changes
            loadCourses('add', this.value);
        });
    }
    
    // Edit department change listener
    const editDept = document.getElementById('edit_department');
    if (editDept) {
        editDept.addEventListener('change', function() {
            const scope = document.getElementById('edit_scope').value;
            if (scope === 'department') {
                filterElectionsByScope('edit');
            }
            // Load courses when department changes
            loadCourses('edit', this.value);
        });
    }

    // Add scope change listener for add modal
    const addScope = document.getElementById('add_scope');
    if (addScope) {
        addScope.addEventListener('change', function() {
            filterElectionsByScope('add');
        });
    }
    
    // Add scope change listener for edit modal
    const editScope = document.getElementById('edit_scope');
    if (editScope) {
        editScope.addEventListener('change', function() {
            filterElectionsByScope('edit');
        });
    }

    // Initialize add modal state
    const addElection = document.getElementById('add_election');
    if (addElection) {
        // Hide all options initially
        for (let i = 0; i < addElection.options.length; i++) {
            addElection.options[i].style.display = 'none';
        }
        // Show the placeholder option
        for (let i = 0; i < addElection.options.length; i++) {
            if (addElection.options[i].value === "") {
                addElection.options[i].style.display = 'block';
                break;
            }
        }
    }

    // Initialize filter listeners
    initFilterListeners();
    
    // Initial attachment of pagination listeners
    setTimeout(function() {
        attachPaginationListeners();
    }, 200);
});

/* ============ AJAX FILTER FUNCTION WITH LOADING SPINNER ============ */
function filterCandidates(page = null, keepPage = false) {
    const scope = document.getElementById('filter_scope').value;
    const departmentId = document.getElementById('filter_department').value;
    const search = document.getElementById('search_input').value;
    
    // Get current page from URL or pagination
    let currentPage = 1;
    
    if (page !== null) {
        currentPage = page;
    } else if (keepPage) {
        // Try to get page from current pagination
        const currentPageElement = document.querySelector('.pagination .current');
        if (currentPageElement) {
            currentPage = parseInt(currentPageElement.textContent);
        } else {
            // Try to get from URL
            const urlParams = new URLSearchParams(window.location.search);
            const urlPage = urlParams.get('page');
            if (urlPage) {
                currentPage = parseInt(urlPage);
            }
        }
    }

    // Show loading state on search button
    const searchBtn = document.getElementById('search_btn');
    const buttonText = searchBtn.querySelector('.button-text');
    const spinner = searchBtn.querySelector('.loading-spinner');
    
    buttonText.style.display = 'none';
    spinner.style.display = 'inline-block';
    searchBtn.disabled = true;

    // Show loading state on table
    const tableContainer = document.getElementById('table-container');
    tableContainer.classList.add('table-loading');

    // Build URL with query parameters
    let url = `/ctumoalboal-comelec/candidates/filter?page=${currentPage}`;
    if (scope) url += `&scope=${scope}`;
    if (departmentId) url += `&department_id=${departmentId}`;
    if (search) url += `&search=${encodeURIComponent(search)}`;

    // Update browser URL without reload
    const newUrl = new URL(window.location);
    newUrl.searchParams.set('page', currentPage);
    if (scope) newUrl.searchParams.set('scope', scope);
    else newUrl.searchParams.delete('scope');
    
    if (departmentId) newUrl.searchParams.set('department_id', departmentId);
    else newUrl.searchParams.delete('department_id');
    
    if (search) newUrl.searchParams.set('search', search);
    else newUrl.searchParams.delete('search');
    
    window.history.pushState({}, '', newUrl);

    return fetch(url, {
        method: 'GET',
        headers: {
            'X-Requested-With': 'XMLHttpRequest',
            'X-CSRFToken': getCsrfToken()
        }
    })
    .then(res => {
        if (!res.ok) {
            throw new Error('Network response was not ok');
        }
        return res.json();
    })
    .then(data => {
        updateTable(data.candidates, data.pagination);
        updatePagination(data.pagination);
    })
    .catch(err => {
        console.error('Error:', err);
        showFloatingNotification('Error filtering candidates', 'error');
    })
    .finally(() => {
        // Hide loading states
        buttonText.style.display = 'inline-block';
        spinner.style.display = 'none';
        searchBtn.disabled = false;
        tableContainer.classList.remove('table-loading');
    });
}

/* Update table with new data - MODIFIED to show beautiful empty state */
function updateTable(candidates, pagination) {
    const tbody = document.getElementById('candidatesTableBody');
    if (!tbody) return;

    if (!candidates || candidates.length === 0) {
        // Create beautiful empty state with 7 columns colspan
        tbody.innerHTML = `
            <tr>
                <td colspan="7" style="padding: 0;">
                    <div class="no-candidates-container">
                        <div class="no-candidates-icon">
                            <i class="fa-solid fa-user-slash"></i>
                        </div>
                        <h3 class="no-candidates-title">No Candidates Found</h3>
                        <p class="no-candidates-message">
                            No candidates match your current filter criteria. Try adjusting your filters or add a new candidate.
                        </p>
                        <div class="no-candidates-suggestions">
                            <div class="suggestion-item highlight" onclick="document.getElementById('openAddCandidate').click()">
                                <i class="fa-solid fa-user-plus"></i>
                                <span>Add New Candidate</span>
                            </div>
                            <div class="suggestion-item" onclick="resetFilters()">
                                <i class="fa-solid fa-eraser"></i>
                                <span>Clear Filters</span>
                            </div>
                        </div>
                    </div>
                </td>
            </tr>
        `;
        return;
    }

    let html = '';
    candidates.forEach(c => {
        const scopeClass = c.scope || 'campus';
        const scopeDisplay = scopeClass.charAt(0).toUpperCase() + scopeClass.slice(1);
        const electionTitle = escapeHtml(c.election_title) || 'No Election';
        
        html += `
            <tr id="candidate-${c.id}">
                <td>
                    ${c.photo ? 
                        `<img src="${c.photo}" class="candidate-photo clickable-photo" alt="Candidate Photo">` : 
                        '<span>No Photo</span>'}
                </td>
                <td>${escapeHtml(c.first_name || '')} ${escapeHtml(c.last_name || '')}</td>
                <td>${escapeHtml(c.party_list) || 'Independent'}</td>
                <td>${escapeHtml(c.department) || 'N/A'}</td>
                <td>${escapeHtml(c.position) || ''}</td>
                <td>
                    <div class="election-info">
                        <span class="election-title">${electionTitle}</span>
                        <span class="scope-badge ${scopeClass}">${scopeDisplay}</span>
                    </div>
                </td>
                <td>
                    <div class="action-buttons">
                        <a href="#" class="edit-btn openEditModal" 
                        data-id="${c.id}" 
                        data-first="${escapeHtml(c.first_name) || ''}" 
                        data-last="${escapeHtml(c.last_name) || ''}" 
                        data-party="${escapeHtml(c.party_list) || ''}"
                        data-platform="${escapeHtml(c.platform) || ''}"
                        data-year_level_id="${c.year_level_id || ''}"
                        data-year_level_name="${escapeHtml(c.year_level) || ''}"
                        data-position="${c.position_id || ''}" 
                        data-election="${c.election_id || ''}" 
                        data-department="${escapeHtml(c.department) || ''}"
                        data-department_id="${c.department_id || ''}"
                        data-course_id="${c.course_id || ''}"
                        data-scope="${c.scope || 'campus'}">Edit</a>
                        <a href="#" class="delete-btn delete-candidate" data-id="${c.id}">Delete</a>
                    </div>
                </td>
            </tr>
        `;
    });

    tbody.innerHTML = html;

    // Re-attach event listeners to new elements
    attachEventListeners();
}

// Helper function to reset filters
function resetFilters() {
    document.getElementById('filter_scope').value = '';
    document.getElementById('filter_department').value = '';
    document.getElementById('filter_department').style.display = 'none';
    document.getElementById('search_input').value = '';
    filterCandidates(1, false);
}

/* ===== PAGINATION FUNCTIONS ===== */
/* Update pagination links */
function updatePagination(pagination) {
    const container = document.getElementById('pagination-container');
    if (!container) return;

    if (pagination.total_pages <= 1) {
        container.innerHTML = '';
        return;
    }

    let html = '<div class="pagination">';
    
    // Previous button
    if (pagination.has_prev) {
        html += `<a href="#" class="pagination-link" data-page="${pagination.prev_page}">&laquo; Prev</a>`;
    } else {
        html += '<span class="disabled">&laquo; Prev</span>';
    }

    // Page numbers
    for (let p = 1; p <= pagination.total_pages; p++) {
        if (p === pagination.current_page) {
            html += `<span class="current">${p}</span>`;
        } else {
            html += `<a href="#" class="pagination-link" data-page="${p}">${p}</a>`;
        }
    }

    // Next button
    if (pagination.has_next) {
        html += `<a href="#" class="pagination-link" data-page="${pagination.next_page}">Next &raquo;</a>`;
    } else {
        html += '<span class="disabled">Next &raquo;</span>';
    }

    html += '</div>';
    container.innerHTML = html;

    // Attach pagination listeners
    attachPaginationListeners();
}

/* Attach pagination listeners */
function attachPaginationListeners() {
    const paginationLinks = document.querySelectorAll('.pagination-link');
    paginationLinks.forEach(link => {
        // Remove any existing listeners to prevent duplicates
        link.removeEventListener('click', handlePaginationClick);
        link.addEventListener('click', handlePaginationClick);
    });
}

/* Handle pagination click */
function handlePaginationClick(e) {
    e.preventDefault();
    const page = parseInt(this.dataset.page);
    filterCandidates(page, true);
}

/* Escape HTML to prevent XSS */
function escapeHtml(text) {
    if (!text) return text;
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

/* Attach event listeners to dynamically added elements */
function attachEventListeners() {
    // Photo lightbox
    document.querySelectorAll('.clickable-photo').forEach(img => {
        img.onclick = () => {
            document.getElementById('lightbox').style.display = 'flex';
            document.getElementById('lightbox-img').src = img.src;
        };
    });

    // Edit modal triggers - use the handler function
    attachEditButtonListeners();

    // Delete buttons
    document.querySelectorAll('.delete-candidate').forEach(btn => {
        btn.onclick = function(e) {
            e.preventDefault();
            e.stopPropagation();
            deleteCandidate(this.dataset.id);
        };
    });
}

/* Initialize filter listeners */
function initFilterListeners() {
    const filterScope = document.getElementById('filter_scope');
    const filterDepartment = document.getElementById('filter_department');
    const searchBtn = document.getElementById('search_btn');
    const searchInput = document.getElementById('search_input');
    const resetBtn = document.getElementById('reset_filter');

    // Update department visibility
    function updateFilterDepartment() {
        if (filterScope.value === 'department') {
            filterDepartment.style.display = 'inline-block';
        } else {
            filterDepartment.style.display = 'none';
            filterDepartment.value = "";
        }
    }

    filterScope.addEventListener('change', () => {
        updateFilterDepartment();
        filterCandidates(1, false); // Reset to page 1 when filter changes
    });

    filterDepartment.addEventListener('change', () => {
        filterCandidates(1, false); // Reset to page 1 when filter changes
    });

    searchBtn.addEventListener('click', () => {
        filterCandidates(1, false); // Reset to page 1 when search
    });

    searchInput.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') {
            e.preventDefault();
            filterCandidates(1, false); // Reset to page 1 when search
        }
    });

    resetBtn.addEventListener('click', () => {
        filterScope.value = '';
        filterDepartment.value = '';
        filterDepartment.style.display = 'none';
        searchInput.value = '';
        filterCandidates(1, false); // Reset to page 1
    });

    // Initial call to set department visibility
    updateFilterDepartment();
}

/* ---------- FLOATING NOTIFICATION FUNCTION (ABOVE MODAL) ---------- */
function showFloatingNotification(message, type) {
    // Remove any existing floating notifications
    const existingNotification = document.querySelector('.floating-notification');
    if (existingNotification) {
        existingNotification.remove();
    }
    
    // Create floating notification element
    const notification = document.createElement('div');
    notification.className = `floating-notification ${type}`;
    
    // Add icon based on type
    const icon = type === 'success' ? 'fa-check-circle' : 'fa-exclamation-circle';
    
    notification.innerHTML = `
        <div class="notification-content">
            <i class="fa ${icon}"></i>
            <div class="notification-message">${message}</div>
            <button class="notification-close" onclick="this.parentElement.parentElement.remove()">
                <i class="fa fa-times"></i>
            </button>
        </div>
    `;
    
    // Style the notification
    notification.style.cssText = `
        position: fixed;
        top: 80px;
        left: 50%;
        transform: translateX(-50%);
        z-index: 100000;
        min-width: 300px;
        max-width: 450px;
        animation: slideDown 0.3s ease-out;
        box-shadow: 0 10px 25px rgba(0,0,0,0.2);
        border-radius: 8px;
        overflow: hidden;
        pointer-events: all;
    `;
    
    // Style the content based on type
    const colors = type === 'success' 
        ? { bg: 'linear-gradient(135deg, #00c851, #00a844)', border: '#007e33' }
        : { bg: 'linear-gradient(135deg, #ff4444, #cc0000)', border: '#a70000' };
    
    notification.querySelector('.notification-content').style.cssText = `
        display: flex;
        align-items: center;
        gap: 12px;
        padding: 14px 20px;
        background: ${colors.bg};
        color: white;
        font-size: 0.95rem;
        font-weight: 500;
        border-left: 5px solid ${colors.border};
        text-shadow: 0 1px 2px rgba(0,0,0,0.1);
    `;
    
    // Style the close button
    const closeBtn = notification.querySelector('.notification-close');
    closeBtn.style.cssText = `
        background: none;
        border: none;
        color: white;
        cursor: pointer;
        font-size: 1.2rem;
        margin-left: auto;
        padding: 0 8px;
        opacity: 0.8;
        transition: opacity 0.2s;
    `;
    closeBtn.onmouseover = () => closeBtn.style.opacity = '1';
    closeBtn.onmouseout = () => closeBtn.style.opacity = '0.8';
    
    // Style the icon
    notification.querySelector('i:first-child').style.cssText = `
        font-size: 1.4rem;
        filter: drop-shadow(0 2px 4px rgba(0,0,0,0.2));
    `;
    
    // Style the message
    notification.querySelector('.notification-message').style.cssText = `
        flex: 1;
        line-height: 1.4;
        word-break: break-word;
    `;
    
    document.body.appendChild(notification);
    
    // Auto hide after 4 seconds
    setTimeout(() => {
        if (notification.parentNode) {
            notification.style.animation = 'slideUp 0.3s ease-out forwards';
            setTimeout(() => {
                if (notification.parentNode) {
                    notification.remove();
                }
            }, 300);
        }
    }, 4000);
}

/* ---------- AJAX SUBMIT FOR ADD CANDIDATE WITH PLATFORM SUPPORT ---------- */
const addCandidateForm = document.getElementById('addCandidateForm');
const addSubmitBtn = document.getElementById('addCandidateSubmitBtn');

if (addCandidateForm) {
    addCandidateForm.addEventListener('submit', async function(e) {
        e.preventDefault();

        // Validate department and course (required for ALL)
        if (!validateDepartmentAndCourse('add')) {
            return; // Stop form submission
        }

        // Validate student first using the function from student_validation.js
        if (typeof validateBeforeSubmit === 'function') {
            const isValid = await validateBeforeSubmit();
            if (!isValid) {
                return; // Stop form submission
            }
        }

        // Show loading state
        addSubmitBtn.disabled = true;
        const buttonText = addSubmitBtn.querySelector('.button-text');
        const spinner = addSubmitBtn.querySelector('.loading-spinner');
        if (buttonText) {
            buttonText.innerHTML = 'Adding...';
            buttonText.style.opacity = '0.7';
        }
        if (spinner) spinner.style.display = 'inline-block';

        const formData = new FormData(this);

        fetch("/ctumoalboal-comelec/candidates", {
            method: 'POST',
            body: formData,
            headers: {
                'X-Requested-With': 'XMLHttpRequest',
                'X-CSRFToken': getCsrfToken()
            }
        })
        .then(res => {
            const contentType = res.headers.get('content-type');
            if (contentType && contentType.includes('application/json')) {
                return res.json();
            } else {
                return res.text().then(text => {
                    if (text.includes('<!DOCTYPE html>')) {
                        throw new Error('Server returned HTML instead of JSON. Possible authentication or routing error.');
                    }
                    return { success: true, message: 'Candidate added successfully!' };
                });
            }
        })
        .then(data => {
            if(data.success) {
                // Show floating success notification
                showFloatingNotification('✓ Candidate added successfully!', 'success');
                
                // Refresh the table with current filters but keep page
                filterCandidates(null, true);

                // Reset form fields but KEEP MODAL OPEN
                addCandidateForm.reset();
                document.getElementById('add_scope').value = '';
                
                // Clear course dropdown
                const addCourse = document.getElementById('add_course');
                addCourse.innerHTML = '<option value="">Select course</option>';
                
                // Clear platform field
                const addPlatform = document.getElementById('add_platform');
                if (addPlatform) {
                    addPlatform.value = '';
                }
                
                // Reset election dropdown - hide all and show placeholder only
                const addElection = document.getElementById('add_election');
                for (let i = 0; i < addElection.options.length; i++) {
                    addElection.options[i].style.display = 'none';
                }
                // Show placeholder option
                for (let i = 0; i < addElection.options.length; i++) {
                    if (addElection.options[i].value === "") {
                        addElection.options[i].style.display = 'block';
                        break;
                    }
                }

            } else {
                // Show floating error notification
                showFloatingNotification('✗ ' + (data.message || 'Failed to add candidate.'), 'error');
            }
        })
        .catch(err => {
            console.error('Error:', err);
            showFloatingNotification('✗ ' + (err.message || 'Error adding candidate'), 'error');
        })
        .finally(() => {
            // Hide loading state
            addSubmitBtn.disabled = false;
            if (buttonText) {
                buttonText.innerHTML = 'Add Candidate';
                buttonText.style.opacity = '1';
            }
            if (spinner) spinner.style.display = 'none';
        });
    });
}

/* ---------- AJAX SUBMIT FOR EDIT CANDIDATE - WITH PLATFORM SUPPORT ---------- */
const editCandidateForm = document.getElementById('editCandidateForm');
const editSubmitBtn = document.getElementById('editCandidateSubmitBtn');

if (editCandidateForm) {
    editCandidateForm.addEventListener('submit', function(e) {
        e.preventDefault();

        // Validate department and course (required for ALL)
        if (!validateDepartmentAndCourse('edit')) {
            return; // Stop form submission
        }

        // Show loading state - change button text to "Updating..."
        editSubmitBtn.disabled = true;
        const buttonText = editSubmitBtn.querySelector('.button-text');
        const spinner = editSubmitBtn.querySelector('.loading-spinner');
        
        if (buttonText) {
            buttonText.innerHTML = 'Updating...';
            buttonText.style.opacity = '0.7';
        }
        if (spinner) spinner.style.display = 'inline-block';

        const formData = new FormData(this);
        const candidateId = document.getElementById('edit_id').value;

        fetch(`/ctumoalboal-comelec/candidates/edit/${candidateId}`, {
            method: 'POST',
            body: formData,
            headers: {
                'X-Requested-With': 'XMLHttpRequest',
                'X-CSRFToken': getCsrfToken()
            }
        })
        .then(res => {
            const contentType = res.headers.get('content-type');
            if (contentType && contentType.includes('application/json')) {
                return res.json();
            } else {
                return res.text().then(text => {
                    if (text.includes('<!DOCTYPE html>')) {
                        throw new Error('Server returned HTML instead of JSON. Possible authentication or routing error.');
                    }
                    return { success: true, message: 'Candidate updated successfully!' };
                });
            }
        })
        .then(data => {
            if(data.success) {
                // Show floating success notification
                showFloatingNotification('✓ Candidate updated successfully!', 'success');
                
                // Refresh the table with current filters but keep page
                filterCandidates(null, true);
                
                // CLOSE THE EDIT MODAL
                closeEditModal();

            } else {
                // Show floating error notification and keep modal open
                showFloatingNotification('✗ ' + (data.message || 'Failed to update candidate.'), 'error');
                
                // Reset button state but keep modal open
                editSubmitBtn.disabled = false;
                if (buttonText) {
                    buttonText.innerHTML = 'Update Candidate';
                    buttonText.style.opacity = '1';
                }
                if (spinner) spinner.style.display = 'none';
            }
        })
        .catch(err => {
            console.error('Error:', err);
            showFloatingNotification('✗ ' + (err.message || 'Error updating candidate'), 'error');
            
            // Reset button state but keep modal open
            editSubmitBtn.disabled = false;
            if (buttonText) {
                buttonText.innerHTML = 'Update Candidate';
                buttonText.style.opacity = '1';
            }
            if (spinner) spinner.style.display = 'none';
        });
    });
}

/* ---------- AJAX DELETE CANDIDATE ---------- */
document.addEventListener('click', function(e) {
    if (e.target.classList.contains('delete-candidate')) {
        e.preventDefault();
        e.stopPropagation();
        const candidateId = e.target.dataset.id;
        deleteCandidate(candidateId);
    }
});

function deleteCandidate(candidateId) {
    if (!confirm('Are you sure you want to delete this candidate?')) {
        return;
    }

    // Disable the delete button to prevent double-clicking
    const deleteBtn = document.querySelector(`.delete-candidate[data-id="${candidateId}"]`);
    if (deleteBtn) {
        deleteBtn.style.pointerEvents = 'none';
        deleteBtn.style.opacity = '0.5';
    }

    // Get current page before deleting
    const currentPageElement = document.querySelector('.pagination .current');
    const currentPage = currentPageElement ? parseInt(currentPageElement.textContent) : 1;

    fetch(`/ctumoalboal-comelec/candidates/delete/${candidateId}`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-Requested-With': 'XMLHttpRequest',
            'X-CSRFToken': getCsrfToken()
        }
    })
    .then(res => {
        // Check if response is JSON
        const contentType = res.headers.get('content-type');
        if (contentType && contentType.includes('application/json')) {
            return res.json();
        } else {
            // If not JSON, but status is OK, consider it successful if row is gone
            if (res.ok) {
                const row = document.getElementById(`candidate-${candidateId}`);
                if (!row) {
                    return { success: true, message: 'Candidate deleted successfully!' };
                }
            }
            throw new Error('Server returned non-JSON response');
        }
    })
    .then(data => {
        if (data.success) {
            showFloatingNotification('✓ Candidate deleted successfully!', 'success');
            // Refresh the table with current filters and keep page
            return filterCandidates(currentPage, true);
        } else {
            throw new Error(data.message || 'Failed to delete candidate');
        }
    })
    .catch(err => {
        console.error('Error:', err);
        
        // Check if the row still exists - if not, deletion was successful despite error
        const row = document.getElementById(`candidate-${candidateId}`);
        if (!row) {
            showFloatingNotification('✓ Candidate deleted successfully!', 'success');
            filterCandidates(currentPage, true);
        } else {
            showFloatingNotification('✗ ' + (err.message || 'Error deleting candidate'), 'error');
            // Re-enable the delete button
            if (deleteBtn) {
                deleteBtn.style.pointerEvents = 'auto';
                deleteBtn.style.opacity = '1';
            }
        }
    });
}

/* Animation keyframes - FIXED VERSION */
(function addAnimationStyles() {
    // Check if styles already exist
    if (document.getElementById('notification-animation-styles')) {
        return;
    }
    
    const style = document.createElement('style');
    style.id = 'notification-animation-styles';
    style.textContent = `
        @keyframes slideDown {
            from {
                transform: translate(-50%, -20px);
                opacity: 0;
            }
            to {
                transform: translate(-50%, 0);
                opacity: 1;
            }
        }
        
        @keyframes slideUp {
            from {
                transform: translate(-50%, 0);
                opacity: 1;
            }
            to {
                transform: translate(-50%, -20px);
                opacity: 0;
            }
        }
        
        @keyframes spin {
            to { transform: rotate(360deg); }
        }
        
        .floating-notification {
            pointer-events: all;
        }
        
        .floating-notification .notification-content {
            backdrop-filter: blur(5px);
        }
        
        /* Dark mode adjustments */
        @media (prefers-color-scheme: dark) {
            .floating-notification .notification-content {
                box-shadow: 0 5px 15px rgba(0,0,0,0.5);
            }
        }
    `;
    document.head.appendChild(style);
})();

// Make functions available globally
window.filterCandidates = filterCandidates;
window.showFloatingNotification = showFloatingNotification;