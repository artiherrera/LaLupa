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
const perPage = 20;

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
async function buscar() {
    const query = document.getElementById('searchInput').value.trim();
    if (!query) {
        mostrarError('Por favor ingresa un término de búsqueda');
        return;
    }

    // Obtener tipo de búsqueda seleccionado
    const searchType = document.querySelector('input[name="searchType"]:checked').value;

    // Guardar para uso posterior
    lastQuery = query;
    lastSearchType = searchType;
    activeFilters = {}; // Reset filtros
    currentPage = 1;

    // Mostrar loading
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

        // Ocultar loading
        document.getElementById('loading').classList.add('hidden');

        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.error || `Error HTTP: ${response.status}`);
        }

        const data = await response.json();
        
        // Debug log para verificar la estructura
        console.log('Datos recibidos:', data);

        // Verificar si hay resultados
        if (!data || data.total === 0) {
            mostrarError('No se encontraron resultados para tu búsqueda');
            return;
        }

        // Mostrar resultados
        document.getElementById('resultsArea').classList.remove('hidden');
        
        // Renderizar el resumen de resultados con las propiedades correctas
        renderResultsSummary(data);
        
        // Renderizar los agregados (proveedores e instituciones)
        renderAggregates(data);
        
        // Renderizar contratos
        if (data.contratos && data.contratos.length > 0) {
            renderContratos(data.contratos, false);
            document.getElementById('contratosSection').classList.remove('hidden');
        }
        
        // Renderizar filtros si están disponibles
        if (data.filtros_disponibles) {
            renderFilters(data.filtros_disponibles);
        }

    } catch (error) {
        console.error('Error en búsqueda:', error);
        document.getElementById('loading').classList.add('hidden');
        mostrarError(error.message || 'Error al realizar la búsqueda. Por favor intenta de nuevo.');
    }
}

// ===========================
// Render del resumen de resultados
// ===========================
function renderResultsSummary(data) {
    const summaryHtml = `
        <strong>Resultados para:</strong> "${data.query}" | 
        <strong>Tipo de búsqueda:</strong> ${data.search_type} | 
        <strong>Total:</strong> ${data.total.toLocaleString()} contratos | 
        <strong>Monto total:</strong> ${formatMoney(data.monto_total)}
    `;
    document.getElementById('resultsSummary').innerHTML = summaryHtml;
}

// ===========================
// Render de agregados
// ===========================
function renderAggregates(data) {
    // Mostrar proveedores
    if (data.proveedores && data.proveedores.length > 0) {
        mostrarProveedores(data.proveedores);
        document.getElementById('empresasSection').classList.remove('hidden');
    } else {
        document.getElementById('empresasSection').classList.add('hidden');
    }

    // Mostrar instituciones
    if (data.instituciones && data.instituciones.length > 0) {
        mostrarInstituciones(data.instituciones);
        document.getElementById('institucionesSection').classList.remove('hidden');
    } else {
        document.getElementById('institucionesSection').classList.add('hidden');
    }
}

