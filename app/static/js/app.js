// ===========================
// VARIABLES GLOBALES
// ===========================
let currentPage = 1;
let totalPages = 1;
let totalCount = 0;
let isLoadingMore = false;
let lastQuery = '';
let lastSearchType = 'todo';
let activeFilters = {};
let availableFilters = {};
let currentSortOrder = 'monto_desc';
const perPage = 50;

// ===========================
// Inicialización
// ===========================
document.addEventListener('DOMContentLoaded', function() {
    // Event listener para buscar con Enter
    document.getElementById('searchInput').addEventListener('keypress', function(e) {
        if (e.key === 'Enter') {
            buscar();
        }
    });

    // Event listeners para los tabs
    document.querySelectorAll('.search-tab').forEach(tab => {
        tab.addEventListener('click', function() {
            // Quitar active de todos los tabs
            document.querySelectorAll('.search-tab').forEach(t => {
                t.classList.remove('active');
            });

            // Activar este tab
            this.classList.add('active');

            // Cambiar placeholder del input
            const placeholder = this.dataset.placeholder;
            document.getElementById('searchInput').placeholder = placeholder;

            // Enfocar el input
            document.getElementById('searchInput').focus();
        });
    });
});

// ===========================
// Toggle Search Help
// ===========================
function toggleSearchHelp() {
    const helpPanel = document.getElementById('searchHelp');
    helpPanel.classList.toggle('hidden');
}

// ===========================
// Función principal de búsqueda
// ===========================
async function buscar(resetFilters = true) {
    const query = document.getElementById('searchInput').value.trim();
    if (!query) {
        mostrarError('Por favor ingresa un término de búsqueda');
        return;
    }

    // Obtener el tipo de búsqueda del tab activo
    const activeTab = document.querySelector('.search-tab.active');
    const searchType = activeTab ? activeTab.dataset.type : 'todo';
    lastQuery = query;
    lastSearchType = searchType;

    if (resetFilters) {
        activeFilters = {};
    }

    currentPage = 1;

    document.getElementById('loading').classList.remove('hidden');
    document.getElementById('resultsArea').classList.add('hidden');
    document.getElementById('errorMessage').classList.add('hidden');

    try {
        const response = await fetch('/api/search', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                query: query,
                search_type: searchType,
                filters: activeFilters,
                sort: currentSortOrder,
                page: 1,
                per_page: perPage
            })
        });

        document.getElementById('loading').classList.add('hidden');

        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.error || `Error HTTP: ${response.status}`);
        }

        const data = await response.json();

        if (!data || data.total === 0) {
            mostrarError('No se encontraron resultados para tu búsqueda');
            return;
        }

        totalCount = data.total;
        totalPages = Math.ceil(totalCount / perPage);

        document.getElementById('resultsArea').classList.remove('hidden');

        // Renderizar componentes
        renderResultsSummary(data, searchType);
        renderFilters(data.filtros_disponibles || {});
        renderAggregates(data, searchType);

        // SIEMPRE mostrar contratos (son el contenido principal)
        if (data.contratos && data.contratos.length > 0) {
            renderContracts(data.contratos);
            document.getElementById('contratosSection').classList.remove('hidden');
            renderPaginationControls();
        } else {
            document.getElementById('contratosSection').classList.add('hidden');
        }

        updateActiveFiltersDisplay();

    } catch (error) {
        console.error('Error en búsqueda:', error);
        document.getElementById('loading').classList.add('hidden');
        mostrarError(error.message || 'Error al realizar la búsqueda. Por favor intenta de nuevo.');
    }
}

// ===========================
// Render del resumen de resultados
// ===========================
function renderResultsSummary(data, searchType) {
    const searchTypeLabels = {
        'todo': 'Búsqueda general',
        'institucion': 'Institución',
        'empresa': 'Proveedor',
        'descripcion': 'Descripción',
        'titulo': 'Título',
        'rfc': 'RFC'
    };

    const summaryHtml = `
        <strong>Resultados para:</strong> "${data.query}" |
        <strong>Tipo:</strong> ${searchTypeLabels[searchType] || searchType} |
        <strong>Total:</strong> ${data.total.toLocaleString()} contratos |
        <strong>Monto total:</strong> ${formatMoney(data.monto_total)}
    `;
    document.getElementById('resultsSummary').innerHTML = summaryHtml;
}

