// ---------- static/js/main.js ----------
const csrfToken = document.querySelector('meta[name="csrf-token"]')?.content;
const isLoggedIn = document.body.dataset.isLoggedIn === 'true';

function showErrorToast(message) {
  const toast = document.createElement('div');
  toast.className = 'alert alert-danger position-fixed top-0 end-0 m-3';
  toast.style.zIndex = '9999';
  toast.innerHTML = `
    <div class="d-flex">
      <div class="toast-body">${message}</div>
      <button type="button" class="btn-close me-2 m-auto" data-bs-dismiss="toast"></button>
    </div>
  `;
  document.body.appendChild(toast);
  setTimeout(() => toast.remove(), 5000);
}

async function startDownload() {
  if (!isLoggedIn) {
    showErrorToast('Please <a href="/login">log in</a> or <a href="/signup">sign up</a> to download.');
    return;
  }
  try {
    const urls = document.getElementById('urlInput').value.trim().split('\n').filter(Boolean);
    if (!urls.length) throw new Error('Please enter at least one URL');

    const format = document.getElementById('format').value;
    const resolution = document.getElementById('resolution').value;
    const directory = document.getElementById('directory').value || sessionStorage.getItem('lastDirectory') || 'downloads';

    sessionStorage.setItem('lastDirectory', directory);

    const progressArea = document.getElementById('progressArea');
    progressArea.innerHTML = '';
    progressArea.scrollIntoView({ behavior: 'smooth' });

    const BATCH_SIZE = 3;
    for (let i = 0; i < urls.length; i += BATCH_SIZE) {
      const batch = urls.slice(i, i + BATCH_SIZE);
      await Promise.all(batch.map(url => processSingleDownload(url, format, resolution, directory)));
    }
  } catch (error) {
    showErrorToast(error.message);
  }
}

// Helper function to get platform badge HTML
function getPlatformBadgeHTML(platform) {
  let badgeColor, platformText;
  
  switch(platform) {
    case 'tiktok':
      badgeColor = '#000000';
      platformText = '📱 TikTok';
      break;
    case 'instagram':
      badgeColor = '#E1306C';
      platformText = '📸 Instagram';
      break;
    case 'twitter':
      badgeColor = '#1DA1F2';
      platformText = '🐦 Twitter';
      break;
    default:
      badgeColor = '#FF0000';
      platformText = '▶️ YouTube';
  }
  
  return `<span class="badge rounded-pill me-2" style="background-color: ${badgeColor}">${platformText}</span>`;
}

async function processSingleDownload(url, format, resolution, directory) {
  const progressContainer = document.createElement('div');
  progressContainer.className = 'progress mb-2';
  progressContainer.innerHTML = `
    <div class="progress-bar" role="progressbar" style="width: 0%">
      <span class="progress-text">0%</span>
    </div>
  `;
  document.getElementById('progressArea').appendChild(progressContainer);

  // Add warning for high-res videos
  if (resolution && parseInt(resolution) >= 1440) {
    const warningElement = document.createElement('div');
    warningElement.className = 'alert alert-warning mb-2';
    warningElement.innerHTML = `
      <strong>Note:</strong> Downloading in ${resolution}p may take longer and require more storage space.
    `;
    progressContainer.before(warningElement);
    // Auto-remove warning after 10 seconds
    setTimeout(() => warningElement.remove(), 10000);
  }

  const bar = progressContainer.querySelector('.progress-bar');
  const text = progressContainer.querySelector('.progress-text');
  let fakeProgress = 0;
  const interval = setInterval(() => {
    fakeProgress += 10;
    if (fakeProgress > 95) fakeProgress = 95;
    bar.style.width = `${fakeProgress}%`;
    text.textContent = `${fakeProgress}%`;
  }, 300);

  try {
    const response = await fetch('/download', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-CSRFToken': csrfToken
      },
      body: JSON.stringify({ url, format, resolution: format === 'mp3' ? null : parseInt(resolution), directory })
    });

    clearInterval(interval);

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.error || 'Download failed');
    }

    const data = await response.json();
    const { filename, platform } = data;

    // Auto-download via anchor click
    const a = document.createElement('a');
    a.href = `/download/${encodeURIComponent(filename)}`;
    a.download = '';
    a.style.display = 'none';
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);

    // Get platform-specific badge
    const platformBadge = getPlatformBadgeHTML(platform || 'youtube');

    progressContainer.innerHTML = `
      <div class="alert alert-success">
        ${platformBadge} ✅ Download complete!
        ${isLoggedIn ? `<a href="/download/${encodeURIComponent(filename)}" class="alert-link">Click to download again</a>` : ''}
        <div class="mt-2 small">
          <em>If the video has no sound, try downloading at a different resolution or using MP3 format for audio only.</em>
        </div>
      </div>
    `;
    if (isLoggedIn) {
      loadHistory();
    }
  } catch (error) {
    clearInterval(interval);
    progressContainer.innerHTML = `
      <div class="alert alert-danger">
        ❌ ${error.message}
        <button class="btn btn-sm btn-light float-end" onclick="this.parentElement.remove()">×</button>
      </div>
    `;
  }
}

