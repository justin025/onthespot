
document.addEventListener('DOMContentLoaded', async () => {
    try {
        const response = await fetch('https://api.github.com/repos/justin025/onthespot/releases/latest');
        const release = await response.json();

        const platform = navigator.platform.toLowerCase();
        let fileExtension = '';

        if (platform.includes('win')) {
            fileExtension = '.exe';
        } else if (platform.includes('mac')) {
            window.location.href = 'https://github.com/justin025/onthespot/releases/latest';
            return;
        } else if (platform.includes('linux')) {
            fileExtension = '.AppImage';
        } else {
            throw new Error('Unsupported platform');
        }

        const asset = release.assets.find(a => a.name.endsWith(fileExtension));
        if (asset) {
            document.getElementById('download').href = asset.browser_download_url;
        } else {
            console.error(`No file found for platform: ${platform}`);
        }
    } catch (error) {
        console.error('Error fetching the latest release:', error);
    }
});