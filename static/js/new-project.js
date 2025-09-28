// New Project JavaScript

let currentStep = 1;
let projectData = {};
let uploadedFileData = null;
let selectedMapType = null;
let selectedLayoutStyle = null;

// Initialize page
document.addEventListener('DOMContentLoaded', function() {
    initializeFileUpload('upload-area', 'file-input', handleFileSelect);
    loadLayouts();
    
    // Set default area name based on project name
    document.getElementById('project-name').addEventListener('input', function() {
        const areaName = document.getElementById('area-name');
        if (!areaName.value) {
            // Extract area name from project name if it follows the pattern "Mapa de Localização - Area Name"
            const projectName = this.value;
            const match = projectName.match(/Mapa de Localização - (.+)/i);
            if (match) {
                areaName.value = match[1];
            }
        }
    });
});

// Step navigation
function nextStep(step) {
    if (step === 2) {
        // Validate project form
        if (!validateProjectForm()) return;
        saveProjectData();
    } else if (step === 3) {
        // Check if file is uploaded
        if (!uploadedFileData) {
            GISSaaS.showAlert('Por favor, envie um arquivo GIS antes de continuar.', 'warning');
            return;
        }
    }
    
    showStep(step);
}

function previousStep(step) {
    showStep(step);
}

function showStep(step) {
    // Hide all steps
    document.querySelectorAll('.step-content').forEach(el => {
        el.classList.add('d-none');
    });
    
    // Show current step
    document.getElementById(`step-${step}`).classList.remove('d-none');
    
    // Update step indicators
    updateStepIndicators(step);
    
    currentStep = step;
}

function updateStepIndicators(activeStep) {
    for (let i = 1; i <= 3; i++) {
        const indicator = document.getElementById(`step-${i}-indicator`);
        indicator.classList.remove('active', 'completed');
        
        if (i < activeStep) {
            indicator.classList.add('completed');
        } else if (i === activeStep) {
            indicator.classList.add('active');
        }
    }
}

// Project form validation
function validateProjectForm() {
    const name = document.getElementById('project-name').value.trim();
    
    if (!name) {
        GISSaaS.showAlert('Por favor, informe o nome do projeto.', 'danger');
        document.getElementById('project-name').focus();
        return false;
    }
    
    return true;
}

function saveProjectData() {
    projectData = {
        name: document.getElementById('project-name').value.trim(),
        description: document.getElementById('project-description').value.trim()
    };
}

// File upload handling
function handleFileSelect(file) {
    // Validate file
    if (!validateFile(file)) return;
    
    // Show upload progress
    GISSaaS.showProgress('upload-progress');
    GISSaaS.updateProgress('upload-progress', 0, 'Preparando upload...');
    
    // Create project first if not exists
    createProjectAndUploadFile(file);
}

function validateFile(file) {
    const allowedExtensions = ['kml', 'zip'];
    const maxSize = 50 * 1024 * 1024; // 50MB
    
    const extension = file.name.split('.').pop().toLowerCase();
    
    if (!allowedExtensions.includes(extension)) {
        GISSaaS.showAlert(
            `Formato de arquivo não suportado. Formatos aceitos: ${allowedExtensions.join(', ')}`,
            'danger'
        );
        return false;
    }
    
    if (file.size > maxSize) {
        GISSaaS.showAlert('Arquivo muito grande. Tamanho máximo: 50MB', 'danger');
        return false;
    }
    
    return true;
}

async function createProjectAndUploadFile(file) {
    try {
        // Create project
        GISSaaS.updateProgress('upload-progress', 20, 'Criando projeto...');
        
        const project = await GISSaaS.createProject(projectData.name, projectData.description);
        projectData.id = project.id;
        
        // Upload file
        GISSaaS.updateProgress('upload-progress', 40, 'Enviando arquivo...');
        
        const uploadResult = await GISSaaS.uploadFile(project.id, file);
        
        GISSaaS.updateProgress('upload-progress', 80, 'Processando arquivo...');
        
        // Simulate processing time
        await new Promise(resolve => setTimeout(resolve, 1000));
        
        GISSaaS.updateProgress('upload-progress', 100, 'Concluído!');
        
        // Hide progress and show success
        setTimeout(() => {
            GISSaaS.hideProgress('upload-progress');
            showFileInfo(uploadResult);
            uploadedFileData = uploadResult;
            
            // Enable next button
            document.getElementById('next-to-config').disabled = false;
        }, 500);
        
    } catch (error) {
        console.error('Upload error:', error);
        GISSaaS.hideProgress('upload-progress');
        GISSaaS.showAlert(`Erro no upload: ${error.message}`, 'danger');
    }
}

