"""Los seis dominios del README, soñados de verdad. Genera; no juzga.

Por cada dominio de `casos_de_dominio.py` monta un store desechable con sus cuatro
trayectorias —las dos caras del mecanismo, más la alternativa descartada y la que la
reemplazó— y llama a `dream.consolidate` **tal como lo llama el plugin**: mismo prompt,
mismo modo de ideación, mismos gates, mismos reintentos, y el contraste de ADR-005 que se
dispara solo cuando hay una contradicción registrada.

No hay ninguna reimplementación acá. Si `consolidate` cambia, esto cambia con él, que es la
lección que dejó `camino_real.py`.

Lo que queda escrito en `salidas/dominios/<slug>.json`: la candidata entera —patrón,
señales, precondiciones, proyecciones, escena, logograma— el contraste con su
`old_valid_when`, y **lo que el gate rechazó en el camino**, que es tan resultado como lo
que pasó.

**No mide nada.** El marcador de enganche es `17-los-seis-dominios-compiten.py`, que no
llama al modelo. La separación es a propósito: generar cuesta, medir es gratis, y una
medición que se rehace sin volver a pagar se puede repetir cuantas veces haga falta.

Corre sobre un `HOME` temporal, con el store real intacto. El hijo que consolida sí recibe
el `HOME` de verdad —si no, `claude -p` se queda sin credenciales (`simulate.py` aprendió
lo mismo).
"""

import argparse
import json
import os
import sys
import tempfile
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))
sys.path.insert(0, str(RAIZ / "experimentos"))

import casos_de_dominio                                      # noqa: E402

SALIDAS = RAIZ / "experimentos" / "salidas" / "dominios"
REPO = "d" * 64


class HomeDesechable:
    """`HOME` temporal para el store. El HOME real se guarda para el hijo que consolida."""

    def __enter__(self):
        self.home_real = os.environ.get("HOME")
        self._dir = tempfile.TemporaryDirectory(prefix="nightshift-dominios-")
        os.environ["HOME"] = self._dir.name
        for modulo in ("nightshift.config", "nightshift.store"):
            sys.modules.pop(modulo, None)
        from nightshift import store
        self.store = store
        self.conn = store.connect()
        return self

    def __exit__(self, *exc):
        try:
            self.conn.close()
        finally:
            if self.home_real is not None:
                os.environ["HOME"] = self.home_real
            self._dir.cleanup()
        return False


def _abrir(d, task_type, trayectoria, sesion):
    tid = d.store.open_trajectory(d.conn, session_id=sesion, repo_fingerprint=REPO,
                                  task_type=task_type, base_commit="abc1234",
                                  redaction={"redactor_version": "0.1.0"})
    for paso in trayectoria["pasos"]:
        # `error_message` para lo que falló, `result_summary` para lo demás: es la misma
        # distinción que hace la captura, y `dream.texto_del_paso` lee las dos.
        campo = ("error_message" if paso["kind"] == "tool_failure" else "result_summary")
        d.store.append_step(d.conn, tid, kind=paso["kind"], tool=paso.get("tool"),
                            tool_native=paso.get("tool_native"),
                            decisive=paso.get("decisive", False),
                            **{campo: paso["texto"]})
        if paso.get("contradicted"):
            d.store.mark_last_contradicted(d.conn, tid)
    d.store.close_trajectory(d.conn, tid, result=trayectoria["outcome"])
    return tid


def montar(d, caso):
    """Las cuatro trayectorias del dominio, en el orden que el camino real necesita.

    El orden importa y no es cosmético: `dream.representative` promueve la de mejor
    desenlace y más nueva, y `dream.contradicted_by` sólo mira las **anteriores** a esa.
    Con la descartada y su reemplazo al final, el contraste se arma entre las dos que
    hablan del mismo problema. Al revés, el contraste saldría entre dos trayectorias que
    no se reemplazan, y sería un contraste sobre nada.
    """
    ids = []
    for i, tr in enumerate(caso["trayectorias"]):
        ids.append(_abrir(d, caso["task_type"], tr, "cara-%d" % i))
    descartada = _abrir(d, caso["task_type"], caso["alternativa"]["descartada"],
                        "alternativa-descartada")
    reemplazo = _abrir(d, caso["task_type"], caso["alternativa"]["reemplazo"],
                       "alternativa-reemplazo")
    return {"caras": ids, "descartada": descartada, "reemplazo": reemplazo}


