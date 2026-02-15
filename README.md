# Email Scraper

Outil CLI Python pour extraire des adresses email de contact à partir d'URLs listées dans un fichier CSV. Conçu pour les campagnes B2B : filtre automatiquement les emails inutiles (agences web, DPO, noreply, fournisseurs gratuits) et garde le meilleur email par site.

## Fonctionnalités

- **Extraction robuste** : regex stricte, liens `mailto:`, désobfuscation (`[at]`, `(at)`, espaces autour de `@`)
- **Détection intelligente** : analyse les liens de la homepage pour trouver les pages contact, mentions légales, à propos (FR + EN)
- **Score de confiance** : chaque email reçoit un score (0.0–1.0) basé sur la source, le domaine, le contexte et le type de page
- **Filtrage campagne B2B** : rejette automatiquement les emails free (gmail, orange), les outils (ovh, hubspot), les rôles non-campagne (dpo, noreply, abuse)
- **Plateformes hébergées** : gestion intelligente des sites Solocal, Wix, Weebly, etc. où le domaine email diffère du domaine site
- **Dédoublonnage** : par domaine en entrée + meilleur email par site en sortie
- **Checkpoints** : sauvegarde intermédiaire tous les N URLs pour crash recovery
- **Rate limiting** : respect du `robots.txt` et délai configurable entre requêtes
- **Cache** : évite le re-scraping avec un cache local
- **Export dual** : CSV + JSON (métadonnées complètes)
- **Parallélisation** : multi-thread avec `concurrent.futures`
- **Mode dry-run** : teste la détection de pages sans scraper
- **Webhook** : notification optionnelle en fin de scraping

## Installation

**Prérequis** : Python >= 3.9

```bash
pip install -r requirements.txt
```

Ou en mode développement :

```bash
pip install -e .
```

## Utilisation

### Format CSV d'entrée

Le fichier CSV doit contenir une colonne `url` (ou `urls`, `website`, `site`, `link`) :

```csv
url
https://example-company.fr
https://another-site.com
mon-site.fr
```

Les URLs sont automatiquement normalisées (ajout `https://`) et dédupliquées par domaine racine.

### Commandes

**Scraping simple :**

```bash
python -m email_scraper -i urls.csv -o results.csv
```

**Multi-thread rapide, ignorer robots.txt :**

```bash
python -m email_scraper -i urls.csv -o results.csv -t 4 --no-robots
```

**Garder les emails free (gmail, orange...) — utile pour sites Solocal/Wix :**

```bash
python -m email_scraper -i urls.csv -o results.csv --no-robots --allow-free-emails
```

**Mode debug complet avec logs fichier :**

```bash
python -m email_scraper -i urls.csv -o results.csv -vv --log-file scrape.log
```

**Mode dry-run (détecte les pages sans extraire) :**

```bash
python -m email_scraper -i urls.csv -o results.csv --dry-run -v
```

**Tout garder, pas de filtre :**

```bash
python -m email_scraper -i urls.csv -o results.csv --no-filter --no-robots
```

**Avec cache, JSON et webhook :**

```bash
python -m email_scraper -i urls.csv -o results.csv \
  -t 4 --no-robots \
  --cache .cache \
  --json results.json \
  --webhook https://hooks.example.com/notify \
  -vv
```

Si installé via `pip install -e .` :

```bash
email-scraper -i urls.csv -o results.csv -t 4 --no-robots
```

### Options CLI

| Option | Description | Défaut |
|--------|-------------|--------|
| `-i, --input` | Fichier CSV d'entrée (requis) | — |
| `-o, --output` | Fichier CSV de sortie (requis) | — |
| `-t, --threads` | Nombre de threads parallèles | `1` |
| `--timeout` | Timeout par requête (secondes) | `15` |
| `--rate-limit` | Délai minimum entre requêtes au même domaine (secondes) | `1.0` |
| `--cache` | Répertoire de cache HTML | désactivé |
| `--json` | Export JSON additionnel avec métadonnées complètes | désactivé |
| `--min-score` | Score de confiance minimum pour garder un email | `0.7` |
| `--max-per-site` | Nombre max d'emails gardés par site (`0` = illimité) | `1` |
| `--no-filter` | Désactive tous les filtres campagne B2B | `False` |
| `--allow-free-emails` | Garde les emails free (gmail, orange, free, sfr, etc.) | `False` |
| `--no-robots` | Ignorer robots.txt | `False` |
| `--dry-run` | Détecter les pages sans scraper (mode test) | `False` |
| `--save-every` | Checkpoint brut tous les N URLs (crash recovery) | `100` |
| `--webhook` | URL webhook de notification à la fin | désactivé |
| `--user-agent` | User-Agent personnalisé | Chrome 131 |
| `--log-file` | Fichier de log | désactivé |
| `-v, -vv` | Verbosité (INFO, DEBUG) | WARNING |

