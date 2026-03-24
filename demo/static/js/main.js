/* LaMa图像修复演示系统 - JavaScript */

// 全局状态
let appState = {
    currentStep: 1,
    uploadedImage: null,
    maskData: null,
    resultPath: null,
    resultUrl: null,
    uploadedImagePath: null,
    maskPath: null,
    inpaintJobId: null,
    sessionId: Date.now().toString(),
    isProcessing: false
};

// DOM元素引用
const statusElement = document.getElementById('status');
const fileInput = document.getElementById('fileInput');
const chooseFileBtn = document.getElementById('chooseFileBtn');
const uploadArea = document.getElementById('uploadArea');
const imagePreview = document.getElementById('imagePreview');
const previewImage = document.getElementById('previewImage');
const nextStep1 = document.getElementById('nextStep1');
const nextStep2 = document.getElementById('nextStep2');
const nextStep3 = document.getElementById('nextStep3');
const maskCanvas = document.getElementById('maskCanvas');
const drawCanvas = document.getElementById('drawCanvas');

// 画布状态
let canvasState = {
    ctx: null,
    drawCtx: null,
    isDrawing: false,
    currentTool: 'brush',
    brushSize: 20,
    history: [],
    historyIndex: -1
};

// 初始化
document.addEventListener('DOMContentLoaded', function() {
    initializeApp();
    checkServerStatus();
    setupEventListeners();
    initializeCanvas();
});

// 初始化应用
function initializeApp() {
    updateStep(appState.currentStep);
    
    // 设置文件拖放
    uploadArea.addEventListener('dragover', (e) => {
        e.preventDefault();
        uploadArea.style.borderColor = '#6366f1';
        uploadArea.style.background = '#f9fafb';
    });
    
    uploadArea.addEventListener('dragleave', (e) => {
        e.preventDefault();
        uploadArea.style.borderColor = '#e5e7eb';
        uploadArea.style.background = 'transparent';
    });
    
    uploadArea.addEventListener('drop', (e) => {
        e.preventDefault();
        uploadArea.style.borderColor = '#e5e7eb';
        uploadArea.style.background = 'transparent';
        
        const files = e.dataTransfer.files;
        if (files.length > 0) {
            handleFileSelect(files[0]);
        }
    });
}

// 检查服务器状态
function checkServerStatus() {
    fetch('/api/status')
        .then(response => response.json())
        .then(data => {
            if (data.status === 'ok') {
                updateStatus('在线', 'online');
                if (data.model_loaded) {
                    showNotification('模型加载成功', 'success');
                } else {
                    showNotification('模型未加载，部分功能可能受限', 'warning');
                }
            }
        })
        .catch(error => {
            console.error('状态检查失败:', error);
            updateStatus('离线', 'offline');
            showNotification('无法连接到服务器', 'error');
        });
}

// 更新状态显示
function updateStatus(text, status = 'online') {
    const dot = statusElement.querySelector('.status-dot');
    const textSpan = statusElement.querySelector('span');
    
    textSpan.textContent = text;
    dot.className = 'fas fa-circle status-dot';
    dot.classList.add(status);
}

// 显示通知
function showNotification(message, type = 'info') {
    // 在实际应用中，这里可以添加更复杂的通知系统
    console.log(`${type.toUpperCase()}: ${message}`);
    
    // 简单的浏览器通知
    if (Notification.permission === 'granted') {
        new Notification(`LaMa演示系统 - ${type}`, {
            body: message,
            icon: '/static/favicon.ico'
        });
    }
}

// 设置事件监听器
function setupEventListeners() {
    if (chooseFileBtn) {
        chooseFileBtn.addEventListener('click', (e) => {
            e.preventDefault();
            e.stopPropagation();
            fileInput.value = '';
            fileInput.click();
        });
    }

    // 点击上传区域时触发文件选择
    uploadArea.addEventListener('click', (e) => {
        const isControl = e.target.closest('.btn, label, input, button');
        if (!isControl) {
            fileInput.value = '';
            fileInput.click();
        }
    });

    // 文件选择
    fileInput.addEventListener('change', (e) => {
        if (e.target.files.length > 0) {
            handleFileSelect(e.target.files[0]);
        }
    });
    
    // 工具选择
    document.querySelectorAll('.tool-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            document.querySelectorAll('.tool-btn').forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            canvasState.currentTool = btn.dataset.tool;
            
            // 更新画笔大小显示
            if (canvasState.currentTool === 'brush') {
                document.getElementById('brushSizeValue').textContent = canvasState.brushSize;
            }
        });
    });
    
    // 画笔大小滑块
    const brushSizeSlider = document.getElementById('brushSize');
    brushSizeSlider.addEventListener('input', (e) => {
        canvasState.brushSize = parseInt(e.target.value);
        document.getElementById('brushSizeValue').textContent = canvasState.brushSize;
    });
}

