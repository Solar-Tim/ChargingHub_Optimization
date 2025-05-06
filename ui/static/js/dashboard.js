/**
 * ChargingHub Optimization - Dashboard JavaScript
 * 
 * This file contains functionality specific to the dashboard page.
 */

document.addEventListener('DOMContentLoaded', function() {
    // Socket.IO connection
    const socket = io();
    let currentProcess = null;
    let autoscroll = true;
    let activeProcesses = {};
    
    // DOM elements
    const terminalOutput = document.getElementById('terminal-output');
    const stopAllBtn = document.getElementById('stop-all-btn');
    const clearOutputBtn = document.getElementById('clear-output-btn');
    const followOutputBtn = document.getElementById('follow-output-btn');
    
    // Phase progress elements
    const phaseElements = {
        'traffic': {
            status: document.getElementById('phase1-status'),
            progress: document.getElementById('phase1-progress'),
            progressText: document.getElementById('phase1-progress-text'),
            details: document.getElementById('phase1-details')
        },
        'charging_hub': {
            status: document.getElementById('phase2-status'),
            progress: document.getElementById('phase2-progress'),
            progressText: document.getElementById('phase2-progress-text'),
            details: document.getElementById('phase2-details'),
            substeps: {
                'truck_matching': {
                    indicator: document.getElementById('substep2-1-indicator'),
                    text: document.getElementById('substep2-1-text')
                },
                'hub_configuration': {
                    indicator: document.getElementById('substep2-2-indicator'),
                    text: document.getElementById('substep2-2-text')
                },
                'demand_optimization': {
                    indicator: document.getElementById('substep2-3-indicator'),
                    text: document.getElementById('substep2-3-text')
                }
            }
        },
        'grid_opt': {
            status: document.getElementById('phase3-status'),
            progress: document.getElementById('phase3-progress'),
            progressText: document.getElementById('phase3-progress-text'),
            details: document.getElementById('phase3-details')
        }
    };
    
    // Execution configuration switches
    const configSwitches = {
        'run-traffic-calculation': document.getElementById('run-traffic-calculation'),
        'run-charging-hub-setup': document.getElementById('run-charging-hub-setup'),
        'run-grid-optimization': document.getElementById('run-grid-optimization'),
        'run-truck-matching': document.getElementById('run-truck-matching'),
        'run-hub-configuration': document.getElementById('run-hub-configuration'),
        'run-demand-optimization': document.getElementById('run-demand-optimization'),
        'use-distance-calculation': document.getElementById('use-distance-calculation'),
        'create-maps': document.getElementById('create-maps'),
        'include-battery': document.getElementById('include-battery'),
        'use-manual-charger-count': document.getElementById('use-manual-charger-count')
    };
    
    // Set initial phase states
    resetPhases();
    
    // Connect to Socket.IO
    socket.on('connect', function() {
        appendToTerminal('WebSocket connected. Ready to run optimization.');
        
        // Request current process status
        fetch('/api/processes/active')
            .then(response => response.json())
            .then(data => {
                // Initialize with active processes
                if (data.processes && data.processes.length > 0) {
                    data.processes.forEach(process => {
                        addProcess(process);
                    });
                    updateUI();
                }
            })
            .catch(error => console.error('Error fetching active processes:', error));
    });
    
    socket.on('disconnect', function() {
        appendToTerminal('WebSocket disconnected. Reconnecting...');
    });
    
    // Process event handlers
    socket.on('process_started', function(data) {
        console.log('Process started:', data);
        addProcess({
            id: data.id,
            status: 'running'
        });
        updateUI();
        
        // Update phase status
        updatePhaseStatus(data.id, 'running');
    });
    
    socket.on('process_output', function(data) {
        if (activeProcesses[data.id]) {
            activeProcesses[data.id].output.push(data.output);
            appendToTerminal(data.output);
            
            // Parse output for progress indicators
            parseProgressFromOutput(data.id, data.output);
        }
    });
    
    socket.on('process_completed', function(data) {
        console.log('Process completed:', data);
        
        if (activeProcesses[data.id]) {
            activeProcesses[data.id].status = data.success ? 'completed' : 'failed';
            activeProcesses[data.id].exitCode = data.exitCode;
            
            // Update phase status
            updatePhaseStatus(
                data.id, 
                data.success ? 'completed' : 'failed', 
                data.success ? 100 : null
            );
            
            updateUI();
        }
    });
    
    // Button event handlers
    document.getElementById('run-full-optimization').addEventListener('click', function() {
        runOptimization('main');
    });
    
    document.getElementById('run-traffic-btn').addEventListener('click', function() {
        runOptimization('traffic');
    });
    
    document.getElementById('run-hub-btn').addEventListener('click', function() {
        runOptimization('charging_hub');
    });
    
    document.getElementById('run-grid-btn').addEventListener('click', function() {
        runOptimization('grid_opt');
    });
    
    stopAllBtn.addEventListener('click', function() {
        if (!confirm('Are you sure you want to stop all running processes?')) {
            return;
        }
        
        stopAllBtn.disabled = true;
        
        fetch('/api/processes/stop_all', {
            method: 'POST'
        })
            .then(response => response.json())
            .then(data => {
                appendToTerminal('Stopped all processes.');
                
                // Update all running processes
                Object.keys(activeProcesses).forEach(processId => {
                    if (activeProcesses[processId].status === 'running') {
                        activeProcesses[processId].status = 'stopped';
                        updatePhaseStatus(processId, 'stopped');
                    }
                });
                
                updateUI();
            })
            .catch(error => {
                console.error('Error stopping processes:', error);
                appendToTerminal('Error stopping processes: ' + error.message);
                stopAllBtn.disabled = false;
            });
    });
    
    clearOutputBtn.addEventListener('click', function() {
        clearTerminal();
    });
    
    followOutputBtn.addEventListener('click', function() {
        autoscroll = !autoscroll;
        followOutputBtn.classList.toggle('active', autoscroll);
        
        if (autoscroll) {
            scrollToBottom();
        }
    });
    
    document.getElementById('save-execution-config').addEventListener('click', function() {
        saveExecutionConfig();
    });
    
    // Helper functions
    function addProcess(process) {
        if (!activeProcesses[process.id]) {
            activeProcesses[process.id] = {
                id: process.id,
                status: process.status || 'running',
                output: [],
                exitCode: process.returnCode
            };
            
            // Request process output if we don't have it
            fetch(`/api/process/${process.id}/status`)
                .then(response => response.json())
                .then(data => {
                    if (data.logs) {
                        activeProcesses[process.id].output = data.logs;
                        
                        // If this is our first process, show its output
                        if (Object.keys(activeProcesses).length === 1) {
                            data.logs.forEach(line => appendToTerminal(line));
                            
                            // Parse all logs to update progress indicators
                            data.logs.forEach(line => parseProgressFromOutput(process.id, line));
                        }
                    }
                })
                .catch(error => {
                    console.error(`Error fetching logs for process ${process.id}:`, error);
                });
        }
    }
    
    function updateUI() {
        // Check if there are any running processes
        const runningProcesses = Object.values(activeProcesses).filter(p => p.status === 'running');
        stopAllBtn.disabled = runningProcesses.length === 0;
    }
    
    function appendToTerminal(text) {
        const preElem = terminalOutput.querySelector('pre');
        
        if (preElem) {
            // Style text based on content
            let styledText = text;
            
            // Process PHASE/STEP identifiers
            if (text.includes('PHASE 1') || text.includes('STEP 1') || text.includes('Traffic Calculation')) {
                styledText = `<span class="text-info fw-bold">${text}</span>`;
            } 
            else if (text.includes('PHASE 2') || text.includes('STEP 2') || text.includes('Charging Hub Setup')) {
                styledText = `<span class="text-info fw-bold">${text}</span>`;
            }
            else if (text.includes('PHASE 3') || text.includes('STEP 3') || text.includes('Grid Optimization')) {
                styledText = `<span class="text-info fw-bold">${text}</span>`;
            }
            // Process substep identifiers
            else if (text.includes('Truck-Charging Type Matching') || text.includes('STEP 1:')) {
                styledText = `<span class="text-info">${text}</span>`;
            }
            else if (text.includes('Charging Hub Configuration') || text.includes('STEP 2:')) {
                styledText = `<span class="text-info">${text}</span>`;
            }
            else if (text.includes('Demand Optimization') || text.includes('STEP 3:')) {
                styledText = `<span class="text-info">${text}</span>`;
            }
            // Process completion messages
            else if (text.includes('completed successfully')) {
                styledText = `<span class="text-success fw-bold">${text}</span>`;
            }
            // Process error messages
            else if (text.includes('ERROR') || text.includes('failed') || text.includes('Error')) {
                styledText = `<span class="text-danger">${text}</span>`;
            }
            // Process timing information
            else if (text.includes('seconds') && (text.includes('completed') || text.includes('runtime'))) {
                styledText = `<span class="text-warning">${text}</span>`;
            }
            // Process optimization progress indicators
            else if (text.includes('Optimizing') || text.includes('Analyzing') || text.includes('Processing')) {
                styledText = `<span class="text-primary">${text}</span>`;
            }
            
            preElem.innerHTML += `\n${styledText}`;
        } else {
            terminalOutput.innerHTML = `<pre class="terminal-text">${text}</pre>`;
        }
        
        if (autoscroll) {
            scrollToBottom();
        }
    }
    
    function clearTerminal() {
        terminalOutput.innerHTML = '<pre class="terminal-text">--- Terminal Cleared ---</pre>';
    }
    
    function scrollToBottom() {
        terminalOutput.scrollTop = terminalOutput.scrollHeight;
    }
    
    function resetPhases() {
        // Reset all phases to pending
        Object.values(phaseElements).forEach(phase => {
            phase.status.className = 'badge bg-secondary';
            phase.status.textContent = 'Pending';
            phase.progress.style.width = '0%';
            phase.progress.setAttribute('aria-valuenow', '0');
            phase.progressText.textContent = '0%';
            
            // Reset substeps if they exist
            if (phase.substeps) {
                Object.values(phase.substeps).forEach(substep => {
                    substep.indicator.innerHTML = '<i class="far fa-circle text-secondary"></i>';
                });
            }
        });
    }
    
    function updatePhaseStatus(processId, status, progressPercent = null) {
        const phase = phaseElements[processId];
        if (!phase) {
            // For main process, update the phase based on current progress
            if (processId === 'main') {
                if (status === 'running' && progressPercent === null) {
                    // When main starts, set first phase to running
                    updatePhaseStatus('traffic', 'running', 5);
                }
            }
            return;
        }
        
        // Update status badge
        switch (status) {
            case 'running':
                phase.status.className = 'badge bg-info';
                phase.status.textContent = 'Running';
                break;
            case 'completed':
                phase.status.className = 'badge bg-success';
                phase.status.textContent = 'Completed';
                break;
            case 'failed':
                phase.status.className = 'badge bg-danger';
                phase.status.textContent = 'Failed';
                break;
            case 'stopped':
                phase.status.className = 'badge bg-warning';
                phase.status.textContent = 'Stopped';
                break;
            case 'skipped':
                phase.status.className = 'badge bg-secondary';
                phase.status.textContent = 'Skipped';
                break;
            default:
                phase.status.className = 'badge bg-secondary';
                phase.status.textContent = 'Pending';
        }
        
        // Update progress if provided
        if (progressPercent !== null) {
            phase.progress.style.width = progressPercent + '%';
            phase.progress.setAttribute('aria-valuenow', progressPercent);
            phase.progressText.textContent = progressPercent + '%';
        }
    }
    
    function parseProgressFromOutput(processId, output) {
        // Look for standardized phase markers
        const phaseStartMatch = output.match(/PHASE (\d+): (.*) STARTED/i);
        const phaseCompleteMatch = output.match(/PHASE (\d+): (.*) COMPLETED/i);
        const phaseProgressMatch = output.match(/PHASE (\d+): (.*) (\d+)% COMPLETE/i);
        const phaseSkippedMatch = output.match(/PHASE (\d+): (.*) SKIPPED/i);
        const phaseFailedMatch = output.match(/PHASE (\d+): (.*) FAILED/i);
        
        // Look for standardized step markers
        const stepStartMatch = output.match(/PHASE (\d+) - STEP (\d+): (.*) STARTED/i);
        const stepCompleteMatch = output.match(/PHASE (\d+) - STEP (\d+): (.*) COMPLETED/i);
        const stepProgressMatch = output.match(/PHASE (\d+) - STEP (\d+): (.*) (\d+)% COMPLETE/i);
        const stepSkippedMatch = output.match(/PHASE (\d+) - STEP (\d+): (.*) SKIPPED/i);
        const stepFailedMatch = output.match(/PHASE (\d+) - STEP (\d+): (.*) FAILED/i);
        
        // Handle phase events
        if (phaseStartMatch) {
            const phaseNum = phaseStartMatch[1];
            const phaseName = phaseStartMatch[2];
            updatePhaseStatus(getPhaseId(phaseNum), 'running', 10);
        } 
        else if (phaseProgressMatch) {
            const phaseNum = phaseProgressMatch[1];
            const phaseName = phaseProgressMatch[2];
            const progress = parseInt(phaseProgressMatch[3], 10);
            updatePhaseStatus(getPhaseId(phaseNum), 'running', progress);
        }
        else if (phaseCompleteMatch) {
            const phaseNum = phaseCompleteMatch[1];
            const phaseName = phaseCompleteMatch[2];
            updatePhaseStatus(getPhaseId(phaseNum), 'completed', 100);
        }
        else if (phaseSkippedMatch) {
            const phaseNum = phaseSkippedMatch[1];
            const phaseName = phaseSkippedMatch[2];
            updatePhaseStatus(getPhaseId(phaseNum), 'skipped', 0);
        }
        else if (phaseFailedMatch) {
            const phaseNum = phaseFailedMatch[1];
            const phaseName = phaseFailedMatch[2];
            updatePhaseStatus(getPhaseId(phaseNum), 'failed', null);
        }
        
        // Handle step events
        if (stepStartMatch) {
            const phaseNum = stepStartMatch[1];
            const stepNum = stepStartMatch[2];
            const stepName = stepStartMatch[3];
            
            // Currently only phase 2 (charging_hub) has substeps
            if (phaseNum === '2') {
                updateSubstepStatus(stepNum, 'running');
            }
        }
        else if (stepProgressMatch) {
            const phaseNum = stepProgressMatch[1];
            const stepNum = stepProgressMatch[2];
            const stepName = stepProgressMatch[3];
            const progress = parseInt(stepProgressMatch[4], 10);
            
            // Currently only phase 2 (charging_hub) has substeps
            if (phaseNum === '2') {
                updateSubstepStatus(stepNum, 'running', progress);
                
                // Also update the main phase progress based on substep progress
                // For example, each substep contributes ~33% to the overall phase progress
                const stepContribution = 33; // Each step is roughly 33% of the total
                const phaseProgress = Math.min(
                    Math.floor((parseInt(stepNum) - 1) * stepContribution + (progress * stepContribution / 100)),
                    99  // Cap at 99% until phase is explicitly completed
                );
                updatePhaseStatus('charging_hub', 'running', phaseProgress);
            }
        }
        else if (stepCompleteMatch) {
            const phaseNum = stepCompleteMatch[1];
            const stepNum = stepCompleteMatch[2];
            const stepName = stepCompleteMatch[3];
            
            // Currently only phase 2 (charging_hub) has substeps
            if (phaseNum === '2') {
                updateSubstepStatus(stepNum, 'completed');
                
                // If this is the last step, nearly complete the phase (but not 100% yet)
                if (stepNum === '3') {
                    updatePhaseStatus('charging_hub', 'running', 99);
                } else {
                    // Otherwise update based on which step completed
                    const progress = parseInt(stepNum) * 33; // Each step is roughly 33% of the total
                    updatePhaseStatus('charging_hub', 'running', progress);
                }
            }
        }
        else if (stepSkippedMatch) {
            const phaseNum = stepSkippedMatch[1];
            const stepNum = stepSkippedMatch[2];
            const stepName = stepSkippedMatch[3];
            
            // Currently only phase 2 (charging_hub) has substeps
            if (phaseNum === '2') {
                updateSubstepStatus(stepNum, 'skipped');
            }
        }
        else if (stepFailedMatch) {
            const phaseNum = stepFailedMatch[1];
            const stepNum = stepFailedMatch[2];
            const stepName = stepFailedMatch[3];
            
            // Currently only phase 2 (charging_hub) has substeps
            if (phaseNum === '2') {
                updateSubstepStatus(stepNum, 'failed');
            }
        }
        
        // Look for generic progress indicators based on Python optimization libraries
        if (output.includes('Optimizing') || output.includes('Iteration')) {
            // Determine which phase is active and increment its progress
            if (processId === 'traffic') {
                incrementPhaseProgress('traffic', 5);
            } else if (processId === 'charging_hub') {
                incrementPhaseProgress('charging_hub', 2);
            } else if (processId === 'grid_opt') {
                incrementPhaseProgress('grid_opt', 5);
            } else if (processId === 'main') {
                // For main process, need to determine which phase is active
                const phaseElements = {
                    'traffic': document.getElementById('phase1-status'),
                    'charging_hub': document.getElementById('phase2-status'),
                    'grid_opt': document.getElementById('phase3-status')
                };
                
                for (const [phaseId, element] of Object.entries(phaseElements)) {
                    if (element.textContent === 'Running') {
                        incrementPhaseProgress(phaseId, 2);
                        break;
                    }
                }
            }
        }
    }

    function getPhaseId(phaseNum) {
        switch(phaseNum) {
            case '1': return 'traffic';
            case '2': return 'charging_hub';
            case '3': return 'grid_opt';
            default: return null;
        }
    }
    
    function incrementPhaseProgress(phaseId, incrementAmount) {
        const phase = phaseElements[phaseId];
        if (!phase) return;
        
        const currentProgress = parseInt(phase.progress.getAttribute('aria-valuenow') || '0');
        if (currentProgress < 90) {  // Cap at 90% until we get completion confirmation
            const newProgress = Math.min(currentProgress + incrementAmount, 90);
            phase.progress.style.width = newProgress + '%';
            phase.progress.setAttribute('aria-valuenow', newProgress);
            phase.progressText.textContent = newProgress + '%';
        }
    }
    
    function runOptimization(processId) {
        // Reset the terminal and phases
        clearTerminal();
        resetPhases();
        
        // Prepare request body with execution flags
        const config = getExecutionConfig();
        
        // Determine the API endpoint based on processId
        let endpoint = `/api/run/${processId}`;
        if (processId === 'main') {
            endpoint = '/api/run/main';
        } else if (processId === 'traffic') {
            endpoint = '/api/run/traffic_calculation';
        } else if (processId === 'charging_hub') {
            endpoint = '/api/run/charging_hub_setup';
        } else if (processId === 'grid_opt') {
            endpoint = '/api/run/grid_optimization';
        }
        
        appendToTerminal(`Starting ${processId} process...`);
        
        // Send request to start the process
        fetch(endpoint, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ config })
        })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    appendToTerminal(`Process ${processId} started successfully.`);
                    currentProcess = processId;
                    
                    // Update UI based on which process is running
                    if (processId === 'main') {
                        updatePhaseStatus('traffic', 'running', 5);
                    } else {
                        updatePhaseStatus(processId, 'running', 5);
                    }
                    
                    updateUI();
                } else {
                    appendToTerminal(`Error starting process: ${data.error}`);
                }
            })
            .catch(error => {
                console.error('Error starting process:', error);
                appendToTerminal(`Error starting process: ${error.message}`);
            });
    }
    
    function getExecutionConfig() {
        const config = {
            EXECUTION_FLAGS: {}
        };
        
        // Map checkbox IDs to config keys
        const flagMapping = {
            'run-traffic-calculation': 'RUN_TRAFFIC_CALCULATION',
            'run-charging-hub-setup': 'RUN_CHARGING_HUB_SETUP',
            'run-grid-optimization': 'RUN_GRID_OPTIMIZATION',
            'run-truck-matching': 'RUN_TRUCK_MATCHING',
            'run-hub-configuration': 'RUN_HUB_CONFIGURATION',
            'run-demand-optimization': 'RUN_DEMAND_OPTIMIZATION',
            'use-distance-calculation': 'USE_DISTANCE_CALCULATION',
            'create-maps': 'CREATE_DISTANCE_MAPS',
            'include-battery': 'INCLUDE_BATTERY',
            'use-manual-charger-count': 'USE_MANUAL_CHARGER_COUNT'
        };
        
        // Set flags based on checkbox states
        Object.entries(flagMapping).forEach(([elementId, configKey]) => {
            const checkbox = document.getElementById(elementId);
            if (checkbox) {
                config.EXECUTION_FLAGS[configKey] = checkbox.checked;
            }
        });
        
        return config;
    }
    
    function saveExecutionConfig() {
        const config = {
            EXECUTION_FLAGS: getExecutionConfig().EXECUTION_FLAGS
        };
        
        fetch('/api/config/save', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(config)
        })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    appendToTerminal('Execution configuration saved successfully.');
                    window.showNotification('Execution configuration saved successfully.', 'success');
                } else {
                    appendToTerminal(`Error saving configuration: ${data.error}`);
                    window.showNotification('Error saving configuration.', 'danger');
                }
            })
            .catch(error => {
                console.error('Error saving configuration:', error);
                appendToTerminal(`Error saving configuration: ${error.message}`);
                window.showNotification('Error saving configuration.', 'danger');
            });
    }
    
    // Initialize by fetching current config
    fetch('/api/config')
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                // Update checkboxes based on current configuration
                const flags = data.config.EXECUTION_FLAGS;
                
                for (const [key, checkbox] of Object.entries(configSwitches)) {
                    if (checkbox) {
                        const configKey = key.replace(/-/g, '_').toUpperCase();
                        checkbox.checked = flags[configKey] !== undefined ? flags[configKey] : true;
                    }
                }
            }
        })
        .catch(error => {
            console.error('Error fetching configuration:', error);
        });
    
    function updateSubstepStatus(stepNum, status, progress = null) {
        // Map step number to substep name
        let substepKey;
        switch(stepNum) {
            case '1': substepKey = 'truck_matching'; break;
            case '2': substepKey = 'hub_configuration'; break;
            case '3': substepKey = 'demand_optimization'; break;
            default: return; // Unknown step
        }
        
        const substep = phaseElements['charging_hub'].substeps[substepKey];
        if (!substep) return;
        
        // Update indicator icon and styling based on status
        switch(status) {
            case 'running':
                substep.indicator.innerHTML = '<i class="fas fa-spinner fa-spin text-info"></i>';
                substep.text.className = 'substep-text text-info';
                // Add progress if provided
                if (progress !== null) {
                    substep.text.textContent = `${substep.text.textContent.split(' [')[0]} [${progress}%]`;
                }
                break;
            case 'completed':
                substep.indicator.innerHTML = '<i class="fas fa-check-circle text-success"></i>';
                substep.text.className = 'substep-text text-success';
                // Reset any progress display
                substep.text.textContent = substep.text.textContent.split(' [')[0];
                break;
            case 'skipped':
                substep.indicator.innerHTML = '<i class="fas fa-forward text-warning"></i>';
                substep.text.className = 'substep-text text-warning';
                substep.text.textContent = `${substep.text.textContent.split(' [')[0]} (Skipped)`;
                break;
            case 'failed':
                substep.indicator.innerHTML = '<i class="fas fa-times-circle text-danger"></i>';
                substep.text.className = 'substep-text text-danger';
                substep.text.textContent = `${substep.text.textContent.split(' [')[0]} (Failed)`;
                break;
            default:
                substep.indicator.innerHTML = '<i class="far fa-circle text-secondary"></i>';
                substep.text.className = 'substep-text';
                // Reset any progress display
                substep.text.textContent = substep.text.textContent.split(' [')[0];
        }
    }
});
