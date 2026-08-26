# ADR-003 — El modelo de dream corre en Claude Code, no local

| Campo | Valor |
|---|---|
| Estado | Aceptada |
| Fecha | 2026-08-26 |
| Decide | Matías |
| Revierte | spec §2.2 ("todo el modelo corre local") y la prohibición de `CLAUDE.md` |

## Contexto

La spec v0.3 puso "cualquier dependencia de API remota" fuera de alcance y fijó Qwen
local. Los dos motivos eran buenos y siguen siéndolo:

1. **Privacidad.** "Histora primero": el caso de uso más sensible se soporta antes que el
   cómodo. Si el material no puede salir de la máquina, no sale.
2. **Fricción de instalación cero API keys nuevas** (condición de éxito 2).

Dos cosas cambiaron desde que se escribió, y las dos se midieron:

**La calidad del modelo local no alcanza.** Dream corre con `qwen3.5:4b` —el más chico
que entra en la ventana nocturna de una Air— y produce abstracciones genéricas. Con el
mismo set fixture, el patrón que sale es *"el error de decodificación ocurre porque los
archivos no declaran su código"*. Eso está en `LATER.md` como riesgo desde M3-a, con la
consecuencia escrita: si M4 da no-go, no se sabría si el problema es la idea o el modelo.

**El argumento de fricción se dio vuelta.** nightshift es un plugin de Claude Code: si
está corriendo, Claude Code está instalado y autenticado. Pedir además ollama y una
descarga de 3 GB es *más* fricción, no menos. Y "cero API keys nuevas" se cumple igual —
no hay ninguna key nueva: es el mismo agente que ya está ahí, invocado por `subprocess`
en modo no interactivo.

## Decisión

El modelo que consolida es **Claude Code por defecto**, invocado como
`claude -p --output-format json` por `subprocess`, con el prompt por stdin.

El backend local **no se borra**: `model_backend: "local"` sigue eligiendo Qwen por
ollama, y `model_command` sigue aceptando cualquier ejecutable que lea stdin y escriba
stdout. Para un repositorio cuyo material no puede salir de la máquina, volver al modelo
local es una línea de config.

## Consecuencias

**Las trayectorias redactadas salen de la máquina.** Es el costo real de esta decisión y
no se disimula. Lo que sale ya pasó por el redactor determinista —el store nunca contiene
material sin redactar (spec §8.2)— pero *redactado* no es lo mismo que *seguro de enviar*
para el caso Histora. Quien tenga ese caso usa el backend local; queda escrito acá para
que la elección sea consciente y no un default heredado.

**El redactor cambia de rol.** Antes era la barrera antes de *persistir*. Ahora es también
la última barrera antes de que el material *salga de la máquina*. Su superficie de riesgo
sube, y con ella la importancia de las fixtures de Histora que todavía no están (`LATER`).

**Dream cuesta dinero.** Cada corrida nocturna tiene un costo por token, y queda
registrado: el store guarda `cost_usd` por corrida y `nightshift schedule status` lo
muestra. Un backend que no cobra devuelve nada, que es la respuesta correcta y no un cero
inventado.

**El benchmark ahora tiene dos modelos.** El del agente que resuelve las tareas y el que
consolida. `bench/PREREG.md` §2 tiene un solo `TODO(Matias)` para "modelo exacto y
versión": hay que desdoblarlo antes de congelar, o el pre-registro fija una constante y
deja la otra suelta.

**Dream no puede capturar su propia sesión.** El backend nuevo es un agente con los hooks
de nightshift disponibles; sin cuidado, consolidar generaría una trayectoria de la propia
consolidación en el store que está consolidando. El hijo corre con un `NIGHTSHIFT_HOME`
desechable, y como ahí no hay config, la captura ni siquiera arranca (spec §8.1).

**Lo que no cambia:** nightshift sigue sin hablar por red desde su propio código. Es
`subprocess` a un ejecutable local, igual que ollama. `make lint-code` sigue verificando
que no haya `socket`, `urllib` ni `http` en `nightshift/`.

## Alternativas consideradas

1. **Quedarse en local puro.** Es la decisión original. Rechazada por quien decide: la
   calidad medida no alcanza para que M4 mida la idea en vez del modelo, y agrega
   fricción de instalación en vez de sacarla.
2. **Un modelo local más grande** (`qwen3.5:9b`, disponible). Considerada y **no
   descartada**: sigue siendo una línea de config. No resuelve la fricción de la descarga
   ni el techo de calidad, pero conserva la privacidad entera.
3. **Hablar con la API de Anthropic directamente.** Rechazada: obliga a una API key
   nueva y rompe la condición de éxito 2. Invocar el agente ya instalado no.
4. **Híbrido por repositorio** — local para los marcados como sensibles, Claude Code para
   el resto. **No implementado.** Es la evolución natural de esta decisión: hoy el backend
   se elige por instalación, no por repo. Va a `LATER.md`.
