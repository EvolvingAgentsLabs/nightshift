"""Casos de ideación de referencia — diseñados primero, y después usados como sintéticos.

**Qué es esto.** Seis mecanismos de fallo clásicos, cada uno con su ideación completa
escrita **a mano**: la escena física, el logograma, el patrón, las señales, las
precondiciones y las proyecciones. Cada caso pasa los gates reales del brazo `fisica`
(`dream.validate` con `modo="fisica"`) — un test lo fija — y después se montan **todos
juntos** en un store desechable para medir el techo a escala: con la ideación escrita como
la spec quiere, ¿cada síntoma encuentra su caso, y ningún ajeno engancha?

**Qué es cada caso, y por qué esos seis.** Mecanismos distintos a propósito — una copia que
no se refresca, una normalización de un solo lado, una carrera, una fuga de recursos, un
borde una unidad corto, y unidades que no se declaran. Si el enganche no puede separar seis
mecanismos *diseñados para ser separables*, el problema del piso que midió el `13` es peor
de lo que parecía; si puede, el techo existe y lo que falta está en la consolidación, que
es lo mismo que dijo el `08`.

**La regla de honestidad, dicha antes del primer caso.** Acá todo lo escribió la misma
mano: los casos, las señales Y las paráfrasis. Por eso esto mide un **techo** —lo mejor que
la cadena puede dar con material ideal— y nunca transferencia. La transferencia necesita un
conjunto retenido escrito por otra persona (`retenido/README.md`), y estos casos **no** lo
reemplazan: lo que sí hacen es separar "el instrumento no puede" de "el material no
alcanza", que es la distinción que el `08` compró para el brazo Mermaid.

**Los casos están calibrados a la regla vigente** (piso 2 + plegado de plural,
enmiendas 0.3.10/0.3.11): son material de referencia del instrumento, y una referencia
que no pasa la regla que ilustra no es una referencia. Cuando la regla cambie, se
recalibran — con la enmienda al lado, nunca en silencio.

**Y lo que estos casos NO son:** ejemplos few-shot para el prompt de consolidación.
Meterlos ahí cambiaría el brazo (PREREG §2) y ensuciaría cualquier medición futura: el
modelo estaría copiando los casos contra los que después se lo mide. Son material del
instrumento, no del tratamiento.
"""

