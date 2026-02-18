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
};

function closeAddCandidateModal() {
    document.getElementById('addCandidateModal').style.display = 'none';
    document.getElementById('addCandidateForm').reset();
    
    // Remove any success message when closing manually
    const existingMsg = document.querySelector('.modal-success-message');
    if (existingMsg) existingMsg.remove();
}

/* EDIT MODAL */
document.querySelectorAll('.openEditModal').forEach(btn => {
    btn.onclick = e => {
        e.preventDefault();
        const id = btn.dataset.id;
        document.getElementById('edit_id').value = id;
        document.getElementById('edit_first').value = btn.dataset.first;
        document.getElementById('edit_last').value = btn.dataset.last;
        
        // NEW: Set party list value
        document.getElementById('edit_party_list').value = btn.dataset.party || '';
        
        document.getElementById('edit_position').value = btn.dataset.position;
        document.getElementById('edit_election').value = btn.dataset.election;
        document.getElementById('edit_department').value = btn.dataset.department;
        document.getElementById('edit_election_type').value = btn.dataset.election_type;

        document.getElementById('edit_department_field').style.display =
            btn.dataset.election_type === 'Department' ? 'block' : 'none';

        document.getElementById('editCandidateModal').style.display = 'flex';
    };
});

function closeEditModal() {
    document.getElementById('editCandidateModal').style.display = 'none';
    document.getElementById('editCandidateForm').reset();
}

/* SHOW/HIDE Department field & FILTER Election dropdown */
const addElectionType = document.getElementById('add_election_type');
const addDepartmentField = document.getElementById('add_department_field');
const addElectionSelect = document.getElementById('add_election');
addDepartmentField.style.display = 'none';

addElectionType.addEventListener('change', () => {
    addDepartmentField.style.display = addElectionType.value === 'Department' ? 'block' : 'none';
    Array.from(addElectionSelect.options).forEach(opt => {
        if(addElectionType.value === 'Department') opt.style.display = opt.classList.contains('department') ? 'block' : 'none';
        else if(addElectionType.value === 'SSG') opt.style.display = opt.classList.contains('ssg') ? 'block' : 'none';
        else opt.style.display = 'block';
    });
    addElectionSelect.value = "";
});

const editElectionType = document.getElementById('edit_election_type');
const editDepartmentField = document.getElementById('edit_department_field');
const editElectionSelect = document.getElementById('edit_election');
editDepartmentField.style.display = 'none';

editElectionType.addEventListener('change', () => {
    editDepartmentField.style.display = editElectionType.value === 'Department' ? 'block' : 'none';
    Array.from(editElectionSelect.options).forEach(opt => {
        if(editElectionType.value === 'Department') opt.style.display = opt.classList.contains('department') ? 'block' : 'none';
        else if(editElectionType.value === 'SSG') opt.style.display = opt.classList.contains('ssg') ? 'block' : 'none';
        else opt.style.display = 'block';
    });
});

/* FILTER: election type & department dependent dropdown */
const filterForm = document.getElementById('filterForm');
const filterElectionType = document.getElementById('filter_election_type');
const filterDepartment = document.getElementById('filter_department');

function updateFilterDepartment() {
    if (filterElectionType.value === 'Department') filterDepartment.style.display = 'inline-block';
    else { filterDepartment.style.display = 'none'; filterDepartment.value = ""; }
}

updateFilterDepartment();
filterElectionType.addEventListener('change', () => { updateFilterDepartment(); filterForm.submit(); });
filterDepartment.addEventListener('change', () => filterForm.submit());

/* ---------- FUNCTION TO ADD SUCCESS MESSAGE INSIDE MODAL ---------- */
function showModalSuccessMessage(message) {
    // Remove any existing success message
    const existingMsg = document.querySelector('.modal-success-message');
    if (existingMsg) existingMsg.remove();
    
    // Create success message element
    const successMsg = document.createElement('div');
    successMsg.className = 'modal-success-message';
    successMsg.innerHTML = `
        <i class="fa-solid fa-check-circle"></i>
        <span>${message}</span>
    `;
    
    // Style the success message
    successMsg.style.cssText = `
        background: linear-gradient(135deg, #06d6a0, #059669);
        color: white;
        padding: 12px 20px;
        border-radius: 8px;
        margin-bottom: 20px;
        display: flex;
        align-items: center;
        gap: 10px;
        font-weight: 500;
        animation: slideDown 0.3s ease-out;
        grid-column: 1 / -1;
    `;
    
    // Insert at the top of the form
    const form = document.getElementById('addCandidateForm');
    form.insertBefore(successMsg, form.firstChild);
    
    // Auto-remove after 3 seconds
    setTimeout(() => {
        if (successMsg.parentNode) {
            successMsg.style.animation = 'slideUp 0.3s ease-out forwards';
            setTimeout(() => {
                if (successMsg.parentNode) {
                    successMsg.remove();
                }
            }, 300);
        }
    }, 3000);
}

