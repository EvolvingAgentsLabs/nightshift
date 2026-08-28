"""El README dice cosas verificables. Éste las verifica.

`lint-docs.sh` comprueba la **estructura** de la documentación: que los archivos existan,
que los enlaces resuelvan, que cada skill esté documentada. Lo que no puede comprobar es
si una frase sigue siendo **cierta**.

Y se desactualizó exactamente así: ADR-003 cambió el modelo de dream a Claude Code, y seis
lugares del README siguieron diciendo "con el modelo local" el mismo día. En este repo eso
cuesta más que en otro, porque el README es donde el proyecto dice explícitamente qué no
funciona: si esa parte no es confiable, ninguna lo es.

Qué se verifica acá, y por qué cada cosa:

- **Comandos y flags** que aparecen en bloques de código existen de verdad. Un ejemplo que
  no corre es peor que no tener ejemplo.
- **Rutas** de la estructura del repositorio existen.
- **Cifras** que se repiten —los `TODO(Matias)` del pre-registro— coinciden con la fuente.
- **Afirmaciones que caducan**: frases que eran ciertas y dejan de serlo cuando cambia un
  default. Es la clase de error que motivó este archivo.

Todo se extrae de bloques de código o de patrones fijos, nunca de la prosa: reformular un
párrafo no puede romper un test.
"""

import contextlib
import io
import re
import unittest
from pathlib import Path

from nightshift import cli, config

RAIZ = Path(__file__).resolve().parent.parent
READMES = ("README.md", "README.es.md")

FENCE_RE = re.compile(r"```[a-z]*\n(.*?)```", re.S)
INLINE_RE = re.compile(r"`([^`\n]+)`")
# Al principio de la línea: una invocación, no una mención en prosa dentro de un bloque
# de código ("the seven hooks nightshift registers" no es un comando).
COMANDO_RE = re.compile(r"^\s*(?:\./bin/)?nightshift ([a-z][a-z-]*)", re.M)
MAKE_RE = re.compile(r"\bmake ([a-z][a-z-]*)")
FLAG_RE = re.compile(r"(--[a-z][a-z-]+)")


def texto(nombre):
    return (RAIZ / nombre).read_text(encoding="utf-8")


def fragmentos_de_codigo(contenido):
    """Sólo bloques cercados y `código en línea`. La prosa no se toca."""
    partes = FENCE_RE.findall(contenido)
    partes += INLINE_RE.findall(FENCE_RE.sub("", contenido))
    return partes


def subcomandos_reales():
    salida = io.StringIO()
    with contextlib.redirect_stdout(salida), contextlib.suppress(SystemExit):
        cli.main(["--help"])
    match = re.search(r"\{([a-z,]+)\}", salida.getvalue())
    return set(match.group(1).split(",")) if match else set()


def ayuda_de(subcomando):
    salida = io.StringIO()
    with contextlib.redirect_stdout(salida), contextlib.suppress(SystemExit):
        cli.main([subcomando, "--help"])
    return salida.getvalue()


def objetivos_de_make():
    contenido = (RAIZ / "Makefile").read_text(encoding="utf-8")
    return set(re.findall(r"^([a-z][a-z-]*):", contenido, re.M))


# Frases que eran ciertas y dejan de serlo cuando cambia un default. Si el default cambia,
# el test dice qué frase hay que revisar en vez de dejarla mintiendo.
AFIRMACIONES_QUE_CADUCAN = (
    (lambda: config.DEFAULTS["model_backend"] == "claude-code",
     re.compile(r"(?i)con el modelo local|with the local model"),
     "el backend por defecto es `claude-code` (ADR-003), así que decir que dream "
     "consolida con el modelo local ya no es cierto"),
    (lambda: config.DEFAULTS["cross_repo"] is False,
     re.compile(r"(?i)transferencia cross-repo (ya )?(funciona|est[áa] entregada)"),
     "`cross_repo` sigue apagado por defecto: la capacidad C no está entregada"),
)


