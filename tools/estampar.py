#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
estampar.py — Arma las partes repetidas del sitio de la CADH.

Lo corre GitHub Actions solo, cada vez que hay un push (workflow "Estampar sitio")
y después de publicar un artículo programado. No hace falta correrlo a mano.

Hace dos cosas:

  1. NAVBAR Y FOOTER
     Copia partials/nav.html y partials/footer.html en todas las páginas, entre
     las marcas <!-- CADH:NAV --> ... <!-- /CADH:NAV --> y
     <!-- CADH:FOOTER --> ... <!-- /CADH:FOOTER -->.
     - Corrige los links para las páginas que están en carpetas (les agrega "../").
     - Marca con class="active" el link de la página actual.
     - Si una página todavía no tiene las marcas (por ejemplo, un artículo nuevo),
       las agrega solo alrededor de su <header class="nav"> y <footer class="footer">.

  2. ÍNDICE DE ARTÍCULOS
     Lee todos los articulos/*.html y arma el listado de cards, del más nuevo al
     más viejo, con paginación: articulos/index.html, articulos/pagina-2.html, …
     De cada artículo toma: título (h1), etiqueta, bajada (meta "cadh-bajada" o,
     si no hay, la meta description), autor, fecha (datePublished), minutos de
     lectura y el texto alternativo de la imagen.
     Los artículos con "noindex" (pruebas, borradores) no aparecen.

Solo usa la librería estándar de Python 3.9+.

Uso:
  python3 tools/estampar.py              (estampa el sitio en la carpeta actual)
  python3 tools/estampar.py --sitio RUTA
  python3 tools/estampar.py --revisar    (no cambia nada; avisa si algo está desactualizado)
"""
import argparse
import html
import os
import posixpath
import re
import sys
from pathlib import Path

# Cuántas cards normales por página. La primera página suma además el
# "Último artículo" destacado arriba, a todo el ancho.
# 8 = dos filas completas de 4 en compu (el grid entra 4 por fila en 1100 px).
POR_PAGINA = 8

SITIO_URL = "https://www.cadh-hema.com.ar"
MESES_CORTOS = ["ene", "feb", "mar", "abr", "may", "jun", "jul", "ago",
                "sep", "oct", "nov", "dic"]

# Páginas con diseño propio, que no llevan el navbar/footer del sitio.
EXCLUIDAS = {"links.html"}

MARCAS = {
    "NAV": ("<!-- CADH:NAV · se genera solo desde partials/nav.html: no editar acá -->",
            "<!-- /CADH:NAV -->"),
    "FOOTER": ("<!-- CADH:FOOTER · se genera solo desde partials/footer.html: no editar acá -->",
               "<!-- /CADH:FOOTER -->"),
    "LISTADO": ("<!-- CADH:LISTADO · se genera solo con los artículos de esta carpeta: no editar acá -->",
                "<!-- /CADH:LISTADO -->"),
}
# Para detectar las páginas que todavía no tienen marcas.
BLOQUE_SUELTO = {
    "NAV": re.compile(r"^([ \t]*)<header class=\"nav\">.*?</header>[ \t]*$", re.S | re.M),
    "FOOTER": re.compile(r"^([ \t]*)<footer class=\"footer\">.*?</footer>[ \t]*$", re.S | re.M),
}


def patron_marcas(nombre):
    return re.compile(r"^([ \t]*)<!-- CADH:" + nombre + r"\b.*?-->.*?<!-- /CADH:" + nombre + r" -->",
                      re.S | re.M)


# ------------------------------------------------------------ partials

def leer_partial(ruta):
    """El contenido del partial sin el comentario de ayuda del principio."""
    texto = ruta.read_text(encoding="utf-8")
    texto = re.sub(r"^\s*<!--.*?-->\s*", "", texto, count=1, flags=re.S)
    return texto.strip("\n")


def es_relativo(url):
    return not re.match(r"^(?:[a-z][a-z0-9+.-]*:|//|#|/)", url, re.I)


def ajustar_links(fragmento, carpeta):
    """Reescribe href/src relativos (escritos desde la raíz) para una página en `carpeta`."""
    if not carpeta:
        return fragmento

    def cambiar(m):
        url = m.group(2)
        if not es_relativo(url):
            return m.group(0)
        return f'{m.group(1)}="{posixpath.relpath(url, carpeta)}"'
    return re.sub(r'\b(href|src)="([^"]*)"', cambiar, fragmento)


def destino_activo(pagina):
    """A qué link del menú corresponde la página (ruta desde la raíz), o None."""
    if pagina.startswith("articulos/"):
        return "articulos/index.html"
    if pagina == "index.html":
        return None  # "Inicio" no se resalta (así estaba el diseño original)
    return pagina


def marcar_activo(fragmento, pagina):
    """Agrega class="active" a los links que van a la página actual y al botón
    del desplegable que los contiene."""
    objetivo = destino_activo(pagina)
    if not objetivo:
        return fragmento
    carpeta = posixpath.dirname(pagina)
    href_obj = posixpath.relpath(objetivo, carpeta) if carpeta else objetivo

    def cambiar(m):
        etiqueta = m.group(0)
        if f'href="{href_obj}"' not in etiqueta or "nav-logo" in etiqueta:
            return etiqueta
        if re.search(r'\bclass="', etiqueta):
            return re.sub(r'\bclass="([^"]*)"', lambda c: f'class="{c.group(1)} active"', etiqueta, count=1)
        return etiqueta[:-1] + ' class="active">'
    fragmento = re.sub(r"<a\b[^>]*>", cambiar, fragmento)

    # El botón "Eventos" se marca si alguno de sus links está activo.
    def desplegable(m):
        bloque = m.group(0)
        menu = re.search(r'<ul class="nav-dropdown-menu">.*?</ul>', bloque, re.S)
        if menu and 'class="active"' in menu.group(0):
            bloque = bloque.replace('class="nav-dropdown-toggle"', 'class="nav-dropdown-toggle active"', 1)
        return bloque
    return re.sub(r'<li class="nav-dropdown">.*?</ul>\s*</li>', desplegable, fragmento, flags=re.S)


def sangrar(fragmento, sangria):
    return "\n".join((sangria + linea) if linea.strip() else "" for linea in fragmento.split("\n"))


def poner_bloque(texto, nombre, contenido):
    """Reemplaza lo que hay entre las marcas `nombre`. Si no hay marcas, las crea
    alrededor del bloque suelto (header/footer). Devuelve (texto, ok)."""
    pm = patron_marcas(nombre)
    m = pm.search(texto)
    if m:
        s = m.group(1)
        inicio, fin = MARCAS[nombre]
        nuevo = f"{s}{inicio}\n{sangrar(contenido, s)}\n{s}{fin}"
        return texto[:m.start()] + nuevo + texto[m.end():], True
    suelto = BLOQUE_SUELTO.get(nombre)
    m = suelto.search(texto) if suelto else None
    if m:
        s = m.group(1)
        inicio, fin = MARCAS[nombre]
        nuevo = f"{s}{inicio}\n{sangrar(contenido, s)}\n{s}{fin}"
        return texto[:m.start()] + nuevo + texto[m.end():], True
    return texto, False


def paginas_del_sitio(sitio):
    for ruta in sorted(sitio.rglob("*.html")):
        rel = ruta.relative_to(sitio).as_posix()
        if rel.split("/")[0] in ("partials", "_programados", "node_modules") or rel.startswith("."):
            continue
        if rel in EXCLUIDAS:
            continue
        yield rel, ruta


# ------------------------------------------------------------ artículos

def buscar(patron, texto):
    r = re.search(patron, texto, re.S)
    return r.group(1).strip() if r else None


def leer_articulos(carpeta):
    arts = []
    for ruta in sorted(carpeta.glob("*.html")):
        if ruta.name == "index.html" or re.match(r"pagina-\d+\.html$", ruta.name):
            continue
        texto = ruta.read_text(encoding="utf-8")
        if re.search(r'<meta name="robots" content="[^"]*noindex', texto):
            continue
        fecha = buscar(r'"datePublished":\s*"([^"]*)"', texto)
        titulo = buscar(r"<h1>(.*?)</h1>", texto)
        if not (fecha and titulo):
            print(f"Aviso: {ruta.name} no tiene título (h1) o datePublished; no lo pongo en el índice.")
            continue
        arts.append({
            "slug": ruta.stem,
            "titulo": titulo,
            "fecha": fecha,
            "etiqueta": buscar(r'<p class="section-label">(.*?)</p>', texto) or "",
            "bajada": (buscar(r'<meta name="cadh-bajada" content="([^"]*)"', texto)
                       or buscar(r'<meta name="description" content="([^"]*)"', texto) or ""),
            "autor": buscar(r"Por <strong>(.*?)</strong>", texto) or "Marcos",
            "lectura": buscar(r"(\d+)\s*min de lectura", texto) or "",
            "alt": buscar(r'<img src="\.\./img/articulos/[^"]+"[^>]*?alt="([^"]*)"', texto) or "",
        })
    arts.sort(key=lambda a: (a["fecha"], a["slug"]), reverse=True)
    return arts


def fecha_corta(iso):
    a, m, d = (int(x) for x in iso.split("-"))
    return f"{d} {MESES_CORTOS[m - 1]} {a}"


def card(a):
    lectura = f" · {a['lectura']} min" if a["lectura"] else ""
    return f'''<a class="card" href="{a['slug']}.html">
  <img class="card-img" src="../img/articulos/{a['slug']}.jpg" width="1200" height="630"
       alt="{a['alt']}" loading="lazy"
       onerror="this.style.visibility='hidden'">
  <div class="card-body">
    <p class="section-label">{a['etiqueta']}</p>
    <h2>{a['titulo']}</h2>
    <p>{a['bajada']}</p>
    <p class="card-meta">{a['autor']} · <time datetime="{a['fecha']}">{fecha_corta(a['fecha'])}</time>{lectura}</p>
  </div>
</a>'''


def archivo_pagina(n):
    return "index.html" if n == 1 else f"pagina-{n}.html"


def url_pagina(n):
    return f"{SITIO_URL}/articulos/" if n == 1 else f"{SITIO_URL}/articulos/pagina-{n}.html"


def paginacion(n, total):
    if total <= 1:
        return ""
    partes = []
    if n > 1:
        partes.append(f'<a class="paginacion-flecha" href="{archivo_pagina(n - 1)}" rel="prev">← Más nuevos</a>')
    numeros = []
    for i in range(1, total + 1):
        if i == n:
            numeros.append(f'<span class="paginacion-num actual" aria-current="page">{i}</span>')
        else:
            numeros.append(f'<a class="paginacion-num" href="{archivo_pagina(i)}">{i}</a>')
    partes.append('<span class="paginacion-nums">' + "".join(numeros) + "</span>")
    if n < total:
        partes.append(f'<a class="paginacion-flecha" href="{archivo_pagina(n + 1)}" rel="next">Más viejos →</a>')
    return ('<nav class="paginacion" aria-label="Páginas de artículos">\n  '
            + "\n  ".join(partes) + "\n</nav>")


def armar_listado(arts, n, total):
    if n == 1:
        en_pagina = arts[:POR_PAGINA + 1]          # destacado + POR_PAGINA
        clase = "card-grid"
    else:
        desde = POR_PAGINA + 1 + (n - 2) * POR_PAGINA
        en_pagina = arts[desde:desde + POR_PAGINA]
        clase = "card-grid sin-destacado"
    cards = "\n\n".join(sangrar(card(a), "  ") for a in en_pagina)
    bloque = f'<div class="{clase}">\n\n{cards}\n\n</div>'
    pag = paginacion(n, total)
    return bloque + ("\n" + pag if pag else "")


def ajustar_cabecera_pagina(texto, n, total):
    """Título, canonical y og:url propios de cada página del índice."""
    if n == 1:
        return texto
    sufijo = f" (página {n})"
    texto = re.sub(r"(<title>)(.*?)( — CADH</title>)", lambda m: m.group(1) + m.group(2) + sufijo + m.group(3), texto, count=1)
    texto = re.sub(r'(<meta (?:property="og:title"|name="twitter:title") content=")(.*?)( — CADH")',
                   lambda m: m.group(1) + m.group(2) + sufijo + m.group(3), texto)
    texto = re.sub(r'(<link rel="canonical" href=")[^"]*', lambda m: m.group(1) + url_pagina(n), texto)
    texto = re.sub(r'(<meta property="og:url" content=")[^"]*', lambda m: m.group(1) + url_pagina(n), texto)
    texto = re.sub(r"(<h1>)(.*?)(</h1>)", lambda m: m.group(1) + m.group(2) + f"<span class=\"h1-pagina\">Página {n} de {total}</span>" + m.group(3), texto, count=1)
    return texto


def armar_indice(sitio, cambios):
    carpeta = sitio / "articulos"
    plantilla_ruta = carpeta / "index.html"
    if not plantilla_ruta.exists():
        return
    plantilla = plantilla_ruta.read_text(encoding="utf-8")
    if not patron_marcas("LISTADO").search(plantilla):
        print("Aviso: articulos/index.html no tiene las marcas CADH:LISTADO; no armo el índice.")
        return
    arts = leer_articulos(carpeta)
    resto = max(0, len(arts) - (POR_PAGINA + 1))
    total = 1 + -(-resto // POR_PAGINA)
    for n in range(1, total + 1):
        texto = ajustar_cabecera_pagina(plantilla, n, total)
        texto, _ = poner_bloque(texto, "LISTADO", armar_listado(arts, n, total))
        guardar(carpeta / archivo_pagina(n), texto, cambios)
    # Páginas que sobran (si se borraron artículos)
    for vieja in carpeta.glob("pagina-*.html"):
        m = re.match(r"pagina-(\d+)\.html$", vieja.name)
        if m and int(m.group(1)) > total:
            cambios.append(f"borrada {vieja.relative_to(sitio).as_posix()}")
            if not SOLO_REVISAR:
                vieja.unlink()


# ------------------------------------------------------------ general

SOLO_REVISAR = False


def guardar(ruta, texto, cambios):
    anterior = ruta.read_text(encoding="utf-8") if ruta.exists() else None
    if anterior == texto:
        return
    cambios.append(ruta.as_posix())
    if not SOLO_REVISAR:
        ruta.write_text(texto, encoding="utf-8")


def main():
    global SOLO_REVISAR
    ap = argparse.ArgumentParser(description="Estampa navbar, footer e índice de artículos")
    ap.add_argument("--sitio", default=".", help="carpeta del sitio (por defecto, la actual)")
    ap.add_argument("--revisar", action="store_true", help="no cambia nada; sale con error si algo está desactualizado")
    args = ap.parse_args()
    SOLO_REVISAR = args.revisar
    sitio = Path(args.sitio).resolve()

    nav = leer_partial(sitio / "partials" / "nav.html")
    footer = leer_partial(sitio / "partials" / "footer.html")
    cambios = []

    # 1. Índice de artículos primero (sus páginas nuevas también llevan nav/footer).
    armar_indice(sitio, cambios)

    # 2. Navbar y footer en todas las páginas.
    for rel, ruta in paginas_del_sitio(sitio):
        texto = ruta.read_text(encoding="utf-8")
        carpeta = posixpath.dirname(rel)
        texto, ok_nav = poner_bloque(texto, "NAV", marcar_activo(ajustar_links(nav, carpeta), rel))
        texto, ok_footer = poner_bloque(texto, "FOOTER", ajustar_links(footer, carpeta))
        if not (ok_nav or ok_footer):
            continue  # página sin navbar ni footer del sitio (pruebas, etc.)
        guardar(ruta, texto, cambios)

    rel = lambda c: os.path.relpath(c, sitio) if c.startswith("/") else c
    if cambios:
        print(("Desactualizado:" if SOLO_REVISAR else "Actualizado:") + "\n  " + "\n  ".join(rel(c) for c in cambios))
    else:
        print("Todo al día: nada para cambiar.")
    if SOLO_REVISAR and cambios:
        sys.exit(1)


if __name__ == "__main__":
    main()