/* ---------- FUNCTION TO CLEAR FORM FIELDS BUT KEEP MODAL OPEN ---------- */
function resetFormFields() {
    const form = document.getElementById('addCandidateForm');
    
    // Clear text inputs
    form.querySelectorAll('input[type="text"]').forEach(input => {
        input.value = '';
    });
    
    // Reset file input
    const photoInput = document.getElementById('add_photo');
    if (photoInput) photoInput.value = '';
    
    // Reset selects to default
    const electionType = document.getElementById('add_election_type');
    electionType.value = '';
    
    const department = document.getElementById('add_department');
    department.value = department.querySelector('option')?.value || '';
    
    const election = document.getElementById('add_election');
    election.value = '';
    
    const position = document.getElementById('add_position');
    position.value = position.querySelector('option')?.value || '';
    
    // Hide department field
    document.getElementById('add_department_field').style.display = 'none';
    
    // Reset election options visibility
    Array.from(election.options).forEach(opt => {
        opt.style.display = 'block';
    });
}

/* ---------- AJAX SUBMIT FOR ADD CANDIDATE ---------- */
const addCandidateForm = document.getElementById('addCandidateForm');
const addSubmitBtn = addCandidateForm.querySelector('.add-btn');

addCandidateForm.addEventListener('submit', function(e) {
    e.preventDefault();

    // Disable button & show spinner
    addSubmitBtn.disabled = true;
    const originalText = addSubmitBtn.innerHTML;
    addSubmitBtn.innerHTML = `<span class="spinner"></span> Adding...`;

    const formData = new FormData(this);

    fetch("/admin/candidates", {
        method: 'POST',
        body: formData,
        headers: {
            'X-Requested-With': 'XMLHttpRequest'
        }
    })
    .then(res => {
        if (!res.ok) {
            throw new Error(`HTTP error! status: ${res.status}`);
        }
        return res.json();
    })
    .then(data => {
        if(data.success) {
            // Show success message INSIDE the modal - MODAL STAYS OPEN
            showModalSuccessMessage('Candidate added successfully!');
            
            // Add new row to table
            const tbody = document.getElementById('candidatesTableBody');
            const tr = document.createElement('tr');
            tr.id = `candidate-${data.id}`;
            
            // Handle department name (could be null)
            const deptName = data.department || '';
            
            tr.innerHTML = `
                <td>
                    ${data.photo ? 
                        `<img src="${data.photo}" class="candidate-photo clickable-photo" alt="Candidate Photo">` : 
                        '<span>No Photo</span>'}
                </td>
                <td>${data.first_name || ''} ${data.last_name || ''}</td>
                <td>${data.party_list || ''}</td>
                <td>${deptName}</td>
                <td>${data.position || ''}</td>
                <td>
                    <a href="#" class="edit-btn openEditModal" 
                       data-id="${data.id}" 
                       data-first="${data.first_name || ''}" 
                       data-last="${data.last_name || ''}" 
                       data-party="${data.party_list || ''}"
                       data-position="${data.position_id || ''}" 
                       data-election="${data.election_id || ''}" 
                       data-department="${deptName}" 
                       data-election_type="${data.election_type || ''}">Edit</a>
                    <a href="${data.delete_url || '#'}" class="delete-btn delete-candidate" data-id="${data.id}">Delete</a>
                </td>
            `;
            tbody.appendChild(tr);

            // Add event listeners to new elements
            const newPhoto = tr.querySelector('.clickable-photo');
            if (newPhoto) {
                newPhoto.onclick = () => {
                    document.getElementById('lightbox').style.display = 'flex';
                    document.getElementById('lightbox-img').src = newPhoto.src;
                };
            }

            tr.querySelector('.openEditModal').addEventListener('click', function(e) {
                e.preventDefault();
                const id = this.dataset.id;
                document.getElementById('edit_id').value = id;
                document.getElementById('edit_first').value = this.dataset.first;
                document.getElementById('edit_last').value = this.dataset.last;
                document.getElementById('edit_party_list').value = this.dataset.party || '';
                document.getElementById('edit_position').value = this.dataset.position;
                document.getElementById('edit_election').value = this.dataset.election;
                document.getElementById('edit_department').value = this.dataset.department;
                document.getElementById('edit_election_type').value = this.dataset.election_type;

                document.getElementById('edit_department_field').style.display =
                    this.dataset.election_type === 'Department' ? 'block' : 'none';

                document.getElementById('editCandidateModal').style.display = 'flex';
            });

            tr.querySelector('.delete-candidate').addEventListener('click', function(e) {
                e.preventDefault();
                deleteCandidate(this.dataset.id);
            });

            // Clear form fields but KEEP MODAL OPEN
            resetFormFields();

        } else {
            // Show error message inside modal
            showModalError(data.error || 'Failed to add candidate.');
        }
    })
    .catch(err => {
        console.error('Error:', err);
        showModalError('Error submitting form. Please try again.');
    })
    .finally(() => {
        // Restore button
        addSubmitBtn.disabled = false;
        addSubmitBtn.innerHTML = originalText;
    });
});