# Cada caso: `slug` (nombre estable), `mecanismo` (la verdad, en términos de software —
# este campo es documentación y NO pasa por el gate de la escena), `physical_scene` y
# `logogram` (pasan `validate_scene` / `validate_logogram`), `pattern`, `signals`,
# `valid_when`, `projected_signals` (la superficie de búsqueda real), y `parafrasis` — cómo
# lo diría quien lo sufre, escrita por la misma mano que todo lo demás (techo, no
# transferencia).
CASOS = [
    {
        "slug": "pizarra-de-la-manana",
        "mecanismo": "Una copia derivada (un cache, una réplica, una vista materializada) "
                     "se consulta en lugar de la fuente y nada la refresca cuando la "
                     "fuente cambia.",
        "physical_scene": (
            "La panadería anota los precios en una libreta que vive en el mostrador, y "
            "cada mañana un empleado los copia a la pizarra de la vereda. Un mediodía la "
            "dueña corrige la libreta, pero la pizarra conserva la copia de la mañana, "
            "así que toda la tarde se cobra el precio viejo. Nadie protesta: cada cliente "
            "paga lo que ve escrito, y la caja cierra pareja con la pizarra. El faltante "
            "recién aparece a la noche, cuando la libreta y la caja se comparan, y para "
            "entonces ya no se sabe cuántos pasaron por la vereda."),
        "logogram": "pizarra de la mañana",
        "pattern": "Una copia derivada se consulta en lugar de la fuente y nada la "
                   "refresca cuando la fuente cambia: las lecturas siguen siendo "
                   "coherentes entre sí, así que ninguna etapa protesta, y la diferencia "
                   "sólo aparece al comparar contra la fuente, al final.",
        "signals": ["la pantalla muestra el valor viejo, no el que acabo de guardar",
                    "los cambios recién se ven después de reiniciar",
                    "dos lecturas del mismo dato dan distinto según por dónde se entra"],
        "valid_when": ["Hay una copia derivada de la fuente que se consulta en su lugar.",
                       "La copia se refresca por un proceso aparte, no en cada cambio."],
        "projected_signals": [
            "dos réplicas muestran valores distintos del mismo dato hasta que corre la "
            "sincronización",
            "un cambio urgente parece no surtir efecto y se aplica dos veces porque la "
            "primera no se vio"],
        "parafrasis": "guardé el cambio y la pantalla me sigue mostrando el valor viejo",
    },
    {
        "slug": "boleto-con-pliegue",
        "mecanismo": "El índice se construye con la clave normalizada y la consulta busca "
                     "con la clave cruda: dos claves idénticas a la vista no coinciden. "
                     "Es la causa compartida de la familia A del benchmark.",
        "physical_scene": (
            "En el guardarropas cada abrigo se cuelga con un talón que la empleada "
            "plancha y alisa antes de clavarlo en el tablero, para que todos queden "
            "parejos. El cliente se lleva la otra mitad tal como salió de la máquina, con "
            "un pliegue en el medio. Al volver, la empleada compara las dos mitades "
            "apoyándolas una sobre la otra: la suya está lisa, la del cliente conserva el "
            "pliegue, y por ese doblez las mitades no calzan aunque el número impreso sea "
            "el mismo. El abrigo está ahí, a la vista de los dos, y el talón dice que no."),
        "logogram": "boleto con pliegue",
        "pattern": "Una etapa normaliza la clave antes de guardarla y otra consulta con "
                   "la clave cruda: dos valores idénticos a la vista no coinciden porque "
                   "sólo uno pasó por la normalización, y el dato buscado existe pero no "
                   "se encuentra.",
        "signals": ["dos claves que se ven idénticas no coinciden",
                    "busco una clave que existe en el índice y no aparece",
                    "anda con unos datos y se rompe con otros que parecen iguales"],
        "valid_when": ["La clave pasa por una limpieza o normalización en un solo lado "
                       "del recorrido.",
                       "La comparación es exacta, sin tolerancia."],
        "projected_signals": [
            "al importar los mismos datos dos veces aparecen duplicados que se ven "
            "iguales",
            "el conteo de valores únicos da más que las filas que se ven en pantalla"],
        "parafrasis": "busco una clave que está en el índice y me dice que no existe",
    },
    {
        "slug": "renglon-pisado",
        "mecanismo": "Dos escritores hacen leer-decidir-escribir sobre estado compartido "
                     "sin reserva: bajo concurrencia la segunda escritura pisa la primera "
                     "sin dejar rastro.",
        "physical_scene": (
            "Dos vendedores comparten un solo cuaderno de ventas. Cada uno mira cuál es "
            "el último renglón escrito, se lleva el número en la cabeza a su escritorio "
            "para redactar la venta con calma, y vuelve a escribirla en el renglón que "
            "recuerda. Cuando los dos van y vienen al mismo tiempo, ambos memorizan el "
            "mismo renglón vacío: el segundo escribe encima del primero y la venta de "
            "abajo desaparece sin dejar ni una tachadura. El cuaderno queda prolijo, la "
            "suma da uno menos, y probarlo despacio no lo muestra, porque despacio nunca "
            "se cruzan."),
        "logogram": "renglón pisado",
        "pattern": "Dos actores leen un estado compartido, deciden con lo leído y "
                   "escriben después, sin reservar el lugar: cuando se superponen, la "
                   "segunda escritura pisa la primera sin dejar rastro, y el fallo sólo "
                   "ocurre bajo concurrencia real.",
        "signals": ["cada tanto se pierde una escritura sin dejar rastro",
                    "el total da de menos sólo cuando hay mucha actividad",
                    "no lo puedo reproducir cuando lo pruebo de a uno"],
        "valid_when": ["Dos o más actores escriben sobre el mismo estado sin reserva ni "
                       "traba.",
                       "Entre leer y escribir pasa un tiempo en el que otro puede "
                       "escribir."],
        "projected_signals": [
            "bajo carga aparecen dos registros con el mismo identificador",
            "una prueba automatizada se cae una de cada tantas corridas y al repetirla "
            "pasa"],
        "parafrasis": "de vez en cuando se pierde un registro y no encuentro rastro de "
                      "qué pasó",
    },
    {
        "slug": "morsas-sin-devolver",
        "mecanismo": "Cada operación toma un recurso de un pool acotado y no lo libera: "
                     "el sistema se degrada sin fallar hasta que el pool se agota.",
        "physical_scene": (
            "En el taller, cada trabajo toma una morsa del estante, la usa y despacha la "
            "pieza terminada, pero la morsa queda en la mesada: devolverla no es parte de "
            "terminar. Cada día el estante amanece con menos morsas y las mesadas más "
            "llenas, y el taller sigue produciendo igual, apenas más incómodo. Una mañana "
            "un trabajo espera porque no queda ninguna morsa libre, y ya no hay forma de "
            "saber qué mesada acumuló cuáles: el que las dejó terminó hace semanas y la "
            "pieza ya se fue."),
        "logogram": "morsas sin devolver",
        "pattern": "Cada operación toma un recurso de un fondo compartido y acotado y no "
                   "lo libera al terminar: el sistema se degrada de a poco sin fallar "
                   "nunca, hasta que el fondo se agota y una operación nueva queda "
                   "esperando algo que nadie va a soltar.",
        "signals": ["cada vez más lento cuanto más tiempo lleva corriendo",
                    "después de reiniciar anda bien un rato y vuelve a degradarse",
                    "de golpe no se pueden abrir conexiones ni recursos nuevos"],
        "valid_when": ["Las operaciones toman recursos de un fondo acotado.",
                       "Liberar el recurso no es condición para que la operación se dé "
                       "por terminada."],
        "projected_signals": [
            "el consumo de memoria crece de forma sostenida sin picos que lo expliquen",
            "el fallo aparece siempre a la misma cantidad de horas de uso"],
        "parafrasis": "el proceso anda cada vez más lento y si lo reinicio se arregla "
                      "por un rato",
    },
    {
        "slug": "cerca-sin-ultimo-poste",
        "mecanismo": "Off-by-one en el borde: el recorrido cuenta intervalos donde debía "
                     "contar extremos, y el último elemento queda sistemáticamente "
                     "afuera.",
        "physical_scene": (
            "La cuadrilla planta un poste cada diez pasos y cuenta tramos de alambre, no "
            "postes. El plano paga diez tramos, así que plantan diez postes, y el último "
            "tramo queda colgando en el aire, sin poste donde atarse. Desde el camino la "
            "cerca se ve entera, porque el ojo sigue el alambre y el hueco queda en la "
            "punta, lejos. Recién se nota el día que un animal rodea el final y entra "
            "caminando, y el capataz cuenta de nuevo: diez tramos necesitan once postes, "
            "y la cuenta siempre estuvo una unidad corta, justo en el borde."),
        "logogram": "cerca sin último poste",
        "pattern": "Un recorrido cuenta intervalos donde debía contar extremos, o al "
                   "revés: todo el interior sale bien y el borde queda sistemáticamente "
                   "afuera, una unidad corto, y el hueco sólo se ve el día que alguien "
                   "usa justo el extremo.",
        "signals": ["el último elemento nunca aparece en el resultado",
                    "la cuenta da exactamente uno menos de lo esperado",
                    "anda con todos los casos menos con el borde"],
        "valid_when": ["Hay un recorrido con un rango que tiene extremos.",
                       "El caso del borde no tiene una prueba propia."],
        "projected_signals": [
            "el primer elemento se procesa dos veces cuando el recorrido se reanuda",
            "con una colección de un solo elemento no se procesa ninguno"],
        "parafrasis": "el último registro de la lista nunca se procesa y los demás sí",
    },
    {
        "slug": "varas-contra-metros",
        "mecanismo": "Dos componentes intercambian una magnitud sin declarar la unidad o "
                     "convención: cada uno es coherente consigo mismo y el desvío sólo "
                     "aparece al juntar los resultados.",
        "physical_scene": (
            "Dos cuadrillas levantan el mismo puente desde las dos orillas, cada una con "
            "su propio plano. Los planos dicen el mismo número, pero una regla está en "
            "varas y la otra en metros. Cada mitad avanza y se verifica contra su propia "
            "regla, y las dos dan perfecto todos los días. Las mitades se encuentran en "
            "el medio del río y no se tocan: quedan separadas por una diferencia que es "
            "siempre la misma proporción del total, chica en un puente corto, enorme en "
            "uno largo. Ninguna medición local la muestra, porque cada regla es coherente "
            "consigo misma."),
        "logogram": "varas contra metros",
        "pattern": "Dos partes intercambian una magnitud asumiendo cada una su propia "
                   "unidad o convención: cada parte es internamente coherente y todas "
                   "sus pruebas locales pasan, y el desvío sólo aparece al juntar los "
                   "resultados, proporcional al tamaño de lo procesado.",
        "signals": ["cada parte da bien por separado y el total da mal",
                    "la diferencia es siempre la misma proporción, no un valor fijo",
                    "el desvío crece con el tamaño de lo que se procesa"],
        "valid_when": ["Dos componentes intercambian una magnitud sin declarar la "
                       "unidad.",
                       "Cada componente se prueba contra sus propios datos, no contra "
                       "los del otro."],
        "projected_signals": [
            "una fecha aparece corrida una cantidad fija de horas según quién la "
            "muestre",
            "el mismo monto difiere en un factor constante entre dos reportes"],
        "parafrasis": "los subtotales dan bien pero cuando junto las dos partes el total "
                      "no cierra",
    },
]

