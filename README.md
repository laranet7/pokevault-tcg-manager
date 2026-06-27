# PokeVault TCG

PokeVault TCG es un gestor personal de cartas Pokemon TCG orientado a inventario real. Permite buscar cartas, agregarlas a colecciones, registrar estado, acabado, idioma, valorizar colecciones, exportarlas y administrar usuarios, todo sobre una base local propia.

## Estado actual

El proyecto ya cuenta con un MVP funcional con frontend en Vue 3 + Sakai/PrimeVue y backend en FastAPI + PostgreSQL.

Consulta tambien el historial funcional en [CHANGELOG.md](./CHANGELOG.md).

## Funcionalidades existentes

### Autenticacion y cuenta

- Login con JWT.
- Cambio obligatorio de clave en primer acceso.
- Cambio de clave desde menu superior.
- Edicion de perfil propio.
- Administracion de usuarios solo para administradores.
- Creacion y edicion de usuarios con control de estado, rol admin y forzado de cambio de clave.
- Los administradores pueden acceder a la administracion global del sistema y no quedan limitados por permisos de coleccion.
- El login no precarga credenciales por defecto.

### Preferencias visuales

- Theme Sakai con modo claro y oscuro.
- Seleccion de preset, color primario y surface.
- Persistencia por usuario en `localStorage` del navegador.
- Logo de topbar personalizado para PokeVault TCG.

### Busqueda de cartas

- Busqueda general por nombre o codigo.
- Busqueda por codigo normal en formato `160/165`.
- Mascara y normalizacion de codigo, por ejemplo `001/165 -> 1/165`.
- Busqueda de promos por codigo, por ejemplo `SVP/088`.
- Busqueda de promos por nombre.
- Soporte para subsets y codigos especiales como `TG01/TG30`.
- Fallback de busqueda a TCGdex cuando Pokemon TCG API no encuentra resultados.
- Badge de fuente para distinguir resultados externos cuando aplica.

### Inventario y colecciones

- Creacion, edicion y eliminacion de colecciones.
- Vista de colecciones en tabla.
- Confirmacion antes de eliminar una coleccion.
- Configuracion de coleccion en modal.
- Toggle por coleccion para ordenar cartas Pokemon por numero de Pokedex y dejar no Pokemon al final.
- Solo se crean las colecciones que el usuario defina; no se generan colecciones seed por defecto.
- Detalle de coleccion con tabla de cartas, seleccion multiple y panel de valorizacion.
- Edicion de items dentro de una coleccion.
- Movimiento de una o varias cartas entre colecciones.
- Busqueda local en inventario, sin importar en que coleccion este la carta.
- Soporte de ownership por coleccion.
- Soporte de colaboradores por coleccion con roles `viewer` y `editor`.
- Transferencia de ownership de una coleccion a otro usuario autorizado.
- El owner puede administrar colaboradores y transferir la coleccion.
- Un colaborador `viewer` puede ver la coleccion, pero no modificarla.
- Un colaborador `editor` puede editar items y operar sobre la coleccion, pero no administrar ownership.
- La visibilidad publica y privada sigue disponible como propiedad funcional de la coleccion.

### Alta de cartas al inventario

- Agregado de cartas desde resultados de busqueda.
- Evita duplicados logicos mediante merge por carta y coleccion cuando corresponde.
- Alta manual para cartas que no existen en APIs externas.
- Opcion de subir imagen manual al crear o importar una carta.
- Persistencia de preferencias del dialogo de alta.
- Ultima coleccion usada.
- Idioma.
- Estado.
- Acabado.
- Toggle Pokeball.
- Precarga de acabado sugerido usando metadata y precios de la API cuando es posible.

### Imagenes de cartas

- Se mantiene URL de imagen externa en base de datos.
- Ademas se guarda copia local de imagen en almacenamiento persistente.
- Soporte de imagen `small` y `large`.
- Endpoint local para servir imagenes desde PokeVault TCG.
- Vista previa ampliada de cartas desde detalle de coleccion y desde busqueda de inventario.
- Esto protege parcialmente el inventario ante cambios o desaparicion de imagenes en APIs externas.

