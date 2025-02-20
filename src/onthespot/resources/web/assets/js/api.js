$(document).ready(() => {
    const downloadQueueContainer = $('#download-queue');

    // Handle search form submission
    $('#search').on('submit', (event) => {
        event.preventDefault(); // Prevent page reload
        const query = $('#search-bar').val().trim(); // Get the search query
        if (query === '') {
            console.error('The search field is empty.');
            return;
        }
        console.log(`Searching for: ${query}`);
        performSearch(query);
    });

    // Perform the search
    function performSearch(query) {
        $.ajax({
            url: `/search_results?q=${encodeURIComponent(query)}`,
            method: 'GET',
            success: (data) => {
                console.log('Search results:', data);
                renderSearchResults(data);
            },
            error: (xhr) => {
                console.error('Error during search:', xhr.statusText);
            }
        });
    }

    // Render search results in the UI
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
            // Build the thumbnail cell if thumbnails are enabled
            const showThumb = window.config && window.config.show_search_thumbnails;
            const thumbnailHtml = showThumb && item.item_thumbnail_url
                ? `<div class="thumbnail">
                        <img src="${item.item_thumbnail_url}" style="width:${window.config.thumbnail_size}px; height:${window.config.thumbnail_size}px;" alt="${item.item_name || 'Thumbnail'}">
                   </div>`
                : '';

            // Build the name, by, type, and service cells
            const nameHtml = `<div class="name">${item.item_name || 'Unknown Name'}</div>`;
            const byHtml = `<div class="by hide-on-mobile">${item.item_by || 'Unknown Artist'}</div>`;
            const typeHtml = `<div class="type">${capitalizeFirstLetter(item.item_type)}</div>`;
            const serviceHtml = item.item_service
                ? `<div class="service">
                        <img src="assets/img/icons/${item.item_service}.png" style="width:20px; height:20px;" alt="${item.item_service || 'Service'}">
                        <span class="hide-on-mobile">${formatServiceName(item.item_service)}</span>
                   </div>`
                : '';

            // Build the action cell with a copy and download button
            const actionsHtml = `<div class="action">
                ${createButton('copy', `copyToClipboard('${item.item_url}')`)}
                ${createButton('download', `handleDownload('${item.item_id}')`)}
            </div>`;

            // Assemble the row. Note that we do not include a status cell here.
            const row = $(`
                <div class="row">
                    ${thumbnailHtml}
                    ${nameHtml}
                    ${byHtml}
                    ${typeHtml}
                    ${serviceHtml}
                    ${actionsHtml}
                </div>
            `);
            $searchResults.append(row);
        });
    }

    // The rest of your download queue, login, etc. code remains unchanged.
    // For example, fetching the download queue:
    function fetchDownloadQueue() {
        $.ajax({
            url: '/api/download_queue',
            method: 'GET',
            contentType: 'application/json',
            success: (response) => {
                if (!response.success || !response.data) {
                    downloadQueueContainer.html('<div class="error">Unexpected data received from the API.</div>');
                    return;
                }
                renderDownloadQueue(response.data);
            },
            error: (xhr) => {
                console.error('Error fetching the download queue:', xhr.statusText);
            }
        });
    }

    // Render download queue (kept as before)
    function renderDownloadQueue(queueData) {
        downloadQueueContainer.empty();
        if (!queueData.length) {
            downloadQueueContainer.append('<div class="empty-message">The download queue is empty.</div>');
            return;
        }
        queueData.forEach((item) => {
            const row = $(`
                <div class="row">
                    <div class="localId">${item.local_id}</div>
                    <div class="thumbnail">
                        <img src="${item.item_thumbnail || 'https://placehold.co/50x50'}" alt="${item.item_name || 'Thumbnail'}">
                    </div>
                    <div class="name">${item.item_name || 'Unknown Name'}</div>
                    <div class="by">${item.item_by || 'Unknown Artist'}</div>
                    <div class="service">
                        <img src="assets/img/icons/${item.item_service || 'unknown'}.png" alt="${item.item_service || 'Service'}">
                    </div>
                    <div class="status">${item.item_status || 'Unknown Status'}</div>
                    <div class="action"></div>
                </div>
            `);
            const actions = row.find('.action');
            actions.append(`<ion-icon name="arrow-down-circle-outline" data-action="download" data-id="${item.local_id}"></ion-icon>`);
            if (item.item_status === 'Failed') {
                actions.append(`<ion-icon name="reload-outline" data-action="retry" data-id="${item.local_id}"></ion-icon>`);
            }
            if (['Waiting', 'Downloading'].includes(item.item_status)) {
                actions.append(`<ion-icon name="close-circle-outline" data-action="cancel" data-id="${item.local_id}"></ion-icon>`);
            }
            downloadQueueContainer.append(row);
        });
    }

    // Event delegation for download queue action icons
    downloadQueueContainer.on('click', 'ion-icon', (event) => {
        const action = $(event.target).data('action');
        const localId = $(event.target).data('id');
        if (action === 'download') handleDownload(localId);
        if (action === 'retry') handleRetry(localId);
        if (action === 'cancel') handleCancel(localId);
    });

    // Action handlers for download queue items
    function handleDownload(id) {
        $.ajax({
            url: `/download/${id}`,
            method: 'GET',
            success: () => console.log(`Download started for ${id}`),
            error: (xhr) => console.error(`Error downloading ${id}:`, xhr.statusText)
        });
    }
    function handleRetry(id) {
        $.ajax({
            url: `/retry/${id}`,
            method: 'POST',
            success: () => {
                console.log(`Retry started for ${id}`);
                fetchDownloadQueue();
            },
            error: (xhr) => console.error(`Error retrying ${id}:`, xhr.statusText)
        });
    }
    function handleCancel(id) {
        $.ajax({
            url: `/cancel/${id}`,
            method: 'POST',
            success: () => {
                console.log(`Cancellation successful for ${id}`);
                fetchDownloadQueue();
            },
            error: (xhr) => console.error(`Error canceling ${id}:`, xhr.statusText)
        });
    }

    window.handleDownload = handleDownload;
    window.handleRetry = handleRetry;
    window.handleCancel = handleCancel;

    // Handle login form submission
    $('#loginform').on('submit', (event) => {
        event.preventDefault();
        const username = $('#username').val();
        const password = $('#password').val();
        $.ajax({
            url: '/login',
            method: 'POST',
            contentType: 'application/json',
            data: JSON.stringify({ username, password }),
            success: (data) => {
                if (data.success) {
                    console.log(data.message);
                    window.location.href = data.next || '/';
                } else {
                    console.error(data.message);
                    alert(data.message);
                }
            },
            error: (xhr) => {
                console.error('Error logging in:', xhr.statusText);
                alert('Login failed. Please try again.');
            }
        });
    });

    // Fetch the initial download queue and refresh it every 5 seconds
    fetchDownloadQueue();
    setInterval(fetchDownloadQueue, 5000);
});
