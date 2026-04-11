/* PHOTO LIGHTBOX */
// manage_candidates.js - Updated with school year support and platform field
// All notifications now float above the modal

// ==================== CSRF TOKEN HELPER - REMOVED ====================
// CSRF protection has been disabled - removed getCsrfToken() function

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
    
    // Initialize department change for course loading (for student)
    const addDepartmentStudent = document.getElementById('add_department_student');
    if (addDepartmentStudent) {
        addDepartmentStudent.addEventListener('change', function() {
            loadCoursesForStudent('add', this.value);
            // Clear validation when department changes
            const existingNotification = document.querySelector('.student-validation-notification');
            if (existingNotification) existingNotification.remove();
        });
    }
    
    // Initialize course change for student validation
    const addCourseStudent = document.getElementById('add_course_student');
    if (addCourseStudent) {
        addCourseStudent.addEventListener('change', function() {
            validateStudentExists();
        });
    }
    
    // Initialize first name and last name validation
    const addFirstName = document.getElementById('add_first_name');
    const addLastName = document.getElementById('add_last_name');
    const addYearLevel = document.getElementById('add_year_level');
    
    if (addFirstName) {
        addFirstName.addEventListener('blur', validateStudentExists);
        addFirstName.addEventListener('input', function() {
            const existingNotification = document.querySelector('.student-validation-notification');
            if (existingNotification) existingNotification.remove();
        });
    }
    
    if (addLastName) {
        addLastName.addEventListener('blur', validateStudentExists);
        addLastName.addEventListener('input', function() {
            const existingNotification = document.querySelector('.student-validation-notification');
            if (existingNotification) existingNotification.remove();
        });
    }
    
    if (addYearLevel) {
        addYearLevel.addEventListener('change', validateStudentExists);
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

// Function to validate if student exists in real-time (simplified)
async function validateStudentExists() {
    const candidateTypeSelect = document.getElementById('candidate_type_select');
    const candidateType = candidateTypeSelect ? candidateTypeSelect.value : 'student';
    
    // Only validate for student candidates
    if (candidateType !== 'student') {
        return true;
    }
    
    const firstName = document.getElementById('add_first_name')?.value?.trim();
    const lastName = document.getElementById('add_last_name')?.value?.trim();
    const courseId = document.getElementById('add_course_student')?.value;
    const yearLevelId = document.getElementById('add_year_level')?.value;
    
    // Check if all required fields are filled
    if (!firstName || !lastName || !courseId || !yearLevelId) {
        const existingNotification = document.querySelector('.student-validation-notification');
        if (existingNotification) existingNotification.remove();
        return false;
    }
    
    try {
        let url = `/ctumoalboal-comelec/validate-student?first_name=${encodeURIComponent(firstName)}&last_name=${encodeURIComponent(lastName)}&course_id=${courseId}`;
        
        const response = await fetch(url, {
            method: 'GET',
            headers: {
                'X-Requested-With': 'XMLHttpRequest'
            }
        });
        
        const data = await response.json();
        
        // Remove existing validation notification
        const existingNotification = document.querySelector('.student-validation-notification');
        if (existingNotification) existingNotification.remove();
        
        // Simple notification - just show if verified or not
        if (data.exists) {
            showStudentValidationNotification('✓ Student Verified', 'success');
            return true;
        } else {
            showStudentValidationNotification('✗ Student Not Found', 'error');
            return false;
        }
    } catch (error) {
        console.error('Validation error:', error);
        showStudentValidationNotification('✗ Validation Error', 'error');
        return false;
    }
}

// Consistent notification function - top center, size fits text
function showStudentValidationNotification(message, type) {
    // Remove existing notification
    const existingNotification = document.querySelector('.student-validation-notification');
    if (existingNotification) existingNotification.remove();
    
    // Create notification element
    const notification = document.createElement('div');
    notification.className = `student-validation-notification ${type}`;
    
    // Use same gradient colors as floating notifications
    const colors = type === 'success' 
        ? { bg: 'linear-gradient(135deg, #00c851, #00a844)', border: '#007e33', icon: 'fa-check-circle' }
        : { bg: 'linear-gradient(135deg, #ff4444, #cc0000)', border: '#a70000', icon: 'fa-exclamation-circle' };
    
    notification.innerHTML = `
        <div class="notification-content">
            <i class="fa ${colors.icon}"></i>
            <div class="notification-message">${message}</div>
            <button class="notification-close">&times;</button>
        </div>
    `;
    
    // Style the notification - TOP CENTER (not vertical center)
    notification.style.cssText = `
        position: fixed;
        top: 80px;
        left: 50%;
        transform: translateX(-50%);
        z-index: 100001;
        min-width: 300px;
        max-width: 450px;
        width: auto;
        animation: slideDown 0.3s ease-out;
        box-shadow: 0 10px 25px rgba(0,0,0,0.2);
        border-radius: 8px;
        overflow: hidden;
        pointer-events: all;
    `;
    
    // Style the content
    const contentDiv = notification.querySelector('.notification-content');
    if (contentDiv) {
        contentDiv.style.cssText = `
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
            white-space: nowrap;
        `;
    }
    
    // Style the icon
    const iconElement = notification.querySelector('.notification-content i:first-child');
    if (iconElement) {
        iconElement.style.cssText = `
            font-size: 1.4rem;
            filter: drop-shadow(0 2px 4px rgba(0,0,0,0.2));
        `;
    }
    
    // Style the message
    const messageElement = notification.querySelector('.notification-message');
    if (messageElement) {
        messageElement.style.cssText = `
            flex: 1;
            line-height: 1.4;
            word-break: keep-all;
            white-space: nowrap;
        `;
    }
    
    // Style the close button
    const closeBtn = notification.querySelector('.notification-close');
    if (closeBtn) {
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
        closeBtn.onclick = () => {
            notification.style.animation = 'slideUp 0.3s ease-out forwards';
            setTimeout(() => notification.remove(), 300);
        };
    }
    
    // Append to body
    document.body.appendChild(notification);
    
    // Auto hide after 3 seconds
    setTimeout(() => {
        if (notification.parentNode) {
            notification.style.animation = 'slideUp 0.3s ease-out forwards';
            setTimeout(() => {
                if (notification.parentNode) notification.remove();
            }, 300);
        }
    }, 3000);
}

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
    const candidateType = btn.dataset.candidateType || 'student';
    
    document.getElementById('edit_id').value = id;
    document.getElementById('edit_candidate_type').value = candidateType;
    
    // Set common fields
    document.getElementById('edit_party_list').value = btn.dataset.party || '';
    document.getElementById('edit_platform').value = btn.dataset.platform || '';
    document.getElementById('edit_position').value = btn.dataset.position;
    document.getElementById('edit_election').value = btn.dataset.election;
    document.getElementById('edit_scope').value = btn.dataset.scope || 'campus';
    document.getElementById('edit_department').value = btn.dataset.department_id || '';
    
    // Set course after department loads
    if (btn.dataset.department_id) {
        loadCourses('edit', btn.dataset.department_id).then(() => {
            if (btn.dataset.course_id) {
                setTimeout(() => {
                    document.getElementById('edit_course').value = btn.dataset.course_id;
                }, 100);
            }
        });
    }
    
    // Handle candidate type specific fields
    if (candidateType === 'studio') {
        // Studio candidate
        const studioName = btn.dataset.studioName || '';
        setupEditModalType('studio', studioName, '', '', '');
    } else {
        // Student candidate
        const firstName = btn.dataset.first || '';
        const lastName = btn.dataset.last || '';
        const yearLevelId = btn.dataset.yearLevelId || '';
        setupEditModalType('student', '', firstName, lastName, yearLevelId);
    }
    
    // Filter elections based on scope
    const scope = btn.dataset.scope || 'campus';
    filterElectionsByScopeForEdit(scope, btn.dataset.department_id, btn.dataset.election);
    
    // Hide any existing notifications
    const editNotification = document.getElementById('editCandidateNotification');
    if (editNotification) {
        editNotification.style.display = 'none';
    }
    
    document.getElementById('editCandidateModal').style.display = 'flex';
}

