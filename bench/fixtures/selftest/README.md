# Fixture sintético del selftest del runner

**Esto no es un fixture del benchmark de M4.** Los repos fixture de las familias A y C
son `TODO(Matias)` en [`../../PREREG.md`](../../PREREG.md) y los define una persona.

Lo de acá existe para una sola cosa: probar que el **runner** funciona de punta a punta
—matriz, ejecución, gate, resumen, reporte y regla de decisión— sin depender de que el
pre-registro esté congelado ni de que exista un agente real.

El "agente" es `agent.sh`, un script que simula resolver el bug. No es Claude Code, no
mide nada de nightshift, y sus números **no significan nada** fuera del selftest. Si
alguna vez ves estos números en un reporte de M4, el reporte está mal.
