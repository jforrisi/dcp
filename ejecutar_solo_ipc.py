"""Script para ejecutar solo IPC y ver el error"""
import subprocess
import sys

print("=" * 80)
print("EJECUTANDO SOLO IPC")
print("=" * 80)
print()

# Ejecutar el script de IPC
script_path = "macro/update/ipc.py"

try:
    proceso = subprocess.Popen(
        [sys.executable, script_path],
        stdin=subprocess.PIPE,
        stdout=sys.stdout,
        stderr=subprocess.PIPE,
        text=True,
        bufsize=1
    )
    
    # Enviar respuestas automáticas si hay confirmaciones
    respuestas = "sí\n" * 10
    proceso.stdin.write(respuestas)
    proceso.stdin.flush()
    proceso.stdin.close()
    
    # Esperar y capturar stderr
    _, stderr_output = proceso.communicate(timeout=600)
    
    if proceso.returncode != 0:
        print("\n" + "=" * 80)
        print("ERROR DETECTADO:")
        print("=" * 80)
        if stderr_output:
            print(stderr_output)
        else:
            print(f"El script terminó con código de salida: {proceso.returncode}")
    else:
        print("\n[OK] Script ejecutado exitosamente")
        
except subprocess.TimeoutExpired:
    proceso.kill()
    print("\n[ERROR] El script tardó más de 10 minutos")
except Exception as e:
    print(f"\n[ERROR] Error al ejecutar: {e}")
    import traceback
    traceback.print_exc()