// ===========================
// Render de filtros en sidebar
// ===========================
function renderFilters(filtros) {
    if (!filtros || Object.keys(filtros).length === 0) {
        document.getElementById('filtersSidebar').classList.add('hidden');
        return;
    }

    availableFilters = filtros;
    document.getElementById('filtersSidebar').classList.remove('hidden');

    const filterSections = document.getElementById('filterSections');
    filterSections.innerHTML = '';

    const filterConfigs = [
        { key: 'instituciones', label: 'Institución', searchable: true },
        { key: 'tipos', label: 'Tipo de Contratación', searchable: false },
        { key: 'procedimientos', label: 'Procedimiento', searchable: false },
        { key: 'anios', label: 'Año', searchable: false },
        { key: 'estatus', label: 'Estatus', searchable: false }
    ];

    filterConfigs.forEach(config => {
        if (filtros[config.key] && Object.keys(filtros[config.key]).length > 0) {
            const sectionHtml = createFilterSection(config, filtros[config.key]);
            filterSections.insertAdjacentHTML('beforeend', sectionHtml);
        }
    });

    // Agregar event listeners para collapse
    document.querySelectorAll('.filter-section-header').forEach(header => {
        header.addEventListener('click', function() {
            this.parentElement.classList.toggle('collapsed');
        });
    });

    // Event listeners para checkboxes
    document.querySelectorAll('.filter-option-item input[type="checkbox"]').forEach(checkbox => {
        checkbox.addEventListener('change', handleFilterChange);
    });

    // Event listeners para búsquedas en filtros
    document.querySelectorAll('.filter-search input').forEach(input => {
        input.addEventListener('input', function(e) {
            filterOptions(e.target);
        });
    });
}

function createFilterSection(config, options) {
    const optionsArray = Object.entries(options).sort((a, b) => b[1] - a[1]);
    const showLimit = 10;
    const hasMore = optionsArray.length > showLimit;
    const visibleOptions = optionsArray.slice(0, showLimit);

    let searchHtml = '';
    if (config.searchable) {
        searchHtml = `
            <div class="filter-search">
                <input type="text" placeholder="Buscar ${config.label.toLowerCase()}..." data-filter-type="${config.key}">
            </div>
        `;
    }

    let optionsHtml = visibleOptions.map(([name, count]) => {
        const isChecked = activeFilters[config.key] && activeFilters[config.key].includes(name);
        return `
            <label class="filter-option-item">
                <input type="checkbox"
                       value="${escapeHtml(name)}"
                       data-filter-type="${config.key}"
                       ${isChecked ? 'checked' : ''}>
                <span class="filter-option-label">
                    <span>${escapeHtml(name)}</span>
                    <span class="filter-option-count">${count.toLocaleString()}</span>
                </span>
            </label>
        `;
    }).join('');

    if (hasMore) {
        optionsHtml += `<button class="filter-show-more" data-filter-type="${config.key}" onclick="showMoreOptions('${config.key}')">+ Ver ${optionsArray.length - showLimit} más</button>`;
    }

    return `
        <div class="filter-section" data-filter-type="${config.key}">
            <div class="filter-section-header">
                <h4>${config.label}</h4>
                <span class="filter-section-toggle">▼</span>
            </div>
            <div class="filter-section-content">
                ${searchHtml}
                <div class="filter-options-list" data-filter-type="${config.key}">
                    ${optionsHtml}
                </div>
            </div>
        </div>
    `;
}

function showMoreOptions(filterType) {
    // TODO: Implementar mostrar todas las opciones
    console.log('Showing more options for', filterType);
}

function filterOptions(input) {
    const filterType = input.dataset.filterType;
    const searchTerm = input.value.toLowerCase();
    const optionsList = document.querySelector(`.filter-options-list[data-filter-type="${filterType}"]`);
    const options = optionsList.querySelectorAll('.filter-option-item');

    options.forEach(option => {
        const label = option.querySelector('.filter-option-label span').textContent.toLowerCase();
        if (label.includes(searchTerm)) {
            option.style.display = 'flex';
        } else {
            option.style.display = 'none';
        }
    });
}

function handleFilterChange(e) {
    const filterType = e.target.dataset.filterType;
    const value = e.target.value;
    const isChecked = e.target.checked;

    if (!activeFilters[filterType]) {
        activeFilters[filterType] = [];
    }

    if (isChecked) {
        if (!activeFilters[filterType].includes(value)) {
            activeFilters[filterType].push(value);
        }
    } else {
        activeFilters[filterType] = activeFilters[filterType].filter(v => v !== value);
        if (activeFilters[filterType].length === 0) {
            delete activeFilters[filterType];
        }
    }

    // Actualizar vista de filtros activos
    updateActiveFiltersDisplay();

    // Re-ejecutar búsqueda
    buscar(false);
}

