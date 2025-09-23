#!/usr/bin/env python3
# view_metrics.py - Script para ver métricas del sistema de logging

import json
import os
from datetime import datetime, timedelta
from collections import Counter
from pathlib import Path

def parse_json_logs(log_file):
    """Parse JSON logs from file"""
    logs = []
    if not os.path.exists(log_file):
        return logs
        
    with open(log_file, 'r') as f:
        for line in f:
            try:
                logs.append(json.loads(line.strip()))
            except:
                continue
    return logs

def show_recent_activity():
    """Muestra actividad reciente"""
    print("\n" + "="*60)
    print("📊 ACTIVIDAD RECIENTE (Últimos 30 minutos)")
    print("="*60)
    
    # Leer logs de acceso
    access_logs = parse_json_logs('logs/access.log')
    
    # Filtrar últimos 30 minutos
    thirty_min_ago = datetime.utcnow() - timedelta(minutes=30)
    recent_logs = [
        log for log in access_logs 
        if datetime.fromisoformat(log.get('timestamp', '')) > thirty_min_ago
    ]
    
    if recent_logs:
        print(f"\n✅ Total de requests: {len(recent_logs)}")
        
        # Endpoints más visitados
        endpoints = Counter(log.get('endpoint') for log in recent_logs if log.get('endpoint'))
        print("\n🎯 Top Endpoints visitados:")
        for endpoint, count in endpoints.most_common(5):
            print(f"   - {endpoint}: {count} visitas")
        
        # Usuarios únicos
        unique_users = set(log.get('user_fingerprint') for log in recent_logs if log.get('user_fingerprint'))
        print(f"\n👥 Usuarios únicos: {len(unique_users)}")
        
        # Dispositivos
        mobile = sum(1 for log in recent_logs if log.get('is_mobile'))
        desktop = len(recent_logs) - mobile
        print(f"\n📱 Dispositivos:")
        print(f"   - Desktop: {desktop} ({desktop*100//len(recent_logs)}%)")
        print(f"   - Mobile: {mobile} ({mobile*100//len(recent_logs)}%)")
    else:
        print("❌ No hay actividad en los últimos 30 minutos")

def show_searches():
    """Muestra búsquedas realizadas"""
    print("\n" + "="*60)
    print("🔍 BÚSQUEDAS REALIZADAS")
    print("="*60)
    
    search_logs = parse_json_logs('logs/search.log')
    
    if search_logs:
        # Últimas 10 búsquedas
        print("\n📝 Últimas 10 búsquedas:")
        for log in search_logs[-10:]:
            params = log.get('search_params', {})
            results = log.get('results_count', 0)
            time = log.get('execution_time_ms', 0)
            timestamp = log.get('timestamp', '')[:19]
            
            query = params.get('q', 'Sin término')
            print(f"\n   [{timestamp}]")
            print(f"   Búsqueda: '{query}'")
            print(f"   Resultados: {results} | Tiempo: {time}ms")
            
            # Mostrar filtros si los hay
            filters = {k: v for k, v in params.items() if k != 'q' and v}
            if filters:
                print(f"   Filtros: {filters}")
        
        # Términos más buscados
        all_terms = []
        for log in search_logs:
            term = log.get('search_params', {}).get('q')
            if term:
                all_terms.append(term.lower())
        
        if all_terms:
            top_terms = Counter(all_terms).most_common(10)
            print("\n🏆 Top 10 términos más buscados:")
            for term, count in top_terms:
                print(f"   - '{term}': {count} veces")
        
        # Estadísticas
        total_searches = len(search_logs)
        with_filters = sum(1 for log in search_logs if log.get('has_filters'))
        no_results = sum(1 for log in search_logs if log.get('results_count', 0) == 0)
        
        print(f"\n📈 Estadísticas totales:")
        print(f"   - Total de búsquedas: {total_searches}")
        print(f"   - Con filtros: {with_filters} ({with_filters*100//total_searches if total_searches else 0}%)")
        print(f"   - Sin resultados: {no_results} ({no_results*100//total_searches if total_searches else 0}%)")
    else:
        print("❌ No hay búsquedas registradas aún")

def show_errors():
    """Muestra errores recientes"""
    print("\n" + "="*60)
    print("❌ ERRORES RECIENTES")
    print("="*60)
    
    error_logs = parse_json_logs('logs/error.log')
    
    if error_logs:
        print(f"\nTotal de errores: {len(error_logs)}")
        
        # Últimos 5 errores
        print("\n🔴 Últimos 5 errores:")
        for log in error_logs[-5:]:
            timestamp = log.get('timestamp', '')[:19]
            error_type = log.get('error_type', 'Unknown')
            message = log.get('error_message', 'Sin mensaje')
            path = log.get('path', 'Unknown')
            
            print(f"\n   [{timestamp}]")
            print(f"   Tipo: {error_type}")
            print(f"   Path: {path}")
            print(f"   Mensaje: {message[:100]}...")
        
        # Tipos de error más comunes
        error_types = Counter(log.get('error_type') for log in error_logs)
        print("\n📊 Tipos de error más comunes:")
        for error_type, count in error_types.most_common(5):
            print(f"   - {error_type}: {count} veces")
    else:
        print("✅ No hay errores registrados (¡Excelente!)")