// 处理文件选择
function handleFileSelect(file) {
    if (!file.type.match('image.*')) {
        showNotification('请选择图像文件', 'error');
        return;
    }
    
    const reader = new FileReader();
    reader.onload = function(e) {
        appState.uploadedImage = {
            file: file,
            dataUrl: e.target.result,
            name: file.name
        };
        
        displayImagePreview(e.target.result);
        uploadToServer(file);
    };
    reader.readAsDataURL(file);
}

// 显示图像预览
function displayImagePreview(dataUrl) {
    previewImage.src = dataUrl;
    imagePreview.style.display = 'block';
    
    // 获取图像尺寸
    const img = new Image();
    img.onload = function() {
        document.getElementById('fileName').textContent = appState.uploadedImage.name;
        document.getElementById('imageResolution').textContent = `${img.width} × ${img.height}`;
        document.getElementById('imageSize').textContent = formatFileSize(appState.uploadedImage.file.size);
        
        // 启用下一步按钮
        nextStep1.disabled = false;
        
        // 初始化画布尺寸
        initializeCanvasWithImage(img);
    };
    img.src = dataUrl;
}

// 初始化画布
function initializeCanvas() {
    canvasState.ctx = maskCanvas.getContext('2d');
    canvasState.drawCtx = drawCanvas.getContext('2d');
    
    // 设置画布事件
    drawCanvas.addEventListener('mousedown', startDrawing);
    drawCanvas.addEventListener('mousemove', draw);
    drawCanvas.addEventListener('mouseup', stopDrawing);
    drawCanvas.addEventListener('mouseout', stopDrawing);
}

// 用图像初始化画布
function initializeCanvasWithImage(img) {
    const container = drawCanvas.parentElement;
    // 使用父元素的父元素来获取可用宽度，因为 canvas-wrapper 可能在隐藏状态下获取不到正确宽度
    const maxWidth = container.parentElement.clientWidth || 800; 
    const maxHeight = 500; // 最大高度
    
    let width = img.width;
    let height = img.height;
    
    // 保持宽高比缩放
    if (width > maxWidth) {
        height = (maxWidth / width) * height;
        width = maxWidth;
    }
    
    if (height > maxHeight) {
        width = (maxHeight / height) * width;
        height = maxHeight;
    }
    
    // 设置画布的实际像素尺寸
    maskCanvas.width = width;
    maskCanvas.height = height;
    drawCanvas.width = width;
    drawCanvas.height = height;
    
    // 设置画布的 CSS 显示尺寸
    maskCanvas.style.width = width + 'px';
    maskCanvas.style.height = height + 'px';
    drawCanvas.style.width = width + 'px';
    drawCanvas.style.height = height + 'px';
    
    // 动态调整父容器的高度以包裹绝对定位的 canvas
    container.style.height = height + 'px';
    container.style.minHeight = height + 'px';
    
    // 绘制原始图像到掩码画布作为背景
    canvasState.ctx.drawImage(img, 0, 0, width, height);
}

// 开始绘制
function startDrawing(e) {
    if (appState.isProcessing) return;
    
    canvasState.isDrawing = true;
    canvasState.drawCtx.lineWidth = canvasState.brushSize;
    canvasState.drawCtx.lineCap = 'round';
    
    const rect = drawCanvas.getBoundingClientRect();
    const x = e.clientX - rect.left;
    const y = e.clientY - rect.top;
    
    canvasState.drawCtx.beginPath();
    canvasState.drawCtx.moveTo(x, y);
    
    // 保存历史状态
    saveCanvasState();
}

// 绘制
function draw(e) {
    if (!canvasState.isDrawing) return;
    
    const rect = drawCanvas.getBoundingClientRect();
    const x = e.clientX - rect.left;
    const y = e.clientY - rect.top;
    
    if (canvasState.currentTool === 'eraser') {
        canvasState.drawCtx.globalCompositeOperation = 'destination-out';
        canvasState.drawCtx.strokeStyle = 'rgba(0,0,0,1)';
    } else {
        canvasState.drawCtx.globalCompositeOperation = 'source-over';
        canvasState.drawCtx.strokeStyle = 'rgba(255,255,255,1)';
    }
    
    canvasState.drawCtx.lineTo(x, y);
    canvasState.drawCtx.stroke();
}

