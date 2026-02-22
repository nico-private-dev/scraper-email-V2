"""Pre-loaded city databases for country-wide GMB scanning.

Each country has a list of (city_name, latitude, longitude) covering
all major population centers. For France, this is all 96 département
préfectures. For Switzerland and Belgium, cantonal/provincial capitals.

This avoids wasting API quota on geocoding and ensures complete
national coverage.
"""

from typing import Dict, List, Tuple

# Type alias: (city_name, latitude, longitude)
City = Tuple[str, float, float]

# ============================================================
# FRANCE — 96 préfectures de département (métropole)
# ============================================================
FRANCE: List[City] = [
    # Île-de-France
    ("Paris", 48.8566, 2.3522),
    ("Melun", 48.5394, 2.6603),
    ("Versailles", 48.8014, 2.1301),
    ("Évry-Courcouronnes", 48.6320, 2.4410),
    ("Nanterre", 48.8924, 2.2147),
    ("Bobigny", 48.9100, 2.4500),
    ("Créteil", 48.7905, 2.4559),
    ("Pontoise", 49.0507, 2.1008),
    # Nord / Hauts-de-France
    ("Lille", 50.6292, 3.0573),
    ("Arras", 50.2913, 2.7810),
    ("Beauvais", 49.4295, 2.0807),
    ("Amiens", 49.8941, 2.2957),
    ("Laon", 49.5640, 3.6200),
    # Grand Est
    ("Strasbourg", 48.5734, 7.7521),
    ("Colmar", 48.0794, 7.3588),
    ("Metz", 49.1193, 6.1757),
    ("Nancy", 48.6921, 6.1844),
    ("Épinal", 48.1726, 6.4510),
    ("Bar-le-Duc", 48.7731, 5.1587),
    ("Châlons-en-Champagne", 48.9566, 4.3631),
    ("Charleville-Mézières", 49.7719, 4.7164),
    ("Troyes", 48.2973, 4.0744),
    ("Chaumont", 48.1138, 5.1393),
    # Normandie
    ("Rouen", 49.4432, 1.0999),
    ("Caen", 49.1829, -0.3707),
    ("Évreux", 49.0241, 1.1508),
    ("Alençon", 48.4327, 0.0919),
    ("Saint-Lô", 49.1166, -1.0908),
    # Bretagne
    ("Rennes", 48.1173, -1.6778),
    ("Saint-Brieuc", 48.5141, -2.7600),
    ("Quimper", 47.9967, -4.1024),
    ("Vannes", 47.6564, -2.7602),
    # Pays de la Loire
    ("Nantes", 47.2184, -1.5536),
    ("Angers", 47.4784, -0.5632),
    ("Le Mans", 48.0061, 0.1996),
    ("Laval", 48.0735, -0.7714),
    ("La Roche-sur-Yon", 46.6705, -1.4268),
    # Centre-Val de Loire
    ("Orléans", 47.9029, 1.9093),
    ("Tours", 47.3941, 0.6848),
    ("Bourges", 47.0811, 2.3993),
    ("Chartres", 48.4564, 1.4896),
    ("Blois", 47.5861, 1.3359),
    ("Châteauroux", 46.8100, 1.6906),
    # Bourgogne-Franche-Comté
    ("Dijon", 47.3220, 5.0415),
    ("Besançon", 47.2378, 6.0241),
    ("Auxerre", 47.7979, 3.5714),
    ("Mâcon", 46.3069, 4.8282),
    ("Nevers", 46.9897, 3.1590),
    ("Lons-le-Saunier", 46.6749, 5.5516),
    ("Vesoul", 47.6197, 6.1568),
    ("Belfort", 47.6397, 6.8628),
    # Nouvelle-Aquitaine
    ("Bordeaux", 44.8378, -0.5792),
    ("Limoges", 45.8315, 1.2578),
    ("Poitiers", 46.5802, 0.3404),
    ("La Rochelle", 46.1603, -1.1511),
    ("Angoulême", 45.6500, 0.1556),
    ("Périgueux", 45.1847, 0.7211),
    ("Niort", 46.3239, -0.4593),
    ("Guéret", 46.1710, 1.8710),
    ("Tulle", 45.2671, 1.7695),
    ("Agen", 44.2033, 0.6164),
    ("Mont-de-Marsan", 43.8940, -0.4993),
    ("Pau", 43.2951, -0.3708),
    # Occitanie
    ("Toulouse", 43.6047, 1.4442),
    ("Montpellier", 43.6108, 3.8767),
    ("Nîmes", 43.8367, 4.3601),
    ("Perpignan", 42.6887, 2.8948),
    ("Carcassonne", 43.2130, 2.3491),
    ("Rodez", 44.3501, 2.5735),
    ("Cahors", 44.4479, 1.4414),
    ("Auch", 43.6449, 0.5857),
    ("Tarbes", 43.2327, 0.0734),
    ("Albi", 43.9281, 2.1490),
    ("Montauban", 44.0176, 1.3554),
    ("Foix", 42.9643, 1.6052),
    ("Mende", 44.5185, 3.4987),
    # Auvergne-Rhône-Alpes
    ("Lyon", 45.7640, 4.8357),
    ("Clermont-Ferrand", 45.7772, 3.0870),
    ("Grenoble", 45.1885, 5.7245),
    ("Saint-Étienne", 45.4397, 4.3872),
    ("Valence", 44.9334, 4.8924),
    ("Chambéry", 45.5646, 5.9178),
    ("Annecy", 45.8992, 6.1294),
    ("Bourg-en-Bresse", 46.2056, 5.2252),
    ("Le Puy-en-Velay", 45.0428, 3.8849),
    ("Aurillac", 44.9261, 2.4398),
    ("Privas", 44.7355, 4.5986),
    # Provence-Alpes-Côte d'Azur
    ("Marseille", 43.2965, 5.3698),
    ("Nice", 43.7102, 7.2620),
    ("Toulon", 43.1242, 5.9280),
    ("Avignon", 43.9493, 4.8055),
    ("Digne-les-Bains", 44.0932, 6.2357),
    ("Gap", 44.5594, 6.0786),
    # Corse
    ("Ajaccio", 41.9263, 8.7369),
    ("Bastia", 42.6973, 9.4510),
]

