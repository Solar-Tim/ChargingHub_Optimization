// Map page JavaScript
$(document).ready(function() {
    console.log('Map page script loaded');
    const apiBase = window.location.origin;
    let mapItems = []; // Store all map items
    let filteredMapItems = []; // Items filtered by search
    const ITEMS_PER_PAGE = 10; // Number of items to show per page
    let currentPage = 1; // Current page of results
    let selectedMap = null; // Currently selected map

    // Function to display a specific page of maps
    function displayMapsPage(page) {
        if (filteredMapItems.length === 0) return;
        
        // Calculate start and end indices
        const startIndex = (page - 1) * ITEMS_PER_PAGE;
        const endIndex = Math.min(startIndex + ITEMS_PER_PAGE, filteredMapItems.length);
        
        // Hide all items first
        mapItems.forEach(item => {
            item.element.addClass('d-none');
        });
        
        // Show only items for the current page
        for (let i = startIndex; i < endIndex; i++) {
            filteredMapItems[i].element.removeClass('d-none');
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
        $('#map-pagination-controls').remove();
        
        // If no items or all items fit on one page, don't show pagination
        if (filteredMapItems.length <= ITEMS_PER_PAGE) return;
        
        // Calculate total pages
        const totalPages = Math.ceil(filteredMapItems.length / ITEMS_PER_PAGE);
        
        // Create pagination controls
        let paginationHTML = `
            <div id="map-pagination-controls" class="d-flex justify-content-between align-items-center mt-2 mb-2">
                <button class="btn btn-sm btn-outline-secondary" id="map-prev-page" ${currentPage === 1 ? 'disabled' : ''}>
                    <i class="fas fa-chevron-left"></i>
                </button>
                <span class="text-muted">Page ${currentPage} of ${totalPages}</span>
                <button class="btn btn-sm btn-outline-secondary" id="map-next-page" ${currentPage === totalPages ? 'disabled' : ''}>
                    <i class="fas fa-chevron-right"></i>
                </button>
            </div>
        `;
        
        // Add pagination after map list container
        $('.map-results-container').after(paginationHTML);
        
        // Add event handlers
        $('#map-prev-page').click(() => {
            if (currentPage > 1) {
                displayMapsPage(currentPage - 1);
            }
        });
        
        $('#map-next-page').click(() => {
            if (currentPage < totalPages) {
                displayMapsPage(currentPage + 1);
            }
        });
    }

    // Function to check if the results container needs a scroll indicator
    function updateScrollIndicator() {
        const container = $('.map-results-container');
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
        const query = $('#search-maps').val().toLowerCase().trim();
        
        // Reset pagination to first page
        currentPage = 1;
        
        // Clear the no-results message
        $('#map-list').find('#no-search-results').remove();
        
        if (!query) {
            // If no search query, include all items
            filteredMapItems = [...mapItems];
        } else {
            // Filter items based on search query
            filteredMapItems = mapItems.filter(item => 
                item.searchText.includes(query)
            );
            
            // Display message if no results match search
            if (filteredMapItems.length === 0) {
                $('#map-list').append(
                    `<div id="no-search-results" class="text-center py-3 text-muted">
                        <i class="fas fa-search fa-lg mb-2"></i><br>
                        No maps matching "${query}"
                    </div>`
                );
            }
        }
        
        // Display first page of filtered items
        displayMapsPage(1);
    }    // Handle map item click
    function handleMapItemClick(e) {
        e.preventDefault();
        
        // Remove active class from all items
        $('.list-group-item').removeClass('active');
        
        // Add active class to clicked item
        $(this).addClass('active');
        
        // Get map name and type
        selectedMap = $(this).data('map-name');
        const mapType = $(this).find('.map-type').text();
        
        // Update map title
        $('#map-title').text(`${mapType} Map View`);
        
        // Load the map
        loadMap(selectedMap);
    }

    // Initialize map list from existing select options
    function initializeMapList() {
        const mapSelect = $('#map-select');
        const mapList = $('#map-list');
        
        mapItems = []; // Clear map items
        filteredMapItems = []; // Clear filtered items
        mapList.empty(); // Clear map list
        
        // Loop through each option in the select
        mapSelect.find('option').each(function() {
            const mapName = $(this).val();
            const mapText = $(this).text();
            let mapType = "Unknown";
            let mapTypeClass = "";
            
            // Determine map type based on text or value
            if (mapText.includes("Combined")) {
                mapType = "Combined";
                mapTypeClass = "map-type-combined";
            } else if (mapText.includes("Power Line")) {
                mapType = "Power Line";
                mapTypeClass = "map-type-power-line";
            } else if (mapText.includes("Substation")) {
                mapType = "Substation";
                mapTypeClass = "map-type-substation";
            }
            
            // Extract date if present
            let dateMatch = mapText.match(/\(([^)]+)\)/);
            let dateStr = dateMatch ? dateMatch[1] : "";
            
            // Create map item element
            const item = $(`
                <a href="#" class="list-group-item list-group-item-action" data-map-name="${mapName}">
                    <div class="d-flex justify-content-between">
                        <div class="map-info">
                            <span class="map-type ${mapTypeClass}">${mapType}</span><br>
                            <small class="text-muted text-truncate">${mapName}</small>
                        </div>
                        <small class="text-muted map-date">
                            ${dateStr}
                        </small>
                    </div>
                </a>
            `);
            
            // Add click handler
            item.click(handleMapItemClick);
            
            // Add to map list
            mapList.append(item);
            
            // Store item for filtering
            mapItems.push({
                element: item,
                searchText: `${mapType} ${mapName} ${dateStr}`.toLowerCase()
            });
        });
        
        // Initialize filtered items with all items
        filteredMapItems = [...mapItems];
        
        // Initialize pagination
        displayMapsPage(1);
          // If there are maps, select and load the first one
        if (mapItems.length > 0) {
            const firstItem = mapList.find('.list-group-item').first();
            // Select first map
            firstItem.addClass('active');
            selectedMap = firstItem.data('map-name');
            // Update map title
            const mapType = firstItem.find('.map-type').text();
            $('#map-title').text(`${mapType} Map View`);
            // Load the map
            loadMap(selectedMap);
        }
    }

    // Load map function (from existing code)
    function loadMap(mapName) {
        // Show loading indicator
        $('#map-frame').show();
        $('#no-map-message').hide();
        $('#map-loading').css('display', 'flex');
        
        if (mapName) {            // Set the iframe source to the map file
            const mapUrl = `${apiBase}/maps/${encodeURIComponent(mapName)}`;
            // Clear any previous src and handlers first
            const mapFrame = document.getElementById('map-frame');
            mapFrame.onload = null;
            mapFrame.onerror = null;
            mapFrame.src = '';
            
            // Set up new handlers
            mapFrame.onload = function() {
                console.log("Map loaded successfully");
                // When map loads, hide loading overlay completely
                $('#map-loading').hide();
                // Make sure iframe is visible and on top
                $(mapFrame).show().css('z-index', '20');
            };
            
            // Handle loading errors
            mapFrame.onerror = function() {
                console.error("Error loading map");
                $('#map-loading').hide();
                $('#no-map-message').css('display', 'flex');
                $('#no-map-message').html('<div class="text-center"><p>Error loading map file.</p></div>');
            };
            
            // Set the src after establishing handlers
            mapFrame.src = mapUrl;
            
            // Add a more aggressive fallback timeout
            setTimeout(function() {
                console.log("Timeout reached - forcing display of map");
                $('#map-loading').hide();
                $(mapFrame).show().css('z-index', '20');
            }, 2000); // 2 second fallback
        } else {
            // No map selected
            $('#map-loading').hide();
            $('#no-map-message').css('display', 'flex');
        }
    }    // Event handlers
    $('#refresh-maps').click(function() {
        // Refresh maps list (could make AJAX call to reload)
        initializeMapList();
    });
    
    // Run optimization button handler
    $('#run-optimization-btn').click(function() {
        window.location.href = '/configuration';
    });
    
    // Search input handler
    $('#search-maps').on('input', applySearchFilter);
    
    // Clear search button handler
    $('#clear-map-search').click(function() {
        $('#search-maps').val('').focus();
        applySearchFilter();
    });
    
    // Handle keyboard events in search input
    $('#search-maps').on('keyup', function(e) {
        // Clear search on Escape key
        if (e.key === 'Escape') {
            $(this).val('');
            applySearchFilter();
        }
    });
    
    // Add keyboard navigation for pagination (left/right arrow keys)
    $(document).keydown(function(e) {
        // Only when focus is not in search input
        if ($('#search-maps').is(':focus')) return;
        
        // Left arrow key - previous page
        if (e.key === 'ArrowLeft') {
            $('#map-prev-page:not([disabled])').click();
        }
        // Right arrow key - next page
        else if (e.key === 'ArrowRight') {
            $('#map-next-page:not([disabled])').click();
        }
    });
    
    // Add scroll event handler for the map results container
    $(document).on('scroll', '.map-results-container', function() {
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

    // Initialize the list (after a brief delay to ensure DOM is ready)
    setTimeout(initializeMapList, 100);
});
