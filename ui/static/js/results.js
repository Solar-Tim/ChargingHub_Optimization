$(document).ready(function() {
    console.log('Results page script loaded');
    const apiBase = window.location.origin;
    let currentResult = null;
    let resultData = null;
    let charts = {};
    let allResultsData = {};
    let allResultItems = []; // Store all result items for filtering
    const ITEMS_PER_PAGE = 10; // Number of items to show per page
    let currentPage = 1; // Current page of results
    let filteredItems = []; // Items filtered by search

    // Refresh results list function
    function refreshResultsList() {
        console.log('Refreshing results list...');
        $.ajax({            url: `${apiBase}/api/results/list`, method: 'GET',
            success: function(data) {
                const resultList = $('#result-list').empty();
                $('#compare-select').empty();
                allResultItems = []; // Clear stored items
                
                if (data.results && data.results.length) {
                    $('#no-results-message').hide();
                    data.results.sort((a, b) => b.date - a.date);data.results.forEach(result => {
                        const dateStr = new Date(result.date * 1000).toISOString().split('T')[0];
                        const item = $(
                            `<a href="#" class="list-group-item list-group-item-action" 
                               data-result-id="${result.id}" 
                               data-result-name="${result.name}">
                                <div class="d-flex justify-content-between">
                                    <div class="result-info">
                                        <strong>${result.id}: ${result.type}</strong><br>
                                        <small class="text-muted text-truncate">${result.name}</small>
                                    </div>
                                    <small class="text-muted result-date">${dateStr}</small>
                                </div>
                            </a>`
                        );
                        resultList.append(item);
                        
                        // Store item with searchable text
                        allResultItems.push({
                            element: item,
                            searchText: `${result.id} ${result.type} ${result.name} ${dateStr}`.toLowerCase()
                        });
                        
                        $('#compare-select').append($('<option>', { value: result.name, text: `${result.id}: ${result.type} (${dateStr})` }));
                    });
                                  // Initialize filtered items with all items
                    filteredItems = [...allResultItems];
                    
                    // Reset to page 1
                    currentPage = 1;
                    
                    // Apply pagination
                    displayResultsPage(1);
                    
                    // Apply any existing search filter (if there is a search term)
                    const searchTerm = $('#search-results').val().trim();
                    if (searchTerm) {
                        applySearchFilter();
                    }
                    
                    const hash = window.location.hash.substring(1);
                    if (hash) { $(`.list-group-item[data-result-name="${hash}"]`).click(); }
                } else {
                    resultList.html($('#no-results-message').parent());
                }
            },
            error: function(xhr, status, error) {
                $('#result-list').html(
                    `<div class="text-center text-danger">
                        <i class="fas fa-exclamation-triangle fa-2x mb-2"></i><br>
                        Error loading results: ${error}<br><small>${xhr.responseText}</small>
                    </div>`
                );
            }
        });
    }    // Function to display a specific page of results
    function displayResultsPage(page) {
        if (filteredItems.length === 0) return;
        
        // Calculate start and end indices
        const startIndex = (page - 1) * ITEMS_PER_PAGE;
        const endIndex = Math.min(startIndex + ITEMS_PER_PAGE, filteredItems.length);
        
        // Hide all items first
        allResultItems.forEach(item => {
            item.element.addClass('d-none');
        });
        
        // Show only items for the current page
        for (let i = startIndex; i < endIndex; i++) {
            filteredItems[i].element.removeClass('d-none');
        }
        
        // Update pagination controls
        updatePaginationControls();
        
        // Update scroll indicator
        updateScrollIndicator();
        
        // Save current page
        currentPage = page;
    }
    
    // Function to update pagination controls
    function updatePaginationControls() {
        // Remove existing pagination
        $('#pagination-controls').remove();
        
        // If no items or all items fit on one page, don't show pagination
        if (filteredItems.length <= ITEMS_PER_PAGE) return;
        
        // Calculate total pages
        const totalPages = Math.ceil(filteredItems.length / ITEMS_PER_PAGE);
        
        // Create pagination controls
        let paginationHTML = `
            <div id="pagination-controls" class="d-flex justify-content-between align-items-center mt-2 mb-2">
                <button class="btn btn-sm btn-outline-secondary" id="prev-page" ${currentPage === 1 ? 'disabled' : ''}>
                    <i class="fas fa-chevron-left"></i>
                </button>
                <span class="text-muted">Page ${currentPage} of ${totalPages}</span>
                <button class="btn btn-sm btn-outline-secondary" id="next-page" ${currentPage === totalPages ? 'disabled' : ''}>
                    <i class="fas fa-chevron-right"></i>
                </button>
            </div>
        `;
        
        // Add pagination after results container
        $('.results-container').after(paginationHTML);
        
        // Add event handlers
        $('#prev-page').click(() => {
            if (currentPage > 1) {
                displayResultsPage(currentPage - 1);
            }
        });
        
        $('#next-page').click(() => {
            if (currentPage < totalPages) {
                displayResultsPage(currentPage + 1);
            }
        });
    }
    
    // Function to check if the results container needs a scroll indicator
    function updateScrollIndicator() {
        const container = $('.results-container');
        if (container.length) {
            // Check if content is taller than container
            const isScrollable = container[0].scrollHeight > container[0].clientHeight;
            
            if (isScrollable) {
                container.addClass('can-scroll');
            } else {
                container.removeClass('can-scroll');
            }
        }
    }
      // Search filter function
    function applySearchFilter() {
        const query = $('#search-results').val().toLowerCase().trim();
        
        // Reset pagination to first page
        currentPage = 1;
        
        // Clear the no-results message
        $('#result-list').find('#no-search-results').remove();
        
        if (!query) {
            // If no search query, include all items
            filteredItems = [...allResultItems];
        } else {
            // Filter items based on search query
            filteredItems = allResultItems.filter(item => 
                item.searchText.includes(query)
            );
            
            // Display message if no results match search
            if (filteredItems.length === 0) {
                $('#result-list').append(
                    `<div id="no-search-results" class="text-center py-3 text-muted">
                        <i class="fas fa-search fa-lg mb-2"></i><br>
                        No results matching "${query}"
                    </div>`
                );
            }
        }
        
        // Display first page of filtered items
        displayResultsPage(1);
    }

    // Event bindings
    $('#refresh-results').click(refreshResultsList);
      // Search input event handler
    $('#search-results').on('input', applySearchFilter);
      // Handle keyboard events in search input
    $('#search-results').on('keyup', function(e) {
        // Clear search on Escape key
        if (e.key === 'Escape') {
            $(this).val('');
            applySearchFilter();
        }
    });
    
    // Add keyboard navigation for pagination (left/right arrow keys)
    $(document).keydown(function(e) {
        // Only when focus is not in search input
        if ($('#search-results').is(':focus')) return;
        
        // Left arrow key - previous page
        if (e.key === 'ArrowLeft') {
            $('#prev-page:not([disabled])').click();
        }
        // Right arrow key - next page
        else if (e.key === 'ArrowRight') {
            $('#next-page:not([disabled])').click();
        }
    });
    
    // Clear search button event handler
    $('#clear-search').click(function() {
        $('#search-results').val('').focus();
        applySearchFilter();
    });
    
    $('#result-list').on('click', '.list-group-item', function(e) {
        e.preventDefault();
        $('.list-group-item').removeClass('active'); $(this).addClass('active');
        currentResult = $(this).data('result-name');
        $('#download-json-btn, #download-csv-btn, #compare-btn').prop('disabled', false);
        $('#result-title').text(`Result: ${currentResult}`);
        loadResultData(currentResult);
        window.location.hash = currentResult;
    });
    $('#tab-overview, #tab-charts').click(function() {
        $('.btn-group .btn').removeClass('active'); $(this).addClass('active');
        $('.result-tab-content').addClass('d-none');
        const tab = $(this).attr('id').replace('tab-', '');
        $(`#${tab}-content`).removeClass('d-none');
        if (tab === 'charts' && resultData) {
            // Update charts when switching to charts tab
            updateCharts(resultData);
        }
    });
    $('#download-json-btn').click(() => currentResult && (window.location.href = `${apiBase}/api/results/download/${currentResult}?format=json`));
    $('#run-optimization-btn').click(() => window.location.href = '/configuration');
    $('#compare-btn').click(() => $('#compareModal').modal('show'));
    $('#do-compare').click(() => {
        const sel = $('#compare-select').val();
        if (!sel || sel.length !== 2) return alert('Please select exactly 2 result files to compare');
        sel.forEach(name => { if (!allResultsData[name]) {
            $.ajax({ url: `${apiBase}/api/results/${name}`, async: false, success: data => { allResultsData[name] = data; } });
        }});
        compareResults(sel[0], sel[1]);
    });
    $('#test-loading-btn').click(() => $('.list-group-item').first().click());
    
    // Chart filter bindings for Energy Flows
    $('#show-demand, #show-grid-energy, #show-battery-discharge, #show-battery-charge, #show-grid-limit').change(function() {
        if (resultData) {
            updateEnergyFlowsChart(resultData);
        }
    });
    
    // View filters for Energy Flows (All Days, Weekday, Weekend)
    $('#view-all-days, #view-weekday, #view-weekend').click(function() {
        $('#view-all-days, #view-weekday, #view-weekend').removeClass('active');
        $(this).addClass('active');
        if (resultData) {
            updateEnergyFlowsChart(resultData);
        }
    });

    // Load and display result data
    function loadResultData(name) {
        // Reset UI and show loading
        $('#placeholder-message').hide();
        $('.result-tab-content').addClass('d-none');
        $('#loading-spinner').removeClass('d-none');
        // Fetch result data
        $.ajax({
            url: `${apiBase}/api/results/${name}`,
            method: 'GET',
            success: function(data) {
                resultData = data;
                populateOverview(data);
                $('#loading-spinner').addClass('d-none');
                $('#tab-overview').click();
                // Initialize charts in background
                setTimeout(() => {
                    initCharts(data);
                }, 100);
            },
            error: function() {
                $('#loading-spinner').addClass('d-none');
                alert('Error loading result data');
            }
        });
    }

    // ─── Helpers ───────────────────────────────────────────────────────────
    function formatTimestamp(ts) {
        // handle both numeric epoch or ISO-string
        let d = (typeof ts === 'number') ? new Date(ts * 1000) : new Date(ts);
        let date = d.toLocaleDateString();
        let time = d.toLocaleTimeString();
        return `${date} ${time}`;
    }
    function formatNumber(num) {
        // round and add space as thousands separator
        return Math.round(num)
                  .toString()
                  .replace(/\B(?=(\d{3})+(?!\d))/g, ' ');
    }

    function formatDecimal(num, places = 2) {
        if (num === undefined || num === null) {
            return '-';
        }
        return Number(num).toFixed(places).replace(/\B(?=(\d{3})+(?!\d))/g, ' ');
    }

    function parseTimestamp(ts) {
        if (typeof ts === 'string' && /^\d{8}_\d{6}$/.test(ts)) {
            const [d, t] = ts.split('_');
            const year = d.slice(0,4), month = d.slice(4,6), day = d.slice(6,8);
            const hh = t.slice(0,2), mm = t.slice(2,4), ss = t.slice(4,6);
            return {
                full:  `${year}-${month}-${day} ${hh}:${mm}:${ss}`,
                date:  `${year}-${month}-${day}`,
                time:  `${hh}:${mm}:${ss}`
            };
        }
        // fallback to ISO/epoch
        const dt = (typeof ts === 'number') ? new Date(ts*1000) : new Date(ts);
        const date = dt.toLocaleDateString();
        const time = dt.toLocaleTimeString();
        return { full:`${date} ${time}`, date, time };
    }

    function populateOverview(data) {
        const r = data.results;
        const ts = parseTimestamp(data.timestamp);

        // ─── Config table ────────────────────────────────────────────────────
        const configRows = [
            ['Scenario',  data.scenario],
            ['Strategy',  r.charging_strategy],
            ['Date',      ts.date],
            ['Time',      ts.time],
            ['Forecast Year', r.forecast_year]
        ];
        $('#config-table').empty();
        configRows.forEach(([k, v]) =>
            $('#config-table').append(`<tr><th>${k}</th><td>${v}</td></tr>`)
        );

        // ─── Summary table ───────────────────────────────────────────────────
        const summaryRows = [
            ['Total Cost',            formatNumber(r.total_cost)],
            ['Connection Cost',       formatNumber(r.connection_cost)],
            ['Capacity Cost',         formatNumber(r.capacity_cost)],
            ['Battery Cost',          formatNumber(r.battery_cost)],
            ['Transformer Cost',      formatNumber(r.transformer_cost)],
            ['Internal Cable Cost',   formatNumber(r.internal_cable_cost)],
            ['Charger Cost',          formatNumber(r.charger_cost)]
        ];
        $('#summary-table').empty();
        summaryRows.forEach(([k, v]) =>
            $('#summary-table').append(
                `<tr>
                    <th>${k}</th>
                    <td class="text-end">${v} €</td>
                </tr>`
            )
        );

        // Cost Breakdown Table and Chart
        const costData = {
            labels: ['Connection', 'Capacity', 'Battery', 'Transformer', 'Internal Cable', 'Chargers'],
            values: [
                r.connection_cost,
                r.capacity_cost,
                r.battery_cost,
                r.transformer_cost,
                r.internal_cable_cost,
                r.charger_cost
            ]
        };
        
        $('#cost-breakdown-table').empty();
        costData.labels.forEach((label, i) => {
            const percent = (costData.values[i] / r.total_cost * 100).toFixed(1);
            $('#cost-breakdown-table').append(
                `<tr>
                    <td>${label}</td>
                    <td class="text-end">${formatNumber(costData.values[i])} €</td>
                    <td class="text-end">${percent}%</td>
                </tr>`
            );
        });
        $('#cost-breakdown-table').append(
            `<tr class="table-primary">
                <th>Total</th>
                <th class="text-end">${formatNumber(r.total_cost)} €</th>
                <th class="text-end">100%</th>
            </tr>`
        );

        // Key metrics
        $('#metric-peak-power').text(formatDecimal(r.max_grid_load, 2));
        const totalEnergy = r.grid_energy?.reduce((sum, val) => sum + val, 0) || 0;
        $('#metric-total-energy').text(formatDecimal(totalEnergy, 2));
        $('#metric-total-cost').text(formatDecimal(r.total_cost, 2));
        
        // Energy metrics
        $('#metric-weekly-energy').text(formatDecimal(r.energy_throughput_weekly_kwh) + ' kWh');
        $('#metric-annual-energy').text(formatDecimal(r.energy_throughput_annual_gwh) + ' GWh');
        
        // Battery metrics
        if (r.battery_capacity > 0) {
            $('#battery-metrics-row').removeClass('d-none');
            $('#metric-battery-capacity').text(formatDecimal(r.battery_capacity, 2));
            $('#metric-battery-peak-power').text(formatDecimal(r.battery_peak_power || (Math.max(...r.grid_energy) - r.max_grid_load), 2));
            $('#metric-battery-savings').text(formatDecimal(r.capacity_cost - r.battery_cost, 2));
            $('#metric-battery-cycles-weekly').text(formatDecimal(r.battery_cycles_weekly || 0, 2));
            $('#metric-battery-cycles-annual').text(formatDecimal(r.battery_cycles_annual || 0, 2));
            $('#battery-state-container').show();
        } else {
            $('#battery-metrics-row').addClass('d-none');
            $('#battery-state-container').hide();
            $('#metric-battery-cycles-weekly').text('-');
            $('#metric-battery-cycles-annual').text('-');
        }

        // Connection details
        $('#metric-transmission-capacity').text(formatDecimal(r.transmission_capacity || 0) + ' kW');
        $('#metric-distribution-capacity').text(formatDecimal(r.distribution_capacity || 0) + ' kW');
        $('#metric-use-distribution').text(r.use_distribution != null ? r.use_distribution.toString() : '-');
        $('#metric-use-transmission').text(r.use_transmission != null ? r.use_transmission.toString() : '-');

        // Infrastructure tables
        $('#infrastructure-distance-table').empty().append(
            `<tr><th>Transmission Distance</th><td>${formatDecimal(r.transmission_distance, 2)} m</td></tr>
             <tr><th>Distribution Distance</th><td>${formatDecimal(r.distribution_distance, 2)} m</td></tr>
             <tr><th>Powerline Distance</th><td>${formatDecimal(r.powerline_distance || 0, 2)} m</td></tr>`
        );
        $('#infrastructure-transformer-table').empty().append(
            `<tr><th>Transformer Capacity</th><td>${r.transformer_capacity} kW</td></tr>
             <tr><th>Description</th><td>${r.transformer_description || '-'}</td></tr>`
        );

        // Charger summary
        $('#charger-summary-table').empty();
        const chargerTypes = [
            ['MCS_count', 'MCS'], 
            ['HPC_count', 'HPC'], 
            ['NCS_count', 'NCS']
        ];
        chargerTypes.forEach(([key, label]) => {
            if (r[key] !== undefined) {
                const sessions = r.weekly_charging_sessions?.[label] || '-';
                const utilization = r.charger_utilization?.[label] 
                    ? `${(r.charger_utilization[label] * 100).toFixed(1)}%` 
                    : '-';
                $('#charger-summary-table').append(
                    `<tr>
                        <td>${label}</td>
                        <td>${r[key]}</td>
                        <td>${sessions}</td>
                        <td>${utilization}</td>
                    </tr>`
                );
            }
        });
        
        // If no charger data, add message
        if ($('#charger-summary-table tr').length === 0) {
            $('#charger-summary-table').append(
                `<tr><td colspan="4" class="text-center">No charger data available</td></tr>`
            );
        }
    }
    
    // Initialize all charts
    function initCharts(data) {
        // Create cost breakdown chart
        createCostBreakdownChart(data);
        
        // Initialize the energy flows chart
        updateEnergyFlowsChart(data);
        
        // Create battery state chart if battery is present
        if (data.results.battery_capacity > 0) {
            createBatteryStateChart(data);
        }
        
        // Create sessions chart if data is available
        if (data.results.daily_charging_sessions) {
            createSessionsChart(data);
        }
        
        // Create utilization chart if data is available
        if (data.results.charger_utilization) {
            createUtilizationChart(data);
        }
    }
    
    // Update charts when switching to charts tab or changing filters
    function updateCharts(data) {
        updateEnergyFlowsChart(data);
        if (charts.batteryStateChart) charts.batteryStateChart.update();
        if (charts.costsChart) charts.costsChart.update();
        if (charts.sessionsChart) charts.sessionsChart.update();
        if (charts.utilizationChart) charts.utilizationChart.update();
    }
    
    // Create cost breakdown chart
    function createCostBreakdownChart(data) {
        const r = data.results;
        
        // Prepare cost data
        const costLabels = ['Connection', 'Capacity', 'Battery', 'Transformer', 'Internal Cable', 'Chargers'];
        const costValues = [
            r.connection_cost,
            r.capacity_cost, 
            r.battery_cost,
            r.transformer_cost,
            r.internal_cable_cost,
            r.charger_cost
        ];
        
        // Create chart
        const ctx = document.getElementById('costs-chart').getContext('2d');
        if (charts.costsChart) charts.costsChart.destroy();
        
        charts.costsChart = new Chart(ctx, {
            type: 'doughnut',
            data: {
                labels: costLabels,
                datasets: [{
                    data: costValues,
                    backgroundColor: [
                        '#4e73df', // Connection - blue
                        '#1cc88a', // Capacity - green
                        '#36b9cc', // Battery - cyan
                        '#f6c23e', // Transformer - yellow
                        '#e74a3b', // Internal Cable - red
                        '#6f42c1'  // Chargers - purple
                    ]
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        position: 'right',
                        labels: {
                            padding: 20,
                            boxWidth: 12
                        }
                    },
                    tooltip: {
                        callbacks: {
                            label: function(context) {
                                const value = context.raw;
                                const total = context.dataset.data.reduce((a, b) => a + b, 0);
                                const percentage = ((value / total) * 100).toFixed(1);
                                const formattedValue = formatNumber(value);
                                return `${context.label}: ${formattedValue} € (${percentage}%)`;
                            }
                        }
                    }
                }
            }
        });
        
        // Create overview cost chart (smaller version)
        const overviewCtx = document.getElementById('overview-costs-chart').getContext('2d');
        if (charts.overviewCostsChart) charts.overviewCostsChart.destroy();
        
        charts.overviewCostsChart = new Chart(overviewCtx, {
            type: 'pie',
            data: {
                labels: costLabels,
                datasets: [{
                    data: costValues,
                    backgroundColor: [
                        '#4e73df', '#1cc88a', '#36b9cc', '#f6c23e', '#e74a3b', '#6f42c1'
                    ]
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        display: false
                    },
                    tooltip: {
                        callbacks: {
                            label: function(context) {
                                const value = context.raw;
                                const total = context.dataset.data.reduce((a, b) => a + b, 0);
                                const percentage = ((value / total) * 100).toFixed(1);
                                const formattedValue = formatNumber(value);
                                return `${context.label}: ${formattedValue} € (${percentage}%)`;
                            }
                        }
                    }
                }
            }
        });
    }
    
    // Update energy flows chart based on filters
    function updateEnergyFlowsChart(data) {
        const r = data.results;
        const timePoints = data.time_periods || [];
        
        if (!timePoints.length) {
            console.error('No time points in data');
            return;
        }
        
        // Determine time range based on selected view
        let startIndex = 0;
        let endIndex = timePoints.length - 1;
        const viewMode = $('#view-all-days.active').length ? 'all' :
                        $('#view-weekday.active').length ? 'weekday' : 'weekend';
        
        // For demonstration - in a real implementation, you would filter based on day of the week
        if (viewMode === 'weekday') {
            // Assuming first 5 days are weekdays (simple simulation)
            endIndex = Math.floor(timePoints.length * (5/7));
        } else if (viewMode === 'weekend') {
            // Assuming last 2 days are weekend
            startIndex = Math.floor(timePoints.length * (5/7));
        }
        
        // Filter data based on time range
        const filteredTimePoints = timePoints.slice(startIndex, endIndex + 1);
        const filteredDemand = data.load_profile ? data.load_profile.slice(startIndex, endIndex + 1) : [];
        const filteredGridEnergy = r.grid_energy ? r.grid_energy.slice(startIndex, endIndex + 1) : [];
        const filteredBatteryCharge = r.battery_charge ? r.battery_charge.slice(startIndex, endIndex + 1) : [];
        const filteredBatteryDischarge = r.battery_discharge ? r.battery_discharge.slice(startIndex, endIndex + 1) : [];
        
        // Convert time points to more readable format (Day X, Hour Y)
        const labels = filteredTimePoints.map(tp => {
            const minutesTotal = parseInt(tp);
            const day = Math.floor(minutesTotal / (24 * 60)) + 1;
            const hour = Math.floor((minutesTotal % (24 * 60)) / 60);
            return `Day ${day}, ${hour}:00`;
        });
        
        // Prepare datasets based on checkboxes
        const datasets = [];
        
        // Demand dataset
        if ($('#show-demand').prop('checked')) {
            datasets.push({
                label: 'Demand',
                data: filteredDemand,
                borderColor: 'rgb(0, 0, 255)',
                backgroundColor: 'rgba(0, 0, 255, 0.1)',
                fill: false,
                borderWidth: 2,
                pointRadius: 0, // Hide points for cleaner display with many data points
                pointHoverRadius: 4 // Show points on hover
            });
        }
        
        // Grid Energy dataset
        if ($('#show-grid-energy').prop('checked')) {
            datasets.push({
                label: 'Grid Energy',
                data: filteredGridEnergy,
                borderColor: 'rgb(0, 128, 0)',
                backgroundColor: 'rgba(0, 128, 0, 0.1)',
                fill: false,
                borderWidth: 2,
                pointRadius: 0,
                pointHoverRadius: 4
            });
        }
        
        // Battery Discharge dataset
        if ($('#show-battery-discharge').prop('checked') && r.battery_discharge) {
            datasets.push({
                label: 'Battery Discharge',
                data: filteredBatteryDischarge,
                borderColor: 'rgb(0, 255, 0)',
                backgroundColor: 'rgba(0, 255, 0, 0.1)',
                fill: false,
                borderWidth: 2,
                pointRadius: 0,
                pointHoverRadius: 4
            });
        }
        
        // Battery Charge dataset
        if ($('#show-battery-charge').prop('checked') && r.battery_charge) {
            datasets.push({
                label: 'Battery Charge',
                data: filteredBatteryCharge,
                borderColor: 'rgb(255, 165, 0)',
                backgroundColor: 'rgba(255, 165, 0, 0.1)',
                fill: false,
                borderWidth: 2,
                pointRadius: 0,
                pointHoverRadius: 4
            });
        }
        
        // Max Grid Load line
        if ($('#show-grid-limit').prop('checked')) {
            datasets.push({
                label: 'Max Grid Load',
                data: Array(filteredTimePoints.length).fill(r.max_grid_load),
                borderColor: 'rgb(255, 0, 0)',
                backgroundColor: 'rgba(255, 0, 0, 0.1)',
                borderDash: [5, 5],
                fill: false,
                borderWidth: 2,
                pointRadius: 0
            });
        }
        
        // Create or update chart
        const ctx = document.getElementById('energy-flows-chart').getContext('2d');
        
        if (charts.energyFlowsChart) {
            charts.energyFlowsChart.data.labels = labels;
            charts.energyFlowsChart.data.datasets = datasets;
            charts.energyFlowsChart.update();
        } else {
            charts.energyFlowsChart = new Chart(ctx, {
                type: 'line',
                data: {
                    labels: labels,
                    datasets: datasets
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    scales: {
                        x: {
                            display: true,
                            title: {
                                display: true,
                                text: 'Time'
                            },
                            ticks: {
                                maxTicksLimit: 24, // Limit number of ticks for readability
                                callback: function(value, index) {
                                    // Show only some labels for clarity
                                    const step = Math.ceil(labels.length / 24);
                                    return index % step === 0 ? this.getLabelForValue(value) : '';
                                }
                            }
                        },
                        y: {
                            display: true,
                            title: {
                                display: true,
                                text: 'Power [kW]'
                            },
                            suggestedMin: 0,
                            ticks: {
                                callback: function(value) {
                                    return value.toLocaleString();
                                }
                            }
                        }
                    },
                    interaction: {
                        mode: 'index',
                        intersect: false
                    },
                    plugins: {
                        legend: {
                            position: 'top',
                            labels: {
                                boxWidth: 12,
                                usePointStyle: true
                            }
                        },
                        title: {
                            display: true,
                            text: 'Energy Flows Over Time'
                        },
                        tooltip: {
                            callbacks: {
                                label: function(context) {
                                    return `${context.dataset.label}: ${context.raw.toLocaleString()} kW`;
                                }
                            }
                        }
                    }
                }
            });
        }
    }
    
    // Create battery state chart
    function createBatteryStateChart(data) {
        const r = data.results;
        const timePoints = data.time_periods || [];
        
        if (!r.battery_soc || !timePoints.length) {
            console.log('No battery SOC data available');
            $('#battery-state-container').hide();
            return;
        }
        
        // Convert time points to more readable format
        const labels = timePoints.map(tp => {
            const minutesTotal = parseInt(tp);
            const day = Math.floor(minutesTotal / (24 * 60)) + 1;
            const hour = Math.floor((minutesTotal % (24 * 60)) / 60);
            return `Day ${day}, ${hour}:00`;
        });
        
        // Create chart
        const ctx = document.getElementById('battery-state-chart').getContext('2d');
        if (charts.batteryStateChart) charts.batteryStateChart.destroy();
        
        charts.batteryStateChart = new Chart(ctx, {
            type: 'line',
            data: {
                labels: labels,
                datasets: [{
                    label: 'Battery State of Charge',
                    data: r.battery_soc,
                    borderColor: 'rgb(128, 0, 128)',
                    backgroundColor: 'rgba(128, 0, 128, 0.1)',
                    fill: true,
                    borderWidth: 2,
                    pointRadius: 0,
                    pointHoverRadius: 4
                }, {
                    label: 'Battery Capacity',
                    data: Array(labels.length).fill(r.battery_capacity),
                    borderColor: 'rgb(128, 0, 128)',
                    borderDash: [5, 5],
                    fill: false,
                    borderWidth: 1,
                    pointRadius: 0
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                scales: {
                    x: {
                        display: true,
                        title: {
                            display: true,
                            text: 'Time'
                        },
                        ticks: {
                            maxTicksLimit: 24,
                            callback: function(value, index) {
                                const step = Math.ceil(labels.length / 24);
                                return index % step === 0 ? this.getLabelForValue(value) : '';
                            }
                        }
                    },
                    y: {
                        display: true,
                        title: {
                            display: true,
                            text: 'Energy [kWh]'
                        },
                        suggestedMin: 0,
                        suggestedMax: r.battery_capacity * 1.1
                    }
                },
                plugins: {
                    legend: {
                        position: 'top',
                        labels: {
                            boxWidth: 12,
                            usePointStyle: true
                        }
                    },
                    title: {
                        display: true,
                        text: 'Battery State of Charge'
                    },
                    tooltip: {
                        callbacks: {
                            label: function(context) {
                                return `${context.dataset.label}: ${context.raw.toFixed(2)} kWh`;
                            }
                        }
                    }
                }
            }
        });
    }
    
    // Create sessions chart
    function createSessionsChart(data) {
        const r = data.results;
        
        if (!r.daily_charging_sessions) {
            $('#sessions-chart').parent().parent().hide();
            return;
        }
        
        const sessions = r.daily_charging_sessions;
        const days = Object.keys(sessions);
        const labels = days.map(d => `Day ${parseInt(d) + 1}`);
        
        // Extract data for each charger type
        const chargerTypes = {};
        
        days.forEach(day => {
            const dayData = sessions[day];
            Object.keys(dayData).forEach(type => {
                if (!chargerTypes[type]) {
                    chargerTypes[type] = Array(days.length).fill(0);
                }
                chargerTypes[type][days.indexOf(day)] = dayData[type];
            });
        });
        
        // Prepare datasets
        const datasets = Object.keys(chargerTypes).map((type, index) => {
            const colors = ['#4e73df', '#1cc88a', '#36b9cc'];
            return {
                label: type,
                data: chargerTypes[type],
                backgroundColor: colors[index % colors.length]
            };
        });
        
        // Create chart
        const ctx = document.getElementById('sessions-chart').getContext('2d');
        if (charts.sessionsChart) charts.sessionsChart.destroy();
        
        charts.sessionsChart = new Chart(ctx, {
            type: 'bar',
            data: {
                labels: labels,
                datasets: datasets
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                scales: {
                    x: {
                        stacked: true
                    },
                    y: {
                        stacked: true,
                        title: {
                            display: true,
                            text: 'Number of Sessions'
                        }
                    }
                },
                plugins: {
                    title: {
                        display: true,
                        text: 'Daily Charging Sessions'
                    },
                    legend: {
                        position: 'top',
                        labels: {
                            boxWidth: 12,
                            usePointStyle: true
                        }
                    }
                }
            }
        });
    }
    
    // Create utilization chart
    function createUtilizationChart(data) {
        const r = data.results;
        
        if (!r.charger_utilization) {
            $('#utilization-chart').parent().parent().hide();
            return;
        }
        
        const utilization = r.charger_utilization;
        const labels = Object.keys(utilization);
        
        // Get weekly totals for each charger type
        const weeklySessions = r.weekly_charging_totals || {};
        
        // Calculate absolute utilization numbers
        const absoluteValues = labels.map(label => {
            // Get the number of chargers of this type
            const countKey = `${label}_count`;
            const numChargers = r[countKey] || 0;
            
            // Get the total weekly sessions for this type
            const totalSessions = weeklySessions[label] || 0;
            
            return totalSessions;
        });
        
        // Create chart
        const ctx = document.getElementById('utilization-chart').getContext('2d');
        if (charts.utilizationChart) charts.utilizationChart.destroy();
        
        charts.utilizationChart = new Chart(ctx, {
            type: 'bar',
            data: {
                labels: labels,
                datasets: [{
                    label: 'Weekly Sessions',
                    data: absoluteValues,
                    backgroundColor: ['#4e73df', '#1cc88a', '#36b9cc']
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                scales: {
                    y: {
                        beginAtZero: true,
                        title: {
                            display: true,
                            text: 'Number of Weekly Sessions'
                        }
                    }
                },
                plugins: {
                    title: {
                        display: true,
                        text: 'Charger Weekly Sessions'
                    },
                    legend: {
                        display: false
                    },
                    tooltip: {
                        callbacks: {
                            label: function(context) {
                                const label = context.dataset.label || '';
                                const value = context.raw;
                                const chargerType = context.label;
                                const countKey = `${chargerType}_count`;
                                const numChargers = r[countKey] || 0;
                                const utilPercent = (utilization[chargerType] * 100).toFixed(1);
                                
                                return [
                                    `${label}: ${value} sessions`,
                                    `Number of chargers: ${numChargers}`,
                                    `Utilization: ${utilPercent}%`
                                ];
                            }
                        }
                    }
                }
            }
        });
    }
    
    // Compare two results
    function compareResults(name1, name2) {
        const r1 = allResultsData[name1].results;
        const r2 = allResultsData[name2].results;
        
        $('#compare-col-1').text(name1);
        $('#compare-col-2').text(name2);
        
        const metricsToCompare = [
            { key: 'total_cost', label: 'Total Cost (€)', format: formatNumber },
            { key: 'connection_cost', label: 'Connection Cost (€)', format: formatNumber },
            { key: 'capacity_cost', label: 'Capacity Cost (€)', format: formatNumber },
            { key: 'battery_cost', label: 'Battery Cost (€)', format: formatNumber },
            { key: 'transformer_cost', label: 'Transformer Cost (€)', format: formatNumber },
            { key: 'internal_cable_cost', label: 'Internal Cable Cost (€)', format: formatNumber },
            { key: 'charger_cost', label: 'Charger Cost (€)', format: formatNumber },
            { key: 'max_grid_load', label: 'Max Grid Load (kW)', format: formatDecimal },
            { key: 'battery_capacity', label: 'Battery Capacity (kWh)', format: formatDecimal },
            { key: 'battery_peak_power', label: 'Battery Peak Power (kW)', format: formatDecimal },
            { key: 'energy_throughput_weekly_kwh', label: 'Weekly Energy (kWh)', format: formatDecimal },
            { key: 'energy_throughput_annual_gwh', label: 'Annual Energy (GWh)', format: formatDecimal }
        ];
        
        $('#compare-table').empty();
        
        metricsToCompare.forEach(metric => {
            const val1 = r1[metric.key] !== undefined ? metric.format(r1[metric.key]) : '-';
            const val2 = r2[metric.key] !== undefined ? metric.format(r2[metric.key]) : '-';
            
            let diff = '-';
            let diffClass = '';
            
            if (r1[metric.key] !== undefined && r2[metric.key] !== undefined) {
                const diffValue = r1[metric.key] - r2[metric.key];
                diff = diffValue > 0 ? `+${metric.format(diffValue)}` : metric.format(diffValue);
                diffClass = diffValue > 0 ? 'text-danger' : diffValue < 0 ? 'text-success' : '';
            }
            
            $('#compare-table').append(
                `<tr>
                    <td>${metric.label}</td>
                    <td>${val1}</td>
                    <td>${val2}</td>
                    <td class="${diffClass}">${diff}</td>
                </tr>`
            );
        });
        
        $('#compare-results').removeClass('d-none');
    }    // Add scroll event handler for the results container
    $(document).on('scroll', '.results-container', function() {
        const container = $(this);
        const scrollPosition = container.scrollTop() + container.innerHeight();
        const scrollHeight = container[0].scrollHeight;
        
        // Hide shadow when at the bottom
        if (scrollPosition >= scrollHeight - 5) {
            container.removeClass('can-scroll');
        } else if (container[0].scrollHeight > container[0].clientHeight) {
            container.addClass('can-scroll');
        }
    });
    
    // Handle window resize to update scroll indicators
    $(window).resize(function() {
        updateScrollIndicator();
    });

    // Initialize the page
    refreshResultsList();
});