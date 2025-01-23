document.addEventListener('DOMContentLoaded', () => {
    const downloadQueueContainer = document.querySelector('#download-queue');

    // Function to fetch the download queue data from the API
    async function fetchDownloadQueue() {
        try {
            const response = await fetch('/api/download_queue', {
                method: 'GET',
                headers: {
                    'Content-Type': 'application/json',
                },
            });

            if (!response.ok) {
                throw new Error(`API Error: ${response.status}`);
            }

            const queueData = await response.json();

            // Validate the data received
            if (!queueData || typeof queueData !== 'object') {
                throw new Error('Unexpected data received from the API');
            }

            // Update the UI with the queue data
            renderDownloadQueue(queueData);
        } catch (error) {
            console.error('Error fetching the download queue:', error.message);
        }
    }

    // Function to render the download queue in the UI
    function renderDownloadQueue(queueData) {
        // Clear the container before rendering new items
        downloadQueueContainer.innerHTML = '';

        Object.values(queueData).forEach(item => {
            // Create a row for each item
            const row = document.createElement('div');
            row.className = 'row';

            // Local ID
            const localId = document.createElement('div');
            localId.className = 'localId';
            localId.textContent = item.local_id;

            // Thumbnail
            const thumbnail = document.createElement('div');
            thumbnail.className = 'thumbnail';
            const img = document.createElement('img');
            img.src = item.item_thumbnail || 'https://placehold.co/50x50';
            img.alt = item.item_name || 'Thumbnail';
            thumbnail.appendChild(img);

            // Item name
            const name = document.createElement('div');
            name.className = 'name';
            name.textContent = item.item_name || 'Unknown Name';

            // Artist or creator
            const by = document.createElement('div');
            by.className = 'by';
            by.textContent = item.item_by || 'Unknown Artist';

            // Service (e.g., Spotify, YouTube)
            const service = document.createElement('div');
            service.className = 'service';
            const serviceImg = document.createElement('img');
            serviceImg.src = `assets/img/icons/${item.item_service || 'unknown'}.png`;
            serviceImg.alt = item.item_service || 'Service';
            service.appendChild(serviceImg);

            // Status
            const status = document.createElement('div');
            status.className = 'status';
            status.textContent = item.item_status || 'Unknown Status';

            // Action (e.g., download icon)
            const action = document.createElement('div');
            action.className = 'action';
            const actionIcon = document.createElement('ion-icon');
            actionIcon.name = 'arrow-down-circle-outline';
            action.appendChild(actionIcon);

            // Append all columns to the row
            row.appendChild(localId);
            row.appendChild(thumbnail);
            row.appendChild(name);
            row.appendChild(by);
            row.appendChild(service);
            row.appendChild(status);
            row.appendChild(action);

            // Append the row to the container
            downloadQueueContainer.appendChild(row);
        });
    }

    // Fetch the initial download queue data
    fetchDownloadQueue();

    // Refresh the download queue every 5 seconds
    setInterval(fetchDownloadQueue, 5000);
});
