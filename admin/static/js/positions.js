// ================= POSITIONS MODAL FUNCTIONS =================

// Get CSRF token
const csrfToken = document.querySelector('meta[name="csrf-token"]')?.getAttribute('content') || '';

// Predefined color palette for positions
const colorPalette = [
    '#3498db', // Blue
    '#e74c3c', // Red
    '#2ecc71', // Green
    '#f39c12', // Orange
    '#9b59b6', // Purple
    '#1abc9c', // Turquoise
    '#e67e22', // Carrot
    '#34495e', // Dark Blue
    '#16a085', // Green Sea
    '#27ae60', // Nephritis
    '#2980b9', // Belize Hole
    '#8e44ad', // Wisteria
    '#2c3e50', // Midnight Blue
    '#d35400', // Pumpkin
    '#c0392b', // Pomegranate
    '#7f8c8d'  // Asbestos
];

// Initialize event listeners for positions modals
document.addEventListener('DOMContentLoaded', function() {
    // Add Position Modal
    const addPositionBtn = document.getElementById('openAddPositionModal');
    if (addPositionBtn) {
        addPositionBtn.addEventListener('click', openAddPositionModal);
    }

    // Position List Modal
    const positionListBtn = document.getElementById('openPositionListModal');
    if (positionListBtn) {
        positionListBtn.addEventListener('click', openPositionListModal);
    }

    // Add Position Form Submit
    const addPositionForm = document.getElementById('addPositionForm');
    if (addPositionForm) {
        addPositionForm.addEventListener('submit', handleAddPosition);
    }

    // Edit Position Form Submit
    const editPositionForm = document.getElementById('editPositionForm');
    if (editPositionForm) {
        editPositionForm.addEventListener('submit', handleEditPosition);
    }

    // Initialize color pickers
    initColorPicker('position_color', 'position_color_hex', 'colorPresets');
    initColorPicker('edit_position_color', 'edit_position_color_hex', 'editColorPresets');
});

// ================= COLOR PICKER FUNCTIONS =================

// Initialize color picker with presets
function initColorPicker(colorInputId, hexInputId, presetsContainerId) {
    const colorInput = document.getElementById(colorInputId);
    const hexInput = document.getElementById(hexInputId);
    const presetsContainer = document.getElementById(presetsContainerId);

    if (!colorInput || !hexInput || !presetsContainer) return;

    // Update hex input when color changes
    colorInput.addEventListener('input', function() {
        hexInput.value = this.value.toUpperCase();
    });

    // Update color input when hex is entered
    hexInput.addEventListener('input', function() {
        const hex = this.value;
        if (/^#[0-9A-F]{6}$/i.test(hex)) {
            colorInput.value = hex;
        }
    });

    // Create color presets
    colorPalette.forEach(color => {
        const preset = document.createElement('div');
        preset.className = 'color-preset';
        preset.style.backgroundColor = color;
        preset.setAttribute('data-color', color);
        
        preset.addEventListener('click', function() {
            colorInput.value = color;
            hexInput.value = color.toUpperCase();
            
            // Remove selected class from all presets
            document.querySelectorAll(`#${presetsContainerId} .color-preset`).forEach(p => {
                p.classList.remove('selected');
            });
            
            // Add selected class to this preset
            this.classList.add('selected');
        });
        
        presetsContainer.appendChild(preset);
    });

    // Select the first preset by default
    if (presetsContainer.children.length > 0) {
        presetsContainer.children[0].classList.add('selected');
    }
}

// ================= MODAL FUNCTIONS =================

// Open Add Position Modal
function openAddPositionModal() {
    const modal = document.getElementById('addPositionModal');
    if (modal) {
        modal.style.display = 'flex';
        document.getElementById('position_name').focus();
        
        // Reset color to first preset
        const colorInput = document.getElementById('position_color');
        const hexInput = document.getElementById('position_color_hex');
        if (colorInput && hexInput && colorPalette.length > 0) {
            colorInput.value = colorPalette[0];
            hexInput.value = colorPalette[0].toUpperCase();
            
            // Reset preset selection
            document.querySelectorAll('#colorPresets .color-preset').forEach((p, index) => {
                if (index === 0) {
                    p.classList.add('selected');
                } else {
                    p.classList.remove('selected');
                }
            });
        }
    }
}