function updateActiveFiltersDisplay() {
    const section = document.getElementById('activeFiltersSection');
    const list = document.getElementById('activeFiltersList');

    if (Object.keys(activeFilters).length === 0) {
        section.classList.add('hidden');
        return;
    }

    section.classList.remove('hidden');

    let html = '';
    for (const [type, values] of Object.entries(activeFilters)) {
        values.forEach(value => {
            html += `
                <div class="active-filter-item">
                    <span>${escapeHtml(value)}</span>
                    <button onclick="removeFilter('${escapeHtml(type)}', '${escapeHtml(value)}')">&times;</button>
                </div>
            `;
        });
    }
    list.innerHTML = html;
}

function removeFilter(type, value) {
    if (activeFilters[type]) {
        activeFilters[type] = activeFilters[type].filter(v => v !== value);
        if (activeFilters[type].length === 0) {
            delete activeFilters[type];
        }
    }

    // Desmarcar checkbox
    const checkbox = document.querySelector(`input[type="checkbox"][data-filter-type="${type}"][value="${value}"]`);
    if (checkbox) {
        checkbox.checked = false;
    }

    updateActiveFiltersDisplay();
    buscar(false);
}

function clearAllFilters() {
    activeFilters = {};

    // Desmarcar todos los checkboxes
    document.querySelectorAll('.filter-option-item input[type="checkbox"]').forEach(cb => {
        cb.checked = false;
    });

    updateActiveFiltersDisplay();
    buscar(false);
}

// ===========================
// Render de agregados
// ===========================
function renderAggregates(data, searchType) {
    // Mostrar proveedores
    if (data.proveedores && data.proveedores.length > 0) {
        renderProviders(data.proveedores);
        document.getElementById('empresasSection').classList.remove('hidden');
    } else {
        document.getElementById('empresasSection').classList.add('hidden');
    }

    // Mostrar instituciones
    if (data.instituciones && data.instituciones.length > 0) {
        renderInstitutions(data.instituciones);
        document.getElementById('institucionesSection').classList.remove('hidden');
    } else {
        document.getElementById('institucionesSection').classList.add('hidden');
    }
}

// Variables globales para almacenar todos los datos
let allProviders = [];
let allInstitutions = [];
let hiddenProviders = new Set();
let hiddenInstitutions = new Set();

function renderProviders(proveedores) {
    // Guardar todos los proveedores
    if (proveedores && proveedores.length > 0) {
        allProviders = proveedores;
    }

    // Filtrar proveedores ocultos
    const visibleProviders = allProviders.filter(prov => !hiddenProviders.has(prov.nombre));

    const html = visibleProviders.map(prov => `
        <div class="aggregate-item" data-name="${escapeHtml(prov.nombre)}">
            <div class="aggregate-info">
                <div class="aggregate-name">${escapeHtml(prov.nombre || 'Sin nombre')}</div>
                <div class="aggregate-details">
                    ${prov.rfc && prov.rfc !== 'RFC Genérico' ? 'RFC: ' + escapeHtml(prov.rfc) + ' | ' : ''}
                    ${prov.num_contratos} contratos
                </div>
            </div>
            <div class="aggregate-amount">${formatMoney(prov.monto_total)}</div>
            <button class="aggregate-remove" onclick="hideProvider('${escapeHtml(prov.nombre).replace(/'/g, "\\'")}'); event.stopPropagation();" title="Ocultar este proveedor">×</button>
        </div>
    `).join('');

    document.getElementById('empresasList').innerHTML = html;

    // Mostrar mensaje si hay proveedores ocultos
    if (hiddenProviders.size > 0) {
        const messageHtml = `
            <div class="hidden-items-message">
                ${hiddenProviders.size} proveedor(es) oculto(s).
                <button onclick="resetProviders()">Mostrar todos</button>
            </div>
        `;
        document.getElementById('empresasList').insertAdjacentHTML('afterbegin', messageHtml);
    }
}

