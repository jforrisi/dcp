# Checklist de Migración de Scripts - Fase 7

Este checklist se usa para trackear el progreso de migración de cada script de actualización a la nueva estructura normalizada.

## Instrucciones

Para cada script migrado, marca las casillas correspondientes cuando completes cada paso.

---

## Scripts de Actualización

### Macro

#### Scripts Simples
- [ ] `macro/update/tipo_cambio_usd.py`
  - [ ] Script migrado
  - [ ] Probado localmente
  - [ ] Datos verificados en BD
  - [ ] Endpoints probados
  - [ ] Listo para producción

- [ ] `macro/update/tipo_cambio_eur.py`
  - [ ] Script migrado
  - [ ] Probado localmente
  - [ ] Datos verificados en BD
  - [ ] Endpoints probados
  - [ ] Listo para producción

- [ ] `macro/update/ipc.py`
  - [ ] Script migrado
  - [ ] Probado localmente
  - [ ] Datos verificados en BD
  - [ ] Endpoints probados
  - [ ] Listo para producción

- [ ] `macro/update/salario_real.py`
  - [ ] Script migrado
  - [ ] Probado localmente
  - [ ] Datos verificados en BD
  - [ ] Endpoints probados
  - [ ] Listo para producción

#### Scripts de Países Individuales
- [ ] `macro/update/nxr_argy.py`
  - [ ] Script migrado
  - [ ] Probado localmente
  - [ ] Datos verificados en BD
  - [ ] Endpoints probados
  - [ ] Listo para producción

- [ ] `macro/update/nxr_bra.py`
  - [ ] Script migrado
  - [ ] Probado localmente
  - [ ] Datos verificados en BD
  - [ ] Endpoints probados
  - [ ] Listo para producción

- [ ] `macro/update/nxr_chile.py`
  - [ ] Script migrado
  - [ ] Probado localmente
  - [ ] Datos verificados en BD
  - [ ] Endpoints probados
  - [ ] Listo para producción

- [ ] `macro/update/nxr_peru.py`
  - [ ] Script migrado
  - [ ] Probado localmente
  - [ ] Datos verificados en BD
  - [ ] Endpoints probados
  - [ ] Listo para producción

- [ ] `macro/update/ipc_paraguay.py`
  - [ ] Script migrado
  - [ ] Probado localmente
  - [ ] Datos verificados en BD
  - [ ] Endpoints probados
  - [ ] Listo para producción

#### Scripts Multipaís (Complejos)
- [ ] `macro/update/ipc_multipais.py`
  - [ ] Script migrado
  - [ ] Probado localmente
  - [ ] Datos verificados en BD
  - [ ] Endpoints probados
  - [ ] Listo para producción

- [ ] `macro/update/nxr_bcch_multipais.py`
  - [ ] Script migrado
  - [ ] Probado localmente
  - [ ] Datos verificados en BD
  - [ ] Endpoints probados
  - [ ] Listo para producción

- [ ] `macro/update/combustibles_miem.py`
  - [ ] Script migrado
  - [ ] Probado localmente
  - [ ] Datos verificados en BD
  - [ ] Endpoints probados
  - [ ] Listo para producción

- [ ] `macro/update/nxr_argy_cargar_historico.py`
  - [ ] Script migrado
  - [ ] Probado localmente
  - [ ] Datos verificados en BD
  - [ ] Endpoints probados
  - [ ] Listo para producción

### Precios - Productos

- [ ] `precios/update/productos/novillo_hacienda.py`
  - [ ] Script migrado
  - [ ] Probado localmente
  - [ ] Datos verificados en BD
  - [ ] Endpoints probados
  - [ ] Listo para producción

- [ ] `precios/update/productos/leche_polvo_entera.py`
  - [ ] Script migrado
  - [ ] Probado localmente
  - [ ] Datos verificados en BD
  - [ ] Endpoints probados
  - [ ] Listo para producción

- [ ] `precios/update/productos/queso_export.py`
  - [ ] Script migrado
  - [ ] Probado localmente
  - [ ] Datos verificados en BD
  - [ ] Endpoints probados
  - [ ] Listo para producción