class ComandosTest(unittest.TestCase):
    def test_los_comandos_de_los_ejemplos_existen(self):
        """Un ejemplo que no corre es peor que no tener ejemplo."""
        reales = subcomandos_reales()
        self.assertTrue(reales, "no se pudo leer la lista de subcomandos")
        for nombre in READMES:
            for fragmento in fragmentos_de_codigo(texto(nombre)):
                for comando in COMANDO_RE.findall(fragmento):
                    with self.subTest(readme=nombre, comando=comando):
                        self.assertIn(comando, reales,
                                      "`nightshift %s` no existe" % comando)

    def test_los_flags_de_los_ejemplos_existen(self):
        for nombre in READMES:
            for fragmento in fragmentos_de_codigo(texto(nombre)):
                for linea in fragmento.splitlines():
                    match = COMANDO_RE.match(linea)
                    if not match:
                        continue
                    comando = match.group(1)
                    if comando not in subcomandos_reales():
                        continue
                    ayuda = ayuda_de(comando)
                    for flag in FLAG_RE.findall(linea.split("#")[0]):
                        with self.subTest(readme=nombre, comando=comando, flag=flag):
                            self.assertIn(flag, ayuda,
                                          "`nightshift %s` no acepta %s" % (comando, flag))

    def test_los_targets_de_make_existen(self):
        objetivos = objetivos_de_make()
        for nombre in READMES:
            for fragmento in fragmentos_de_codigo(texto(nombre)):
                for objetivo in MAKE_RE.findall(fragmento):
                    with self.subTest(readme=nombre, objetivo=objetivo):
                        self.assertIn(objetivo, objetivos, "`make %s` no existe" % objetivo)


class RutasTest(unittest.TestCase):
    def test_las_rutas_de_la_estructura_existen(self):
        """La estructura del repositorio se desactualiza sola en cuanto algo se mueve."""
        for nombre in READMES:
            for fragmento in fragmentos_de_codigo(texto(nombre)):
                if "plugin.json" not in fragmento:      # el bloque de la estructura
                    continue
                padre = ""
                for linea in fragmento.splitlines():
                    if not linea.strip():
                        continue
                    ruta = linea.split()[0]
                    # Las entradas con alternativas (`familia-a|c|d/`) o elipsis no son rutas.
                    if "|" in ruta or "…" in ruta or not re.match(
                            r"^[a-zA-Z0-9._/-]+$", ruta):
                        continue
                    if linea.startswith(" "):
                        # Indentada: cuelga del último directorio de la columna izquierda.
                        ruta = padre + ruta
                    elif ruta.endswith("/"):
                        padre = ruta
                    if "/" not in ruta and "." not in ruta:
                        continue
                    with self.subTest(readme=nombre, ruta=ruta):
                        self.assertTrue((RAIZ / ruta).exists(), "%s no existe" % ruta)


class CifrasTest(unittest.TestCase):
    def test_la_cuenta_de_todos_del_prereg_coincide(self):
        """La cifra está repetida en cuatro documentos; la fuente es una sola."""
        reales = len(re.findall(r"TODO\(Matias\)",
                                (RAIZ / "bench" / "PREREG.md").read_text(encoding="utf-8")))
        patron = re.compile(r"(\d+)\s+`TODO\(Matias\)`")
        vistos = 0
        for nombre in READMES + ("doc/PLAN-M4.md", "doc/HANDOFF.md", "LATER.md"):
            for cifra in patron.findall(texto(nombre)):
                vistos += 1
                with self.subTest(documento=nombre, cifra=cifra):
                    self.assertEqual(int(cifra), reales,
                                     "%s dice %s y el pre-registro tiene %d"
                                     % (nombre, cifra, reales))
        self.assertGreater(vistos, 0, "nadie cita la cuenta: el test no está mirando nada")


