#!/usr/bin/env python3
"""
Script para executar Celery Worker e Beat.
"""
import os
import sys
import subprocess
from multiprocessing import Process

def run_celery_worker():
    """Executa Celery Worker."""
    print("🔄 Iniciando Celery Worker...")
    cmd = [
        'celery', '-A', 'interjornada_system', 'worker',
        '--loglevel=info',
        '--concurrency=4',
        '--queues=devices,logs,interjornada,dashboard'
    ]
    subprocess.run(cmd)

def run_celery_beat():
    """Executa Celery Beat."""
    print("⏰ Iniciando Celery Beat...")
    cmd = [
        'celery', '-A', 'interjornada_system', 'beat',
        '--loglevel=info'
    ]
    subprocess.run(cmd)

def run_celery_flower():
    """Executa Celery Flower (monitoramento)."""
    print("🌸 Iniciando Celery Flower...")
    cmd = [
        'celery', '-A', 'interjornada_system', 'flower',
        '--port=5555'
    ]
    subprocess.run(cmd)

def main():
    """Função principal."""
    print("=" * 60)
    print("🔄 CELERY WORKER & BEAT - SISTEMA DE INTERJORNADA")
    print("=" * 60)
    
    # Verificar se Celery está instalado
    try:
        import celery
        print(f"✅ Celery {celery.__version__} encontrado")
    except ImportError:
        print("❌ Celery não encontrado. Instale com: pip install celery")
        sys.exit(1)
    
    # Verificar se Redis está rodando
    try:
        import redis
        r = redis.Redis(host='localhost', port=6379, db=0)
        r.ping()
        print("✅ Redis conectado")
    except Exception as e:
        print(f"❌ Redis não conectado: {e}")
        print("Inicie Redis com: redis-server")
        sys.exit(1)
    
    # Iniciar processos
    processes = []
    
    try:
        # Worker
        worker_process = Process(target=run_celery_worker)
        worker_process.start()
        processes.append(worker_process)
        
        # Beat
        beat_process = Process(target=run_celery_beat)
        beat_process.start()
        processes.append(beat_process)
        
        # Flower (opcional)
        try:
            flower_process = Process(target=run_celery_flower)
            flower_process.start()
            processes.append(flower_process)
            print("🌸 Flower disponível em: http://localhost:5555")
        except Exception as e:
            print(f"⚠️ Flower não disponível: {e}")
        
        print("\n✅ Celery iniciado com sucesso!")
        print("🔄 Worker: Processando tarefas")
        print("⏰ Beat: Agendando tarefas")
        print("🌸 Flower: http://localhost:5555")
        print("\nPressione Ctrl+C para parar...")
        
        # Aguardar processos
        for process in processes:
            process.join()
            
    except KeyboardInterrupt:
        print("\n🛑 Parando Celery...")
        for process in processes:
            process.terminate()
            process.join()
        print("✅ Celery parado com sucesso!")

if __name__ == '__main__':
    main()
