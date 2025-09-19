// static/js/app.js

// Variables globales
let currentResults = null;
let activeFilters = {};
let currentFilterType = null;

// Event listeners al cargar la página
document.addEventListener('DOMContentLoaded', function() {
    // Enter para buscar
    document.getElementById('searchInput').addEventListener('keypress', function(e) {
        if (e.key === 'Enter') {
            buscar();
        }
    });
});

// Función principal de búsqueda
async function buscar() {
    const query = document.getElementById('searchInput').value.trim();
    if (!query) {
        alert('Por favor ingresa un término de búsqueda');
        return;
    }
    
    const searchType = document.querySelector('input[name="searchType"]:checked').value;
    
    // Limpiar filtros anteriores
    activeFilters = {};
    
    // Mostrar loading
    document.getElementById('loading').classList.remove('hidden');
    document.getElementById('resultsArea').classList.add('hidden');
    document.getElementById('errorMessage').classList.add('hidden');
    
    try {
        const response = await fetch('/api/search', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                query: query,
                search_type: searchType,
                filters: activeFilters
            })
        });
        
        if (!response.ok) {
            throw new Error('Error en la búsqueda');
        }
        
        const data = await response.json();
        currentResults = data;
        
        document.getElementById('loading').classList.add('hidden');
        mostrarResultados(data);
        
    } catch (error) {
        document.getElementById('loading').classList.add('hidden');
        mostrarError('Error al realizar la búsqueda. Por favor intenta de nuevo.');
        console.error('Error:', error);
    }
}

// Mostrar resultados
function mostrarResultados(data) {
    if (data.total === 0) {
        mostrarError('No se encontraron resultados para tu búsqueda');
        return;
    }
    
    // Mostrar resumen
    const summaryHtml = `
        <strong>Resultados para:</strong> "${data.query}" | 
        <strong>Total:</strong> ${data.total.toLocaleString()} contratos | 
        <strong>Monto total:</strong> ${formatMoney(data.monto_total)}
    `;
    document.getElementById('resultsSummary').innerHTML = summaryHtml;
    
    // Configurar filtros si hay resultados
    if (data.filtros_disponibles && Object.keys(data.filtros_disponibles).length > 0) {
        configurarFiltros(data.filtros_disponibles);
        document.getElementById('filtersBar').classList.remove('hidden');
    }
    
    // Mostrar proveedores (antes empresas)
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
    
    // Mostrar contratos
    if (data.contratos && data.contratos.length > 0) {
        mostrarContratos(data.contratos);
        document.getElementById('contratosSection').classList.remove('hidden');
    } else {
        document.getElementById('contratosSection').classList.add('hidden');
    }
    
    // Mostrar área de resultados
    document.getElementById('resultsArea').classList.remove('hidden');
}

// Mostrar empresas
function mostrarProveedores(proveedores) {
    let html = '';
    
    proveedores.forEach(proveedor => {
        html += `
            <div class="group-item" onclick="verProveedor('${proveedor.rfc}')">
                <div class="group-info">
                    <div class="group-name">${proveedor.nombre || 'Sin nombre'}</div>
                    <div class="group-details">
                        RFC: ${proveedor.rfc} | ${proveedor.num_contratos} contratos
                    </div>
                </div>
                <div class="group-amount">${formatMoney(proveedor.monto_total)}</div>
            </div>
        `;
    });
    
    document.getElementById('empresasList').innerHTML = html;
}