function showFileInfo(fileData) {
    const fileInfoDiv = document.getElementById('file-info');
    const fileDetailsDiv = document.getElementById('file-details');
    
    fileDetailsDiv.innerHTML = `
        <div class="row">
            <div class="col-md-6">
                <strong>Nome:</strong> ${fileData.original_filename}<br>
                <strong>Tipo:</strong> ${fileData.file_type.toUpperCase()}<br>
                <strong>Tamanho:</strong> ${GISSaaS.formatFileSize(fileData.file_size)}
            </div>
            <div class="col-md-6">
                <strong>Geometria:</strong> ${fileData.geometry_type || 'Detectando...'}<br>
                <strong>Sistema de Coordenadas:</strong> ${fileData.coordinate_system || 'Detectando...'}<br>
                <strong>Status:</strong> <span class="badge bg-success">Processado</span>
            </div>
        </div>
    `;
    
    fileInfoDiv.classList.remove('d-none');
}

// Map types and layout loading
async function loadLayouts() {
    try {
        displayMapTypes();
        setupLayoutStyleListeners();
    } catch (error) {
        console.error('Error loading layouts:', error);
        GISSaaS.showAlert('Erro ao carregar tipos de mapa', 'danger');
    }
}

function displayMapTypes() {
    const container = document.getElementById('map-type-options');
    
    // Definir tipos de mapa - apenas Localização habilitado
    const mapTypes = [
        {
            id: 'location',
            name: 'Mapa de Localização',
            description: 'Layout padrão para mapas de localização',
            icon: 'fas fa-map-marker-alt',
            enabled: true
        },
        {
            id: 'hydrographic',
            name: 'Mapa Hidrográfico Básico',
            description: 'Layout para mapas hidrográficos',
            icon: 'fas fa-water',
            enabled: false
        },
        {
            id: 'hypsometric',
            name: 'Mapa Hipsométrico Padrão',
            description: 'Layout para mapas hipsométricos',
            icon: 'fas fa-mountain',
            enabled: false
        },
        {
            id: 'relief',
            name: 'Mapa de Relevo Simples',
            description: 'Layout básico para mapas de relevo',
            icon: 'fas fa-chart-area',
            enabled: false
        }
    ];
    
    container.innerHTML = mapTypes.map(mapType => `
        <div class="col-md-6 mb-3">
            <div class="novo_projeto-layout-option">
                <input type="radio" name="map-type" value="${mapType.id}" id="map-${mapType.id}" 
                       ${mapType.enabled ? '' : 'disabled'} ${mapType.id === 'location' ? 'checked' : ''}>
                <label for="map-${mapType.id}" class="novo_projeto-layout-card ${mapType.enabled ? '' : 'disabled'}">
                    <div class="novo_projeto-layout-icon">
                        <i class="${mapType.icon}"></i>
                    </div>
                    <h6>${mapType.name}</h6>
                    <p class="text-muted">${mapType.enabled ? mapType.description : 'Em Breve'}</p>
                    ${!mapType.enabled ? '<div class="coming-soon-badge">Em Breve</div>' : ''}
                </label>
            </div>
        </div>
    `).join('');
    
    // Selecionar o tipo de mapa padrão
    selectedMapType = 'location';
    
    // Add change listeners para tipos de mapa habilitados
    document.querySelectorAll('input[name="map-type"]:not([disabled])').forEach(radio => {
        radio.addEventListener('change', function() {
            selectedMapType = this.value;
        });
    });
}

function setupLayoutStyleListeners() {
    // Configurar listeners para estilos de layout
    document.querySelectorAll('input[name="layout-style"]').forEach(radio => {
        radio.addEventListener('change', function() {
            selectedLayoutStyle = this.value;
        });
    });
    
    // Definir estilo padrão
    selectedLayoutStyle = 'classic';
}

