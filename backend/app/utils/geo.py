# Places as arithmetic: rounding points, and distances that can't be turned back
# into addresses. Pure: no database (that's app/utils/places.py).
#
# A pin is rounded to its square before it is ever stored. Distances are then
# worked out between 1 km squares whatever is stored, and said in bands, so
# moving your own place about to triangulate someone finds a square at best.
import math

EARTH_KM = 6371.0088
KM_A_DEGREE = 111.32
SQUARE_KM = 1.0         # nothing finer ever goes into a distance

# A pin's precision -> the square it is rounded to (km; None: kept as it is).
PIN_SQUARES = {'exact': None, '1km': 1.0, '5km': 5.0, '10km': 10.0, '100km': 100.0}
# How far off a place may be, by precision. Named ones come from the gazetteer.
# A country is no measure of nearness, so it gives no distance.
ROUGH_KM = {'exact': 0.1, '1km': 0.7, '5km': 3.5, '10km': 7.0, '100km': 70.0,
            'postcode': 3.0, 'town': 4.0, 'region': 100.0, 'country': None}
BANDS_KM = (2, 5, 10, 25, 50, 100, 250, 500, 1000, 5000)


def coordinates(lat, lon):
    """(lat, lon) as floats, or None when they aren't a point on Earth."""
    if any(isinstance(v, bool) or not isinstance(v, (int, float)) for v in (lat, lon)):
        return None
    if not (-90 <= lat <= 90 and -180 <= lon <= 180):      # NaN fails this too
        return None
    return float(lat), float(lon)


def square_centre(lat, lon, km):
    """The centre of the point's square on a fixed grid: the same for every point in it."""
    step = km / KM_A_DEGREE
    lat = max(-89.9, min(89.9, (math.floor(lat / step) + 0.5) * step))
    step_lon = min(360.0, step / math.cos(math.radians(lat)))
    lon = (math.floor((lon + 180.0) / step_lon) + 0.5) * step_lon - 180.0
    return round(lat, 6), round(min(lon, 180.0), 6)


def rounded(lat, lon, precision):
    """A pin as it may be stored."""
    km = PIN_SQUARES[precision]
    return square_centre(lat, lon, km) if km else (round(lat, 6), round(lon, 6))


def km_between(one, other):
    lat1, lon1, lat2, lon2 = map(math.radians, (one[0], one[1], other[0], other[1]))
    a = math.sin((lat2 - lat1) / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin((lon2 - lon1) / 2) ** 2
    return 2 * EARTH_KM * math.asin(min(1.0, math.sqrt(a)))


def distance(one, other):
    """How far apart two places are, as it may be told: {km, text}, where km is
    the band's edge and never the distance; None when that can't be said."""
    if not one or not other:
        return None
    ends = []
    rough = 0.0
    for place in (one, other):
        point = coordinates(place.get('lat'), place.get('lon'))
        off_by = ROUGH_KM.get(place.get('precision'))
        if point is None or off_by is None:
            return None
        rough += off_by
        ends.append(square_centre(*point, SQUARE_KM))
    km = max(km_between(*ends), rough)
    for edge in BANDS_KM:
        if km <= edge:
            return {'km': edge, 'text': f'Within {edge} km'}
    return {'km': 20040, 'text': f'Over {BANDS_KM[-1]} km away'}