// Helper function to filter elections for edit modal
function filterElectionsByScopeForEdit(scope, departmentId, selectedElectionId) {
    const editElection = document.getElementById('edit_election');
    
    if (!editElection) return;
    
    // Hide all options first
    for (let i = 0; i < editElection.options.length; i++) {
        editElection.options[i].style.display = 'none';
    }
    
    // Show placeholder
    for (let i = 0; i < editElection.options.length; i++) {
        if (editElection.options[i].value === "") {
            editElection.options[i].style.display = 'block';
            break;
        }
    }
    
    if (scope === 'department') {
        // Show department elections
        for (let i = 0; i < editElection.options.length; i++) {
            const option = editElection.options[i];
            if (option.value === "") continue;
            
            const optionScope = option.getAttribute('data-scope');
            const optionDept = option.getAttribute('data-department');
            
            if (optionScope === 'department' && optionDept === departmentId) {
                option.style.display = 'block';
            }
        }
    } else {
        // Show campus elections
        for (let i = 0; i < editElection.options.length; i++) {
            const option = editElection.options[i];
            if (option.value === "") {
                option.style.display = 'block';
                continue;
            }
            
            const optionScope = option.getAttribute('data-scope');
            if (optionScope === 'campus') {
                option.style.display = 'block';
            }
        }
    }
    
    // Set selected election
    if (selectedElectionId) {
        editElection.value = selectedElectionId;
    }
}

