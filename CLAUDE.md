# CLAUDE.md — scraper-email-V2

## Project Overview

**scraper-email-V2** est un scraper CLI Python qui extrait les emails de contact depuis une liste d'URLs fournie en CSV. Il est conçu pour les campagnes B2B : il filtre automatiquement les emails inutiles (agences web, DPO, noreply, fournisseurs d'email gratuits) et garde le meilleur email par site.

**Repository** : `nico-private-dev/scraper-email-V2`

## Repository Structure

```
scraper-email-V2/
├── CLAUDE.md                    # Ce fichier
├── pyproject.toml               # Config projet, dépendances, entry point
├── requirements.txt             # Dépendances pip
├── .gitignore
├── README.md
└── email_scraper/
    ├── __init__.py              # Version (__version__ = "1.0.0")
    ├── __main__.py              # python -m email_scraper
    ├── cli.py                   # Interface CLI (argparse, orchestration)
    ├── scraper.py               # EmailScraper : fetch pages, coordonne l'extraction
    ├── detector.py              # Détection des pages contact/legal/about depuis la homepage
    ├── extractor.py             # Extraction email : regex, mailto, désobfuscation, validation
    ├── scorer.py                # Score de confiance (0.0–1.0) pour chaque email
    └── filter.py                # Filtrage campagne B2B (domaine, rôle, free email, etc.)
```

## Installation

### Prérequis

- Python >= 3.9

### Setup

```bash
pip install -r requirements.txt
# OU installation en mode éditable :
pip install -e .
```

## Utilisation

### Commande de base

```bash
python -m email_scraper -i urls.csv -o results.csv
```

Le CSV d'entrée doit avoir une colonne nommée `url`, `urls`, `website`, `site` ou `link`.

### Options CLI complètes

```bash
python -m email_scraper \
  -i urls.csv          # CSV d'entrée avec colonne URL (requis)
  -o results.csv       # CSV de sortie (requis)
  -t 4                 # Nombre de threads parallèles (défaut: 1)
  --timeout 20         # Timeout HTTP en secondes (défaut: 15)
  --rate-limit 1.0     # Délai min entre requêtes au même domaine (défaut: 1.0s)
  --cache .cache       # Répertoire cache pour pages HTML (optionnel)
  --json results.json  # Export JSON en plus du CSV (optionnel)
  --min-score 0.7      # Score de confiance minimum (défaut: 0.7)
  --max-per-site 1     # Max emails gardés par site (défaut: 1, 0 = illimité)
  --no-filter          # Désactive tous les filtres campagne
  --allow-free-emails  # Garde les emails gmail, orange, free, etc.
  --no-robots          # Ignore robots.txt
  --dry-run            # Détecte les pages sans extraire (mode test)
  --user-agent "..."   # User-Agent custom
  --save-every 100     # Checkpoint brut tous les N URLs (défaut: 100)
  --webhook URL        # Notification webhook à la fin
  --log-file scrape.log # Sauvegarder les logs dans un fichier
  -v                   # Verbosité INFO
  -vv                  # Verbosité DEBUG
```

### Exemples concrets

```bash
# Scraping simple
python -m email_scraper -i urls.csv -o results.csv

# Scraping rapide multi-thread, ignorer robots.txt
python -m email_scraper -i urls.csv -o results.csv -t 4 --no-robots

# Garder les emails free (gmail, orange...) — utile pour sites Solocal/Wix
python -m email_scraper -i urls.csv -o results.csv --no-robots --allow-free-emails

# Mode debug complet avec logs fichier
python -m email_scraper -i urls.csv -o results.csv -vv --log-file scrape.log

# Mode test : voir les pages détectées sans scraper
python -m email_scraper -i urls.csv -o results.csv --dry-run -v

# Tout garder, pas de filtre
python -m email_scraper -i urls.csv -o results.csv --no-filter --no-robots
```

### Format CSV de sortie

| url | email | source_page | confidence_score |
|-----|-------|-------------|-----------------|
| https://example.com | contact@example.com | https://example.com/contact | 0.85 |

### Entry point installé

Après `pip install -e .`, la commande `email-scraper` est disponible :

```bash
email-scraper -i urls.csv -o results.csv
```

## Architecture & Pipeline

### Flux de traitement pour chaque URL

