// studio_candidate.js - Handles studio candidate functionality

document.addEventListener('DOMContentLoaded', function() {
    // Initialize candidate type toggle for Add modal
    initCandidateTypeToggle();
    
    // Initialize candidate type toggle for Edit modal (will be called when edit modal opens)
    // This is handled in the manage_candidates.js edit function
});

function initCandidateTypeToggle() {
    const candidateTypeRadios = document.querySelectorAll('input[name="candidate_type"]');
    const studentFields = document.getElementById('studentFields');
    const studioFields = document.getElementById('studioFields');
    
    if (!candidateTypeRadios.length) return;
    
    function toggleFields() {
        const selectedType = document.querySelector('input[name="candidate_type"]:checked').value;
        
        if (selectedType === 'student') {
            // Show student fields, hide studio fields
            if (studentFields) studentFields.style.display = 'block';
            if (studioFields) studioFields.style.display = 'none';
            
            // Make student fields required
            const firstName = document.getElementById('add_first_name');
            const lastName = document.getElementById('add_last_name');
            const yearLevel = document.getElementById('add_year_level');
            
            if (firstName) firstName.required = true;
            if (lastName) lastName.required = true;
            if (yearLevel) yearLevel.required = true;
            
            // Make studio fields not required
            const studioName = document.getElementById('add_studio_name');
            if (studioName) studioName.required = false;
            
        } else {
            // Show studio fields, hide student fields
            if (studentFields) studentFields.style.display = 'none';
            if (studioFields) studioFields.style.display = 'block';
            
            // Make student fields not required
            const firstName = document.getElementById('add_first_name');
            const lastName = document.getElementById('add_last_name');
            const yearLevel = document.getElementById('add_year_level');
            
            if (firstName) firstName.required = false;
            if (lastName) lastName.required = false;
            if (yearLevel) yearLevel.required = false;
            
            // Make studio fields required
            const studioName = document.getElementById('add_studio_name');
            if (studioName) studioName.required = true;
        }
    }
    
    // Add event listeners to radio buttons
    candidateTypeRadios.forEach(radio => {
        radio.addEventListener('change', toggleFields);
    });
    
    // Initial call to set correct state
    toggleFields();
}

// Function to handle edit modal type display
function setupEditModalType(candidateType, studioName, firstName, lastName, yearLevelId) {
    const editTypeDisplay = document.getElementById('edit_type_display');
    const editStudentFields = document.getElementById('editStudentFields');
    const editStudioFields = document.getElementById('editStudioFields');
    const editCandidateType = document.getElementById('edit_candidate_type');
    
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
        
        // Set studio name
        const studioNameInput = document.getElementById('edit_studio_name');
        if (studioNameInput) studioNameInput.value = studioName || '';
        
        // Make studio name required
        if (studioNameInput) studioNameInput.required = true;
        
        // Make student fields not required
        const editFirstName = document.getElementById('edit_first');
        const editLastName = document.getElementById('edit_last');
        const editYearLevel = document.getElementById('edit_year_level');
        
        if (editFirstName) editFirstName.required = false;
        if (editLastName) editLastName.required = false;
        if (editYearLevel) editYearLevel.required = false;
        
    } else {
        // Show student type
        editTypeDisplay.innerHTML = '<i class="fa-solid fa-user-graduate"></i> Student Candidate';
        editTypeDisplay.style.background = '#3b82f6';
        
        // Show student fields, hide studio fields
        if (editStudentFields) editStudentFields.style.display = 'block';
        if (editStudioFields) editStudioFields.style.display = 'none';
        
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

// Export function for use in manage_candidates.js
window.setupEditModalType = setupEditModalType;
window.initCandidateTypeToggle = initCandidateTypeToggle;