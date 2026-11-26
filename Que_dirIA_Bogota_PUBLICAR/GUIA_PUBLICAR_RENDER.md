# Publicar ¿Qué dirIA Bogotá? para compartir con el equipo

## Antes de subir

- Esta carpeta está lista para GitHub y Render; sube **el contenido** de `Que_dirIA_Bogota_PUBLICAR`, no un ZIP único.
- Para garantizar respuestas reales aunque el proveedor reinicie, incorpora en `data/` **los CSV oficiales verificados** de los que se hablará en el pitch. Si aún no los tienes, la app intenta descargarlos desde Datos Abiertos Bogotá cuando arranca; si falla, muestra el modo muestra, que no es equivalente a una respuesta de datos verificados.
- Asegúrate de que el inventario no contenga datos personales; aquí se esperan datos abiertos de parques.
- **Nunca publiques** archivos `.env`, claves de API, información privada ni credenciales.

## Paso 1 — GitHub
1. Entra en https://github.com/new, inicia sesión y crea un repositorio llamado `que-diria-bogota`.
2. Pulsa `Add file` -> `Upload files` y arrastra el contenido de esta carpeta: `server.py`, `render.yaml`, `web/`, `data/`, `tests/`, README y guías.
3. Confirma los cambios (`Commit changes`).
4. Invita a tus compañeros desde `Settings > Collaborators` si necesitan editar el código. Para usar el chatbot **solo necesitan el enlace público**.

## Paso 2 — Render (opción automatizada)
1. Entra en https://dashboard.render.com/ y vincula tu GitHub.
2. Usa `New` -> `Blueprint` y selecciona el repositorio.
3. Detectará `render.yaml` y creará el servicio `que-diria-bogota` con Python y la variable `PUBLIC_DEPLOY=1`.
4. Cuando indique `Live`, abre el enlace `https://...onrender.com` que Render te asigne. **No inventes el enlace; cópialo desde el panel.**
5. Pruébalo también en una ventana privada y desde el celular.

Alternativa manual: `New > Web Service`, elige repo, `Language = Python`, Build Command `echo listo`, Start Command `python server.py`, Health Check Path `/api/health`, Environment `PUBLIC_DEPLOY=1` y `OPEN_BROWSER=0`.

## ¿Puede estar disponible todo el día?
- Render **Free** se suspende tras 15 minutos de inactividad; el primer visitante puede esperar en el inicio. No es adecuado para una demostración crítica.
- En el panel de Render, en el servicio abre `Settings > Instance Type` (el nombre puede variar) y cambia a una instancia de pago **Starter** antes de exponer; consulta precio vigente y método de pago. Una instancia de pago no se suspende por inactividad. Eso no significa garantía de 100 % de disponibilidad.
- Para fiabilidad, **incluye los CSV oficiales como archivos del repositorio** (se vuelven a desplegar con el código). Las importaciones hechas únicamente durante ejecución pueden perderse tras reinicios o despliegues.

## Geminis (opcional)
- La versión básica responde con reglas locales. Si decides habilitar Gemini, guarda `GEMINI_API_KEY` **solo** en `Environment` de Render, nunca en código ni GitHub. Hay consumo y límites de API; controla los costos y el uso público. En el servidor se limita por defecto a 40 intentos de Gemini por hora (`GEMINI_HOURLY_LIMIT`), tras lo cual se vuelve al intérprete local.
- Si no configuras la clave, el chat sigue usando consultas deterministas, pero no debe anunciarse como "Gemini activo".

## Seguridad y edición
- Al activar `PUBLIC_DEPLOY=1` se deshabilitan para visitantes `/api/upload` y `/api/refresh`, para impedir que terceros reemplacen inventarios o provoquen descargas masivas.
- Tus compañeros pueden usar el enlace sin instalar programas. Para cambiar los CSV o el código, suban una actualización a GitHub y Render la desplegará.
- Los resultados de la sección de evaluación se guardan en **cada navegador**; para combinar encuestas cada persona debe exportar su CSV y compartirlo con el equipo.

## Comprobación
1. Abre `https://TU-SERVICIO.onrender.com/api/health` y busca `{"ok": true}`.
2. Abre la página principal. Comprueba en "Datos y evidencia" que el modo sea CSV y las fuentes sean reconocibles.
3. Haz una consulta (por ejemplo: «¿Cuántos parques hay en Suba?») y revisa su fuente.
4. Haz una pregunta no cubierta («¿Qué canchas están disponibles ahora?») y confirma que no inventa la respuesta.
5. Prueba el enlace desde otro dispositivo y una ventana de incógnito.

> Aviso: proyecto académico independiente, no app oficial de la Alcaldía o del IDRD.
