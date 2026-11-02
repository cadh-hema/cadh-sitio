# Comunidad Argentina de HEMA — CADH

Sitio web oficial de la **Comunidad Argentina de HEMA (CADH)**.  
Hosteado en GitHub Pages · [comunidadargentinadehema.com.ar](https://www.comunidadargentinadehema.com.ar)

---

## ¿Qué es este repositorio?

Este repo contiene el código fuente del sitio estático de la CADH. HTML + CSS + JS puro, sin frameworks, sin dependencias externas salvo Google Fonts. Se publica automáticamente con GitHub Pages.

---

## Estructura del proyecto

```
/
├── index.html            ← Página de inicio
├── hemapa.html           ← Mapa de practicantes
├── recursos.html         ← Lista de recursos de HEMA
├── convivencia.html      ← Pautas de convivencia y colaboración
├── sobre-cadh.html       ← Sobre la comunidad y el administrador
├── campamento.html       ← Campamento CADH (evento anual)
├── css/
│   └── styles.css        ← (pendiente) Hoja de estilos compartida
├── img/
│   ├── hero-1.jpg        ← Fotos del carrusel del hero (hero-1 a hero-4)
│   ├── hero-2.jpg
│   ├── hero-3.jpg
│   ├── hero-4.jpg
│   ├── logo-cadh.svg     ← Logo de la CADH en SVG
│   ├── logo-campamento.png ← Logo del Campamento CADH
│   ├── og-image.jpg      ← Imagen para compartir en redes (1200×630px)
│   ├── favicon.ico       ← Favicon 32×32
│   ├── favicon-192.png   ← Favicon para Android
│   └── campamento/       ← Fotos de las ediciones del campamento
│       └── foto-01.jpg   ← (y las que se agreguen)
├── CADH-guia-de-estilo.md ← Guía de estilo del ecosistema CADH/HEMARKET
└── README.md             ← Este archivo
```

---

## Cómo correr el sitio localmente

No hace falta ningún servidor ni instalar nada. Abrís `index.html` directo en el navegador y listo.

Si querés un servidor local (útil para que el mapa del HEMAPA cargue correctamente), podés usar la extensión **Live Server** de VS Code, o desde la terminal:

```bash
# Con Python 3
python -m http.server 8000
# Después abrís http://localhost:8000 en el navegador
```

---

## Navbar, footer e índice de artículos (se arman solos)

- **Navbar:** se edita solo en `partials/nav.html`. **Footer:** solo en `partials/footer.html`.
- Al hacer push, el workflow **Estampar sitio** (`tools/estampar.py`) los copia a todas las páginas, corrige los links de las páginas que están en carpetas y marca el link de la página actual.
- En cada página, lo que está entre `<!-- CADH:NAV -->` y `<!-- /CADH:NAV -->` (y lo mismo con `CADH:FOOTER`) se pisa en cada push: no editar ahí.
- **Índice de artículos:** `articulos/index.html` y `articulos/pagina-2.html`, `pagina-3.html`… se arman solos con todos los artículos de la carpeta, del más nuevo al más viejo: el destacado + 8 por página. La frase corta de cada card sale de `<meta name="cadh-bajada">` del artículo (o de la meta description si no tiene).
- Una página nueva solo necesita tener un `<header class="nav">` y un `<footer class="footer">` cualquiera: la primera vez que corre el estampador los reemplaza por los oficiales.
- `links.html` tiene diseño propio y no lleva navbar ni footer.
- Después de cada push, si el robot cambió algo, GitHub Desktop muestra **Pull origin**: apretalo antes de seguir editando.

---

## Cómo editar el contenido

### Agregar recursos (`recursos.html`)

Todos los datos están en el bloque `const RECURSOS = [...]` al final del archivo. Buscá la sección que corresponda y agregá un bloque nuevo:

```javascript
{
  nombre:  "Nombre del sitio o canal",
  url:     "https://...",
  desc:    "Descripción breve de qué es y por qué vale la pena.",
  idioma:  "Español",   // o "Inglés" o "Bilingüe"
  por:     "Nombre de quien lo recomendó"
},
```

### Agregar fotos al campamento (`campamento.html`)

1. Guardá las fotos en `img/campamento/` (formato WebP o JPG, máximo 300KB cada una).
2. En `campamento.html`, dentro de la sección `.galeria-grid`, reemplazá los placeholders por:

```html
<div class="galeria-item">
  <img src="img/campamento/foto-01.jpg" alt="Descripción de la foto" loading="lazy">
</div>
```

### Agregar novedades al campamento

En `campamento.html`, dentro de `.novedades-list`, copiás este bloque y lo pegás **al principio** (las más recientes van arriba):

```html
<div class="novedad-item">
  <div class="novedad-fecha">DD/MM/AAAA</div>
  <div class="novedad-texto">Descripción de la novedad.</div>
</div>
```

### Cambiar las fotos del carrusel del hero (`index.html`)

Reemplazá los archivos `img/hero-1.jpg` a `img/hero-4.jpg` con las fotos nuevas. Si querés más o menos de 4 fotos, avisale al administrador técnico para ajustar la animación CSS.

---

## Cómo publicar cambios

1. Editás el archivo que corresponda.
2. Guardás.
3. Subís los cambios a GitHub (ver sección de abajo).
4. GitHub Pages publica automáticamente en menos de 2 minutos.

### Subir cambios con GitHub Desktop (recomendado)

1. Abrís **GitHub Desktop**.
2. Vas a ver los archivos modificados listados.
3. Escribís un mensaje corto en el campo "Summary" (ej: `Agrego recurso de YouTube`).
4. Hacés click en **Commit to main**.
5. Hacés click en **Push origin**.
6. Listo — en 1-2 minutos el sitio está actualizado.

---

## Imágenes: convenciones

| Archivo | Formato | Tamaño máximo | Dimensiones |
|---|---|---|---|
| Fotos del hero | JPG o WebP | 300KB | 1920×1080px recomendado |
| Fotos del campamento | JPG o WebP | 300KB | Cualquiera, cuadradas quedan mejor |
| Logo CADH | SVG | — | Vectorial, escala a cualquier tamaño |
| Logo campamento | PNG con fondo transparente | 200KB | — |
| OG image | JPG | 300KB | Exactamente 1200×630px |

---

## Guía de estilo

Ver [`CADH-guia-de-estilo.md`](./CADH-guia-de-estilo.md) para colores, tipografías, componentes y tono de escritura.

---

## Proyectos relacionados

| Proyecto | Estado | Descripción |
|---|---|---|
| **CADH** (este repo) | ✅ Activo | Sitio principal de la comunidad |
| **HEMARKET** | 🔧 En desarrollo | Portal de compra/venta de equipamiento HEMA |

---

## Contacto

- **Email:** comunidadargentinadehema@gmail.com
- **Instagram:** [@comunidadargentinadehema](https://www.instagram.com/comunidadargentinadehema)
- **Facebook:** [/comunidadargentinadehema](https://www.facebook.com/comunidadargentinadehema)
- **WhatsApp Community:** [Sumate acá](https://chat.whatsapp.com/J8FOacdq1g0GMBEtuvFxuf)

---

*Un proyecto de la Comunidad Argentina de HEMA · Argentina · 2024*
