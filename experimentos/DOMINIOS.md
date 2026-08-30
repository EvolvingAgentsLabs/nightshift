# Los seis dominios del README, medidos

El README nombra seis dominios donde *la arquitectura encajaría* —caza de amenazas,
diagnóstico diferencial, helpdesk, mantenimiento industrial, memoria corporativa y QA de
juegos— y los presenta con una advertencia adelante: **son hipótesis sobre dónde encaja
esto, no casos de estudio.** nightshift nunca corrió sobre otra cosa que su propio
repositorio.

Esto es el intento de correrla sobre los seis, con el diseño escrito **antes** de mirar
ningún resultado.

## Qué se mide, y qué no

**Se mide el consolidador y el retrieval** contra material de otro dominio: si `dream`
puede abstraer un mecanismo que no es de software, si la escena y el logograma pasan sus
gates cuando el dominio ya es físico, si lo que proyecta engancha con una tercera cara del
mismo mecanismo, y si la alternativa descartada sobrevive con su precondición.

**No se mide la captura**, y es la mitad de la máquina: no existe ningún harness que
capture a un analista de un SOC, a un clínico o a un operario. Las trayectorias de
[`casos_de_dominio.py`](casos_de_dominio.py) están escritas a mano. Un ensayo no es
evidencia (`CLAUDE.md`), y esto es un ensayo con la captura reemplazada por una persona.

**No se mide transferencia.** Todo —las trayectorias, los síntomas retenidos y los
ajenos— lo escribió la misma mano, así que el número es un **techo de autor**: lo mejor
que la cadena puede dar con material armado para ser separable. Vale el mismo asterisco
que el retenido de `5b3ff97f`, y por el mismo motivo: contra material de autor se registra
el número y no se emite veredicto.

Lo único que el pre-registro compra es el **orden**: los retenidos se commitean antes de
que ningún modelo consolide, así que no se pueden ajustar después para que enganchen.

## Los trece experimentos

Dos por dominio, más uno que sólo existe con los seis juntos.

### E1(d) — la cadena para adelante, en el dominio `d`

Las dos trayectorias del dominio se consolidan por el camino real —`dream.consolidate`,
modo `fisica`, el modelo que use el plugin— y de la candidata que salga se mide:

1. **¿pasó los gates?** `physical_scene`, `logogram` y el JSON entero pasan `dream.validate`
   sin reintentos infinitos, o el reporte dice qué rechazó y cuántas veces.
2. **¿proyectó?** `projected_signals` no vacío: síntomas que ninguna de las dos
   trayectorias muestra.
3. **¿engancha?** Los **dos síntomas retenidos** del dominio —terceras caras del mismo
   mecanismo, escritas antes— enganchan por el camino real (`retrieve.candidates` +
   `render`, con la compuerta de `context.classify_task` en el medio).
4. **¿discrimina?** Los **diez ajenos** —los retenidos de los otros cinco dominios— no
   enganchan.

**Sale en contra si** no hay candidata, o si `projected_signals` viene vacío, o si engancha
0 de 2 retenidos, o si engancha algún ajeno. Los números intermedios se publican como
número: acá no hay umbral, y fijar uno sería fijar una constante del experimento
(`bench/PREREG.md` §2, `CLAUDE.md` regla 4).

### E2(d) — la precondición sobrevive, en el dominio `d`

El camino del contraste (ADR-005, `dream.build_contrast_prompt`) sobre las otras dos
trayectorias del dominio: la alternativa que se descartó y la que la reemplazó. Se mide si
el contraste devuelve `old_valid_when` no vacío y si esa condición nombra el **régimen
real** que el pre-registro escribió como `precondicion_esperada` — el destino fijo que no
rota, el golpe local reciente, la ventana de uso corta, el fluido frío, el costo del dinero
bajo, la fecha de publicación encima.

**Sale en contra si** `validate_contrast` rechaza, o si `old_valid_when` viene vacío, o si
la condición es de las que el propio prompt llama «una forma elegante de decir nunca».
El parecido con la precondición esperada lo juzga una persona leyendo las dos: el script
imprime las dos al lado y **no** decide.

### E1-bis(d) — el fallback semántico, y NO estaba pre-registrado

Se agregó el 2026-08-30 **después de leer el resultado de E1**, y por eso lleva el
asterisco puesto en el nombre: no es parte del pre-registro y no se puede citar como si lo
fuera. Existe porque el proyecto ya tiene construida una salida para el modo de falla que
E1 encontró —el fallback semántico por embeddings (`embedding_command`, apagado por
default)— y medirla es más honesto que suponerla.

Es el mismo E1, con una sola clave de config cambiada.

```sh
python3 experimentos/17-los-seis-dominios-compiten.py --semantico
```

### E3 — los seis compiten en un solo store

Las seis candidatas montadas juntas, y los doce síntomas retenidos preguntando. Es la
pregunta que sólo existe con volumen: **¿cada síntoma encuentra el dominio del que salió,
o el store empieza a contestar cualquier cosa?** Es el `15` con seis dominios en lugar de
seis mecanismos de software.

**Sale en contra si** un síntoma engancha un dominio ajeno por encima del propio.

## Cómo se corre

```sh
python3 experimentos/16-los-suenios-de-los-seis-dominios.py   # genera: 6 llamadas al modelo
python3 experimentos/17-los-seis-dominios-compiten.py         # mide: gratis, lee lo generado
```

El primero llama al modelo y escribe los sueños en `salidas/dominios/`. El segundo no
llama a nadie: lee lo que quedó escrito y mide. Los dos corren sobre stores desechables en
un `HOME` temporal — **el store real no se toca, y esto no suma al conteo de ningún gate.**

## Lo que salió

En [`RESULTADOS-DOMINIOS.md`](RESULTADOS-DOMINIOS.md), con los sueños completos en
`salidas/dominios/`.
