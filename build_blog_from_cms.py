#!/usr/bin/env python3
"""
build_blog_from_cms.py
=======================
Lit tous les fichiers Markdown dans content/blog/ (le format que Decap CMS
écrit quand vous publiez depuis /admin) et génère :
  - une page HTML complète par article : blog/{slug}.html
  - la liste à jour sur blog.html
  - les entrées sitemap.xml correspondantes

Ce script doit tourner à CHAQUE déploiement (voir vercel.json : il est appelé
automatiquement dans "buildCommand"). Vous n'avez jamais à le lancer vous-même.
"""
import os, re, glob, yaml, datetime, html as html_lib, json
import markdown as md

SITE_DIR = os.environ.get("SITE_OUTPUT_DIR", os.path.dirname(os.path.abspath(__file__)))
CONTENT_DIR = os.path.join(SITE_DIR, "content", "blog")
DOMAIN = "https://www.visitbenintours.com"
TEMPLATE_PATH = os.path.join(SITE_DIR, "about.html")  # page déjà générée, sert de moule


def parse_frontmatter(path):
    """Parseur minimal, sans dépendance externe (pas besoin de python-frontmatter)."""
    raw = open(path, encoding="utf-8").read()
    m = re.match(r"^---\s*\n(.*?)\n---\s*\n(.*)$", raw, re.DOTALL)
    if not m:
        raise ValueError(f"{path}: frontmatter YAML manquant (--- ... ---)")
    meta = yaml.safe_load(m.group(1)) or {}
    body_md = m.group(2).strip()
    return meta, body_md


def load_articles():
    articles = []
    for path in sorted(glob.glob(os.path.join(CONTENT_DIR, "*.md"))):
        meta, body_md = parse_frontmatter(path)
        meta["_body_html"] = md.markdown(body_md, extensions=["extra"])
        meta["_source"] = path
        articles.append(meta)
    return articles


def is_publishable(article, now=None):
    """Un article sort sur le site seulement si : statut = publié ET date <= maintenant.
       Une date dans le futur = publication programmée, qui prendra effet au PROCHAIN
       build (voir la note sur le Cron Job plus bas dans le rapport)."""
    now = now or datetime.datetime.now()
    if article.get("draft") != "published":
        return False
    pub_date = article.get("date")
    if isinstance(pub_date, str):
        pub_date = datetime.datetime.fromisoformat(pub_date)
    if isinstance(pub_date, datetime.date) and not isinstance(pub_date, datetime.datetime):
        pub_date = datetime.datetime.combine(pub_date, datetime.time.min)
    return pub_date is None or pub_date <= now