function renderInstitutions(instituciones) {
    // Guardar todas las instituciones
    if (instituciones && instituciones.length > 0) {
        allInstitutions = instituciones;
    }

    // Filtrar instituciones ocultas
    const visibleInstitutions = allInstitutions.filter(inst => !hiddenInstitutions.has(inst.siglas));

    const html = visibleInstitutions.map(inst => `
        <div class="aggregate-item" data-siglas="${escapeHtml(inst.siglas)}">
            <div class="aggregate-info">
                <div class="aggregate-name">${escapeHtml(inst.nombre || inst.siglas)}</div>
                <div class="aggregate-details">
                    ${escapeHtml(inst.siglas)} | ${inst.num_contratos} contratos
                </div>
            </div>
            <div class="aggregate-amount">${formatMoney(inst.monto_total)}</div>
            <button class="aggregate-remove" onclick="hideInstitution('${escapeHtml(inst.siglas).replace(/'/g, "\\'")}'); event.stopPropagation();" title="Ocultar esta institución">×</button>
        </div>
    `).join('');

    document.getElementById('institucionesList').innerHTML = html;

    // Mostrar mensaje si hay instituciones ocultas
    if (hiddenInstitutions.size > 0) {
        const messageHtml = `
            <div class="hidden-items-message">
                ${hiddenInstitutions.size} institución(es) oculta(s).
                <button onclick="resetInstitutions()">Mostrar todas</button>
            </div>
        `;
        document.getElementById('institucionesList').insertAdjacentHTML('afterbegin', messageHtml);
    }
}

// Funciones para ocultar/mostrar proveedores
function hideProvider(nombre) {
    hiddenProviders.add(nombre);
    renderProviders();
}

function resetProviders() {
    hiddenProviders.clear();
    renderProviders();
}

// Funciones para ocultar/mostrar instituciones
function hideInstitution(siglas) {
    hiddenInstitutions.add(siglas);
    renderInstitutions();
}

function resetInstitutions() {
    hiddenInstitutions.clear();
    renderInstitutions();
}

async function showAllProviders() {
    if (!lastQuery) {
        mostrarError('Por favor realiza una búsqueda primero');
        return;
    }

    document.getElementById('loading').classList.remove('hidden');

    try {
        const response = await fetch('/api/all-providers', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                query: lastQuery,
                search_type: lastSearchType,
                filters: activeFilters
            })
        });

        document.getElementById('loading').classList.add('hidden');

        if (!response.ok) {
            throw new Error('Error al obtener proveedores');
        }

        const data = await response.json();

        if (data.top_proveedores && data.top_proveedores.length > 0) {
            // Renderizar TODOS los proveedores
            renderProviders(data.top_proveedores);

            // Actualizar el título de la sección
            const empresasSection = document.getElementById('empresasSection');
            const title = empresasSection.querySelector('h2');
            if (title) {
                title.textContent = `TODOS LOS PROVEEDORES (${data.top_proveedores.length})`;
            }

            // Scroll suave a la sección de proveedores
            empresasSection.scrollIntoView({ behavior: 'smooth', block: 'start' });
        } else {
            mostrarError('No se encontraron proveedores');
        }

    } catch (error) {
        console.error('Error al obtener todos los proveedores:', error);
        document.getElementById('loading').classList.add('hidden');
        mostrarError('Error al obtener la lista completa de proveedores');
    }
}

async function showAllInstitutions() {
    if (!lastQuery) {
        mostrarError('Por favor realiza una búsqueda primero');
        return;
    }

    document.getElementById('loading').classList.remove('hidden');

    try {
        const response = await fetch('/api/all-institutions', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                query: lastQuery,
                search_type: lastSearchType,
                filters: activeFilters
            })
        });

        document.getElementById('loading').classList.add('hidden');

        if (!response.ok) {
            throw new Error('Error al obtener instituciones');
        }

        const data = await response.json();

        if (data.top_instituciones && data.top_instituciones.length > 0) {
            // Renderizar TODAS las instituciones
            renderInstitutions(data.top_instituciones);

            // Actualizar el título de la sección
            const institucionesSection = document.getElementById('institucionesSection');
            const title = institucionesSection.querySelector('h2');
            if (title) {
                title.textContent = `TODAS LAS INSTITUCIONES (${data.top_instituciones.length})`;
            }

            // Scroll suave a la sección de instituciones
            institucionesSection.scrollIntoView({ behavior: 'smooth', block: 'start' });
        } else {
            mostrarError('No se encontraron instituciones');
        }

    } catch (error) {
        console.error('Error al obtener todas las instituciones:', error);
        document.getElementById('loading').classList.add('hidden');
        mostrarError('Error al obtener la lista completa de instituciones');
    }
}

