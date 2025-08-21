// ... (The rest of the file)
// The `resetForm` function is not defined anywhere, so I will add it.

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

// Make sure to attach event listeners correctly
document.addEventListener('DOMContentLoaded', initializeCreatePage);
document.addEventListener('turbo:load', initializeCreatePage);

// Example of how a reset button might be wired
const resetButton = document.getElementById('resetFormButton');
if(resetButton) {
    resetButton.addEventListener('click', resetCreateForm);
}