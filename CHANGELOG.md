# Changelog

Este archivo registra la evolucion funcional de PokeVault TCG a partir del MVP actual.

Formato sugerido:

- `Added`: funcionalidades nuevas
- `Changed`: cambios de comportamiento o UX
- `Fixed`: correcciones
- `Removed`: elementos eliminados

## [Unreleased]

### Added

- Pendiente

## [0.1.0-mvp] - 2026-06-25

### Added

- Autenticacion con login JWT, perfil propio y cambio obligatorio de clave.
- Panel de usuarios con creacion y edicion de accesos.
- Persistencia por usuario de theme, dark/light, preset y colores en navegador.
- Busqueda de cartas por nombre, codigo, promo y modo general.
- Busqueda local de inventario sin depender de la coleccion.
- Fallback de busqueda a TCGdex cuando Pokemon TCG API no devuelve resultados.
- Vista de colecciones en tabla con creacion por modal y configuracion por modal.
- Eliminacion de colecciones con confirmacion.
- Toggle por coleccion para ordenar por numero de Pokedex.
- Detalle de coleccion con tabla de cartas, seleccion multiple y movimiento entre colecciones.
- Exportacion de colecciones a PDF y Excel.
- Alta manual de cartas con carga de imagen propia.
- Descarga y almacenamiento local persistente de imagenes de cartas.
- Vista previa ampliada de cartas dentro de colecciones e inventario.
- Dashboard con valorizacion por coleccion.
- Historial de snapshots y variacion entre valorizaciones.

### Changed

- Se separaron `Mi perfil` y `Usuarios` en vistas distintas.
- Se simplifico la navegacion superior y lateral para alinearla a PokeVault TCG.
- Se ajusto el login para no precargar credenciales de ejemplo.
- El dialogo para agregar cartas ahora recuerda la ultima coleccion y preferencias de alta.
- La carga de cartas ahora intenta sugerir acabado y precio base segun metadata disponible.
- Las colecciones de dashboard se muestran solo cuando tienen cartas.
- La valorizacion de colecciones en dashboard se ordena de mayor a menor valor.
- El topbar usa identidad visual propia de PokeVault TCG.

### Fixed

- Evita que una actualizacion de precios pise un valor manual previo con `0` o sin precio valido.
- Correcciones en busqueda por codigo con normalizacion de formatos como `001/165`.
- Correcciones para resultados promo y subsets especiales.
- Manejo mas robusto de imagenes faltantes desde APIs externas.
- Mejoras en mensajes y flujo de movimiento de cartas entre colecciones.
