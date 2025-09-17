# LaLupa 🔍

Buscador de contratos gubernamentales mexicanos.

## Instalación

1. Clonar el repositorio
2. Crear entorno virtual: `python3 -m venv venv`
3. Activar entorno virtual: `source venv/bin/activate`
4. Instalar dependencias: `pip install -r requirements.txt`
5. Configurar variables de entorno en `.env`
6. Ejecutar: `python run.py`

## Tecnologías

- Flask
- PostgreSQL
- SQLAlchemy

## Estructura

```
lalupa/
├── app/
│   ├── templates/
│   ├── static/
│   └── __init__.py
├── config/
├── migrations/
├── tests/
├── .env
├── .gitignore
├── requirements.txt
├── run.py
└── README.md
```
