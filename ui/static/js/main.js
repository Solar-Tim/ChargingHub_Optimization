/**
 * ChargingHub Optimization - Main JavaScript
 * 
 * This file contains common functionality used across all pages of the UI.
 */

// Initialize on document ready
document.addEventListener('DOMContentLoaded', function() {
    // Socket.IO connection setup
    const socket = io();
    
    // Socket connection status handling
    socket.on('connect', function() {
        console.log('WebSocket connected');
    });
    
    socket.on('disconnect', function() {
        console.log('WebSocket disconnected');
    });
    
    // Handle notifications (flash messages)
    function showNotification(message, type = 'info') {
        const notificationContainer = document.getElementById('notification-container');
        
        if (!notificationContainer) {
            // Create notification container if it doesn't exist
            const container = document.createElement('div');
            container.id = 'notification-container';
            container.style.position = 'fixed';
            container.style.top = '10px';
            container.style.right = '10px';
            container.style.zIndex = '9999';
            document.body.appendChild(container);
        }
        
        // Create notification element
        const notification = document.createElement('div');
        notification.className = `alert alert-${type} alert-dismissible fade show`;
        notification.role = 'alert';
        notification.innerHTML = `
            ${message}
            <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
        `;
        
        // Add to container
        document.getElementById('notification-container').appendChild(notification);
        
        // Auto-dismiss after 5 seconds
        setTimeout(() => {
            notification.classList.remove('show');
            setTimeout(() => {
                notification.remove();
            }, 150); // Wait for fade out animation
        }, 5000);
    }
    
    // Expose function globally
    window.showNotification = showNotification;
    
    // Set up tooltips
    const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    tooltipTriggerList.map(function(tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });
    
    // Process status update handling
    socket.on('process_status', function(data) {
        // This event is emitted by the server when a process status changes
        if (data.id && data.status) {
            console.log(`Process ${data.id} status: ${data.status}`);
            
            // Find status indicators for this process
            const indicators = document.querySelectorAll(`[data-process-id="${data.id}"]`);
            
            indicators.forEach(indicator => {
                // Remove all status classes
                indicator.classList.remove('running', 'stopped', 'warning');
                
                // Add the appropriate class based on status
                if (data.status === 'running') {
                    indicator.classList.add('running');
                } else if (data.status === 'stopped') {
                    indicator.classList.add('stopped');
                } else if (data.status === 'warning') {
                    indicator.classList.add('warning');
                }
            });
            
            // Also update any text elements that show process status
            const statusTexts = document.querySelectorAll(`[data-process-status-id="${data.id}"]`);
            statusTexts.forEach(element => {
                element.textContent = data.status;
            });
        }
    });
    
    // Process output handling
    socket.on('process_output', function(data) {
        // This event is emitted when a process produces output
        if (data.id && data.output) {
            // Find output containers for this process
            const containers = document.querySelectorAll(`[data-process-output-id="${data.id}"]`);
            
            containers.forEach(container => {
                container.innerHTML += data.output + '\n';
                container.scrollTop = container.scrollHeight;
            });
        }
    });
    
    // Form validation helper
    function validateForm(form) {
        // Add was-validated class to trigger Bootstrap validation styles
        form.classList.add('was-validated');
        
        // Check validity
        return form.checkValidity();
    }
    
    // Expose form validation function globally
    window.validateForm = validateForm;
});