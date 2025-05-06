/**
 * Location Map Handler
 * Manages the interactive map for location selection in configuration
 */

// Global map variable
let locationMap = null;
let markerLayer = null;
let bufferLayer = null;

// Initialize map when the location tab is activated
document.addEventListener('DOMContentLoaded', function() {
    // Check if location tab exists
    const locationTab = document.getElementById('location-tab');
    if (!locationTab) return;

    // Initialize map when the location tab is clicked
    locationTab.addEventListener('click', initMap);
    
    // Also initialize if the tab is already active on page load
    if (locationTab.classList.contains('active')) {
        initMap();
    }
});

function initMap() {
    // Only initialize once
    if (locationMap !== null) return;
    
    // Hide loading indicator
    const loadingElement = document.getElementById('map-loading');
    if (loadingElement) {
        loadingElement.style.display = 'none';
    }
    
    // Get initial coordinates from form
    const longitude = parseFloat(document.getElementById('LONGITUDE').value) || 10.0;
    const latitude = parseFloat(document.getElementById('LATITUDE').value) || 51.0;
    const bufferRadius = parseFloat(document.getElementById('BUFFER_RADIUS').value) || 100;
    
    // Initialize the map
    locationMap = L.map('location-map').setView([latitude, longitude], 15);
    
    // Add OpenStreetMap tile layer
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
        maxZoom: 19
    }).addTo(locationMap);
    
    // Add marker layer group
    markerLayer = L.layerGroup().addTo(locationMap);
    
    // Add buffer layer group
    bufferLayer = L.layerGroup().addTo(locationMap);
    
    // Add a marker at the initial position
    updateMapMarker(latitude, longitude, bufferRadius);
    
    // Add click event to the map
    locationMap.on('click', function(e) {
        const lat = e.latlng.lat;
        const lng = e.latlng.lng;
        
        // Update form fields
        document.getElementById('LATITUDE').value = lat.toFixed(6);
        document.getElementById('LONGITUDE').value = lng.toFixed(6);
        
        // Update marker on map
        const bufferRadius = parseFloat(document.getElementById('BUFFER_RADIUS').value) || 100;
        updateMapMarker(lat, lng, bufferRadius);
    });
    
    // Add search control
    const geocoder = L.Control.geocoder({
        defaultMarkGeocode: false
    }).addTo(locationMap);
    
    geocoder.on('markgeocode', function(e) {
        const lat = e.geocode.center.lat;
        const lng = e.geocode.center.lng;
        
        // Update form fields
        document.getElementById('LATITUDE').value = lat.toFixed(6);
        document.getElementById('LONGITUDE').value = lng.toFixed(6);
        
        // Update marker and view
        const bufferRadius = parseFloat(document.getElementById('BUFFER_RADIUS').value) || 100;
        updateMapMarker(lat, lng, bufferRadius);
        locationMap.setView([lat, lng], 15);
    });
    
    // Connect search button to geocoder
    document.getElementById('search-btn').addEventListener('click', function() {
        const searchText = document.getElementById('location-search').value;
        if (searchText) {
            geocoder.geocode(searchText);
        }
    });
    
    // Allow pressing Enter in search box
    document.getElementById('location-search').addEventListener('keypress', function(e) {
        if (e.key === 'Enter') {
            document.getElementById('search-btn').click();
        }
    });
    
    // Reset view button
    document.getElementById('reset-view-btn').addEventListener('click', function() {
        locationMap.setView([latitude, longitude], 15);
    });
    
    // Update map when buffer radius changes
    document.getElementById('BUFFER_RADIUS').addEventListener('change', function() {
        const lat = parseFloat(document.getElementById('LATITUDE').value);
        const lng = parseFloat(document.getElementById('LONGITUDE').value);
        const bufferRadius = parseFloat(this.value) || 100;
        updateMapMarker(lat, lng, bufferRadius);
    });
    
    // Update map when coordinates change via input fields
    document.getElementById('LATITUDE').addEventListener('change', updateMapFromInputs);
    document.getElementById('LONGITUDE').addEventListener('change', updateMapFromInputs);
    
    // Add buffer radius legend
    const legend = L.control({position: 'bottomright'});
    legend.onAdd = function() {
        const div = L.DomUtil.create('div', 'buffer-legend');
        div.innerHTML = '<strong>Buffer Radius</strong><br>' +
                       '<div style="background: rgba(255, 0, 0, 0.2); padding: 5px; border-radius: 5px;">' +
                       '<span id="buffer-radius-display">' + bufferRadius + ' meters</span></div>';
        return div;
    };
    legend.addTo(locationMap);
    
    // Fix the map size issue (sometimes Leaflet doesn't detect container size correctly)
    setTimeout(function() {
        locationMap.invalidateSize();
    }, 100);
}

function updateMapFromInputs() {
    const lat = parseFloat(document.getElementById('LATITUDE').value);
    const lng = parseFloat(document.getElementById('LONGITUDE').value);
    const bufferRadius = parseFloat(document.getElementById('BUFFER_RADIUS').value) || 100;
    
    if (!isNaN(lat) && !isNaN(lng)) {
        updateMapMarker(lat, lng, bufferRadius);
    }
}

function updateMapMarker(lat, lng, bufferRadius) {
    // Clear existing markers and buffers
    markerLayer.clearLayers();
    bufferLayer.clearLayers();
    
    // Add marker at position
    const marker = L.marker([lat, lng], {
        draggable: true
    }).addTo(markerLayer);
    
    // Update marker drag event
    marker.on('dragend', function(e) {
        const position = marker.getLatLng();
        document.getElementById('LATITUDE').value = position.lat.toFixed(6);
        document.getElementById('LONGITUDE').value = position.lng.toFixed(6);
        
        // Redraw buffer
        updateBuffer(position.lat, position.lng, bufferRadius);
    });
    
    // Add buffer zone
    updateBuffer(lat, lng, bufferRadius);
    
    // Update buffer radius display
    const bufferDisplay = document.getElementById('buffer-radius-display');
    if (bufferDisplay) {
        bufferDisplay.textContent = bufferRadius + ' meters';
    }
}

function updateBuffer(lat, lng, radius) {
    // Clear existing buffer
    bufferLayer.clearLayers();
    
    // Add buffer circle
    L.circle([lat, lng], {
        radius: radius,
        fill: true,
        fillColor: 'red',
        fillOpacity: 0.2,
        stroke: true,
        color: 'red',
        weight: 2
    }).addTo(bufferLayer);
}
