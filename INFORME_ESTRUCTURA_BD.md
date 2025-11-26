# Informe de Estructura y Calidad de Datos - Base de Datos de Contratos

**Fecha**: 2025-11-08
**Total de registros**: 995,888

## 1. Estructura de la Tabla `contratos.contratos`

### Columnas Disponibles (43 columnas)

| Columna | Tipo | Nullable | Descripción |
|---------|------|----------|-------------|
| `codigo_contrato` | text | YES | Identificador único del contrato |
| `codigo_expediente` | text | YES | Código del expediente |
| `titulo_contrato` | text | YES | Título/nombre del contrato |
| `descripcion_contrato` | text | YES | Descripción detallada |
| `proveedor_contratista` | text | YES | Nombre del proveedor |
| `rfc` | varchar | YES | RFC del proveedor |
| `importe` | double precision | YES | Importe normalizado |
| `importe_contrato` | double precision | YES | Importe del contrato |
| `moneda` | varchar | YES | Tipo de moneda |
| `fecha_inicio_contrato` | timestamp | YES | Fecha de inicio |
| `fecha_fin_contrato` | timestamp | YES | Fecha de fin |
| `fecha_firma_contrato` | timestamp | YES | Fecha de firma |
| `anio_fuente` | varchar | YES | Año de la fuente |
| `tipo_contratacion` | text | YES | Tipo (ADQUISICIONES, etc.) |
| `tipo_procedimiento` | text | YES | Tipo de procedimiento |
| `institucion` | text | YES | Institución contratante |
| `siglas_institucion` | text | YES | Siglas |
| `estatus_contrato` | text | YES | Estatus actual |
| ... | ... | ... | (y 25 columnas más) |

### Columnas NO usadas en el modelo actual

Las siguientes columnas existen en la BD pero NO están en nuestro modelo `Contrato`:

- `caracter_procedimiento`
- `clave_cartera_shcp`
- `clave_programa_federal`
- `clave_uc`
- `compra_consolidada`
- `contrato_marco`
- `contrato_plurianual`
- `convenio_modificatorio`
- `credito_externo`
- `estratificacion`
- `fecha_apertura`
- `fecha_fallo`
- `fecha_firma_contrato`
- `fecha_publicacion`
- `folio_rupc`
- `forma_participacion`
- `nombre_uc`
- `num_contrato`
- `numero_procedimiento`
- `orden_de_gobierno`
- `organismo_financiero`
- `referencia_expediente`
- `moneda_norm`

## 2. Calidad de Datos

### Completitud de Campos Críticos

| Campo | Registros con datos | Porcentaje | Observaciones |
|-------|---------------------|------------|---------------|
| `codigo_contrato` | 995,888 | 100.0% | ✓ Excelente |
| `titulo_contrato` | 995,888 | 100.0% | ✓ Excelente |
| `proveedor_contratista` | 995,883 | 100.0% | ✓ Excelente (solo 5 faltantes) |
| `rfc` | 995,888 | 100.0% | ⚠️ Todos tienen valor (revisar validez) |
| `importe` | 995,888 | 100.0% | ⚠️ Todos tienen valor (revisar negativos/ceros) |
| `fecha_inicio_contrato` | 756,244 | 75.9% | ⚠️ 24% sin fecha |
| `anio_fuente` | 995,888 | 100.0% | ✓ Excelente |

### Problemas Identificados

#### 1. **Códigos de Contrato Vacíos**
- **15,058 registros** tienen `codigo_contrato` vacío o NULL (string vacío)
- Esto es un problema crítico ya que es la llave primaria
- **Acción requerida**: Generar códigos únicos o usar otro identificador

#### 2. **Duplicados**
- **3 códigos duplicados** (además del vacío)
  - `codigo_contrato` vacío: 15,058 veces
  - `2646681`: 2 veces
  - `2850897`: 2 veces
- **Acción requerida**: Resolver duplicados antes de insertar

#### 3. **Importes Inválidos**
- **912 contratos** con importe $0 o negativo
- Rango: $0.00 a $77,259,004,011.00
- Promedio: $3,343,985.21
- **Acción requerida**: Validar importes antes de insertar

#### 4. **Formato de RFC**
- Algunos RFC tienen formato incorrecto
- Ejemplos encontrados:
  - `AAA0003232I9` (12 caracteres)
  - `MME960821JHA` (12 caracteres)
- RFC válido: 12-13 caracteres alfanuméricos
- **Acción requerida**: Validar y limpiar RFC

## 3. Distribución de Datos

### Por Año

| Año | Registros | Porcentaje |
|-----|-----------|------------|
| 2025 | 81,154 | 8.1% |
| 2024 | 143,432 | 14.4% |
| 2023 | 13,406 | 1.3% |
| 2022 | 193,572 | 19.4% |
| 2021 | 206,103 | 20.7% |
| 2020 | 161,541 | 16.2% |
| 2019 | 196,680 | 19.8% |

### Ejemplo de Datos Reales

```
Código: 2759216
Título: HARINA DE TRIGO
Proveedor: MOLINERA DE MEXICO SA DE CV
RFC: MME960821JHA
Importe: $2,384,100.00
Año: 2022
Tipo: ADQUISICIONES - ADJUDICACIÓN DIRECTA
```

## 4. Recomendaciones para el Proceso de Limpieza

### 4.1. Manejo de Código de Contrato

```python
# Si viene vacío, generar uno único
if not codigo_contrato or codigo_contrato.strip() == '':
    codigo_contrato = f"AUTO_{uuid.uuid4().hex[:12].upper()}"
```

### 4.2. Validación de RFC

