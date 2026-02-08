"""
Script de Limpieza de Archivos No Utilizados
============================================
Identifica y elimina archivos no utilizados en el sistema:
- Scripts de migración completados
- Scripts de diagnóstico y verificación
- Archivos temporales
- Backups duplicados
- Archivos de prueba
- Documentación obsoleta

Modos de ejecución:
- --dry-run (por defecto): Solo muestra qué se eliminaría
- --execute: Elimina los archivos
- --interactive: Pregunta antes de eliminar cada archivo
"""

import os
import re
import ast
import fnmatch
from pathlib import Path
from typing import List, Dict, Set, Tuple, Optional
from datetime import datetime
from collections import defaultdict
import argparse


# Directorios y archivos a MANTENER siempre
DIRECTORIOS_PROTEGIDOS = {
    'backend',
    'frontend',
    'update',
    'helpers',
    'data_raw',
    'backup',  # Carpeta de backups (no archivos individuales)
}

ARCHIVOS_PROTEGIDOS = {
    'requirements.txt',
    'Procfile',
    'railway.json',
    'nixpacks.toml',
    'build.bat',
    'build.sh',
    'series_tiempo.db',
    'update_database.txt',  # Si se usa
    'README.md',
    'README_SETUP.md',
    'GIT_SETUP.md',
    'RAILWAY_DEPLOY.md',
    'RAILWAY_UPDATE_DATABASE.md',
    'ejecutar_todas_actualizaciones.py',
    'update/update_database.py',
}

# Patrones de archivos a ELIMINAR
PATRONES_ELIMINAR = {
    # Scripts de migración
    'migracion': ['migracion_*.py', 'migrar_*.py', 'MIGRACION_*.md', 'RESUMEN_MIGRACION_*.md'],
    
    # Scripts de diagnóstico y verificación
    'diagnostico': ['diagnostico_*.py', 'verificar_*.py', 'analizar_*.py', 'buscar_*.py'],
    
    # Scripts de test (revisar si son parte de suite)
    'test': ['test_*.py'],
    
    # Archivos temporales
    'temporales': ['~$*.xlsx', 'z.py', 'zz.py'],
    
    # Archivos de prueba/exportación
    'prueba': ['prueba_*.xlsx', 'exportar_*.py'],
    
    # Scripts obsoletos
    'obsoletos': [
        'actualizar_*.py',  # Excepto los en update/
        'agregar_*.py',
        'aplicar_*.py',
        'cargar_*.py',
        'activar_*.py',
        'fix_*.py',
        'consultar_*.py',
        'ejecutar_solo_*.py',
    ],
    
    # Archivos de reporte
    'reportes': ['*.txt'],  # Excepto update_database.txt (ya protegido)
    
    # Documentación obsoleta
    'documentacion': ['ANALISIS_*.md', 'ESTADO_*.md', 'REPORTE_*.md'],
}

# Excepciones: archivos que parecen obsoletos pero pueden estar en uso
EXCEPCIONES_REVISAR = {
    'update_database.py',  # En raíz, parece obsoleto pero verificar
    'update_database_complicados.py',
    'limpiar_scripts_automatico.py',
    'migrar_scripts_actualizacion.py',
    'INSTRUCCIONES_*.md',
}


