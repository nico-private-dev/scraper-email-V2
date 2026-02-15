# CLAUDE.md — scraper-email-V2

## Project Overview

**scraper-email-V2** est un scraper CLI Python qui extrait les emails de contact pour les campagnes B2B. Deux modes d'entrée :
1. **Mode CSV** : à partir d'une liste d'URLs dans un fichier CSV
2. **Mode GMB** : à partir d'une recherche Google Maps (mot-clé + localisation) via l'API Google Places

Il filtre automatiquement les emails inutiles (agences web, DPO, noreply, fournisseurs d'email gratuits) et garde le meilleur email par site.

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
    ├── filter.py                # Filtrage campagne B2B (domaine, rôle, free email, etc.)
    └── gmb.py                   # Collecte URLs business via Google Places API (mode GMB)
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

### Mode CSV (depuis une liste d'URLs)

```bash
python -m email_scraper -i urls.csv -o results.csv
```

Le CSV d'entrée doit avoir une colonne nommée `url`, `urls`, `website`, `site` ou `link`.

### Mode GMB (depuis Google Maps)

```bash
python -m email_scraper --gmb "cabinet comptable" --location "Paris" -o results.csv
```

Nécessite une clé API Google Places (`--api-key` ou env var `GOOGLE_PLACES_API_KEY`).

### Exemples concrets

```bash
# --- Mode CSV ---
python -m email_scraper -i urls.csv -o results.csv
python -m email_scraper -i urls.csv -o results.csv -t 4 --no-robots
python -m email_scraper -i urls.csv -o results.csv --no-robots --allow-free-emails
python -m email_scraper -i urls.csv -o results.csv --dry-run -v

# --- Mode GMB ---
# Recherche basique
python -m email_scraper --gmb "cabinet comptable" --location "Paris" -o results.csv

# Avec multi-thread et rayon élargi
python -m email_scraper --gmb "plombier" --location "Lyon" -o results.csv --radius 15 -t 4

# Limiter le quota API (sécurité budget)
python -m email_scraper --gmb "restaurant" --location "Marseille" -o results.csv --api-quota 50

# Limiter le nombre de business collectés
python -m email_scraper --gmb "avocat" --location "Bordeaux" -o results.csv --gmb-max 30
```

### Options CLI complètes

**Source d'entrée (choisir un) :**

| Option | Description |
|--------|-------------|
| `-i, --input FILE` | CSV d'entrée avec colonne URL |
| `--gmb QUERY` | Recherche Google Maps (ex: "cabinet comptable") |

**Options GMB (avec `--gmb`) :**

| Option | Description | Défaut |
|--------|-------------|--------|
| `--location` | Ville/zone (requis avec --gmb) | — |
| `--api-key` | Clé API Google Places (ou env `GOOGLE_PLACES_API_KEY`) | — |
| `--radius` | Rayon de recherche en km | `10` |
| `--gmb-max` | Nombre max de business à collecter (0 = tout) | `0` |
| `--api-quota` | Limite de requêtes API par exécution (sécurité budget) | `100` (~3.50$) |

**Options scraping et filtrage :**

| Option | Description | Défaut |
|--------|-------------|--------|
| `-t, --threads` | Threads parallèles | `1` |
| `--timeout` | Timeout HTTP (secondes) | `15` |
| `--rate-limit` | Délai entre requêtes au même domaine | `1.0` |
| `--cache` | Répertoire cache HTML | désactivé |
| `--json` | Export JSON additionnel | désactivé |
| `--min-score` | Score de confiance minimum | `0.7` |
| `--max-per-site` | Max emails par site (0 = illimité) | `1` |
| `--no-filter` | Désactive les filtres campagne | `False` |
| `--allow-free-emails` | Garde les emails free (gmail, etc.) | `False` |
| `--no-robots` | Ignore robots.txt | `False` |
| `--dry-run` | Mode test sans extraction | `False` |
| `--save-every` | Checkpoint brut tous les N URLs | `100` |
| `--webhook` | URL webhook notification | désactivé |
| `--log-file` | Fichier de log | désactivé |
| `-v, -vv` | Verbosité (INFO, DEBUG) | WARNING |

### Format CSV de sortie

Mode CSV :

| url | email | source_page | confidence_score |
|-----|-------|-------------|-----------------|
| https://example.com | contact@example.com | https://example.com/contact | 0.85 |

Mode GMB (colonnes enrichies) :

| url | email | source_page | confidence_score | business_name | address | phone | rating | category |
|-----|-------|-------------|-----------------|---------------|---------|-------|--------|----------|
| https://cabinet-dupont.fr | contact@cabinet-dupont.fr | .../contact | 0.85 | Cabinet Dupont | 12 rue de Rivoli, 75001 Paris | 01 42 33 44 55 | 4.5 | Comptable |

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
| `gmb.py` | `GMBCollector` : Google Places API, quadrillage zones, pagination, quota tracking |

### Dataclasses

- **`EmailResult`** (`scraper.py`) : `url`, `email`, `source_page`, `confidence_score`, `source_type`, `page_type`
- **`ScrapeResult`** (`scraper.py`) : `input_url`, `emails: List[EmailResult]`, `pages_scraped`, `errors`
- **`BusinessResult`** (`gmb.py`) : `place_id`, `business_name`, `url`, `address`, `phone`, `rating`, `review_count`, `category`
- **`GMBCollectResult`** (`gmb.py`) : `businesses: List[BusinessResult]`, `total_api_requests`, `estimated_cost`, `errors`

## Mode GMB — Détails techniques

### Google Places API (New)

Le module `gmb.py` utilise l'endpoint Text Search de la Places API (New) :
- `POST https://places.googleapis.com/v1/places:searchText`
- Coût par requête : ~0.035$ (Text Search + champs Contact)
- Crédit gratuit : 200$/mois (~5 700 requêtes)
- Pagination : max 3 pages de 20 résultats = 60 résultats par query

### Quadrillage automatique

Pour contourner le cap de 60 résultats/query, le collecteur découpe la zone en cercles :
- `--radius <= 5km` : 1 seul cercle (centre de la zone)
- `--radius > 5km` : grille de cercles de 3km avec chevauchement
- Exemple Paris (10km) : ~12 cercles → jusqu'à 720 résultats uniques
- Déduplication par `place_id` (un business dans 2 cercles = 1 seul résultat)

### Quota et sécurité budget

Le quota (`--api-quota`, défaut 100) est une **limite dure** : le collecteur s'arrête immédiatement quand il est atteint. Il affiche le coût estimé avant et après la collecte.

| Quota | Coût max | Résultats max estimés |
|-------|----------|----------------------|
| 50 | ~1.75$ | ~1 000 |
| 100 (défaut) | ~3.50$ | ~2 000 |
| 500 | ~17.50$ | ~10 000 |
| 5 700 | ~200$ | ~toute la ville |

La clé API peut être passée via `--api-key` ou la variable d'environnement `GOOGLE_PLACES_API_KEY`.

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
