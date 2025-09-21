// New Project JavaScript

let currentStep = 1;
let projectData = {};
let uploadedFileData = null;
let selectedLayout = null;

// Initialize page
document.addEventListener('DOMContentLoaded', function() {
    initializeFileUpload('upload-area', 'file-input', handleFileSelect);
    loadLayouts();
    
    // Set default map title based on project name
    document.getElementById('project-name').addEventListener('input', function() {
        const mapTitle = document.getElementById('map-title');
        if (!mapTitle.value) {
            mapTitle.value = `Mapa de Localização - ${this.value}`;
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
    const allowedExtensions = ['shp', 'kml', 'kmz', 'geojson', 'gpx'];
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

// Layout loading and selection
async function loadLayouts() {
    try {
        const layouts = await GISSaaS.getLayouts('location');
        displayLayouts(layouts);
    } catch (error) {
        console.error('Error loading layouts:', error);
        GISSaaS.showAlert('Erro ao carregar layouts', 'danger');
    }
}

function displayLayouts(layouts) {
    const container = document.getElementById('layout-options');
    
    if (!layouts || layouts.length === 0) {
        container.innerHTML = `
            <div class="col-12">
                <div class="alert alert-warning">
                    Nenhum layout disponível no momento.
                </div>
            </div>
        `;
        return;
    }
    
    container.innerHTML = layouts.map(layout => `
        <div class="col-md-6 mb-3">
            <div class="layout-option">
                <input type="radio" name="layout" value="${layout.id}" id="layout-${layout.id}">
                <label for="layout-${layout.id}" class="layout-card">
                    <div class="layout-icon">
                        <i class="fas fa-map"></i>
                    </div>
                    <h5>${layout.name}</h5>
                    <p class="text-muted">${layout.description}</p>
                </label>
            </div>
        </div>
    `).join('');
    
    // Select first layout by default
    if (layouts.length > 0) {
        document.getElementById(`layout-${layouts[0].id}`).checked = true;
        selectedLayout = layouts[0];
    }
    
    // Add change listeners
    document.querySelectorAll('input[name="layout"]').forEach(radio => {
        radio.addEventListener('change', function() {
            selectedLayout = layouts.find(l => l.id === this.value);
        });
    });
}

// Project creation
async function createProject() {
    try {
        // Validate configuration form
        if (!validateConfigForm()) return;
        
        GISSaaS.setLoading('create-project-btn', true);
        
        // Prepare configuration data
        const configData = {
            project: projectData.id,
            layout: selectedLayout.id,
            title: document.getElementById('map-title').value.trim(),
            subtitle: document.getElementById('map-subtitle').value.trim(),
            primary_color: document.getElementById('primary-color').value,
            secondary_color: document.getElementById('secondary-color').value,
            show_scale: document.getElementById('show-scale').checked,
            show_north_arrow: document.getElementById('show-north').checked,
            show_legend: document.getElementById('show-legend').checked,
            additional_info: document.getElementById('additional-info').value.trim()
        };
        
        // Save configuration
        await GISSaaS.saveMapConfiguration(configData);
        
        // Handle logo upload if present
        const logoFile = document.getElementById('logo-upload').files[0];
        if (logoFile) {
            // TODO: Implement logo upload
            console.log('Logo upload not implemented yet');
        }
        
        GISSaaS.showAlert('Projeto criado com sucesso!', 'success');
        
        // Redirect to project page
        setTimeout(() => {
            window.location.href = `/project/${projectData.id}/`;
        }, 1500);
        
    } catch (error) {
        console.error('Error creating project:', error);
        GISSaaS.showAlert(`Erro ao criar projeto: ${error.message}`, 'danger');
        GISSaaS.setLoading('create-project-btn', false);
    }
}

function validateConfigForm() {
    const title = document.getElementById('map-title').value.trim();
    
    if (!title) {
        GISSaaS.showAlert('Por favor, informe o título do mapa.', 'danger');
        document.getElementById('map-title').focus();
        return false;
    }
    
    if (!selectedLayout) {
        GISSaaS.showAlert('Por favor, selecione um layout.', 'danger');
        return false;
    }
    
    return true;
}

// Color picker preview
document.addEventListener('DOMContentLoaded', function() {
    const primaryColor = document.getElementById('primary-color');
    const secondaryColor = document.getElementById('secondary-color');
    
    if (primaryColor) {
        primaryColor.addEventListener('change', updateColorPreview);
    }
    
    if (secondaryColor) {
        secondaryColor.addEventListener('change', updateColorPreview);
    }
});

function updateColorPreview() {
    // TODO: Implement live color preview
    console.log('Color preview update not implemented yet');
}