/* ---------- FUNCTION TO SHOW ERROR MESSAGE INSIDE MODAL ---------- */
function showModalError(message) {
    // Remove any existing message
    const existingMsg = document.querySelector('.modal-success-message');
    if (existingMsg) existingMsg.remove();
    
    // Create error message element
    const errorMsg = document.createElement('div');
    errorMsg.className = 'modal-success-message'; // Reuse same class but style differently
    errorMsg.innerHTML = `
        <i class="fa-solid fa-exclamation-circle"></i>
        <span>${message}</span>
    `;
    
    errorMsg.style.cssText = `
        background: linear-gradient(135deg, #ef476f, #dc2626);
        color: white;
        padding: 12px 20px;
        border-radius: 8px;
        margin-bottom: 20px;
        display: flex;
        align-items: center;
        gap: 10px;
        font-weight: 500;
        animation: slideDown 0.3s ease-out;
        grid-column: 1 / -1;
    `;
    
    const form = document.getElementById('addCandidateForm');
    form.insertBefore(errorMsg, form.firstChild);
    
    setTimeout(() => {
        if (errorMsg.parentNode) {
            errorMsg.style.animation = 'slideUp 0.3s ease-out forwards';
            setTimeout(() => {
                if (errorMsg.parentNode) {
                    errorMsg.remove();
                }
            }, 300);
        }
    }, 5000);
}

/* ---------- AJAX SUBMIT FOR EDIT CANDIDATE ---------- */
const editCandidateForm = document.getElementById('editCandidateForm');
const editSubmitBtn = editCandidateForm.querySelector('.edit-btn');

editCandidateForm.addEventListener('submit', function(e) {
    e.preventDefault();

    // Disable button & show spinner
    editSubmitBtn.disabled = true;
    const originalText = editSubmitBtn.innerHTML;
    editSubmitBtn.innerHTML = `<span class="spinner"></span> Updating...`;

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
        if (!res.ok) {
            throw new Error(`HTTP error! status: ${res.status}`);
        }
        return res.json();
    })
    .then(data => {
        if(data.success) {
            // Show success notification
            showNotification('Candidate updated successfully!', 'success');
            
            // Update the table row
            const row = document.getElementById(`candidate-${candidateId}`);
            if (row) {
                row.querySelector('td:nth-child(2)').textContent = `${data.first_name || ''} ${data.last_name || ''}`;
                row.querySelector('td:nth-child(3)').textContent = data.party_list || '';
                row.querySelector('td:nth-child(4)').textContent = data.department || '';
                row.querySelector('td:nth-child(5)').textContent = data.position || '';
                
                // Update photo if changed
                if (data.photo) {
                    const photoCell = row.querySelector('td:first-child');
                    photoCell.innerHTML = `<img src="${data.photo}" class="candidate-photo clickable-photo" alt="Candidate Photo">`;
                    
                    // Add click event to new photo
                    const newPhoto = photoCell.querySelector('.clickable-photo');
                    newPhoto.onclick = () => {
                        document.getElementById('lightbox').style.display = 'flex';
                        document.getElementById('lightbox-img').src = newPhoto.src;
                    };
                }

                // Update edit button data attributes
                const editBtn = row.querySelector('.openEditModal');
                editBtn.dataset.first = data.first_name || '';
                editBtn.dataset.last = data.last_name || '';
                editBtn.dataset.party = data.party_list || '';
                editBtn.dataset.position = data.position_id || '';
                editBtn.dataset.election = data.election_id || '';
                editBtn.dataset.department = data.department || '';
                editBtn.dataset.election_type = data.election_type || '';
            }

            // Close modal
            closeEditModal();

        } else {
            showNotification(data.error || 'Failed to update candidate.', 'error');
        }
    })
    .catch(err => {
        console.error('Error:', err);
        showNotification('Error updating candidate. Please try again.', 'error');
    })
    .finally(() => {
        // Restore button
        editSubmitBtn.disabled = false;
        editSubmitBtn.innerHTML = originalText;
    });
});

