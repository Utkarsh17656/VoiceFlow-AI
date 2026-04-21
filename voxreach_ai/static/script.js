document.addEventListener("DOMContentLoaded", () => {
    
    // File Drag and Drop functionality
    const fileDropArea = document.getElementById("fileDropArea");
    const fileInput = document.getElementById("fileInput");
    const dropText = document.getElementById("dropText");
    const uploadForm = document.getElementById("uploadForm");
    const submitBtn = document.getElementById("submitBtn");
    const spinnerContainer = document.getElementById("spinnerContainer");

    // Prevent default drag behaviors
    ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
        fileDropArea.addEventListener(eventName, preventDefaults, false);
    });

    function preventDefaults(e) {
        e.preventDefault();
        e.stopPropagation();
    }

    // Highlight drop area when item is dragged over it
    ['dragenter', 'dragover'].forEach(eventName => {
        fileDropArea.addEventListener(eventName, () => {
            fileDropArea.classList.add('dragover');
        });
    });

    ['dragleave', 'drop'].forEach(eventName => {
        fileDropArea.addEventListener(eventName, () => {
            fileDropArea.classList.remove('dragover');
        });
    });

    // Handle dropped files
    fileDropArea.addEventListener('drop', (e) => {
        let dt = e.dataTransfer;
        let files = dt.files;
        handleFiles(files);
    });

    // Handle file input change
    fileInput.addEventListener('change', function() {
        handleFiles(this.files);
    });

    function handleFiles(files) {
        if (files.length > 0) {
            const fileName = files[0].name;
            if(fileName.endsWith('.csv')) {
                dropText.textContent = fileName;
                dropText.classList.add('file-chosen');
            } else {
                dropText.textContent = "Error: Please upload a .csv file";
                dropText.classList.remove('file-chosen');
                dropText.style.color = "red";
                fileInput.value = ""; // Clear invalid file
            }
        }
    }

    // Form Submit functionality
    if(uploadForm) {
        uploadForm.addEventListener('submit', (e) => {
            // Check if file is selected
            if (!fileInput.files.length) {
                e.preventDefault();
                alert("Please select a file first.");
                return;
            }
            
            // Show spinner
            fileDropArea.style.display = "none";
            submitBtn.disabled = true;
            submitBtn.textContent = "Processing...";
            spinnerContainer.classList.remove('hidden');
        });
    }

    // Table Search functionality
    const searchInput = document.getElementById("searchInput");
    if(searchInput) {
        searchInput.addEventListener("input", function() {
            const searchTerm = this.value.toLowerCase();
            const rows = document.querySelectorAll("#resultsTable tbody tr");
            
            rows.forEach(row => {
                const name = row.querySelector(".cell-name").textContent.toLowerCase();
                const phone = row.querySelector(".cell-phone").textContent.toLowerCase();
                
                if(name.includes(searchTerm) || phone.includes(searchTerm)) {
                    row.style.display = "";
                } else {
                    row.style.display = "none";
                }
            });
        });
    }
});

// Row Message "Show more / less" functionality
function toggleMessage(id, element) {
    const msgElement = document.getElementById(id);
    if(msgElement.classList.contains("expanded")) {
        msgElement.classList.remove("expanded");
        msgElement.classList.add("collapsed");
        element.textContent = "Show more";
    } else {
        msgElement.classList.add("expanded");
        msgElement.classList.remove("collapsed");
        element.textContent = "Show less";
    }
}

// Download CSV functionality
function downloadCSV() {
    const table = document.getElementById("resultsTable");
    if (!table) return;

    let csvContent = "";
    
    // Header
    const headers = Array.from(table.querySelectorAll("th")).map(th => `"${th.textContent.trim()}"`);
    csvContent += headers.join(",") + "\r\n";
    
    // Rows
    const rows = Array.from(table.querySelectorAll("tbody tr")).filter(row => row.style.display !== "none"); // Only include visible rows
    
    rows.forEach(row => {
        const rowData = [];
        
        // 1. Name
        rowData.push(`"${row.querySelector('.cell-name').textContent.trim().replace(/"/g, '""')}"`);
        
        // 2. Phone
        rowData.push(`"${row.querySelector('.cell-phone').textContent.trim().replace(/"/g, '""')}"`);
        
        // 3. Message (extract from the div to avoid button text)
        const messageDiv = row.querySelector('.message-content');
        rowData.push(`"${messageDiv.textContent.trim().replace(/"/g, '""')}"`);
        
        // 4. Status
        const statusSpan = row.querySelector('.badge');
        rowData.push(`"${statusSpan.textContent.trim()}"`);
        
        // 5. Error
        rowData.push(`"${row.querySelector('.cell-error').textContent.trim().replace(/"/g, '""')}"`);
        
        csvContent += rowData.join(",") + "\r\n";
    });
    
    // Trigger download
    const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.setAttribute("href", url);
    link.setAttribute("download", "voxreach_results.csv");
    link.style.visibility = "hidden";
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
}