class MarcadorDeConjeturasTest(unittest.TestCase):
    """El número que este repo ya publicó mal, y la regla que lo evita.

    El README llegó a decir «seis proyecciones: dos confirmadas, dos refutadas, dos
    abiertas» y **dos de esas cuentas no existían**. La causa no fue descuido: era un
    marcador escrito a mano, en dos idiomas, sin ninguna fuente que lo desmintiera.

    La fuente ahora es el store (`nightshift resolve`). Que el README igual muestre una
    foto es útil, así que la regla no es prohibirla — es que **lleve fecha y que los dos
    idiomas digan lo mismo**, que son las dos formas concretas en que se desincronizó.
    """

    MARCADOR_RE = re.compile(
        r"(\d+)\s+(?:proyectadas|projected)\s*·\s*(\d+)\s+(?:abiertas|open)\s*·\s*"
        r"(\d+)\s+(?:confirmadas|confirmed)\s*·\s*(\d+)\s+(?:refutadas|refuted)")

    def _marcadores(self, nombre):
        return self.MARCADOR_RE.findall(texto(nombre))

    def test_los_dos_readme_dicen_el_mismo_marcador(self):
        cuentas = {nombre: self._marcadores(nombre) for nombre in READMES}
        valores = list(cuentas.values())
        self.assertEqual(valores[0], valores[1],
                         "los dos README publican marcadores distintos: %s" % cuentas)

    def test_el_marcador_lleva_fecha_y_manda_a_correr_el_comando(self):
        """Sin fecha, una foto se lee como el estado de hoy para siempre."""
        for nombre in READMES:
            contenido = texto(nombre)
            for match in self.MARCADOR_RE.finditer(contenido):
                ventana = contenido[max(0, match.start() - 200):match.end() + 200]
                with self.subTest(readme=nombre):
                    self.assertRegex(ventana, r"20\d\d-\d\d-\d\d",
                                     "el marcador no dice de cuándo es")
                    self.assertIn("nightshift resolve", ventana,
                                  "el marcador no manda a la fuente que lo calcula")


class CuentaDeHipotesisTest(unittest.TestCase):
    """La cuenta de hipótesis que publican los documentos coincide con los archivos.

    Existe porque este repo ya se equivocó así dos veces con un número escrito a mano: el
    marcador de proyecciones publicado en dos idiomas se desincronizó, y el 2026-08-28 el
    conteo de hipótesis quedó viejo en tres documentos el mismo día en que se agregaron dos
    archivos. Un número copiado envejece; uno derivado, no.

    Se comprueba el **total**, que es lo que se puede derivar sin correr nada. Cuántas
    pasan no se testea acá: eso lo dice `make experiments`, que es a donde los documentos
    mandan.
    """

    DOCS = ("README.md", "README.es.md", "doc/HANDOFF.md")
    # "**23 hipótesis**" / "**23 hypotheses**", en negrita para no atrapar una cifra suelta
    # de prosa.
    CUENTA_RE = re.compile(r"\*\*(\d+) (?:hipótesis|hypotheses)\*\*")

    def test_la_cuenta_publicada_coincide_con_los_archivos(self):
        reales = len([p for p in (RAIZ / "experimentos" / "hipotesis").glob("H*.py")
                      if not p.name.startswith("_")])
        self.assertTrue(reales, "no se encontró ninguna hipótesis: cambió la convención")
        vistas = 0
        for nombre in self.DOCS:
            for match in self.CUENTA_RE.finditer(texto(nombre)):
                vistas += 1
                with self.subTest(doc=nombre):
                    self.assertEqual(int(match.group(1)), reales,
                                     "%s publica %s hipótesis y hay %d archivos"
                                     % (nombre, match.group(1), reales))
        self.assertTrue(vistas, "ningún documento publica la cuenta: se perdió el marcador")


