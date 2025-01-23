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

        // Perform the search (replace with your actual API or logic)
        console.log(`Searching for: ${query}`);
        performSearch(query);
    });

    // Perform the search (example implementation)
    function performSearch(query) {
        $.ajax({
            url: `/search_results?q=${encodeURIComponent(query)}`,
            method: 'GET',
            success: (data) => {
                console.log('Search results:', data);
                // TODO: Render search results in the UI
            },
            error: (xhr) => {
                console.error('Error during search:', xhr.statusText);
            }
        });
    }

    // Fetch the download queue from the API
    function fetchDownloadQueue() {
        downloadQueueContainer.html('<div class="loading">Loading...</div>'); // Display a loading indicator

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
                downloadQueueContainer.html('<div class="error">Failed to load the download queue.</div>');
            }
        });
    }

    // Render the download queue in the UI
    function renderDownloadQueue(queueData) {
        downloadQueueContainer.empty(); // Clear the container

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

    // Handle click actions (download, retry, cancel)
    downloadQueueContainer.on('click', 'ion-icon', (event) => {
        const action = $(event.target).data('action');
        const localId = $(event.target).data('id');

        if (action === 'download') handleDownload(localId);
        if (action === 'retry') handleRetry(localId);
        if (action === 'cancel') handleCancel(localId);
    });

    // Handle downloading an item
    function handleDownload(localId) {
        $.ajax({
            url: `/download/${localId}`,
            method: 'GET',
            success: () => console.log(`Download started for ${localId}`),
            error: (xhr) => console.error(`Error downloading ${localId}:`, xhr.statusText)
        });
    }

    // Handle retrying a failed download
    function handleRetry(localId) {
        $.ajax({
            url: `/retry/${localId}`,
            method: 'POST',
            success: () => {
                console.log(`Retry started for ${localId}`);
                fetchDownloadQueue(); // Refresh the queue
            },
            error: (xhr) => console.error(`Error retrying ${localId}:`, xhr.statusText)
        });
    }

    // Handle canceling a download
    function handleCancel(localId) {
        $.ajax({
            url: `/cancel/${localId}`,
            method: 'POST',
            success: () => {
                console.log(`Cancellation successful for ${localId}`);
                fetchDownloadQueue(); // Refresh the queue
            },
            error: (xhr) => console.error(`Error canceling ${localId}:`, xhr.statusText)
        });
    }

    // Check authentication
    function checkAuthentication() {
        $.ajax({
            url: '/api/download_queue',
            method: 'GET',
            success: () => console.log('User is authenticated.'),
            error: (xhr) => {
                if (xhr.status === 401) $('#login-container').addClass('active');
                else console.error('Authentication check failed:', xhr.statusText);
            }
        });
    }

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
                    window.location.href = data.next || '/'; // Redirect after login
                } else {
                    console.error(data.message);
                    alert(data.message); // Show error
                }
            },
            error: (xhr) => {
                console.error('Error logging in:', xhr.statusText);
                alert('Login failed. Please try again.');
            }
        });
    });

    // Fetch the initial download queue
    fetchDownloadQueue();

    // Refresh the download queue every 5 seconds
    setInterval(fetchDownloadQueue, 5000);
});