// 停止绘制
function stopDrawing() {
    if (canvasState.isDrawing) {
        canvasState.isDrawing = false;
        canvasState.drawCtx.closePath();
        
        // 更新掩码预览
        updateMaskPreview();
        
        // 启用下一步按钮
        nextStep2.disabled = false;
    }
}

// 保存画布状态
function saveCanvasState() {
    const state = drawCanvas.toDataURL();
    canvasState.history.push(state);
    canvasState.historyIndex = canvasState.history.length - 1;
}

// 清除掩码
function clearMask() {
    canvasState.drawCtx.clearRect(0, 0, drawCanvas.width, drawCanvas.height);
    saveCanvasState();
    updateMaskPreview();
}

// 撤销操作
function undoMask() {
    if (canvasState.historyIndex > 0) {
        canvasState.historyIndex--;
        const img = new Image();
        img.onload = function() {
            canvasState.drawCtx.clearRect(0, 0, drawCanvas.width, drawCanvas.height);
            canvasState.drawCtx.drawImage(img, 0, 0);
            updateMaskPreview();
        };
        img.src = canvasState.history[canvasState.historyIndex];
    }
}

// 填充整个画布
function fillMask() {
    canvasState.drawCtx.fillStyle = 'rgba(255,255,255,1)';
    canvasState.drawCtx.fillRect(0, 0, drawCanvas.width, drawCanvas.height);
    saveCanvasState();
    updateMaskPreview();
}

// 更新掩码预览
function updateMaskPreview() {
    const maskData = drawCanvas.toDataURL();
    appState.maskData = maskData;
    
    // 发送到服务器
    sendMaskToServer();
}

// 上传到服务器
function uploadToServer(file) {
    showLoading('上传图像中...');
    
    const formData = new FormData();
    formData.append('file', file);
    
    fetch('/api/upload', {
        method: 'POST',
        body: formData
    })
    .then(response => {
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        return response.json();
    })
    .then(data => {
        hideLoading();
        if (data.status === 'ok') {
            appState.uploadedImagePath = data.filepath;
            showNotification('图像上传成功', 'success');
        } else {
            showNotification('上传失败: ' + data.error, 'error');
        }
    })
    .catch(error => {
        hideLoading();
        showNotification('上传失败: ' + error.message, 'error');
        console.error("上传错误详情:", error);
    });
}

// 发送掩码到服务器
function sendMaskToServer() {
    if (!appState.uploadedImage) return;
    
    // 将画布数据转换为Blob
    drawCanvas.toBlob(function(blob) {
        const formData = new FormData();
        formData.append('mask', blob, 'mask.png');
        
        fetch('/api/create_mask', {
            method: 'POST',
            body: formData
        })
        .then(response => response.json())
        .then(data => {
            if (data.status === 'ok') {
                appState.maskPath = data.mask_path;
                console.log('掩码创建成功');
            }
        })
        .catch(error => {
            console.error('掩码创建失败:', error);
        });
    });
}

// 开始图像修复
function startInpainting() {
    if (appState.isProcessing) return;
    if (!appState.uploadedImagePath) {
        showNotification('请先上传图像', 'warning');
        return;
    }
    if (!appState.maskPath) {
        showNotification('请先绘制掩码', 'warning');
        return;
    }
    
    const refine = document.getElementById('refineOption').checked;
    const autoResizeEnabled = document.getElementById('autoResizeOption').checked;
    const roiInferenceEnabled = document.getElementById('roiOption').checked;
    const maxLongSide = parseInt(document.getElementById('maxLongSideInput').value || '1536', 10);
    const roiPadding = parseInt(document.getElementById('roiPaddingInput').value || '128', 10);
    const inpaintBtn = document.getElementById('inpaintBtn');
    
    showLoading(refine ? '正在进行高质量修复...' : '正在进行标准修复...');
    updateLoadingProgress(1, '任务已提交');
    appState.isProcessing = true;
    inpaintBtn.disabled = true;
    
    const startTime = Date.now();

    fetch('/api/inpaint/start', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({
            refine: refine,
            session_id: appState.sessionId,
            image_path: appState.uploadedImagePath,
            mask_path: appState.maskPath,
            auto_resize_enabled: autoResizeEnabled,
            max_long_side: Number.isFinite(maxLongSide) ? maxLongSide : 1536,
            roi_inference_enabled: roiInferenceEnabled,
            roi_padding: Number.isFinite(roiPadding) ? roiPadding : 128
        })
    })
    .then(response => {
        if (!response.ok) {
            return response.json().then(err => {
                throw new Error(err.error || `HTTP ${response.status}`);
            });
        }
        return response.json();
    })
    .then(data => {
        if (data.status !== 'ok' || !data.job_id) {
            throw new Error(data.error || '任务启动失败');
        }
        appState.inpaintJobId = data.job_id;
        pollInpaintProgress(appState.inpaintJobId, startTime, refine);
    })
    .catch(error => {
        hideLoading();
        appState.isProcessing = false;
        inpaintBtn.disabled = false;
        showNotification('修复失败: ' + error.message, 'error');
    });
}

