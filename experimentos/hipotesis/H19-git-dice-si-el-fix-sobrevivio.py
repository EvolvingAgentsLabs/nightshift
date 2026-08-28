"""H19 — Git puede decir si el fix de una trayectoria sobrevivió."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _marco import PASS, FAIL, BLOCKED, StoreDesechable, correr_solo

IDEA = "oraculos"
HIPOTESIS = "Git puede decir si el fix de una trayectoria sobrevivio."


def correr():
    import subprocess, tempfile
    from nightshift import context, oracle
    with tempfile.TemporaryDirectory(prefix="nightshift-git-") as repo:
        def git(*args):
            return subprocess.run(["git", "-C", repo, *args], capture_output=True,
                                  text=True, timeout=10)
        git("init", "-q", "-b", "main")
        git("config", "user.email", "x@example.com")
        git("config", "user.name", "x")
        open(os.path.join(repo, "a.txt"), "w").write("uno\n")
        git("add", "-A"); git("commit", "-qm", "el fix que sobrevive")
        sobrevive = git("rev-parse", "HEAD").stdout.strip()
        open(os.path.join(repo, "b.txt"), "w").write("dos\n")
        git("add", "-A"); git("commit", "-qm", "el fix que se revierte")
        revertido = git("rev-parse", "HEAD").stdout.strip()
        git("revert", "--no-edit", revertido)

        v_ok = oracle.corroborate(repo, sobrevive)
        v_rev = oracle.corroborate(repo, revertido)
        v_falso = oracle.corroborate(repo, "0" * 40)
        v_sin = oracle.corroborate(repo, None)
        v_otro = oracle.corroborate(repo, sobrevive, fingerprint="f" * 64)

    esperado = {"sobrevivio": (v_ok["status"], oracle.SURVIVED),
                "revertido": (v_rev["status"], oracle.REVERTED),
                "inexistente": (v_falso["status"], oracle.ABSENT),
                "sin base_commit": (v_sin["status"], oracle.UNKNOWN),
                "otro repo": (v_otro["status"], oracle.UNKNOWN)}
    fallos = ["%s: %s (esperado %s)" % (n, a, b) for n, (a, b) in esperado.items() if a != b]
    if fallos:
        return FAIL, "\n".join(fallos)
    return PASS, ("5 casos sobre un repo git de verdad: sobrevive, revertido, inexistente,\n"
                  "sin base_commit y desde otro repo.\n"
                  "Sin modelo, sin red y sin credencial: es la unica fuente del proyecto\n"
                  "que no sale ni de lo capturado ni de lo abstraido.\n"
                  "Y NO es verify: corrobora. Una candidata que sobrevivio sigue siendo\n"
                  "candidate, sigue pesando lo mismo y sigue sin estar verificada.")


if __name__ == "__main__":
    sys.exit(correr_solo(sys.modules[__name__]))