// ===========================
// Render de contratos
// ===========================
function renderContratos(contratos, append = false) {
    let html = '';

    contratos.forEach(contrato => {
        const titulo = contrato.titulo || contrato.descripcion || 'Sin título';
        const tituloCorto = titulo.length > 100 ? titulo.substring(0, 100) + '...' : titulo;

        const botonCompranet = contrato.url_compranet && contrato.url_compranet.startsWith('http') 
            ? `<a href="${contrato.url_compranet}" target="_blank" class="btn-compranet" title="Ver en CompraNet">🔗 CompraNet</a>` 
            : '';

        html += `
            <div class="contract-item">
                <div class="contract-header">
                    <div style="flex: 1;">
                        <div class="contract-title">${tituloCorto}</div>
                        <div class="contract-details">
                            <strong>${contrato.institucion || contrato.siglas_institucion || ''}</strong> | 
                            ${contrato.proveedor || 'Sin proveedor'}<br>
                            Código: ${contrato.codigo_contrato || 'N/A'} | 
                            ${contrato.tipo_procedimiento || ''} | 
                            ${contrato.anio || ''}
                        </div>
                        ${botonCompranet}
                    </div>
                    <div class="contract-amount">${formatMoney(contrato.importe)}</div>
                </div>
            </div>
        `;
    });

    if (append) {
        document.getElementById('contratosList').insertAdjacentHTML('beforeend', html);
    } else {
        document.getElementById('contratosList').innerHTML = html;
    }
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

    let buttonsHtml = '';
    
    // Instituciones
    if (filtros.instituciones && Object.keys(filtros.instituciones).length > 0) {
        buttonsHtml += `<button class="filter-btn" onclick="openFilterModal('instituciones', ${JSON.stringify(filtros.instituciones).replace(/"/g, '&quot;')})">
            Institución (${Object.keys(filtros.instituciones).length})
        </button>`;
    }
    
    // Tipos de contratación
    if (filtros.tipos && Object.keys(filtros.tipos).length > 0) {
        buttonsHtml += `<button class="filter-btn" onclick="openFilterModal('tipos', ${JSON.stringify(filtros.tipos).replace(/"/g, '&quot;')})">
            Tipo (${Object.keys(filtros.tipos).length})
        </button>`;
    }
    
    // Procedimientos
    if (filtros.procedimientos && Object.keys(filtros.procedimientos).length > 0) {
        buttonsHtml += `<button class="filter-btn" onclick="openFilterModal('procedimientos', ${JSON.stringify(filtros.procedimientos).replace(/"/g, '&quot;')})">
            Procedimiento (${Object.keys(filtros.procedimientos).length})
        </button>`;
    }
    
    // Años
    if (filtros.anios && Object.keys(filtros.anios).length > 0) {
        buttonsHtml += `<button class="filter-btn" onclick="openFilterModal('anios', ${JSON.stringify(filtros.anios).replace(/"/g, '&quot;')})">
            Año (${Object.keys(filtros.anios).length})
        </button>`;
    }
    
    // Estatus
    if (filtros.estatus && Object.keys(filtros.estatus).length > 0) {
        buttonsHtml += `<button class="filter-btn" onclick="openFilterModal('estatus', ${JSON.stringify(filtros.estatus).replace(/"/g, '&quot;')})">
            Estatus (${Object.keys(filtros.estatus).length})
        </button>`;
    }

    document.getElementById('filterButtons').innerHTML = buttonsHtml;
    document.getElementById('filtersBar').classList.remove('hidden');
}

// ===========================
// Modal de filtros
// ===========================
let currentFilterType = '';
let currentFilterOptions = {};

function openFilterModal(type, options) {
    currentFilterType = type;
    currentFilterOptions = options;
    
    const modal = document.getElementById('filterModal');
    const modalTitle = document.getElementById('filterModalTitle');
    const modalBody = document.getElementById('filterModalBody');
    
    // Configurar título
    const titles = {
        'instituciones': 'Filtrar por Institución',
        'tipos': 'Filtrar por Tipo de Contratación',
        'procedimientos': 'Filtrar por Tipo de Procedimiento',
        'anios': 'Filtrar por Año',
        'estatus': 'Filtrar por Estatus'
    };
    modalTitle.textContent = titles[type] || 'Filtrar';
    
    // Generar checkboxes
    let bodyHtml = '<div class="filter-options">';
    for (const [key, count] of Object.entries(options)) {
        const isChecked = activeFilters[type] && activeFilters[type].includes(key) ? 'checked' : '';
        bodyHtml += `
            <label class="filter-option">
                <input type="checkbox" value="${key}" ${isChecked}>
                <span>${key} (${count})</span>
            </label>
        `;
    }
    bodyHtml += '</div>';
    modalBody.innerHTML = bodyHtml;
    
    modal.classList.remove('hidden');
}

function closeFilterModal() {
    document.getElementById('filterModal').classList.add('hidden');
}

function applyFilters() {
    const checkboxes = document.querySelectorAll('#filterModalBody input[type="checkbox"]:checked');
    const selectedValues = Array.from(checkboxes).map(cb => cb.value);
    
    if (selectedValues.length > 0) {
        activeFilters[currentFilterType] = selectedValues;
    } else {
        delete activeFilters[currentFilterType];
    }
    
    closeFilterModal();
    updateActiveFiltersDisplay();
    buscar(); // Realizar nueva búsqueda con filtros
}

function updateActiveFiltersDisplay() {
    const container = document.getElementById('activeFilters');
    if (Object.keys(activeFilters).length === 0) {
        container.innerHTML = '';
        return;
    }
    
    let html = '<span>Filtros activos: </span>';
    for (const [type, values] of Object.entries(activeFilters)) {
        values.forEach(value => {
            html += `<span class="active-filter-tag">${value} 
                <button onclick="removeFilter('${type}', '${value}')">&times;</button>
            </span>`;
        });
    }
    html += `<button class="clear-filters-btn" onclick="clearAllFilters()">Limpiar todos</button>`;
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
    buscar();
}

function clearAllFilters() {
    activeFilters = {};
    updateActiveFiltersDisplay();
    buscar();
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
        
        const response = await fetch('/api/search', {
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

// Cerrar modal al hacer clic fuera
window.onclick = function(event) {
    const modal = document.getElementById('filterModal');
    if (event.target == modal) {
        closeFilterModal();
    }
}