```python
def validar_rfc(rfc):
    if not rfc:
        return None
    rfc = rfc.strip().upper()
    # Remover caracteres especiales
    rfc = re.sub(r'[^A-Z0-9]', '', rfc)
    # Validar longitud 12-13
    if len(rfc) >= 12 and len(rfc) <= 13:
        return rfc
    return None
```

### 4.3. Validación de Importes

```python
def validar_importe(importe):
    try:
        valor = float(importe)
        # Rechazar negativos
        if valor < 0:
            return None
        # Advertir sobre ceros
        if valor == 0:
            logger.warning(f"Importe en $0: {codigo_contrato}")
        return valor
    except:
        return None
```

### 4.4. Manejo de Duplicados

```python
# Antes de insertar
INSERT INTO contratos.contratos (...)
VALUES (...)
ON CONFLICT (codigo_contrato) DO UPDATE SET
    -- Actualizar solo si los datos son más recientes
    titulo_contrato = EXCLUDED.titulo_contrato,
    importe = EXCLUDED.importe,
    ...
WHERE contratos.fecha_inicio_contrato < EXCLUDED.fecha_inicio_contrato
```

### 4.5. Mapeo Completo de Columnas CSV → BD

El sistema debe mapear correctamente todas las columnas disponibles:

```python
column_mapping = {
    # Campos principales
    'CODIGO_CONTRATO': 'codigo_contrato',
    'TITULO_CONTRATO': 'titulo_contrato',
    'DESCRIPCION_CONTRATO': 'descripcion_contrato',
    'PROVEEDOR_CONTRATISTA': 'proveedor_contratista',
    'RFC': 'rfc',
    'IMPORTE': 'importe',

    # Fechas
    'FECHA_INICIO': 'fecha_inicio_contrato',
    'FECHA_FIN': 'fecha_fin_contrato',
    'FECHA_FIRMA': 'fecha_firma_contrato',

    # Clasificación
    'TIPO_CONTRATACION': 'tipo_contratacion',
    'TIPO_PROCEDIMIENTO': 'tipo_procedimiento',

    # Institución
    'INSTITUCION': 'institucion',
    'SIGLAS_INSTITUCION': 'siglas_institucion',

    # Año
    'ANIO': 'anio_fuente',

    # Columnas adicionales (si están disponibles)
    'NUMERO_PROCEDIMIENTO': 'numero_procedimiento',
    'FOLIO_RUPC': 'folio_rupc',
    'ESTATUS_CONTRATO': 'estatus_contrato',
    # ... agregar más según el CSV
}
```

## 5. Formato Esperado del CSV de Entrada

### Columnas Mínimas Requeridas

1. `CODIGO_CONTRATO` (o se generará automáticamente)
2. `TITULO_CONTRATO`
3. `PROVEEDOR_CONTRATISTA`
4. `RFC`
5. `IMPORTE`
6. `ANIO`

### Columnas Opcionales pero Recomendadas

- `DESCRIPCION_CONTRATO`
- `FECHA_INICIO`
- `FECHA_FIN`
- `TIPO_CONTRATACION`
- `TIPO_PROCEDIMIENTO`
- `INSTITUCION`
- `SIGLAS_INSTITUCION`
- `ESTATUS_CONTRATO`

### Formato de Datos

- **Fechas**: `YYYY-MM-DD`, `DD/MM/YYYY`, o `DD-MM-YYYY`
- **Importes**: Números con o sin comas (`1234.56` o `1,234.56`)
- **RFC**: 12-13 caracteres alfanuméricos
- **Encoding**: UTF-8 (preferible UTF-8-BOM)

## 6. Flujo de Limpieza Propuesto

```
1. CARGAR CSV
   ↓
2. VALIDAR ESTRUCTURA
   - Verificar columnas requeridas
   - Mapear nombres de columnas
   ↓
3. LIMPIAR DATOS
   - Normalizar texto (espacios, mayúsculas/minúsculas)
   - Validar RFC
   - Convertir importes
   - Parsear fechas
   - Generar códigos faltantes
   ↓
4. VALIDAR CALIDAD
   - Rechazar registros sin campos críticos
   - Advertir sobre anomalías
   - Registrar problemas en log
   ↓
5. DETECTAR DUPLICADOS
   - Por codigo_contrato
   - Decidir estrategia (reemplazar/ignorar/actualizar)
   ↓
6. INSERTAR EN BD
   - Transacción por lotes (cada 100 registros)
   - Manejo de conflictos
   - Rollback en caso de error crítico
   ↓
7. REPORTAR RESULTADOS
   - Registros insertados
   - Registros actualizados
   - Registros con errores
   - Problemas encontrados
```

## 7. Conclusiones

### Fortalezas
- ✓ Excelente completitud en campos críticos (>99%)
- ✓ Gran volumen de datos (casi 1 millón de contratos)
- ✓ Datos desde 2019 hasta 2025
- ✓ Estructura bien definida con 43 columnas

### Áreas de Mejora
- ⚠️ 15K registros sin código de contrato válido
- ⚠️ Algunos RFC con formato incorrecto
- ⚠️ 912 contratos con importe $0 o negativo
- ⚠️ 24% de contratos sin fecha de inicio
- ⚠️ Necesidad de actualizar el modelo SQLAlchemy con todas las columnas

### Próximos Pasos
1. Actualizar `admin_app.py` con validaciones robustas
2. Implementar generación de códigos únicos
3. Mejorar validación de RFC
4. Agregar validación de importes
5. Implementar estrategia de duplicados
6. Considerar actualizar el modelo `Contrato` con todas las columnas disponibles