// Close Add Position Modal
function closeAddPositionModal() {
    const modal = document.getElementById('addPositionModal');
    if (modal) {
        modal.style.display = 'none';
        document.getElementById('addPositionForm').reset();
    }
}

// Open Position List Modal
function openPositionListModal() {
    const modal = document.getElementById('positionListModal');
    if (modal) {
        modal.style.display = 'flex';
        loadPositions();
    }
}

// Close Position List Modal
function closePositionListModal() {
    const modal = document.getElementById('positionListModal');
    if (modal) {
        modal.style.display = 'none';
    }
}

// Open Edit Position Modal
function openEditPositionModal(positionId, positionName, positionColor = '#3498db') {
    const modal = document.getElementById('editPositionModal');
    if (modal) {
        document.getElementById('edit_position_id').value = positionId;
        document.getElementById('edit_position_name').value = positionName;
        
        const colorInput = document.getElementById('edit_position_color');
        const hexInput = document.getElementById('edit_position_color_hex');
        
        if (colorInput && hexInput) {
            colorInput.value = positionColor;
            hexInput.value = positionColor.toUpperCase();
            
            // Highlight the matching preset
            document.querySelectorAll('#editColorPresets .color-preset').forEach(p => {
                if (p.getAttribute('data-color') === positionColor) {
                    p.classList.add('selected');
                } else {
                    p.classList.remove('selected');
                }
            });
        }
        
        modal.style.display = 'flex';
        document.getElementById('edit_position_name').focus();
    }
}

// Close Edit Position Modal
function closeEditPositionModal() {
    const modal = document.getElementById('editPositionModal');
    if (modal) {
        modal.style.display = 'none';
        document.getElementById('editPositionForm').reset();
    }
}

// ================= AJAX FUNCTIONS =================

// Load all positions (UPDATED - Color column removed)
async function loadPositions() {
    const tbody = document.getElementById('positionsTableBody');
    if (!tbody) return;

    // Show loading
    tbody.innerHTML = `
        <tr>
            <td colspan="3" class="loading-positions">
                <i class="fa-solid fa-spinner fa-spin"></i> Loading positions...
            </td>
        </tr>
    `;

    try {
        const response = await fetch('/admin/manage_positions/data', {
            method: 'GET',
            headers: {
                'Accept': 'application/json',
                'X-Requested-With': 'XMLHttpRequest'
            }
        });

        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }

        const positions = await response.json();

        if (positions.length === 0) {
            tbody.innerHTML = `
                <tr>
                    <td colspan="3" class="empty-positions">
                        <i class="fa-solid fa-clipboard-list"></i>
                        <h3>No Positions Found</h3>
                        <p>Add your first position using the "Add Position" button.</p>
                    </td>
                </tr>
            `;
            return;
        }

        // Render positions table (without color column)
        tbody.innerHTML = positions.map((pos, index) => `
            <tr id="position-row-${pos.id}">
                <td>${index + 1}</td>
                <td>${escapeHtml(pos.name)}</td>
                <td>
                    <div class="position-actions">
                        <button class="position-action-btn position-edit-btn" 
                                onclick="openEditPositionModal(${pos.id}, '${escapeHtml(pos.name)}', '${pos.color || '#3498db'}')">
                            <i class="fa-solid fa-edit"></i> Edit
                        </button>
                        <button class="position-action-btn position-delete-btn" 
                                onclick="deletePosition(${pos.id}, '${escapeHtml(pos.name)}')">
                            <i class="fa-solid fa-trash"></i> Delete
                        </button>
                    </div>
                </td>
            </tr>
        `).join('');

    } catch (error) {
        console.error('Error loading positions:', error);
        tbody.innerHTML = `
            <tr>
                <td colspan="3" style="text-align: center; color: var(--danger); padding: 30px;">
                    <i class="fa-solid fa-exclamation-circle"></i>
                    <p>Error loading positions. Please try again.</p>
                </td>
            </tr>
        `;
    }
}