function pollInpaintProgress(jobId, startTime, refine) {
    const inpaintBtn = document.getElementById('inpaintBtn');
    const poll = () => {
        fetch(`/api/inpaint/status/${jobId}`)
            .then(response => response.json())
            .then(data => {
                if (data.status !== 'ok') {
                    throw new Error(data.error || '查询进度失败');
                }
                const progress = Number.isFinite(data.progress) ? data.progress : 0;
                updateLoadingProgress(progress, data.message || '处理中');

                if (data.job_status === 'done') {
                    appState.resultPath = data.result_path;
                    appState.resultUrl = data.result_url;
                    updateResultPreview();
                    const apiTotal = data.timings && typeof data.timings.total_sec === 'number'
                        ? data.timings.total_sec.toFixed(2)
                        : null;
                    const processTime = apiTotal || ((Date.now() - startTime) / 1000).toFixed(2);
                    document.getElementById('processTime').textContent = `${processTime}秒`;
                    document.getElementById('qualityLevel').textContent = refine ? '高质量' : '标准';
                    if (data.timings) {
                        console.table(data.timings);
                    }
                    nextStep3.disabled = false;
                    appState.isProcessing = false;
                    inpaintBtn.disabled = false;
                    hideLoading();
                    showNotification('图像修复完成', 'success');
                    return;
                }

                if (data.job_status === 'error') {
                    appState.isProcessing = false;
                    inpaintBtn.disabled = false;
                    hideLoading();
                    const resultPreview = document.getElementById('resultPreview');
                    resultPreview.innerHTML = `<div class="result-placeholder"><i class="fas fa-exclamation-triangle"></i><p>修复失败：${data.error || '未知错误'}</p></div>`;
                    showNotification(`修复失败: ${data.error || '未知错误'}`, 'error');
                    return;
                }

                setTimeout(poll, 800);
            })
            .catch(error => {
                appState.isProcessing = false;
                inpaintBtn.disabled = false;
                hideLoading();
                showNotification(`修复失败: ${error.message}`, 'error');
            });
    };
    poll();
}

// 更新结果预览
function updateResultPreview() {
    if (appState.resultUrl) {
        const resultPreview = document.getElementById('resultPreview');
        const imageUrl = `${appState.resultUrl}?t=${Date.now()}`;
        resultPreview.innerHTML = `<img src="${imageUrl}" alt="修复结果" style="width:100%;height:100%;object-fit:contain;">`;
        const img = resultPreview.querySelector('img');
        if (img) {
            img.onerror = function() {
                console.error('结果图片加载失败:', imageUrl);
                showNotification('结果图片加载失败，请查看后端日志', 'error');
            };
        }
        return;
    }

    fetch('/api/preview/result')
        .then(response => response.json())
        .then(data => {
            if (data.status === 'ok') {
                const resultPreview = document.getElementById('resultPreview');
                resultPreview.innerHTML = `<img src="${data.data}" alt="修复结果" style="width:100%;height:100%;object-fit:contain;">`;
            }
        });
}

// 下载结果
function downloadResult() {
    let downloadUrl = null;
    let downloadName = `lama_result_${Date.now()}.png`;

    if (appState.resultUrl) {
        downloadUrl = `${appState.resultUrl}?download=1&t=${Date.now()}`;
        if (appState.resultPath) {
            downloadName = appState.resultPath.split('/').pop();
        }
    } else if (appState.resultPath) {
        const filename = appState.resultPath.split('/').pop();
        downloadName = filename;
        downloadUrl = `/api/download/${encodeURIComponent(filename)}?download=1&t=${Date.now()}`;
    }

    if (!downloadUrl) {
        showNotification('没有可下载的结果', 'warning');
        return;
    }

    fetch(downloadUrl)
        .then(response => {
            if (!response.ok) {
                throw new Error(`下载失败: HTTP ${response.status}`);
            }
            return response.blob();
        })
        .then(blob => {
            const objectUrl = URL.createObjectURL(blob);
            const link = document.createElement('a');
            link.href = objectUrl;
            link.download = downloadName;
            link.rel = 'noopener';
            document.body.appendChild(link);
            link.click();
            link.remove();
            URL.revokeObjectURL(objectUrl);
        })
        .catch(error => {
            showNotification(error.message, 'error');
        });
}