// Mostrar instituciones
function mostrarInstituciones(instituciones) {
    let html = '';
    
    instituciones.forEach(inst => {
        html += `
            <div class="group-item" onclick="verInstitucion('${inst.siglas}')">
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

// Mostrar contratos
function mostrarContratos(contratos) {
    let html = '';
    
    contratos.forEach(contrato => {
        const titulo = contrato.titulo || contrato.descripcion || 'Sin título';
        const tituloCorto = titulo.length > 100 ? titulo.substring(0, 100) + '...' : titulo;
        
        // Crear botón de CompraNet si existe URL
        const botonCompranet = contrato.url_compranet && contrato.url_compranet.startsWith('http') 
            ? `<a href="${contrato.url_compranet}" target="_blank" class="btn-compranet" title="Ver en CompraNet">
                🔗 CompraNet
               </a>` 
            : '';
        
        html += `
            <div class="contract-item">
                <div class="contract-header">
                    <div style="flex: 1;">
                        <div class="contract-title">${tituloCorto}</div>
                        <div class="contract-details">
                            <strong>${contrato.institucion || contrato.siglas_institucion}</strong> | 
                            ${contrato.proveedor || 'Sin proveedor'}<br>
                            Código: ${contrato.codigo_contrato} | 
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
    
    document.getElementById('contratosList').innerHTML = html;
}

// Configurar filtros
function configurarFiltros(filtros) {
    let html = '';
    
    // Crear botones de filtro
    if (filtros.instituciones && Object.keys(filtros.instituciones).length > 0) {
        html += `<button class="filter-btn" onclick="abrirFiltro('institucion')">Institución ▼</button>`;
    }
    if (filtros.tipos && Object.keys(filtros.tipos).length > 0) {
        html += `<button class="filter-btn" onclick="abrirFiltro('tipo')">Tipo ▼</button>`;
    }
    if (filtros.procedimientos && Object.keys(filtros.procedimientos).length > 0) {
        html += `<button class="filter-btn" onclick="abrirFiltro('procedimiento')">Procedimiento ▼</button>`;
    }
    if (filtros.anios && Object.keys(filtros.anios).length > 0) {
        html += `<button class="filter-btn" onclick="abrirFiltro('anio')">Año ▼</button>`;
    }
    if (filtros.estatus && Object.keys(filtros.estatus).length > 0) {
        html += `<button class="filter-btn" onclick="abrirFiltro('estatus')">Estado ▼</button>`;
    }
    
    document.getElementById('filterButtons').innerHTML = html;
}

// Abrir modal de filtro
function abrirFiltro(tipo) {
    currentFilterType = tipo;
    const modal = document.getElementById('filterModal');
    const modalTitle = document.getElementById('filterModalTitle');
    const modalBody = document.getElementById('filterModalBody');
    
    // Configurar título
    const titulos = {
        'institucion': 'Filtrar por Institución',
        'tipo': 'Filtrar por Tipo',
        'procedimiento': 'Filtrar por Procedimiento',
        'anio': 'Filtrar por Año',
        'estatus': 'Filtrar por Estado'
    };
    modalTitle.textContent = titulos[tipo];
    
    // Configurar opciones
    let html = '';
    const filtrosData = {
        'institucion': currentResults.filtros_disponibles.instituciones,
        'tipo': currentResults.filtros_disponibles.tipos,
        'procedimiento': currentResults.filtros_disponibles.procedimientos,
        'anio': currentResults.filtros_disponibles.anios,
        'estatus': currentResults.filtros_disponibles.estatus
    };
    
    const opciones = filtrosData[tipo];
    if (opciones) {
        Object.entries(opciones).forEach(([valor, cantidad]) => {
            const isChecked = activeFilters[tipo] && activeFilters[tipo].includes(valor);
            html += `
                <div class="filter-option">
                    <label>
                        <input type="checkbox" value="${valor}" ${isChecked ? 'checked' : ''}>
                        ${valor}
                        <span class="filter-count">(${cantidad})</span>
                    </label>
                </div>
            `;
        });
    }
    
    modalBody.innerHTML = html;
    modal.classList.remove('hidden');
}

// Cerrar modal de filtro
function closeFilterModal() {
    document.getElementById('filterModal').classList.add('hidden');
}

// Aplicar filtros
function applyFilters() {
    const checkboxes = document.querySelectorAll('#filterModalBody input[type="checkbox"]:checked');
    const valores = Array.from(checkboxes).map(cb => cb.value);
    
    if (valores.length > 0) {
        // Los años ya vienen como strings, perfecto para el backend
        activeFilters[currentFilterType] = valores;
    } else {
        delete activeFilters[currentFilterType];
    }
    
    closeFilterModal();
    mostrarFiltrosActivos();
    buscarConFiltros();
}

// Mostrar filtros activos
function mostrarFiltrosActivos() {
    let html = '';
    
    Object.entries(activeFilters).forEach(([tipo, valores]) => {
        valores.forEach(valor => {
            html += `
                <div class="filter-chip">
                    ${valor}
                    <span class="remove" onclick="removerFiltro('${tipo}', '${valor}')">×</span>
                </div>
            `;
        });
    });
    
    document.getElementById('activeFilters').innerHTML = html;
}

// Remover filtro
function removerFiltro(tipo, valor) {
    if (activeFilters[tipo]) {
        activeFilters[tipo] = activeFilters[tipo].filter(v => v !== valor);
        if (activeFilters[tipo].length === 0) {
            delete activeFilters[tipo];
        }
    }
    mostrarFiltrosActivos();
    buscarConFiltros();
}

// Buscar con filtros aplicados
async function buscarConFiltros() {
    const query = document.getElementById('searchInput').value.trim();
    const searchType = document.querySelector('input[name="searchType"]:checked').value;
    
    document.getElementById('loading').classList.remove('hidden');
    
    try {
        const response = await fetch('/api/search', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                query: query,
                search_type: searchType,
                filters: activeFilters
            })
        });
        
        const data = await response.json();
        currentResults = data;
        
        document.getElementById('loading').classList.add('hidden');
        mostrarResultados(data);
        
    } catch (error) {
        document.getElementById('loading').classList.add('hidden');
        mostrarError('Error al aplicar filtros');
    }
}

// Ver detalle de empresa
async function verProveedor(rfc) {
    try {
        const response = await fetch(`/api/empresa/${rfc}`);
        const data = await response.json();
        
        // Por ahora solo mostrar alert, después haremos una vista detallada
        alert(`Proveedor: ${data.empresa}\nTotal contratos: ${data.total_contratos}\nMonto total: ${formatMoney(data.monto_total)}`);
        
    } catch (error) {
        console.error('Error:', error);
    }
}

// Ver detalle de institución
async function verInstitucion(siglas) {
    try {
        const response = await fetch(`/api/institucion/${siglas}`);
        const data = await response.json();
        
        // Por ahora solo mostrar alert, después haremos una vista detallada
        alert(`Institución: ${data.institucion}\nTotal contratos: ${data.total_contratos}\nMonto total: ${formatMoney(data.monto_total)}`);
        
    } catch (error) {
        console.error('Error:', error);
    }
}

// Formatear moneda
function formatMoney(amount) {
    if (amount === null || amount === undefined) return '$0.00';
    return '$' + amount.toLocaleString('es-MX', {
        minimumFractionDigits: 2,
        maximumFractionDigits: 2
    });
}

// Mostrar error
function mostrarError(mensaje) {
    const errorDiv = document.getElementById('errorMessage');
    errorDiv.textContent = mensaje;
    errorDiv.classList.remove('hidden');
    document.getElementById('resultsArea').classList.add('hidden');
}