// Add new position
async function handleAddPosition(event) {
    event.preventDefault();
    
    const form = event.target;
    const submitBtn = form.querySelector('.add-btn');
    const positionName = document.getElementById('position_name').value.trim();
    const positionColor = document.getElementById('position_color')?.value || '#3498db';
    
    if (!positionName) {
        showNotification('error', 'Please enter a position name.');
        return;
    }
    
    // Disable button and show loading
    const originalText = submitBtn.innerHTML;
    submitBtn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Adding...';
    submitBtn.disabled = true;
    
    try {
        const response = await fetch('/admin/manage_positions', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/x-www-form-urlencoded',
                'X-CSRF-Token': csrfToken,
                'X-Requested-With': 'XMLHttpRequest'
            },
            body: new URLSearchParams({
                'position_name': positionName,
                'position_color': positionColor
            })
        });
        
        const data = await response.json();
        
        if (data.success) {
            showNotification('success', data.message);
            closeAddPositionModal();
            
            // Refresh positions list if modal is open
            if (document.getElementById('positionListModal').style.display === 'flex') {
                loadPositions();
            }
            
            // Refresh position dropdown in candidate forms
            refreshPositionDropdowns();
            
        } else {
            showNotification('error', data.message || 'Failed to add position.');
        }
        
    } catch (error) {
        console.error('Error adding position:', error);
        showNotification('error', 'Network error. Please try again.');
    } finally {
        // Restore button
        submitBtn.innerHTML = originalText;
        submitBtn.disabled = false;
    }
}

// Edit position
async function handleEditPosition(event) {
    event.preventDefault();
    
    const form = event.target;
    const submitBtn = form.querySelector('.edit-btn');
    const positionId = document.getElementById('edit_position_id').value;
    const positionName = document.getElementById('edit_position_name').value.trim();
    const positionColor = document.getElementById('edit_position_color')?.value || '#3498db';
    
    if (!positionName) {
        showNotification('error', 'Please enter a position name.');
        return;
    }
    
    // Disable button and show loading
    const originalText = submitBtn.innerHTML;
    submitBtn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Updating...';
    submitBtn.disabled = true;
    
    try {
        const response = await fetch(`/admin/manage_positions/${positionId}`, {
            method: 'PUT',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRF-Token': csrfToken,
                'X-Requested-With': 'XMLHttpRequest'
            },
            body: JSON.stringify({
                position_name: positionName,
                position_color: positionColor
            })
        });
        
        const data = await response.json();
        
        if (data.success) {
            showNotification('success', data.message);
            closeEditPositionModal();
            
            // Refresh positions list
            loadPositions();
            
            // Refresh position dropdowns
            refreshPositionDropdowns();
            
        } else {
            showNotification('error', data.message || 'Failed to update position.');
        }
        
    } catch (error) {
        console.error('Error updating position:', error);
        showNotification('error', 'Network error. Please try again.');
    } finally {
        // Restore button
        submitBtn.innerHTML = originalText;
        submitBtn.disabled = false;
    }
}

// Delete position
async function deletePosition(positionId, positionName) {
    if (!confirm(`Are you sure you want to delete the position "${positionName}"?\n\nThis action cannot be undone.`)) {
        return;
    }
    
    try {
        const response = await fetch(`/admin/manage_positions/${positionId}`, {
            method: 'DELETE',
            headers: {
                'X-CSRF-Token': csrfToken,
                'X-Requested-With': 'XMLHttpRequest'
            }
        });
        
        const data = await response.json();
        
        if (data.success) {
            showNotification('success', data.message);
            
            // Remove row from table
            const row = document.getElementById(`position-row-${positionId}`);
            if (row) {
                row.remove();
            }
            
            // If no positions left, show empty state
            const tbody = document.getElementById('positionsTableBody');
            if (tbody && tbody.children.length === 0) {
                loadPositions(); // This will show empty state
            }
            
            // Refresh position dropdowns
            refreshPositionDropdowns();
            
        } else {
            showNotification('error', data.message || 'Failed to delete position.');
        }
        
    } catch (error) {
        console.error('Error deleting position:', error);
        showNotification('error', 'Network error. Please try again.');
    }
}

