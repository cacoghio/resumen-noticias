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


def sin_tildes(texto: str) -> str:
    texto = unicodedata.normalize("NFKD", texto.lower())
    return "".join(c for c in texto if not unicodedata.combining(c)).strip()


def medio_base(medio: str) -> str:
    texto = sin_tildes(medio)
    return ALIAS_MEDIOS.get(texto, texto)


@dataclass
class Noticia:
    medio: str
    seccion: str  # pista de la fuente: claude_code | anthropic | competencia | voces
    titulo: str
    resumen: str
    link: str
    fecha: datetime | None
    tipo: str = "articulo"  # articulo | video | comunidad | blog | release
    personas: list[str] = field(default_factory=list)
    grupo: str | None = None  # notas que Google News ya agrupó como la misma historia
    version: str = ""  # solo releases de Claude Code


@dataclass
class Cluster:
    id: str
    noticias: list[Noticia] = field(default_factory=list)

    @property
    def cobertura(self) -> int:
        return len({medio_base(n.medio) for n in self.noticias})

    @property
    def tipos(self) -> set[str]:
        return {n.tipo for n in self.noticias}

    @property
    def personas(self) -> list[str]:
        vistas: list[str] = []
        for n in self.noticias:
            for p in n.personas:
                if p not in vistas:
                    vistas.append(p)
        return vistas

    @property
    def secciones(self) -> set[str]:
        return {n.seccion for n in self.noticias}

    @property
    def peso(self) -> int:
        """Para ordenar candidatos: releases > voces/Claude/Anthropic > resto."""
        if "release" in self.tipos:
            return 2
        if self.personas or self.secciones & {"claude_code", "anthropic", "voces"}:
            return 1
        return 0

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
