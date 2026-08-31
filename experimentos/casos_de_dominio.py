"""Los seis dominios del README, como cadenas de ejecución — el PRE-REGISTRO.

**Qué es esto.** El README afirma que la arquitectura de nightshift está hecha para seis
dominios que no son programar: caza de amenazas, diagnóstico diferencial, helpdesk,
mantenimiento industrial, memoria corporativa y QA de juegos. Lo dice con una advertencia
adelante —son hipótesis sobre dónde encaja, no casos de estudio— y con un motivo: la
máquina nunca corrió sobre otra cosa que su propio repositorio.

Este archivo es el material para correrla sobre los seis. Cada dominio trae:

- **dos trayectorias del mismo mecanismo con dos caras distintas** — lo que `dream`
  consolida;
- **dos trayectorias más**, la alternativa que se descartó y la que la reemplazó — lo que
  consume el contraste (ADR-005), que es por donde pasa la capacidad B;
- **dos síntomas retenidos**, terceras caras del mismo mecanismo que **no aparecen en
  ninguna trayectoria**, y con las que se mide si la memoria engancha;
- **la precondición esperada** de la alternativa descartada, escrita acá para poder
  comparar contra lo que el modelo devuelva.

**La regla de honestidad, dicha antes del primer caso, y es la misma del `15`.** Todo esto
lo escribió la misma mano: las trayectorias, los síntomas retenidos y los ajenos. Por eso
lo que se mide es un **techo de autor** —lo mejor que la cadena puede dar con material
armado para ser separable— y **nunca transferencia**, ni sensibilidad, ni evidencia de que
la memoria sirva en ninguno de los seis dominios. Vale el mismo asterisco que el retenido
de `5b3ff97f`: contra material de autor se registra el número y no se emite veredicto.

**Lo único que compra este pre-registro es el orden.** Los retenidos y los ajenos se
escriben y se commitean **antes** de que ningún modelo consolide nada, así que no se
pueden ajustar después para que enganchen. Eso no lo vuelve transferencia; lo vuelve
auditable, que es lo que git puede sostener (`11-la-profecia-tiene-notario.py`).

**Y una diferencia que conviene no perder de vista.** Estas trayectorias son sintéticas: en
un dominio de verdad las escribiría la captura, no una persona, y no existe hoy ningún
harness que capture a un analista de un SOC o a un médico. Un ensayo no es evidencia
(`CLAUDE.md`): esto mide **el consolidador y el retrieval**, con la captura reemplazada por
material escrito a mano.

El caso 2 —diagnóstico diferencial— lleva encima el mismo recorte que el README: nada de
lo que salga de acá es apto para acercarse a un paciente, y el motivo no es prudencia sino
que `verify` no existe y nada llega a `procedure`.
"""

# Cada dominio: `slug`, `dominio` (el título del README), `mecanismo` (la verdad, en
# prosa; es documentación y no pasa por ningún gate), `task_type` (la clave con la que
# agrupa `dream.groups`), `trayectorias` (las dos caras que se consolidan), `alternativa`
# (la descartada y la que la reemplazó, para el contraste), `retenidos` (las terceras
# caras, que NO aparecen arriba) y `precondicion_esperada` (documentación: contra qué se
# compara el `old_valid_when` que devuelva el modelo).
#
# Cada paso: `kind` del vocabulario del esquema, `tool` normalizado, `tool_native` como lo
# diría el dominio, `texto` (que va a `result_summary` o a `error_message`), y las banderas
# `decisive` / `contradicted`. El texto se corta en 160 caracteres antes de llegar al
# modelo (`dream.MAX_CHARS_POR_PASO`) y entran seis pasos por trayectoria
# (`dream.MAX_STEPS_EN_PROMPT`), así que cada trayectoria trae seis pasos con contenido y
# ninguno más largo que eso.

