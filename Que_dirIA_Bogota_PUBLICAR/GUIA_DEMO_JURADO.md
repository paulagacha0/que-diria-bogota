# Guion breve — ¿Qué dirIA Bogotá?

**Duración sugerida: 90 segundos de demostración.**

**Antes de presentar:** abre `INICIAR_WINDOWS.bat`, comprueba que la cabecera diga **Datos cargados** y que la sección **Datos y evidencia** muestre el CSV oficial. Si solo aparece **Cifras del pitch**, carga el archivo del IDRD desde la misma sección. No anuncies conteos como verificados si sigues en modo muestra.

### 1. El problema (15 segundos)
"Bogotá tiene datos abiertos, pero consultar un CSV y filtrar columnas no es algo que todo ciudadano sepa hacer. Nuestro objetivo es convertir la pregunta cotidiana en una respuesta sencilla y comprobable."

### 2. El chatbot (25 segundos)
Entra a **Pregúntale a Bogotá** y escribe:

- `¿Cuántos parques hay en Suba?`
- `Compara Suba y Kennedy`

Explica: "El motor interpreta mi pregunta, el código filtra las filas del archivo y muestra la respuesta junto con su origen. La IA no escribe cifras por su cuenta." Abre el panel derecho para mostrar la **auditoría** (intención, localidad, universo consultado).

### 3. Explorar (15 segundos)
Abre **Explorar parques**. Selecciona una localidad y filtra por nombre. Muestra que la respuesta del chat y los registros del explorador corresponden al mismo inventario. El mapa funciona **solo** si hay coordenadas reales en el archivo.

### 4. Seguridad y límites (15 segundos)
Regresa al chat y pregunta `¿Puedo reservar una cancha para hoy?`. El asistente no debe inventar disponibilidad: reconoce que el dato no está en su fuente.

### 5. Evaluación (20 segundos)
Muestra **Evaluación del MVP**. Explica que van a comparar cinco preguntas entre el portal tradicional y el asistente, con al menos diez usuarios. Se medirá tiempo, acierto y claridad. La sección también permite probar internamente hasta treinta preguntas y exportar los registros obtenidos. **Una prueba técnica no reemplaza una prueba real con ciudadanos.**

**Cierre:** "¿Qué dirIA Bogotá? no reemplaza los datos públicos: los hace conversables, comprensibles y verificables."

## Preguntas que probablemente hará el jurado

**¿De dónde salen las cifras?** De las filas de los CSV oficiales cargados, no de Gemini. En pantalla mostramos los enlaces y fechas de las fuentes. Si solo hay cifras del pitch, se indica expresamente.

**¿Qué hace la inteligencia artificial?** Con la clave Gemini configurada, interpreta la intención en lenguaje natural y devuelve filtros estructurados; Python ejecuta los conteos. Sin clave se usa un intérprete local de reglas, claramente identificado.

**¿Cuántos parques cubren?** Los registros que tenga el inventario cargado. El pitch anterior describía una muestra de 210, no la totalidad de Bogotá. Un CSV diferente puede tener otra cobertura.

**¿Por qué no usar únicamente un buscador?** Porque la hipótesis del proyecto es que una conversación natural reduce barreras técnicas. Se debe comprobar comparando tiempo, acierto y claridad con el portal tradicional.

**¿Cuáles son las limitaciones?** No permite reservas, precios, horarios, disponibilidad en vivo ni recomendaciones de seguridad no verificadas. Sin coordenadas no ubica parques en el mapa.

**¿Qué fue lo más importante al diseñarlo?** Separar las funciones: la IA entiende el lenguaje, el código calcula resultados y la evidencia permite verificar la respuesta.
