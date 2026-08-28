"""La profecía tiene fecha, ¿y el arreglo tiene commit? (git como notario)

**La evidencia más fuerte que tiene el proyecto es prosa.** `LATER.md` cuenta que dream
proyectó cinco síntomas que nadie había observado y que la sesión siguiente fue a mirarlos:
dos confirmados y arreglados, uno confirmado como latente, uno refutado, uno abierto. Es el
único lugar donde el ciclo entero cerró sobre material real, y es lo que el README promete.

Y sin embargo, **hoy ningún script puede comprobarlo.** Lo que quedó registrado en el store
es un campo de texto libre: `resolved_by = "sesión 2026-08-28, PR 54"`. Una persona lo lee y
entiende; un gate no. Y la regla 2 de `CLAUDE.md` es clara: *si no se puede automatizar, no
es un gate, es una opinión*. La mejor evidencia del proyecto está, ahora mismo, del lado de
las opiniones.

**Qué hace este experimento.** Le pide a git que haga de notario. Para cada conjetura
resuelta pregunta tres cosas que se responden solas:

1. ¿El registro nombra un **objeto verificable** —un commit o un PR— o sólo prosa?
2. Si lo nombra: ¿ese objeto **existe** en la historia de este repositorio?
3. ¿Es **posterior** a la trayectoria que produjo la conjetura, y sigue siendo ancestro de
   `HEAD` — es decir, nadie lo revirtió?

Las tres juntas son la afirmación que el proyecto querría poder hacer: *"esto se conjeturó
antes de que ocurriera, y acá está el commit que lo arregló después"*. Una conjetura que
pasa las tres deja de depender de que alguien se acuerde.

**Lo que NO hace.** No decide si la conjetura era cierta —eso lo dijo la persona que fue a
mirar— ni le pone nota al arreglo. Mide **cuánta de la evidencia del proyecto sobrevive a
que la revise un script**, que es una pregunta distinta y hoy sin responder.

**Y desde el 2026-08-28 es un gate, hacia adelante.** `nightshift resolve` acepta
`--commit SHA` o `--pr N` y lo guarda en `projections.resolution_ref`, en su propia
columna y con dos formas nada más. El store anota una sola vez `notary_since`: las
resoluciones anteriores quedan como testimonio —eran prosa cuando se escribieron y no hay
forma honesta de convertirlas— y **las posteriores tienen que nombrar un objeto que git
encuentre**. Este archivo sale 1 si alguna no lo hace.

No llama al modelo. Lee el store real en sólo lectura y corre `git` sobre este repositorio.

    python3 experimentos/11-la-profecia-tiene-notario.py     # sale 1 si el gate falla
    make notario
"""

import re
import subprocess
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))

# Un sha suelto en el texto, o un "PR 54" / "#54" / "pull request 54".
RE_SHA = re.compile(r"\b([0-9a-f]{7,40})\b")
RE_PR = re.compile(r"(?:pr|pull request|#)\s*#?\s*(\d{1,5})\b", re.IGNORECASE)


def git(*args):
    r = subprocess.run(["git"] + list(args), cwd=str(RAIZ),
                       capture_output=True, text=True)
    return r.returncode, r.stdout.strip()


def commit_de_pr(numero):
    """El merge commit de un PR, si está en la historia."""
    code, salida = git("log", "--all", "--format=%H %cI %s",
                       "--grep=Merge pull request #%s " % numero)
    if code != 0 or not salida:
        return None
    sha, fecha, asunto = salida.splitlines()[0].split(" ", 2)
    return {"sha": sha, "fecha": fecha, "asunto": asunto}


def commit_por_sha(sha):
    code, salida = git("log", "-1", "--format=%H %cI %s", sha)
    if code != 0 or not salida:
        return None
    sha, fecha, asunto = salida.split(" ", 2)
    return {"sha": sha, "fecha": fecha, "asunto": asunto}


def es_ancestro(sha):
    code, _ = git("merge-base", "--is-ancestor", sha, "HEAD")
    return code == 0


def objeto_citado(texto):
    """¿El registro nombra algo que git pueda buscar?

    Se busca primero el PR y después el sha suelto: un `resolved_by` como "sesión
    2026-08-28, PR 54" tiene las dos formas de fecha adentro y un sha de siete caracteres
    hexadecimales se parece demasiado a cualquier cosa.
    """
    for m in RE_PR.finditer(texto or ""):
        c = commit_de_pr(m.group(1))
        if c:
            return ("PR #%s" % m.group(1)), c
    for m in RE_SHA.finditer(texto or ""):
        if m.group(1).isdigit():           # "2026" no es un sha
            continue
        c = commit_por_sha(m.group(1))
        if c:
            return ("commit %s" % m.group(1)[:8]), c
    return None, None