// Display school year info if filtered
function displaySchoolYearInfo() {
    // Check if there's a school year badge already in the DOM
    const existingBadge = document.querySelector('.school-year-badge');
    if (existingBadge) {
        console.log("School year filter active:", existingBadge.textContent);
    }
}

// Initialize functions
function initModals() {}
function initFilters() {}
function initSearch() {}
function initDeleteButtons() {}
function initEditButtons() {
    attachEditButtonListeners();
}
function initPhotoClick() {}
function initAddCandidate() {}

// Filter positions by election
function filterPositionsByElection(mode) {
    // This function can be implemented if needed
    console.log("Filter positions by election called for mode:", mode);
}

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
        const modal = document.getElementById('addCandidateModal');
        if (modal) {
            modal.style.display = 'flex';
        }
        
        // Reset form and clear any notifications
        const form = document.getElementById('addCandidateForm');
        if (form) form.reset();
        
        // Hide any existing notifications
        const addNotification = document.getElementById('addCandidateNotification');
        if (addNotification) {
            addNotification.style.display = 'none';
        }
        
        // Remove validation notification
        const existingValidation = document.querySelector('.student-validation-notification');
        if (existingValidation) existingValidation.remove();
        
        // Clear course dropdown for student
        const addCourseStudent = document.getElementById('add_course_student');
        if (addCourseStudent) {
            addCourseStudent.innerHTML = '<option value="">Select course</option>';
        }
        
        // Clear platform field
        const addPlatform = document.getElementById('add_platform');
        if (addPlatform) {
            addPlatform.value = '';
        }
        
        // Hide ALL election options initially
        const addElection = document.getElementById('add_election');
        if (addElection) {
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
        }
        
        // Reset candidate type toggle
        const candidateTypeSelect = document.getElementById('candidate_type_select');
        if (candidateTypeSelect) {
            candidateTypeSelect.value = 'student';
            // Trigger the toggle function
            if (typeof toggleCandidateFields === 'function') {
                toggleCandidateFields();
            }
        }
    };
}

function closeAddCandidateModal() {
    const modal = document.getElementById('addCandidateModal');
    if (modal) {
        modal.style.display = 'none';
    }
    const form = document.getElementById('addCandidateForm');
    if (form) form.reset();
    
    // Clear any notification
    const addNotification = document.getElementById('addCandidateNotification');
    if (addNotification) {
        addNotification.style.display = 'none';
    }
    
    // Remove validation notification
    const existingValidation = document.querySelector('.student-validation-notification');
    if (existingValidation) existingValidation.remove();
}

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
    const modal = document.getElementById('editCandidateModal');
    if (modal) {
        modal.style.display = 'none';
    }
    const form = document.getElementById('editCandidateForm');
    if (form) form.reset();
    
    // Clear any notification
    const editNotification = document.getElementById('editCandidateNotification');
    if (editNotification) {
        editNotification.style.display = 'none';
    }
    
    // Reset the edit button state
    resetEditButtonState();
}

