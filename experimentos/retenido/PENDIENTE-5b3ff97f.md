# Retenido pendiente — trayectoria `5b3ff97f`

**Para Matías.** Abajo hay cinco conjeturas que dream escribió sobre una sesión de
`debug_test_failure` del 2026-08-27. Ninguna se usó en ningún experimento todavía.

**Lo que hay que hacer:** debajo de cada una, escribir en una línea cómo describirías ese
síntoma **si te estuviera pasando a vos** — la frase que tipearías al abrir una sesión,
antes de saber la causa.

**La única regla:** no mirar la conjetura mientras escribís la línea. Leela, entendé qué
síntoma describe, mirá para otro lado, y escribila con tus palabras. Si al terminar
comparte media oración con la conjetura, está mal escrita y el número que salga no va a
valer nada.

Podés dejar en blanco las que no sepas cómo decir. Una paráfrasis forzada mide peor que una
ausencia.

---

### 1
> Los registros sellados antes del cambio se renderizan bien y sólo los nuevos rompen, lo
> que hace parecer el fallo intermitente.

tu frase:

### 2
> El chequeo de salud del store informa todo en verde porque cuenta registros y no campos
> dentro de cada registro.

tu frase:

### 3
> Una vista resumida lista el registro sin problema y sólo la vista de detalle explota, con
> el mismo dato de origen.

tu frase:

### 4
> Otro consumidor del mismo registro devuelve vacío en lugar de fallar, y el hueco pasa
> inadvertido en vez de romper.

tu frase:

### 5
> Exportar y reimportar el store fija la pérdida: el campo ya no puede reconstruirse porque
> el canal lateral no viaja con el registro.

tu frase:

---

Cuando esté lleno: `python3 experimentos/12-sensibilidad.py`
