"""CLI interface for the email scraper."""

import argparse
import json
import logging
import os
import re
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Dict, List, Optional
from urllib.parse import urlparse

import pandas as pd
from tqdm import tqdm

from . import __version__
from .scraper import EmailScraper, ScrapeResult, EmailResult
from .filter import filter_results

logger = logging.getLogger("email_scraper")


def setup_logging(verbosity: int, log_file: Optional[str] = None):
    """Configure logging based on verbosity level."""
    if verbosity >= 2:
        level = logging.DEBUG
    elif verbosity >= 1:
        level = logging.INFO
    else:
        level = logging.WARNING

    formatter = logging.Formatter(
        "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # Console handler
    console = logging.StreamHandler(sys.stderr)
    console.setLevel(level)
    console.setFormatter(formatter)
    logger.addHandler(console)
    logger.setLevel(level)

    # File handler (optional)
    if log_file:
        file_handler = logging.FileHandler(log_file, encoding="utf-8")
        file_handler.setLevel(logging.DEBUG)  # Always DEBUG in file
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)


def load_urls(input_path: str) -> List[str]:
    """Load URLs from a CSV file."""
    path = Path(input_path)
    if not path.exists():
        logger.error("Input file not found: %s", input_path)
        sys.exit(1)

    try:
        df = pd.read_csv(path)
    except Exception as e:
        logger.error("Failed to read CSV: %s", e)
        sys.exit(1)

    # Find URL column (case-insensitive)
    url_col = None
    for col in df.columns:
        if col.strip().lower() in ("url", "urls", "website", "site", "link"):
            url_col = col
            break

    if url_col is None:
        logger.error(
            "No URL column found in CSV. Expected one of: url, urls, website, site, link. "
            "Found columns: %s", list(df.columns)
        )
        sys.exit(1)

    urls = df[url_col].dropna().astype(str).str.strip().tolist()
    urls = [u for u in urls if u and u.lower() != "nan"]

    logger.info("Loaded %d URLs from %s (column: '%s')", len(urls), input_path, url_col)
    return urls


def _extract_root_domain(url: str) -> str:
    """Extract root domain from URL for deduplication.

    Normalizes: http/https, www prefix, trailing paths, query strings.
    Examples:
        https://www.tacher-acogex.com/nous-connaitre/falaise/ → tacher-acogex.com
        http://www.tacher-acogex.com/ → tacher-acogex.com
        tacher-acogex.com → tacher-acogex.com
    """
    url = url.strip()
    if not url.startswith(("http://", "https://")):
        url = "https://" + url
    netloc = urlparse(url).netloc.lower()
    # Strip www. prefix
    netloc = re.sub(r"^www\.", "", netloc)
    # Strip port if present
    netloc = netloc.split(":")[0]
    return netloc


def deduplicate_urls(urls: List[str]) -> List[str]:
    """Deduplicate URLs by root domain, keeping the first occurrence.

    When the CSV has multiple URLs for the same site (http vs https,
    with/without www, different subpages), keep only one per domain.
    """
    seen: Dict[str, str] = {}
    for url in urls:
        domain = _extract_root_domain(url)
        if domain and domain not in seen:
            seen[domain] = url
    deduped = list(seen.values())
    if len(deduped) < len(urls):
        logger.info(
            "Deduplicated %d URLs → %d unique domains (removed %d duplicates)",
            len(urls), len(deduped), len(urls) - len(deduped)
        )
    return deduped


def save_csv(results: List[EmailResult], output_path: str,
             gmb_metadata: Optional[Dict[str, dict]] = None):
    """Save results to CSV, with optional GMB business metadata."""
    if not results:
        logger.warning("No emails found - creating empty output file")
        cols = ["url", "email", "source_page", "confidence_score"]
        if gmb_metadata is not None:
            cols.extend(["business_name", "address", "phone", "rating", "category"])
        df = pd.DataFrame(columns=cols)
    else:
        rows = []
        for r in results:
            row = {
                "url": r.url,
                "email": r.email,
                "source_page": r.source_page,
                "confidence_score": r.confidence_score,
            }
            if gmb_metadata is not None:
                domain = _extract_root_domain(r.url)
                meta = gmb_metadata.get(domain, {})
                row["business_name"] = meta.get("business_name", "")
                row["address"] = meta.get("address", "")
                row["phone"] = meta.get("phone", "")
                row["rating"] = meta.get("rating", "")
                row["category"] = meta.get("category", "")
            rows.append(row)
        df = pd.DataFrame(rows)

    df.to_csv(output_path, index=False, encoding="utf-8-sig")
    logger.info("Results saved to %s (%d rows)", output_path, len(df))


