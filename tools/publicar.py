#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
publicar.py — Publicación programada de artículos de la CADH.

Lee los artículos que esperan en el repo privado (carpeta "programados/") y, cuando
llega la hora indicada en cada uno, los publica en el sitio:

  1. copia el artículo a articulos/<slug>.html y la imagen a img/articulos/<slug>.jpg
  2. pone la fecha de publicación (la programada) en el texto, en los metadatos
     y en el JSON-LD
  3. agrega la card arriba de todo en articulos/index.html
  4. agrega al sitemap.xml las URLs que falten (/articulos/ y cada artículo)
  5. pone el artículo en el botón "Último artículo" de links.html (bio de Instagram)

Solo usa la librería estándar de Python 3.9+.

Uso:
  python3 tools/publicar.py --origen RUTA_REPO_PRIVADO --destino RUTA_SITIO
  python3 tools/publicar.py --origen RUTA_REPO_PRIVADO --validar
  python3 tools/publicar.py --origen ... --destino ... --ahora "2026-10-25 14:40"   (pruebas)

Una página de prueba lleva "prueba: si" en el bloque CADH-PROGRAMADO: se publica
tal cual (sin imagen, sin card en el índice y sin sitemap) para verificar que la
cadena automática funciona. Debe incluir <meta name="robots" content="noindex">.

Un artículo cuenta como "ya publicado" si existe articulos/<slug>.html en el sitio,
así que correr el script dos veces no duplica nada.

