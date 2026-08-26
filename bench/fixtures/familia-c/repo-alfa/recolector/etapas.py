def escalar(lectura):
    return {"sensor": lectura["sensor"], "magnitud": lectura["magnitud"] * 10}


def redondear(lectura):
    return {"sensor": lectura["sensor"], "magnitud": round(lectura["magnitud"], 2)}


def rotular(lectura):
    return {"sensor": lectura["sensor"].upper(), "magnitud": lectura["magnitud"]}