async function loadHistory() {
  const historyList = document.getElementById('historyList');
  if (!isLoggedIn || !historyList) {
    const loading = document.getElementById('historyLoading');
    if (loading) loading.style.display = 'none';
    return;
  }

  try {
    const response = await fetch('/my_downloads');
    const html = await response.text();
    const parser = new DOMParser();
    const doc = parser.parseFromString(html, 'text/html');
    const historyItems = doc.querySelectorAll('.list-group-item');

    historyList.innerHTML = '';
    historyItems.forEach(item => historyList.appendChild(item.cloneNode(true)));

    document.getElementById('historyLoading').style.display = 'none';
    historyList.style.display = 'block';
  } catch (error) {
    console.error('History load error:', error);
  }
}

// ---- Theme Toggle Logic ----
const themeBtn = document.getElementById('themeToggleBtn');
const savedTheme = localStorage.getItem('theme') || 'dark';

function applyTheme(theme) {
  if (theme === 'light') {
    document.documentElement.classList.add('light-mode');
    themeBtn.textContent = '☀️ / 🌙';
  } else {
    document.documentElement.classList.remove('light-mode');
    themeBtn.textContent = '🌙 / ☀️';
  }
  localStorage.setItem('theme', theme);
}

// Initialize on page load
applyTheme(savedTheme);

themeBtn.addEventListener('click', () => {
  const newTheme = (localStorage.getItem('theme') === 'light') ? 'dark' : 'light';
  applyTheme(newTheme);
});

// URL Validation helper - checks if URL is from a supported platform
function validateURL(url) {
  // Simple regex patterns for supported platforms
  const youtubePattern = /^(https?:\/\/)?(www\.)?(youtube\.com|youtu\.be)\/.+/i;
  const tiktokPattern = /^(https?:\/\/)?(www\.)?(tiktok\.com|vm\.tiktok\.com|vt\.tiktok\.com)\/.+/i;
  const instagramPattern = /^(https?:\/\/)?(www\.)?(instagram\.com|instagr\.am)\/(p|reel|tv)\/.+/i;
  const twitterPattern = /^(https?:\/\/)?(www\.)?(twitter\.com|x\.com)\/.+\/status\/\d+/i;
  const facebookPattern = /^(https?:\/\/)?(www\.)?(facebook\.com|fb\.com|fb\.watch)\/.+/i;
  
  return youtubePattern.test(url) || 
         tiktokPattern.test(url) || 
         instagramPattern.test(url) || 
         twitterPattern.test(url) ||
         facebookPattern.test(url);
}

// Initialization
document.addEventListener('DOMContentLoaded', () => {
  // Only run index.html specific code if the elements exist
  const directoryInput = document.getElementById('directory');
  if (directoryInput) {
    directoryInput.value = sessionStorage.getItem('lastDirectory') || 'downloads';
  }

  const formatSelect = document.getElementById('format');
  const resolutionSelect = document.getElementById('resolution');
  if (formatSelect && resolutionSelect) {
    resolutionSelect.disabled = formatSelect.value === 'mp3'; // Initial check
    formatSelect.addEventListener('change', function () {
      resolutionSelect.disabled = this.value === 'mp3';
    });
  }

  const urlInput = document.getElementById('urlInput');
  if (urlInput) {
    urlInput.addEventListener('dragover', e => e.preventDefault());
    urlInput.addEventListener('drop', e => {
      e.preventDefault();
      const text = e.dataTransfer.getData('text');
      urlInput.value += (urlInput.value ? '\n' : '') + text.trim();
    });
    
    // Add paste event listener to validate URLs
    urlInput.addEventListener('paste', e => {
      // Wait for the paste to complete
      setTimeout(() => {
        const urls = urlInput.value.split('\n').filter(Boolean);
        for (const url of urls) {
          if (!validateURL(url)) {
            showErrorToast(`Warning: "${url}" may not be from a supported platform (YouTube, TikTok, Instagram, Twitter, Facebook).`);
            break; // Only show one warning
          }
        }
      }, 100);
    });
  }

  // Load history on main page if relevant elements exist
  if (document.getElementById('historyList')) {
    loadHistory();
  }
});

// --- New function for deleting downloads ---
async function deleteDownload(filename) {
  if (!isLoggedIn) {
    showErrorToast('Please log in to manage downloads.');
    return;
  }

  if (!confirm(`Are you sure you want to delete ${decodeURIComponent(filename)}?`)) {
    return;
  }

  try {
    const response = await fetch(`/delete_download/${filename}`, {
      method: 'DELETE',
      headers: {
        'X-CSRFToken': csrfToken // Include CSRF token
      }
    });

    const data = await response.json();

    if (response.ok && data.success) {
      // Remove the item from the list
      const itemToRemove = document.getElementById(`history-item-${filename}`);
      if (itemToRemove) {
        itemToRemove.remove();
      } else {
        console.warn('Could not find history item to remove:', filename);
      }
      // Optionally show a success toast
      // showSuccessToast('Download deleted successfully!');
    } else {
      throw new Error(data.error || 'Failed to delete download.');
    }
  } catch (error) {
    showErrorToast(error.message);
    console.error('Delete error:', error);
  }
}