def save_json(results: List[EmailResult], output_path: str):
    """Save results to JSON with full metadata."""
    data = [r.to_dict() for r in results]
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    logger.info("JSON results saved to %s", output_path)


def send_webhook(webhook_url: str, results: List[EmailResult], duration: float):
    """Send completion notification via webhook."""
    import requests as req

    payload = {
        "status": "completed",
        "total_emails": len(results),
        "unique_domains": len(set(r.url for r in results)),
        "duration_seconds": round(duration, 2),
        "summary": [
            {"url": r.url, "email": r.email, "confidence": r.confidence_score}
            for r in results[:50]  # First 50 results in summary
        ],
    }

    try:
        resp = req.post(webhook_url, json=payload, timeout=10)
        resp.raise_for_status()
        logger.info("Webhook notification sent to %s", webhook_url)
    except Exception as e:
        logger.warning("Failed to send webhook: %s", e)


def _load_dotenv():
    """Load environment variables from .env file if it exists."""
    env_path = Path(".env")
    if not env_path.exists():
        return
    for line in env_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        value = value.strip().strip("'\"")
        if key and key not in os.environ:  # Don't override existing env vars
            os.environ[key] = value


def build_parser() -> argparse.ArgumentParser:
    """Build the CLI argument parser."""
    parser = argparse.ArgumentParser(
        prog="email-scraper",
        description="Extract emails from URLs (CSV file or Google Maps search).",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Mode CSV (from URL list)
  %(prog)s -i urls.csv -o results.csv
  %(prog)s -i urls.csv -o results.csv -t 4 --no-robots -vv

  # Mode GMB (from Google Maps search)
  %(prog)s --gmb "cabinet comptable" --location "Paris" -o results.csv
  %(prog)s --gmb "plombier" --location "Lyon" -o results.csv --radius 15 -t 4
  %(prog)s --gmb "restaurant" --location "Marseille" -o results.csv --api-quota 50 -v
        """,
    )

    # --- Input source ---
    source = parser.add_argument_group("input source (choose one)")
    source.add_argument(
        "-i", "--input",
        type=str,
        default=None,
        help="Input CSV file with a 'url' column",
    )
    source.add_argument(
        "--gmb",
        type=str,
        default=None,
        metavar="QUERY",
        help="Search Google Maps for businesses (e.g., \"cabinet comptable\")",
    )

    # --- GMB options ---
    gmb_group = parser.add_argument_group("GMB options (used with --gmb)")
    gmb_group.add_argument(
        "--location",
        type=str,
        default=None,
        help="City or area to search (e.g., \"Paris\", \"Lyon 3ème\")",
    )
    gmb_group.add_argument(
        "--country",
        type=str,
        default=None,
        metavar="COUNTRY",
        help="Scan an entire country city by city (e.g., \"france\", \"suisse\", \"belgique\")",
    )
    gmb_group.add_argument(
        "--api-key",
        type=str,
        default=None,
        help="Google Places API key (or set GOOGLE_PLACES_API_KEY env var)",
    )
    gmb_group.add_argument(
        "--radius",
        type=float,
        default=10.0,
        help="Search radius in km (default: 10). Larger = more API requests",
    )
    gmb_group.add_argument(
        "--gmb-max",
        type=int,
        default=0,
        help="Max businesses to collect from GMB (default: 0 = all found)",
    )
    gmb_group.add_argument(
        "--api-quota",
        type=int,
        default=100,
        help="Max API requests allowed per run (default: 100 = ~$3.50). "
             "Safety limit to stay within the free $200/month credit",
    )

    # --- Output ---
    parser.add_argument(
        "-o", "--output",
        required=True,
        help="Output CSV file path",
    )

    # --- Scraping options ---
    parser.add_argument(
        "-t", "--threads",
        type=int,
        default=1,
        help="Number of parallel threads (default: 1)",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=15,
        help="Request timeout in seconds (default: 15)",
    )
    parser.add_argument(
        "--rate-limit",
        type=float,
        default=1.0,
        help="Minimum delay between requests to same domain in seconds (default: 1.0)",
    )
    parser.add_argument(
        "--cache",
        type=str,
        default=None,
        help="Cache directory for fetched pages (optional)",
    )
    parser.add_argument(
        "--json",
        type=str,
        default=None,
        dest="json_output",
        help="Also export results as JSON with full metadata (optional)",
    )
    parser.add_argument(
        "--webhook",
        type=str,
        default=None,
        help="Webhook URL for completion notification (optional)",
    )

    # --- Filtering options ---
    parser.add_argument(
        "--min-score",
        type=float,
        default=0.7,
        help="Minimum confidence score to keep an email (default: 0.7)",
    )
    parser.add_argument(
        "--max-per-site",
        type=int,
        default=1,
        help="Max emails to keep per site (default: 1, best for campaigns. 0 = unlimited)",
    )
    parser.add_argument(
        "--no-filter",
        action="store_true",
        help="Disable campaign filtering (keep all emails including agencies, DPO, etc.)",
    )
    parser.add_argument(
        "--allow-free-emails",
        action="store_true",
        help="Keep emails from free providers (Gmail, Orange, Free, etc.). "
             "Useful for Solocal/Wix sites where businesses use personal email.",
    )
    parser.add_argument(
        "--no-robots",
        action="store_true",
        help="Ignore robots.txt restrictions",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Detect pages without extracting emails (test mode)",
    )
    parser.add_argument(
        "--user-agent",
        type=str,
        default=None,
        help="Custom User-Agent string",
    )
    parser.add_argument(
        "-v", "--verbose",
        action="count",
        default=0,
        help="Increase verbosity (-v for INFO, -vv for DEBUG)",
    )
    parser.add_argument(
        "--log-file",
        type=str,
        default=None,
        help="Save logs to file (optional)",
    )
    parser.add_argument(
        "--save-every",
        type=int,
        default=100,
        help="Save raw checkpoint every N URLs for crash recovery (default: 100)",
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {__version__}",
    )

    return parser


def _collect_gmb_urls(args) -> tuple:
    """Run GMB collection and return (urls, gmb_metadata).

    Supports two modes:
    - --location: single city search
    - --country: scan all cities in a country

    Returns:
        Tuple of (list of URL strings, dict mapping domain to business metadata)
    """
    from .gmb import GMBCollector, QuotaExceededError, COST_PER_REQUEST

    # Resolve API key
    api_key = args.api_key or os.environ.get("GOOGLE_PLACES_API_KEY")
    if not api_key:
        logger.error(
            "Google Places API key required. "
            "Use --api-key KEY or set GOOGLE_PLACES_API_KEY env var."
        )
        sys.exit(1)

    max_cost = args.api_quota * COST_PER_REQUEST

    collector = GMBCollector(
        api_key=api_key,
        max_requests=args.api_quota,
    )

    if args.country:
        # --- Country-wide scan ---
        from .cities import get_cities, get_country_name
        country_name = get_country_name(args.country)
        cities = get_cities(args.country)
        radius = args.radius if args.radius != 10.0 else 5.0  # default 5km per city

        print(f"GMB country mode: \"{args.gmb}\" across {country_name}")
        print(f"  Cities to scan:  {len(cities)}")
        print(f"  Radius per city: {radius}km")
        print(f"  API quota:       {args.api_quota} requests (max ~${max_cost:.2f})")
        if args.gmb_max > 0:
            print(f"  Max businesses:  {args.gmb_max}")
        print()

        # Progress with tqdm
        pbar = tqdm(total=len(cities), desc="Cities", unit="city")

        def _progress(city_name, idx, total, biz_count):
            pbar.set_postfix_str(f"{city_name} ({biz_count} biz)")
            pbar.update(1) if idx > 0 else None

        result = collector.collect_cities(
            query=args.gmb,
            cities=cities,
            radius_km=radius,
            max_results=args.gmb_max,
            progress_callback=_progress,
        )
        # Final update for last city
        pbar.update(pbar.total - pbar.n)
        pbar.close()

    else:
        # --- Single location scan ---
        print(f"GMB mode: searching Google Maps for \"{args.gmb}\" in \"{args.location}\"")
        print(f"  API quota:       {args.api_quota} requests (max ~${max_cost:.2f})")
        print(f"  Search radius:   {args.radius}km")
        if args.gmb_max > 0:
            print(f"  Max businesses:  {args.gmb_max}")
        print()

        result = collector.collect(
            query=args.gmb,
            location=args.location,
            radius_km=args.radius,
            max_results=args.gmb_max,
        )

    # GMB summary
    print(f"\n{'=' * 60}")
    print(f"GMB collection complete")
    print(f"{'=' * 60}")
    print(f"  Businesses found:  {len(result.businesses)} (with website)")
    print(f"  API requests used: {result.total_api_requests}/{args.api_quota}")
    print(f"  Estimated cost:    ${result.estimated_cost:.2f}")
    if result.errors:
        print(f"  Errors:            {len(result.errors)}")
    print(f"{'=' * 60}\n")

    if not result.businesses:
        logger.warning("No businesses with websites found on Google Maps")
        return [], {}

    # Build URL list and metadata dict (keyed by domain for matching)
    urls = []
    gmb_metadata: Dict[str, dict] = {}
    for biz in result.businesses:
        urls.append(biz.url)
        domain = _extract_root_domain(biz.url)
        gmb_metadata[domain] = {
            "business_name": biz.business_name,
            "address": biz.address,
            "phone": biz.phone,
            "rating": biz.rating if biz.rating is not None else "",
            "category": biz.category,
        }

    logger.info("Collected %d URLs from Google Maps", len(urls))
    return urls, gmb_metadata


def main(argv: Optional[List[str]] = None):
    """Main entry point."""
    # Load .env file if present (for API keys, etc.)
    _load_dotenv()

    parser = build_parser()
    args = parser.parse_args(argv)

    # Setup logging
    setup_logging(args.verbose, args.log_file)

    # --- Validate input source ---
    if args.gmb and args.input:
        logger.error("Cannot use both -i/--input and --gmb. Choose one input source.")
        sys.exit(1)
    if not args.gmb and not args.input:
        logger.error("An input source is required: -i FILE or --gmb QUERY")
        sys.exit(1)
    if args.gmb and not args.location and not args.country:
        logger.error("--location or --country is required when using --gmb")
        sys.exit(1)
    if args.gmb and args.location and args.country:
        logger.error("Cannot use both --location and --country. Choose one.")
        sys.exit(1)
    if args.country and not args.gmb:
        logger.error("--country requires --gmb (search query)")
        sys.exit(1)
    if args.country:
        from .cities import get_cities
        try:
            cities = get_cities(args.country)
        except ValueError as e:
            logger.error(str(e))
            sys.exit(1)

    # GMB mode: default to allowing free emails (small businesses often use gmail/orange)
    if args.gmb and not args.allow_free_emails:
        args.allow_free_emails = True
        print("Note: --allow-free-emails activé par défaut en mode GMB "
              "(les petits commerces utilisent souvent gmail/orange/hotmail)")

    # --- Collect URLs ---
    gmb_metadata: Optional[Dict[str, dict]] = None

    if args.gmb:
        # GMB mode: collect from Google Maps
        urls, gmb_metadata = _collect_gmb_urls(args)
        if not urls:
            save_csv([], args.output, gmb_metadata)
            return 0
    else:
        # CSV mode: load from file
        urls = load_urls(args.input)

    if not urls:
        logger.error("No URLs to process")
        sys.exit(1)

    urls = deduplicate_urls(urls)

    # --- Scrape emails from collected URLs ---
    scraper_kwargs = {
        "timeout": args.timeout,
        "respect_robots": not args.no_robots,
        "cache_dir": args.cache,
        "rate_limit": args.rate_limit,
    }
    if args.user_agent:
        scraper_kwargs["user_agent"] = args.user_agent

    start_time = time.time()
    all_emails: List[EmailResult] = []
    errors: List[str] = []
    urls_processed = 0

    def _checkpoint_save():
        """Save raw (unfiltered) emails to output CSV as crash recovery."""
        if all_emails and not args.dry_run:
            save_csv(all_emails, args.output, gmb_metadata)
            logger.info(
                "Checkpoint: saved %d raw emails after %d/%d URLs",
                len(all_emails), urls_processed, len(urls),
            )

    if args.threads > 1:
        # Parallel execution
        logger.info("Starting parallel scraping with %d threads", args.threads)
        scraper = EmailScraper(**scraper_kwargs)

        with ThreadPoolExecutor(max_workers=args.threads) as executor:
            futures = {
                executor.submit(scraper.scrape_url, url, args.dry_run): url
                for url in urls
            }

            with tqdm(total=len(urls), desc="Scraping", unit="url") as pbar:
                for future in as_completed(futures):
                    url = futures[future]
                    try:
                        result = future.result()
                        all_emails.extend(result.emails)
                        errors.extend(result.errors)
                    except Exception as e:
                        logger.error("Unexpected error for %s: %s", url, e)
                        errors.append(f"Unexpected error for {url}: {e}")
                    urls_processed += 1
                    pbar.update(1)
                    if args.save_every > 0 and urls_processed % args.save_every == 0:
                        _checkpoint_save()
    else:
        # Sequential execution
        logger.info("Starting sequential scraping")
        scraper = EmailScraper(**scraper_kwargs)

        for url in tqdm(urls, desc="Scraping", unit="url"):
            try:
                result = scraper.scrape_url(url, args.dry_run)
                all_emails.extend(result.emails)
                errors.extend(result.errors)
            except Exception as e:
                logger.error("Unexpected error for %s: %s", url, e)
                errors.append(f"Unexpected error for {url}: {e}")
            urls_processed += 1
            if args.save_every > 0 and urls_processed % args.save_every == 0:
                _checkpoint_save()

    duration = time.time() - start_time

    # Save raw (unfiltered) CSV before filtering
    raw_count = len(all_emails)
    if not args.dry_run and all_emails:
        output_path = Path(args.output)
        raw_path = str(output_path.with_stem(output_path.stem + "_raw"))
        save_csv(all_emails, raw_path, gmb_metadata)
        print(f"\nRaw emails saved to: {raw_path} ({raw_count} emails)")

    # Apply campaign filtering
    if not args.no_filter and not args.dry_run:
        all_emails = filter_results(
            all_emails,
            min_score=args.min_score,
            require_domain_match=True,
            max_per_site=args.max_per_site,
            allow_free_emails=args.allow_free_emails,
        )

    # Summary
    print(f"\n{'=' * 60}")
    print(f"Scraping complete")
    print(f"{'=' * 60}")
    print(f"  URLs processed:  {len(urls)}")
    print(f"  Emails found:    {raw_count}")
    if not args.no_filter and not args.dry_run:
        print(f"  After filtering: {len(all_emails)}  (min score: {args.min_score})")
        print(f"  Filtered out:    {raw_count - len(all_emails)}")
    print(f"  Errors:          {len(errors)}")
    print(f"  Duration:        {duration:.1f}s")
    print(f"{'=' * 60}")

    if not args.dry_run:
        # Save filtered CSV (with GMB metadata if in GMB mode)
        save_csv(all_emails, args.output, gmb_metadata)

        # Save JSON if requested
        if args.json_output:
            save_json(all_emails, args.json_output)

        # Send webhook if configured
        if args.webhook:
            send_webhook(args.webhook, all_emails, duration)

    # Log errors summary
    if errors:
        logger.warning("Encountered %d error(s):", len(errors))
        for err in errors[:20]:  # Show first 20 errors
            logger.warning("  - %s", err)
        if len(errors) > 20:
            logger.warning("  ... and %d more", len(errors) - 20)

    return 0 if not errors else 1


if __name__ == "__main__":
    sys.exit(main())
