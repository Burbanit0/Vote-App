"""
test_gallery.py — Tests for the public scenario gallery.
"""
import pytest
from app import db
from app.models import GalleryScenario


# ── Fixtures ──────────────────────────────────────────────────────────────────

def make_scenario(app, **kwargs) -> int:
    """Helper: insert one GalleryScenario and return its ID."""
    with app.app_context():
        defaults = dict(
            title="Test scenario",
            description="A test description",
            params={"candidates": ["A", "B"], "num_voters": 100},
            results_summary={"condorcet_winner": "A", "winners": {"plurality": "A"}},
            tags=["test"],
            is_featured=False,
        )
        defaults.update(kwargs)
        s = GalleryScenario(**defaults)
        db.session.add(s)
        db.session.commit()
        return s.id  # return only the ID (ORM object is detached after context exits)


def seed_n(app, n: int) -> list[int]:
    """Insert n scenarios and return their IDs."""
    ids = []
    with app.app_context():
        for i in range(n):
            s = GalleryScenario(
                title=f"Scenario {i}",
                description=f"Description {i}",
                params={},
                results_summary={"condorcet_winner": None, "winners": {}},
                tags=["tag-a"] if i % 2 == 0 else ["tag-b"],
                is_featured=(i < 2),
            )
            db.session.add(s)
        db.session.commit()
        with app.app_context():
            ids = [s.id for s in GalleryScenario.query.all()]
    return ids


# ── GET /api/scenarios/gallery/ — listing ─────────────────────────────────────

def test_list_returns_200(client):
    resp = client.get("/api/scenarios/gallery/")
    assert resp.status_code == 200


def test_list_response_structure(client):
    data = client.get("/api/scenarios/gallery/").get_json()
    for key in ("items", "total", "page", "per_page", "pages"):
        assert key in data


def test_list_empty_gallery(client):
    data = client.get("/api/scenarios/gallery/").get_json()
    assert data["total"] == 0
    assert data["items"] == []
    assert data["pages"] == 1   # at least 1 page even when empty


# ── Pagination ────────────────────────────────────────────────────────────────

def test_pagination_limit(client, app):
    seed_n(app, 25)
    data = client.get("/api/scenarios/gallery/?per_page=10").get_json()
    assert len(data["items"]) == 10
    assert data["per_page"] == 10
    assert data["total"] == 25
    assert data["pages"] == 3


def test_pagination_page2(client, app):
    seed_n(app, 25)
    page1 = client.get("/api/scenarios/gallery/?per_page=10&page=1").get_json()
    page2 = client.get("/api/scenarios/gallery/?per_page=10&page=2").get_json()
    ids_p1 = {s["id"] for s in page1["items"]}
    ids_p2 = {s["id"] for s in page2["items"]}
    assert len(ids_p2) == 10
    assert ids_p1.isdisjoint(ids_p2)   # no overlap between pages


def test_pagination_last_page(client, app):
    seed_n(app, 25)
    data = client.get("/api/scenarios/gallery/?per_page=10&page=3").get_json()
    assert len(data["items"]) == 5   # 25 - 20 = 5 remaining


def test_pagination_beyond_last_page(client, app):
    seed_n(app, 5)
    data = client.get("/api/scenarios/gallery/?per_page=10&page=99").get_json()
    assert data["items"] == []
    assert data["total"] == 5


def test_per_page_capped_at_50(client, app):
    seed_n(app, 60)
    data = client.get("/api/scenarios/gallery/?per_page=9999").get_json()
    assert len(data["items"]) <= 50


# ── Sorting ───────────────────────────────────────────────────────────────────

def test_sort_recent_default(client, app):
    seed_n(app, 5)
    data = client.get("/api/scenarios/gallery/").get_json()
    dates = [s["created_at"] for s in data["items"]]
    assert dates == sorted(dates, reverse=True)


def test_sort_popular(client, app):
    # We can't increment views via fixture easily, just verify it doesn't crash
    seed_n(app, 5)
    resp = client.get("/api/scenarios/gallery/?sort=popular")
    assert resp.status_code == 200


def test_sort_featured(client, app):
    seed_n(app, 5)    # first 2 are featured
    data = client.get("/api/scenarios/gallery/?sort=featured").get_json()
    for item in data["items"]:
        assert item["is_featured"] is True


# ── Tag filtering ─────────────────────────────────────────────────────────────

def test_filter_by_tag(client, app):
    seed_n(app, 10)    # even=tag-a, odd=tag-b
    data = client.get("/api/scenarios/gallery/?tag=tag-a").get_json()
    assert data["total"] == 5
    for item in data["items"]:
        assert "tag-a" in item["tags"]


