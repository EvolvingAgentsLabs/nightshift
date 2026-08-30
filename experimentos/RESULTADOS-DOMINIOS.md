# Los seis dominios — resultados

Corrido el **2026-08-30**. Diseño y material en [`DOMINIOS.md`](DOMINIOS.md) y
[`casos_de_dominio.py`](casos_de_dominio.py), commiteados **antes** de que el modelo
consolidara nada. Los sueños completos están en `salidas/dominios/*.json` y la salida
entera del marcador en `salidas/dominios/marcador.txt`.

Modelo: `claude -p --output-format json`, modo de ideación `fisica`. Seis consolidaciones
más seis contrastes: **3,51 USD**, 410.567 tokens de entrada y 33.979 de salida.

**El asterisco, arriba y no al pie.** Las trayectorias, los síntomas retenidos y los
ajenos los escribió la misma mano. Esto es un **techo de autor** —qué puede dar la cadena
con material armado para ser separable— y **no** es transferencia, ni sensibilidad, ni
evidencia de que la memoria sirva en un SOC, en una guardia o en una planta. Además mide
media máquina: no existe harness que capture a un analista o a un clínico, así que la
captura la reemplazó una persona.

---

## El resumen, en una línea

**Soñar fuera del software funciona; encontrar lo soñado, no.** Los seis dominios
produjeron candidata a la primera, sin un solo rechazo de gate, con escena, logograma,
precondiciones y proyecciones. Y después el retrieval enganchó **2 de 12** síntomas
retenidos, con **3 falsos positivos**. La mitad que el proyecto considera resuelta —el
retrieval léxico— es la que se cae, y se cae por un motivo que se puede señalar con el
dedo.

---

## E1 — la cadena para adelante: 2 de 12

| dominio | proyecciones | engancha | llega | ajenos (de 10) |
|---|---|---|---|---|
| caza-de-amenazas | 5 | 1 de 2 | 1 de 2 | 0 |
| diagnostico-diferencial | 5 | 1 de 2 | 1 de 2 | 2 |
| helpdesk | 5 | 0 de 2 | 0 de 2 | 1 |
| mantenimiento-industrial | 5 | 0 de 2 | 0 de 2 | 0 |
| memoria-corporativa | 5 | 0 de 2 | 0 de 2 | 0 |
| qa-de-juego | 5 | 0 de 2 | 0 de 2 | 0 |
| **total** | **30** | **2 de 12** | **2 de 12** | **3 de 60** |

**Los gates no rechazaron nada.** Cero reintentos en seis dominios: `validate`,
`validate_scene` y `validate_logogram` —escritos para que un modelo no conteste con la
explicación de siempre disfrazada de imagen— aceptaron a la primera una acequia de
piedra, un guardarropas y una balanza. `VOCABULARIO_DEL_CODIGO` tampoco molestó, que era
el rechazo falso que este experimento esperaba encontrar en helpdesk y en el SOC.

**Y las proyecciones son el mejor material que produjo el proyecto hasta ahora.** El
dominio industrial proyectó *"reforzada la pieza que cedía, ahora cede otra distinta y
parece un problema nuevo sin relación"* y *"probada fuera del recorrido, la pieza
sospechada siempre da bien y nadie entiende por qué falla montada"*. Ninguna de las dos
está en las trayectorias. Eso es exactamente la idea 2 del pivot, y salió sola.

### Por qué falla el enganche, con el número al lado

Las diez que no engancharon comparten **una sola palabra de contenido o ninguna** con la
superficie de búsqueda, que tiene el piso en 2:

| síntoma retenido | mejor frase de la memoria | comparten |
|---|---|---|
| *el motor del transporte se recalienta a la tarde y a la mañana no, ya le cambiamos el rodamiento dos veces* | *cambié la pieza por una nueva y limpia y el aviso volvió a las pocas horas* | **0** |
| *el sello nuevo de la bomba duró tres semanas igual que el anterior* | *puse la pieza reforzada y duró casi lo mismo, con el mismo dibujo de desgaste* | 1 (`duro`) |
| *si abro el mapa justo cuando me empuja el enemigo me quedo pegado en el aire* | *el efecto queda pegado para siempre después de una acción que dura un instante* | 1 (`pegado`) |
| *casi todo el equipo de la contraparte está contratado como proveedores independientes* | *el grueso de quienes hacen el trabajo no está en relación de dependencia y factura como proveedor* | 1 (`proveedor`) |

Las frases de la izquierda y las de la derecha **hablan de lo mismo**. No comparten
palabras. El enganche es léxico y la coincidencia léxica entre dos personas que describen
el mismo mecanismo con vocabularios distintos es, medida acá, de cero a uno.

Y los tres falsos positivos cierran la pinza: los tres enganchan con **exactamente dos**
palabras, y las dos son las menos informativas de la oración.

| prompt ajeno | memoria que enganchó | las dos palabras |
|---|---|---|
| *el uso de disco del archivo compartido sube todas las noches…* | diagnóstico diferencial | `hora`, `vuelve` |
| *desde ayer la pantalla de consulta tarda un minuto…* | diagnóstico diferencial | `nada`, `tarda` |
| *el uso de disco del archivo compartido sube todas las noches…* | helpdesk | `compartido`, `siempre` |

