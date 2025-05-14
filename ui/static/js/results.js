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
                    // Sort results by name instead of date
                    data.results.sort((a, b) => a.name.localeCompare(b.name));
                 
                    data.results.forEach(result => {
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
    
    // View filters for Energy Flows (All Days, 24h, Weekday, Weekend)
    $('#view-all-days, #view-24h, #view-weekday, #view-weekend').click(function() {
        $('#view-all-days, #view-24h, #view-weekday, #view-weekend').removeClass('active');
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
    }    function formatDecimal(num, places = 2) {
        if (num === undefined || num === null) {
            return '-';
        }
        return Number(num).toFixed(places).replace(/\B(?=(\d{3})+(?!\d))/g, ' ');
    }
    
    function formatEnergyValue(value, places = 2) {
        if (value === undefined || value === null) {
            return '-';
        }
        
        // Convert to MWh if value is >= 1000 kWh
        if (value >= 1000) {
            return formatDecimal(value / 1000, places) + ' MWh';
        } else {
            return formatDecimal(value, places) + ' kWh';
        }
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
            ['File',  data.scenario],
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
        );        // Key metrics - Correctly mapped to the appropriate data fields
        $('#metric-peak-demand').text(formatDecimal(r.peak_load || r.peak_demand || r.max_demand || 0, 2)); // Peak Demand
        $('#metric-peak-grid-load').text(formatDecimal(r.max_grid_load, 2)); // Peak Grid Load
        $('#metric-weekly-energy').text(formatEnergyValue(r.energy_throughput_weekly_kwh)); // Weekly Energy Throughput
        
        // Energy metrics
        $('#energy-metric-weekly').text(formatEnergyValue(r.energy_throughput_weekly_kwh));
        $('#metric-annual-energy').text(formatDecimal(r.energy_throughput_annual_gwh) + ' GWh');
        
        // Battery metrics
        if (r.battery_capacity > 0) {
            $('#battery-metrics-row').removeClass('d-none');
            $('#metric-battery-capacity').text(formatDecimal(r.battery_capacity, 2));
            $('#metric-battery-peak-power').text(formatDecimal(r.battery_peak_power, 2));
            $('#metric-battery-cost').text(formatDecimal(r.battery_cost, 2));
            $('#metric-battery-cycles-weekly').text(formatDecimal(r.battery_cycles_weekly || 0, 2));
            $('#metric-battery-cycles-annual').text(formatDecimal(r.battery_cycles_annual || 0, 2));
            $('#battery-state-container').show();
        } else {
            $('#battery-metrics-row').addClass('d-none');
            $('#battery-state-container').hide();
            $('#metric-battery-cycles-weekly').text('-');
            $('#metric-battery-cycles-annual').text('-');
        }        // Connection details - determine which connection is used
        const useDistribution = r.use_distribution != null ? (r.use_distribution > 0.5 ? 1 : 0) : 0;
        const useTransmission = r.use_transmission != null ? (r.use_transmission > 0.5 ? 1 : 0) : 0;
        const useExistingMV = r.use_existing_mv != null ? (r.use_existing_mv > 0.5 ? 1 : 0) : 0;
        const useHV = r.use_hv != null ? (r.use_hv > 0.5 ? 1 : 0) : 0;
        
        // Determine the connection type
        let connectionType = "None";
        if (useExistingMV === 1) {
            connectionType = "Existing MV Connection";
        } else if (useDistribution === 1) {
            connectionType = "Distribution Line";
        } else if (useTransmission === 1) {
            connectionType = "Transmission Line";
        } else if (useHV === 1) {
            connectionType = "New Substation";
        }
        
        // Update the connection details card to use a styled table like the Energy Metrics
        $('#connection-details-table').parent().parent().html(`
            <div class="card-header bg-primary text-white">
                <h6 class="card-title mb-0">Connection Details</h6>
            </div>
            <div class="card-body">
                <table class="table table-sm table-striped">
                    <tbody>
                        <tr>
                            <th>Connection Type</th>
                            <td class="text-end">${connectionType}</td>
                        </tr>
                        ${useDistribution === 1 && r.distribution_distance ? 
                            `<tr>
                                <th>Distribution Distance</th>
                                <td class="text-end">${formatDecimal(r.distribution_distance, 2)} m</td>
                            </tr>` : ''
                        }
                        ${useTransmission === 1 && r.transmission_distance ? 
                            `<tr>
                                <th>Transmission Distance</th>
                                <td class="text-end">${formatDecimal(r.transmission_distance, 2)} m</td>
                            </tr>` : ''
                        }
                        ${useHV === 1 && r.hv_distance ? 
                            `<tr>
                                <th>HV Distance</th>
                                <td class="text-end">${formatDecimal(r.powerline_distance, 2)} m</td>
                            </tr>` : ''
                        }
                        ${useExistingMV !== 1 ? (
                            useDistribution === 1 && r.distribution_selected_size !== undefined ? 
                                `<tr>
                                    <th>Selected Cable Size</th>
                                    <td class="text-end">${formatDecimal(r.distribution_selected_size, 1)} mm²</td>
                                </tr>` : 
                            useTransmission === 1 && r.transmission_selected_size !== undefined ? 
                                `<tr>
                                    <th>Selected Cable Size</th>
                                    <td class="text-end">${formatDecimal(r.transmission_selected_size, 1)} mm²</td>
                                </tr>` : 
                            useHV === 1 && r.hv_selected_size !== undefined ? 
                                `<tr>
                                    <th>Selected Cable Size</th>
                                    <td class="text-end">${formatDecimal(r.hv_selected_size, 1)} mm²</td>
                                </tr>` : ''
                        ) : ''}
                        ${r.capacity_limit ? 
                            `<tr>
                                <th>Grid Connection Limit</th>
                                <td class="text-end">${formatDecimal(r.capacity_limit, 2)} kW</td>
                            </tr>` : ''
                        }
                        ${useExistingMV !== 1 ? (
                            useDistribution === 1 && r.distribution_capacity ? 
                                `<tr>
                                    <th>Cable Power Limit</th>
                                    <td class="text-end">${formatDecimal(r.distribution_capacity, 2)} kW</td>
                                </tr>` : 
                            useTransmission === 1 && r.transmission_capacity ? 
                                `<tr>
                                    <th>Cable Power Limit</th>
                                    <td class="text-end">${formatDecimal(r.transmission_capacity, 2)} kW</td>
                                </tr>` : 
                            useHV === 1 && r.hv_capacity ? 
                                `<tr>
                                    <th>Cable Power Limit</th>
                                    <td class="text-end">${formatDecimal(r.hv_capacity, 2)} kW</td>
                                </tr>` : ''
                        ) : ''}
                        <tr>
                            <th>Connection Cost</th>
                            <td class="text-end">${formatNumber(r.connection_cost)} €</td>
                        </tr>
                        <tr>
                            <th>Capacity Cost</th>
                            <td class="text-end">${formatNumber(r.capacity_cost)} €</td>
                        </tr>
                    </tbody>
                </table>
            </div>
        `);

        // Infrastructure tables - now only showing non-connection distance information
        $('#infrastructure-distance-table').empty();
        
        // Populate the Alternative Connections table with unused connection types
        populateAlternativeConnections(r, useExistingMV, useDistribution, useTransmission, useHV);
        
        // Add any other distance/capacity metrics that aren't connection-related
        // For example, if there are site-specific distances or capacities
        $('#infrastructure-transformer-table').empty().append(
            `<tr><th>Transformer Capacity</th><td>${r.transformer_capacity} kW</td></tr>
             <tr><th>Description</th><td>${r.transformer_description || '-'}</td></tr>`
        );

        // Call the new charger summary function instead of directly populating the table
        populateChargerSummary(r);
    }
    
    // Initialize all charts
    function initCharts(data) {
        // Always make sure "All Days" option is selected by default when initializing charts
        $('#view-all-days, #view-24h, #view-weekday, #view-weekend').removeClass('active');
        $('#view-all-days').addClass('active');
        
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
        // Make sure "All Days" is selected by default when switching to charts tab if none are active
        if (!$('#view-all-days.active, #view-24h.active, #view-weekday.active, #view-weekend.active').length) {
            $('#view-all-days, #view-24h, #view-weekday, #view-weekend').removeClass('active');
            $('#view-all-days').addClass('active');
        }
        
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
                        $('#view-24h.active').length ? '24h' :
                        $('#view-weekday.active').length ? 'weekday' : 'weekend';
        
        console.log(`Selected view mode: ${viewMode}`);
        
        // Calculate indices based on view mode
        if (viewMode === '24h') {
            // Find the timestamps for Day 1 9:00 (hours = 9) and Day 2 9:00 (hours = 33)
            // A day has 24 hours, so day 1 hour 9 = 9, day 2 hour 9 = 33
            const day1Minutes = 24 * 60; // Minutes in a day
            const hour9Minutes = 9 * 60; // 9:00 in minutes
            
            // Find exact or closest time points to Day 1 9:00 and Day 2 9:00
            const findClosestTimePoint = (targetMinutes) => {
                let closest = 0;
                let minDiff = Number.MAX_SAFE_INTEGER;
                
                timePoints.forEach((tp, index) => {
                    const minutes = parseInt(tp);
                    const diff = Math.abs(minutes - targetMinutes);
                    if (diff < minDiff) {
                        minDiff = diff;
                        closest = index;
                    }
                });
                
                return closest;
            };
            
            // Day 1 9:00 AM is the 9th hour of the first day = 9 * 60 = 540 minutes
            const day1Hour9 = hour9Minutes;
            
            // Day 2 9:00 AM is the 9th hour of the second day = 24 * 60 + 9 * 60 = 1980 minutes
            const day2Hour9 = day1Minutes + hour9Minutes;
            
            startIndex = findClosestTimePoint(day1Hour9);
            endIndex = findClosestTimePoint(day2Hour9);
            
            console.log(`24h view - Start: Day 1, 9:00 (${timePoints[startIndex]} minutes), End: Day 2, 9:00 (${timePoints[endIndex]} minutes)`);
        } else if (viewMode === 'weekday') {
            // Assuming first 5 days are weekdays (simple simulation)
            endIndex = Math.floor(timePoints.length * (5/7)) - 1;
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
        
        // Convert time points to more readable format with additional debugging info
        const labels = filteredTimePoints.map(tp => {
            const minutesTotal = parseInt(tp);
            const day = Math.floor(minutesTotal / (24 * 60)) + 1;
            const hour = Math.floor((minutesTotal % (24 * 60)) / 60);
            const minutes = minutesTotal % 60;
            const hourStr = hour.toString().padStart(2, '0');
            
            // Include minutes if non-zero (useful for 15-min intervals)
            if (minutes > 0) {
                const minStr = minutes.toString().padStart(2, '0');
                return `Day ${day}, ${hourStr}:${minStr}`;
            }
            return `Day ${day}, ${hourStr}:00`;
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
        
        // Define the correct order of days in German
        const dayOrder = ['Montag', 'Dienstag', 'Mittwoch', 'Donnerstag', 'Freitag', 'Samstag', 'Sonntag'];
        
        // Get the days from the data and sort them according to the defined order
        let days = Object.keys(sessions);
        days.sort((a, b) => {
            return dayOrder.indexOf(a) - dayOrder.indexOf(b);
        });
        
        // Use the sorted day names for labels
        const labels = days;
        
        // Extract data for each charger type, ensuring it follows the sorted day order
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
        
        // Define the desired order of charger types
        const desiredOrder = ['MCS', 'HPC', 'NCS'];
        
        // Filter and sort labels according to the desired order
        let labels = Object.keys(utilization).filter(label => desiredOrder.includes(label));
        labels.sort((a, b) => desiredOrder.indexOf(a) - desiredOrder.indexOf(b));
        
        // Get weekly totals for each charger type
        const weeklySessions = r.weekly_charging_totals || {};
        
        // Calculate absolute utilization numbers
        const absoluteValues = labels.map(label => {
            // Get the total weekly sessions for this type
            return weeklySessions[label] || 0;
        });
        
        // Calculate sessions per day per charger for tooltips
        const sessionsPerDayPerCharger = labels.map(label => {
            const countKey = `${label}_count`;
            const numChargers = r[countKey] || 0;
            const totalSessions = weeklySessions[label] || 0;
            
            // Calculate sessions per day per charger (weekly sessions / 7 days / number of chargers)
            return numChargers > 0 ? (totalSessions / 7 / numChargers) : 0;
        });
        
        // Create chart
        const ctx = document.getElementById('utilization-chart').getContext('2d');
        if (charts.utilizationChart) charts.utilizationChart.destroy();
        
        // Choose appropriate colors based on the order
        const backgroundColors = [];
        labels.forEach(label => {
            if (label === 'MCS') backgroundColors.push('#1cc88a'); // Green
            else if (label === 'HPC') backgroundColors.push('#4e73df'); // Blue
            else if (label === 'NCS') backgroundColors.push('#36b9cc'); // Cyan
        });
        
        charts.utilizationChart = new Chart(ctx, {
            type: 'bar',
            data: {
                labels: labels,
                datasets: [{
                    label: 'Weekly Sessions',
                    data: absoluteValues,
                    backgroundColor: backgroundColors
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
                                const index = labels.indexOf(chargerType);
                                const countKey = `${chargerType}_count`;
                                const numChargers = r[countKey] || 0;
                                const sessionsPerDay = sessionsPerDayPerCharger[index].toFixed(1);
                                
                                return [
                                    `${label}: ${value} sessions`,
                                    `Number of chargers: ${numChargers}`,
                                    `Sessions per day per charger: ${sessionsPerDay}`
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
        
        // Extract names without IDs for cleaner display
        const displayName1 = name1.split('_').slice(1).join('_');
        const displayName2 = name2.split('_').slice(1).join('_');
        
        $('#compare-col-1').text(displayName1);
        $('#compare-col-2').text(displayName2);
        
        // Organize metrics into categories for better presentation
        const metricCategories = [
            {
                name: 'Cost Breakdown',
                metrics: [
                    { key: 'total_cost', label: 'Total Cost (€)', format: formatNumber, important: true },
                    { key: 'connection_cost', label: 'Connection Cost (€)', format: formatNumber },
                    { key: 'capacity_cost', label: 'Capacity Cost (€)', format: formatNumber },
                    { key: 'battery_cost', label: 'Battery Cost (€)', format: formatNumber },
                    { key: 'transformer_cost', label: 'Transformer Cost (€)', format: formatNumber },
                    { key: 'internal_cable_cost', label: 'Internal Cable Cost (€)', format: formatNumber },
                    { key: 'charger_cost', label: 'Charger Cost (€)', format: formatNumber }
                ]
            },
            {
                name: 'Technical Specifications',
                metrics: [
                    { key: 'max_grid_load', label: 'Max Grid Load (kW)', format: formatDecimal, important: true },
                    { key: 'battery_capacity', label: 'Battery Capacity (kWh)', format: formatDecimal, important: true },
                    { key: 'battery_peak_power', label: 'Battery Peak Power (kW)', format: formatDecimal },
                    { key: 'energy_throughput_weekly_kwh', label: 'Weekly Energy (kWh)', format: formatDecimal },
                    { key: 'energy_throughput_annual_gwh', label: 'Annual Energy (GWh)', format: formatDecimal }
                ]
            },
            {
                name: 'Charger Configuration',
                metrics: [
                    { key: 'MCS_count', label: 'MCS Chargers', format: formatDecimal },
                    { key: 'HPC_count', label: 'HPC Chargers', format: formatDecimal },
                    { key: 'NCS_count', label: 'NCS Chargers', format: formatDecimal }
                ]
            }
        ];
        
        // Clear previous results
        $('#compare-table').empty();
        
        // Create a more structured table with categories
        metricCategories.forEach(category => {
            // Add category header
            $('#compare-table').append(
                `<tr class="table-secondary">
                    <th colspan="4">${category.name}</th>
                </tr>`
            );
            
            // Add metrics in this category
            category.metrics.forEach(metric => {
                // Skip metrics that don't exist in either result
                if (r1[metric.key] === undefined && r2[metric.key] === undefined) return;
                
                const val1 = r1[metric.key] !== undefined ? metric.format(r1[metric.key]) : '-';
                const val2 = r2[metric.key] !== undefined ? metric.format(r2[metric.key]) : '-';
                
                let diff = '-';
                let diffClass = '';
                let diffIcon = '';
                
                if (r1[metric.key] !== undefined && r2[metric.key] !== undefined) {
                    const diffValue = r1[metric.key] - r2[metric.key];
                    diff = diffValue > 0 ? `+${metric.format(diffValue)}` : metric.format(diffValue);
                    
                    // Determine if higher is better based on metric key (for costs, lower is better)
                    const isLowerBetter = metric.key.includes('cost');
                    
                    if (diffValue > 0) {
                        diffClass = isLowerBetter ? 'text-danger' : 'text-success';
                        diffIcon = isLowerBetter ? 
                            '<i class="fas fa-arrow-up text-danger"></i>' : 
                            '<i class="fas fa-arrow-up text-success"></i>';
                    } else if (diffValue < 0) {
                        diffClass = isLowerBetter ? 'text-success' : 'text-danger';
                        diffIcon = isLowerBetter ? 
                            '<i class="fas fa-arrow-down text-success"></i>' : 
                            '<i class="fas fa-arrow-down text-danger"></i>';
                    }
                    
                    // Calculate percent difference if relevant
                    if (r2[metric.key] !== 0) {
                        const percentDiff = (diffValue / Math.abs(r2[metric.key]) * 100).toFixed(1);
                        diff += ` (${percentDiff}%)`;
                    }
                }
                
                // Apply heavier styling to important metrics
                const rowClass = metric.important ? 'fw-bold' : '';
                
                $('#compare-table').append(
                    `<tr class="${rowClass}">
                        <td>${metric.label}</td>
                        <td class="text-end">${val1}</td>
                        <td class="text-end">${val2}</td>
                        <td class="text-end ${diffClass}">${diffIcon} ${diff}</td>
                    </tr>`
                );
            });
        });
        
        // Add a summary section highlighting the key differences
        const totalCostDiff = r1.total_cost - r2.total_cost;
        const costPercentDiff = ((totalCostDiff / r2.total_cost) * 100).toFixed(1);
        const summaryMessage = totalCostDiff < 0 ? 
            `<div class="alert alert-success mt-3">
                <i class="fas fa-check-circle"></i> <strong>Result 1 costs ${formatNumber(Math.abs(totalCostDiff))}€ less</strong> 
                than Result 2 (${costPercentDiff}% saving)
            </div>` : 
            `<div class="alert alert-warning mt-3">
                <i class="fas fa-exclamation-triangle"></i> <strong>Result 1 costs ${formatNumber(totalCostDiff)}€ more</strong> 
                than Result 2 (${costPercentDiff}% increase)
            </div>`;
        
        // Show result summary and explanation
        $('#compare-summary').html(summaryMessage);
        $('#compare-summary').show();
        
        // Show the key differences chart
        createComparisonChart(name1, name2, r1, r2);
        
        $('#compare-results').removeClass('d-none');
    }

    // Create a comparison chart to visualize differences
    function createComparisonChart(name1, name2, r1, r2) {
        // Prepare data for the chart
        const costCategories = ['Connection', 'Capacity', 'Battery', 'Transformer', 'Internal Cable', 'Chargers'];
        const costData1 = [
            r1.connection_cost || 0,
            r1.capacity_cost || 0, 
            r1.battery_cost || 0,
            r1.transformer_cost || 0,
            r1.internal_cable_cost || 0,
            r1.charger_cost || 0
        ];
        
        const costData2 = [
            r2.connection_cost || 0,
            r2.capacity_cost || 0, 
            r2.battery_cost || 0,
            r2.transformer_cost || 0,
            r2.internal_cable_cost || 0,
            r2.charger_cost || 0
        ];
        
        // Extract names without IDs for cleaner display
        const displayName1 = name1.split('_').slice(1).join('_');
        const displayName2 = name2.split('_').slice(1).join('_');
        
        // Create or update chart
        const ctx = document.getElementById('comparison-chart').getContext('2d');
        
        if (charts.comparisonChart) {
            charts.comparisonChart.destroy();
        }
        
        charts.comparisonChart = new Chart(ctx, {
            type: 'bar',
            data: {
                labels: costCategories,
                datasets: [
                    {
                        label: displayName1,
                        data: costData1,
                        backgroundColor: '#4e73df',
                        order: 1
                    },
                    {
                        label: displayName2,
                        data: costData2,
                        backgroundColor: '#1cc88a',
                        order: 2
                    }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                scales: {
                    y: {
                        beginAtZero: true,
                        title: {
                            display: true,
                            text: 'Cost (€)'
                        },
                        ticks: {
                            callback: function(value) {
                                return value.toLocaleString();
                            }
                        }
                    }
                },
                plugins: {
                    title: {
                        display: true,
                        text: 'Cost Comparison by Category'
                    },
                    tooltip: {
                        callbacks: {
                            label: function(context) {
                                return `${context.dataset.label}: ${formatNumber(context.raw)} €`;
                            }
                        }
                    }
                }
            }
        });
    }

    // Add scroll event handler for the results container
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
    
    // Helper function to populate the Alternative Connections table
    function populateAlternativeConnections(r, useExistingMV, useDistribution, useTransmission, useHV) {
        const alternativeTable = $('#infrastructure-distance-table');
        alternativeTable.empty();
        
        // If no data is available, show a message
        if (!r) {
            alternativeTable.append('<tr><td colspan="2" class="text-center">No alternative connection data available</td></tr>');
            return;
        }
        
        let alternativesFound = false;
        
        // Check for Distribution Line as an alternative
        if (useDistribution !== 1 && r.distribution_distance !== undefined) {
            alternativeTable.append(`
                <tr class="table-secondary">
                    <th colspan="2">Distribution Line</th>
                </tr>
                <tr>
                    <th>Distance</th>
                    <td class="text-end">${formatDecimal(r.distribution_distance, 2)} m</td>
                </tr>
            `);
            
            // Add cable size if available
            if (r.distribution_selected_size !== undefined) {
                alternativeTable.append(`
                    <tr>
                        <th>Cable Size</th>
                        <td class="text-end">${formatDecimal(r.distribution_selected_size, 1)} mm²</td>
                    </tr>
                `);
            }
            
            if (r.distribution_cost !== undefined) {
                alternativeTable.append(`
                    <tr>
                        <th>Cost</th>
                        <td class="text-end">${formatNumber(r.distribution_cost)} €</td>
                    </tr>
                `);
            }
            
            alternativesFound = true;
        }
        
        // Check for Transmission Line as an alternative
        if (useTransmission !== 1 && r.transmission_distance !== undefined) {
            alternativeTable.append(`
                <tr class="table-secondary">
                    <th colspan="2">Transmission Line</th>
                </tr>
                <tr>
                    <th>Distance</th>
                    <td class="text-end">${formatDecimal(r.transmission_distance, 2)} m</td>
                </tr>
            `);
            
            // Add cable size if available
            if (r.transmission_selected_size !== undefined) {
                alternativeTable.append(`
                    <tr>
                        <th>Cable Size</th>
                        <td class="text-end">${formatDecimal(r.transmission_selected_size, 1)} mm²</td>
                    </tr>
                `);
            }
            
            if (r.transmission_cost !== undefined) {
                alternativeTable.append(`
                    <tr>
                        <th>Cost</th>
                        <td class="text-end">${formatNumber(r.transmission_cost)} €</td>
                    </tr>
                `);
            }
            
            alternativesFound = true;
        }
        
        // Check for HV/New Substation as an alternative
        if (useHV !== 1 && r.powerline_distance !== undefined) {
            alternativeTable.append(`
                <tr class="table-secondary">
                    <th colspan="2">New Substation (HV)</th>
                </tr>
                <tr>
                    <th>Distance</th>
                    <td class="text-end">${formatDecimal(r.hv_distance || r.powerline_distance, 2)} m</td>
                </tr>
            `);
            
            // Add cable size if available
            if (r.hv_selected_size !== undefined) {
                alternativeTable.append(`
                    <tr>
                        <th>Cable Size</th>
                        <td class="text-end">${formatDecimal(r.hv_selected_size, 1)} mm²</td>
                    </tr>
                `);
            }
            
            if (r.hv_cost !== undefined) {
                alternativeTable.append(`
                    <tr>
                        <th>Cost</th>
                        <td class="text-end">${formatNumber(r.hv_cost)} €</td>
                    </tr>
                `);
            }
            
            alternativesFound = true;
        }
        
        // If no alternatives were found, show a message
        if (!alternativesFound) {
            alternativeTable.append('<tr><td colspan="2" class="text-center">No alternative connection data available</td></tr>');
        }
    }
    
    // Update the charger summary table with enhanced information
    function populateChargerSummary(r) {
        $('#charger-summary-table').empty();
        const chargerTypes = [
            ['MCS_count', 'MCS'], 
            ['HPC_count', 'HPC'], 
            ['NCS_count', 'NCS']
        ];
        
        let hasData = false;
        
        chargerTypes.forEach(([key, label]) => {
            if (r[key] !== undefined) {
                hasData = true;
                const count = r[key];
                
                // Get weekly sessions from the weekly_charging_totals if available
                const weeklySessions = r.weekly_charging_totals && r.weekly_charging_totals[label] !== undefined 
                    ? r.weekly_charging_totals[label] 
                    : (r.weekly_charging_sessions && r.weekly_charging_sessions[label] ? r.weekly_charging_sessions[label] : 0);
                
                // Get utilization as sessions per charger per day
                const utilization = r.charger_utilization && r.charger_utilization[label] !== undefined
                    ? formatDecimal(r.charger_utilization[label], 1)
                    : '-';
                
                // Sessions per week per charger, calculated if available
                const sessionsPerWeekPerCharger = count > 0 && weeklySessions 
                    ? formatDecimal(weeklySessions / count, 1) 
                    : '-';
                
                $('#charger-summary-table').append(
                    `<tr>
                        <td class="text-center">${label}</td>
                        <td class="text-center">${count}</td>
                        <td class="text-center">${weeklySessions}</td>
                        <td class="text-center">${utilization}</td>
                    </tr>`
                );
            }
        });
        
        // If no charger data, add a message
        if (!hasData) {
            $('#charger-summary-table').append(
                `<tr><td colspan="4" class="text-center">No charger data available</td></tr>`
            );
        }
    }
});