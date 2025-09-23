# test_new_structure.py

"""Script para probar que la nueva estructura funciona correctamente"""
import os
import sys
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()

# Configurar el entorno antes de importar la app
os.environ['FLASK_ENV'] = 'development'

# Importar y crear la app
from app import create_app, db
from app.models import Contrato
from app.services import SearchService, AggregationService, FilterService
from sqlalchemy import func

def test_database_connection():
    """Prueba la conexión a la base de datos"""
    print("\n1. Probando conexión a la base de datos...")
    try:
        app = create_app('development')
        with app.app_context():
            # Test básico de conexión
            result = db.session.execute(db.text('SELECT 1')).scalar()
            assert result == 1
            
            # Contar contratos
            count = db.session.query(func.count(Contrato.codigo_contrato)).scalar()
            print(f"   ✅ Conexión exitosa. Contratos en BD: {count:,}")
            return True
    except Exception as e:
        print(f"   ❌ Error: {e}")
        return False

def test_services():
    """Prueba los servicios"""
    print("\n2. Probando servicios...")
    try:
        app = create_app('development')
        with app.app_context():
            # Probar SearchService
            search_service = SearchService()
            query_text, search_type = search_service.validate_search_input(
                "construcción", "todo"
            )
            print(f"   ✅ SearchService funciona")
            
            # Probar AggregationService
            aggregation_service = AggregationService()
            stats = aggregation_service.get_stats()
            print(f"   ✅ AggregationService funciona")
            print(f"      - Total contratos: {stats['total_contratos']:,}")
            print(f"      - Total instituciones: {stats['total_instituciones']:,}")
            print(f"      - Total empresas: {stats['total_empresas']:,}")
            
            # Probar FilterService
            filter_service = FilterService()
            base_query = Contrato.query.limit(100)
            filtros = filter_service.obtener_filtros_disponibles(base_query)
            print(f"   ✅ FilterService funciona")
            print(f"      - Tipos de filtros disponibles: {list(filtros.keys())}")
            
            return True
    except Exception as e:
        print(f"   ❌ Error: {e}")
        return False

def test_endpoints():
    """Prueba los endpoints"""
    print("\n3. Probando endpoints...")
    try:
        app = create_app('development')
        client = app.test_client()
        
        # Probar /api/stats
        response = client.get('/api/stats')
        assert response.status_code == 200
        print(f"   ✅ GET /api/stats funciona")
        
        # Probar /api/search
        response = client.post('/api/search', 
            json={'query': 'construcción', 'search_type': 'todo'})
        assert response.status_code == 200
        data = response.get_json()
        print(f"   ✅ POST /api/search funciona")
        print(f"      - Resultados encontrados: {data.get('total', 0):,}")
        
        # Probar página principal
        response = client.get('/')
        assert response.status_code == 200
        print(f"   ✅ GET / (página principal) funciona")
        
        return True
    except Exception as e:
        print(f"   ❌ Error: {e}")
        return False

def main():
    """Ejecuta todas las pruebas"""
    print("=" * 50)
    print("PRUEBAS DE LA NUEVA ESTRUCTURA")
    print("=" * 50)
    
    all_tests_passed = True
    
    # Ejecutar pruebas
    all_tests_passed &= test_database_connection()
    all_tests_passed &= test_services()
    all_tests_passed &= test_endpoints()
    
    print("\n" + "=" * 50)
    if all_tests_passed:
        print("✅ TODAS LAS PRUEBAS PASARON")
        print("\nPuedes ejecutar la aplicación con:")
        print("  python run.py")
    else:
        print("❌ ALGUNAS PRUEBAS FALLARON")
        print("Revisa los errores arriba")
    print("=" * 50)

if __name__ == "__main__":
    main()