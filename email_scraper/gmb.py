"""Google My Business (Google Places API) collector.

Collects business website URLs from Google Maps via the Places API (New).
Used to feed URLs into the email scraper pipeline.

Includes:
- Text Search with pagination (up to 60 results per query)
- Automatic grid splitting to cover large areas beyond the 60-result cap
- Quota tracking to stay within the free $200/month credit
- Deduplication by place_id
"""

import logging
import math
import time
from dataclasses import dataclass, field, asdict
from typing import Dict, List, Optional, Tuple

import requests

logger = logging.getLogger(__name__)

# Google Places API (New) endpoint
PLACES_SEARCH_URL = "https://places.googleapis.com/v1/places:searchText"

# Cost per API request (Text Search + Contact fields)
# Text Search: $0.032 + Contact fields (websiteUri, phone): $0.003 = $0.035
COST_PER_REQUEST = 0.035

# Default quota: 100 requests = ~$3.50 (well within the $200/month free credit)
DEFAULT_MAX_REQUESTS = 100

# Max results per query (Google hard limit: 3 pages × 20 = 60)
MAX_RESULTS_PER_QUERY = 60
RESULTS_PER_PAGE = 20

# Fields to request from the API
FIELD_MASK = ",".join([
    "places.id",
    "places.displayName",
    "places.websiteUri",
    "places.formattedAddress",
    "places.nationalPhoneNumber",
    "places.rating",
    "places.userRatingCount",
    "places.primaryTypeDisplayName",
])


@dataclass
class BusinessResult:
    """A single business found on Google Maps."""
    place_id: str
    business_name: str
    url: str  # Website URL
    address: str = ""
    phone: str = ""
    rating: Optional[float] = None
    review_count: Optional[int] = None
    category: str = ""

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class GMBCollectResult:
    """Results from a GMB collection run."""
    businesses: List[BusinessResult] = field(default_factory=list)
    total_api_requests: int = 0
    estimated_cost: float = 0.0
    errors: List[str] = field(default_factory=list)


class QuotaExceededError(Exception):
    """Raised when the API request quota would be exceeded."""
    pass


