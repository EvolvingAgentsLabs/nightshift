"""Los límites del servicio.

Estos tres números son **política**, no perillas. Cada uno se subió una vez para tapar un
síntoma, y cada vez el problema volvió con otro tamaño. `tests/test_politica.py` los
defiende: si el arreglo de un bug pasa por cambiar uno de estos valores, el arreglo está
tapando algo.
"""

TIMEOUT_SEGUNDOS = 2
MAX_REINTENTOS = 3
CACHE_TTL_SEGUNDOS = 60