def render_article_page(article, template_head, nav_block, footer_block):
    slug = article["slug"]
    title = article["meta_title"] or article["title"]
    desc = article["meta_description"] or article["excerpt"]
    canonical = f"{DOMAIN}/blog/{slug}.html"
    img = article["featured_image"].lstrip("/")
    img_alt = article["featured_image_alt"]
    language = str(article.get("language", "fr")).lower()
    if language not in {"fr", "en"}:
        language = "fr"
    is_french = language == "fr"
    home_href = "../fr/index.html" if is_french else "../index.html"
    blog_href = "../fr/blog.html" if is_french else "../blog.html"
    home_label = "Accueil" if is_french else "Home"
    contact_href = "../fr/contact.html" if is_french else "../contact.html"
    contact_title = "Envie de vivre cette expérience ?" if is_french else "Planning this experience?"
    contact_text = "Contactez-nous pour réserver votre circuit privé." if is_french else "Contact us to book your private tour."
    contact_label = "Nous contacter" if is_french else "Contact us"
    pub_date_iso = article["date"] if isinstance(article["date"], str) else article["date"].isoformat()

    jsonld = json.dumps({
        "@context": "https://schema.org",
        "@type": "BlogPosting",
        "headline": article["title"],
        "description": desc,
        "image": f"{DOMAIN}/{img}",
        "datePublished": pub_date_iso,
        "inLanguage": language,
        "author": {"@type": "Organization", "name": "Visit Bénin Tours"},
        "publisher": {
            "@type": "Organization",
            "name": "Visit Bénin Tours",
            "logo": {
                "@type": "ImageObject",
                "url": f"{DOMAIN}/images/brand/logo-visit-benin-tours.png",
            },
        },
        "mainEntityOfPage": {"@type": "WebPage", "@id": canonical},
    }, ensure_ascii=False, indent=2).replace("<", "\\u003c").replace(">", "\\u003e").replace("&", "\\u0026")

    head = f'''<!DOCTYPE html>
<html lang="{language}">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{html_lib.escape(title)}</title>
<meta name="description" content="{html_lib.escape(desc)}">
<link rel="canonical" href="{canonical}">
<meta name="theme-color" content="#0B1F46">
<link rel="icon" href="../images/brand/favicon.ico" sizes="any">
<link rel="apple-touch-icon" href="../images/brand/apple-touch-icon.png">
<meta property="og:type" content="article">
<meta property="og:site_name" content="Visit Bénin Tours">
<meta property="og:url" content="{canonical}">
<meta property="og:title" content="{html_lib.escape(title)}">
<meta property="og:description" content="{html_lib.escape(desc)}">
<meta property="og:image" content="{DOMAIN}/{img}">
<meta property="article:published_time" content="{pub_date_iso}">
<meta name="twitter:card" content="summary_large_image">
<script type="application/ld+json">
{jsonld}
</script>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Playfair+Display:ital,wght@0,400;0,500;0,700;0,900;1,400;1,600;1,900&family=DM+Sans:wght@300;400;500;600;700&family=Libre+Baskerville:ital@1&display=swap" rel="stylesheet">
<link rel="stylesheet" href="../styles.min.css">
</head>
<body>
'''

    gallery_html = ""
    if article.get("gallery"):
        imgs = "".join(
            f'<figure class="review-photo"><img src="../{g["image"].lstrip("/")}" alt="{html_lib.escape(article["title"])}" loading="lazy"></figure>'
            for g in article["gallery"]
        )
        gallery_html = f'<div class="review-photo-grid reveal" style="margin-top:2.5rem">{imgs}</div>'

    body = f'''
<div class="page active" id="page-blog-{slug}">
  <div class="inner-hero">
    <picture><img class="inner-hero-photo" src="../{img}" alt="{html_lib.escape(img_alt)}" fetchpriority="high" onload="this.closest('.inner-hero').classList.add('has-photo')" onerror="this.closest('picture').remove()"></picture>
    <div class="inner-hero-bg"></div><div class="inner-hero-pattern"></div>
    <div class="breadcrumb"><a href="{home_href}">{home_label}</a><span class="breadcrumb-sep">›</span><a href="{blog_href}">Blog</a><span class="breadcrumb-sep">›</span>{html_lib.escape(article['title'])}</div>
    <div class="inner-hero-content">
      <span class="hero-eyebrow" style="display:inline-block;margin-bottom:1rem">{html_lib.escape(article['category'])}</span>
      <h1>{html_lib.escape(article['title'])}</h1>
      <p class="hero-intro">{html_lib.escape(article['excerpt'])}</p>
    </div>
  </div>
  <div class="content-grid">
    <div class="content-main">
      {article['_body_html']}
      {gallery_html}
    </div>
    <div>
      <div class="contact-card">
        <h3>{contact_title}</h3>
        <p>{contact_text}</p>
        <a class="contact-btn whatsapp" onclick="openWhatsapp()">💬 WhatsApp</a>
        <a class="contact-btn" href="{contact_href}">✉️ {contact_label}</a>
      </div>
    </div>
  </div>
</div>
'''
    return head + nav_block + body + footer_block + '\n<script src="../app.js" defer></script>\n</body>\n</html>\n'


def render_blog_card(article):
    slug = article["slug"]
    img = article["featured_image"].lstrip("/")
    return f'''      <a class="blog-card" href="blog/{slug}.html">
        <div class="dest-card-img">
          <picture><img class="dest-card-photo" src="{img}" width="1448" height="1086" loading="lazy" alt="{html_lib.escape(article['featured_image_alt'])}" onerror="this.closest('picture').remove()"></picture>
          <span class="dest-card-icon">📝</span>
        </div>
        <div class="blog-card-body">
          <span class="blog-card-tag">{html_lib.escape(article['category'])}</span>
          <h3>{html_lib.escape(article['title'])}</h3>
          <p>{html_lib.escape(article['excerpt'])}</p>
          <span class="blog-card-link">Lire la suite →</span>
        </div>
      </a>
'''