def test_filter_unknown_tag(client, app):
    seed_n(app, 5)
    data = client.get("/api/scenarios/gallery/?tag=nonexistent").get_json()
    assert data["total"] == 0
    assert data["items"] == []


# ── GET /api/scenarios/gallery/featured ──────────────────────────────────────

def test_featured_returns_200(client):
    resp = client.get("/api/scenarios/gallery/featured")
    assert resp.status_code == 200


def test_featured_only_returns_featured(client, app):
    seed_n(app, 10)   # first 2 are featured
    data = client.get("/api/scenarios/gallery/featured").get_json()
    assert isinstance(data, list)
    for item in data:
        assert item["is_featured"] is True


def test_featured_max_6(client, app):
    seed_n(app, 10)
    data = client.get("/api/scenarios/gallery/featured").get_json()
    assert len(data) <= 6


# ── GET /api/scenarios/gallery/<id> — views increment ────────────────────────

def test_get_by_id_returns_200(client, app):
    sid = make_scenario(app)
    resp = client.get(f"/api/scenarios/gallery/{sid}")
    assert resp.status_code == 200


def test_get_by_id_includes_params(client, app):
    sid = make_scenario(app, params={"candidates": ["X", "Y"], "num_voters": 42})
    data = client.get(f"/api/scenarios/gallery/{sid}").get_json()
    assert "params" in data
    assert data["params"]["num_voters"] == 42


def test_views_increments_on_each_get(client, app):
    sid = make_scenario(app)
    assert client.get(f"/api/scenarios/gallery/{sid}").get_json()["views"] == 1
    assert client.get(f"/api/scenarios/gallery/{sid}").get_json()["views"] == 2
    assert client.get(f"/api/scenarios/gallery/{sid}").get_json()["views"] == 3


def test_get_unknown_id_returns_404(client):
    resp = client.get("/api/scenarios/gallery/99999")
    assert resp.status_code == 404


# ── POST /api/scenarios/gallery/ ─────────────────────────────────────────────

def test_create_returns_201(client):
    resp = client.post("/api/scenarios/gallery/", json={
        "title":           "My scenario",
        "description":     "An interesting test",
        "params":          {"candidates": ["A", "B"]},
        "results_summary": {"condorcet_winner": "A"},
        "tags":            ["test", "plurality"],
    })
    assert resp.status_code == 201


def test_create_response_has_id(client):
    resp = client.post("/api/scenarios/gallery/", json={
        "title": "T", "description": "D",
    })
    data = resp.get_json()
    assert "id" in data
    assert isinstance(data["id"], int)


def test_create_missing_title_returns_400(client):
    resp = client.post("/api/scenarios/gallery/", json={"description": "D"})
    assert resp.status_code == 400


def test_create_missing_description_returns_400(client):
    resp = client.post("/api/scenarios/gallery/", json={"title": "T"})
    assert resp.status_code == 400


def test_create_is_not_featured_by_default(client):
    resp = client.post("/api/scenarios/gallery/", json={"title": "T", "description": "D"})
    assert resp.get_json()["is_featured"] is False


def test_create_tags_capped_at_10(client):
    resp = client.post("/api/scenarios/gallery/", json={
        "title": "T", "description": "D",
        "tags": [f"tag{i}" for i in range(20)],  # 20 tags
    })
    assert len(resp.get_json()["tags"]) <= 10


def test_create_and_retrieve(client):
    client.post("/api/scenarios/gallery/", json={
        "title": "Retrieve me", "description": "Test", "tags": ["abc"],
    })
    data = client.get("/api/scenarios/gallery/").get_json()
    titles = [s["title"] for s in data["items"]]
    assert "Retrieve me" in titles


# ── Seed script ───────────────────────────────────────────────────────────────

def test_seed_inserts_exactly_6_scenarios(app):
    from scripts.seed_gallery import seed
    n = seed(app=app, clear=True)
    assert n == 6
    with app.app_context():
        assert GalleryScenario.query.count() == 6


def test_seed_all_featured(app):
    from scripts.seed_gallery import seed
    seed(app=app, clear=True)
    with app.app_context():
        featured = GalleryScenario.query.filter_by(is_featured=True).count()
        assert featured == 6


def test_seed_idempotent(app):
    from scripts.seed_gallery import seed
    seed(app=app, clear=True)
    seed(app=app, clear=True)
    with app.app_context():
        assert GalleryScenario.query.count() == 6  # not 12


def test_seed_scenario_titles(app):
    from scripts.seed_gallery import seed
    seed(app=app, clear=True)
    with app.app_context():
        titles = {s.title for s in GalleryScenario.query.all()}
    expected = {
        "Le paradoxe de Condorcet",
        "Vote blanc décisif",
        "L'effet du vote utile",
        "Borda contre Schulze",
        "Élection fragmentée",
        "STAR contre Score simple",
    }
    assert expected == titles
