"""Oráculos: comportamiento que el modelo no produce solo (plan §7, ADR-006).

Dream proyecta conjeturas. Un oráculo es lo que las **cierra** — y hasta acá el único era
una persona tecleando `nightshift resolve`.

**La restricción que ordena todo el diseño: un oráculo es un comando, no un servicio.**
ADR-003 prohíbe que `nightshift/` hable con la red o exija una API key nueva. El mismo
patrón que ya usa el modelo —`subprocess`, stdin, stdout— sirve para una persona, un
script, otro modelo o una API que envuelva el usuario, con su credencial y su riesgo, sin
que nightshift hable con la red **nunca**.

Dos cosas viven acá y son distintas, aunque las dos sean "un oráculo":

- **Resolver una conjetura** (`ask`): un veredicto sobre un síntoma que nadie observó.
- **Corroborar una trayectoria** (`corroborate`): mirar la historia de git y preguntar si
  el fix sobrevivió. **No es `verify`.** `verify` (ADR-002, M5) reproduce una trayectoria
  contra un gate declarado; esto lee historia. Una candidata que sobrevivió no queda
  verificada: queda **corroborada**, que es una tercera categoría y no un ascenso. Si esa
  distinción se afloja, el proyecto pasa a decir que verifica cuando no verifica.
"""

from __future__ import annotations

import json
import shlex
import subprocess

from . import context

DEFAULT_TIMEOUT = 30

# Lo que un oráculo puede contestar sobre una conjetura. Los mismos tres estados que la
# tabla, y por el mismo motivo: no hay un cuarto para "probablemente".
VEREDICTOS = ("confirmed", "refuted", "open")


class OracleError(RuntimeError):
    """El oráculo no pudo contestar. Nunca se traga como un `open`.

    Un oráculo roto que devuelve "no sé" es indistinguible de uno que miró y no supo, y
    esa confusión convierte una falla de plomería en un dato.
    """


# ------------------------------------------------------------------ el genérico
def command_from_config(cfg) -> list[str] | None:
    """El ejecutable del usuario, si lo configuró. Nada más que eso."""
    configurado = cfg.get("oracle_command")
    if not configurado:
        return None
    if isinstance(configurado, str):
        return shlex.split(configurado)
    return [str(parte) for parte in configurado]


def ask(command, *, projection, pattern=None, timeout=DEFAULT_TIMEOUT) -> dict:
    """Le pregunta a un oráculo externo por **una** conjetura. Devuelve el veredicto.

    Contrato, deliberadamente chico para que escribir un oráculo sea media hora y no un
    proyecto: por stdin entra un JSON con `projection` y `pattern`; por stdout sale un
    JSON con `status` (uno de `VEREDICTOS`) y `evidence`.

    Lo que **no** hace: interpretar. Si el oráculo contesta algo que no encaja en el
    contrato, es un error y no un `open`.
    """
    pregunta = json.dumps({"projection": projection, "pattern": pattern,
                           "answers": list(VEREDICTOS)}, ensure_ascii=False)
    try:
        salida = subprocess.run(command, input=pregunta, capture_output=True, text=True,
                                timeout=timeout)
    except (OSError, subprocess.SubprocessError) as exc:
        raise OracleError("el oráculo no corrió: %s" % exc) from exc
    if salida.returncode != 0:
        raise OracleError("el oráculo salió %d: %s"
                          % (salida.returncode, (salida.stderr or "")[:200]))
    try:
        datos = json.loads(salida.stdout.strip() or "{}")
    except ValueError as exc:
        raise OracleError("el oráculo no devolvió JSON: %s"
                          % (salida.stdout or "")[:200]) from exc
    if not isinstance(datos, dict) or datos.get("status") not in VEREDICTOS:
        raise OracleError("veredicto fuera del contrato: %r" % (datos,))
    evidencia = str(datos.get("evidence") or "").strip()
    if datos["status"] != "open" and not evidencia:
        # La misma regla que para una persona, y por el mismo motivo: un veredicto sin
        # motivo es olvidar con otro nombre.
        raise OracleError("el oráculo resolvió sin evidencia")
    return {"status": datos["status"], "evidence": evidencia}


# --------------------------------------------------------------- el oráculo git
UNKNOWN, SURVIVED, REVERTED, ABSENT = "unknown", "survived", "reverted", "absent"


def corroborate(cwd, base_commit, *, fingerprint=None) -> dict:
    """¿El fix de esta trayectoria sobrevivió? Lee git y nada más.

    Sin modelo, sin red, sin credencial, y **completamente externo al modelo**: es la
    única fuente del proyecto que no sale ni de lo capturado ni de lo abstraído.

    Devuelve `{"status": …, "evidence": …, "checked_at": …}`. `unknown` cuando no se puede
    decidir, y eso es una respuesta: el store guarda el fingerprint del repo y no su ruta,
    así que corroborar sólo funciona corriendo **desde el repo que produjo la
    trayectoria**. Adivinar de qué repo se trata sería inventar procedencia.
    """
    resultado = {"status": UNKNOWN, "evidence": None, "checked_at": None,
                 "base_commit": base_commit}
    if not base_commit:
        resultado["evidence"] = "la trayectoria no registró `base_commit`"
        return resultado
    if fingerprint and context.repo_fingerprint(cwd) != fingerprint:
        resultado["evidence"] = ("este no es el repo que produjo la trayectoria: el store"
                                 " guarda el fingerprint, no la ruta")
        return resultado

    # ¿Existe todavía el objeto? Un rebase o un `push --force` lo puede haber dejado
    # huérfano, y eso no es lo mismo que revertido.
    if context._git(cwd, "cat-file", "-e", "%s^{commit}" % base_commit) is None and \
            context._git(cwd, "rev-parse", "--verify", "%s^{commit}" % base_commit) is None:
        resultado["status"] = ABSENT
        resultado["evidence"] = "el commit ya no está en este repo (rebase, force-push o poda)"
        return resultado

    # ¿Sigue siendo ancestro de HEAD? Si no, la rama que lo tenía no llegó.
    ancestro = subprocess.run(
        ["git", "-C", str(cwd), "merge-base", "--is-ancestor", base_commit, "HEAD"],
        capture_output=True, text=True, timeout=5.0)
    if ancestro.returncode != 0:
        resultado["status"] = ABSENT
        resultado["evidence"] = "el commit existe pero no es ancestro de HEAD"
        return resultado

    # ¿Lo revirtieron? La convención de `git revert` deja el sha en el cuerpo.
    revert = context._git(cwd, "log", "--oneline", "--grep",
                          "This reverts commit %s" % base_commit)
    if revert:
        resultado["status"] = REVERTED
        resultado["evidence"] = "revertido por %s" % revert.splitlines()[0][:80]
        return resultado

    despues = context._git(cwd, "rev-list", "--count", "%s..HEAD" % base_commit)
    resultado["status"] = SURVIVED
    resultado["evidence"] = ("sigue siendo ancestro de HEAD y nadie lo revirtió;"
                             " %s commit(s) después" % (despues or "?"))
    resultado["checked_at"] = None
    return resultado