def show_performance():
    """Muestra métricas de performance"""
    print("\n" + "="*60)
    print("⚡ MÉTRICAS DE PERFORMANCE")
    print("="*60)
    
    access_logs = parse_json_logs('logs/access.log')
    
    # Filtrar logs con response_time
    perf_logs = [log for log in access_logs if log.get('response_time')]
    
    if perf_logs:
        response_times = [log['response_time'] for log in perf_logs]
        response_times.sort()
        
        avg_time = sum(response_times) / len(response_times)
        median_time = response_times[len(response_times)//2]
        p95_time = response_times[int(len(response_times) * 0.95)] if len(response_times) > 20 else max(response_times)
        slow_requests = sum(1 for t in response_times if t > 1000)
        
        print(f"\n📊 Tiempos de respuesta (últimas {len(response_times)} peticiones):")
        print(f"   - Promedio: {avg_time:.2f}ms")
        print(f"   - Mediana: {median_time:.2f}ms")
        print(f"   - P95: {p95_time:.2f}ms")
        print(f"   - Más rápido: {min(response_times):.2f}ms")
        print(f"   - Más lento: {max(response_times):.2f}ms")
        print(f"   - Requests lentos (>1s): {slow_requests}")
        
        # Endpoints más lentos
        endpoint_times = {}
        for log in perf_logs:
            endpoint = log.get('endpoint', 'unknown')
            time = log.get('response_time', 0)
            if endpoint not in endpoint_times:
                endpoint_times[endpoint] = []
            endpoint_times[endpoint].append(time)
        
        # Calcular promedio por endpoint
        endpoint_avg = {
            endpoint: sum(times)/len(times) 
            for endpoint, times in endpoint_times.items()
        }
        
        print("\n🐌 Endpoints más lentos (promedio):")
        for endpoint, avg in sorted(endpoint_avg.items(), key=lambda x: x[1], reverse=True)[:5]:
            print(f"   - {endpoint}: {avg:.2f}ms")
    else:
        print("❌ No hay métricas de performance aún")

def show_live_tail():
    """Muestra logs en tiempo real"""
    print("\n" + "="*60)
    print("👁️  LOGS EN TIEMPO REAL")
    print("="*60)
    print("\nPara ver logs en tiempo real, ejecuta estos comandos en tu terminal:\n")
    
    commands = [
        ("Ver todo el tráfico", "tail -f logs/access.log | python -m json.tool"),
        ("Ver búsquedas en vivo", "tail -f logs/search.log | python -m json.tool"),
        ("Ver errores", "tail -f logs/error.log"),
        ("Ver todos a la vez", "tail -f logs/*.log"),
        ("Filtrar por término", "tail -f logs/access.log | grep 'contract'"),
    ]
    
    for desc, cmd in commands:
        print(f"📌 {desc}:")
        print(f"   $ {cmd}\n")

def check_log_files():
    """Verifica que existan los archivos de log"""
    print("\n" + "="*60)
    print("📁 ESTADO DE ARCHIVOS DE LOG")
    print("="*60)
    
    log_dir = Path('logs')
    if not log_dir.exists():
        print("❌ El directorio 'logs/' no existe. Asegúrate de que la app esté corriendo.")
        return False
    
    log_files = ['app.log', 'access.log', 'search.log', 'error.log', 'performance.log']
    
    print("\nArchivos de log:")
    for log_file in log_files:
        file_path = log_dir / log_file
        if file_path.exists():
            size = file_path.stat().st_size
            if size > 1024*1024:  # Más de 1MB
                size_str = f"{size / (1024*1024):.2f} MB"
            elif size > 1024:  # Más de 1KB
                size_str = f"{size / 1024:.2f} KB"
            else:
                size_str = f"{size} bytes"
            
            # Contar líneas
            with open(file_path, 'r') as f:
                lines = sum(1 for _ in f)
            
            print(f"   ✅ {log_file}: {size_str} ({lines} líneas)")
        else:
            print(f"   ⚠️  {log_file}: No existe aún")
    
    return True

def main():
    """Función principal"""
    print("\n" + "="*70)
    print(" 🔍 SISTEMA DE MÉTRICAS Y LOGGING - CONTRATOS GUBERNAMENTALES")
    print("="*70)
    
    # Verificar archivos
    if not check_log_files():
        return
    
    # Mostrar todas las métricas
    show_recent_activity()
    show_searches()
    show_performance()
    show_errors()
    show_live_tail()
    
    print("\n" + "="*70)
    print(" 💡 TIP: Ejecuta este script regularmente para monitorear tu app")
    print("="*70)
    print()

if __name__ == "__main__":
    main()