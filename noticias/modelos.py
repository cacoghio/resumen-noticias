import unicodedata
from dataclasses import dataclass, field
from datetime import datetime


ALIAS_MEDIOS = {
    "bbc mundo": "bbc",
    "el pais america": "el pais",
    "opinion - cooperativa": "cooperativa",
    "teletrece": "canal 13",
    "t13": "canal 13",
}


def medio_base(medio: str) -> str:
    texto = unicodedata.normalize("NFKD", medio.lower())
    texto = "".join(c for c in texto if not unicodedata.combining(c)).strip()
    return ALIAS_MEDIOS.get(texto, texto)


@dataclass
class Noticia:
    medio: str
    ambito: str  # chile | mundo | mixto
    titulo: str
    resumen: str
    link: str
    fecha: datetime | None
    portada: bool = False
    grupo: str | None = None  # notas que Google News ya agrupó como la misma historia


@dataclass
class Cluster:
    id: str
    noticias: list[Noticia] = field(default_factory=list)

    @property
    def cobertura(self) -> int:
        return len({medio_base(n.medio) for n in self.noticias})

    @property
    def portada(self) -> bool:
        return any(n.portada for n in self.noticias)

    @property
    def principal(self) -> Noticia:
        # La nota con más resumen suele ser la más informativa
        return max(self.noticias, key=lambda n: len(n.resumen))

    @property
    def fecha(self) -> datetime | None:
        fechas = [n.fecha for n in self.noticias if n.fecha]
        return max(fechas) if fechas else None

    @property
    def links(self) -> set[str]:
        return {n.link for n in self.noticias}