```
URL d'entrée
  │
  ├── 1. Normalisation (ajout https://, dédup par domaine)
  │
  ├── 2. Fetch homepage (scraper.py)
  │     └── Vérif robots.txt, cache, retry 403 avec Referer
  │
  ├── 3. Détection sous-pages (detector.py)
  │     └── Cherche liens vers /contact, /mentions-legales, /a-propos
  │         via patterns d'URL slugs + texte des liens (FR + EN)
  │
  ├── 4. Fetch & extraction de chaque page (extractor.py)
  │     ├── mailto: links (priorité haute)
  │     ├── Désobfuscation : [at], (at), espaces autour de @
  │     ├── Regex sur texte + HTML source
  │     └── Nettoyage : TLD invalide, numéros de tel collés, etc.
  │
  ├── 5. Scoring de confiance (scorer.py)
  │     ├── Source : mailto > obfusqué > regex
  │     ├── Match domaine email ↔ domaine site (+0.30 / -0.25)
  │     ├── Type de page : contact > legal > about > homepage
  │     ├── Contexte sémantique : mots-clés proches (contact, téléphone...)
  │     └── Qualité local part : contact@ > prenom.nom > random
  │
  └── 6. Filtrage campagne B2B (filter.py) — appliqué à la fin
        ├── Score minimum (défaut 0.7)
        ├── Rejet emails free (gmail, orange, free, sfr...)
        ├── Rejet domaines outils (ovh, wix, hubspot, cloudflare...)
        ├── Rejet rôles non-campagne (dpo, rgpd, noreply, abuse...)
        ├── Vérif correspondance domaine email ↔ site
        ├── Exceptions plateformes hébergées (Solocal, Wix, etc.)
        └── Sélection du meilleur email par site (contact@ > info@ > prénom.nom)
```

### Modules clés

| Module | Rôle |
|--------|------|
| `cli.py` | Parsing args, orchestration séquentielle/parallèle, checkpoints, export CSV/JSON |
| `scraper.py` | `EmailScraper` : fetch HTTP, cache, robots.txt, rate limiting, coordination |
| `detector.py` | `detect_pages()` : trouve les pages contact/legal/about via slug + texte liens |
| `extractor.py` | `extract_emails()` : regex, mailto, désobfuscation, `clean_email()`, `validate_email()` |
| `scorer.py` | `compute_confidence()` : score 0.0–1.0 multi-facteurs |
| `filter.py` | `filter_results()` : filtrage B2B, `is_campaign_worthy()`, sélection best-per-site |

### Dataclasses

- **`EmailResult`** (`scraper.py`) : `url`, `email`, `source_page`, `confidence_score`, `source_type`, `page_type`
- **`ScrapeResult`** (`scraper.py`) : `input_url`, `emails: List[EmailResult]`, `pages_scraped`, `errors`

## Points importants pour les modifications

### Checkpoints (`--save-every`)

Les checkpoints sauvegardent les emails **bruts (non filtrés)** en CSV toutes les N URLs. Le filtrage ne s'applique qu'une seule fois à la fin. Ne jamais appeler `filter_results()` dans les boucles de scraping.

### Plateformes hébergées

Les sites Solocal, Wix, Weebly, etc. ont un domaine plateforme (ex: `mon-commerce.site-solocal.com`). L'email du commerce sera forcément sur un domaine différent. Le code gère ça :
- `scorer.py` : pas de pénalité domaine mismatch pour ces plateformes
- `filter.py` : skip du domain match check, seuil de score réduit de -0.30

### Filtrage campagne B2B

Le filtrage est dans `filter.py` et s'applique uniquement à la fin du scraping (dans `main()`). Les listes noires sont :
- `FREE_EMAIL_DOMAINS` : gmail, orange, free, hotmail, etc.
- `TOOL_DOMAINS` : ovh, wix, hubspot, sendinblue, cloudflare, etc.
- `NON_CAMPAIGN_LOCAL_PARTS` : dpo, rgpd, noreply, abuse, postmaster, etc.

`--allow-free-emails` désactive uniquement le filtre `FREE_EMAIL_DOMAINS`.

### User-Agent

Le scraper simule Chrome 131 sur Windows avec headers réalistes (Sec-Fetch-*, Accept-Language fr-FR). Il retry automatiquement les 403 avec un header Referer.

## Dependencies

| Package | Usage |
|---------|-------|
| `requests` | HTTP fetching |
| `beautifulsoup4` | Parsing HTML, extraction liens |
| `pandas` | Lecture CSV entrée, écriture CSV sortie |
| `tqdm` | Barre de progression |

Dev optionnel : `pytest`, `pytest-cov`

## Code Conventions

- Python 3.9+, type hints partout
- Logging via `logging.getLogger(__name__)` dans chaque module
- Pas de dépendances lourdes (pas de Selenium, pas de headless browser)
- Les emails sont toujours en lowercase
- Les domaines sont toujours nettoyés (strip www., lowercase, strip port)

## Git Workflow

- **Main branch** : `main`
- Commits clairs et focalisés
- Ne pas force-push sur les branches partagées