- [ ] `precios/update/productos/precio_leche_productor.py`
  - [ ] Script migrado
  - [ ] Probado localmente
  - [ ] Datos verificados en BD
  - [ ] Endpoints probados
  - [ ] Listo para producción

- [ ] `precios/update/productos/carne_exportacion.py`
  - [ ] Script migrado
  - [ ] Probado localmente
  - [ ] Datos verificados en BD
  - [ ] Endpoints probados
  - [ ] Listo para producción

- [ ] `precios/update/productos/celulosa_pulp.py`
  - [ ] Script migrado
  - [ ] Probado localmente
  - [ ] Datos verificados en BD
  - [ ] Endpoints probados
  - [ ] Listo para producción

- [ ] `precios/update/productos/precio_arroz_wb.py`
  - [ ] Script migrado
  - [ ] Probado localmente
  - [ ] Datos verificados en BD
  - [ ] Endpoints probados
  - [ ] Listo para producción

- [ ] `precios/update/productos/precio_soja_wb.py`
  - [ ] Script migrado
  - [ ] Probado localmente
  - [ ] Datos verificados en BD
  - [ ] Endpoints probados
  - [ ] Listo para producción

- [ ] `precios/update/productos/precio_trigo_wb.py`
  - [ ] Script migrado
  - [ ] Probado localmente
  - [ ] Datos verificados en BD
  - [ ] Endpoints probados
  - [ ] Listo para producción

### Precios - Servicios

- [ ] `precios/update/servicios/arquitectura.py`
  - [ ] Script migrado
  - [ ] Probado localmente
  - [ ] Datos verificados en BD
  - [ ] Endpoints probados
  - [ ] Listo para producción

- [ ] `precios/update/servicios/bookkeeping.py`
  - [ ] Script migrado
  - [ ] Probado localmente
  - [ ] Datos verificados en BD
  - [ ] Endpoints probados
  - [ ] Listo para producción

- [ ] `precios/update/servicios/contabilidad.py`
  - [ ] Script migrado
  - [ ] Probado localmente
  - [ ] Datos verificados en BD
  - [ ] Endpoints probados
  - [ ] Listo para producción

- [ ] `precios/update/servicios/ingenieria.py`
  - [ ] Script migrado
  - [ ] Probado localmente
  - [ ] Datos verificados en BD
  - [ ] Endpoints probados
  - [ ] Listo para producción

- [ ] `precios/update/servicios/software.py`
  - [ ] Script migrado
  - [ ] Probado localmente
  - [ ] Datos verificados en BD
  - [ ] Endpoints probados
  - [ ] Listo para producción

- [ ] `precios/update/servicios/servicios_no_tradicionales.py`
  - [ ] Script migrado
  - [ ] Probado localmente
  - [ ] Datos verificados en BD
  - [ ] Endpoints probados
  - [ ] Listo para producción

---

## Proceso de Migración por Script

Para cada script, seguir estos pasos:

1. **Backup**: Hacer copia del script original
   ```bash
   cp script.py script.py.backup
   ```

2. **Modificar**: Actualizar función `insertar_en_bd()` usando `helpers/maestro_helper.py`
   - Ver ejemplo en `migracion_fase6_template_script.py`

3. **Probar Localmente**: Ejecutar el script y verificar que funciona
   ```bash
   python script.py
   ```

4. **Verificar Datos**: Comprobar en BD que:
   - Registro se insertó correctamente en `maestro`
   - FKs se crearon correctamente (si aplica)
   - Precios se insertaron en `maestro_precios`

5. **Probar Endpoints**: Verificar que el backend funciona con los nuevos datos
   - Probar endpoints relevantes (prices, dcp, cotizaciones según corresponda)

6. **Marcar como Completado**: Una vez verificado, marcar checklist

---

## Notas

- **Orden sugerido**: Empezar con scripts simples (tipo_cambio_usd.py) y avanzar hacia los más complejos
- **Compatibilidad**: Los scripts migrados deben funcionar incluso si las FKs no se pueden obtener
- **Rollback**: Si algo falla, simplemente restaurar el backup del script original