CASOS = [
    # ------------------------------------------------------------------ 1 · SOC
    {
        "slug": "caza-de-amenazas",
        "dominio": "Ciberseguridad: caza de amenazas y respuesta a incidentes",
        "task_type": "caza_de_amenazas",
        "mecanismo": (
            "El transporte del atacante es un canal legítimo y programado, con permiso "
            "propio. Cada control ve un actor autorizado y ninguno protesta; la anomalía "
            "no existe en el eje del permiso, existe en el eje del horario. Buscar el "
            "binario malicioso vuelve limpio todas las veces."),
        "trayectorias": [
            {"outcome": "tests_passed", "pasos": [
                {"kind": "hypothesis", "tool": "other", "tool_native": "nota_del_analista",
                 "texto": "Se arrancó suponiendo que la estación tenía un binario "
                          "malicioso instalado por un adjunto de correo."},
                {"kind": "tool_use", "tool": "other", "tool_native": "barrido_antivirus",
                 "texto": "El barrido completo de la estación volvió limpio: cero "
                          "detecciones en los tres motores, incluida la memoria."},
                {"kind": "observation", "tool": "other", "tool_native": "consulta_siem",
                 "texto": "El volumen de salida del segmento de administración triplica "
                          "su promedio entre las dos y las cinco de la mañana; de día "
                          "está en el promedio."},
                {"kind": "tool_use", "tool": "other", "tool_native": "consulta_proxy",
                 "texto": "Cuarenta y una transferencias de doscientos megas, todas "
                          "iniciadas por la cuenta del sistema de respaldo, ninguna con "
                          "alerta asociada."},
                {"kind": "observation", "tool": "other", "tool_native": "auditoria_de_tareas",
                 "decisive": True,
                 "texto": "La tarea programada del respaldo fue modificada hace nueve "
                          "días y agrega un destino más. Corre con el permiso del "
                          "respaldo, y por eso ninguna regla la marcó."},
                {"kind": "correction", "tool": "other", "tool_native": "cambio_aplicado",
                 "texto": "Se revirtió la tarea programada y se rotaron las credenciales "
                          "de esa cuenta. El volumen nocturno volvió al promedio en la "
                          "misma noche."},
            ]},
            {"outcome": "tests_passed", "pasos": [
                {"kind": "hypothesis", "tool": "other", "tool_native": "nota_del_analista",
                 "texto": "La primera lectura fue que los reclamos de lentitud de la "
                          "semana del feriado venían de la migración del correo."},
                {"kind": "tool_use", "tool": "other", "tool_native": "inventario_de_agentes",
                 "texto": "La herramienta de administración remota está en trescientos "
                          "equipos, firmada por el fabricante y sin ninguna alerta "
                          "asociada en el año."},
                {"kind": "observation", "tool": "other", "tool_native": "consulta_siem",
                 "texto": "Las sesiones de esa herramienta se concentran en la semana del "
                          "feriado, justo cuando el equipo de soporte no trabajaba."},
                {"kind": "tool_failure", "tool": "other", "tool_native": "revision_de_reglas",
                 "texto": "Ninguna regla de detección se disparó: la herramienta está en "
                          "la lista de permitidas y el permiso alcanza para copiar "
                          "carpetas enteras."},
                {"kind": "observation", "tool": "other", "tool_native": "revision_de_cuentas",
                 "decisive": True,
                 "texto": "El operador de esas sesiones es una cuenta de mantenimiento "
                          "que ningún administrador reclama, activa solamente cuando la "
                          "oficina está vacía."},
                {"kind": "correction", "tool": "other", "tool_native": "cambio_aplicado",
                 "texto": "Se deshabilitó la cuenta de mantenimiento y el permiso de la "
                          "herramienta quedó atado a la franja horaria de trabajo."},
            ]},
        ],
        "alternativa": {
            "descartada": {"outcome": "user_corrected", "pasos": [
                {"kind": "hypothesis", "tool": "other", "tool_native": "nota_del_analista",
                 "texto": "Se propuso cortar el incidente bloqueando la dirección de "
                          "destino en el cortafuegos perimetral."},
                {"kind": "tool_use", "tool": "other", "tool_native": "cambio_de_cortafuegos",
                 "texto": "Se bloqueó la dirección de destino. El tráfico nocturno cayó a "
                          "cero durante las primeras seis horas."},
                {"kind": "tool_failure", "tool": "other", "tool_native": "consulta_siem",
                 "contradicted": True,
                 "texto": "A la noche siguiente el mismo volumen salió hacia otra "
                          "dirección: el destino rota, y bloquear una lista fija corre "
                          "detrás de una lista que crece."},
                {"kind": "observation", "tool": "other", "tool_native": "nota_del_analista",
                 "decisive": True,
                 "texto": "Bloquear el destino trata el síntoma más visible y deja "
                          "intacto el permiso que hace posible la salida."},
            ]},
            "reemplazo": {"outcome": "tests_passed", "pasos": [
                {"kind": "hypothesis", "tool": "other", "tool_native": "nota_del_analista",
                 "texto": "Se cambió de eje: en vez del destino, el permiso y el horario "
                          "del canal que transporta."},
                {"kind": "tool_use", "tool": "other", "tool_native": "cambio_aplicado",
                 "texto": "La cuenta del canal quedó limitada a su franja horaria y su "
                          "uso fuera de esa franja pasó a ser alerta por sí solo."},
                {"kind": "observation", "tool": "other", "tool_native": "consulta_siem",
                 "decisive": True,
                 "texto": "El intento siguiente se marcó en el momento, con destino "
                          "nuevo: la alerta ya no depende de conocer la dirección de "
                          "antemano."},
            ]},
        },
        "precondicion_esperada": (
            "Bloquear el destino era lo correcto cuando el destino es uno solo y fijo, "
            "y no rota entre noches."),
        "retenidos": [
            ("volumen-nocturno",
             "el uso de disco del archivo compartido sube todas las noches a la misma "
             "hora y de dia vuelve al valor de siempre"),
            ("cuenta-fuera-de-hora",
             "una cuenta de servicio inicio sesion un domingo de madrugada y ningun "
             "administrador dice haberla usado"),
        ],
    },

    # -------------------------------------------------------------- 2 · medicina
    {
        "slug": "diagnostico-diferencial",
        "dominio": "Diagnóstico diferencial en medicina interna",
        "task_type": "diagnostico_diferencial",
        "mecanismo": (
            "Un órgano irrita un nervio que comparte territorio con una zona lejana, y "
            "el dolor se siente en esa zona. Todo estudio del lugar donde duele vuelve "
            "normal, y volver a estudiar ese lugar es la trampa del mecanismo."),
        "trayectorias": [
            {"outcome": "tests_passed", "pasos": [
                {"kind": "hypothesis", "tool": "other", "tool_native": "nota_clinica",
                 "texto": "Se arrancó suponiendo una lesión del manguito rotador por el "
                          "dolor de hombro derecho de tres días."},
                {"kind": "tool_use", "tool": "other", "tool_native": "estudio_por_imagen",
                 "texto": "La radiografía del hombro volvió normal: sin fractura, sin "
                          "calcificación, sin pinzamiento."},
                {"kind": "tool_failure", "tool": "other", "tool_native": "tratamiento",
                 "texto": "Dos días de antiinflamatorio no cambiaron nada, y el hipo que "
                          "acompañaba al dolor siguió igual."},
                {"kind": "observation", "tool": "other", "tool_native": "examen_fisico",
                 "texto": "El dolor sube al inspirar hondo y no cambia al mover el brazo: "
                          "el movimiento del hombro no lo reproduce."},
                {"kind": "observation", "tool": "other", "tool_native": "estudio_por_imagen",
                 "decisive": True,
                 "texto": "La ecografía del abdomen superior mostró una colección debajo "
                          "del diafragma que irrita el nervio que comparte territorio con "
                          "el hombro."},
                {"kind": "correction", "tool": "other", "tool_native": "conducta",
                 "texto": "Se drenó la colección. El dolor de hombro y el hipo cedieron "
                          "juntos, sin ningún tratamiento dirigido al hombro."},
            ]},
            {"outcome": "tests_passed", "pasos": [
                {"kind": "hypothesis", "tool": "other", "tool_native": "nota_clinica",
                 "texto": "Se arrancó por la mandíbula: dolor mandibular de una semana, "
                          "con náusea, en alguien sin antecedentes dentales."},
                {"kind": "tool_use", "tool": "other", "tool_native": "estudio_por_imagen",
                 "texto": "La revisión odontológica y la placa panorámica volvieron "
                          "normales: sin caries profunda, sin absceso."},
                {"kind": "tool_failure", "tool": "other", "tool_native": "tratamiento",
                 "texto": "El analgésico calmó el dolor unas horas y volvió, siempre "
                          "asociado al esfuerzo y no a la masticación."},
                {"kind": "observation", "tool": "other", "tool_native": "examen_fisico",
                 "texto": "El dolor aparece al subir una escalera y cede en reposo; "
                          "apretar la mandíbula no lo reproduce."},
                {"kind": "observation", "tool": "other", "tool_native": "estudio_funcional",
                 "decisive": True,
                 "texto": "La prueba de esfuerzo mostró isquemia: el corazón duele en el "
                          "territorio del nervio que comparte con la mandíbula, lejos del "
                          "órgano."},
                {"kind": "correction", "tool": "other", "tool_native": "conducta",
                 "texto": "Se derivó a cardiología y el dolor mandibular desapareció con "
                          "el tratamiento del origen, no con el del lugar donde dolía."},
            ]},
        ],
        "alternativa": {
            "descartada": {"outcome": "user_corrected", "pasos": [
                {"kind": "hypothesis", "tool": "other", "tool_native": "nota_clinica",
                 "texto": "Se pidió una resonancia del hombro para ver el tejido blando "
                          "que la radiografía no muestra."},
                {"kind": "tool_use", "tool": "other", "tool_native": "estudio_por_imagen",
                 "texto": "La resonancia del hombro volvió normal, dos semanas de espera "
                          "después, y el dolor seguía igual."},
                {"kind": "observation", "tool": "other", "tool_native": "nota_clinica",
                 "contradicted": True, "decisive": True,
                 "texto": "Estudiar más fino el lugar donde duele no puede encontrar nada "
                          "cuando el origen está en otro órgano: el estudio confirma lo "
                          "que ya se sabía."},
            ]},
            "reemplazo": {"outcome": "tests_passed", "pasos": [
                {"kind": "hypothesis", "tool": "other", "tool_native": "nota_clinica",
                 "texto": "Se cambió la pregunta: en vez de qué hay en el hombro, qué "
                          "órganos comparten territorio con el hombro."},
                {"kind": "observation", "tool": "other", "tool_native": "examen_fisico",
                 "texto": "El dolor no se reproduce moviendo la zona y sí cambia con la "
                          "respiración: eso ya separa el origen local del referido."},
                {"kind": "observation", "tool": "other", "tool_native": "estudio_por_imagen",
                 "decisive": True,
                 "texto": "El estudio del abdomen superior encontró el origen en la "
                          "primera vuelta, sin repetir ninguna imagen de la zona que "
                          "dolía."},
            ]},
        },
        "precondicion_esperada": (
            "Estudiar más fino el lugar donde duele era lo correcto cuando hay un "
            "antecedente de golpe o esfuerzo local reciente que explique el dolor ahí "
            "mismo."),
        "retenidos": [
            ("rodilla-que-no-tiene-nada",
             "el chico se queja de que le duele la rodilla al caminar y la resonancia de "
             "rodilla no muestra nada"),
            ("entre-los-omoplatos",
             "la paciente dice que le arde entre los omoplatos desde hace un mes y el "
             "estudio de columna volvio normal"),
        ],
    },

    # -------------------------------------------------------------- 3 · helpdesk
    {
        "slug": "helpdesk",
        "dominio": "Helpdesk: cerrar la distancia entre el nivel 3 y el nivel 1",
        "task_type": "helpdesk",
        "mecanismo": (
            "Un recurso compartido y contado se agota en un servicio central. Cada "
            "consumidor traduce la espera al vocabulario de su propia pantalla, así que "
            "el que llama nunca nombra el recurso, y cada pantalla parece un problema "
            "distinto."),
        "trayectorias": [
            {"outcome": "tests_passed", "pasos": [
                {"kind": "hypothesis", "tool": "other", "tool_native": "nota_del_ticket",
                 "texto": "El ticket entró como problema de impresión: el botón de "
                          "imprimir aparece gris y no se puede apretar."},
                {"kind": "tool_use", "tool": "other", "tool_native": "accion_en_el_equipo",
                 "texto": "Se reinstaló el controlador de impresión y se probó con otra "
                          "impresora. El botón siguió gris en las dos."},
                {"kind": "observation", "tool": "other", "tool_native": "prueba_manual",
                 "texto": "El botón se habilita recién cuando vuelve la respuesta del "
                          "servicio de facturación, y esa respuesta está tardando más de "
                          "treinta segundos."},
                {"kind": "tool_failure", "tool": "other", "tool_native": "medicion_del_servicio",
                 "texto": "El servicio de facturación devuelve error de espera agotada en "
                          "una de cada tres consultas, y sólo en horario de oficina."},
                {"kind": "observation", "tool": "other", "tool_native": "medicion_del_servicio",
                 "decisive": True,
                 "texto": "El conjunto de conexiones del servicio está en su máximo y no "
                          "se libera: las que quedan colgadas nunca se devuelven, así que "
                          "el resto espera."},
                {"kind": "correction", "tool": "other", "tool_native": "cambio_aplicado",
                 "texto": "Se corrigió la devolución de las conexiones colgadas. El botón "
                          "dejó de aparecer gris sin tocar nada del lado de la "
                          "impresión."},
            ]},
            {"outcome": "tests_passed", "pasos": [
                {"kind": "hypothesis", "tool": "other", "tool_native": "nota_del_ticket",
                 "texto": "Tres reclamos distintos dicen que los informes salen en blanco; "
                          "se supuso una plantilla rota después del cambio del viernes."},
                {"kind": "tool_use", "tool": "other", "tool_native": "accion_en_el_equipo",
                 "texto": "Se restauró la plantilla anterior y el informe siguió saliendo "
                          "en blanco para algunos usuarios y bien para otros."},
                {"kind": "observation", "tool": "other", "tool_native": "revision_de_tickets",
                 "texto": "Los informes salen vacíos solamente entre las nueve y las diez "
                          "de la mañana, que es cuando entra el lote grande de "
                          "facturación."},
                {"kind": "tool_failure", "tool": "other", "tool_native": "medicion_del_servicio",
                 "texto": "En esa franja el servicio central rechaza consultas nuevas y "
                          "el informe recibe una respuesta vacía en lugar de un error "
                          "visible."},
                {"kind": "observation", "tool": "other", "tool_native": "medicion_del_servicio",
                 "decisive": True,
                 "texto": "El lote toma todas las conexiones disponibles durante una hora "
                          "y cada pantalla muestra el faltante con la forma de su propia "
                          "pantalla."},
                {"kind": "correction", "tool": "other", "tool_native": "cambio_aplicado",
                 "texto": "Se le reservó al lote un conjunto propio y separado. Los "
                          "informes de la mañana volvieron a salir completos."},
            ]},
        ],
        "alternativa": {
            "descartada": {"outcome": "user_corrected", "pasos": [
                {"kind": "hypothesis", "tool": "other", "tool_native": "nota_del_ticket",
                 "texto": "Se propuso reiniciar el servicio central todas las mañanas "
                          "antes de que abra la oficina."},
                {"kind": "tool_use", "tool": "other", "tool_native": "cambio_aplicado",
                 "texto": "Con el reinicio diario los reclamos bajaron a la mitad durante "
                          "la primera semana."},
                {"kind": "tool_failure", "tool": "other", "tool_native": "revision_de_tickets",
                 "contradicted": True,
                 "texto": "A la tercera semana los reclamos volvieron y llegaron más "
                          "tarde en el día: el reinicio corre el agotamiento de hora, no "
                          "lo saca."},
                {"kind": "observation", "tool": "other", "tool_native": "nota_del_ticket",
                 "decisive": True,
                 "texto": "Un reinicio programado esconde la señal que hacía falta para "
                          "encontrar el consumo que no devuelve lo que toma."},
            ]},
            "reemplazo": {"outcome": "tests_passed", "pasos": [
                {"kind": "hypothesis", "tool": "other", "tool_native": "nota_del_ticket",
                 "texto": "Se cambió de eje: en vez de vaciar el recurso a diario, medir "
                          "quién lo toma y no lo devuelve."},
                {"kind": "observation", "tool": "other", "tool_native": "medicion_del_servicio",
                 "texto": "La medición mostró que un solo consumidor retiene el noventa "
                          "por ciento de lo que toma, y lo retiene para siempre."},
                {"kind": "correction", "tool": "other", "tool_native": "cambio_aplicado",
                 "decisive": True,
                 "texto": "Corregido ese consumidor, el recurso dejó de agotarse y los "
                          "reclamos de las tres pantallas distintas desaparecieron "
                          "juntos."},
            ]},
        },
        "precondicion_esperada": (
            "El reinicio programado era lo correcto cuando la ventana de uso es corta y "
            "conocida y el arreglo de fondo no llega antes de esa ventana."),
        "retenidos": [
            ("app-que-no-carga",
             "la aplicacion del celular se queda cargando y despues dice que no hay "
             "conexion, pero el wifi anda bien"),
            ("pantalla-lenta-y-vacia",
             "desde ayer la pantalla de consulta tarda un minuto y a veces vuelve vacia "
             "sin decir nada"),
        ],
    },

    # ---------------------------------------------------- 4 · mantenimiento industrial
    {
        "slug": "mantenimiento-industrial",
        "dominio": "Mantenimiento industrial y robótica",
        "task_type": "mantenimiento_industrial",
        "mecanismo": (
            "Una restricción aguas abajo hace subir la presión aguas arriba, y lo que se "
            "rompe o alarma es el elemento más débil de la línea, no el que causa. "
            "Cambiar la pieza rota devuelve la máquina a producción y el ciclo vuelve "
            "con el período de la pieza nueva."),
        "trayectorias": [
            {"outcome": "tests_passed", "pasos": [
                {"kind": "hypothesis", "tool": "other", "tool_native": "nota_de_turno",
                 "texto": "La alarma de presión alta se atribuyó al filtro saturado, que "
                          "es lo que la marcó las dos veces anteriores."},
                {"kind": "tool_use", "tool": "other", "tool_native": "intervencion",
                 "texto": "Se paró el motor, se purgó la válvula y se cambió el filtro. "
                          "La alarma se apagó y la línea volvió a producir."},
                {"kind": "tool_failure", "tool": "other", "tool_native": "lectura_de_sensor",
                 "texto": "Seis horas después la alarma de presión volvió con el filtro "
                          "nuevo puesto y limpio."},
                {"kind": "observation", "tool": "other", "tool_native": "lectura_de_sensor",
                 "texto": "La temperatura del fluido bajó doce grados desde el cambio de "
                          "turno, y con esa temperatura el fluido pasa mucho más espeso."},
                {"kind": "observation", "tool": "other", "tool_native": "inspeccion",
                 "decisive": True,
                 "texto": "El intercambiador aguas abajo estaba enfriando de más: la "
                          "restricción está ahí, y el filtro sólo era el elemento que "
                          "primero acusa la presión."},
                {"kind": "correction", "tool": "other", "tool_native": "cambio_aplicado",
                 "texto": "Se corrigió la regulación del intercambiador. La alarma no "
                          "volvió en tres turnos y el filtro dejó de ensuciarse cada seis "
                          "horas."},
            ]},
            {"outcome": "tests_passed", "pasos": [
                {"kind": "hypothesis", "tool": "other", "tool_native": "nota_de_turno",
                 "texto": "El sello de la bomba se rompe cada dos semanas y se pidió "
                          "cambiar de proveedor del sello por uno más resistente."},
                {"kind": "tool_use", "tool": "other", "tool_native": "intervencion",
                 "texto": "Se montó el sello reforzado del proveedor nuevo, con el par de "
                          "apriete de catálogo."},
                {"kind": "tool_failure", "tool": "other", "tool_native": "lectura_de_sensor",
                 "texto": "El sello reforzado duró diecinueve días y falló igual, con el "
                          "mismo dibujo de desgaste del lado de la aspiración."},
                {"kind": "observation", "tool": "other", "tool_native": "lectura_de_sensor",
                 "texto": "La presión de aspiración cae por debajo del mínimo cada vez "
                          "que la válvula de la línea de retorno se cierra del todo."},
                {"kind": "observation", "tool": "other", "tool_native": "inspeccion",
                 "decisive": True,
                 "texto": "La restricción está en el retorno cerrado: la bomba trabaja "
                          "contra una salida tapada y el sello es lo primero que cede "
                          "aguas arriba."},
                {"kind": "correction", "tool": "other", "tool_native": "cambio_aplicado",
                 "texto": "Se dejó un paso mínimo garantizado en el retorno. El sello "
                          "original llegó a los tres meses sin marcas de desgaste."},
            ]},
        ],
        "alternativa": {
            "descartada": {"outcome": "user_corrected", "pasos": [
                {"kind": "hypothesis", "tool": "other", "tool_native": "nota_de_turno",
                 "texto": "Se propuso bajar la presión de la bomba para que la alarma no "
                          "llegara al umbral."},
                {"kind": "tool_use", "tool": "other", "tool_native": "cambio_aplicado",
                 "texto": "Con la presión más baja la alarma desapareció por completo "
                          "durante todo el turno."},
                {"kind": "tool_failure", "tool": "other", "tool_native": "registro_de_produccion",
                 "contradicted": True,
                 "texto": "La producción del turno cayó un dieciocho por ciento: a esa "
                          "presión la línea no llega al ritmo comprometido."},
                {"kind": "observation", "tool": "other", "tool_native": "nota_de_turno",
                 "decisive": True,
                 "texto": "Bajar la presión esconde la restricción sin sacarla, y se paga "
                          "con producción todos los turnos, no una sola vez."},
            ]},
            "reemplazo": {"outcome": "tests_passed", "pasos": [
                {"kind": "hypothesis", "tool": "other", "tool_native": "nota_de_turno",
                 "texto": "Se cambió de eje: en vez de bajar lo que empuja, buscar qué "
                          "está tapando aguas abajo."},
                {"kind": "observation", "tool": "other", "tool_native": "lectura_de_sensor",
                 "texto": "Midiendo la caída a lo largo de la línea, el salto grande "
                          "aparece después del filtro y no antes."},
                {"kind": "correction", "tool": "other", "tool_native": "cambio_aplicado",
                 "decisive": True,
                 "texto": "Sacada la restricción de aguas abajo, la presión volvió sola "
                          "al rango y la línea produjo al ritmo comprometido."},
            ]},
        },
        "precondicion_esperada": (
            "Bajar la presión era lo correcto cuando el fluido está frío y espeso y una "
            "parada de línea cuesta más que la producción que se pierde por trabajar más "
            "lento."),
        "retenidos": [
            ("motor-que-se-recalienta",
             "el motor del transporte se recalienta a la tarde y a la manana no, ya le "
             "cambiamos el rodamiento dos veces"),
            ("sello-nuevo-que-dura-poco",
             "el sello nuevo de la bomba duro tres semanas igual que el anterior y lo "
             "montamos con el par de catalogo"),
        ],
    },

    # ------------------------------------------------------- 5 · memoria corporativa
    {
        "slug": "memoria-corporativa",
        "dominio": "Memoria corporativa y estrategia legal",
        "task_type": "memoria_corporativa",
        "mecanismo": (
            "La estructura de la contraparte concentra el riesgo en un lugar distinto "
            "del que la diligencia mira por costumbre. El presupuesto se gasta en el "
            "activo visible, que sale limpio, y el pasivo que decide la operación está "
            "en cómo está armado el vínculo con quienes hacen el trabajo."),
        "trayectorias": [
            {"outcome": "tests_passed", "pasos": [
                {"kind": "hypothesis", "tool": "other", "tool_native": "memo_interno",
                 "texto": "Se arrancó con que el valor de la operación estaba en la "
                          "cartera de patentes, y ahí se puso el presupuesto de la "
                          "revisión."},
                {"kind": "tool_use", "tool": "other", "tool_native": "revision_documental",
                 "texto": "Seis semanas de revisión de la cartera de patentes: todas "
                          "vigentes, ninguna en disputa, ningún hallazgo que cambie el "
                          "precio."},
                {"kind": "observation", "tool": "other", "tool_native": "revision_documental",
                 "texto": "El setenta por ciento del equipo de la contraparte no está en "
                          "relación de dependencia: factura como proveedor independiente."},
                {"kind": "tool_failure", "tool": "other", "tool_native": "consulta_a_asesores",
                 "texto": "La autoridad ya reclasificó ese mismo esquema en dos casos del "
                          "sector, con efecto retroactivo sobre los años trabajados."},
                {"kind": "observation", "tool": "other", "tool_native": "cuantificacion",
                 "decisive": True,
                 "texto": "La contingencia por esa reclasificación supera el precio "
                          "ofrecido: el riesgo no estaba en lo que se estaba comprando "
                          "sino en quién hace el trabajo."},
                {"kind": "correction", "tool": "other", "tool_native": "decision",
                 "texto": "Se abandonó la compra. La revisión de patentes se registró "
                          "como el gasto que no movió ninguna decisión."},
            ]},
            {"outcome": "tests_passed", "pasos": [
                {"kind": "hypothesis", "tool": "other", "tool_native": "memo_interno",
                 "texto": "Para la alianza comercial se supuso que lo que había que "
                          "revisar era la marca y su registro en cada país."},
                {"kind": "tool_use", "tool": "other", "tool_native": "revision_documental",
                 "texto": "La marca salió limpia en los siete países y el informe se "
                          "entregó sin observaciones."},
                {"kind": "observation", "tool": "other", "tool_native": "revision_documental",
                 "texto": "Los contratos con la red de distribución tienen exclusividad "
                          "sin plazo y sin causal de salida en cinco de esos países."},
                {"kind": "tool_failure", "tool": "other", "tool_native": "consulta_a_asesores",
                 "texto": "Salir de esos contratos requiere acuerdo de la otra parte, y "
                          "la indemnización estimada duplica el resultado esperado de la "
                          "alianza."},
                {"kind": "observation", "tool": "other", "tool_native": "cuantificacion",
                 "decisive": True,
                 "texto": "Otra vez el pasivo estaba en el vínculo con quien opera, no en "
                          "el activo que se revisó, y aparece recién al querer "
                          "deshacerlo."},
                {"kind": "correction", "tool": "other", "tool_native": "decision",
                 "texto": "La alianza se firmó acotada a dos países, y la revisión "
                          "empezó por los contratos de la red en las operaciones "
                          "siguientes."},
            ]},
        ],
        "alternativa": {
            "descartada": {"outcome": "user_corrected", "pasos": [
                {"kind": "hypothesis", "tool": "other", "tool_native": "memo_interno",
                 "texto": "En vez de comprar la empresa se propuso licenciar su "
                          "tecnología y evitar el pasivo entero."},
                {"kind": "tool_use", "tool": "other", "tool_native": "cuantificacion",
                 "texto": "La licencia daba acceso a lo mismo sin heredar ninguna "
                          "contingencia de personal."},
                {"kind": "tool_failure", "tool": "other", "tool_native": "cuantificacion",
                 "contradicted": True,
                 "texto": "Con el costo del dinero al nueve por ciento, el flujo de "
                          "regalías a diez años supera el precio de compra y la opción "
                          "deja de cerrar."},
                {"kind": "observation", "tool": "other", "tool_native": "memo_interno",
                 "decisive": True,
                 "texto": "La licencia gana o pierde por el costo del dinero, no por el "
                          "activo: es la misma decisión con otro régimen de tasa."},
            ]},
            "reemplazo": {"outcome": "tests_passed", "pasos": [
                {"kind": "hypothesis", "tool": "other", "tool_native": "memo_interno",
                 "texto": "Se cambió de eje: primero cuantificar el pasivo del vínculo "
                          "con quien hace el trabajo, y recién después discutir la forma "
                          "de la operación."},
                {"kind": "observation", "tool": "other", "tool_native": "cuantificacion",
                 "texto": "Cuantificado ese pasivo, la conversación de precio se dio una "
                          "sola vez y con el número sobre la mesa."},
                {"kind": "correction", "tool": "other", "tool_native": "decision",
                 "decisive": True,
                 "texto": "La operación se cerró con retención de precio por esa "
                          "contingencia, sin repetir la revisión del activo visible."},
            ]},
        },
        "precondicion_esperada": (
            "Licenciar en vez de comprar era lo correcto cuando el costo del dinero está "
            "por debajo de cierto umbral, porque ahí el flujo de regalías vale menos que "
            "el precio de compra."),
        "retenidos": [
            ("otra-empresa-parecida",
             "el directorio quiere comprar una empresa parecida y proponen empezar "
             "revisando su cartera de marcas"),
            ("equipo-como-proveedores",
             "casi todo el equipo de la contraparte esta contratado como proveedores "
             "independientes y facturan por mes"),
        ],
    },

    # ------------------------------------------------------------- 6 · QA de juegos
    {
        "slug": "qa-de-juego",
        "dominio": "Diseño de juegos y testing de QA",
        "task_type": "qa_de_juego",
        "mecanismo": (
            "Dos estados que el diseño supone excluyentes se solapan porque una "
            "transición se interrumpe antes de limpiar su marca. Cualquier acción que "
            "pueda interrumpir esa transición reproduce el estado, así que la lista de "
            "combinaciones no se termina nunca."),
        "trayectorias": [
            {"outcome": "tests_passed", "pasos": [
                {"kind": "hypothesis", "tool": "other", "tool_native": "reporte_de_qa",
                 "texto": "El reporte decía que el inventario estaba roto: quedar "
                          "invulnerable para siempre después de abrirlo en el aire."},
                {"kind": "tool_use", "tool": "other", "tool_native": "reproduccion",
                 "texto": "Se reprodujo la secuencia doce veces: saltar, abrir el "
                          "inventario en el aire, recibir un golpe. Siempre queda "
                          "invulnerable."},
                {"kind": "tool_failure", "tool": "other", "tool_native": "reproduccion",
                 "texto": "Bloquear el inventario mientras el personaje está en el aire "
                          "no alcanzó: la misma secuencia con el menú de mapa vuelve a "
                          "dejarlo invulnerable."},
                {"kind": "observation", "tool": "other", "tool_native": "instrumentacion",
                 "texto": "La marca de invulnerabilidad se levanta al empezar la "
                          "animación de golpe y se baja al terminarla, no por tiempo."},
                {"kind": "observation", "tool": "other", "tool_native": "instrumentacion",
                 "decisive": True,
                 "texto": "Abrir cualquier menú congela la animación, así que la "
                          "animación no termina nunca y la marca no se baja: el menú es "
                          "un ejemplo, no la causa."},
                {"kind": "correction", "tool": "other", "tool_native": "cambio_aplicado",
                 "texto": "La marca pasó a bajarse en la salida del estado y no al final "
                          "de la animación. Las dos secuencias dejaron de reproducir el "
                          "efecto."},
            ]},
            {"outcome": "tests_passed", "pasos": [
                {"kind": "hypothesis", "tool": "other", "tool_native": "reporte_de_qa",
                 "texto": "Se reportó como problema de colisión: el personaje atraviesa "
                          "la pared si toma una poción mientras sube la escalera."},
                {"kind": "tool_use", "tool": "other", "tool_native": "reproduccion",
                 "texto": "Se reprodujo en tres escaleras distintas y en dos mapas: pasa "
                          "siempre que el consumo empieza antes de que termine el "
                          "enganche a la escalera."},
                {"kind": "tool_failure", "tool": "other", "tool_native": "reproduccion",
                 "texto": "Ajustar el volumen de colisión de la pared no cambió nada: el "
                          "personaje la sigue atravesando con la pared más gruesa."},
                {"kind": "observation", "tool": "other", "tool_native": "instrumentacion",
                 "texto": "Durante el enganche a la escalera el personaje deja de "
                          "chocar, y esa suspensión se levanta al terminar el enganche."},
                {"kind": "observation", "tool": "other", "tool_native": "instrumentacion",
                 "decisive": True,
                 "texto": "El consumo interrumpe el enganche a mitad de camino, así que "
                          "la suspensión queda puesta: el mismo solapamiento de dos "
                          "estados, con otra cara."},
                {"kind": "correction", "tool": "other", "tool_native": "cambio_aplicado",
                 "texto": "La suspensión pasó a levantarse en la salida del estado. Las "
                          "dos secuencias, la de la poción y la del inventario, se "
                          "arreglaron con el mismo cambio."},
            ]},
        ],
        "alternativa": {
            "descartada": {"outcome": "user_corrected", "pasos": [
                {"kind": "hypothesis", "tool": "other", "tool_native": "reporte_de_qa",
                 "texto": "Se propuso bloquear la combinación reportada: no dejar abrir "
                          "el inventario mientras el personaje está en el aire."},
                {"kind": "tool_use", "tool": "other", "tool_native": "cambio_aplicado",
                 "texto": "Con el bloqueo puesto, la secuencia del reporte dejó de "
                          "reproducir el efecto y el reporte se cerró."},
                {"kind": "tool_failure", "tool": "other", "tool_native": "reproduccion",
                 "contradicted": True,
                 "texto": "Dos días después llegó el mismo efecto con el menú de mapa, y "
                          "después con la pantalla de pausa: la lista de combinaciones no "
                          "se termina."},
                {"kind": "observation", "tool": "other", "tool_native": "reporte_de_qa",
                 "decisive": True,
                 "texto": "Bloquear la combinación tapa la puerta que alguien encontró y "
                          "deja abiertas las que todavía no probó nadie."},
            ]},
            "reemplazo": {"outcome": "tests_passed", "pasos": [
                {"kind": "hypothesis", "tool": "other", "tool_native": "reporte_de_qa",
                 "texto": "Se cambió de eje: en vez de prohibir combinaciones, arreglar "
                          "dónde se limpia la marca del estado."},
                {"kind": "observation", "tool": "other", "tool_native": "instrumentacion",
                 "texto": "Limpiando la marca en la salida del estado, ninguna "
                          "interrupción puede dejarla puesta, venga de donde venga."},
                {"kind": "correction", "tool": "other", "tool_native": "cambio_aplicado",
                 "decisive": True,
                 "texto": "El bloqueo de la combinación se pudo sacar: dejó de hacer "
                          "falta, y con él se fue una restricción que molestaba a quien "
                          "juega."},
            ]},
        },
        "precondicion_esperada": (
            "Bloquear la combinación era lo correcto cuando falta muy poco para la fecha "
            "de publicación y tocar la máquina de estados no entra en la ventana de "
            "pruebas que queda."),
        "retenidos": [
            ("empujon-y-mapa",
             "si abro el mapa justo cuando me empuja el enemigo me quedo pegado en el "
             "aire y no caigo mas"),
            ("guardar-en-la-puerta",
             "guardar la partida en medio de la animacion de la puerta me deja sin poder "
             "moverme"),
        ],
    },
]


def por_slug(slug):
    for caso in CASOS:
        if caso["slug"] == slug:
            return caso
    raise KeyError(slug)


def retenidos_ajenos(slug):
    """Los retenidos de los OTROS cinco dominios. El control negativo de cada uno.

    No hace falta inventar prompts ajenos: los diez síntomas de los otros dominios ya son
    material real del mismo experimento, escritos antes de ver ningún sueño, y con la
    misma mano — que en un control negativo juega a favor de encontrar falsos positivos,
    no en contra.
    """
    return [(caso["slug"] + "/" + etiqueta, prompt)
            for caso in CASOS if caso["slug"] != slug
            for etiqueta, prompt in caso["retenidos"]]
