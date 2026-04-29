// ── Theme Management ───────────────────────────────────────────────────────
const savedTheme = localStorage.getItem('voxreach-theme') || 'light';
if (savedTheme === 'dark') {
    document.documentElement.setAttribute('data-theme', 'dark');
}

document.addEventListener("DOMContentLoaded", () => {
    // Setup Theme Toggle
    const themeToggle = document.getElementById('themeToggle');
    if (themeToggle) {
        themeToggle.textContent = savedTheme === 'dark' ? '☀️' : '🌙';
        
        themeToggle.addEventListener('click', () => {
            const currentTheme = document.documentElement.getAttribute('data-theme');
            const newTheme = currentTheme === 'dark' ? 'light' : 'dark';
            
            if (newTheme === 'dark') {
                document.documentElement.setAttribute('data-theme', 'dark');
                themeToggle.textContent = '☀️';
                localStorage.setItem('voxreach-theme', 'dark');
            } else {
                document.documentElement.removeAttribute('data-theme');
                themeToggle.textContent = '🌙';
                localStorage.setItem('voxreach-theme', 'light');
            }
        });
    }

    const fileDropArea    = document.getElementById("fileDropArea");
    const fileInput       = document.getElementById("fileInput");
    const dropText        = document.getElementById("dropText");
    const uploadForm      = document.getElementById("uploadForm");
    const submitBtn       = document.getElementById("submitBtn");
    const spinnerContainer = document.getElementById("spinnerContainer");
    const sheetUrlInput   = document.getElementById("sheetUrlInput");

    // ── File type validation helper ────────────────────────────────────────
    function isValidFileType(filename) {
        const name = filename.toLowerCase();
        return name.endsWith('.csv') || name.endsWith('.xlsx') || name.endsWith('.xls');
    }

    // ── Drag-and-drop ──────────────────────────────────────────────────────
    ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
        fileDropArea.addEventListener(eventName, e => {
            e.preventDefault();
            e.stopPropagation();
        }, false);
    });

    ['dragenter', 'dragover'].forEach(eventName => {
        fileDropArea.addEventListener(eventName, () => fileDropArea.classList.add('dragover'));
    });
    ['dragleave', 'drop'].forEach(eventName => {
        fileDropArea.addEventListener(eventName, () => fileDropArea.classList.remove('dragover'));
    });

    fileDropArea.addEventListener('drop', e => {
        const files = e.dataTransfer.files;
        if (files.length) {
            fileInput.files = files;
            handleFileSelected(files[0]);
        }
    });

    // ── File input change ──────────────────────────────────────────────────
    fileInput.addEventListener('change', function () {
        if (this.files.length) handleFileSelected(this.files[0]);
    });

    function handleFileSelected(file) {
        if (isValidFileType(file.name)) {
            dropText.textContent = file.name;
            dropText.classList.add('file-chosen');
            dropText.style.color = '';
            // Clear the sheet URL so only the file is used
            if (sheetUrlInput) {
                sheetUrlInput.value = '';
                sheetUrlInput.classList.remove('has-value');
            }
        } else {
            dropText.textContent = 'Error: Please upload a .csv or .xlsx file';
            dropText.classList.remove('file-chosen');
            dropText.style.color = 'red';
            fileInput.value = '';
        }
    }

    // ── Google Sheet URL input — clear file if user types a URL ───────────
    if (sheetUrlInput) {
        sheetUrlInput.addEventListener('input', function () {
            if (this.value.trim()) {
                // Clear the file so only the URL is used
                fileInput.value = '';
                dropText.textContent = 'Drag & Drop your CSV or Excel file here or click to browse';
                dropText.classList.remove('file-chosen');
                dropText.style.color = '';
                this.classList.add('has-value');
            } else {
                this.classList.remove('has-value');
            }
        });
    }

    // ── Form submit validation ─────────────────────────────────────────────
    if (uploadForm) {
        uploadForm.addEventListener('submit', e => {
            const hasFile  = fileInput.files.length > 0;
            const sheetUrl = sheetUrlInput ? sheetUrlInput.value.trim() : '';
            const hasSheet = sheetUrl.length > 0;

            // Must have at least one source
            if (!hasFile && !hasSheet) {
                e.preventDefault();
                alert('Please select a .csv / .xlsx file OR paste a Google Sheets URL.');
                return;
            }

            // Validate file type if a file was chosen
            if (hasFile && !isValidFileType(fileInput.files[0].name)) {
                e.preventDefault();
                alert('Invalid file type. Please upload a .csv or .xlsx file.');
                return;
            }

            // Basic URL check for Google Sheet
            if (hasSheet && !sheetUrl.includes('docs.google.com/spreadsheets')) {
                e.preventDefault();
                alert('That does not look like a valid Google Sheets URL. Please check and try again.');
                return;
            }

            // Show loading state
            fileDropArea.style.display = 'none';
            if (sheetUrlInput && sheetUrlInput.closest('.sheet-url-section')) {
                sheetUrlInput.closest('.sheet-url-section').style.display = 'none';
                // also hide OR divider
                const divider = document.querySelector('.or-divider');
                if (divider) divider.style.display = 'none';
            }
            submitBtn.disabled = true;
            submitBtn.textContent = 'Processing...';
            spinnerContainer.classList.remove('hidden');
        });
    }

    // ── Table search ───────────────────────────────────────────────────────
    const searchInput = document.getElementById('searchInput');
    if (searchInput) {
        searchInput.addEventListener('input', function () {
            const term = this.value.toLowerCase();
            document.querySelectorAll('#resultsTable tbody tr').forEach(row => {
                const name  = row.querySelector('.cell-name')?.textContent.toLowerCase()  || '';
                const phone = row.querySelector('.cell-phone')?.textContent.toLowerCase() || '';
                row.style.display = (name.includes(term) || phone.includes(term)) ? '' : 'none';
            });
        });
    }
});

// ── Message expand / collapse ──────────────────────────────────────────────
function toggleMessage(id, element) {
    const msg = document.getElementById(id);
    if (!msg) return;
    const expanded = msg.classList.contains('expanded');
    msg.classList.toggle('expanded',  !expanded);
    msg.classList.toggle('collapsed',  expanded);
    element.textContent = expanded ? 'Show more' : 'Show less';
}

// ── Download CSV results ───────────────────────────────────────────────────
function downloadCSV() {
    const table = document.getElementById('resultsTable');
    if (!table) return;

    const headers = Array.from(table.querySelectorAll('th')).map(th => `"${th.textContent.trim()}"`);
    let csv = headers.join(',') + '\r\n';

    Array.from(table.querySelectorAll('tbody tr'))
        .filter(row => row.style.display !== 'none')
        .forEach(row => {
            const cols = [
                `"${row.querySelector('.cell-name')?.textContent.trim().replace(/"/g, '""') || ''}"`,
                `"${row.querySelector('.cell-phone')?.textContent.trim().replace(/"/g, '""') || ''}"`,
                `"${row.querySelector('.message-content')?.textContent.trim().replace(/"/g, '""') || ''}"`,
                `"${row.querySelector('.badge')?.textContent.trim() || ''}"`,
                `"${row.querySelector('.cell-error')?.textContent.trim().replace(/"/g, '""') || ''}"`,
            ];
            csv += cols.join(',') + '\r\n';
        });

    const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' });
    const url  = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href     = url;
    link.download = 'voxreach_results.csv';
    link.style.visibility = 'hidden';
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
}