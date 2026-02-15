# Email Scraper

Outil CLI Python pour extraire des adresses email de contact pour les campagnes B2B. Deux modes d'entrée :
- **Mode CSV** : à partir d'une liste d'URLs dans un fichier CSV
- **Mode GMB** : à partir d'une recherche Google Maps (mot-clé + localisation) via l'API Google Places

Filtre automatiquement les emails inutiles (agences web, DPO, noreply, fournisseurs gratuits) et garde le meilleur email par site.

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
- **Mode GMB** : recherche Google Maps par mot-clé + localisation, collecte les URLs et métadonnées business
- **Quadrillage automatique** : découpe les zones larges en cercles pour dépasser le cap de 60 résultats Google
- **Sécurité budget** : quota API configurable pour rester dans le crédit gratuit (200$/mois)
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

### Mode CSV (depuis une liste d'URLs)

Le fichier CSV doit contenir une colonne `url` (ou `urls`, `website`, `site`, `link`) :

```csv
url
https://example-company.fr
https://another-site.com
mon-site.fr
```

```bash
python -m email_scraper -i urls.csv -o results.csv
python -m email_scraper -i urls.csv -o results.csv -t 4 --no-robots
python -m email_scraper -i urls.csv -o results.csv --no-robots --allow-free-emails
```

### Mode GMB (depuis Google Maps)

Recherche des business sur Google Maps par mot-clé + localisation, collecte leurs URLs de site web, puis scrape les emails.

**Prérequis** : clé API Google Places (New). [Créer une clé](https://console.cloud.google.com/apis/credentials) et activer l'API "Places API (New)". Crédit gratuit : 200$/mois.

```bash
# Recherche basique
python -m email_scraper --gmb "cabinet comptable" --location "Paris" -o results.csv

# Clé API via argument ou variable d'environnement
python -m email_scraper --gmb "plombier" --location "Lyon" -o results.csv --api-key "AIza..."
export GOOGLE_PLACES_API_KEY="AIza..."
python -m email_scraper --gmb "plombier" --location "Lyon" -o results.csv

# Rayon élargi + multi-thread
python -m email_scraper --gmb "plombier" --location "Lyon" -o results.csv --radius 15 -t 4

# Limiter le quota API (sécurité budget)
python -m email_scraper --gmb "restaurant" --location "Marseille" -o results.csv --api-quota 50

# Limiter le nombre de business collectés
python -m email_scraper --gmb "avocat" --location "Bordeaux" -o results.csv --gmb-max 30
```

#### Sécurité budget

Le quota API (`--api-quota`, défaut 100) est une **limite dure** : le scraper s'arrête quand il est atteint. Le coût est affiché avant et après.

| Quota | Coût max | Résultats max |
|-------|----------|---------------|
| 50 | ~1.75$ | ~1 000 |
| **100** (défaut) | **~3.50$** | **~2 000** |
| 500 | ~17.50$ | ~10 000 |

Avec le crédit gratuit de 200$/mois, tu peux faire ~5 700 requêtes/mois sans payer.

### Options CLI

**Source d'entrée (choisir un) :**

| Option | Description |
|--------|-------------|
| `-i, --input FILE` | CSV d'entrée avec colonne URL |
| `--gmb QUERY` | Recherche Google Maps (ex: `"cabinet comptable"`) |

**Options GMB :**

| Option | Description | Défaut |
|--------|-------------|--------|
| `--location` | Ville/zone (requis avec `--gmb`) | — |
| `--api-key` | Clé API Google Places (ou env `GOOGLE_PLACES_API_KEY`) | — |
| `--radius` | Rayon de recherche en km | `10` |
| `--gmb-max` | Max business à collecter (`0` = tout) | `0` |
| `--api-quota` | Limite de requêtes API par exécution | `100` |

**Options scraping et filtrage :**

| Option | Description | Défaut |
|--------|-------------|--------|
| `-t, --threads` | Threads parallèles | `1` |
| `--timeout` | Timeout par requête (secondes) | `15` |
| `--rate-limit` | Délai entre requêtes au même domaine (secondes) | `1.0` |
| `--cache` | Répertoire de cache HTML | désactivé |
| `--json` | Export JSON additionnel | désactivé |
| `--min-score` | Score de confiance minimum | `0.7` |
| `--max-per-site` | Max emails par site (`0` = illimité) | `1` |
| `--no-filter` | Désactive les filtres campagne B2B | `False` |
| `--allow-free-emails` | Garde les emails free (gmail, orange, etc.) | `False` |
| `--no-robots` | Ignorer robots.txt | `False` |
| `--dry-run` | Détecte les pages sans scraper (mode test) | `False` |
| `--save-every` | Checkpoint brut tous les N URLs | `100` |
| `--webhook` | URL webhook de notification | désactivé |
| `--user-agent` | User-Agent personnalisé | Chrome 131 |
| `--log-file` | Fichier de log | désactivé |
| `-v, -vv` | Verbosité (INFO, DEBUG) | WARNING |

### Format CSV de sortie

**Mode CSV :**

```csv
url,email,source_page,confidence_score
https://example.fr,contact@example.fr,https://example.fr/contact,0.85
```

**Mode GMB (colonnes enrichies avec métadonnées business) :**

```csv
url,email,source_page,confidence_score,business_name,address,phone,rating,category
https://cabinet-dupont.fr,contact@cabinet-dupont.fr,https://cabinet-dupont.fr/contact,0.85,Cabinet Dupont,"12 rue de Rivoli, 75001 Paris",01 42 33 44 55,4.5,Comptable
```

Par défaut, un seul email par site. `--max-per-site 0` pour tous les garder.

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
├── filter.py        # Filtrage campagne B2B, sélection meilleur email par site
└── gmb.py           # Collecte URLs business via Google Places API (mode GMB)
```

### Pipeline de traitement

**Mode GMB :** Étape 0 avant le pipeline ci-dessous :
- Géocodage de la localisation → lat/lng
- Quadrillage en cercles (rayon 3km, chevauchement) pour dépasser le cap de 60 résultats
- Requête Text Search API pour chaque cercle → collecte URLs + métadonnées
- Déduplication par `place_id`

**Pour chaque URL (mode CSV ou GMB) :**

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