En el borde del piso, lo que decide el enganche no es el mecanismo: es `hora`, `nada`,
`siempre`. El piso en 2 **ni deja pasar las verdaderas ni frena las falsas**, y esto es la
misma degradación que midió el [`13`](13-cuanto-discrimina-el-enganche.py) sobre el store
real, reproducida sobre material diseñado para ser separable.

Las dos que sí engancharon (`cuenta` + `administrador` en el SOC, `estudio` + `normal` +
`volvió` en medicina) engancharon porque **quien escribió el retenido usó los mismos
sustantivos que el modelo**. Es coincidencia de vocabulario del autor, y no cuenta como
transferencia ni siquiera dentro del techo.

## E1-bis — el fallback semántico, que no estaba pre-registrado

**Se agregó después de ver el resultado de E1, y hay que decirlo así.** El proyecto ya
tiene construida una salida para este modo de falla —el fallback semántico por embeddings,
`embedding_command`, apagado por default— y medirla es más honesto que suponerla. No es
parte del pre-registro y no se puede leer como si lo fuera.

Con `tools/embed-ollama.sh` (embeddinggemma local) enchufado, sobre el mismo material:

| | engancha | ajenos (de 60) |
|---|---|---|
| léxico (default) | 2 de 12 | 3 |
| **+ semántico** | **11 de 12** | **20** |

El coseno recupera casi todo lo que las palabras perdían **y engancha uno de cada tres
prompts ajenos**. Con el fallback puesto, el dominio industrial engancha sus dos síntomas
y también siete de los diez ajenos, incluida *"la paciente dice que le arde entre los
omóplatos"*. Una memoria que contesta a un tercio de lo que le preguntan no está
enganchando: está presente.

Y estaba anticipado, en el propio `config.py`: la nota de calibración del 2026-08-29 dice
que el coseno separa sinónimos de registro parecido y **no** separa síntoma contra
mecanismo abstracto (0,24–0,28, por debajo de los ajenos, 0,33). Este experimento es esa
nota, con seis dominios en vez de cuatro pares.

## E2 — la precondición sobrevive: 6 de 6 contrastes, y son buenos

El camino del contraste (ADR-005) devolvió `old_valid_when` en los seis, con dos o tres
condiciones cada uno, y ninguna fue rechazada por `validate_contrast`. Tres muestras, al
lado de lo que el pre-registro esperaba:

- **Memoria corporativa.** Esperado: *licenciar era lo correcto cuando el costo del dinero
  está por debajo de cierto umbral*. Devuelto: *"cuando el costo del dinero es bajo frente
  al flujo comprometido, el valor presente de los pagos periódicos queda por debajo del
  precio de adquisición y la opción de acceso sin adquirir vuelve a ganar"*. Es la misma
  condición, con el mecanismo financiero explicado.
- **Mantenimiento industrial.** Esperado: *bajar la presión servía cuando parar la línea
  cuesta más que producir despacio*. Devuelto: *"cuando el ritmo realmente exigido es menor
  o igual al que la línea entrega ya degradada: ahí bajar la magnitud no cuesta rendimiento
  y el paliativo es gratis"*. **No es la condición que estaba escrita, y es mejor** — nombra
  el régimen exacto en el que el paliativo deja de costar.
- **Diagnóstico diferencial.** Esperado: *estudiar el sitio doloroso servía con antecedente
  de golpe local*. Devuelto: *"cuando las maniobras baratas sí reproducen el síntoma
  moviendo la zona… y sólo falta caracterizar el tejido para elegir tratamiento"*. Otra vez
  el mismo régimen, expresado por la maniobra que lo detecta en lugar de por el
  antecedente.

Ninguna de las condiciones cae en lo que el propio prompt llama *"una forma elegante de
decir nunca"*. **La capacidad B funciona fuera del software**, y es la parte de la máquina
que salió mejor parada.

La comparación de arriba la hizo una persona leyendo las dos columnas. El script imprime
las dos y no puntúa: puntuar el parecido sería inventar un umbral, y los umbrales los fija
Matías (`CLAUDE.md` regla 4).

## E3 — los seis compitiendo en un store

Mismos dos enganches propios de E1 (2 de 12), dos síntomas que además enganchan un dominio
ajeno, y —el número que importa leer bien— **el propio queda entre los inyectados 8 de 12
veces**. Esas ocho no son enganches: con seis filas en el store, `same_repo` inyecta
igual. Es la distinción que `camino_real.py` obliga a mantener: *rankear* no es *enganchar*,
y una memoria inyectada por vecindad y no por síntoma es ruido con formato de ayuda.

---

## Qué se aprendió, y qué habría que hacer con eso

Cinco cosas, en orden de cuánto cambian la lectura del README.