def soniar(caso, *, modo, timeout):
    from nightshift import config, dream

    with HomeDesechable() as d:
        ids = montar(d, caso)
        cfg = config.load()
        comando = dream.detect_command(cfg)
        if not comando:
            raise SystemExit("no hay con qué consolidar: ni `claude` ni un qwen en ollama")
        modelo = dream.LocalModel(comando, timeout=timeout, home=d.home_real)
        reporte = dream.consolidate(d.conn, modelo, cfg=cfg, lookback_days=3650,
                                    log=lambda m: print("    %s" % m), modo=modo)

        # Lo que quedó en el store es lo que se guarda: leer del reporte lo que el store
        # persistió sería creerle al reporte sobre la base.
        candidatas = []
        for fila in d.conn.execute(
                "SELECT * FROM trajectories WHERE status = 'candidate'").fetchall():
            candidatas.append({
                "trajectory": fila["id"],
                "abstraction": json.loads(fila["abstraction_json"] or "{}"),
                "valid_when": json.loads(fila["valid_when_json"] or "[]"),
                "projected_signals": json.loads(fila["projected_signals_json"] or "[]"),
                "physical_scene": fila["physical_scene"],
                "logogram": fila["logogram"],
                "diagram": fila["diagram"],
                "ideation": fila["ideation"],
            })
        contrastes = []
        for fila in d.conn.execute(
                "SELECT * FROM trajectories WHERE status = 'superseded'").fetchall():
            contrastes.append({
                "trajectory": fila["id"],
                "es_la_descartada": fila["id"] == ids["descartada"],
                "contrast": json.loads(fila["contrast_json"] or "null")
                if "contrast_json" in fila.keys() else None,
            })

    return {"slug": caso["slug"], "dominio": caso["dominio"],
            "task_type": caso["task_type"], "modo": modo,
            "modelo": reporte["model"], "estrategia": reporte["strategy"],
            "grupos": reporte["groups"], "trayectorias": reporte["trajectories"],
            "rechazos": reporte["rejected"], "saltados": reporte["skipped"],
            "costo_usd": reporte["cost_usd"],
            "tokens_entrada": reporte["input_tokens"],
            "tokens_salida": reporte["output_tokens"],
            "candidatas": candidatas, "contrastes": contrastes,
            "precondicion_esperada": caso["precondicion_esperada"],
            "mecanismo_escrito_a_mano": caso["mecanismo"]}


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--dominio", action="append",
                    help="slug a soñar; repetible. Por defecto, los seis")
    ap.add_argument("--modo", default="fisica",
                    choices=("fisica", "mermaid"),
                    help="medio de la ideación (ADR-007). El default es el del plugin")
    ap.add_argument("--timeout", type=int, default=600)
    args = ap.parse_args()

    slugs = args.dominio or [c["slug"] for c in casos_de_dominio.CASOS]
    SALIDAS.mkdir(parents=True, exist_ok=True)

    print("Seis dominios, seis sueños. Modo de ideación: %s." % args.modo)
    print("Trayectorias escritas a mano: esto mide el consolidador, NO la captura.")
    print()

    for slug in slugs:
        caso = casos_de_dominio.por_slug(slug)
        print("▸ %s — %s" % (slug, caso["dominio"]))
        try:
            salida = soniar(caso, modo=args.modo, timeout=args.timeout)
        except Exception as exc:                             # noqa: BLE001
            # Un dominio que explota no se lleva puestos los otros cinco, y el motivo
            # queda escrito: un sueño que no salió es resultado igual.
            print("    FALLÓ: %s: %s" % (type(exc).__name__, exc))
            salida = {"slug": slug, "dominio": caso["dominio"], "modo": args.modo,
                      "error": "%s: %s" % (type(exc).__name__, exc),
                      "candidatas": [], "contrastes": []}
        destino = SALIDAS / ("%s.json" % slug)
        with open(destino, "w", encoding="utf-8") as fh:
            json.dump(salida, fh, indent=2, ensure_ascii=False)
            fh.write("\n")
        cand = salida.get("candidatas") or []
        if cand:
            c = cand[0]
            print("    candidata: %d señal(es), %d precondición(es), %d proyección(es)"
                  % (len(c["abstraction"].get("signals") or []),
                     len(c["valid_when"]), len(c["projected_signals"])))
            print("    logograma: %s" % (c["logogram"] or "—"))
        else:
            print("    sin candidata")
        con = [x for x in salida.get("contrastes") or [] if x.get("contrast")]
        print("    contraste: %s" % ("sí, con %d condición(es) de la descartada"
                                     % len(con[0]["contrast"].get("old_valid_when") or [])
                                     if con else "no"))
        print("    → %s" % destino.relative_to(RAIZ))
        print()

    print("Generado. El marcador lo saca 17-los-seis-dominios-compiten.py, que no")
    print("vuelve a llamar al modelo.")


if __name__ == "__main__":
    main()
