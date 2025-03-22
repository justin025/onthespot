$(document).ready(() => {
    const downloadQueueContainer = $('#download-queue');

    $('#search').on('submit', (e) => {
        e.preventDefault();
        const query = $('#search-bar').val().trim();
        if (!query) return;
        performSearch(query);
    });

    function performSearch(query) {
        $.ajax({
            url: `/search_results?q=${encodeURIComponent(query)}`,
            method: 'GET',
            success: renderSearchResults,
            error: (xhr) => console.error('Search error:', xhr.statusText)
        });
    }

    function renderSearchResults(results) {
        let $searchResults = $('#search-results');
        if (!$searchResults.length) {
            $searchResults = $('<div id="search-results"></div>');
            $('#search-container').append($searchResults);
        }
        $searchResults.empty();
        if (!results.length) {
            $searchResults.append('<div class="empty-message">No results found.</div>');
            return;
        }
        results.forEach((item) => {
            const showThumb = window.config && window.config.show_search_thumbnails;
            const thumbnailHtml = showThumb && item.item_thumbnail_url
                ? `<div class="thumbnail"><img src="${item.item_thumbnail_url}" style="width:${window.config.thumbnail_size}px; height:${window.config.thumbnail_size}px;" alt="${item.item_name || 'Thumbnail'}"></div>`
                : '';
            const nameHtml = `<div class="name">${item.item_name || 'Unknown Name'}</div>`;
            const byHtml = `<div class="by">${item.item_by || 'Unknown Artist'}</div>`;
            const typeHtml = `<div class="type">${capitalizeFirstLetter(item.item_type)}</div>`;
            const serviceHtml = item.item_service
                ? `<div class="service"><img src="assets/img/icons/${item.item_service}.png" style="width:20px; height:20px;" alt="${item.item_service || 'Service'}"><span class="hide-on-mobile">${formatServiceName(item.item_service)}</span></div>`
                : '';
            const actionsHtml = `<div class="action">
                ${createButton('copy', `copyToClipboard('${item.item_url}')`)}
                ${createButton('download', `handleDownload('${item.item_url}')`)}
            </div>`;
            const row = $(`<div class="row">${thumbnailHtml}${nameHtml}${byHtml}${typeHtml}${serviceHtml}${actionsHtml}</div>`);
            $searchResults.append(row);
        });
    }

    function fetchDownloadQueue() {
        $.ajax({
            url: '/api/download_queue',
            method: 'GET',
            contentType: 'application/json',
            success: (response) => {
                if (!response.success || typeof response.data !== 'object') {
                    downloadQueueContainer.html('<div class="error">Unexpected data received from the API.</div>');
                    return;
                }
                renderDownloadQueue(response.data);
            },
            error: (xhr) => console.error('Download queue error:', xhr.statusText)
        });
    }

    function renderDownloadQueue(queueData) {
        downloadQueueContainer.empty();
        const seen = {};
        const keys = Object.keys(queueData);
        if (keys.length === 0) {
            downloadQueueContainer.append('<div class="empty-message">The download queue is empty.</div>');
            return;
        }
        keys.forEach((key) => {
            const item = queueData[key];
            if (item.item_url && seen[item.item_url]) return;
            if (item.item_url) seen[item.item_url] = true;
            const row = $(`
                <div class="row" data-id="${item.local_id}" data-status="${item.item_status}">
                    <div class="localId">${item.local_id}</div>
                    <div class="thumbnail"><img src="${item.item_thumbnail || 'https://placehold.co/50x50'}" alt="${item.item_name || 'Thumbnail'}"></div>
                    <div class="name">${item.item_name || 'Unknown Name'}</div>
                    <div class="by">${item.item_by || 'Unknown Artist'}</div>
                    <div class="service"><img src="assets/img/icons/${item.item_service || 'unknown'}.png" alt="${item.item_service || 'Service'}"></div>
                    <div class="status">${item.item_status || 'Unknown Status'}</div>
                    <div class="action">
                        ${(['Downloaded', 'Already Exists'].includes(item.item_status))
                            ? `<ion-icon name="play-outline" data-action="open" data-id="${item.local_id}"></ion-icon>`
                            : `<ion-icon name="arrow-down-circle-outline" data-action="download" data-id="${item.local_id}"></ion-icon>`}
                        ${item.item_status === 'Failed' ? `<ion-icon name="reload-outline" data-action="retry" data-id="${item.local_id}"></ion-icon>` : ''}
                        ${(['Waiting', 'Downloading'].includes(item.item_status)) ? `<ion-icon name="close-circle-outline" data-action="cancel" data-id="${item.local_id}"></ion-icon>` : ''}
                    </div>
                </div>
            `);
            downloadQueueContainer.append(row);
        });
    }

    downloadQueueContainer.on('click', 'ion-icon', (e) => {
        e.stopPropagation();
        const action = $(e.target).data('action');
        const identifier = $(e.target).data('id');
        if (action === 'download') handleDownload(identifier);
        if (action === 'open') handleOpen(identifier);
        if (action === 'retry') handleRetry(identifier);
        if (action === 'cancel') handleCancel(identifier);
    });

    downloadQueueContainer.on('click', '.row', function(e) {
        if ($(e.target).closest('ion-icon').length) return;
        const id = $(this).data('id');
        const status = $(this).data('status');
        if (['Downloaded', 'Already Exists'].includes(status))
            handleOpen(id);
        else
            handleDownload(id);
    });

    function handleDownload(identifier) {
        $.ajax({
            url: `/download/${encodeURIComponent(identifier)}`,
            method: 'POST',
            success: () => {
                console.log(`Download initiated for ${identifier}`);
                $('#notification').removeClass('hidden');
                setTimeout(() => { $('#notification').addClass('hidden'); }, 3000);
                fetchDownloadQueue();
            },
            error: (xhr) => console.error(`Error initiating download for ${identifier}:`, xhr.statusText)
        });
    }

    function handleOpen(id) {
        window.open(`/download/${id}`, '_blank');
    }

    function handleRetry(id) {
        $.ajax({
            url: `/retry/${id}`,
            method: 'POST',
            success: () => { console.log(`Retry started for ${id}`); fetchDownloadQueue(); },
            error: (xhr) => console.error(`Error retrying ${id}:`, xhr.statusText)
        });
    }

    function handleCancel(id) {
        $.ajax({
            url: `/cancel/${id}`,
            method: 'POST',
            success: () => { console.log(`Cancellation successful for ${id}`); fetchDownloadQueue(); },
            error: (xhr) => console.error(`Error canceling ${id}:`, xhr.statusText)
        });
    }

    window.handleDownload = handleDownload;
    window.handleOpen = handleOpen;
    window.handleRetry = handleRetry;
    window.handleCancel = handleCancel;

    $('#loginform').on('submit', (e) => {
        e.preventDefault();
        const username = $('#username').val();
        const password = $('#password').val();
        $.ajax({
            url: '/login',
            method: 'POST',
            contentType: 'application/json',
            data: JSON.stringify({ username, password }),
            success: (data) => { if (data.success) window.location.href = data.next || '/'; else alert(data.message); },
            error: (xhr) => alert('Login failed. Please try again.')
        });
    });

    fetchDownloadQueue();
    setInterval(fetchDownloadQueue, 5000);
});