### Format CSV de sortie

```csv
url,email,source_page,confidence_score
https://example.fr,contact@example.fr,https://example.fr/contact,0.85
```

Par défaut, un seul email est gardé par site (le meilleur pour une campagne). Utiliser `--max-per-site 0` pour tous les garder.

### Format JSON de sortie

```json
[
  {
    "url": "https://example.fr",
    "email": "contact@example.fr",
    "source_page": "https://example.fr/contact",
    "confidence_score": 0.85,
    "source_type": "mailto",
    "page_type": "contact"
  }
]
```

## Architecture

```
email_scraper/
├── __init__.py      # Version
├── __main__.py      # Point d'entrée python -m
├── cli.py           # Interface CLI, I/O, orchestration parallèle, checkpoints
├── scraper.py       # EmailScraper : fetch HTTP, cache, robots.txt, rate limiting
├── detector.py      # Détection des pages contact/legal/about (slugs + texte liens)
├── extractor.py     # Extraction emails : regex, mailto, désobfuscation, validation
├── scorer.py        # Score de confiance (0.0–1.0) multi-facteurs
└── filter.py        # Filtrage campagne B2B, sélection meilleur email par site
```

### Pipeline de traitement

Pour chaque URL du CSV :

1. **Normalisation** — ajout `https://`, déduplication par domaine racine
2. **Fetch homepage** — requête HTTP avec headers Chrome réalistes, vérif robots.txt, cache, retry 403 avec Referer
3. **Détection sous-pages** — analyse des liens de la homepage pour trouver `/contact`, `/mentions-legales`, `/a-propos` (patterns FR + EN)
4. **Extraction emails** — sur chaque page : liens `mailto:`, désobfuscation, regex sur texte + HTML source, nettoyage
5. **Scoring** — score de confiance 0.0–1.0 basé sur 5 facteurs (voir ci-dessous)
6. **Filtrage B2B** — appliqué une seule fois à la fin : score minimum, rejet free/outils/rôles, sélection meilleur email par site

## Score de confiance

Le score (0.0–1.0) est calculé à partir de 5 facteurs :

| Facteur | Poids max | Détail |
|---------|-----------|--------|
| Méthode source | 0.25 | `mailto` (+0.25) > obfusqué (+0.20) > regex (+0.10) |
| Match domaine | 0.30 | Exact (+0.30), partiel (+0.20), plateforme hébergée (+0.30), différent (-0.25) |
| Type de page | 0.20 | Contact (+0.20) > legal (+0.15) > about (+0.12) > homepage (+0.08) |
| Contexte sémantique | 0.15 | Mots-clés de contact à proximité (téléphone, adresse, formulaire...) |
| Qualité local part | 0.10 | `contact@` (1.0) > `prenom.nom@` (0.8) > alphanumérique (0.6) |

Pénalité supplémentaire : email avec domaine différent sur une page mentions légales (-0.15) — typiquement une agence web.

## Filtrage campagne B2B

Le filtrage (`filter.py`) s'applique à la fin du scraping et vérifie :

1. **Score minimum** — par défaut 0.7 (réduit de 0.30 pour les plateformes hébergées)
2. **Domaines free** — gmail, orange, free, hotmail, sfr, yahoo, protonmail... → rejeté (sauf `--allow-free-emails`)
3. **Domaines outils** — ovh, wix, hubspot, sendinblue, cloudflare, amazonaws... → toujours rejeté
4. **Rôles non-campagne** — dpo, rgpd, noreply, abuse, postmaster, webmaster... → toujours rejeté
5. **Correspondance domaine** — l'email doit être sur le même domaine que le site (sauf plateformes hébergées)
6. **Sélection meilleur email** — priorité : `contact@` > `info@` > `hello@` > `prenom.nom@` > autre

### Plateformes hébergées

Les sites Solocal, Wix, Weebly, Squarespace, Jimdo, etc. utilisent un domaine plateforme (ex: `mon-commerce.site-solocal.com`). L'email du commerce est forcément sur un autre domaine. Le scraper gère ça automatiquement :
- Pas de pénalité domaine mismatch au scoring
- Skip du domain match check au filtrage
- Seuil de score réduit

## Dépendances

| Package | Usage |
|---------|-------|
| `requests` | Requêtes HTTP |
| `beautifulsoup4` | Parsing HTML, extraction des liens |
| `pandas` | Lecture/écriture CSV |
| `tqdm` | Barre de progression |

Dev optionnel : `pytest`, `pytest-cov`
