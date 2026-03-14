/* PHOTO LIGHTBOX */
// manage_candidates.js - Updated with school year support and platform field

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

// Handle edit button click
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
    
    // Set platform if available
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
        courseSelect.innerHTML = '<option value="">Select course (optional)</option>';
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

    document.getElementById('editCandidateNotification').style.display = 'none';
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
document.getElementById('openAddCandidate').onclick = e => {
    e.preventDefault();
    document.getElementById('addCandidateModal').style.display = 'flex';
    
    // Reset form and clear any notifications
    document.getElementById('addCandidateForm').reset();
    document.getElementById('addCandidateNotification').style.display = 'none';
    document.getElementById('addCandidateNotification').className = 'modal-notification';
    
    // Clear course dropdown
    const addCourse = document.getElementById('add_course');
    addCourse.innerHTML = '<option value="">Select course (optional)</option>';
    
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

function closeAddCandidateModal() {
    document.getElementById('addCandidateModal').style.display = 'none';
    document.getElementById('addCandidateForm').reset();
    
    // Clear any notification
    document.getElementById('addCandidateNotification').style.display = 'none';
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
    document.getElementById('editCandidateNotification').style.display = 'none';
    
    // Reset the edit button state
    resetEditButtonState();
}

/* Function to load courses based on department selection */
function loadCourses(mode, departmentId) {
    return new Promise((resolve, reject) => {
        const courseSelect = document.getElementById(mode + '_course');
        
        // Clear current options
        courseSelect.innerHTML = '<option value="">Select course (optional)</option>';
        
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
        
        // Fetch courses for the selected department
        fetch(`/admin/courses/by_department/${departmentId}`)
            .then(response => {
                if (!response.ok) {
                    throw new Error('Network response was not ok');
                }
                return response.json();
            })
            .then(data => {
                // Clear loading option
                courseSelect.innerHTML = '<option value="">Select course (optional)</option>';
                
                if (data.courses && data.courses.length > 0) {
                    data.courses.forEach(course => {
                        const option = document.createElement('option');
                        option.value = course.id;
                        // FIXED: Use course_name and course_code instead of name and code
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
    let url = `/admin/candidates/filter?page=${currentPage}`;
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
            'X-Requested-With': 'XMLHttpRequest'
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
        showGlobalNotification('Error filtering candidates', 'error');
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

/* ---------- FUNCTION TO SHOW NOTIFICATION INSIDE MODAL ---------- */
function showModalNotification(modalId, message, type) {
    const notification = document.getElementById(modalId + 'Notification');
    if (!notification) return;
    
    notification.className = 'modal-notification ' + type;
    notification.innerHTML = '<i class="fa ' + (type === 'success' ? 'fa-check-circle' : 'fa-exclamation-circle') + '"></i>' + message;
    notification.style.display = 'flex';
    
    // Auto hide after 5 seconds
    setTimeout(function() {
        notification.style.display = 'none';
    }, 5000);
}

/* ---------- AJAX SUBMIT FOR ADD CANDIDATE ---------- */
const addCandidateForm = document.getElementById('addCandidateForm');
const addSubmitBtn = document.getElementById('addCandidateSubmitBtn');

if (addCandidateForm) {
    addCandidateForm.addEventListener('submit', function(e) {
        e.preventDefault();

        // Show loading state
        addSubmitBtn.disabled = true;
        const buttonText = addSubmitBtn.querySelector('.button-text');
        const spinner = addSubmitBtn.querySelector('.loading-spinner');
        if (buttonText) buttonText.style.opacity = '0.7';
        if (spinner) spinner.style.display = 'inline-block';

        const formData = new FormData(this);

        fetch("/admin/candidates", {
            method: 'POST',
            body: formData,
            headers: {
                'X-Requested-With': 'XMLHttpRequest'
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
                // Show success message INSIDE the modal - MODAL STAYS OPEN
                showModalNotification('addCandidate', data.message || 'Candidate added successfully!', 'success');
                
                // Refresh the table with current filters but keep page
                filterCandidates(null, true);

                // Reset form fields but KEEP MODAL OPEN
                addCandidateForm.reset();
                document.getElementById('add_scope').value = '';
                
                // Clear course dropdown
                const addCourse = document.getElementById('add_course');
                addCourse.innerHTML = '<option value="">Select course (optional)</option>';
                
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
                showModalNotification('addCandidate', data.message || 'Failed to add candidate.', 'error');
            }
        })
        .catch(err => {
            console.error('Error:', err);
            showModalNotification('addCandidate', err.message || 'Error adding candidate', 'error');
        })
        .finally(() => {
            // Hide loading state
            addSubmitBtn.disabled = false;
            if (buttonText) buttonText.style.opacity = '1';
            if (spinner) spinner.style.display = 'none';
        });
    });
}

/* ---------- AJAX SUBMIT FOR EDIT CANDIDATE - FIXED VERSION ---------- */
const editCandidateForm = document.getElementById('editCandidateForm');
const editSubmitBtn = document.getElementById('editCandidateSubmitBtn');

if (editCandidateForm) {
    editCandidateForm.addEventListener('submit', function(e) {
        e.preventDefault();

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

        fetch(`/admin/candidates/edit/${candidateId}`, {
            method: 'POST',
            body: formData,
            headers: {
                'X-Requested-With': 'XMLHttpRequest'
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
                // Show success notification
                showGlobalNotification(data.message || 'Candidate updated successfully!', 'success');
                
                // Refresh the table with current filters but keep page
                filterCandidates(null, true);
                
                // CLOSE THE EDIT MODAL - this will also reset the button state via closeEditModal
                closeEditModal();

            } else {
                // Show error inside modal if failed
                showModalNotification('editCandidate', data.message || 'Failed to update candidate.', 'error');
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
            showModalNotification('editCandidate', err.message || 'Error updating candidate', 'error');
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

    fetch(`/admin/candidates/delete/${candidateId}`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-Requested-With': 'XMLHttpRequest'
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
            showGlobalNotification('Candidate deleted successfully!', 'success');
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
            showGlobalNotification('Candidate deleted successfully!', 'success');
            filterCandidates(currentPage, true);
        } else {
            showGlobalNotification(err.message || 'Error deleting candidate. Please try again.', 'error');
            // Re-enable the delete button
            if (deleteBtn) {
                deleteBtn.style.pointerEvents = 'auto';
                deleteBtn.style.opacity = '1';
            }
        }
    });
}

/* ---------- GLOBAL NOTIFICATION FUNCTION ---------- */
function showGlobalNotification(message, type = 'info') {
    // Remove any existing notifications
    const existingNotifications = document.querySelectorAll('.global-notification');
    existingNotifications.forEach(notif => notif.remove());

    const notification = document.createElement('div');
    notification.className = `global-notification ${type}`;
    notification.innerHTML = `
        <i class="fa ${type === 'success' ? 'fa-check-circle' : 'fa-exclamation-circle'}"></i>
        <span>${message}</span>
    `;
    
    notification.style.cssText = `
        position: fixed;
        top: 20px;
        right: 20px;
        padding: 15px 20px;
        border-radius: 10px;
        color: white;
        font-weight: 500;
        z-index: 100000;
        animation: slideIn 0.3s ease-out;
        box-shadow: 0 4px 12px rgba(0,0,0,0.15);
        display: flex;
        align-items: center;
        gap: 10px;
        background: ${type === 'success' ? 'linear-gradient(135deg, #00c851, #00a844)' : 
                    type === 'error' ? 'linear-gradient(135deg, #ff4444, #cc0000)' : 
                    'linear-gradient(135deg, #4361ee, #3b82f6)'};
    `;

    document.body.appendChild(notification);

    setTimeout(() => {
        if (notification.parentNode) {
            notification.style.animation = 'slideOut 0.3s ease-out forwards';
            setTimeout(() => {
                if (notification.parentNode) {
                    notification.remove();
                }
            }, 300);
        }
    }, 5000);
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
        @keyframes slideIn {
            from { transform: translateX(100%); opacity: 0; }
            to { transform: translateX(0); opacity: 1; }
        }
        @keyframes slideOut {
            from { transform: translateX(0); opacity: 1; }
            to { transform: translateX(100%); opacity: 0; }
        }
        @keyframes spin {
            to { transform: rotate(360deg); }
        }
        @keyframes slideDown {
            from { transform: translateY(-20px); opacity: 0; }
            to { transform: translateY(0); opacity: 1; }
        }
    `;
    document.head.appendChild(style);
})();

// Make sure filterCandidates returns a promise for chaining
window.filterCandidates = filterCandidates;