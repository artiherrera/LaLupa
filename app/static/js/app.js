// ===========================
// VARIABLES GLOBALES
// ===========================
let currentPage = 1;
let totalPages = 1;
let totalCount = 0;
let currentContracts = null;
let isLoadingMore = false;
let lastQuery = '';
let lastSearchType = 'descripcion';
let activeFilters = {};
let pendingFilters = {};
let availableFilters = {};
const perPage = 20;

// Variables para la tabla
let currentSortColumn = 'importe';
let currentSortOrder = 'desc';
let cachedContracts = [];
let expandedRows = new Set();

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

    // Observer para scroll infinito
    const sentinel = document.getElementById('scrollSentinel');
    if (sentinel) {
        const observer = new IntersectionObserver((entries) => {
            if (entries[0].isIntersecting && !isLoadingMore && currentPage < totalPages) {
                cargarContratos(currentPage + 1, true);
            }
        });
        observer.observe(sentinel);
    }
});

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
        pendingFilters = {};
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
                filters: activeFilters
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

        document.getElementById('resultsArea').classList.remove('hidden');
        renderResultsSummary(data, searchType);

        // Mostrar agregados de forma inteligente según el tipo de búsqueda
        renderAggregatesIntelligent(data, searchType);

        // Si hay filtros aplicados O si es búsqueda específica, mostrar contratos
        if (Object.keys(activeFilters).length > 0 || searchType === 'institucion' || searchType === 'empresa') {
            if (data.contratos && data.contratos.length > 0) {
                renderContratos(data.contratos, false);
                document.getElementById('contratosSection').classList.remove('hidden');
            }
        } else {
            // Solo mostrar contratos si hay filtros aplicados
            document.getElementById('contratosSection').classList.add('hidden');
        }

        if (data.filtros_disponibles) {
            renderFilters(data.filtros_disponibles);
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
        'todo': '📝 Búsqueda general',
        'institucion': '🏢 Institución',
        'empresa': '💼 Proveedor',
        'descripcion': '📝 Descripción',
        'titulo': '📄 Título',
        'rfc': '🔢 RFC'
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
// Render inteligente de agregados según tipo de búsqueda
// ===========================
function renderAggregatesIntelligent(data, searchType) {
    // Si busco por institución, mostrar solo proveedores
    if (searchType === 'institucion') {
        if (data.proveedores && data.proveedores.length > 0) {
            mostrarProveedores(data.proveedores);
            document.getElementById('empresasSection').classList.remove('hidden');
            // Cambiar título
            document.querySelector('#empresasSection h2').textContent = `💼 PROVEEDORES (¿A quién le compra?)`;
        } else {
            document.getElementById('empresasSection').classList.add('hidden');
        }
        // Ocultar instituciones (no tiene sentido mostrarlas)
        document.getElementById('institucionesSection').classList.add('hidden');
    }
    // Si busco por proveedor, mostrar solo instituciones
    else if (searchType === 'empresa') {
        if (data.instituciones && data.instituciones.length > 0) {
            mostrarInstituciones(data.instituciones);
            document.getElementById('institucionesSection').classList.remove('hidden');
            // Cambiar título
            document.querySelector('#institucionesSection h2').textContent = `🏢 CLIENTES (¿A quién le vende?)`;
        } else {
            document.getElementById('institucionesSection').classList.add('hidden');
        }
        // Ocultar proveedores (no tiene sentido mostrarlos)
        document.getElementById('empresasSection').classList.add('hidden');
    }
    // Para búsqueda general, mostrar ambos
    else {
        if (data.proveedores && data.proveedores.length > 0) {
            mostrarProveedores(data.proveedores);
            document.getElementById('empresasSection').classList.remove('hidden');
            document.querySelector('#empresasSection h2').textContent = `🏢 TOP PROVEEDORES`;
        } else {
            document.getElementById('empresasSection').classList.add('hidden');
        }

        if (data.instituciones && data.instituciones.length > 0) {
            mostrarInstituciones(data.instituciones);
            document.getElementById('institucionesSection').classList.remove('hidden');
            document.querySelector('#institucionesSection h2').textContent = `🏛️ TOP INSTITUCIONES`;
        } else {
            document.getElementById('institucionesSection').classList.add('hidden');
        }
    }
}

// ===========================
// Render de agregados (DEPRECADO - usar renderAggregatesIntelligent)
// ===========================
// Esta función se mantiene comentada por compatibilidad
// pero ya no se usa. Reemplazada por renderAggregatesIntelligent()
/*
function renderAggregates(data) {
    if (data.proveedores && data.proveedores.length > 0) {
        mostrarProveedores(data.proveedores);
        document.getElementById('empresasSection').classList.remove('hidden');
    } else {
        document.getElementById('empresasSection').classList.add('hidden');
    }

    if (data.instituciones && data.instituciones.length > 0) {
        mostrarInstituciones(data.instituciones);
        document.getElementById('institucionesSection').classList.remove('hidden');
    } else {
        document.getElementById('institucionesSection').classList.add('hidden');
    }
}
*/

// ===========================
// Render de contratos - TABLA COMPLETA
// ===========================
function renderContratos(contratos, append = false) {
    if (!append) {
        cachedContracts = [...contratos];
        expandedRows.clear();
    } else {
        cachedContracts = [...cachedContracts, ...contratos];
    }

    const sortedContracts = sortContracts(cachedContracts, currentSortColumn, currentSortOrder);

    const formatDate = (dateStr) => {
        if (!dateStr) return 'N/D';
        const date = new Date(dateStr);
        return date.toLocaleDateString('es-MX', { year: 'numeric', month: 'short', day: 'numeric' });
    };

    let html = '';
    
    if (!append) {
        html = `
            <div class="table-container">
                <table class="contracts-table">
                    <thead>
                        <tr>
                            <th onclick="sortTable('titulo')" class="sortable ${currentSortColumn === 'titulo' ? 'active' : ''}">
                                Título
                                ${getSortIcon('titulo')}
                            </th>
                            <th>Descripción</th>
                            <th onclick="sortTable('proveedor')" class="sortable ${currentSortColumn === 'proveedor' ? 'active' : ''}">
                                Proveedor
                                ${getSortIcon('proveedor')}
                            </th>
                            <th onclick="sortTable('anio_fundacion')" class="sortable ${currentSortColumn === 'anio_fundacion' ? 'active' : ''}">
                                Año Fundación
                                ${getSortIcon('anio_fundacion')}
                            </th>
                            <th onclick="sortTable('institucion')" class="sortable ${currentSortColumn === 'institucion' ? 'active' : ''}">
                                Institución
                                ${getSortIcon('institucion')}
                            </th>
                            <th onclick="sortTable('procedimiento')" class="sortable ${currentSortColumn === 'procedimiento' ? 'active' : ''}">
                                Procedimiento
                                ${getSortIcon('procedimiento')}
                            </th>
                            <th onclick="sortTable('fecha')" class="sortable ${currentSortColumn === 'fecha' ? 'active' : ''}">
                                Período
                                ${getSortIcon('fecha')}
                            </th>
                            <th onclick="sortTable('importe')" class="sortable ${currentSortColumn === 'importe' ? 'active' : ''}" style="text-align: right;">
                                Importe
                                ${getSortIcon('importe')}
                            </th>
                            <th style="text-align: center;">Enlace</th>
                        </tr>
                    </thead>
                    <tbody>
        `;
    }

    sortedContracts.forEach((contrato, index) => {
        const titulo = contrato.titulo || 'Sin título';
        const descripcion = contrato.descripcion || 'Sin descripción disponible';
        const rowId = `row-${index}`;
        const isExpanded = expandedRows.has(rowId);
        
        const tituloDisplay = titulo.length > 80 ? titulo.substring(0, 80) + '...' : titulo;
        const descripcionDisplay = descripcion.length > 100 ? descripcion.substring(0, 100) + '...' : descripcion;
        
        const hasMoreTitulo = titulo.length > 80;
        const hasMoreDescripcion = descripcion.length > 100;

        html += `
            <tr data-row-id="${rowId}">
                <td class="cell-title">
                    <div class="cell-content">
                        ${isExpanded || !hasMoreTitulo ? titulo : tituloDisplay}
                        ${hasMoreTitulo ? `<button class="btn-expand" onclick="toggleRow('${rowId}')">${isExpanded ? '▲ Menos' : '▼ Más'}</button>` : ''}
                    </div>
                </td>
                <td class="cell-description">
                    <div class="cell-content">
                        ${isExpanded || !hasMoreDescripcion ? descripcion : descripcionDisplay}
                        ${hasMoreDescripcion ? `<button class="btn-expand" onclick="toggleRow('${rowId}')">${isExpanded ? '▲ Menos' : '▼ Más'}</button>` : ''}
                    </div>
                </td>
                <td>${contrato.proveedor || 'No especificado'}</td>
                <td class="cell-year">${contrato.anio_fundacion_empresa || 'N/D'}</td>
                <td>${contrato.siglas_institucion || 'N/D'}</td>
                <td class="cell-procedure">${contrato.tipo_procedimiento || 'N/D'}</td>
                <td class="cell-date">${formatDate(contrato.fecha_inicio)} - ${formatDate(contrato.fecha_fin)}</td>
                <td class="cell-amount">${formatMoney(contrato.importe)}</td>
                <td class="cell-link" style="text-align: center;">
                    ${contrato.direccion_anuncio ? 
                        `<a href="${contrato.direccion_anuncio}" target="_blank" rel="noopener noreferrer" class="contract-link" title="Ver contrato">
                            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                                <path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6"></path>
                                <polyline points="15 3 21 3 21 9"></polyline>
                                <line x1="10" y1="14" x2="21" y2="3"></line>
                            </svg>
                        </a>` 
                        : '<span style="color: var(--text-quaternary);">N/D</span>'
                    }
                </td>
            </tr>
        `;
    });

    if (!append) {
        html += `
                    </tbody>
                </table>
            </div>
        `;
        document.getElementById('contratosList').innerHTML = html;
    } else {
        const tbody = document.querySelector('.contracts-table tbody');
        if (tbody) {
            tbody.insertAdjacentHTML('beforeend', html);
        }
    }
}

function toggleRow(rowId) {
    if (expandedRows.has(rowId)) {
        expandedRows.delete(rowId);
    } else {
        expandedRows.add(rowId);
    }
    renderContratos(cachedContracts, false);
}

function sortContracts(contracts, column, order) {
    const sorted = [...contracts].sort((a, b) => {
        let valA, valB;

        switch(column) {
            case 'titulo':
                valA = (a.titulo || '').toLowerCase();
                valB = (b.titulo || '').toLowerCase();
                break;
            case 'proveedor':
                valA = (a.proveedor || '').toLowerCase();
                valB = (b.proveedor || '').toLowerCase();
                break;
            case 'anio_fundacion':
                valA = parseInt(a.anio_fundacion_empresa) || 0;
                valB = parseInt(b.anio_fundacion_empresa) || 0;
                break;
            case 'institucion':
                valA = (a.siglas_institucion || '').toLowerCase();
                valB = (b.siglas_institucion || '').toLowerCase();
                break;
            case 'procedimiento':
                valA = (a.tipo_procedimiento || '').toLowerCase();
                valB = (b.tipo_procedimiento || '').toLowerCase();
                break;
            case 'fecha':
                valA = new Date(a.fecha_inicio || 0);
                valB = new Date(b.fecha_inicio || 0);
                break;
            case 'importe':
                valA = parseFloat(a.importe) || 0;
                valB = parseFloat(b.importe) || 0;
                break;
            default:
                return 0;
        }

        if (valA < valB) return order === 'asc' ? -1 : 1;
        if (valA > valB) return order === 'asc' ? 1 : -1;
        return 0;
    });

    return sorted;
}

function sortTable(column) {
    if (currentSortColumn === column) {
        currentSortOrder = currentSortOrder === 'asc' ? 'desc' : 'asc';
    } else {
        currentSortColumn = column;
        currentSortOrder = (column === 'importe' || column === 'fecha' || column === 'anio_fundacion') ? 'desc' : 'asc';
    }
    renderContratos(cachedContracts, false);
}

function getSortIcon(column) {
    if (currentSortColumn !== column) {
        return '<span class="sort-icon">⇅</span>';
    }
    return currentSortOrder === 'asc' 
        ? '<span class="sort-icon active">↑</span>' 
        : '<span class="sort-icon active">↓</span>';
}

// ===========================
// Mostrar proveedores
// ===========================
function mostrarProveedores(proveedores) {
    let html = '';
    proveedores.forEach(proveedor => {
        const rfc = proveedor.rfc && proveedor.rfc !== 'RFC Genérico' 
            ? proveedor.rfc 
            : 'Sin RFC';
        
        html += `
            <div class="group-item">
                <div class="group-info">
                    <div class="group-name">${proveedor.nombre || 'Sin nombre'}</div>
                    <div class="group-details">
                        RFC: ${rfc} | ${proveedor.num_contratos} contratos
                    </div>
                </div>
                <div class="group-amount">${formatMoney(proveedor.monto_total)}</div>
            </div>
        `;
    });
    document.getElementById('empresasList').innerHTML = html;
}

// ===========================
// Mostrar instituciones
// ===========================
function mostrarInstituciones(instituciones) {
    let html = '';
    instituciones.forEach(inst => {
        html += `
            <div class="group-item">
                <div class="group-info">
                    <div class="group-name">${inst.nombre || inst.siglas}</div>
                    <div class="group-details">
                        ${inst.siglas} | ${inst.num_contratos} contratos
                    </div>
                </div>
                <div class="group-amount">${formatMoney(inst.monto_total)}</div>
            </div>
        `;
    });
    document.getElementById('institucionesList').innerHTML = html;
}

// ===========================
// Render de filtros
// ===========================
function renderFilters(filtros) {
    if (!filtros || Object.keys(filtros).length === 0) {
        document.getElementById('filtersBar').classList.add('hidden');
        return;
    }

    availableFilters = filtros;

    const filterButtons = document.getElementById('filterButtons');
    filterButtons.innerHTML = '';

    const filterConfigs = [
        { key: 'instituciones', label: 'Institución' },
        { key: 'tipos', label: 'Tipo' },
        { key: 'procedimientos', label: 'Procedimiento' },
        { key: 'anios', label: 'Año' },
        { key: 'estatus', label: 'Estatus' }
    ];

    filterConfigs.forEach(config => {
        if (filtros[config.key] && Object.keys(filtros[config.key]).length > 0) {
            const button = document.createElement('button');
            button.className = 'filter-btn';
            button.textContent = `${config.label} (${Object.keys(filtros[config.key]).length})`;
            
            button.addEventListener('click', function() {
                openFilterModal(config.key);
            });
            
            filterButtons.appendChild(button);
        }
    });

    document.getElementById('filtersBar').classList.remove('hidden');
}

// ===========================
// Modal de filtros
// ===========================
let currentFilterType = '';
let currentFilterOptions = {};

function openFilterModal(type) {
    currentFilterType = type;
    currentFilterOptions = availableFilters[type];
    
    if (!currentFilterOptions) {
        return;
    }
    
    const modalEl = document.getElementById('filterModal');
    const modalTitle = document.getElementById('filterModalTitle');
    const modalBody = document.getElementById('filterModalBody');
    
    const titles = {
        'instituciones': 'Filtrar por Institución',
        'tipos': 'Filtrar por Tipo de Contratación',
        'procedimientos': 'Filtrar por Tipo de Procedimiento',
        'anios': 'Filtrar por Año',
        'estatus': 'Filtrar por Estatus'
    };
    modalTitle.textContent = titles[type] || 'Filtrar';
    
    let bodyHtml = '<div class="filter-options">';
    
    const allChecked = !pendingFilters[type] || pendingFilters[type].length === 0;
    const totalCount = Object.values(currentFilterOptions).reduce((sum, count) => sum + count, 0);
    
    bodyHtml += `
        <label class="filter-option filter-option-all">
            <input type="checkbox" 
                   value="__ALL__" 
                   ${allChecked ? 'checked' : ''} 
                   onchange="toggleAllFilters(this)">
            <span><strong>Todos</strong> (${totalCount.toLocaleString()} contratos)</span>
        </label>
        <hr class="filter-divider">
    `;
    
    for (const [key, count] of Object.entries(currentFilterOptions)) {
        const isChecked = pendingFilters[type] && pendingFilters[type].includes(key);
        
        bodyHtml += `
            <label class="filter-option">
                <input type="checkbox" 
                       value="${key}" 
                       ${isChecked ? 'checked' : ''}
                       onchange="uncheckAllIfIndividual()">
                <span>${key} (${count.toLocaleString()})</span>
            </label>
        `;
    }
    
    bodyHtml += '</div>';
    
    modalBody.innerHTML = bodyHtml;
    modalEl.classList.remove('hidden');
}

function closeFilterModal() {
    document.getElementById('filterModal').classList.add('hidden');
}

function toggleAllFilters(checkbox) {
    if (checkbox.checked) {
        const allCheckboxes = document.querySelectorAll(
            '#filterModalBody input[type="checkbox"]:not([value="__ALL__"])'
        );
        allCheckboxes.forEach(cb => cb.checked = false);
    }
}

function uncheckAllIfIndividual() {
    const allCheckbox = document.querySelector('#filterModalBody input[value="__ALL__"]');
    if (allCheckbox) {
        allCheckbox.checked = false;
    }
}

function applyFilters() {
    const checkboxes = document.querySelectorAll(
        '#filterModalBody input[type="checkbox"]:checked:not([value="__ALL__"])'
    );
    const selectedValues = Array.from(checkboxes).map(cb => cb.value);
    
    // SIEMPRE guardar en pendientes, aunque sea vacío (representa "Todos")
    if (selectedValues.length > 0) {
        pendingFilters[currentFilterType] = selectedValues;
    } else {
        // Si no hay nada seleccionado o "Todos" está marcado, guardar como array vacío
        pendingFilters[currentFilterType] = [];
    }
    
    closeFilterModal();
    updatePendingFiltersDisplay();
}

// ===========================
// Gestión de filtros pendientes
// ===========================
function updatePendingFiltersDisplay() {
    const container = document.getElementById('pendingFilterTags');
    const area = document.getElementById('pendingFiltersArea');
    
    // Mostrar el área si hay CUALQUIER filtro pendiente (incluso vacíos)
    if (Object.keys(pendingFilters).length === 0) {
        area.classList.add('hidden');
        return;
    }
    
    area.classList.remove('hidden');
    
    let html = '';
    for (const [type, values] of Object.entries(pendingFilters)) {
        if (values.length === 0) {
            // Si el array está vacío, significa "Todos"
            const labels = {
                'instituciones': 'Todas las instituciones',
                'tipos': 'Todos los tipos',
                'procedimientos': 'Todos los procedimientos',
                'anios': 'Todos los años',
                'estatus': 'Todos los estatus'
            };
            html += `<span class="pending-filter-tag">${labels[type] || 'Todos'}</span>`;
        } else {
            // Mostrar los valores específicos
            values.forEach(value => {
                html += `<span class="pending-filter-tag">${value}</span>`;
            });
        }
    }
    container.innerHTML = html;
}

function confirmFilters() {
    activeFilters = { ...pendingFilters };
    pendingFilters = {};
    document.getElementById('pendingFiltersArea').classList.add('hidden');
    buscar(false);
}

function cancelPendingFilters() {
    pendingFilters = {};
    document.getElementById('pendingFiltersArea').classList.add('hidden');
}

// ===========================
// Gestión de filtros activos
// ===========================
function updateActiveFiltersDisplay() {
    const container = document.getElementById('activeFilterTags');
    const area = document.getElementById('activeFiltersArea');
    
    if (Object.keys(activeFilters).length === 0) {
        area.classList.add('hidden');
        return;
    }
    
    area.classList.remove('hidden');
    
    let html = '';
    for (const [type, values] of Object.entries(activeFilters)) {
        values.forEach(value => {
            html += `<span class="active-filter-tag">${value} 
                <button onclick="removeFilter('${type}', '${value}')">&times;</button>
            </span>`;
        });
    }
    container.innerHTML = html;
}

function removeFilter(type, value) {
    if (activeFilters[type]) {
        activeFilters[type] = activeFilters[type].filter(v => v !== value);
        if (activeFilters[type].length === 0) {
            delete activeFilters[type];
        }
    }
    updateActiveFiltersDisplay();
    buscar(false);
}

function clearAllFilters() {
    activeFilters = {};
    pendingFilters = {};
    document.getElementById('activeFiltersArea').classList.add('hidden');
    document.getElementById('pendingFiltersArea').classList.add('hidden');
    buscar(true);
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

// ===========================
// Cargar contratos adicionales (scroll infinito)
// ===========================
async function cargarContratos(page, append = false) {
    if (isLoadingMore) return;
    
    try {
        isLoadingMore = true;
        
        const response = await fetch('/api/contracts/page', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                query: lastQuery,
                search_type: lastSearchType,
                filters: activeFilters,
                page: page,
                per_page: perPage
            })
        });

        if (!response.ok) {
            throw new Error(`HTTP ${response.status}`);
        }
        
        const data = await response.json();
        
        if (data.contratos && data.contratos.length > 0) {
            renderContratos(data.contratos, append);
            currentPage = page;
        }
        
        isLoadingMore = false;
        
    } catch (error) {
        console.error('Error cargando más contratos:', error);
        isLoadingMore = false;
    }
}

// ===========================
// Cerrar modal al hacer clic fuera
// ===========================
window.onclick = function(event) {
    if (event.target.id === 'filterModal') {
        closeFilterModal();
    }
}