Ojo: en modo publicación este script se ejecuta en un repo público y sus mensajes
quedan en un log público. Por eso, mientras un artículo no sale, NO imprime
su nombre ni su contenido.
"""
import argparse
import html
import os
import re
import shutil
import sys
from datetime import datetime
from html.parser import HTMLParser
from pathlib import Path
from zoneinfo import ZoneInfo

TZ = ZoneInfo("America/Argentina/Buenos_Aires")
SITIO = "https://www.cadh-hema.com.ar"
MESES = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio",
         "agosto", "septiembre", "octubre", "noviembre", "diciembre"]
MESES_CORTOS = ["ene", "feb", "mar", "abr", "may", "jun", "jul", "ago",
                "sep", "oct", "nov", "dic"]
SLUG_OK = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
BLOQUE = re.compile(r"<!--\s*CADH-PROGRAMADO\b(.*?)-->[ \t]*\n?", re.S)
VOID = {"meta", "link", "img", "br", "input", "hr", "source", "area", "base", "col", "wbr"}


# ---------------------------------------------------------------- lectura

def leer_articulo(ruta):
    """Devuelve un dict con todo lo que hace falta saber de un artículo programado."""
    texto = ruta.read_text(encoding="utf-8")
    meta = {}
    m = BLOQUE.search(texto)
    if m:
        for linea in m.group(1).splitlines():
            if ":" in linea:
                clave, valor = linea.split(":", 1)
                meta[clave.strip().lower()] = valor.strip()
    limpio = BLOQUE.sub("", texto, count=1)

    def buscar(patron, flags=re.S):
        r = re.search(patron, limpio, flags)
        return r.group(1).strip() if r else None

    art = {
        "ruta": ruta,
        "slug": ruta.stem,
        "texto": limpio,
        "meta": meta,
        "prueba": meta.get("prueba", "").strip().lower() in ("si", "sí", "true", "1"),
        "cuando": None,
        "titulo": buscar(r"<h1>(.*?)</h1>"),
        "etiqueta": buscar(r'<p class="section-label">(.*?)</p>'),
        "lectura": buscar(r"(\d+)\s*min de lectura"),
        "autor": buscar(r"Por <strong>(.*?)</strong>") or "Marcos",
        "descripcion": buscar(r'<meta name="description" content="([^"]*)"'),
        "alt": buscar(r'<img src="\.\./img/articulos/[^"]+"[^>]*?alt="([^"]*)"'),
        "canonical": buscar(r'<link rel="canonical" href="([^"]*)"'),
    }
    try:
        art["cuando"] = datetime.strptime(meta["publicar"], "%Y-%m-%d %H:%M").replace(tzinfo=TZ)
    except (KeyError, ValueError):
        pass
    return art


def cargar_programados(origen):
    carpeta = Path(origen) / "programados"
    return [leer_articulo(r) for r in sorted(carpeta.glob("*.html"))]


# ------------------------------------------------------------- validación

class _Balance(HTMLParser):
    def __init__(self):
        super().__init__()
        self.pila, self.mal = [], []

    def handle_starttag(self, tag, attrs):
        if tag not in VOID:
            self.pila.append(tag)

    def handle_endtag(self, tag):
        if tag in VOID:
            return
        if self.pila and self.pila[-1] == tag:
            self.pila.pop()
        else:
            self.mal.append(tag)


def validar(art, origen):
    """Lista de problemas que impedirían publicar bien. Vacía = todo en orden."""
    p = []
    slug = art["slug"]
    if not SLUG_OK.match(slug):
        p.append("el nombre del archivo debe ser solo minúsculas, números y guiones (ej: tratados-de-hema.html)")
    if art["cuando"] is None:
        p.append('falta o está mal la línea "publicar: AAAA-MM-DD HH:MM" en el bloque CADH-PROGRAMADO del principio')
    if art["prueba"]:
        return p  # las páginas de prueba no llevan imagen, card ni metadatos
    esperado = f"{SITIO}/articulos/{slug}.html"
    if art["canonical"] != esperado:
        p.append(f"el canonical debería ser {esperado} (hoy: {art['canonical']})")
    for campo, nombre in (("titulo", "el título (h1)"), ("etiqueta", 'la etiqueta (class="section-label")'),
                          ("lectura", 'el tiempo de lectura ("N min de lectura")'),
                          ("descripcion", "la meta description")):
        if not art[campo]:
            p.append(f"no encuentro {nombre}")
    if "Publicado el <time" not in art["texto"]:
        p.append('falta la fecha visible ("Publicado el <time ...>")')
    for clave in ('"datePublished"', '"dateModified"', 'article:published_time'):
        if clave not in art["texto"]:
            p.append(f"falta {clave} en los metadatos")
    if not art["alt"] or "[Descripción" in art["alt"]:
        p.append("la imagen destacada todavía tiene el texto alternativo de ejemplo: escribí una descripción real")
    imagen = Path(origen) / "img" / f"{slug}.jpg"
    if not imagen.exists():
        p.append(f"falta la imagen img/{slug}.jpg (1200×630)")
    elif imagen.stat().st_size > 400 * 1024:
        p.append(f"la imagen img/{slug}.jpg pesa {imagen.stat().st_size // 1024} KB: conviene que sea ≤ 300 KB")
    b = _Balance()
    b.feed(art["texto"])
    if b.pila or b.mal:
        p.append(f"el HTML tiene etiquetas sin cerrar o mal anidadas (sin cerrar: {b.pila}, sobran: {b.mal})")
    return p


# ------------------------------------------------------------ publicación

def fecha_larga(c):
    return f"{c.day} de {MESES[c.month - 1]} de {c.year}"


def fecha_corta(c):
    return f"{c.day} {MESES_CORTOS[c.month - 1]} {c.year}"


def estampar_fecha(texto, c):
    iso = c.strftime("%Y-%m-%d")
    texto = re.sub(r'(<meta property="article:published_time" content=")[^"]*',
                   lambda m: m.group(1) + iso, texto)
    texto = re.sub(r'("datePublished":\s*")[^"]*', lambda m: m.group(1) + iso, texto)
    texto = re.sub(r'("dateModified":\s*")[^"]*', lambda m: m.group(1) + iso, texto)
    texto = re.sub(r'(Publicado el <time datetime=")[^"]*(">)[^<]*(</time>)',
                   lambda m: m.group(1) + iso + m.group(2) + fecha_larga(c) + m.group(3), texto)
    return texto


def tarjeta(art, c):
    bajada = art["meta"].get("bajada") or art["descripcion"] or ""
    bajada = html.escape(bajada, quote=False) if art["meta"].get("bajada") else bajada
    slug = art["slug"]
    return f'''      <a class="card" href="{slug}.html">
        <img class="card-img" src="../img/articulos/{slug}.jpg" width="1200" height="630"
             alt="{art['alt']}" loading="lazy"
             onerror="this.style.visibility='hidden'">
        <div class="card-body">
          <p class="section-label">{art['etiqueta']}</p>
          <h2>{art['titulo']}</h2>
          <p>{bajada}</p>
          <p class="card-meta">{art['autor']} · <time datetime="{c.strftime('%Y-%m-%d')}">{fecha_corta(c)}</time> · {art['lectura']} min</p>
        </div>
      </a>'''


def agregar_tarjeta(destino, art, c):
    ruta = Path(destino) / "articulos" / "index.html"
    idx = ruta.read_text(encoding="utf-8")
    m = re.search(r'<div class="card-grid">\n', idx)
    if not m:
        raise SystemExit('articulos/index.html no tiene <div class="card-grid">: no puedo agregar la card')
    idx = idx[:m.end()] + "\n" + tarjeta(art, c) + "\n" + idx[m.end():]
    ruta.write_text(idx, encoding="utf-8")


def _entrada_sitemap(url, fecha, freq, prioridad):
    return (f"  <url>\n    <loc>{url}</loc>\n    <lastmod>{fecha}</lastmod>\n"
            f"    <changefreq>{freq}</changefreq>\n    <priority>{prioridad}</priority>\n  </url>\n\n")


def sincronizar_sitemap(destino, ultima_fecha):
    """Agrega al sitemap /articulos/ y cada artículo publicado que falte."""
    ruta = Path(destino) / "sitemap.xml"
    xml = ruta.read_text(encoding="utf-8")
    nuevas = ""
    url_idx = f"{SITIO}/articulos/"
    if f"<loc>{url_idx}</loc>" in xml:
        xml = re.sub(r"(<loc>" + re.escape(url_idx) + r"</loc>\s*<lastmod>)[^<]*",
                     lambda m: m.group(1) + ultima_fecha, xml)
    else:
        nuevas += _entrada_sitemap(url_idx, ultima_fecha, "weekly", "0.7")
    for f in sorted((Path(destino) / "articulos").glob("*.html")):
        if f.name == "index.html":
            continue
        url = f"{SITIO}/articulos/{f.name}"
        if f"<loc>{url}</loc>" in xml:
            continue
        contenido = f.read_text(encoding="utf-8")
        if "noindex" in contenido:
            continue  # páginas de prueba u ocultas: no van al sitemap
        m = re.search(r'"datePublished":\s*"([^"]*)"', contenido)
        nuevas += _entrada_sitemap(url, m.group(1) if m else ultima_fecha, "monthly", "0.6")
    if nuevas:
        xml = xml.replace("</urlset>", nuevas + "</urlset>")
    ruta.write_text(xml, encoding="utf-8")


def actualizar_links(destino, art):
    """Pone el artículo recién publicado en el botón "Último artículo" de links.html
    (la página de la bio de Instagram). Reemplaza lo que hay entre los comentarios
    ULTIMO-ARTICULO:INICIO y ULTIMO-ARTICULO:FIN. Si la página o las marcas no
    están, avisa y sigue: no es motivo para frenar la publicación."""
    ruta = Path(destino) / "links.html"
    if not ruta.exists():
        print("Aviso: no existe links.html; no actualizo el último artículo.")
        return False
    pagina = ruta.read_text(encoding="utf-8")
    marcas = re.compile(r"(<!-- ULTIMO-ARTICULO:INICIO -->\n).*?(\n[ \t]*<!-- ULTIMO-ARTICULO:FIN -->)", re.S)
    if not marcas.search(pagina):
        print("Aviso: links.html no tiene las marcas ULTIMO-ARTICULO; no actualizo el último artículo.")
        return False
    slug = art["slug"]
    bloque = f'''    <a class="link link-article" href="articulos/{slug}.html">
      <img class="link-thumb" src="img/articulos/{slug}.jpg" alt="" width="88" height="58" loading="lazy" onerror="this.style.visibility='hidden'">
      <span>
        <span class="link-label">Último artículo</span>
        <span class="link-title">{art['titulo']}</span>
      </span>
      <svg class="link-arrow" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M9 6l6 6-6 6"/></svg>
    </a>'''
    ruta.write_text(marcas.sub(lambda m: m.group(1) + bloque + m.group(2), pagina, count=1), encoding="utf-8")
    return True


def publicar_articulo(art, origen, destino):
    c = art["cuando"]
    slug = art["slug"]
    destino = Path(destino)
    (destino / "articulos").mkdir(exist_ok=True)
    (destino / "img" / "articulos").mkdir(parents=True, exist_ok=True)
    (destino / "articulos" / f"{slug}.html").write_text(estampar_fecha(art["texto"], c), encoding="utf-8")
    imagen = Path(origen) / "img" / f"{slug}.jpg"
    if imagen.exists():
        shutil.copyfile(imagen, destino / "img" / "articulos" / f"{slug}.jpg")
    if not art["prueba"]:
        agregar_tarjeta(destino, art, c)


def salida_github(**pares):
    ruta = os.environ.get("GITHUB_OUTPUT")
    if ruta:
        with open(ruta, "a", encoding="utf-8") as f:
            for k, v in pares.items():
                f.write(f"{k}={v}\n")


# ------------------------------------------------------------------- main

def main():
    ap = argparse.ArgumentParser(description="Publicación programada de artículos de la CADH")
    ap.add_argument("--origen", required=True, help="carpeta del repo privado (la que contiene programados/)")
    ap.add_argument("--destino", default=".", help="carpeta del sitio (por defecto, la actual)")
    ap.add_argument("--validar", action="store_true", help="solo revisar los programados, sin publicar")
    ap.add_argument("--ahora", help='hora simulada "AAAA-MM-DD HH:MM" (hora de Argentina), para pruebas')
    args = ap.parse_args()

    arts = cargar_programados(args.origen)

    if args.validar:
        hubo_error = False
        for a in arts:
            problemas = validar(a, args.origen)
            cuando = a["cuando"].strftime("%d/%m/%Y %H:%M") if a["cuando"] else "SIN FECHA"
            if problemas:
                hubo_error = True
                print(f"✗ {a['slug']}.html (sale: {cuando})")
                for x in problemas:
                    print(f"    - {x}")
            else:
                print(f"✓ {a['slug']}.html (sale: {cuando})")
        if not arts:
            print("No hay artículos en programados/.")
        sys.exit(1 if hubo_error else 0)

    ahora = (datetime.strptime(args.ahora, "%Y-%m-%d %H:%M").replace(tzinfo=TZ)
             if args.ahora else datetime.now(TZ))
    destino = Path(args.destino)

    # Sin imprimir nada identificable de lo que todavía no salió.
    sin_fecha = [a for a in arts if a["cuando"] is None]
    if sin_fecha:
        print(f"Aviso: hay {len(sin_fecha)} archivo(s) programado(s) sin fecha válida; se ignoran.")
    pendientes = [a for a in arts
                  if a["cuando"] is not None
                  and a["cuando"] <= ahora
                  and SLUG_OK.match(a["slug"])
                  and not (destino / "articulos" / f"{a['slug']}.html").exists()]
    pendientes.sort(key=lambda a: a["cuando"])  # el más nuevo queda arriba del índice

    if not pendientes:
        print("Nada para publicar.")
        salida_github(publicado="false")
        return

    publicados = []
    for a in pendientes:
        for x in validar(a, args.origen):
            print(f"Aviso ({a['slug']}): {x}")
        publicar_articulo(a, args.origen, destino)
        publicados.append(a)
        print(f"Publicado: {a['slug']} (fecha {fecha_larga(a['cuando'])})")

    reales = [a for a in publicados if not a["prueba"]]
    if reales:
        sincronizar_sitemap(destino, reales[-1]["cuando"].strftime("%Y-%m-%d"))
        actualizar_links(destino, reales[-1])  # el más nuevo va al botón de la bio
    salida_github(publicado="true", lista=", ".join(a["slug"] for a in publicados))


if __name__ == "__main__":
    main()
