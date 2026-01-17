document.addEventListener('DOMContentLoaded', () => {
    // ================= MODAL HANDLING =================
    const roleModal = document.getElementById('roleModal');
    const viewRolesModal = document.getElementById('viewRolesModal');
    const editRoleModal = document.getElementById('editRoleModal');

    document.getElementById('openRoleModal').onclick = () => roleModal.style.display = 'flex';
    document.getElementById('closeRoleModal').onclick = () => roleModal.style.display = 'none';
    document.getElementById('openViewRolesModal').onclick = () => viewRolesModal.style.display = 'flex';
    document.getElementById('closeViewRolesModal').onclick = () => viewRolesModal.style.display = 'none';
    document.getElementById('closeEditRoleModal').onclick = () => editRoleModal.style.display = 'none';

    // ================= EDIT ROLE FUNCTION =================
    const editRoleForm = document.getElementById('editRoleForm');
    const editRoleName = document.getElementById('editRoleName');
    window.openEditRoleModal = function(roleId, roleName) {
        editRoleName.value = roleName;
        editRoleForm.dataset.roleId = roleId;
        editRoleModal.style.display = 'flex';
        editRoleName.focus();
    }

    // ================= NOTIFICATION FUNCTIONS =================
    function showModalNotification(notificationId, message, type) {
        const notification = document.getElementById(notificationId);
        if (!notification) return;
        notification.innerHTML = `
            <i class="fa-solid ${type === 'success' ? 'fa-check-circle' : 'fa-exclamation-circle'}"></i>
            <span>${message}</span>
        `;
        notification.className = `modal-notification ${type}`;
        notification.style.display = 'flex';
        setTimeout(() => {
            notification.style.animation = 'fadeOut 0.3s ease';
            setTimeout(() => {
                notification.style.display = 'none';
                notification.style.animation = '';
            }, 300);
        }, 4000);
    }

    function showFormNotification(message, type) {
        const notification = document.getElementById('userFormNotification');
        if (!notification) return;
        notification.innerHTML = `
            <i class="fa-solid ${type === 'success' ? 'fa-check-circle' : 'fa-exclamation-circle'}"></i>
            <span>${message}</span>
        `;
        notification.className = `form-notification ${type}`;
        notification.style.display = 'flex';
        setTimeout(() => {
            notification.style.animation = 'fadeOut 0.3s ease';
            setTimeout(() => {
                notification.style.display = 'none';
                notification.style.animation = '';
            }, 300);
        }, 4000);
    }

    // ================= AJAX: Add Role =================
    const addRoleForm = document.getElementById('addRoleForm');
    const addRoleIcon = document.getElementById('addRoleIcon');
    addRoleForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        addRoleIcon.className = 'loading-spinner';
        const formData = new FormData(addRoleForm);
        try {
            const res = await fetch(window.USERS_URLS.addRole, { method: 'POST', body: formData });
            addRoleIcon.className = 'fa-solid fa-save';
            if (res.redirected) {
                showModalNotification('addRoleNotification', 'Role added successfully!', 'success');
                addRoleForm.reset();
                updateRolesDropdown();
                loadRolesTable();
            } else {
                showModalNotification('addRoleNotification', 'Error adding role. Please try again.', 'error');
            }
        } catch (err) {
            addRoleIcon.className = 'fa-solid fa-save';
            showModalNotification('addRoleNotification', 'Network error. Please try again.', 'error');
            console.error(err);
        }
    });

    // ================= AJAX: Edit Role =================
    const editRoleBtn = document.getElementById('editRoleBtn');
    const editRoleIcon = document.getElementById('editRoleIcon');
    editRoleForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        const roleId = editRoleForm.dataset.roleId;
        editRoleIcon.className = 'loading-spinner';
        const formData = new FormData(editRoleForm);
        try {
            const res = await fetch(`${window.USERS_URLS.editRole}${roleId}`, { method: 'POST', body: formData });
            editRoleIcon.className = 'fa-solid fa-save';
            if (res.redirected) {
                showModalNotification('editRoleNotification', 'Role updated successfully!', 'success');
                updateRolesDropdown();
                loadRolesTable();
                setTimeout(() => { editRoleModal.style.display = 'none'; }, 1500);
            } else {
                showModalNotification('editRoleNotification', 'Error updating role. Please try again.', 'error');
            }
        } catch (err) {
            editRoleIcon.className = 'fa-solid fa-save';
            showModalNotification('editRoleNotification', 'Network error. Please try again.', 'error');
            console.error(err);
        }
    });

    // ================= AJAX: Delete Role =================
    window.deleteRole = async function(roleId, btn) {
        if (!confirm('Are you sure you want to delete this role?')) return;
        const icon = btn.querySelector('i');
        const originalClass = icon.className;
        icon.className = 'loading-spinner';
        try {
            const res = await fetch(`${window.USERS_URLS.deleteRole}${roleId}`, { method: 'POST' });
            icon.className = originalClass;
            if (res.redirected) {
                showModalNotification('viewRolesNotification', 'Role deleted successfully!', 'success');
                updateRolesDropdown();
                loadRolesTable();
            } else {
                showModalNotification('viewRolesNotification', 'Error deleting role. Please try again.', 'error');
            }
        } catch (err) {
            icon.className = originalClass;
            showModalNotification('viewRolesNotification', 'Network error. Please try again.', 'error');
            console.error(err);
        }
    }

    // ================= AJAX: Create User =================
    const createUserForm = document.getElementById('createUserForm');
    const createUserBtn = document.getElementById('createUserBtn');
    const createUserIcon = document.getElementById('createUserIcon');
    createUserForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        createUserIcon.className = 'loading-spinner';
        createUserBtn.disabled = true;
        const formData = new FormData(createUserForm);
        try {
            const res = await fetch(window.USERS_URLS.createUser, { method: 'POST', body: formData });
            if (res.redirected) {
                createUserForm.reset();
                showFormNotification('User created successfully!', 'success');
                loadUsersTable();
            } else {
                showFormNotification('Error creating user. Please check your inputs.', 'error');
            }
        } catch (err) {
            showFormNotification('Network error. Please try again.', 'error');
            console.error(err);
        } finally {
            createUserIcon.className = 'fa-solid fa-user-plus';
            createUserBtn.disabled = false;
        }
    });

    // ================= UPDATE ROLES DROPDOWN =================
    async function updateRolesDropdown() {
        try {
            const res = await fetch(window.USERS_URLS.createUser);
            const text = await res.text();
            const parser = new DOMParser();
            const doc = parser.parseFromString(text, 'text/html');
            const roleOptions = doc.querySelectorAll('#roleSelect option');
            if (roleOptions.length > 0) {
                const roleSelect = document.getElementById('roleSelect');
                const firstOption = roleSelect.options[0];
                roleSelect.innerHTML = '';
                roleSelect.appendChild(firstOption);
                roleOptions.forEach(option => {
                    if (option.value !== '') {
                        const newOption = document.createElement('option');
                        newOption.value = option.value;
                        newOption.textContent = option.textContent;
                        roleSelect.appendChild(newOption);
                    }
                });
            }
        } catch (err) {
            console.error('Error updating roles dropdown:', err);
        }
    }

    // ================= RELOAD ROLES TABLE =================
    async function loadRolesTable() {
        try {
            const res = await fetch(window.USERS_URLS.createUser);
            const text = await res.text();
            const parser = new DOMParser();
            const doc = parser.parseFromString(text, 'text/html');
            const newRolesTableBody = doc.querySelector('#rolesTableBody');
            if (newRolesTableBody) {
                document.querySelector('#rolesTableBody').innerHTML = newRolesTableBody.innerHTML;
            }
        } catch (err) {
            console.error('Error loading roles table:', err);
        }
    }

    // ================= RELOAD USERS TABLE =================
    async function loadUsersTable() {
        try {
            const res = await fetch(window.USERS_URLS.createUser);
            const text = await res.text();
            const parser = new DOMParser();
            const doc = parser.parseFromString(text, 'text/html');
            const newUsersTableBody = doc.querySelector('#usersTableBody');
            if (newUsersTableBody) {
                document.querySelector('#usersTableBody').innerHTML = newUsersTableBody.innerHTML;
            }
        } catch (err) {
            console.error('Error loading users table:', err);
        }
    }

    // ================= CLOSE MODALS OUTSIDE CLICK =================
    window.addEventListener('click', (e) => {
        if (e.target == roleModal) roleModal.style.display = 'none';
        if (e.target == viewRolesModal) viewRolesModal.style.display = 'none';
        if (e.target == editRoleModal) editRoleModal.style.display = 'none';
    });

    // ================= ESCAPE KEY CLOSE =================
    window.addEventListener('keydown', (e) => {
        if (e.key === 'Escape') {
            roleModal.style.display = 'none';
            viewRolesModal.style.display = 'none';
            editRoleModal.style.display = 'none';
        }
    });
});