// ===========================
// Render de contratos como tarjetas
// ===========================
function renderContracts(contratos) {
    const formatDate = (dateStr) => {
        if (!dateStr) return 'N/D';
        const date = new Date(dateStr);
        return date.toLocaleDateString('es-MX', { year: 'numeric', month: 'short', day: 'numeric' });
    };

    const html = contratos.map(contrato => `
        <div class="contract-card-compact">
            <div class="contract-header">
                <div class="contract-title-compact">
                    ${escapeHtml(contrato.titulo || 'Sin título')}
                </div>
                <div class="contract-amount-badge">
                    ${formatMoney(contrato.importe)}
                </div>
            </div>

            <div class="contract-meta">
                <div class="contract-meta-item">
                    <div class="meta-label">Proveedor</div>
                    <div class="meta-value">${escapeHtml(contrato.proveedor || 'No especificado')}</div>
                </div>
                <div class="contract-meta-item">
                    <div class="meta-label">Institución</div>
                    <div class="meta-value">${escapeHtml(contrato.siglas_institucion || 'N/D')}</div>
                </div>
                <div class="contract-meta-item">
                    <div class="meta-label">Procedimiento</div>
                    <div class="meta-value">${escapeHtml(contrato.tipo_procedimiento || 'N/D')}</div>
                </div>
                <div class="contract-meta-item">
                    <div class="meta-label">Período</div>
                    <div class="meta-value">${formatDate(contrato.fecha_inicio)} - ${formatDate(contrato.fecha_fin)}</div>
                </div>
            </div>

            ${contrato.descripcion ? `
                <div class="contract-description-compact">
                    ${escapeHtml(contrato.descripcion)}
                </div>
            ` : ''}

            <div class="contract-footer">
                <div class="contract-badges">
                    ${contrato.anio_fuente ? `<span class="contract-badge">${contrato.anio_fuente}</span>` : ''}
                    ${contrato.estatus ? `<span class="contract-badge">${escapeHtml(contrato.estatus)}</span>` : ''}
                </div>
                ${contrato.direccion_anuncio ? `
                    <a href="${escapeHtml(contrato.direccion_anuncio)}" target="_blank" rel="noopener noreferrer" class="contract-link-btn">
                        Ver contrato →
                    </a>
                ` : ''}
            </div>
        </div>
    `).join('');

    document.getElementById('contratosList').innerHTML = html;

    // Actualizar contador
    document.getElementById('resultsCount').innerHTML = `
        Mostrando <strong>${((currentPage - 1) * perPage) + 1}-${Math.min(currentPage * perPage, totalCount)}</strong>
        de <strong>${totalCount.toLocaleString()}</strong> contratos
    `;
}

// ===========================
// Paginación
// ===========================
function renderPaginationControls() {
    const controls = document.getElementById('paginationControls');

    if (totalPages <= 1) {
        controls.classList.add('hidden');
        return;
    }

    controls.classList.remove('hidden');

    document.getElementById('currentPageNum').textContent = currentPage;
    document.getElementById('totalPagesNum').textContent = totalPages;
    document.getElementById('pageJumpInput').value = currentPage;
    document.getElementById('pageJumpInput').max = totalPages;

    document.getElementById('prevPageBtn').disabled = currentPage === 1;
    document.getElementById('nextPageBtn').disabled = currentPage === totalPages;
}

async function goToNextPage() {
    if (currentPage < totalPages) {
        currentPage++;
        await loadPage(currentPage);
    }
}

async function goToPrevPage() {
    if (currentPage > 1) {
        currentPage--;
        await loadPage(currentPage);
    }
}

async function jumpToPage() {
    const input = document.getElementById('pageJumpInput');
    const page = parseInt(input.value);

    if (page >= 1 && page <= totalPages && page !== currentPage) {
        currentPage = page;
        await loadPage(currentPage);
    }
}