/* Function to load courses based on department selection (for edit modal) */
function loadCourses(mode, departmentId) {
    return new Promise((resolve, reject) => {
        const courseSelect = document.getElementById(mode + '_course');
        
        if (!courseSelect) {
            resolve();
            return;
        }
        
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
                'Content-Type': 'application/json'
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

/* Function to load courses for student (add modal) */
function loadCoursesForStudent(mode, departmentId) {
    const courseSelect = document.getElementById(mode + '_course_student');
    
    if (!courseSelect) return;
    
    // Clear current options
    courseSelect.innerHTML = '<option value="">Select course</option>';
    
    if (!departmentId) {
        return;
    }
    
    // Show loading state
    const loadingOption = document.createElement('option');
    loadingOption.value = '';
    loadingOption.textContent = 'Loading courses...';
    loadingOption.disabled = true;
    courseSelect.appendChild(loadingOption);
    
    fetch(`/ctumoalboal-comelec/courses/by_department/${departmentId}`, {
        headers: {
            'Content-Type': 'application/json'
        }
    })
        .then(response => {
            if (!response.ok) {
                throw new Error('Network response was not ok');
            }
            return response.json();
        })
        .then(data => {
            courseSelect.innerHTML = '<option value="">Select course</option>';
            
            if (data.courses && data.courses.length > 0) {
                data.courses.forEach(course => {
                    const option = document.createElement('option');
                    option.value = course.id;
                    option.textContent = course.course_name + (course.course_code ? ` (${course.course_code})` : '');
                    courseSelect.appendChild(option);
                });
            }
        })
        .catch(err => {
            console.error('Error loading courses:', err);
            courseSelect.innerHTML = '<option value="">Error loading courses</option>';
        });
}

/* Filter elections by scope */
function filterElectionsByScope(mode) {
    const scope = document.getElementById(mode + '_scope');
    const electionSelect = document.getElementById(mode + '_election');
    
    if (!scope || !electionSelect) return;
    
    const scopeValue = scope.value;
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
    
    if (scopeValue === 'department') {
        // Get selected department for student
        const departmentId = document.getElementById(mode + '_department_student');
        const deptValue = departmentId ? departmentId.value : null;
        
        if (deptValue) {
            // Show only department elections for the selected department
            for (let i = 0; i < options.length; i++) {
                const option = options[i];
                if (option.value === "") continue;
                
                const optionScope = option.getAttribute('data-scope');
                const optionDept = option.getAttribute('data-department');
                
                if (optionScope === 'department' && optionDept === deptValue) {
                    option.style.display = 'block';
                }
            }
        }
    } else if (scopeValue === 'campus') {
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

/* Validate department and course before submission */
function validateDepartmentAndCourse(mode) {
    // For add mode, check candidate type first
    if (mode === 'add') {
        const candidateTypeSelect = document.getElementById('candidate_type_select');
        const candidateType = candidateTypeSelect ? candidateTypeSelect.value : 'student';
        
        // STUDIO CANDIDATES - skip department and course validation
        if (candidateType === 'studio') {
            console.log("Studio candidate - skipping department/course validation");
            return true;
        }
        
        // STUDENT CANDIDATES - require department and course
        const deptSelect = document.getElementById('add_department_student');
        const courseSelect = document.getElementById('add_course_student');
        
        if (!deptSelect || !deptSelect.value) {
            showFloatingNotification('Please select a department', 'error');
            if (deptSelect) deptSelect.focus();
            return false;
        }
        if (!courseSelect || !courseSelect.value) {
            showFloatingNotification('Please select a course', 'error');
            if (courseSelect) courseSelect.focus();
            return false;
        }
        
    } else if (mode === 'edit') {
        const candidateType = document.getElementById('edit_candidate_type');
        const candidateTypeValue = candidateType ? candidateType.value : 'student';
        
        // STUDIO CANDIDATES - skip department and course validation
        if (candidateTypeValue === 'studio') {
            console.log("Studio candidate edit - skipping department/course validation");
            return true;
        }
        
        // STUDENT CANDIDATES - require department and course
        const deptSelect = document.getElementById('edit_department');
        const courseSelect = document.getElementById('edit_course');
        
        if (!deptSelect || !deptSelect.value) {
            showFloatingNotification('Please select a department', 'error');
            if (deptSelect) deptSelect.focus();
            return false;
        }
        if (!courseSelect || !courseSelect.value) {
            showFloatingNotification('Please select a course', 'error');
            if (courseSelect) courseSelect.focus();
            return false;
        }
    }
    
    return true;
}

// Candidate Type Dropdown Toggle Function
function toggleCandidateFields() {
    const candidateTypeSelect = document.getElementById('candidate_type_select');
    if (!candidateTypeSelect) return;
    
    const studentFields = document.getElementById('studentFields');
    const studioFields = document.getElementById('studioFields');
    const partyListField = document.getElementById('partyListField');
    const platformField = document.getElementById('platformField');
    const scopeSelect = document.getElementById('add_scope');
    const electionSelect = document.getElementById('add_election');
    
    const selectedType = candidateTypeSelect.value;
    
    if (selectedType === 'student') {
        // Show student fields, hide studio fields
        if (studentFields) studentFields.style.display = 'block';
        if (studioFields) studioFields.style.display = 'none';
        
        // Show party list and platform for students
        if (partyListField) partyListField.style.display = 'block';
        if (platformField) platformField.style.display = 'block';
        
        // Make student fields required
        const firstName = document.getElementById('add_first_name');
        const lastName = document.getElementById('add_last_name');
        const yearLevel = document.getElementById('add_year_level');
        const department = document.getElementById('add_department_student');
        const course = document.getElementById('add_course_student');
        
        if (firstName) firstName.required = true;
        if (lastName) lastName.required = true;
        if (yearLevel) yearLevel.required = true;
        if (department) department.required = true;
        if (course) course.required = true;
        
        // Make studio fields not required
        const studioName = document.getElementById('add_studio_name');
        if (studioName) studioName.required = false;
        
        // Enable scope and election filtering
        if (scopeSelect) scopeSelect.disabled = false;
        if (electionSelect) electionSelect.disabled = false;
        
        // Reset scope to empty and trigger filter
        if (scopeSelect) {
            scopeSelect.value = '';
            filterElectionsByScope('add');
        }
        
        // Remove validation notification when switching to student
        const existingValidation = document.querySelector('.student-validation-notification');
        if (existingValidation) existingValidation.remove();
        
    } else {
        // STUDIO CANDIDATE
        if (studentFields) studentFields.style.display = 'none';
        if (studioFields) studioFields.style.display = 'block';
        
        // Hide party list and platform for studios
        if (partyListField) partyListField.style.display = 'none';
        if (platformField) platformField.style.display = 'none';
        
        // Make student fields not required
        const firstName = document.getElementById('add_first_name');
        const lastName = document.getElementById('add_last_name');
        const yearLevel = document.getElementById('add_year_level');
        const department = document.getElementById('add_department_student');
        const course = document.getElementById('add_course_student');
        
        if (firstName) firstName.required = false;
        if (lastName) lastName.required = false;
        if (yearLevel) yearLevel.required = false;
        if (department) department.required = false;
        if (course) course.required = false;
        
        // Make studio fields required
        const studioName = document.getElementById('add_studio_name');
        if (studioName) studioName.required = true;
        
        // For studio candidates, only campus-wide elections should be shown
        if (scopeSelect) {
            scopeSelect.value = 'campus';
            scopeSelect.disabled = true;
            // Filter elections to show only campus-wide
            filterElectionsForStudio();
        }
    }
}

// Function to filter elections for studio candidates (only campus-wide)
function filterElectionsForStudio() {
    const electionSelect = document.getElementById('add_election');
    if (!electionSelect) return;
    
    const options = electionSelect.options;
    
    // Hide all options first
    for (let i = 0; i < options.length; i++) {
        options[i].style.display = 'none';
    }
    
    // Show placeholder
    for (let i = 0; i < options.length; i++) {
        if (options[i].value === "") {
            options[i].style.display = 'block';
            break;
        }
    }
    
    // Show only campus-wide elections
    for (let i = 0; i < options.length; i++) {
        const option = options[i];
        if (option.value === "") continue;
        
        const optionScope = option.getAttribute('data-scope');
        if (optionScope === 'campus') {
            option.style.display = 'block';
        }
    }
}

// Attach event listener for candidate type toggle
document.addEventListener('DOMContentLoaded', function() {
    const candidateTypeSelect = document.getElementById('candidate_type_select');
    if (candidateTypeSelect) {
        candidateTypeSelect.addEventListener('change', toggleCandidateFields);
        toggleCandidateFields(); // Initial call
    }
});

/* ============ AJAX FILTER FUNCTION WITH LOADING SPINNER ============ */
function filterCandidates(page = null, keepPage = false) {
    const scope = document.getElementById('filter_scope');
    const departmentFilter = document.getElementById('filter_department');
    const search = document.getElementById('search_input');
    
    const scopeValue = scope ? scope.value : '';
    const departmentId = departmentFilter ? departmentFilter.value : '';
    const searchValue = search ? search.value : '';
    
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
    if (searchBtn) {
        const buttonText = searchBtn.querySelector('.button-text');
        const spinner = searchBtn.querySelector('.loading-spinner');
        
        if (buttonText) buttonText.style.display = 'none';
        if (spinner) spinner.style.display = 'inline-block';
        searchBtn.disabled = true;
    }

    // Show loading state on table
    const tableContainer = document.getElementById('table-container');
    if (tableContainer) {
        tableContainer.classList.add('table-loading');
    }

    // Build URL with query parameters
    let url = `/ctumoalboal-comelec/candidates/filter?page=${currentPage}`;
    if (scopeValue) url += `&scope=${scopeValue}`;
    if (departmentId) url += `&department_id=${departmentId}`;
    if (searchValue) url += `&search=${encodeURIComponent(searchValue)}`;

    // Update browser URL without reload
    const newUrl = new URL(window.location);
    newUrl.searchParams.set('page', currentPage);
    if (scopeValue) newUrl.searchParams.set('scope', scopeValue);
    else newUrl.searchParams.delete('scope');
    
    if (departmentId) newUrl.searchParams.set('department_id', departmentId);
    else newUrl.searchParams.delete('department_id');
    
    if (searchValue) newUrl.searchParams.set('search', searchValue);
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
        showFloatingNotification('Error filtering candidates', 'error');
    })
    .finally(() => {
        // Hide loading states
        if (searchBtn) {
            const buttonText = searchBtn.querySelector('.button-text');
            const spinner = searchBtn.querySelector('.loading-spinner');
            
            if (buttonText) buttonText.style.display = 'inline-block';
            if (spinner) spinner.style.display = 'none';
            searchBtn.disabled = false;
        }
        if (tableContainer) {
            tableContainer.classList.remove('table-loading');
        }
    });
}

/* Update table with new data */
function updateTable(candidates, pagination) {
    const tbody = document.getElementById('candidatesTableBody');
    if (!tbody) return;

    if (!candidates || candidates.length === 0) {
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
        
        // Determine display name based on candidate type
        let displayName = '';
        if (c.candidate_type === 'studio') {
            displayName = escapeHtml(c.studio_name || '');
        } else {
            displayName = escapeHtml((c.first_name || '') + ' ' + (c.last_name || ''));
        }
        
        html += `
            <tr id="candidate-${c.id}">
                <td>
                    ${c.photo ? 
                        `<img src="${c.photo}" class="candidate-photo clickable-photo" alt="Candidate Photo">` : 
                        '<span>No Photo</span>'}
                </td>
                <td>${displayName}</td>
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
                        data-candidate-type="${c.candidate_type || 'student'}"
                        data-first="${escapeHtml(c.first_name) || ''}" 
                        data-last="${escapeHtml(c.last_name) || ''}" 
                        data-studio-name="${escapeHtml(c.studio_name) || ''}"
                        data-party="${escapeHtml(c.party_list) || ''}"
                        data-platform="${escapeHtml(c.platform) || ''}"
                        data-year-level-id="${c.year_level_id || ''}"
                        data-year-level-name="${escapeHtml(c.year_level) || ''}"
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
    const filterScope = document.getElementById('filter_scope');
    const filterDepartment = document.getElementById('filter_department');
    const searchInput = document.getElementById('search_input');
    
    if (filterScope) filterScope.value = '';
    if (filterDepartment) {
        filterDepartment.value = '';
        filterDepartment.style.display = 'none';
    }
    if (searchInput) searchInput.value = '';
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
            const lightbox = document.getElementById('lightbox');
            const lightboxImg = document.getElementById('lightbox-img');
            if (lightbox && lightboxImg) {
                lightbox.style.display = 'flex';
                lightboxImg.src = img.src;
            }
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
        if (filterScope && filterDepartment) {
            if (filterScope.value === 'department') {
                filterDepartment.style.display = 'inline-block';
            } else {
                filterDepartment.style.display = 'none';
                filterDepartment.value = "";
            }
        }
    }

    if (filterScope) {
        filterScope.addEventListener('change', () => {
            updateFilterDepartment();
            filterCandidates(1, false);
        });
    }

    if (filterDepartment) {
        filterDepartment.addEventListener('change', () => {
            filterCandidates(1, false);
        });
    }

    if (searchBtn) {
        searchBtn.addEventListener('click', () => {
            filterCandidates(1, false);
        });
    }

    if (searchInput) {
        searchInput.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') {
                e.preventDefault();
                filterCandidates(1, false);
            }
        });
    }

    if (resetBtn) {
        resetBtn.addEventListener('click', () => {
            if (filterScope) filterScope.value = '';
            if (filterDepartment) {
                filterDepartment.value = '';
                filterDepartment.style.display = 'none';
            }
            if (searchInput) searchInput.value = '';
            filterCandidates(1, false);
        });
    }

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
    
    const contentDiv = notification.querySelector('.notification-content');
    if (contentDiv) {
        contentDiv.style.cssText = `
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
    }
    
    // Style the close button
    const closeBtn = notification.querySelector('.notification-close');
    if (closeBtn) {
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
    }
    
    // Style the icon
    const iconElement = notification.querySelector('i:first-child');
    if (iconElement) {
        iconElement.style.cssText = `
            font-size: 1.4rem;
            filter: drop-shadow(0 2px 4px rgba(0,0,0,0.2));
        `;
    }
    
    // Style the message
    const messageElement = notification.querySelector('.notification-message');
    if (messageElement) {
        messageElement.style.cssText = `
            flex: 1;
            line-height: 1.4;
            word-break: break-word;
        `;
    }
    
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

        // ========== DEBUG: Log candidate type and form data ==========
        const candidateTypeSelect = document.getElementById('candidate_type_select');
        console.log("=== SUBMITTING CANDIDATE ===");
        console.log("Candidate Type:", candidateTypeSelect ? candidateTypeSelect.value : 'not found');
        
        // Log all form data
        const debugFormData = new FormData(this);
        for (let pair of debugFormData.entries()) {
            console.log(pair[0] + ': ' + pair[1]);
        }
        console.log("===========================");
        // ========== END DEBUG ==========

        // Validate department and course (required for ALL)
        if (!validateDepartmentAndCourse('add')) {
            console.log("Validation failed for department/course");
            return; // Stop form submission
        }

        // For student candidates, check if student exists before submitting
        const candidateType = candidateTypeSelect ? candidateTypeSelect.value : 'student';
        if (candidateType === 'student') {
            const isValid = await validateStudentExists();
            if (!isValid) {
                showFloatingNotification('✗ Please verify student information before submitting.', 'error');
                return; // Stop form submission
            }
        }

        // Show loading state
        if (addSubmitBtn) {
            addSubmitBtn.disabled = true;
            const buttonText = addSubmitBtn.querySelector('.button-text');
            const spinner = addSubmitBtn.querySelector('.loading-spinner');
            if (buttonText) {
                buttonText.innerHTML = 'Adding...';
                buttonText.style.opacity = '0.7';
            }
            if (spinner) spinner.style.display = 'inline-block';
        }

        const formData = new FormData(this);

        fetch("/ctumoalboal-comelec/candidates", {
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
            console.log("Server response:", data);
            if(data.success) {
                // Show floating success notification
                showFloatingNotification('✓ Candidate added successfully!', 'success');
                
                // Refresh the table with current filters but keep page
                filterCandidates(null, true);

                // Reset form fields but KEEP MODAL OPEN
                addCandidateForm.reset();
                
                const addScope = document.getElementById('add_scope');
                if (addScope) addScope.value = '';
                
                // Clear course dropdown for student
                const addCourseStudent = document.getElementById('add_course_student');
                if (addCourseStudent) {
                    addCourseStudent.innerHTML = '<option value="">Select course</option>';
                }
                
                // Clear platform field
                const addPlatform = document.getElementById('add_platform');
                if (addPlatform) {
                    addPlatform.value = '';
                }
                
                // Reset election dropdown - hide all and show placeholder only
                const addElection = document.getElementById('add_election');
                if (addElection) {
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
                }
                
                // Reset candidate type toggle
                const candidateTypeSelectReset = document.getElementById('candidate_type_select');
                if (candidateTypeSelectReset) {
                    candidateTypeSelectReset.value = 'student';
                    toggleCandidateFields();
                }
                
                // Remove validation notification
                const existingValidation = document.querySelector('.student-validation-notification');
                if (existingValidation) existingValidation.remove();

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
            if (addSubmitBtn) {
                addSubmitBtn.disabled = false;
                const buttonText = addSubmitBtn.querySelector('.button-text');
                const spinner = addSubmitBtn.querySelector('.loading-spinner');
                if (buttonText) {
                    buttonText.innerHTML = 'Add Candidate';
                    buttonText.style.opacity = '1';
                }
                if (spinner) spinner.style.display = 'none';
            }
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
        if (editSubmitBtn) {
            editSubmitBtn.disabled = true;
            const buttonText = editSubmitBtn.querySelector('.button-text');
            const spinner = editSubmitBtn.querySelector('.loading-spinner');
            
            if (buttonText) {
                buttonText.innerHTML = 'Updating...';
                buttonText.style.opacity = '0.7';
            }
            if (spinner) spinner.style.display = 'inline-block';
        }

        const formData = new FormData(this);
        const candidateId = document.getElementById('edit_id').value;

        fetch(`/ctumoalboal-comelec/candidates/edit/${candidateId}`, {
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
        })
        .catch(err => {
            console.error('Error:', err);
            showFloatingNotification('✗ ' + (err.message || 'Error updating candidate'), 'error');
            
            // Reset button state but keep modal open
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

// Setup edit modal type (for studio/student candidates)
function setupEditModalType(candidateType, studioName, firstName, lastName, yearLevelId) {
    const editTypeDisplay = document.getElementById('edit_type_display');
    const editStudentFields = document.getElementById('editStudentFields');
    const editStudioFields = document.getElementById('editStudioFields');
    const editCandidateType = document.getElementById('edit_candidate_type');
    const editPartyListField = document.getElementById('edit_party_list')?.closest('.form-row');
    const editPlatformField = document.getElementById('edit_platform')?.closest('.form-group');
    
    if (!editTypeDisplay) return;
    
    // Set the hidden candidate type field
    if (editCandidateType) editCandidateType.value = candidateType;
    
    if (candidateType === 'studio') {
        // Show studio type
        editTypeDisplay.innerHTML = '<i class="fa-solid fa-video"></i> Studio Candidate';
        editTypeDisplay.style.background = '#f59e0b';
        
        // Show studio fields, hide student fields
        if (editStudentFields) editStudentFields.style.display = 'none';
        if (editStudioFields) editStudioFields.style.display = 'block';
        
        // Hide party list and platform for studio candidates in edit modal
        if (editPartyListField) editPartyListField.style.display = 'none';
        if (editPlatformField) editPlatformField.style.display = 'none';
        
        // Set studio name
        const studioNameInput = document.getElementById('edit_studio_name');
        if (studioNameInput) studioNameInput.value = studioName || '';
        
        // Make studio name required
        if (studioNameInput) studioNameInput.required = true;
        
        // Make student fields not required
        const editFirstName = document.getElementById('edit_first');
        const editLastName = document.getElementById('edit_last');
        const editYearLevel = document.getElementById('edit_year_level');
        const editDepartment = document.getElementById('edit_department');
        const editCourse = document.getElementById('edit_course');
        
        if (editFirstName) editFirstName.required = false;
        if (editLastName) editLastName.required = false;
        if (editYearLevel) editYearLevel.required = false;
        if (editDepartment) editDepartment.required = false;
        if (editCourse) editCourse.required = false;
        
    } else {
        // Show student type
        editTypeDisplay.innerHTML = '<i class="fa-solid fa-user-graduate"></i> Student Candidate';
        editTypeDisplay.style.background = '#3b82f6';
        
        // Show student fields, hide studio fields
        if (editStudentFields) editStudentFields.style.display = 'block';
        if (editStudioFields) editStudioFields.style.display = 'none';
        
        // Show party list and platform for student candidates in edit modal
        if (editPartyListField) editPartyListField.style.display = 'block';
        if (editPlatformField) editPlatformField.style.display = 'block';
        
        // Set student name fields
        const editFirstName = document.getElementById('edit_first');
        const editLastName = document.getElementById('edit_last');
        const editYearLevel = document.getElementById('edit_year_level');
        
        if (editFirstName) editFirstName.value = firstName || '';
        if (editLastName) editLastName.value = lastName || '';
        if (editYearLevel && yearLevelId) editYearLevel.value = yearLevelId;
        
        // Make student fields required
        if (editFirstName) editFirstName.required = true;
        if (editLastName) editLastName.required = true;
        if (editYearLevel) editYearLevel.required = true;
        
        // Make studio name not required
        const studioNameInput = document.getElementById('edit_studio_name');
        if (studioNameInput) studioNameInput.required = false;
    }
}

// Make functions available globally
window.filterCandidates = filterCandidates;
window.showFloatingNotification = showFloatingNotification;
window.resetFilters = resetFilters;
window.filterElectionsByScope = filterElectionsByScope;
window.filterPositionsByElection = filterPositionsByElection;
window.validateStudentExists = validateStudentExists;