// Project creation with map generation
async function createProject() {
    try {
        // Validate configuration form
        if (!validateConfigForm()) return;
        
        // Show processing modal
        showProcessingModal();
        
        // Step 1: Analyze file
        updateProcessingStep(1, 'active');
        await simulateDelay(2000);
        
        // Get or create a layout (for now, use a default layout ID)
        // In a real implementation, you would fetch available layouts from the API
        const defaultLayoutId = await getDefaultLayoutId();
        
        // Prepare configuration data according to the MapConfiguration model
        const configData = {
            project: projectData.id,
            layout: defaultLayoutId, // Required ForeignKey to MapLayout
            title: 'Mapa de Localização', // Título fixo
            subtitle: document.getElementById('area-name').value.trim(),
            primary_color: '#2E8B57', // Default colors
            secondary_color: '#4682B4',
            show_scale: true, // Valores padrão
            show_north_arrow: true,
            show_legend: true,
            additional_info: '' // Optional field
        };
        
        // Complete step 1
        updateProcessingStep(1, 'completed');
        
        // Step 2: Apply template
        updateProcessingStep(2, 'active');
        await simulateDelay(1500);
        
        // Save configuration first
        await GISSaaS.saveMapConfiguration(configData);
        
        await simulateDelay(1500);
        
        // Generate map based on selected style
        let mapResult;
        switch(selectedLayoutStyle) {
            case 'modern':
                mapResult = await GISSaaS.generateModernMap(projectData.id, 'png');
                break;
            case 'vibrant':
                mapResult = await GISSaaS.generateVividMap(projectData.id, 'png');
                break;
            case 'classic':
            default:
                mapResult = await GISSaaS.generateMap(projectData.id, 'png');
                break;
        }
        
        // Complete step 2
        updateProcessingStep(2, 'completed');
        
        // Step 3: Finalize map
        updateProcessingStep(3, 'active');
        await simulateDelay(2000);
        
        // Complete step 3
        updateProcessingStep(3, 'completed');
        
        // Wait a moment to show completion
        await simulateDelay(1000);
        
        // Hide modal and redirect
        hideProcessingModal();
        
        // Redirect to project page
        setTimeout(() => {
            window.location.href = `/project/${projectData.id}/`;
        }, 500);
        
    } catch (error) {
        console.error('Error creating project:', error);
        hideProcessingModal();
        GISSaaS.showAlert(`Erro ao elaborar mapa: ${error.message}`, 'danger');
    }
}

// Modal functions
function showProcessingModal() {
    const modal = new bootstrap.Modal(document.getElementById('processing-modal'));
    modal.show();
    
    // Reset all steps
    resetProcessingSteps();
}

function hideProcessingModal() {
    const modal = bootstrap.Modal.getInstance(document.getElementById('processing-modal'));
    if (modal) {
        modal.hide();
    }
}

function resetProcessingSteps() {
    for (let i = 1; i <= 3; i++) {
        const step = document.getElementById(`process-step-${i}`);
        step.classList.remove('active', 'completed');
    }
}

function updateProcessingStep(stepNumber, status) {
    const step = document.getElementById(`process-step-${stepNumber}`);
    step.classList.remove('active', 'completed');
    step.classList.add(status);
}

function simulateDelay(ms) {
    return new Promise(resolve => setTimeout(resolve, ms));
}

// Get default layout ID
async function getDefaultLayoutId() {
    try {
        // Get layouts from API using the correct endpoint
        const response = await fetch('/api/layouts/by_type/?type=location');
        if (response.ok) {
            const layouts = await response.json();
            if (layouts && layouts.length > 0) {
                return layouts[0].id;
            }
        }
        
        // If specific endpoint fails, try getting all layouts
        const allLayoutsResponse = await fetch('/api/layouts/');
        if (allLayoutsResponse.ok) {
            const allLayouts = await allLayoutsResponse.json();
            const locationLayouts = allLayouts.filter(layout => layout.layout_type === 'location');
            if (locationLayouts.length > 0) {
                return locationLayouts[0].id;
            }
        }
        
        throw new Error('Nenhum layout de localização encontrado');
        
    } catch (error) {
        console.error('Error getting default layout:', error);
        throw error;
    }
}

function validateConfigForm() {
    const areaName = document.getElementById('area-name').value.trim();
    
    if (!areaName) {
        GISSaaS.showAlert('Por favor, informe o nome da área/imóvel.', 'danger');
        document.getElementById('area-name').focus();
        return false;
    }
    
    if (!selectedMapType) {
        GISSaaS.showAlert('Por favor, selecione um tipo de mapa.', 'danger');
        return false;
    }
    
    if (!selectedLayoutStyle) {
        GISSaaS.showAlert('Por favor, selecione um estilo de layout.', 'danger');
        return false;
    }
    
    return true;
}
