"""
Script para ejecutar un solo script de descarga con debugging completo.
Uso: python update/run_single.py curva_pesos_uyu_temp
"""
import sys
import os
from pathlib import Path

# Agregar el directorio raíz al path
root_dir = Path(__file__).parent.parent
sys.path.insert(0, str(root_dir))

def main():
    if len(sys.argv) < 2:
        print("Uso: python update/run_single.py <nombre_script>")
        print("\nScripts disponibles:")
        print("  - curva_pesos_uyu_temp")
        print("  - curva_pesos_uyu_ui_temp")
        print("  - ipc_colombia")
        print("  - ipc_paraguay")
        sys.exit(1)
    
    script_name = sys.argv[1]
    
    # Mapeo de nombres a módulos
    scripts = {
        'curva_pesos_uyu_temp': 'update.download.curva_pesos_uyu_temp',
        'curva_pesos_uyu_ui_temp': 'update.download.curva_pesos_uyu_ui_temp',
        'ipc_colombia': 'update.download.ipc_colombia',
        'ipc_paraguay': 'update.download.ipc_paraguay',
    }
    
    if script_name not in scripts:
        print(f"Error: Script '{script_name}' no reconocido")
        print(f"Scripts disponibles: {', '.join(scripts.keys())}")
        sys.exit(1)
    
    module_name = scripts[script_name]
    
    try:
        print(f"Importando módulo: {module_name}")
        module = __import__(module_name, fromlist=['main'])
        
        print(f"Ejecutando: {script_name}")
        print("=" * 80)
        module.main()
        print("=" * 80)
        print("Script completado exitosamente")
        
    except Exception as e:
        print(f"\n{'='*80}")
        print(f"ERROR: El script falló con: {type(e).__name__}: {e}")
        print(f"{'='*80}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()