def resueltas():
    """Las conjeturas que alguien ya resolvió, con la fecha de su trayectoria."""
    from nightshift import store
    conn = store.connect()
    try:
        filas = conn.execute(
            "SELECT p.text, p.status, p.resolved_by, p.evidence, p.resolved_at,"
            "       p.resolution_ref, t.id AS tid, t.created_at AS t0"
            "  FROM projections p JOIN trajectories t ON t.id = p.trajectory_id"
            " WHERE p.status IN ('confirmed', 'refuted')"
            " ORDER BY t.created_at, p.idx").fetchall()
        return [dict(f) for f in filas], store.notary_since(conn)
    finally:
        conn.close()


def objeto_del_ref(ref):
    """El objeto que nombra la columna nueva. Dos formas y nada más."""
    if not ref:
        return None, None
    clase, _, valor = ref.partition(":")
    if clase == "pr":
        return ("PR #%s" % valor), commit_de_pr(valor)
    if clase == "commit":
        return ("commit %s" % valor[:8]), commit_por_sha(valor)
    return ref, None


def main():
    conjeturas, desde = resueltas()
    if not conjeturas:
        raise SystemExit("no hay conjeturas resueltas en este store: nada que notarizar")

    print("la profecía tiene fecha, ¿y el arreglo tiene commit?")
    print("%d conjetura(s) resuelta(s) en el store real. Notario: git sobre este repo."
          % len(conjeturas))
    print("el gate exige objeto verificable desde %s (`notary_since`)." % (desde or "—"))
    print()

    notarizadas, solo_prosa, incumplen = [], [], []
    for c in conjeturas:
        # Primero la columna. La prosa es el camino de compatibilidad para lo viejo, y
        # existe para poder medir cuánto quedó afuera, no para seguir aceptando prosa.
        cita, commit = objeto_del_ref(c.get("resolution_ref"))
        if not commit:
            cita, commit = objeto_citado("%s %s" % (c["resolved_by"] or "",
                                                    c["evidence"] or ""))
        print("· [%s] %s" % (c["status"], c["text"][:66]))
        print("    trayectoria %s del %s" % (c["tid"][:8], c["t0"]))
        print("    resuelta por: %s" % (c["resolved_by"] or "(sin autor)"))
        if not commit:
            solo_prosa.append(c)
            if desde and (c["resolved_at"] or "") > desde:
                incumplen.append(c)
                print("    INCUMPLE EL GATE: resuelta el %s, después de que la columna"
                      % c["resolved_at"])
                print("    existiera, y sin `--commit` ni `--pr`.")
            else:
                print("    NO NOTARIZADA: el registro no nombra ningún commit ni PR que git")
                print("    pueda buscar. Es anterior al gate: queda como testimonio.")
            print()
            continue
        posterior = commit["fecha"] > c["t0"]
        vivo = es_ancestro(commit["sha"])
        ok = posterior and vivo
        (notarizadas if ok else solo_prosa).append(c)
        if not ok and desde and (c["resolved_at"] or "") > desde:
            incumplen.append(c)
        print("    cita %s → %s  %s" % (cita, commit["sha"][:8], commit["asunto"][:44]))
        print("    posterior a la conjetura: %s (%s)" % ("sí" if posterior else "NO",
                                                         commit["fecha"]))
        print("    sigue siendo ancestro de HEAD: %s" % ("sí" if vivo else "NO, se revirtió"))
        print("    %s" % ("NOTARIZADA: la conjetura es anterior y el arreglo está en la "
                          "historia." if ok else "NO NOTARIZADA."))
        print()

    print("=" * 82)
    print("notarizadas por git: %d de %d" % (len(notarizadas), len(conjeturas)))
    print()
    if not notarizadas:
        print("NINGUNA. La mejor evidencia del proyecto es, hoy, íntegramente prosa: un")
        print("campo de texto libre que una persona entiende y un gate no puede leer.")
    elif solo_prosa:
        print("PARCIAL. %d conjetura(s) se pueden verificar sin creerle a nadie; %d dependen"
              % (len(notarizadas), len(solo_prosa)))
        print("de que alguien se acuerde. La diferencia entre las dos no es la calidad de la")
        print("evidencia: es que en unas el autor escribió `PR 54` y en otras escribió el")
        print("nombre de un archivo de notas. Es un accidente de redacción decidiendo qué")
        print("parte del proyecto es auditable.")
    else:
        print("TODAS. Cada conjetura resuelta apunta a un objeto que git encuentra, fechado")
        print("después de la trayectoria que la produjo y todavía vivo en la historia.")
    print()
    print("Lo que esto NO dice: que la conjetura fuera cierta, ni que el arreglo fuera bueno.")
    print("Dice cuánta de la evidencia sobrevive a que la revise un script en vez de una")
    print("persona — y `CLAUDE.md` regla 2 es sobre exactamente esa diferencia.")
    print()
    if incumplen:
        print("GATE: FALLA. %d resolución(es) posteriores a `notary_since` sin objeto"
              % len(incumplen))
        print("verificable. Resolvelas de nuevo con `--commit SHA` o `--pr N`:")
        for c in incumplen:
            print("  · %s" % c["text"][:70])
    else:
        print("GATE: OK — ninguna resolución posterior a `notary_since` quedó sin notario.")
    print("=" * 82)
    return 1 if incumplen else 0


if __name__ == "__main__":
    sys.exit(main())