1. **El consolidador no es de software.** Nada del prompt, de los gates ni de la ideación
   física necesitó tocarse para abstraer una acequia, un guardarropas o una balanza. La
   afirmación del README —*"el núcleo de nightshift no es sobre código"*— es la única de
   la página que este experimento **sostiene con material propio**, y sostenerla costó
   3,51 USD.
2. **El retrieval sí es de software, y nadie lo había escrito así.** No por su código,
   sino por su supuesto: que el que pregunta y el que consolidó comparten vocabulario.
   Dentro de un repo eso es casi cierto —el que escribe el prompt y el que escribió el
   error usan las mismas palabras— y fuera es falso. El piso en 2 no discrimina; en el
   borde decide con `hora`, `nada` y `siempre`.
3. **La salida que el proyecto ya construyó no alcanza, y está medido.** El fallback
   semántico convierte una memoria muda en una indiscriminada: 11 de 12 a costa de 20
   ajenos de 60. Encenderlo por default sería cambiar un modo de falla silencioso por uno
   ruidoso.
4. **La capacidad B es la más portable de las cinco.** El contraste devolvió precondiciones
   accionables en los seis dominios, y en dos casos mejores que las escritas a mano. Es la
   pieza que menos depende del vocabulario, porque compara dos trayectorias entre sí en
   lugar de comparar un texto con un prompt.
5. **Lo que este experimento no puede tocar sigue siendo la mitad de la máquina.** No hay
   captura fuera de un agente de código, y sin captura los cinco dominios de arriba son un
   ejercicio con trayectorias escritas a mano. Que el consolidador funcione no acerca a
   nightshift a un SOC: acerca a un SOC **que ya tuviera su cadena de ejecución
   capturada**, que es un problema entero y ajeno a este repositorio.

Lo que **no** se aprendió, y conviene decirlo con la misma claridad: que la memoria sirva.
Sigue sin medirse, sigue sin `verify`, y nada de lo de acá llega a `procedure`. Doce
síntomas escritos por la misma persona que escribió las trayectorias no son un
experimento sobre la utilidad de nada.

## El plugin, usado sobre la sesión que produjo esto

La sesión que escribió estos experimentos fue capturada por el plugin —`5f35bfac`, tipo
`docs`, 62 pasos— y recibió **seis memorias inyectadas**, tres en `SessionStart` y tres en
el primer prompt. Los motivos de las seis, tal como los registró el store:

```
16a5f7ff  rank 1  score 2.07  same_repo,has_decisive_step,tests_passed
a5d95061  rank 2  score 2.04  same_repo,has_decisive_step,tests_passed
d529a430  rank 3  score 2.04  same_repo,has_decisive_step,tests_passed
057531f2  rank 1  score 2.63  same_task_type,same_repo,tests_passed
242e105a  rank 2  score 2.04  same_repo,has_decisive_step,tests_passed
8678f39f  rank 3  score 2.03  same_repo,has_decisive_step,tests_passed
```

**Ninguno de los seis motivos es un enganche.** No hay `signal_match`, ni
`projected_match`, ni `logogram_match`, ni `failure_match`: las seis llegaron por vecindad
—mismo repo, mismo tipo de tarea, la trayectoria terminó en verde— y ninguna porque
hablara del problema que la sesión tenía enfrente. Es el mismo resultado que E1 midió
sobre material sintético, ocurriendo en vivo sobre el store real, el mismo día.

**Y no es que el enganche no ocurra nunca sobre el store real**, que sería la lectura de
más: la sesión anterior, del 2026-08-30 a las 00:02, enganchó con score 5.25 y tres
motivos de enganche —`signal_match,precondition_match,projected_match`—. La diferencia
entre esa sesión y ésta es de qué hablaban: aquélla trabajaba sobre el mismo material del
que salió la memoria, con las mismas palabras. Es el mismo eje que separa E1 de E1-bis, y
la conclusión no es "el enganche está roto" sino **"el enganche depende de compartir
vocabulario"**, que es una afirmación más chica y más incómoda.

Y hay una coincidencia que vale registrar con su asterisco puesto. La memoria de rango 1,
`16a5f7ff`, dice: *"las sondas de inspección se escriben contra una forma recordada del
objeto en vez de contra el objeto vivo"*, logograma **plano viejo, pieza real**. En esta
sesión eso pasó: el primer script de diagnóstico armó la superficie de búsqueda con lo que
el prompt de consolidación **dice** que es la superficie —señales, precondiciones,
proyecciones, logograma— y no con lo que `retrieve.candidates` lee de verdad, que además
incluye `decisive_signal`. El error se encontró porque dos números no coincidieron, no
porque alguien hubiera leído la memoria y actuado sobre ella.

Así que la lectura correcta es la que el propio `status` imprime al lado del eco: **es
correlación, no causa.** La memoria que describía el error estaba en la ventana, llegó por
`same_repo`, y el error se cometió igual. Que ese sea el resumen honesto del dogfooding es
exactamente por qué `verify` —y no otra cosa— es lo que falta.

Las consecuencias que no se implementan acá —porque no están en el plan— quedaron
anotadas en [`LATER.md`](../LATER.md).
