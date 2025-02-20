function createButton(type, onClick) {
    let iconName = '';
    if (type === 'copy') {
        iconName = 'copy-outline';
    } else if (type === 'download') {
        iconName = 'add-outline';
    }
    return `<ion-icon name="${iconName}" onclick="${onClick}"></ion-icon>`;
}

function copyToClipboard(text) {
    if (navigator.clipboard && navigator.clipboard.writeText) {
      navigator.clipboard.writeText(text)
        .then(() => console.log('Copied to clipboard'))
        .catch(err => console.error('Copy error:', err));
    } else {
      const textarea = document.createElement('textarea');
      textarea.value = text;
      document.body.appendChild(textarea);
      textarea.select();
      try {
        document.execCommand('copy');
        console.log('Copied to clipboard');
      } catch (err) {
        console.error('Fallback: Oops, unable to copy', err);
      }
      document.body.removeChild(textarea);
    }
  }

function capitalizeFirstLetter(string) {
    return string ? string.charAt(0).toUpperCase() + string.slice(1) : '';
}

function formatServiceName(service) {
    return service ? service.replace('_', ' ').toUpperCase() : '';
}