# Control negativo: prompts de otros dominios. Cualquier enganche acá invalida el techo
# del caso que lo produzca — no hay "falso positivo aceptable" en un corpus diseñado.
AJENOS = [
    "el certificado ssl del dominio vencio y el deploy no arranca",
    "quiero agregar paginacion a la tabla de usuarios",
    "hay que traducir los textos de la interfaz al portugues",
    "quiero cambiar la tipografia y el color del encabezado",
]


def medir_a_escala():
    """Monta los seis casos en UN solo store desechable y mide la matriz completa.

    Es la diferencia con `camino_real.medir`, que monta una candidata por store: acá la
    pregunta es de discriminación —¿la paráfrasis encuentra *su* caso entre seis?— y esa
    pregunta sólo existe con los seis compitiendo, que es como los encontraría una sesión
    real. El `13` midió esto sobre el store real y no controlado; esto lo mide sobre
    material diseñado, que es el techo.

    Devuelve `{"detalle": [...], "ajenos": [...]}`. Cada fila del detalle dice: si el
    prompt pasó la compuerta del clasificador, qué casos enganchó, si el propio quedó
    entre los elegidos (`llega`), y si un caso ajeno enganchó más alto que el propio
    (`cruzada`). Nunca toca el store real.
    """
    import sys
    from pathlib import Path
    raiz = Path(__file__).resolve().parent
    if str(raiz) not in sys.path:
        sys.path.insert(0, str(raiz))
    import camino_real

    with camino_real.StoreDesechable() as d:
        from nightshift import config, retrieve
        ids = {}
        for caso in CASOS:
            tid = camino_real.montar(
                d, {"pattern": caso["pattern"], "signals": caso["signals"],
                    "valid_when": caso["valid_when"]},
                caso["projected_signals"],
                physical_scene=caso["physical_scene"], logogram=caso["logogram"])
            ids[tid] = caso["slug"]
        cfg = config.load()

        def rankear(prompt):
            pasa, tipo = camino_real.compuerta(prompt)
            tipo_consulta = tipo if pasa else camino_real.TASK
            scored = retrieve.candidates(d.conn, task_type=tipo_consulta,
                                         repo_fingerprint=camino_real.REPO,
                                         cfg=cfg, prompt=prompt)
            _, elegidas = retrieve.render(d.conn, scored,
                                          max_injected=cfg.get("max_injected", 3),
                                          native_memory=None, task_type=tipo_consulta,
                                          repo_fingerprint=camino_real.REPO)
            # `render` devuelve las elegidas como `(score, reasons, row)`, igual que
            # `candidates`: es la misma tupla que consume el hook.
            elegidos = {row["id"] for _, _, row in elegidas}
            enganchan = [(ids[row["id"]], reasons) for _, reasons, row in scored
                         if retrieve.MOTIVOS_DE_ENGANCHE
                         & set((reasons or "").split(","))]
            return pasa, tipo, scored, elegidos, enganchan

        detalle = []
        for caso in CASOS:
            pasa, tipo, scored, elegidos, enganchan = rankear(caso["parafrasis"])
            propio = next(t for t, slug in ids.items() if slug == caso["slug"])
            slugs_que_enganchan = [s for s, _ in enganchan]
            propia_engancha = caso["slug"] in slugs_que_enganchan
            elegida = propio in elegidos and propia_engancha
            cruzadas = [s for s in slugs_que_enganchan if s != caso["slug"]]
            # ¿Un caso ajeno quedó por encima del propio entre los que enganchan?
            arriba = []
            for _, reasons, row in scored:
                if row["id"] == propio:
                    break
                if bool(retrieve.MOTIVOS_DE_ENGANCHE & set((reasons or "").split(","))):
                    arriba.append(ids[row["id"]])
            detalle.append({"slug": caso["slug"], "parafrasis": caso["parafrasis"],
                            "compuerta": pasa, "clasifica": tipo,
                            "propia_engancha": propia_engancha,
                            "elegida": elegida, "llega": pasa and elegida,
                            "cruzadas": cruzadas, "arriba_del_propio": arriba,
                            "motivos": dict(enganchan)})

        ajenos = []
        for prompt in AJENOS:
            pasa, tipo, scored, elegidos, enganchan = rankear(prompt)
            ajenos.append({"prompt": prompt, "compuerta": pasa, "clasifica": tipo,
                           "engancha": [s for s, _ in enganchan]})
    return {"detalle": detalle, "ajenos": ajenos}