class AfirmacionesTest(unittest.TestCase):
    def test_ninguna_afirmacion_caducada_sigue_en_pie(self):
        for condicion, prohibida, motivo in AFIRMACIONES_QUE_CADUCAN:
            if not condicion():
                continue                      # el default cambió: la frase puede volver
            for nombre in READMES:
                encontrada = prohibida.search(texto(nombre))
                with self.subTest(readme=nombre, motivo=motivo):
                    self.assertIsNone(encontrada,
                                      "%s dice «%s», y %s" % (
                                          nombre,
                                          encontrada.group(0) if encontrada else "",
                                          motivo))

    def test_el_encabezado_de_estado_coincide_con_la_version(self):
        from nightshift import __version__

        milestone = re.search(r"-M(\d)", __version__).group(1)
        for nombre in READMES:
            linea = next(l for l in texto(nombre).splitlines()
                         if l.startswith("> **Estado:") or l.startswith("> **Status:"))
            with self.subTest(readme=nombre):
                self.assertIn("M%s" % milestone, linea,
                              "el encabezado dice otra cosa que `__version__` (%s)"
                              % __version__)

    def test_ningun_milestone_esta_en_verde_con_su_gate_abierto(self):
        """El ✅ y el texto de la misma fila no pueden decir cosas distintas.

        M0 estuvo marcado ✅ mientras su propia celda decía que la revisión de ADR-001
        seguía pendiente — y `LATER.md` tiene una sección titulada "se pasó de M0 sin
        cerrar su gate". Un badge que contradice a su propio texto es peor que no tener
        badge: el badge se lee y el texto no.
        """
        pendiente = re.compile(
            r"(?i)pendiente|pending|still needs|le faltan|falta[n]? |refuses to run|"
            r"no puede correr|se niega a correr|TODO\(Matias\)|is Matías's to run|"
            r"lo corre Matías")
        for nombre in READMES:
            for linea in texto(nombre).splitlines():
                if not linea.startswith("| M") or "✅" not in linea:
                    continue
                # El ✅ del milestone es el de la primera celda; los de las otras marcan
                # entregables sueltos y no el milestone entero.
                celdas = [c.strip() for c in linea.strip("|").split("|")]
                if len(celdas) < 3 or "✅" not in celdas[0]:
                    continue
                with self.subTest(readme=nombre, fila=celdas[0]):
                    self.assertIsNone(pendiente.search(celdas[2]),
                                      "%s está en verde y su gate dice: %s"
                                      % (celdas[0], celdas[2][:90]))

    def test_la_licencia_que_declara_el_readme_es_la_del_repo(self):
        """Los dos READMEs decían MIT y el archivo es Apache 2.0.

        Es el tipo de dato que nadie vuelve a mirar después de escribirlo una vez, y el
        único del README que tiene consecuencias legales para quien lo use. La fuente es
        `LICENSE`; el README no puede decir otra cosa.
        """
        licencia = (RAIZ / "LICENSE").read_text(encoding="utf-8")
        familia = ("Apache License" in licencia and "Version 2.0" in licencia
                   and "Apache 2.0" or None)
        self.assertIsNotNone(familia, "no se reconoce la licencia de `LICENSE`")
        for nombre in READMES:
            contenido = texto(nombre)
            with self.subTest(readme=nombre):
                self.assertIn(familia, contenido,
                              "%s no declara la licencia del repo (%s)"
                              % (nombre, familia))
                for otra in ("MIT", "GPL", "BSD"):
                    self.assertNotIn(otra, contenido,
                                     "%s nombra %s y la licencia es %s"
                                     % (nombre, otra, familia))

    def test_el_readme_sigue_diciendo_que_nada_esta_verificado(self):
        """Mientras `verify` no exista, decir lo contrario sería el peor error del repo."""
        from nightshift import store

        conn = store.connect()
        try:
            procedimientos = conn.execute(
                "SELECT COUNT(*) c FROM trajectories WHERE status = 'procedure'"
            ).fetchone()["c"]
        finally:
            conn.close()
        self.assertEqual(procedimientos, 0, "algo llegó a `procedure` sin que exista verify")
        for nombre in READMES:
            with self.subTest(readme=nombre):
                contenido = texto(nombre)
                self.assertTrue(
                    "reaches `procedure`" in contenido
                    or "llega a `procedure`" in contenido,
                    "el README tiene que seguir diciendo que nada está verificado")


if __name__ == "__main__":
    unittest.main()
