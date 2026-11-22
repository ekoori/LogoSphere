# Places without a database: rounding, what a distance gives away, and the
# gazetteer, built here from a few invented lines in GeoNames' formats.
import importlib.util
import math
import zipfile
from pathlib import Path

import pytest

from app.utils import gazetteer, geo

HERE = (-37.768934, 145.043210)


def at(lat, lon, precision='1km'):
    return {'lat': lat, 'lon': lon, 'precision': precision}


@pytest.mark.parametrize('precision,km', [(p, k) for p, k in geo.PIN_SQUARES.items() if k])
def test_a_pin_is_rounded_into_its_square(precision, km):
    for lat, lon in (HERE, (64.1466, -21.9426), (0.0001, -179.99), (35.6895, 139.6917), (-89.95, 12.0)):
        out = geo.rounded(lat, lon, precision)
        assert -90 <= out[0] <= 90 and -180 <= out[1] <= 180
        if abs(lat) < 80:
            assert geo.km_between((lat, lon), out) <= km * math.sqrt(2) / 2 * 1.06


def test_neighbours_in_a_square_become_one_point():
    centre = geo.rounded(*HERE, '1km')
    for d_lat, d_lon in ((0.002, 0.002), (-0.002, 0.001), (0.0, -0.003)):
        assert geo.rounded(centre[0] + d_lat, centre[1] + d_lon, '1km') == centre


def test_exact_is_kept_exact():
    assert geo.rounded(*HERE, 'exact') == HERE


def test_a_distance_tells_the_square_and_band_only():
    centre = geo.square_centre(*HERE, geo.SQUARE_KM)
    probes = [(centre[0] + i * 0.01, centre[1] + j * 0.013) for i in range(-12, 13, 4) for j in range(-12, 13, 4)]
    seen = set()
    for hidden in ((centre[0] + 0.003, centre[1] - 0.004), (centre[0] - 0.003, centre[1] + 0.004)):
        seen.add(tuple(geo.distance(at(*p, 'exact'), at(*hidden, 'exact'))['km'] for p in probes))
    assert len(seen) == 1           # no probe tells two spots in one square apart
    assert set(next(iter(seen))) <= set(geo.BANDS_KM)


def test_a_rough_place_never_claims_to_be_close():
    assert geo.distance(at(*HERE, 'exact'), at(*HERE, 'exact')) == {'km': 2, 'text': 'Within 2 km'}
    assert geo.distance(at(*HERE, '10km'), at(*HERE, '10km'))['km'] == 25
    assert geo.distance(at(*HERE, 'town'), at(*HERE, 'region'))['km'] == 250
    assert geo.distance(at(*HERE), at(*HERE, 'country')) is None
    assert geo.distance(at(*HERE), None) is None
    assert geo.distance(at(*HERE), at(51.5, -0.12))['text'] == 'Over 5000 km away'


def test_only_points_on_earth():
    for lat, lon in ((91, 0), (0, 181), (float('nan'), 0), (float('inf'), 1), (True, 1), ('1', 2), (None, None)):
        assert geo.coordinates(lat, lon) is None
    assert geo.coordinates(0, -180) == (0.0, -180.0)


# -- gazetteer --------------------------------------------------------------
def city(number, name, lat, lon, admin1='07', admin2='', people=0, other_names='', code='PPL'):
    cells = [''] * 19
    for i, value in ((0, number), (1, name), (2, name), (3, other_names), (4, lat), (5, lon), (6, 'P'), (7, code),
                     (8, 'XA'), (10, admin1), (11, admin2), (14, people)):
        cells[i] = str(value)
    return '\t'.join(cells)


@pytest.fixture
def built(tmp_path, monkeypatch):
    def packed(name, member, rows):
        with zipfile.ZipFile(tmp_path / name, 'w') as z:
            z.writestr(member, '\n'.join(rows) + '\n')
            z.writestr('readme.txt', 'ignored')

    (tmp_path / 'countryInfo.txt').write_text(
        '# comment\nXA\tXAA\t1\tXA\tExampleland\tBigton\t1\t2\n', encoding='utf-8')
    (tmp_path / 'admin1CodesASCII.txt').write_text('XA.07\tSouth Vale\tSouth Vale\t9\n', encoding='utf-8')
    (tmp_path / 'admin2Codes.txt').write_text('XA.07.12\tCreek Shire\tCreek Shire\t8\n', encoding='utf-8')
    packed('cities500.zip', 'cities500.txt', [
        city(1, 'Bigton', -37.8, 145.0, people=900000, other_names='Grande Ville'),
        city(2, 'Éllery', -37.77, 145.04, admin2='12', people=12000)])
    packed('XA.zip', 'XA.txt', [
        city(2, 'Éllery', -37.77, 145.04),                                  # already in cities500
        city(3, 'Ellery East', -37.775, 145.06, people=0, code='PPLX'),     # a suburb
        city(4, 'Lostham', -37.7, 145.1, code='PPLH')])                     # gone
    packed('postcodes.zip', 'allCountries.txt', [
        'XA\t39991\tAardpost\tSouth Vale\t07\t\t\t\t\t-37.70\t145.00\t4',
        'XA\t3999\tÉllery\tSouth Vale\t07\t\t\t\t\t-37.77\t145.04\t4',
        'XA\t3999\tFarside\tSouth Vale\t07\t\t\t\t\t-20.00\t120.00\t4'])

    script = Path(__file__).resolve().parents[2] / 'tools' / 'build_places.py'
    spec = importlib.util.spec_from_file_location('build_places', script)
    tool = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(tool)
    out = tmp_path / 'data' / 'places.sqlite'
    assert tool.build(tmp_path, out) == 8       # three towns, a region, a country, three postcodes
    monkeypatch.setenv('PLACES_DB', str(out))


def names(text):
    return [f['name'] for f in gazetteer.search(text)]


def test_finds_places_as_people_type_them(built):
    assert names('ellery')[:2] == ['Éllery', 'Ellery East']
    assert names('grande')[0] == 'Bigton'                   # another of its names
    assert names('bigton exampleland')[0] == 'Bigton'
    assert names('exampleland')[0] == 'Exampleland'
    assert names('3999')[0] == '3999 Éllery'
    assert gazetteer.search('south vale')[0]['precision'] == 'region'
    assert names('lostham') == [] and names('x') == []
    assert gazetteer.search('éllery')[0]['label'] == 'Éllery, Creek Shire, South Vale, Exampleland'


def test_a_whole_postcode_then_the_nearer_one(built):
    assert names('3999') == ['3999 Éllery', '3999 Farside', '39991 Aardpost']
    near_farside = gazetteer.search('3999', near=(-21.0, 121.0))
    assert [f['name'] for f in near_farside] == ['3999 Farside', '3999 Éllery', '39991 Aardpost']


def test_search_words_are_never_syntax(built):
    for text in ('"', 'NOT', 'a* OR b', "x'); DROP TABLE place;--", 'ellery:east', '(((', '^bigton'):
        gazetteer.search(text)
    assert names('bigton')


def test_names_a_pin(built):
    assert gazetteer.nearest(-37.7702, 145.0405)[0]['name'] == 'Éllery'
    first = gazetteer.search('bigton')[0]
    assert gazetteer.get(first['id']) == first
    assert gazetteer.get(999) is None and gazetteer.get('1') is None


def test_works_without_the_data(tmp_path, monkeypatch):
    monkeypatch.setenv('PLACES_DB', str(tmp_path / 'none.sqlite'))
    assert not gazetteer.available()
    assert gazetteer.search('bigton') == [] and gazetteer.nearest(0, 0) == [] and gazetteer.get(1) is None
