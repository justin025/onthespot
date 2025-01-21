document.addEventListener('DOMContentLoaded', async () => {
    try {
        const response = await fetch('https://api.github.com/repos/justin025/onthespot/releases/latest');
        const release = await response.json();
        const asset = release.assets.find(a => a.name.endsWith('.exe') && (a.name.includes('x86') || a.name.includes('64')));
        if (asset) document.getElementById('download').href = asset.browser_download_url;
    } catch (error) {
        console.error('Error fetching the latest release:', error);
    }
});