// 重新开始
function startOver() {
    fetch('/api/clear', {
        method: 'POST'
    })
    .then(response => response.json())
    .then(data => {
        if (data.status === 'ok') {
            // 重置应用状态
            appState = {
                currentStep: 1,
                uploadedImage: null,
                maskData: null,
                resultPath: null,
                resultUrl: null,
                uploadedImagePath: null,
                maskPath: null,
                inpaintJobId: null,
                sessionId: Date.now().toString(),
                isProcessing: false
            };
            
            // 重置UI
            imagePreview.style.display = 'none';
            nextStep1.disabled = true;
            nextStep2.disabled = true;
            nextStep3.disabled = true;
            
            // 清除画布
            clearMask();
            
            // 返回第一步
            updateStep(1);
            
            showNotification('已重置，可以开始新的修复', 'info');
        }
    });
}

// 复制结果链接
function copyResultLink() {
    if (!appState.resultPath) {
        showNotification('没有结果链接可复制', 'warning');
        return;
    }
    
    const link = `${window.location.origin}/api/download/${appState.resultPath.split('/').pop()}`;
    
    navigator.clipboard.writeText(link)
        .then(() => {
            showNotification('链接已复制到剪贴板', 'success');
        })
        .catch(err => {
            console.error('复制失败:', err);
            showNotification('复制失败', 'error');
        });
}

// 步骤导航
function nextStep(step) {
    if (step > 4) return;
    
    appState.currentStep = step;
    updateStep(step);
    
    // 加载预览
    if (step === 3) {
        loadPreviews();
    }
}

function prevStep(step) {
    if (step < 1) return;
    
    appState.currentStep = step;
    updateStep(step);
}

function updateStep(step) {
    // 更新步骤指示器
    document.querySelectorAll('.step').forEach((el, index) => {
        if (index + 1 <= step) {
            el.classList.add('completed');
        } else {
            el.classList.remove('completed');
        }
        
        if (index + 1 === step) {
            el.classList.add('active');
        } else {
            el.classList.remove('active');
        }
    });
    
    // 更新内容面板
    document.querySelectorAll('.step-panel').forEach((el, index) => {
        if (index + 1 === step) {
            el.classList.add('active');
        } else {
            el.classList.remove('active');
        }
    });
}

// 加载预览
function loadPreviews() {
    // 加载原始图像预览
    fetch('/api/preview/original')
        .then(response => response.json())
        .then(data => {
            if (data.status === 'ok') {
                const originalPreview = document.getElementById('originalPreview');
                originalPreview.innerHTML = `<img src="${data.data}" alt="原始图像" style="width:100%;height:100%;object-fit:contain;">`;
            }
        });
    
    // 加载掩码预览
    fetch('/api/preview/mask')
        .then(response => response.json())
        .then(data => {
            if (data.status === 'ok') {
                const maskPreview = document.getElementById('maskPreview');
                maskPreview.innerHTML = `<img src="${data.data}" alt="掩码" style="width:100%;height:100%;object-fit:contain;">`;
            }
        });
}

// 工具函数
function formatFileSize(bytes) {
    if (bytes === 0) return '0 B';
    
    const k = 1024;
    const sizes = ['B', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
}

function showLoading(message = '处理中...') {
    const overlay = document.getElementById('loadingOverlay');
    const messageElement = document.getElementById('loadingMessage');
    
    messageElement.textContent = message;
    updateLoadingProgress(0, '准备中');
    overlay.style.display = 'flex';
}

function hideLoading() {
    const overlay = document.getElementById('loadingOverlay');
    overlay.style.display = 'none';
}

function updateLoadingProgress(progress, text) {
    const bar = document.getElementById('loadingProgressBar');
    const progressText = document.getElementById('loadingProgressText');
    const messageElement = document.getElementById('loadingMessage');
    const safeProgress = Math.max(0, Math.min(100, Number(progress) || 0));
    if (bar) {
        bar.style.width = `${safeProgress}%`;
    }
    if (progressText) {
        progressText.textContent = `${safeProgress.toFixed(0)}%`;
    }
    if (messageElement && text) {
        messageElement.textContent = text;
    }
}
