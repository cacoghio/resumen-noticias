"""Agrupa en clusters las notas que cuentan la misma historia."""
import re
import unicodedata

from .modelos import Cluster, Noticia

PALABRAS_VACIAS = set("""
a al ante bajo con contra de del desde durante e el en entre es esta este esto hacia hasta la las
le les lo los mas mas no o para pero por que se sin sobre su sus tras un una unos unas y ya
como cual cuando donde fue han hay ha ser son sera tiene tienen otra otro muy tras segun
the of and to in for on with is at by
""".split())

UMBRAL = 0.45


def normalizar(titulo: str) -> set[str]:
    texto = unicodedata.normalize("NFKD", titulo.lower())
    texto = "".join(c for c in texto if not unicodedata.combining(c))
    palabras = re.findall(r"[a-z0-9]+", texto)
    return {p for p in palabras if p not in PALABRAS_VACIAS and (len(p) > 2 or p.isdigit())}


def _parecido(a: set[str], b: set[str]) -> float:
    if not a or not b:
        return 0.0
    comunes = len(a & b)
    jaccard = comunes / len(a | b)
    # Un título corto casi contenido en uno largo también es la misma historia
    contencion = comunes / min(len(a), len(b)) if min(len(a), len(b)) >= 4 else 0.0
    return max(jaccard, contencion * 0.8)


def similitud(a: str, b: str) -> float:
    return _parecido(normalizar(a), normalizar(b))


def agrupar(noticias: list[Noticia], umbral: float = UMBRAL) -> list[Cluster]:
    grupos: list[tuple[list[set[str]], list[Noticia]]] = []
    por_grupo: dict[str, int] = {}
    # Primero las notas que Google News ya agrupó, para que las sueltas se unan a ellas
    ordenadas = sorted(noticias, key=lambda n: n.grupo is None)
    for nota in ordenadas:
        palabras = normalizar(nota.titulo)
        destino = por_grupo.get(nota.grupo) if nota.grupo else None
        if destino is None:
            destino = next(
                (i for i, (firmas, _) in enumerate(grupos)
                 if any(_parecido(palabras, f) >= umbral for f in firmas)),
                None,
            )
        if destino is None:
            grupos.append(([palabras], [nota]))
            destino = len(grupos) - 1
        else:
            grupos[destino][0].append(palabras)
            grupos[destino][1].append(nota)
        if nota.grupo:
            por_grupo.setdefault(nota.grupo, destino)

    clusters = [Cluster(id="", noticias=notas) for _, notas in grupos]
    clusters.sort(
        key=lambda c: (c.cobertura, c.portada, c.fecha.timestamp() if c.fecha else 0),
        reverse=True,
    )
    for i, c in enumerate(clusters, start=1):
        c.id = f"c{i:03d}"
    return clusters