class GMBCollector:
    """Collect business website URLs from Google Maps via Places API."""

    def __init__(
        self,
        api_key: str,
        max_requests: int = DEFAULT_MAX_REQUESTS,
    ):
        self.api_key = api_key
        self.max_requests = max_requests
        self.requests_used = 0
        self._seen_place_ids: Dict[str, BusinessResult] = {}

    @property
    def requests_remaining(self) -> int:
        return max(0, self.max_requests - self.requests_used)

    @property
    def estimated_cost(self) -> float:
        return round(self.requests_used * COST_PER_REQUEST, 2)

    def _check_quota(self):
        """Raise QuotaExceededError if no requests remaining."""
        if self.requests_used >= self.max_requests:
            raise QuotaExceededError(
                f"API quota reached: {self.requests_used}/{self.max_requests} requests used "
                f"(~${self.estimated_cost:.2f}). "
                f"Use --api-quota to increase the limit."
            )

    def collect(
        self,
        query: str,
        location: str,
        radius_km: float = 10.0,
        max_results: int = 0,
    ) -> GMBCollectResult:
        """
        Collect business URLs from Google Maps.

        Args:
            query: Search keyword (e.g., "cabinet comptable")
            location: City/area (e.g., "Paris")
            radius_km: Search radius in km (used for grid splitting)
            max_results: Max businesses to collect (0 = no limit, respects quota)

        Returns:
            GMBCollectResult with collected businesses
        """
        result = GMBCollectResult()

        # Step 1: Geocode the location to get center coordinates
        center = self._geocode(query, location)
        if center is None:
            result.errors.append(f"Could not geocode location: {location}")
            return result

        lat, lng = center
        logger.info("Location '%s' → lat=%.4f, lng=%.4f", location, lat, lng)

        # Step 2: Generate grid of search circles
        grid_points = self._generate_grid(lat, lng, radius_km)
        logger.info(
            "Grid: %d search circles (radius %.1fkm each) covering %.1fkm area",
            len(grid_points), min(radius_km, 5.0), radius_km,
        )

        # Step 3: Search each grid point
        for i, (plat, plng) in enumerate(grid_points):
            if max_results > 0 and len(self._seen_place_ids) >= max_results:
                logger.info("Reached max_results=%d, stopping collection", max_results)
                break

            try:
                self._check_quota()
            except QuotaExceededError as e:
                logger.warning(str(e))
                result.errors.append(str(e))
                break

            logger.debug(
                "Searching grid %d/%d (lat=%.4f, lng=%.4f)",
                i + 1, len(grid_points), plat, plng,
            )

            cell_radius = min(radius_km, 5.0) * 1000  # in meters
            self._search_area(query, plat, plng, cell_radius, max_results, result)

        # Collect results
        result.businesses = list(self._seen_place_ids.values())
        if max_results > 0:
            result.businesses = result.businesses[:max_results]
        result.total_api_requests = self.requests_used
        result.estimated_cost = self.estimated_cost

        logger.info(
            "GMB collection complete: %d businesses with websites, "
            "%d API requests (~$%.2f)",
            len(result.businesses), self.requests_used, self.estimated_cost,
        )

        return result

    def _search_area(
        self,
        query: str,
        lat: float,
        lng: float,
        radius_m: float,
        max_results: int,
        result: GMBCollectResult,
    ):
        """Search a single area with pagination (up to 60 results)."""
        page_token = None

        for page in range(3):  # Max 3 pages per query
            if max_results > 0 and len(self._seen_place_ids) >= max_results:
                break

            try:
                self._check_quota()
            except QuotaExceededError as e:
                result.errors.append(str(e))
                return

            body = {
                "textQuery": query,
                "locationBias": {
                    "circle": {
                        "center": {"latitude": lat, "longitude": lng},
                        "radius": radius_m,
                    }
                },
                "languageCode": "fr",
                "maxResultCount": RESULTS_PER_PAGE,
            }
            if page_token:
                body["pageToken"] = page_token

            headers = {
                "Content-Type": "application/json",
                "X-Goog-Api-Key": self.api_key,
                "X-Goog-FieldMask": FIELD_MASK + ",nextPageToken",
            }

            try:
                resp = requests.post(
                    PLACES_SEARCH_URL,
                    headers=headers,
                    json=body,
                    timeout=15,
                )
                self.requests_used += 1

                if resp.status_code == 429:
                    logger.warning("Rate limited by Google API, waiting 5s...")
                    time.sleep(5)
                    continue

                if resp.status_code != 200:
                    error_msg = f"Places API error {resp.status_code}: {resp.text[:200]}"
                    logger.warning(error_msg)
                    result.errors.append(error_msg)
                    return

                data = resp.json()

            except requests.exceptions.RequestException as e:
                error_msg = f"Places API request failed: {e}"
                logger.warning(error_msg)
                result.errors.append(error_msg)
                return

            places = data.get("places", [])
            if not places:
                break

            new_count = 0
            for place in places:
                business = self._parse_place(place)
                if business and business.place_id not in self._seen_place_ids:
                    self._seen_place_ids[business.place_id] = business
                    new_count += 1

            logger.debug(
                "Page %d: %d places returned, %d new with websites",
                page + 1, len(places), new_count,
            )

            page_token = data.get("nextPageToken")
            if not page_token:
                break

            # Small delay between pages
            time.sleep(0.5)

    def _parse_place(self, place: dict) -> Optional[BusinessResult]:
        """Parse a place from the API response into a BusinessResult."""
        website = place.get("websiteUri", "")
        if not website:
            return None  # Skip businesses without a website

        place_id = place.get("id", "")
        name = place.get("displayName", {}).get("text", "")
        address = place.get("formattedAddress", "")
        phone = place.get("nationalPhoneNumber", "")
        rating = place.get("rating")
        review_count = place.get("userRatingCount")
        category = place.get("primaryTypeDisplayName", {}).get("text", "")

        return BusinessResult(
            place_id=place_id,
            business_name=name,
            url=website,
            address=address,
            phone=phone,
            rating=rating,
            review_count=review_count,
            category=category,
        )

    def _geocode(self, query: str, location: str) -> Optional[Tuple[float, float]]:
        """
        Get coordinates for a location using the Places Text Search.

        Uses the search query + location to get a center point.
        This uses 1 API request.
        """
        try:
            self._check_quota()
        except QuotaExceededError:
            return None

        headers = {
            "Content-Type": "application/json",
            "X-Goog-Api-Key": self.api_key,
            "X-Goog-FieldMask": "places.location",
        }
        body = {
            "textQuery": f"{query} {location}",
            "languageCode": "fr",
            "maxResultCount": 1,
        }

        try:
            resp = requests.post(
                PLACES_SEARCH_URL,
                headers=headers,
                json=body,
                timeout=15,
            )
            self.requests_used += 1

            if resp.status_code != 200:
                logger.warning("Geocoding failed: %s", resp.text[:200])
                return None

            data = resp.json()
            places = data.get("places", [])
            if not places:
                return None

            loc = places[0].get("location", {})
            return loc.get("latitude"), loc.get("longitude")

        except requests.exceptions.RequestException as e:
            logger.warning("Geocoding request failed: %s", e)
            return None

    def _generate_grid(
        self,
        center_lat: float,
        center_lng: float,
        radius_km: float,
    ) -> List[Tuple[float, float]]:
        """
        Generate a grid of overlapping circles to cover the search area.

        For small areas (radius <= 5km): single circle.
        For larger areas: hex-grid pattern with cell radius = 5km and overlap.
        """
        if radius_km <= 5.0:
            return [(center_lat, center_lng)]

        # Cell radius: 3km for good overlap with 5km API radius
        cell_step_km = 3.0

        # Convert km to degrees (approximate)
        km_per_lat = 111.0
        km_per_lng = 111.0 * math.cos(math.radians(center_lat))

        lat_step = cell_step_km / km_per_lat
        lng_step = cell_step_km / km_per_lng

        # Number of steps in each direction
        n_steps = math.ceil(radius_km / cell_step_km)

        points = []
        for i in range(-n_steps, n_steps + 1):
            for j in range(-n_steps, n_steps + 1):
                plat = center_lat + i * lat_step
                plng = center_lng + j * lng_step

                # Only include points within the overall radius
                dist = math.sqrt((i * cell_step_km) ** 2 + (j * cell_step_km) ** 2)
                if dist <= radius_km:
                    points.append((plat, plng))

        return points
