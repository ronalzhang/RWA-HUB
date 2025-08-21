// =================================================================
// RWA-HUB: /app/static/js/assets/create.js - 修复后完整代码
// =================================================================
// This is a reconstructed version of create.js with fixes.

async function deployAssetContract(assetData) {
    console.log("开始部署智能合约:", assetData);
    updateStepStatus('step-4', 'loading', '部署智能合约...');

    try {
        // FIXED API ENDPOINT
        const response = await fetch('/api/deploy-contract', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                ...getAuthHeaders()
            },
            body: JSON.stringify({ 
                asset_id: assetData.asset_id, 
                wallet_address: getWalletAddress() 
            })
        });

        if (!response.ok) {
            const errorText = await response.text();
            // Try to parse as JSON, if it fails, use the raw text
            let errorJson = {};
            try {
                errorJson = JSON.parse(errorText);
            } catch(e) {
                // ignore
            }
            throw new Error(errorJson.error || `HTTP error! status: ${response.status}, text: ${errorText}`);
        }

        const result = await response.json();

        if (result.success) {
            console.log("智能合约部署成功:", result);
            updateStepStatus('step-4', 'completed', '智能合约已部署');
            return result;
        } else {
            throw new Error(result.error || '部署失败');
        }
    } catch (error) {
        console.error("智能合约部署失败:", error);
        updateStepStatus('step-4', 'failed', `部署失败: ${error.message}`);
        throw error;
    }
}

async function checkStatus(signature) {
    try {
        // FIXED API ENDPOINT
        const response = await fetch(`/api/solana/check_transaction?signature=${signature}`);
        if (!response.ok) {
            throw new Error('检查交易状态失败');
        }
        const data = await response.json();
        return data;
    } catch (error) {
        console.error('检查交易状态出错:', error);
        throw error;
    }
}

async function handlePaymentSuccess(txHash) {
    console.log("支付成功，交易哈希:", txHash);
    updateStepStatus('step-3', 'completed', '支付已成功');

    try {
        const assetData = await processAssetCreation();
        if (assetData && assetData.contract_ready) {
            await deployAssetContract(assetData);
        }
        // ... (other success logic might be here)
        // Assuming we want to show a success message and reset the form
        showToast('资产创建和部署流程已成功启动！', 'success');

    } catch (error) {
        console.error("处理支付成功后发生错误:", error);
        showToast(`处理支付后续流程时出错: ${error.message}`, 'error');
    } finally {
        // FIXED function call
        resetCreateForm(); 
    }
}

function resetCreateForm() {
    const form = document.getElementById('assetForm');
    if (form) {
        form.reset();
    }
    uploadedImages = [];
    uploadedDocuments = [];
    renderImages();
    renderDocuments();
    localStorage.removeItem(CONFIG.DRAFT.KEY);
    
    // Reset all step indicators
    const steps = ['step-1', 'step-2', 'step-3', 'step-4', 'step-5'];
    steps.forEach(stepId => {
        const stepElement = document.getElementById(stepId);
        if (stepElement) {
            stepElement.classList.remove('completed', 'loading', 'failed');
            stepElement.classList.add('pending');
        }
    });
    
    // Reset main progress bar
    const mainProgress = document.getElementById('mainProgress');
    if (mainProgress) {
        mainProgress.style.width = '0%';
        mainProgress.textContent = '0%';
    }
    
    console.log('表单和状态已重置');
}

// Assuming other functions like processAssetCreation, updateStepStatus, getAuthHeaders, 
// getWalletAddress, showToast, uploadedImages, uploadedDocuments, renderImages, 
// renderDocuments, CONFIG, initializeCreatePage exist in the parts of the file I cannot see.

// Make sure to attach event listeners correctly
document.addEventListener('DOMContentLoaded', initializeCreatePage);
document.addEventListener('turbo:load', initializeCreatePage);

// Example of how a reset button might be wired
const resetButton = document.getElementById('resetFormButton');
if(resetButton) {
    resetButton.addEventListener('click', resetCreateForm);
}