# ============================================================
# SUISSE — 26 chefs-lieux de cantons + villes majeures
# ============================================================
SUISSE: List[City] = [
    # Cantons romands (FR)
    ("Genève", 46.2044, 6.1432),
    ("Lausanne", 46.5197, 6.6323),
    ("Sion", 46.2332, 7.3593),
    ("Neuchâtel", 46.9900, 6.9293),
    ("Fribourg", 46.8065, 7.1620),
    ("Delémont", 47.3651, 7.3429),
    # Cantons alémaniques
    ("Zürich", 47.3769, 8.5417),
    ("Bern", 46.9480, 7.4474),
    ("Basel", 47.5596, 7.5886),
    ("Luzern", 47.0502, 8.3093),
    ("St. Gallen", 47.4245, 9.3767),
    ("Aarau", 47.3925, 8.0444),
    ("Solothurn", 47.2088, 7.5370),
    ("Schaffhausen", 47.6960, 8.6362),
    ("Frauenfeld", 47.5535, 8.8988),
    ("Chur", 46.8508, 9.5321),
    ("Zug", 47.1662, 8.5155),
    ("Sarnen", 46.8961, 8.2456),
    ("Stans", 46.9597, 8.3660),
    ("Glarus", 47.0404, 9.0683),
    ("Altdorf", 46.8800, 8.6441),
    ("Schwyz", 47.0207, 8.6530),
    ("Herisau", 47.3867, 9.2794),
    ("Appenzell", 47.3318, 9.4083),
    # Canton italien
    ("Bellinzona", 46.1952, 9.0235),
    ("Lugano", 46.0037, 8.9511),
    # Grandes villes non-capitales
    ("Winterthur", 47.4986, 8.7246),
    ("Biel/Bienne", 47.1368, 7.2467),
    ("Thun", 46.7580, 7.6280),
    ("Montreux", 46.4312, 6.9107),
    ("La Chaux-de-Fonds", 47.1035, 6.8256),
]

# ============================================================
# BELGIQUE — 10 chefs-lieux de province + grandes villes
# ============================================================
BELGIQUE: List[City] = [
    # Bruxelles
    ("Bruxelles", 50.8503, 4.3517),
    # Flandre
    ("Anvers", 51.2194, 4.4025),
    ("Gand", 51.0543, 3.7174),
    ("Bruges", 51.2093, 3.2247),
    ("Louvain", 50.8798, 4.7005),
    ("Hasselt", 50.9307, 5.3378),
    # Wallonie
    ("Liège", 50.6326, 5.5797),
    ("Namur", 50.4669, 4.8675),
    ("Mons", 50.4542, 3.9563),
    ("Charleroi", 50.4108, 4.4446),
    ("Arlon", 49.6833, 5.8167),
    ("Wavre", 50.7172, 4.6105),
    # Autres villes importantes
    ("Tournai", 50.6058, 3.3883),
    ("Verviers", 50.5892, 5.8626),
    ("Courtrai", 50.8279, 3.2649),
    ("Ostende", 51.2154, 2.9286),
    ("Malines", 51.0259, 4.4776),
]

# ============================================================
# LUXEMBOURG
# ============================================================
LUXEMBOURG: List[City] = [
    ("Luxembourg-Ville", 49.6117, 6.1319),
    ("Esch-sur-Alzette", 49.4958, 5.9806),
    ("Differdange", 49.5242, 5.8914),
    ("Dudelange", 49.4809, 6.0867),
    ("Ettelbruck", 49.8475, 6.1044),
]

# ============================================================
# Registry + aliases
# ============================================================
COUNTRIES: Dict[str, List[City]] = {
    "france": FRANCE,
    "suisse": SUISSE,
    "belgique": BELGIQUE,
    "luxembourg": LUXEMBOURG,
}

COUNTRY_ALIASES: Dict[str, str] = {
    # ISO codes
    "fr": "france",
    "ch": "suisse",
    "be": "belgique",
    "lu": "luxembourg",
    # English names
    "switzerland": "suisse",
    "belgium": "belgique",
}


def get_cities(country: str) -> List[City]:
    """Get city list for a country (by name or alias).

    Args:
        country: Country name or ISO code (e.g., "france", "fr", "suisse", "ch")

    Returns:
        List of (city_name, lat, lng) tuples

    Raises:
        ValueError: If country is not recognized
    """
    key = country.strip().lower()
    key = COUNTRY_ALIASES.get(key, key)

    if key not in COUNTRIES:
        available = sorted(set(list(COUNTRIES.keys()) + list(COUNTRY_ALIASES.keys())))
        raise ValueError(
            f"Unknown country: '{country}'. "
            f"Available: {', '.join(available)}"
        )

    return COUNTRIES[key]


def get_country_name(country: str) -> str:
    """Get the canonical country name."""
    key = country.strip().lower()
    key = COUNTRY_ALIASES.get(key, key)
    return key.capitalize()