/* ---------- AJAX DELETE CANDIDATE ---------- */
document.addEventListener('click', function(e) {
    if (e.target.classList.contains('delete-candidate')) {
        e.preventDefault();
        const candidateId = e.target.dataset.id;
        deleteCandidate(candidateId);
    }
});

function deleteCandidate(candidateId) {
    if (!confirm('Are you sure you want to delete this candidate?')) {
        return;
    }

    fetch(`/admin/candidates/delete/${candidateId}`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-Requested-With': 'XMLHttpRequest'
        }
    })
    .then(res => {
        if (!res.ok) {
            throw new Error(`HTTP error! status: ${res.status}`);
        }
        return res.json();
    })
    .then(data => {
        if(data.success) {
            showNotification('Candidate deleted successfully!', 'success');
            // Remove row from table
            const row = document.getElementById(`candidate-${candidateId}`);
            if (row) {
                row.remove();
            }
        } else {
            showNotification(data.error || 'Failed to delete candidate.', 'error');
        }
    })
    .catch(err => {
        console.error('Error:', err);
        showNotification('Error deleting candidate. Please try again.', 'error');
    });
}

/* ---------- NOTIFICATION FUNCTION ---------- */
function showNotification(message, type = 'info') {
    // Remove existing notification
    const existingNotification = document.querySelector('.ajax-notification');
    if (existingNotification) {
        existingNotification.remove();
    }

    // Create notification element
    const notification = document.createElement('div');
    notification.className = `ajax-notification ${type}`;
    notification.textContent = message;
    
    // Style the notification
    notification.style.cssText = `
        position: fixed;
        top: 20px;
        right: 20px;
        padding: 12px 20px;
        border-radius: 8px;
        color: white;
        font-weight: 500;
        z-index: 100000;
        animation: slideIn 0.3s ease-out;
        box-shadow: 0 4px 12px rgba(0,0,0,0.15);
        max-width: 350px;
        word-wrap: break-word;
    `;

    // Set background color based on type
    if (type === 'success') {
        notification.style.background = 'linear-gradient(135deg, #06d6a0, #059669)';
    } else if (type === 'error') {
        notification.style.background = 'linear-gradient(135deg, #ef476f, #dc2626)';
    } else {
        notification.style.background = 'linear-gradient(135deg, #4361ee, #3b82f6)';
    }

    document.body.appendChild(notification);

    // Auto-remove after 5 seconds
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

    // Add click to dismiss
    notification.addEventListener('click', () => {
        notification.style.animation = 'slideOut 0.3s ease-out forwards';
        setTimeout(() => {
            if (notification.parentNode) {
                notification.remove();
            }
        }, 300);
    });
}

/* Animation keyframes */
const style = document.createElement('style');
style.textContent = `
    @keyframes slideIn {
        from { transform: translateX(100%); opacity: 0; }
        to { transform: translateX(0); opacity: 1; }
    }
    @keyframes slideOut {
        from { transform: translateX(100%); opacity: 1; }
        to { transform: translateX(0); opacity: 0; }
    }
    @keyframes slideDown {
        from { transform: translateY(-20px); opacity: 0; }
        to { transform: translateY(0); opacity: 1; }
    }
    @keyframes slideUp {
        from { transform: translateY(0); opacity: 1; }
        to { transform: translateY(-20px); opacity: 0; }
    }
`;
document.head.appendChild(style);