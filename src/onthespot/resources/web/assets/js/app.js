$(document).ready(function () {
    const currentTitle = document.title;
    document.title = `OnTheSpot - ${currentTitle}`;
    $('#search-bar').focus();

    // Closing Menu
    $(document).on('click keydown', e => {
        if (e.key === 'Escape' || $(e.target).is('ion-icon[name="close-outline"]')) {
            $('ion-icon[name="close-outline"]').parent().removeClass('active');
            $('#search input').focus();
        }
    });

    // Confirm Search
    $(document).on('click keydown', '#search-button', function (e) {
        if ((e.type === 'click' || (e.type === 'keydown' && e.key === 'Enter')) && $('#search-bar').val().trim() !== '') {
            $('#search input').focus();
            $('#search-container').addClass('render-results');
            $('#search-results-container').addClass('active');
            $('#download-queue-button').addClass('active');
        }
    });

    // Open Search Results
    $(document).on('click', '#search-container.render-results', function (e) {
        e.stopPropagation();
        $('#download-queue-button').addClass('active');
        $('#search-results-container').addClass('active');
    });

    // Close Search Results
    $(document).on('click', function (e) {
        if ($(e.target).closest('#search-results, #search-button, #search-bar').length === 0) {
            // $('#search-container').removeClass('render-results'); // Moving searchbar back to the middle
            // $('#download-queue-button').removeClass('active');
            $('#search-results-container').removeClass('active');
        }
    });

    // Download Queue
    $('#download-queue-button').click(function () {
        $(`#download-queue-container`).css("opacity", '1');
        $('#search-results-container').removeClass('active');
    });

    $(document).on('keydown', e => {
        if (e.key === 's') {
            $('#search-bar').focus();
        }
    });

    $('#login-button').click(function () {
        $(`#login-container`).addClass('active');
    });

    $('#about-button').click(function () {
        $(`#about-container`).addClass('active');
    });

    $('#about-container').on('click', function (e) {
        if ($(e.target).closest('#about').length === 0) {
            $(this).removeClass('active');
        }
    });

    $('#settings-button').click(function () {
        $(`#settings-container`).addClass('active');
    });
});