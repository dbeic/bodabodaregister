/**
 * Main JavaScript for Bodaboda SACCO Registration System
 * Enhanced with batch processing and print functionality
 */

document.addEventListener('DOMContentLoaded', function() {
    // Auto-dismiss alerts after 5 seconds
    const alerts = document.querySelectorAll('.alert');
    alerts.forEach(function(alert) {
        setTimeout(function() {
            const closeBtn = alert.querySelector('.btn-close');
            if (closeBtn) {
                closeBtn.click();
            }
        }, 5000);
    });

    // Add CSRF token to all AJAX requests
    const csrfToken = document.querySelector('meta[name="csrf-token"]')?.getAttribute('content');
    if (csrfToken) {
        fetch('', {
            headers: {
                'X-CSRFToken': csrfToken
            }
        });
    }

    // Confirm delete actions
    const deleteButtons = document.querySelectorAll('.delete-confirm');
    deleteButtons.forEach(function(btn) {
        btn.addEventListener('click', function(e) {
            if (!confirm('Are you sure you want to delete this item? This action cannot be undone.')) {
                e.preventDefault();
            }
        });
    });

    // Batch issuance form handling
    const batchForm = document.getElementById('batchForm');
    if (batchForm) {
        batchForm.addEventListener('submit', function(e) {
            const selectedFormat = document.querySelector('input[name="format_type"]:checked');
            if (!selectedFormat) {
                e.preventDefault();
                showToast('Please select a print format.', 'warning');
                return;
            }
            
            const confirmMsg = `This will generate badges for all unissued members (${document.querySelector('.unissued-count')?.textContent || 'unknown'}). Continue?`;
            if (!confirm(confirmMsg)) {
                e.preventDefault();
            }
        });
    }

    // Form validation helper
    function validateForm(form) {
        const inputs = form.querySelectorAll('input[required], select[required], textarea[required]');
        let isValid = true;
        
        inputs.forEach(function(input) {
            if (!input.value.trim()) {
                input.classList.add('is-invalid');
                isValid = false;
            } else {
                input.classList.remove('is-invalid');
            }
        });
        
        return isValid;
    }

    // Phone number formatting
    const phoneInputs = document.querySelectorAll('input[type="tel"]');
    phoneInputs.forEach(function(input) {
        input.addEventListener('input', function() {
            // Remove non-numeric characters
            this.value = this.value.replace(/[^0-9+]/g, '');
        });
    });

    // National ID formatting
    const idInputs = document.querySelectorAll('#national_id');
    idInputs.forEach(function(input) {
        input.addEventListener('input', function() {
            // Remove non-numeric characters
            this.value = this.value.replace(/[^0-9]/g, '');
        });
    });

    // Member number formatting (allow letters and numbers)
    const memberInputs = document.querySelectorAll('#member_number');
    memberInputs.forEach(function(input) {
        input.addEventListener('input', function() {
            // Convert to uppercase
            this.value = this.value.toUpperCase();
        });
    });

    // Image preview for file inputs
    const fileInputs = document.querySelectorAll('input[type="file"][accept*="image"]');
    fileInputs.forEach(function(input) {
        input.addEventListener('change', function() {
            const file = this.files[0];
            if (file) {
                const previewId = this.getAttribute('data-preview') || 'imagePreview';
                const preview = document.getElementById(previewId);
                
                if (preview) {
                    const reader = new FileReader();
                    reader.onload = function(e) {
                        preview.innerHTML = `<img src="${e.target.result}" class="img-fluid rounded" style="max-height: 200px;">`;
                    };
                    reader.readAsDataURL(file);
                }
            }
        });
    });

    // Auto-submit search form on enter
    const searchInputs = document.querySelectorAll('input[type="search"]');
    searchInputs.forEach(function(input) {
        input.addEventListener('keypress', function(e) {
            if (e.key === 'Enter') {
                const form = this.closest('form');
                if (form) {
                    form.submit();
                }
            }
        });
    });

    // Tooltip initialization
    const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    tooltipTriggerList.map(function(tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });

    // Popover initialization
    const popoverTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="popover"]'));
    popoverTriggerList.map(function(popoverTriggerEl) {
        return new bootstrap.Popover(popoverTriggerEl);
    });

    // Print badge functionality with options
    document.querySelectorAll('.print-badge').forEach(function(btn) {
        btn.addEventListener('click', function() {
            const quality = this.getAttribute('data-quality') || 'standard';
            if (quality === 'high') {
                // Add bleed indicator for print
                const badgeContainer = document.querySelector('.badge-display')?.closest('.card-body');
                if (badgeContainer) {
                    badgeContainer.classList.add('bleed-indicator');
                    setTimeout(() => {
                        badgeContainer.classList.remove('bleed-indicator');
                    }, 1000);
                }
            }
            window.print();
        });
    });

    // Download badge with options
    document.querySelectorAll('.download-badge').forEach(function(btn) {
        btn.addEventListener('click', function(e) {
            e.preventDefault();
            const url = this.getAttribute('href');
            const format = this.getAttribute('data-format') || 'png';
            const bleed = this.getAttribute('data-bleed') || 'false';
            
            if (url) {
                const downloadUrl = `${url}?format=${format}&bleed=${bleed}`;
                window.location.href = downloadUrl;
                showToast(`Downloading ${format.toUpperCase()} badge...`, 'info');
            }
        });
    });

    // Quality selector for batch issuance
    document.querySelectorAll('.quality-option').forEach(function(el) {
        el.addEventListener('click', function() {
            document.querySelectorAll('.quality-option').forEach(function(opt) {
                opt.classList.remove('selected');
            });
            this.classList.add('selected');
            const qualityInput = document.getElementById('print_quality');
            if (qualityInput) {
                qualityInput.value = this.getAttribute('data-value');
            }
        });
    });

    // Keyboard shortcuts
    document.addEventListener('keydown', function(e) {
        // Ctrl+Shift+R: Go to register page
        if (e.ctrlKey && e.shiftKey && e.key === 'R') {
            window.location.href = '/register';
            e.preventDefault();
        }
        // Ctrl+Shift+D: Go to dashboard
        if (e.ctrlKey && e.shiftKey && e.key === 'D') {
            window.location.href = '/dashboard';
            e.preventDefault();
        }
        // Ctrl+Shift+H: Go to home
        if (e.ctrlKey && e.shiftKey && e.key === 'H') {
            window.location.href = '/';
            e.preventDefault();
        }
        // Ctrl+Shift+B: Go to batch issuance
        if (e.ctrlKey && e.shiftKey && e.key === 'B') {
            window.location.href = '/badge/batch';
            e.preventDefault();
        }
        // Ctrl+P: Print current page
        if (e.ctrlKey && e.key === 'p') {
            // Allow default print behavior
            return true;
        }
    });

    // Batch progress simulation
    const batchProgressBtn = document.getElementById('startBatch');
    if (batchProgressBtn) {
        batchProgressBtn.addEventListener('click', function() {
            const progressBar = document.getElementById('batchProgress');
            if (progressBar) {
                let progress = 0;
                const interval = setInterval(function() {
                    progress += Math.random() * 10;
                    if (progress >= 100) {
                        progress = 100;
                        clearInterval(interval);
                        showToast('Batch processing complete!', 'success');
                    }
                    progressBar.style.width = progress + '%';
                    progressBar.textContent = Math.round(progress) + '%';
                    progressBar.setAttribute('aria-valuenow', progress);
                }, 500);
            }
        });
    }

    // Filter buttons for dashboard
    document.querySelectorAll('.filter-btn').forEach(function(btn) {
        btn.addEventListener('click', function() {
            const filter = this.getAttribute('data-filter');
            const currentUrl = new URL(window.location.href);
            currentUrl.searchParams.set('filter', filter);
            window.location.href = currentUrl.toString();
        });
    });

    console.log('Bodaboda SACCO Registration System loaded successfully!');
    console.log('Features: Badge Generation, QR Codes, Batch Issuance, Print Ready');
});

