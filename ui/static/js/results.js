$(document).ready(function() {
    console.log('Results page script loaded');
    const apiBase = window.location.origin;
    let currentResult = null;
    let resultData = null;
    let charts = {};
    let allResultsData = {};

    // Refresh results list function
    function refreshResultsList() {
        console.log('Refreshing results list...');
        $.ajax({
            url: `${apiBase}/api/results/list`, method: 'GET',
            success: function(data) {
                const resultList = $('#result-list').empty();
                $('#compare-select').empty();
                if (data.results && data.results.length) {
                    $('#no-results-message').hide();
                    data.results.sort((a, b) => b.date - a.date);
                    data.results.forEach(result => {
                        const dateStr = new Date(result.date * 1000).toISOString().split('T')[0];
                        const item = $(
                            `<a href="#" class="list-group-item list-group-item-action" 
                               data-result-id="${result.id}" 
                               data-result-name="${result.name}">
                                <div class="d-flex justify-content-between align-items-center">
                                    <div class="result-info">
                                        <h6 class="mb-0">${result.id}</h6>
                                        <small class="text-muted text-truncate">${result.type}</small>
                                    </div>
                                    <small class="text-muted result-date">${dateStr}</small>
                                </div>
                            </a>`
                        );
                        resultList.append(item);
                        $('#compare-select').append($('<option>', { value: result.name, text: `${result.id}: ${result.type} (${dateStr})` }));
                    });
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
    }

    // Event bindings
    $('#refresh-results').click(refreshResultsList);
    $('#result-list').on('click', '.list-group-item', function(e) {
        e.preventDefault();
        $('.list-group-item').removeClass('active'); $(this).addClass('active');
        currentResult = $(this).data('result-name');
        $('#download-json-btn, #download-csv-btn, #compare-btn').prop('disabled', false);
        $('#result-title').text(`Result: ${currentResult}`);
        loadResultData(currentResult);
        window.location.hash = currentResult;
    });
    $('#tab-overview, #tab-charts, #tab-data').click(function() {
        $('.btn-group .btn').removeClass('active'); $(this).addClass('active');
        $('.result-tab-content').hide();
        const tab = $(this).attr('id').replace('tab-', '');
        $(`#${tab}-content`).show();
        if (tab === 'charts' && resultData) {
            setTimeout(() => { charts.gridEnergyChart?.update(); charts.batteryEnergyChart?.update(); charts.costsChart?.update(); }, 50);
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

    // Load and display result data
    function loadResultData(name) {
        // Reset UI and show loading
        $('#placeholder-message').hide();
        $('.result-tab-content').hide();
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
            ['Time',      ts.time]
        ];
        $('#config-table').empty();
        configRows.forEach(([k, v]) =>
            $('#config-table').append(`<tr><th>${k}</th><td>${v}</td></tr>`)
        );

        // ─── Summary table ───────────────────────────────────────────────────
        const summaryRows = [
            ['Total Cost',            formatNumber(r.total_cost)],
            ['Capacity Cost',         formatNumber(r.capacity_cost)],
            ['Connection Cost',       formatNumber(r.connection_cost)],         
            ['Transformer Cost',      formatNumber(r.transformer_cost)],
            ['Battery Cost',          formatNumber(r.battery_cost)],
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

        // Key metrics
        $('#metric-peak-power').text(r.max_grid_load.toFixed(2));
        const totalEnergy = r.grid_energy.reduce((sum, val) => sum + val, 0);
        $('#metric-total-energy').text(totalEnergy.toFixed(2));
        $('#metric-total-cost').text(r.total_cost.toFixed(2));

        // Battery metrics
        if (r.battery_capacity > 0) {
            $('#battery-metrics-row').removeClass('d-none');
            $('#metric-battery-capacity').text(r.battery_capacity.toFixed(2));
            $('#metric-battery-peak-power').text((Math.max(...r.grid_energy) - r.max_grid_load).toFixed(2));
            $('#metric-battery-savings').text((r.capacity_cost - r.battery_cost).toFixed(2));
        } else {
            $('#battery-metrics-row').addClass('d-none');
        }

        // Infrastructure tables
        $('#infrastructure-distance-table').empty().append(
            `<tr><th>Transmission Distance</th><td>${r.transmission_distance.toFixed(2)}</td></tr>
             <tr><th>Distribution Distance</th><td>${r.distribution_distance.toFixed(2)}</td></tr>`
        );
        $('#infrastructure-transformer-table').empty().append(
            `<tr><th>Transformer Capacity</th><td>${r.transformer_capacity}</td></tr>
             <tr><th>Description</th><td>${r.transformer_description}</td></tr>`
        );

        // Charger summary
        $('#charger-summary-table').empty();
        [['MCS_count','MCS'],['HPC_count','HPC'],['NCS_count','NCS']].forEach(([key,label]) => {
            if (r[key] !== undefined) {
                $('#charger-summary-table').append(`<tr><td>${label}</td><td>${r[key]}</td><td>-</td><td>-</td></tr>`);
            }
        });

        $('#overview-content').removeClass('d-none').show();
    }

    // Initialize
    refreshResultsList();
});