### Valorizacion y precios

- Valorizacion por coleccion en dashboard.
- Dashboard mostrando solo colecciones con cartas.
- Orden descendente por precio en valorizacion de colecciones.
- Actualizacion de precios por coleccion.
- Historial de snapshots de precio por item.
- Variacion entre la ultima valorizacion y la anterior.
- Si una API no devuelve precio o devuelve `0`, no se pisa automaticamente un valor manual previo valido.
- Soporte de monedas segun fuente disponible, incluyendo casos en USD y EUR.

### Exportacion

- Exportacion de coleccion a PDF.
- Exportacion de coleccion a Excel.
- En PDF se puede elegir 2 o 3 columnas.
- En PDF se usan imagenes de cartas del propio sistema.
- Opciones para incluir precio TCG y precio final de venta.
- El PDF incluye datos como nombre, rareza, estado, edicion, acabado, idioma y cantidad.
- Excel se exporta como tabla para ordenar o filtrar luego.

### Integraciones externas

- Integracion principal con Pokemon TCG API.
- Integracion de respaldo con TCGdex para busquedas no resueltas por la API principal.
- Envio automatico de `X-Api-Key` desde backend cuando `POKEMON_TCG_API_KEY` esta configurada.

## Stack

### Backend

- FastAPI
- SQLAlchemy Async
- Alembic
- PostgreSQL
- Docker

### Frontend

- Vue 3
- PrimeVue
- Sakai Vue
- Vite
- Tailwind utility classes

## Variables de entorno

Copia `.env.example` a `.env` y ajusta los valores segun tu entorno.

| Variable | Descripcion |
| --- | --- |
| `POSTGRES_USER` | Usuario de PostgreSQL |
| `POSTGRES_PASSWORD` | Clave de PostgreSQL |
| `POSTGRES_DB` | Base de datos |
| `POSTGRES_PORT` | Puerto local del contenedor PostgreSQL |
| `DATABASE_URL` | Conexion async usada por el backend |
| `CORS_ORIGINS` | Origenes permitidos para frontend |
| `POKEMON_TCG_API_URL` | URL base de Pokemon TCG API |
| `POKEMON_TCG_API_KEY` | API key enviada como `X-Api-Key` |
| `MEDIA_ROOT` | Ruta de almacenamiento local de imagenes |
| `SEED_DEFAULT_ADMIN` | Si es `true`, intenta bootstrapear un admin inicial |
| `TERMS_VERSION` | Version vigente de los terminos de uso |
| `AUTH_SECRET_KEY` | Secreto para JWT |
| `AUTH_TOKEN_TTL_HOURS` | Duracion del token |
| `VITE_API_BASE_URL` | URL base que usa el frontend |

## Como levantar el proyecto

### Con Docker Compose

1. Copia `.env.example` a `.env`.
2. Completa `POKEMON_TCG_API_KEY` cuando la tengas disponible.
3. Desde la raiz ejecuta:

```powershell
docker compose up -d --build
```

4. Si necesitas aplicar migraciones manualmente:

```powershell
docker compose exec backend alembic upgrade head
```

### Servicios locales

- Frontend: `http://localhost:8080`
- Backend: `http://localhost:8000`
- Swagger/OpenAPI: `http://localhost:8000/docs`

## Acceso inicial

- La pantalla de login no rellena `Admin / Admin`.
- Si `SEED_DEFAULT_ADMIN=true`, el backend intentara crear el usuario administrador inicial definido por el seed para bootstrap.
- En el primer login, el usuario marcado con `must_change_password=true` sera redirigido al cambio obligatorio de clave.

Si no quieres bootstrap automatico de admin en un ambiente nuevo, desactiva el seed correspondiente antes del deploy.

## Comandos utiles

```powershell
docker compose up -d --build
docker compose down
docker compose logs -f backend
docker compose logs -f frontend
docker compose exec backend alembic upgrade head
```

