// candidate-application.js

// CSRF Token Helper Function
function getCsrfToken() {
    const metaTag = document.querySelector('meta[name="csrf-token"]');
    return metaTag ? metaTag.getAttribute('content') : '';
}

// Function to filter elections by scope
function filterElectionsForApply() {
    const scope = document.getElementById('apply_scope').value;
    const electionSelect = document.getElementById('apply_election');
    const options = electionSelect.options;
    
    // Hide all options
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
    
    // Filter by scope
    for (let i = 0; i < options.length; i++) {
        const option = options[i];
        if (option.value === "") continue;
        
        const optionScope = option.getAttribute('data-scope');
        if (optionScope === scope) {
            option.style.display = 'block';
        }
    }
}

// Open candidate application modal
function openCandidateModal() {
    const modal = document.getElementById('candidateApplicationModal');
    
    // Reset form
    document.getElementById('candidateApplicationForm').reset();
    document.getElementById('candidateApplicationNotification').style.display = 'none';
    
    // Reset course dropdown if exists
    const courseSelect = document.getElementById('apply_course');
    if (courseSelect) {
        courseSelect.innerHTML = '<option value="">Select course (optional)</option>';
    }
    
    // Reset election options
    const electionSelect = document.getElementById('apply_election');
    for (let i = 0; i < electionSelect.options.length; i++) {
        electionSelect.options[i].style.display = 'none';
    }
    // Show placeholder
    for (let i = 0; i < electionSelect.options.length; i++) {
        if (electionSelect.options[i].value === "") {
            electionSelect.options[i].style.display = 'block';
            break;
        }
    }
    
    modal.style.display = 'flex';
    document.body.classList.add('modal-open');
}

// Close candidate application modal
function closeCandidateModal() {
    document.getElementById('candidateApplicationModal').style.display = 'none';
    document.body.classList.remove('modal-open');
}

// Show notification in modal
function showApplicationNotification(message, type) {
    const notification = document.getElementById('candidateApplicationNotification');
    notification.className = 'modal-notification ' + type;
    notification.innerHTML = '<i class="fa ' + (type === 'success' ? 'fa-check-circle' : 'fa-exclamation-circle') + '"></i>' + message;
    notification.style.display = 'flex';
    
    setTimeout(() => {
        notification.style.display = 'none';
    }, 5000);
}

document.addEventListener('DOMContentLoaded', function() {
    const applyBtn = document.getElementById('applyAsCandidateBtn');
    if (applyBtn) {
        applyBtn.addEventListener('click', openCandidateModal);
    }
    
    // Close modal when clicking outside
    window.addEventListener('click', function(event) {
        const modal = document.getElementById('candidateApplicationModal');
        if (event.target === modal) {
            closeCandidateModal();
        }
    });
    
    // Handle escape key
    document.addEventListener('keydown', function(e) {
        if (e.key === 'Escape') {
            const modal = document.getElementById('candidateApplicationModal');
            if (modal.style.display === 'flex') {
                closeCandidateModal();
            }
        }
    });
    
    // Handle form submission
    const applicationForm = document.getElementById('candidateApplicationForm');
    if (applicationForm) {
        applicationForm.addEventListener('submit', function(e) {
            e.preventDefault();
            
            const submitBtn = document.getElementById('applySubmitBtn');
            const buttonText = submitBtn.querySelector('.button-text');
            const spinner = submitBtn.querySelector('.loading-spinner');
            
            // Show loading
            submitBtn.disabled = true;
            buttonText.style.opacity = '0.7';
            spinner.style.display = 'inline-block';
            
            const formData = new FormData(this);
            const csrfToken = getCsrfToken(); // Get CSRF token
            
            fetch('/student/apply-as-candidate', {
                method: 'POST',
                headers: {
                    'X-CSRFToken': csrfToken // ADD CSRF TOKEN HEADER
                },
                body: formData
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    showApplicationNotification('Application submitted successfully!', 'success');
                    setTimeout(() => {
                        location.reload();
                    }, 2000);
                } else {
                    showApplicationNotification('Error: ' + data.message, 'error');
                    submitBtn.disabled = false;
                    buttonText.style.opacity = '1';
                    spinner.style.display = 'none';
                }
            })
            .catch(error => {
                showApplicationNotification('Error submitting application', 'error');
                submitBtn.disabled = false;
                buttonText.style.opacity = '1';
                spinner.style.display = 'none';
            });
        });
    }
});