// Utility function for making AJAX requests
function makeRequest(url, method = 'GET', data = null) {
    return new Promise(function(resolve, reject) {
        const xhr = new XMLHttpRequest();
        xhr.open(method, url, true);
        xhr.setRequestHeader('Content-Type', 'application/json');
        xhr.setRequestHeader('X-Requested-With', 'XMLHttpRequest');
        
        const csrfToken = document.querySelector('meta[name="csrf-token"]')?.getAttribute('content');
        if (csrfToken) {
            xhr.setRequestHeader('X-CSRFToken', csrfToken);
        }
        
        xhr.onload = function() {
            if (xhr.status >= 200 && xhr.status < 300) {
                try {
                    resolve(JSON.parse(xhr.responseText));
                } catch (e) {
                    resolve(xhr.responseText);
                }
            } else {
                reject(new Error(xhr.statusText));
            }
        };
        
        xhr.onerror = function() {
            reject(new Error('Network error'));
        };
        
        if (data) {
            xhr.send(JSON.stringify(data));
        } else {
            xhr.send();
        }
    });
}

// Utility function for showing toast notifications
function showToast(message, type = 'info', duration = 3000) {
    const toastContainer = document.getElementById('toastContainer');
    if (!toastContainer) {
        // Create container if it doesn't exist
        const container = document.createElement('div');
        container.id = 'toastContainer';
        container.style.position = 'fixed';
        container.style.bottom = '20px';
        container.style.right = '20px';
        container.style.zIndex = '9999';
        document.body.appendChild(container);
    }
    
    const toast = document.createElement('div');
    toast.className = `toast align-items-center text-white bg-${type} border-0`;
    toast.role = 'alert';
    toast.ariaLive = 'assertive';
    toast.ariaAtomic = 'true';
    
    toast.innerHTML = `
        <div class="d-flex">
            <div class="toast-body">
                ${message}
            </div>
            <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast"></button>
        </div>
    `;
    
    document.getElementById('toastContainer').appendChild(toast);
    const bsToast = new bootstrap.Toast(toast, { delay: duration });
    bsToast.show();
    
    toast.addEventListener('hidden.bs.toast', function() {
        toast.remove();
    });
}

// Utility function for batch badge issuance
function issueBatchBadges(memberIds, options = {}) {
    const format = options.format || 'pdf';
    const quality = options.quality || 'high';
    const bleed = options.bleed || true;
    
    return makeRequest('/badge/batch', 'POST', {
        member_ids: memberIds,
        format: format,
        quality: quality,
        bleed: bleed
    });
}

// Utility function to get badge status
function getBadgeStatus(memberId) {
    return makeRequest(`/badge/status/${memberId}`);
}

// Utility function to issue single badge
function issueBadge(memberId, issuedBy = 'system') {
    return makeRequest(`/badge/issue/${memberId}`, 'POST', {
        issued_by: issuedBy
    });
}
