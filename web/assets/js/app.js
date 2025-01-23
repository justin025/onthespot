$(document).ready(function () {
    const currentTitle = document.title;
    document.title = `OnTheSpot - ${currentTitle}`;
    $('#search-bar').focus();

    $(document).on('click keydown', e => {
        if (e.key === 'Escape' || $(e.target).is('ion-icon[name="close-outline"]')) {
            $('ion-icon[name="close-outline"]').parent().removeClass('active');
        }
    });

    $(document).on('click keydown', e => {
        if (e.key === 'Escape' || $(e.target).is('ion-icon[name="close-outline"]')) {
            $('#search-container').addClass('download-queue');
        }
    });

    $(document).on('click keydown', '#search-button', function (e) {
        if ((e.type === 'click' || (e.type === 'keydown' && e.key === 'Enter')) && $('#search-bar').val().trim() !== '') {
            $('#search-container').addClass('download-queue');
        }
    });

    $(document).on('keydown', e => {
        if (e.key === 's') {
            e.preventDefault();
            $('#search-bar').focus();
        }
    });

    $('#settingsButton').click(function () {
        $(`#settings-container`).addClass('active');
    });

    $('#login-button').click(function () {
        $(`#login-container`).addClass('active');
    });

    $('#about-button').click(function () {
        $(`#about-container`).addClass('active');
    });

    $('#settings-button').click(function () {
        $(`#settings-container`).addClass('active');
    });
});