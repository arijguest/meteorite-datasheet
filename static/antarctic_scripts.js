document.addEventListener('DOMContentLoaded', function() {
    // Initialize DataTable
    $('#meteoriteTable').DataTable({
        serverSide: true,
        processing: true,
        ajax: {
            url: '/data',
            type: 'GET',
            error: function(xhr, error, code) {
                console.error('Error fetching data:', error);
            }
        },
        columns: [
            { data: 'name' },
            { data: 'recclass' },
            { data: 'recclass_clean' },
            { data: 'mass_formatted' },
            { data: 'year_formatted' },
            { data: 'reclat' },
            { data: 'reclong' },
            { data: 'fall' }
        ],
        dom: '<"top"f>rt<"bottom"lp><"clear">',
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

    // Initialize Plotly charts
    Plotly.newPlot('time', {{ time_html|safe }});
    Plotly.newPlot('map', {{ map_html|safe }});
    Plotly.newPlot('heatmap', {{ heatmap_html|safe }});

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
    $(window).on('resize', function() {
        if (window.innerWidth <= 768) {
            $('.chart-container').addClass('mobile-view');
        } else {
            $('.chart-container').removeClass('mobile-view');
        }
    });

    // Generate Common Legend
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
});
