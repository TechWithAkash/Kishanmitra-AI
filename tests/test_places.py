"""Place search, GPS reverse-geocoding and place-name guessing (network mocked)."""

import pytest
import requests

from kisanmitra import places


class FakeResponse:
    def __init__(self, data, status=200):
        self._data, self.status_code = data, status

    def raise_for_status(self):
        if self.status_code >= 400:
            raise requests.HTTPError(str(self.status_code))

    def json(self):
        return self._data


def geocode_payload(*items):
    return {"results": [{"name": n, "latitude": la, "longitude": lo, "admin1": s, "admin2": d} for n, la, lo, s, d in items]}


def test_search_returns_places_with_district_and_state(monkeypatch):
    monkeypatch.setattr(places.requests, "get", lambda *a, **k: FakeResponse(
        geocode_payload(("Satānā", 20.59, 74.2, "Maharashtra", "Nashik"), ("Satāna", 27.3, 76.7, "Rajasthan", "Alwar"))))
    hits = places.search("Satana")
    assert [h.label() for h in hits] == ["Satānā, Nashik, Maharashtra", "Satāna, Alwar, Rajasthan"]


def test_search_never_raises_when_the_service_is_down(monkeypatch):
    def boom(*a, **k):
        raise requests.ConnectionError("down")
    monkeypatch.setattr(places.requests, "get", boom)
    assert places.search("Satana") == []
    assert places.search("a") == []  # too short: no request at all


def test_reverse_geocodes_gps_to_village_district_state(monkeypatch):
    monkeypatch.setattr(places.time, "sleep", lambda s: None)
    monkeypatch.setattr(places.requests, "get", lambda *a, **k: FakeResponse({"address": {
        "suburb": "Shalimar", "city": "Nashik", "state_district": "Nashik District", "state": "Maharashtra"}}))
    p = places.reverse(20.0012, 73.7868)
    assert (p.name, p.district, p.state, p.source) == ("Shalimar", "Nashik", "Maharashtra", "gps")
    assert (p.lat, p.lon) == (20.0012, 73.7868)  # exact GPS coordinates are kept for the weather lookup


def test_reverse_keeps_coordinates_when_lookup_fails(monkeypatch):
    monkeypatch.setattr(places.time, "sleep", lambda s: None)
    def boom(*a, **k):
        raise requests.ConnectionError("down")
    monkeypatch.setattr(places.requests, "get", boom)
    p = places.reverse(19.1234, 73.5678)
    assert p.lat == 19.1234 and p.state is None and "19.12" in p.name


def test_reverse_rejects_invalid_coordinates():
    with pytest.raises(ValueError):
        places.reverse(120.0, 10.0)


def test_guess_accepts_only_exact_name_matches(monkeypatch):
    monkeypatch.setattr(places, "search", lambda q, limit=6, language="en": [places.Place("Rainpur", 1, 2, "Bihar", "X")])
    # "Rain" fuzzy-matches "Rainpur" in the geocoder but must not be taken for a place
    assert places.guess_from_text("chances of Rain tomorrow", ignore=set()) is None
    monkeypatch.setattr(places, "search", lambda q, limit=6, language="en": [places.Place("Satānā", 20.5, 74.2, "Maharashtra", "Nashik")])
    assert places.guess_from_text("weather in Satana", ignore=set()).name == "Satānā"


def test_known_words_are_not_sent_to_the_geocoder(monkeypatch):
    called = []
    monkeypatch.setattr(places, "search", lambda q, limit=6, language="en": called.append(q) or [])
    places.guess_from_text("tomato price in nashik today weather", ignore={"tomato", "nashik"})
    assert called == []


def test_agmarknet_state_spelling():
    assert places.Place("Delhi", state="Delhi").mandi_state == "NCT of Delhi"
    assert places.Place("Pune", state="Maharashtra").mandi_state == "Maharashtra"
