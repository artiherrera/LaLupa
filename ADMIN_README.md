# Panel de Administración - Carga de Datos

Esta aplicación Flask paralela se encarga de la limpieza y carga de datos de contratos a la base de datos.

## Características

- Interfaz web intuitiva para cargar archivos CSV
- Limpieza automática de datos (normalización de texto, validación de RFC, conversión de fechas, etc.)
- Procesamiento de archivos grandes (hasta 100MB)
- Drag & drop de archivos
- Estadísticas en tiempo real
- Log de actividades
- Gestión de base de datos

## Instalación

1. Instalar dependencias (si aún no lo has hecho):

```bash
pip install -r requirements.txt
```

2. Asegurarse de que el archivo `.env` esté configurado con las credenciales de la base de datos.

## Uso

### Iniciar el servidor de administración

```bash
python admin_app.py
```

La aplicación se ejecutará en `http://localhost:5001` (puerto diferente a la app principal).

### Iniciar ambas aplicaciones simultáneamente

En terminales separadas:

**Terminal 1 - App principal:**
```bash
python run.py
```

**Terminal 2 - App de administración:**
```bash
python admin_app.py
```

## Interfaz Web

Accede a `http://localhost:5001` para ver el panel de administración.

### Funcionalidades disponibles:

1. **Ver Estadísticas**
   - Total de contratos en la base de datos
   - Último año registrado
   - Botón para actualizar estadísticas

2. **Cargar Archivos CSV**
   - Haz clic en el área de carga o arrastra un archivo CSV
   - El sistema automáticamente limpiará y validará los datos
   - Verás el progreso de la carga en tiempo real
   - El log mostrará detalles de la operación

3. **Limpiar Base de Datos**
   - Botón para eliminar todos los registros
   - Requiere doble confirmación por seguridad

## Formato del CSV

El archivo CSV debe contener las siguientes columnas (pueden estar en cualquier orden):

- `CODIGO_CONTRATO` (requerido, clave primaria)
- `CODIGO_EXPEDIENTE`
- `TITULO_CONTRATO`
- `TITULO_EXPEDIENTE`
- `DESCRIPCION_CONTRATO`
- `TIPO_CONTRATACION`
- `TIPO_PROCEDIMIENTO`
- `PROVEEDOR_CONTRATISTA`
- `RFC`
- `INSTITUCION`
- `SIGLAS_INSTITUCION`
- `IMPORTE`
- `IMPORTE_CONTRATO`
- `MONEDA`
- `FECHA_INICIO`
- `FECHA_FIN`
- `ESTATUS_CONTRATO`
- `DIRECCION_ANUNCIO`
- `ANIO`
- `ANIO_FUNDACION_EMPRESA`

## Proceso de Limpieza Automática

El sistema realiza las siguientes operaciones de limpieza:

### Texto
- Elimina espacios múltiples
- Normaliza espacios en blanco
- Convierte valores vacíos a NULL

### RFC
- Convierte a mayúsculas
- Elimina caracteres no alfanuméricos
- Valida longitud (12-13 caracteres)

### Importes
- Elimina comas y símbolos de moneda
- Convierte a número decimal
- Valida que sean valores positivos

### Fechas
- Intenta múltiples formatos (YYYY-MM-DD, DD/MM/YYYY, etc.)
- Convierte a formato ISO estándar
- Extrae años automáticamente

### Duplicados
- Elimina duplicados por `CODIGO_CONTRATO`
- Mantiene el primer registro encontrado

### Validación
- Elimina registros sin `CODIGO_CONTRATO`
- Valida tipos de datos
- Maneja errores individuales sin detener el proceso completo

## API Endpoints

### GET /api/stats
Obtiene estadísticas de la base de datos.

**Respuesta:**
```json
{
  "total_contratos": 12345,
  "ultimo_anio": 2024
}
```

### POST /api/upload
Sube y procesa un archivo CSV.

**Request:**
- Multipart form data con campo `file`

**Respuesta:**
```json
{
  "message": "Archivo procesado exitosamente",
  "registros_insertados": 1000,
  "registros_con_errores": 5
}
```

### POST /api/clear
Elimina todos los registros de la base de datos.

**Respuesta:**
```json
{
  "message": "Base de datos limpiada exitosamente",
  "registros_eliminados": 12345
}
```

## Configuración de Puerto

Puedes cambiar el puerto de la aplicación de administración editando el archivo `.env`:

```
ADMIN_PORT=5001
```

O pasándolo como variable de entorno al ejecutar:

```bash
ADMIN_PORT=8080 python admin_app.py
```

## Manejo de Errores

- Los errores de registros individuales no detienen el proceso completo
- Se registra el número de registros con errores
- Los logs muestran detalles de cada error para depuración

## Seguridad

- Validación de tipo de archivo (solo CSV)
- Límite de tamaño de archivo (100MB)
- Confirmación doble para operaciones destructivas
- Prevención de SQL injection mediante queries parametrizadas
- Uso de transacciones para mantener integridad de datos

## Logs

Los logs se muestran en:
1. La consola del servidor
2. El panel web en tiempo real
3. Los logs estándar de la aplicación Flask

## Troubleshooting

### Error de conexión a la base de datos
- Verifica que `DATABASE_URL` esté correctamente configurada en `.env`
- Asegúrate de tener acceso a la base de datos

### Archivo muy grande
- El límite es 100MB, divide archivos más grandes
- Considera aumentar `MAX_CONTENT_LENGTH` si es necesario

### Errores de encoding
- Asegúrate de que el CSV esté en UTF-8
- El sistema intenta automáticamente con UTF-8-BOM

### Puerto en uso
- Cambia `ADMIN_PORT` en `.env`
- O cierra la aplicación que está usando el puerto

## Desarrollo

### Estructura del código

```
admin_app.py
├── DataCleaner (clase)
│   ├── limpiar_texto()
│   ├── limpiar_rfc()
│   ├── limpiar_importe()
│   ├── limpiar_fecha()
│   ├── extraer_anio()
│   └── limpiar_dataframe()
├── Flask Routes
│   ├── / (interfaz web)
│   ├── /api/stats (estadísticas)
│   ├── /api/upload (carga)
│   └── /api/clear (limpieza)
└── Template HTML embebido
```

### Extender funcionalidad

Para agregar más validaciones o limpiezas, edita la clase `DataCleaner` en [admin_app.py](admin_app.py).

## Mejoras Futuras

- [ ] Soporte para Excel (.xlsx)
- [ ] Exportación de datos a CSV
- [ ] Validación avanzada con reglas de negocio
- [ ] Programación de cargas automáticas
- [ ] Backup antes de operaciones destructivas
- [ ] Autenticación de usuarios
- [ ] Historial de cargas
- [ ] Preview de datos antes de cargar
- [ ] Validación de esquema personalizable

## Soporte

Para reportar problemas o sugerir mejoras, contacta al equipo de desarrollo.