class LimpiadorArchivos:
    """Clase principal para limpiar archivos no utilizados."""
    
    def __init__(self, proyecto_root: Path):
        self.proyecto_root = proyecto_root
        self.archivos_importados: Set[str] = set()
        self.archivos_ejecutados: Set[str] = set()
        self.archivos_referenciados: Set[str] = set()
        self.archivos_a_eliminar: Dict[str, List[Path]] = defaultdict(list)
        self.archivos_a_revisar: List[Path] = []
        self.total_tamaño = 0
        
    def analizar_imports(self) -> None:
        """Analiza todos los archivos Python para encontrar imports."""
        print("Analizando imports y referencias...")
        
        for archivo_py in self.proyecto_root.rglob("*.py"):
            # Saltar archivos en directorios protegidos (excepto para análisis)
            if any(archivo_py.parts[0] == dir_prot for dir_prot in DIRECTORIOS_PROTEGIDOS):
                continue
                
            try:
                contenido = archivo_py.read_text(encoding='utf-8', errors='ignore')
                tree = ast.parse(contenido, filename=str(archivo_py))
                
                # Analizar imports
                for node in ast.walk(tree):
                    if isinstance(node, ast.Import):
                        for alias in node.names:
                            self.archivos_importados.add(alias.name.split('.')[0])
                    elif isinstance(node, ast.ImportFrom):
                        if node.module:
                            self.archivos_importados.add(node.module.split('.')[0])
                
                # Buscar referencias a archivos en strings (subprocess, exec, etc.)
                for node in ast.walk(tree):
                    if isinstance(node, ast.Str) or isinstance(node, ast.Constant):
                        valor = node.s if isinstance(node, ast.Str) else node.value
                        if isinstance(valor, str):
                            # Buscar referencias a archivos .py
                            matches = re.findall(r'[\w/]+\.py', valor)
                            for match in matches:
                                self.archivos_referenciados.add(match)
                                
            except Exception as e:
                # Ignorar errores de parsing
                pass
    
    def buscar_archivos_por_patron(self, patron: str, categoria: str) -> List[Path]:
        """Busca archivos que coincidan con un patrón glob."""
        archivos = []
        
        # Buscar en raíz del proyecto (no en directorios protegidos)
        for archivo in self.proyecto_root.iterdir():
            if archivo.is_file():
                # Verificar si está en directorio protegido
                if any(archivo.parts[0] == dir_prot for dir_prot in DIRECTORIOS_PROTEGIDOS):
                    continue
                    
                # Verificar si está protegido
                if archivo.name in ARCHIVOS_PROTEGIDOS:
                    continue
                
                # Para scripts obsoletos, excluir los que están en update/
                if categoria == 'obsoletos' and 'actualizar' in patron.lower():
                    # No incluir archivos en update/ ya que son activos
                    continue
                
                # Verificar si coincide con el patrón glob
                if fnmatch.fnmatch(archivo.name, patron):
                    archivos.append(archivo)
        
        return archivos
    
    def gestionar_backups(self) -> None:
        """Gestiona backups de bases de datos, manteniendo solo los más recientes."""
        print("Analizando backups de bases de datos...")
        
        backups = []
        
        # Buscar en raíz
        for archivo in self.proyecto_root.glob("series_tiempo_backup_*.db"):
            if archivo.is_file():
                backups.append(archivo)
        
        # Buscar en backend
        backend_dir = self.proyecto_root / "backend"
        if backend_dir.exists():
            for archivo in backend_dir.glob("series_tiempo_backup_*.db"):
                if archivo.is_file():
                    backups.append(archivo)
        
        if len(backups) <= 2:
            # Mantener todos si hay 2 o menos
            return
        
        # Ordenar por fecha de modificación (más reciente primero)
        backups.sort(key=lambda x: x.stat().st_mtime, reverse=True)
        
        # Mantener solo los 2 más recientes
        backups_a_eliminar = backups[2:]
        
        for backup in backups_a_eliminar:
            self.archivos_a_eliminar['backups'].append(backup)
            self.total_tamaño += backup.stat().st_size
    
    def verificar_archivo_obsoleto(self, archivo: Path) -> bool:
        """Verifica si un archivo obsoleto realmente no se usa."""
        nombre_sin_ext = archivo.stem
        
        # Verificar si está en imports
        if nombre_sin_ext in self.archivos_importados:
            return False
        
        # Verificar si está referenciado
        for ref in self.archivos_referenciados:
            if nombre_sin_ext in ref or archivo.name in ref:
                return False
        
        # Verificar si está en excepciones
        for excepcion in EXCEPCIONES_REVISAR:
            if archivo.match(excepcion):
                return False
        
        return True
    
    def analizar_archivos(self) -> None:
        """Analiza todos los archivos del proyecto."""
        print("Analizando archivos del proyecto...")
        
        # Analizar imports primero
        self.analizar_imports()
        
        # Buscar archivos por patrones
        for categoria, patrones in PATRONES_ELIMINAR.items():
            for patron in patrones:
                archivos = self.buscar_archivos_por_patron(patron, categoria)
                
                for archivo in archivos:
                    # Excluir archivos en update/ de patrones obsoletos
                    if categoria == 'obsoletos' and 'update' in str(archivo):
                        continue
                    
                    # Excluir update_database.txt de reportes
                    if categoria == 'reportes' and archivo.name == 'update_database.txt':
                        continue
                    
                    # Verificar si es obsoleto
                    if categoria == 'obsoletos':
                        if not self.verificar_archivo_obsoleto(archivo):
                            self.archivos_a_revisar.append(archivo)
                            continue
                    
                    # Verificar excepciones
                    es_excepcion = False
                    for excepcion in EXCEPCIONES_REVISAR:
                        if fnmatch.fnmatch(archivo.name, excepcion):
                            self.archivos_a_revisar.append(archivo)
                            es_excepcion = True
                            break
                    
                    if not es_excepcion:
                        self.archivos_a_eliminar[categoria].append(archivo)
                        self.total_tamaño += archivo.stat().st_size
        
        # Gestionar backups
        self.gestionar_backups()
        
        # Verificar update_database.py en raíz (parece obsoleto)
        update_db_raiz = self.proyecto_root / "update_database.py"
        if update_db_raiz.exists():
            # Verificar si se usa (buscar referencias)
            contenido = update_db_raiz.read_text(encoding='utf-8', errors='ignore')
            # Si referencia precios/ o macro/ antiguos, es obsoleto
            if 'precios/download' in contenido or 'precios/update' in contenido or 'macro/update' in contenido:
                # Verificar que no esté siendo importado o ejecutado
                if not self.verificar_archivo_obsoleto(update_db_raiz):
                    self.archivos_a_revisar.append(update_db_raiz)
                else:
                    self.archivos_a_eliminar['obsoletos'].append(update_db_raiz)
                    self.total_tamaño += update_db_raiz.stat().st_size
    
    def generar_reporte(self) -> str:
        """Genera un reporte detallado de archivos a eliminar."""
        reporte = []
        reporte.append("=" * 80)
        reporte.append("REPORTE DE LIMPIEZA DE ARCHIVOS NO UTILIZADOS")
        reporte.append("=" * 80)
        reporte.append(f"Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        reporte.append("")
        
        total_archivos = sum(len(archivos) for archivos in self.archivos_a_eliminar.values())
        reporte.append(f"Total de archivos a eliminar: {total_archivos}")
        reporte.append(f"Espacio a liberar: {self._formatear_tamaño(self.total_tamaño)}")
        reporte.append("")
        
        # Por categoría
        for categoria, archivos in sorted(self.archivos_a_eliminar.items()):
            if archivos:
                reporte.append(f"\n{categoria.upper()} ({len(archivos)} archivos):")
                reporte.append("-" * 80)
                for archivo in sorted(archivos):
                    tamaño = archivo.stat().st_size
                    reporte.append(f"  {archivo.name:50s} ({self._formatear_tamaño(tamaño)})")
        
        # Archivos a revisar
        if self.archivos_a_revisar:
            reporte.append(f"\n\nARCHIVOS A REVISAR MANUALMENTE ({len(self.archivos_a_revisar)} archivos):")
            reporte.append("-" * 80)
            for archivo in sorted(self.archivos_a_revisar):
                reporte.append(f"  {archivo.name}")
        
        reporte.append("\n" + "=" * 80)
        
        return "\n".join(reporte)
    
    def _formatear_tamaño(self, bytes: int) -> str:
        """Formatea el tamaño en bytes a formato legible."""
        for unidad in ['B', 'KB', 'MB', 'GB']:
            if bytes < 1024.0:
                return f"{bytes:.2f} {unidad}"
            bytes /= 1024.0
        return f"{bytes:.2f} TB"
    
    def eliminar_archivos(self, modo_interactivo: bool = False) -> Tuple[int, int]:
        """Elimina los archivos identificados."""
        eliminados = 0
        errores = 0
        
        todos_archivos = []
        for archivos in self.archivos_a_eliminar.values():
            todos_archivos.extend(archivos)
        
        for archivo in sorted(todos_archivos):
            if modo_interactivo:
                respuesta = input(f"¿Eliminar {archivo.name}? (s/n): ").strip().lower()
                if respuesta != 's':
                    continue
            
            try:
                archivo.unlink()
                eliminados += 1
                print(f"✓ Eliminado: {archivo.name}")
            except Exception as e:
                errores += 1
                print(f"✗ Error al eliminar {archivo.name}: {e}")
        
        return eliminados, errores


def main():
    """Función principal."""
    parser = argparse.ArgumentParser(
        description='Limpia archivos no utilizados del proyecto',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Ejemplos:
  python limpiar_archivos_no_usados.py                    # Modo dry-run (por defecto)
  python limpiar_archivos_no_usados.py --dry-run           # Modo dry-run explícito
  python limpiar_archivos_no_usados.py --execute           # Elimina archivos
  python limpiar_archivos_no_usados.py --interactive       # Pregunta antes de eliminar
        """
    )
    
    parser.add_argument(
        '--dry-run',
        action='store_true',
        default=True,
        help='Solo muestra qué se eliminaría sin hacer cambios (por defecto)'
    )
    parser.add_argument(
        '--execute',
        action='store_true',
        help='Elimina los archivos identificados'
    )
    parser.add_argument(
        '--interactive',
        action='store_true',
        help='Pregunta antes de eliminar cada archivo'
    )
    parser.add_argument(
        '--reporte',
        type=str,
        help='Guarda el reporte en un archivo'
    )
    
    args = parser.parse_args()
    
    # Determinar modo
    if args.execute:
        modo = 'execute'
    elif args.interactive:
        modo = 'interactive'
    else:
        modo = 'dry-run'
    
    # Obtener directorio raíz del proyecto
    proyecto_root = Path(__file__).parent.absolute()
    
    print("=" * 80)
    print("LIMPIEZA DE ARCHIVOS NO UTILIZADOS")
    print("=" * 80)
    print(f"Directorio: {proyecto_root}")
    print(f"Modo: {modo}")
    print("")
    
    # Crear limpiador
    limpiador = LimpiadorArchivos(proyecto_root)
    
    # Analizar archivos
    limpiador.analizar_archivos()
    
    # Generar reporte
    reporte = limpiador.generar_reporte()
    print(reporte)
    
    # Guardar reporte si se solicita
    if args.reporte:
        reporte_path = proyecto_root / args.reporte
        reporte_path.write_text(reporte, encoding='utf-8')
        print(f"\nReporte guardado en: {reporte_path}")
    
    # Ejecutar limpieza según modo
    if modo == 'dry-run':
        print("\n" + "=" * 80)
        print("MODO DRY-RUN: No se eliminaron archivos.")
        print("Usa --execute para eliminar o --interactive para modo interactivo.")
        print("=" * 80)
    elif modo == 'execute':
        print("\n" + "=" * 80)
        respuesta = input("¿Estás seguro de eliminar estos archivos? (escribe 'SI' para confirmar): ")
        if respuesta == 'SI':
            eliminados, errores = limpiador.eliminar_archivos(modo_interactivo=False)
            print("\n" + "=" * 80)
            print(f"Limpieza completada: {eliminados} archivos eliminados, {errores} errores")
            print("=" * 80)
        else:
            print("Operación cancelada.")
    elif modo == 'interactive':
        print("\n" + "=" * 80)
        print("MODO INTERACTIVO: Se preguntará antes de eliminar cada archivo")
        print("=" * 80)
        eliminados, errores = limpiador.eliminar_archivos(modo_interactivo=True)
        print("\n" + "=" * 80)
        print(f"Limpieza completada: {eliminados} archivos eliminados, {errores} errores")
        print("=" * 80)


if __name__ == "__main__":
    main()