async function loadPage(page) {
    document.getElementById('loading').classList.remove('hidden');

    try {
        const response = await fetch('/api/search', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                query: lastQuery,
                search_type: lastSearchType,
                filters: activeFilters,
                sort: currentSortOrder,
                page: page,
                per_page: perPage
            })
        });

        document.getElementById('loading').classList.add('hidden');

        if (!response.ok) {
            throw new Error(`HTTP ${response.status}`);
        }

        const data = await response.json();

        if (data.contratos && data.contratos.length > 0) {
            renderContracts(data.contratos);
            renderPaginationControls();

            // Scroll al inicio de la sección de contratos
            document.getElementById('contratosSection').scrollIntoView({ behavior: 'smooth', block: 'start' });
        }

    } catch (error) {
        console.error('Error cargando página:', error);
        document.getElementById('loading').classList.add('hidden');
        mostrarError('Error al cargar la página. Por favor intenta de nuevo.');
    }
}

// ===========================
// Ordenamiento
// ===========================
async function changeSortOrder() {
    const select = document.getElementById('sortSelect');
    currentSortOrder = select.value;
    currentPage = 1;
    await loadPage(1);
}

// ===========================
// Funciones auxiliares
// ===========================
function formatMoney(amount) {
    if (amount === null || amount === undefined || isNaN(amount)) return '$0.00';
    return '$' + Number(amount).toLocaleString('es-MX', {
        minimumFractionDigits: 2,
        maximumFractionDigits: 2
    });
}

function mostrarError(mensaje) {
    const errorDiv = document.getElementById('errorMessage');
    errorDiv.textContent = mensaje;
    errorDiv.classList.remove('hidden');
    document.getElementById('resultsArea').classList.add('hidden');
}