## Endpoints principales

### Salud y autenticacion

- `GET /api/health`
- `POST /api/auth/login`
- `GET /api/auth/me`
- `POST /api/auth/change-password`
- `GET /api/me/terms-status`
- `POST /api/me/accept-terms`

### Cartas

- `GET /api/cards/search`
- `GET /api/cards/{id}`
- `GET /api/cards/{id}/image?size=small|large`

### Dashboard y colecciones

- `GET /api/dashboard/collections-valuation`
- `POST /api/collections`
- `GET /api/collections`
- `GET /api/collections/{id}`
- `PATCH /api/collections/{id}`
- `DELETE /api/collections/{id}`
- `POST /api/collections/{id}/refresh-prices`
- `GET /api/collections/{id}/price-variation`
- `GET /api/collections/{id}/collaborators`
- `POST /api/collections/{id}/collaborators`
- `DELETE /api/collections/{id}/collaborators/{user_id}`
- `POST /api/collections/{id}/transfer-ownership`

### Items de coleccion

- `POST /api/collections/{id}/items`
- `POST /api/collections/{id}/items/import`
- `POST /api/collections/{id}/items/manual`
- `GET /api/collections/{id}/items`
- `GET /api/collection-items/search?query=...`
- `PATCH /api/collection-items/{id}`
- `DELETE /api/collection-items/{id}`
- `POST /api/collection-items/move`
- `GET /api/collection-items/{id}/price-history`

### Usuarios

- `GET /api/users`
- `GET /api/users/options`
- `POST /api/users`
- `PATCH /api/users/me`
- `PATCH /api/users/{id}`

## Modelo de permisos

- `admin`: puede administrar usuarios y tiene acceso global a colecciones e inventario.
- `owner`: usuario dueno de una coleccion. Puede editarla, administrar colaboradores y transferir ownership.
- `editor`: colaborador con permiso de edicion sobre la coleccion y sus items.
- `viewer`: colaborador con permiso solo de visualizacion.

En endpoints de colecciones, el backend distingue permisos `view`, `edit` y `manage` para resolver acceso segun el rol del usuario.

## Persistencia

Docker Compose usa dos volumenes principales:

- `postgres_data`: datos PostgreSQL
- `pokevault_media`: imagenes locales de cartas

Esto permite mantener inventario e imagenes aun cuando reconstruyas contenedores.

## Estructura del proyecto

```txt
pokevault/
|-- backend/
|-- frontend/
|-- docs/
|-- docker-compose.yml
|-- .env.example
|-- README.md
|-- CHANGELOG.md
```

## Roadmap documental

- `README.md`: vision general, instalacion, variables, uso y arquitectura.
- `CHANGELOG.md`: cambios funcionales posteriores al MVP.

## Support the project

PokeVault TCG is a free, open-source and unofficial project built for personal Pokemon TCG collection management.

If this project is useful to you and you would like to support its development, you can optionally send a voluntary contribution.

Your support helps with maintenance, improvements, documentation, bug fixes and future features.

[Buy me a coffee](https://paypal.me/pokevaulttcg)

Contributions are completely optional. PokeVault TCG will remain free and open source.

## Apoya el proyecto

PokeVault TCG es un proyecto gratuito, open source y no oficial, creado para gestionar colecciones personales de cartas Pokemon TCG.

Si este proyecto te resulta util y quieres apoyar su desarrollo, puedes realizar una contribucion voluntaria.

Tu apoyo ayuda a mantener el proyecto, mejorar la documentacion, corregir errores y desarrollar nuevas funcionalidades.

[Invitame un cafe](https://paypal.me/pokevaulttcg)

Los aportes son completamente opcionales. PokeVault TCG seguira siendo gratuito y open source.

## Disclaimer

Este proyecto es independiente y no esta afiliado a Nintendo, Creatures, GAME FREAK, The Pokemon Company, Pokemon TCG API ni TCGdex.
