> **PARA COMPARTIR EN INTERNET:** esta carpeta incluye `render.yaml` y la guía [GUIA_PUBLICAR_RENDER.md](GUIA_PUBLICAR_RENDER.md). En la web pública se desactivan importaciones y actualizaciones de cualquier visitante.

# ¿Qué dirIA Bogotá? — MVP funcional para presentación

**Asistente conversacional ciudadano para consultar parques y escenarios deportivos del IDRD.**

## Inicio sencillo (Windows)

1. Descomprime el ZIP.
2. Haz doble clic en `INICIAR_WINDOWS.bat` (necesitas **Python 3.9 o superior**).
3. Abre `http://localhost:8765` si no se abre automáticamente.
4. En **Datos y evidencia**, comprueba si se cargaron los conjuntos oficiales. Si no, descárgalos de los enlaces y usa **Importar CSV**.
5. Ve a **Pregúntale a Bogotá** y prueba preguntas. Para mostrar el mapa necesitarás un CSV con latitud y longitud.

No necesitas instalar bibliotecas de Python ni introducir una clave de Gemini para usar el sistema básico. La descarga inicial requiere conexión a Internet; los datos importados quedan guardados localmente y se reutilizan en siguientes ejecuciones.

### ¿Qué es real y qué es solo una muestra?

- Si se cargó algún **CSV**, todos los conteos y listas se calculan en tiempo real desde sus filas. El panel indica la fuente y fecha de corte según metadatos oficiales cuando está disponible.
- Si **no hay CSV**, el panel solo muestra las cifras parciales del pitch proporcionado por el equipo: 210 registros, 19 localidades, Suba 27, Kennedy 22, Engativá 18. Se marca claramente como **modo muestra**, sin presentar las cifras como verificadas.
- El nombre del proyecto, su alcance y la metodología están alineados con `Pitch_Que_dirIA_Bogota_v2.pdf` y la presentación del equipo.
- No se promete disponibilidad, reservas, tarifas, horarios ni detalle de canchas sin fuentes adicionales.
- La cobertura real es el **inventario cargado**, no el universo total de parques de Bogotá. Diferentes inventarios pueden tener recortes o duplicados.

### Fuentes oficiales y licencia

- [Parques IDRD](https://datosabiertos.bogota.gov.co/dataset/parques-idrd) — corte publicado: 2025-09-04.
- [Directorio de parques y escenarios IDRD](https://datosabiertos.bogota.gov.co/dataset/depor2023) — corte publicado: 2023-09-06.

**Datos del Instituto Distrital de Recreación y Deporte (IDRD), publicados en Datos Abiertos Bogotá bajo licencia CC BY 4.0.** Debe mantenerse atribución al autor institucional. Si importas datos propios, revisa sus permisos de uso.

El sistema intenta descargar automáticamente los CSV por API CKAN. Si el servidor del portal no permite la conexión, se puede subir el CSV descargado manualmente. Los archivos quedan en `data/` junto al proyecto.

### Modo IA real (opcional)

Por defecto el chatbot usa un **intérprete local de reglas**, sin presentarse falsamente como un modelo de IA generativa. Para habilitar Gemini como intérprete de preguntas, configura `GEMINI_API_KEY` en el equipo antes de ejecutar `server.py`. La clave queda en el servidor, nunca se envía al navegador. Ejemplo en PowerShell:

```powershell
$env:GEMINI_API_KEY="TU_CLAVE_PRIVADA"
python server.py
```

Si Gemini está activo, solo convierte la pregunta a un objeto estructurado (`intención`, `localidad`, `tipo`, `nombre`); **no genera respuestas numéricas**. Los filtros y cálculos se ejecutan en Python contra los archivos cargados. Si Gemini no responde, el sistema vuelve a las reglas locales. Se envía a Google únicamente la pregunta del usuario y el esquema de interpretación: no los archivos CSV.

### Protocolo de prueba del pitch

- 10 ciudadanos sin formación en datos.
- 5 preguntas comparadas con la consulta tradicional en el portal.
- 30 preguntas de control con respuestas verificadas previamente en el CSV.
- Medir tiempo de consulta, acierto y claridad percibida de 1 a 5.
- Registrar observaciones reales desde el panel **Evaluación del MVP** y exportar CSV. La evidencia se guarda en el navegador local, no en una base de datos remota.

### Guion de demostración (90 segundos)

1. **Inicio**: explicar problema de barrera técnica y mostrar cifras del inventario, aclarando su cobertura.
2. **Chat**: preguntar “¿Cuántos parques hay en Suba?” y mostrar fuente y auditoría.
3. **Comparar**: preguntar “Compara Suba y Kennedy”.
4. **Explorar**: usar filtros por localidad; mapa solo si hay coordenadas.
5. **Transparencia**: preguntar “¿Puedo reservar una cancha para hoy?”; mostrar rechazo por falta de datos en tiempo real.
6. **Evaluación**: mostrar cómo se mide desempeño con usuarios y exportación, sin inventar resultados.

### Publicación

Esta aplicación usa servidor Python, así que **GitHub Pages no es suficiente** para publicarla como web dinámica. Puedes desplegar `python server.py` en un host Python que permita puertos y variables de entorno; configura la variable `PORT` que te entregue el servicio y desactiva `OPEN_BROWSER=0`. Evita exponer públicamente la opción de subir archivos o de refrescar fuentes sin autenticación: en esta primera versión están diseñadas para una demo local.

### Arquitectura

- `server.py`: servidor HTTP, descarga/lectura CSV, normalización, respuestas trazables y uso opcional de Gemini.
- `web/`: interfaz HTML/CSS/JS (chat, explorador, auditoría, visualizaciones, mapa, evaluación).
- `data/`: CSV guardados localmente (vacía al distribuir, salvo archivo de marcador).
- `tests/`: pruebas de regresión del motor de consulta.

**Aviso:** prototipo académico independiente. No es una aplicación oficial ni está afiliada a la Alcaldía Mayor de Bogotá o al IDRD.