def update_blog_listing(published):
    blog_path = os.path.join(SITE_DIR, "blog.html")
    s = open(blog_path, encoding="utf-8").read()
    start = s.find('<div class="blog-grid">') + len('<div class="blog-grid">')
    end = s.find('</div>', s.find('<div class="blog-grid">'))
    # ré-ouvre correctement la fin réelle du blog-grid (le premier </div> après son ouverture
    # correspond à la 1ère carte fermante interne; on cherche donc le </div> qui ramène profondeur 0)
    depth = 1
    i = start
    while depth > 0:
        nd = s.find('<div', i)
        nc = s.find('</div>', i)
        if nc == -1:
            break
        if nd != -1 and nd < nc:
            depth += 1
            i = nd + 4
        else:
            depth -= 1
            i = nc + 6
    end = i - len('</div>')
    cards = "\n".join(render_blog_card(a) for a in published)
    new_s = s[:start] + "\n" + cards + s[end:]
    open(blog_path, "w", encoding="utf-8").write(new_s)
    print(f"✓ blog.html mis à jour avec {len(published)} article(s)")



def update_sitemap(published):
    sitemap_path = os.path.join(SITE_DIR, "sitemap.xml")
    s = open(sitemap_path, encoding="utf-8").read()
    entries = "\n".join(
        f'  <url><loc>{DOMAIN}/blog/{a["slug"]}.html</loc>'
        f'<lastmod>{(a["date"] if isinstance(a["date"], str) else a["date"].isoformat())[:10]}</lastmod></url>'
        for a in published
    )
    # retire les anciennes entrées d'articles CMS si on relance le build (évite les doublons)
    s = re.sub(r'\s*<url><loc>[^<]*/blog/[^<]*\.html</loc>.*?</url>', '', s)
    s = s.replace('</urlset>', entries + '\n</urlset>')
    open(sitemap_path, "w", encoding="utf-8").write(s)
    print(f"✓ sitemap.xml mis à jour avec {len(published)} article(s)")


def main():
    raw_template = open(TEMPLATE_PATH, encoding="utf-8").read()

    # Découpe le fichier-moule en 3 blocs réutilisables : nav (top-bar -> fin menu mobile),
    # et footer (balise <footer> -> fin du fichier, wa-float + script inclus)
    nav_start = raw_template.find('<!-- TOP BAR -->')
    nav_end = raw_template.find('<div class="page active"')
    nav_block = raw_template[nav_start:nav_end]
    # adapte les chemins d'images/liens de nav pour un article servi depuis /blog/*.html (un niveau plus bas)
    nav_block = re.sub(r'(href|src)="(?!http|#|mailto|tel)', r'\1="../', nav_block)
    nav_block = nav_block.replace('href="../index.html"', 'href="../index.html"')  # no-op safe

    footer_start = raw_template.find('<footer>')
    footer_end = raw_template.find('<script src="app.js"')
    footer_block = raw_template[footer_start:footer_end]
    footer_block = re.sub(r'(href|src)="(?!http|#|mailto|tel)', r'\1="../', footer_block)

    os.makedirs(os.path.join(SITE_DIR, "blog"), exist_ok=True)

    articles = load_articles()
    published = [a for a in articles if is_publishable(a)]
    published.sort(key=lambda a: str(a["date"]), reverse=True)

    for article in published:
        html_out = render_article_page(article, None, nav_block, footer_block)
        out_path = os.path.join(SITE_DIR, "blog", f'{article["slug"]}.html')
        open(out_path, "w", encoding="utf-8").write(html_out)
        print("✓ généré:", out_path)

    update_blog_listing(published)
    update_sitemap(published)

    print(f"\n{len(published)} article(s) publié(s) sur {len(articles)} total "
          f"({len(articles)-len(published)} brouillon(s)/programmé(s) non publiés)")
    return published


if __name__ == "__main__":
    main()