// Refresh position dropdowns in candidate forms
function refreshPositionDropdowns() {
    // Refresh for add candidate form
    const addPositionSelect = document.getElementById('add_position');
    const editPositionSelect = document.getElementById('edit_position');
    
    // Reload positions
    fetch('/admin/manage_positions/data')
        .then(response => response.json())
        .then(positions => {
            // Update add position dropdown
            if (addPositionSelect) {
                const currentValue = addPositionSelect.value;
                addPositionSelect.innerHTML = positions.map(pos => 
                    `<option value="${pos.id}" ${pos.id == currentValue ? 'selected' : ''}>${escapeHtml(pos.name)}</option>`
                ).join('');
            }
            
            // Update edit position dropdown
            if (editPositionSelect) {
                const currentValue = editPositionSelect.value;
                editPositionSelect.innerHTML = positions.map(pos => 
                    `<option value="${pos.id}" ${pos.id == currentValue ? 'selected' : ''}>${escapeHtml(pos.name)}</option>`
                ).join('');
            }
        })
        .catch(error => console.error('Error refreshing position dropdowns:', error));
}

// ================= HELPER FUNCTIONS =================

// Show notification
function showNotification(type, message) {
    const existing = document.querySelector('.custom-notification');
    if (existing) existing.remove();
    
    const notification = document.createElement('div');
    notification.className = `custom-notification ${type}`;
    
    let icon = 'fa-info-circle';
    if (type === 'success') icon = 'fa-check-circle';
    if (type === 'error') icon = 'fa-exclamation-circle';
    if (type === 'info') icon = 'fa-info-circle';
    
    notification.innerHTML = `
        <i class="fa-solid ${icon}"></i>
        <span>${message}</span>
        <button onclick="this.parentElement.remove()">
            <i class="fa-solid fa-times"></i>
        </button>
    `;
    
    document.body.appendChild(notification);
    
    // Auto-remove after 5 seconds
    setTimeout(() => {
        if (notification.parentElement) {
            notification.remove();
        }
    }, 5000);
}

// Escape HTML to prevent XSS
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// Initialize notification styles
if (!document.querySelector('#notification-styles')) {
    const style = document.createElement('style');
    style.id = 'notification-styles';
    style.textContent = `
        .custom-notification {
            position: fixed;
            top: 20px;
            right: 20px;
            padding: 15px 20px;
            border-radius: 8px;
            display: flex;
            align-items: center;
            gap: 12px;
            z-index: 10000;
            box-shadow: 0 4px 12px rgba(0,0,0,0.15);
            animation: slideIn 0.3s ease;
            max-width: 500px;
            min-width: 300px;
        }
        
        .custom-notification.success {
            background: #d4edda;
            color: #155724;
            border-left: 4px solid #28a745;
        }
        
        .custom-notification.error {
            background: #f8d7da;
            color: #721c24;
            border-left: 4px solid #dc3545;
        }
        
        .custom-notification.info {
            background: #d1ecf1;
            color: #0c5460;
            border-left: 4px solid #17a2b8;
        }
        
        .custom-notification button {
            background: none;
            border: none;
            color: inherit;
            cursor: pointer;
            padding: 0;
            margin-left: auto;
            opacity: 0.7;
            transition: opacity 0.2s;
        }
        
        .custom-notification button:hover {
            opacity: 1;
        }
        
        @keyframes slideIn {
            from {
                transform: translateX(100%);
                opacity: 0;
            }
            to {
                transform: translateX(0);
                opacity: 1;
            }
        }
    `;
    document.head.appendChild(style);
}

// Close modal when clicking outside
document.addEventListener('click', function(event) {
    // Add Position Modal
    const addPositionModal = document.getElementById('addPositionModal');
    if (addPositionModal && event.target === addPositionModal) {
        closeAddPositionModal();
    }
    
    // Position List Modal
    const positionListModal = document.getElementById('positionListModal');
    if (positionListModal && event.target === positionListModal) {
        closePositionListModal();
    }
    
    // Edit Position Modal
    const editPositionModal = document.getElementById('editPositionModal');
    if (editPositionModal && event.target === editPositionModal) {
        closeEditPositionModal();
    }
});

// Close modal with Escape key
document.addEventListener('keydown', function(event) {
    if (event.key === 'Escape') {
        closeAddPositionModal();
        closePositionListModal();
        closeEditPositionModal();
    }
});