document.addEventListener('DOMContentLoaded', () => {
    const fileInput = document.getElementById('file-input');
    const btnUpload = document.getElementById('btn-upload');
    const statusMsg = document.getElementById('status-msg');
    const resultsContainer = document.getElementById('results-container');

    btnUpload.addEventListener('click', async () => {
        const files = Array.from(fileInput.files);
        if (files.length === 0) {
            statusMsg.textContent = 'Lỗi: Bạn chưa chọn file ảnh nào.';
            statusMsg.className = 'message error';
            return;
        }

        btnUpload.disabled = true;
        btnUpload.textContent = `Đang xử lý ${files.length} ảnh...`;
        statusMsg.textContent = `Đang xử lý ${files.length} ảnh...`;
        statusMsg.className = 'message';
        resultsContainer.innerHTML = '';

        const results = [];
        let successCount = 0;
        let errorCount = 0;

        for (let i = 0; i < files.length; i++) {
            const file = files[i];
            const formData = new FormData();
            formData.append('file', file);

            try {
                const response = await fetch('/upload', {
                    method: 'POST',
                    body: formData
                });

                const data = await response.json();
                results.push({
                    index: i + 1,
                    filename: file.name,
                    success: response.ok,
                    data: data
                });

                if (response.ok) {
                    successCount++;
                } else {
                    errorCount++;
                }
            } catch (error) {
                results.push({
                    index: i + 1,
                    filename: file.name,
                    success: false,
                    error: error.message
                });
                errorCount++;
            }
        }

        results.forEach(result => {
            const resultCard = document.createElement('div');
            resultCard.className = 'result-card';
            
            if (result.success) {
                resultCard.innerHTML = `
                    <div class="result-header">
                        <h4>Ảnh ${result.index}: ${result.filename}</h4>
                        <span class="status-badge success">Thành công</span>
                    </div>
                    <div class="result-image-wrapper">
                        <img src="${result.data.result_url}" alt="Kết quả ${result.index}">
                    </div>
                    <div class="result-message">${result.data.message}</div>
                    ${result.data.details && result.data.details.length > 0 ? `
                        <div class="result-details">
                            <strong>Chi tiết:</strong>
                            <ul>
                                ${result.data.details.map(d => `<li>Biển số: ${d.plate} - Chủ xe: ${d.owner}</li>`).join('')}
                            </ul>
                        </div>
                    ` : ''}
                `;
            } else {
                resultCard.innerHTML = `
                    <div class="result-header">
                        <h4>Ảnh ${result.index}: ${result.filename}</h4>
                        <span class="status-badge error">Lỗi</span>
                    </div>
                    <div class="result-message error">${result.data?.message || result.error || 'Lỗi không xác định'}</div>
                `;
            }
            
            resultsContainer.appendChild(resultCard);
        });

        statusMsg.textContent = `Hoàn thành: ${successCount} thành công, ${errorCount} lỗi`;
        statusMsg.className = errorCount > 0 ? 'message error' : 'message success';
        btnUpload.disabled = false;
        btnUpload.textContent = 'Bắt đầu Xử lý';
    });
});