function escapeHtml(text) {
    if (!text) return '';
    const map = {
        '&': '&amp;',
        '<': '&lt;',
        '>': '&gt;',
        '"': '&quot;',
        "'": '&#039;'
    };
    return text.toString().replace(/[&<>"']/g, m => map[m]);
}

// ===========================
// Exportar a PDF
// ===========================
async function exportToPDF() {
    if (!lastQuery) {
        mostrarError('Por favor realiza una búsqueda primero');
        return;
    }

    const btn = document.getElementById('exportPdfBtn');
    btn.disabled = true;
    btn.textContent = 'Generando PDF...';

    try {
        // Obtener datos completos
        const [providersResponse, institutionsResponse, contractsResponse] = await Promise.all([
            fetch('/api/all-providers', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    query: lastQuery,
                    search_type: lastSearchType,
                    filters: activeFilters
                })
            }),
            fetch('/api/all-institutions', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    query: lastQuery,
                    search_type: lastSearchType,
                    filters: activeFilters
                })
            }),
            fetch('/api/all-contracts', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    query: lastQuery,
                    search_type: lastSearchType,
                    filters: activeFilters,
                    sort: currentSortOrder
                })
            })
        ]);

        const providers = await providersResponse.json();
        const institutions = await institutionsResponse.json();
        const contracts = await contractsResponse.json();

        // Crear PDF usando jsPDF
        const { jsPDF } = window.jspdf;
        const doc = new jsPDF('p', 'mm', 'a4');

        let yPos = 20;
        const pageWidth = doc.internal.pageSize.getWidth();
        const pageHeight = doc.internal.pageSize.getHeight();
        const margin = 15;
        const maxWidth = pageWidth - (margin * 2);

        // Portada
        doc.setFontSize(24);
        doc.setFont(undefined, 'bold');
        doc.text('LaLupa', pageWidth / 2, yPos, { align: 'center' });

        yPos += 10;
        doc.setFontSize(16);
        doc.text('Reporte de Contratos Gubernamentales', pageWidth / 2, yPos, { align: 'center' });

        yPos += 15;
        doc.setFontSize(12);
        doc.setFont(undefined, 'normal');
        doc.text(`Búsqueda: ${lastQuery}`, margin, yPos);
        yPos += 7;
        doc.text(`Tipo: ${lastSearchType}`, margin, yPos);
        yPos += 7;
        doc.text(`Fecha: ${new Date().toLocaleDateString('es-MX', {
            year: 'numeric',
            month: 'long',
            day: 'numeric'
        })}`, margin, yPos);

        yPos += 15;
        doc.setFontSize(14);
        doc.setFont(undefined, 'bold');
        doc.text('Resumen', margin, yPos);

        yPos += 8;
        doc.setFontSize(11);
        doc.setFont(undefined, 'normal');
        doc.text(`Total de contratos: ${totalCount.toLocaleString()}`, margin, yPos);
        yPos += 6;
        doc.text(`Monto total: ${formatMoney(providers.top_proveedores.reduce((sum, p) => sum + p.monto_total, 0))}`, margin, yPos);
        yPos += 6;
        doc.text(`Proveedores: ${providers.top_proveedores.length}`, margin, yPos);
        yPos += 6;
        doc.text(`Instituciones: ${institutions.top_instituciones.length}`, margin, yPos);

        // Nueva página para proveedores
        doc.addPage();
        yPos = 20;

        doc.setFontSize(16);
        doc.setFont(undefined, 'bold');
        doc.text('Top Proveedores', margin, yPos);
        yPos += 10;

        // Tabla de proveedores
        const providerData = providers.top_proveedores.slice(0, 50).map(p => [
            p.nombre,
            p.rfc,
            p.num_contratos.toString(),
            formatMoney(p.monto_total)
        ]);

        doc.autoTable({
            startY: yPos,
            head: [['Proveedor', 'RFC', 'Contratos', 'Monto Total']],
            body: providerData,
            theme: 'grid',
            headStyles: { fillColor: [0, 122, 255], textColor: 255, fontStyle: 'bold' },
            styles: { fontSize: 9, cellPadding: 3 },
            columnStyles: {
                0: { cellWidth: 70 },
                1: { cellWidth: 35 },
                2: { cellWidth: 25, halign: 'center' },
                3: { cellWidth: 35, halign: 'right' }
            },
            margin: { left: margin, right: margin }
        });

        // Nueva página para instituciones
        doc.addPage();
        yPos = 20;

        doc.setFontSize(16);
        doc.setFont(undefined, 'bold');
        doc.text('Top Instituciones', margin, yPos);
        yPos += 10;

        // Tabla de instituciones
        const institutionData = institutions.top_instituciones.slice(0, 50).map(i => [
            i.siglas,
            i.nombre,
            i.num_contratos.toString(),
            formatMoney(i.monto_total)
        ]);

        doc.autoTable({
            startY: yPos,
            head: [['Siglas', 'Institución', 'Contratos', 'Monto Total']],
            body: institutionData,
            theme: 'grid',
            headStyles: { fillColor: [0, 122, 255], textColor: 255, fontStyle: 'bold' },
            styles: { fontSize: 9, cellPadding: 3 },
            columnStyles: {
                0: { cellWidth: 25 },
                1: { cellWidth: 70 },
                2: { cellWidth: 25, halign: 'center' },
                3: { cellWidth: 35, halign: 'right' }
            },
            margin: { left: margin, right: margin }
        });

        // Nueva página para contratos - DETALLE COMPLETO
        doc.addPage();
        yPos = 20;

        doc.setFontSize(16);
        doc.setFont(undefined, 'bold');
        doc.text('Detalle Completo de Contratos', margin, yPos);
        yPos += 5;

        doc.setFontSize(10);
        doc.setFont(undefined, 'normal');
        if (contracts.limited) {
            doc.text('(Mostrando los primeros 1,000 contratos)', margin, yPos);
        } else {
            doc.text(`(Total: ${contracts.total_returned} contratos)`, margin, yPos);
        }
        yPos += 12;

        // Renderizar cada contrato con TODOS sus detalles
        contracts.contratos.forEach((contrato, index) => {
            // Verificar si necesitamos una nueva página
            if (yPos > pageHeight - 60) {
                doc.addPage();
                yPos = 20;
            }

            // Número de contrato
            doc.setFontSize(11);
            doc.setFont(undefined, 'bold');
            doc.text(`Contrato #${index + 1}`, margin, yPos);
            yPos += 6;

            // Crear tabla con toda la información del contrato
            const contratoData = [];

            // Información básica
            if (contrato.codigo_contrato) {
                contratoData.push(['Código de Contrato', contrato.codigo_contrato]);
            }
            if (contrato.titulo) {
                contratoData.push(['Título', contrato.titulo]);
            }
            if (contrato.descripcion) {
                contratoData.push(['Descripción', contrato.descripcion]);
            }

            // Proveedor
            if (contrato.proveedor) {
                contratoData.push(['Proveedor', contrato.proveedor]);
            }
            if (contrato.rfc) {
                contratoData.push(['RFC', contrato.rfc]);
            }

            // Institución
            if (contrato.institucion) {
                contratoData.push(['Institución', contrato.institucion]);
            }
            if (contrato.siglas_institucion) {
                contratoData.push(['Siglas Institución', contrato.siglas_institucion]);
            }
            if (contrato.unidad_compradora) {
                contratoData.push(['Unidad Compradora', contrato.unidad_compradora]);
            }
            if (contrato.responsable) {
                contratoData.push(['Responsable', contrato.responsable]);
            }

            // Montos y fechas
            if (contrato.importe != null) {
                contratoData.push(['Importe', formatMoney(contrato.importe)]);
            }
            if (contrato.fecha_inicio) {
                contratoData.push(['Fecha Inicio', new Date(contrato.fecha_inicio).toLocaleDateString('es-MX')]);
            }
            if (contrato.fecha_fin) {
                contratoData.push(['Fecha Fin', new Date(contrato.fecha_fin).toLocaleDateString('es-MX')]);
            }

            // Procedimiento
            if (contrato.tipo_contratacion) {
                contratoData.push(['Tipo Contratación', contrato.tipo_contratacion]);
            }
            if (contrato.tipo_procedimiento) {
                contratoData.push(['Tipo Procedimiento', contrato.tipo_procedimiento]);
            }
            if (contrato.forma_procedimiento) {
                contratoData.push(['Forma Procedimiento', contrato.forma_procedimiento]);
            }
            if (contrato.caracter) {
                contratoData.push(['Carácter', contrato.caracter]);
            }

            // Estado y clasificación
            if (contrato.estatus) {
                contratoData.push(['Estatus', contrato.estatus]);
            }
            if (contrato.clave_cucop) {
                contratoData.push(['Clave CUCOP', contrato.clave_cucop]);
            }
            if (contrato.titulo_cucop) {
                contratoData.push(['Título CUCOP', contrato.titulo_cucop]);
            }

            // Ubicación
            if (contrato.entidad_federativa) {
                contratoData.push(['Entidad Federativa', contrato.entidad_federativa]);
            }
            if (contrato.municipio) {
                contratoData.push(['Municipio', contrato.municipio]);
            }

            // Fuente y año
            if (contrato.anio_fuente) {
                contratoData.push(['Año', contrato.anio_fuente.toString()]);
            }
            if (contrato.fuente) {
                contratoData.push(['Fuente', contrato.fuente]);
            }

            // Enlace al anuncio (IMPORTANTE)
            if (contrato.direccion_anuncio) {
                contratoData.push(['URL del Contrato', contrato.direccion_anuncio]);
            }

            // Información adicional
            if (contrato.numero_expediente) {
                contratoData.push(['No. Expediente', contrato.numero_expediente]);
            }
            if (contrato.referencia) {
                contratoData.push(['Referencia', contrato.referencia]);
            }
            if (contrato.observaciones) {
                contratoData.push(['Observaciones', contrato.observaciones]);
            }

            // Generar tabla con toda la información
            doc.autoTable({
                startY: yPos,
                body: contratoData,
                theme: 'grid',
                styles: {
                    fontSize: 8,
                    cellPadding: 2,
                    overflow: 'linebreak',
                    cellWidth: 'wrap'
                },
                columnStyles: {
                    0: {
                        cellWidth: 45,
                        fontStyle: 'bold',
                        fillColor: [240, 240, 240]
                    },
                    1: {
                        cellWidth: 130,
                        overflow: 'linebreak'
                    }
                },
                margin: { left: margin, right: margin },
                didDrawPage: function(data) {
                    yPos = data.cursor.y;
                }
            });

            yPos = doc.lastAutoTable.finalY + 8;
        });

        // Pie de página en todas las páginas
        const pageCount = doc.internal.getNumberOfPages();
        for (let i = 1; i <= pageCount; i++) {
            doc.setPage(i);
            doc.setFontSize(8);
            doc.setFont(undefined, 'normal');
            doc.text(
                `Página ${i} de ${pageCount} - Generado por LaLupa`,
                pageWidth / 2,
                pageHeight - 10,
                { align: 'center' }
            );
        }

        // Descargar PDF
        const filename = `LaLupa_${lastQuery.replace(/[^a-z0-9]/gi, '_')}_${new Date().toISOString().split('T')[0]}.pdf`;
        doc.save(filename);

        // Mensaje de éxito
        btn.textContent = 'PDF Descargado';
        setTimeout(() => {
            btn.textContent = 'Descargar PDF Completo';
            btn.disabled = false;
        }, 2000);

    } catch (error) {
        console.error('Error generando PDF:', error);
        mostrarError('Error al generar el PDF. Por favor intenta de nuevo.');
        btn.textContent = 'Descargar PDF Completo';
        btn.disabled = false;
    }
}
