// Global Configuration
const CONFIG = {
    mapDefaults: {
        zoom: 1,
        center: { lat: 0, lon: 0 },
        style: 'carto-darkmatter'
    },
    dataTable: {
        pageLength: 25,
        lengthMenu: [[10, 25, 50, 100, -1], [10, 25, 50, 100, "All"]],
        order: [[3, 'desc']],
        responsive: true
    }
};

// Main Application Logic
class MeteoriteExplorer {
    constructor() {
        this.initializeDataTable();
        this.initializeMaps();
        this.initializeEventListeners();
        table.on('init.dt', function () {
            // Hide the loading spinner after data has been loaded
            $('.loading').fadeOut('slow');
            $('#main-content').fadeIn('slow');
        });
    }

    initializeDataTable() {
        let table = $('#meteoriteTable').DataTable({
            serverSide: true,
            processing: true,
            ajax: {
                url: '/data',
                type: 'GET',
                error: function (xhr, error, code) {
                    ErrorHandler.handleError(error, 'DataTable AJAX');
                }
            },
            columns: [
                { data: 'name' },
                { data: 'mass' },
                { data: 'year' },
                { data: 'recclass' },
                { data: 'reclat' },
                { data: 'reclong' }
            ],
            dom: '<"top"<"row"<"col-md-6"f><"col-md-6"B>>>rt<"bottom"<"row"<"col-md-6"l><"col-md-6"p>>>',
            buttons: [
                {
                    extend: 'collection',
                    text: '<i class="fas fa-download"></i> Export',
                    buttons: [
                        {
                            extend: 'csv',
                            text: '<i class="fas fa-file-csv"></i> CSV',
                            className: 'export-button'
                        },
                        {
                            extend: 'excel',
                            text: '<i class="fas fa-file-excel"></i> Excel',
                            className: 'export-button'
                        },
                        {
                            extend: 'pdf',
                            text: '<i class="fas fa-file-pdf"></i> PDF',
                            className: 'export-button'
                        }
                    ]
                },
                {
                    text: '<i class="fas fa-print"></i> Print',
                    extend: 'print',
                    className: 'print-button'
                }
            ],
            language: {
                search: "<i class='fas fa-search'></i> Search Records:",
                lengthMenu: "Show _MENU_ entries per page",
                info: "Showing _START_ to _END_ of _TOTAL_ meteorites",
                paginate: {
                    first: '<i class="fas fa-angle-double-left"></i>',
                    last: '<i class="fas fa-angle-double-right"></i>',
                    next: '<i class="fas fa-angle-right"></i>',
                    previous: '<i class="fas fa-angle-left"></i>'
                },
                zeroRecords: "No matching meteorites found",
                emptyTable: "No meteorite data available"
            }
        });
    }
    initializeMaps() {
        setTimeout(() => {
            try {
                const mapConfig = {
                    'mapbox.zoom': CONFIG.mapDefaults.zoom,
                    'mapbox.center.lat': CONFIG.mapDefaults.center.lat,
                    'mapbox.center.lon': CONFIG.mapDefaults.center.lon,
                    'mapbox.style': CONFIG.mapDefaults.style
                };
    
                if (document.getElementById('map')) {
                    Plotly.relayout('map', mapConfig);
                }
                if (document.getElementById('heatmap')) {
                    Plotly.relayout('heatmap', mapConfig);
                }
            } catch (error) {
                console.error('Error initializing maps:', error);
            }
        }, 1000);
    }    

    initializeEventListeners() {
        // Smooth scrolling for anchor links
        $('a[href*="#"]').on('click', function(e) {
            e.preventDefault();
            const target = $($(this).attr('href'));
            if (target.length) {
                $('html, body').animate({
                    scrollTop: target.offset().top - 70
                }, 500, 'linear');
            }
        });

        // Chart container hover effects
        $('.chart-container').hover(
            function() { $(this).addClass('chart-hover'); },
            function() { $(this).removeClass('chart-hover'); }
        );

        // Window resize handler
        $(window).on('resize', this.handleResize.bind(this));
    }

    handleResize() {
        if (window.innerWidth <= 768) {
            $('.chart-container').addClass('mobile-view');
        } else {
            $('.chart-container').removeClass('mobile-view');
        }
    }
}

// Error Handler
class ErrorHandler {
    static handleError(error, context) {
        console.error(`Error in ${context}:`, error);
        // Add error notification system here if needed
    }
}

// Initialize Application
$(document).ready(() => {
    try {
        window.meteoriteExplorer = new MeteoriteExplorer();
    } catch (error) {
        ErrorHandler.handleError(error, 'Application Initialization');
    }
    generateCommonLegend();
});

// Generate Common Legend
function generateCommonLegend() {
    const COLORS = {
        'L-type': '#FF6B6B',
        'H-type': '#4ECDC4',
        'LL-type': '#45B7D1',
        'Carbonaceous': '#96CEB4',
        'Enstatite': '#FFEEAD',
        'Achondrite': '#D4A5A5',
        'Iron': '#9A8C98',
        'Mesosiderite': '#C9ADA7',
        'Martian': '#F08080',
        'Lunar': '#87CEEB',
        'Pallasite': '#DDA0DD',
        'Unknown': '#808080',
        'Other': '#FFFFFF'
    };

    const legendContainer = $('#commonLegend');

    for (const [classification, color] of Object.entries(COLORS)) {
        const legendItem = $(`
            <div class="legend-item">
                <div class="legend-color-box" style="background-color: ${color};"></div>
                <span>${classification}</span>
            </div>
        `);
        legendContainer.append(legendItem);
    }
}

// Export functionality for testing
if (typeof module !== 'undefined' && module.exports) {
    module.exports = {
        MeteoriteExplorer,
        ErrorHandler,
        CONFIG
    };
}
