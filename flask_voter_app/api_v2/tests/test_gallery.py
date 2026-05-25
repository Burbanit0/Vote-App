"""Tests for Phase 4.5.a.1 — public scenario gallery on FastAPI."""
import pytest
from datetime import datetime, timezone

from fastapi.testclient import TestClient

from app import db, create_app
from app.models import GalleryScenario
from api_v2.core import db as v2_db
from api_v2.core.config import get_settings


@pytest.fixture(scope="function")
def flask_app():
    app = create_app(config_object="config.TestingConfig")
    app.config["TESTING"] = True
    app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///:memory:"
    app.config["JWT_SECRET_KEY"] = "test-secret-key"
    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()


@pytest.fixture(scope="function")
def client(flask_app, monkeypatch):
    monkeypatch.setattr(v2_db, "_app", flask_app)
    monkeypatch.setattr(get_settings(), "jwt_secret_key", "test-secret-key")
    from api_v2.main import app
    with TestClient(app) as c:
        yield c


def _seed(flask_app, **overrides):
    with flask_app.app_context():
        s = GalleryScenario(
            title=overrides.get("title", "Demo scenario"),
            description=overrides.get("description", "A test scenario"),
            params=overrides.get("params", {"num_voters": 100}),
            results_summary=overrides.get("results_summary", {"winner": "A"}),
            tags=overrides.get("tags", ["condorcet", "arrow"]),
            is_featured=overrides.get("is_featured", False),
            views=overrides.get("views", 0),
            created_at=overrides.get("created_at", datetime.now(timezone.utc)),
        )
        db.session.add(s)
        db.session.commit()
        return s.id


# ── /featured ──────────────────────────────────────────────────────────────

class TestFeatured:
    def test_empty_when_nothing_featured(self, client):
        r = client.get("/api/v2/scenarios/gallery/featured")
        assert r.status_code == 200, r.text
        assert r.json() == []

    def test_returns_featured_only_sorted_by_views(self, client, flask_app):
        _seed(flask_app, title="Quiet",   is_featured=True,  views=5)
        _seed(flask_app, title="Hot",     is_featured=True,  views=100)
        _seed(flask_app, title="Unlisted", is_featured=False, views=50)
        r = client.get("/api/v2/scenarios/gallery/featured")
        assert r.status_code == 200, r.text
        body = r.json()
        assert [s["title"] for s in body] == ["Hot", "Quiet"]
        assert all(s["is_featured"] for s in body)

    def test_limit_clamped_to_20(self, client):
        r = client.get("/api/v2/scenarios/gallery/featured?limit=999")
        assert r.status_code == 422


# ── /{id} ──────────────────────────────────────────────────────────────────

class TestGetScenario:
    def test_returns_detail_and_increments_views(self, client, flask_app):
        sid = _seed(flask_app, title="Cyclic", views=0)
        r = client.get(f"/api/v2/scenarios/gallery/{sid}")
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["title"] == "Cyclic"
        assert body["views"] == 1   # incremented from 0
        assert "params" in body     # detail view includes params

        # Hit again — counter increments.
        r2 = client.get(f"/api/v2/scenarios/gallery/{sid}")
        assert r2.json()["views"] == 2

    def test_not_found(self, client):
        r = client.get("/api/v2/scenarios/gallery/99999")
        assert r.status_code == 404


# ── / (list) ───────────────────────────────────────────────────────────────

class TestList:
    def test_default_recent_pagination(self, client, flask_app):
        for i in range(25):
            _seed(flask_app, title=f"S{i}")
        r = client.get("/api/v2/scenarios/gallery")
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["total"] == 25
        assert body["page"] == 1
        assert body["per_page"] == 20
        assert body["pages"] == 2
        assert len(body["items"]) == 20

    def test_per_page_clamped(self, client):
        r = client.get("/api/v2/scenarios/gallery?per_page=999")
        assert r.status_code == 422

    def test_tag_filter(self, client, flask_app):
        _seed(flask_app, title="Arrow1", tags=["arrow"])
        _seed(flask_app, title="Cond1",  tags=["condorcet"])
        r = client.get("/api/v2/scenarios/gallery?tag=arrow")
        assert r.status_code == 200, r.text
        titles = [s["title"] for s in r.json()["items"]]
        assert "Arrow1" in titles
        assert "Cond1" not in titles

    def test_sort_popular(self, client, flask_app):
        _seed(flask_app, title="Quiet", views=1)
        _seed(flask_app, title="Hot",   views=100)
        r = client.get("/api/v2/scenarios/gallery?sort=popular")
        assert r.status_code == 200
        titles = [s["title"] for s in r.json()["items"]]
        assert titles[0] == "Hot"


# ── POST / (create) ────────────────────────────────────────────────────────

class TestCreate:
    def test_creates_and_returns_detail(self, client, flask_app):
        r = client.post("/api/v2/scenarios/gallery", json={
            "title":       "Brand new",
            "description": "A scenario submitted via /api/v2",
            "params":      {"num_voters": 200, "ideology": "polarized"},
            "results_summary": {"winner": "Alice"},
            "tags":        ["arrow", "polarization"],
        })
        assert r.status_code == 201, r.text
        body = r.json()
        assert body["title"] == "Brand new"
        assert body["is_featured"] is False   # always False at creation
        assert body["views"] == 0
        assert body["tags"] == ["arrow", "polarization"]
        assert body["params"] == {"num_voters": 200, "ideology": "polarized"}

    def test_tags_capped_at_10(self, client):
        r = client.post("/api/v2/scenarios/gallery", json={
            "title": "Too tagged", "description": "x",
            "tags": [f"tag{i}" for i in range(20)],
        })
        # Pydantic rejects > 10 tags up front.
        assert r.status_code == 422

    def test_rejects_empty_title(self, client):
        r = client.post("/api/v2/scenarios/gallery", json={
            "title": "", "description": "x",
        })
        assert r.status_code == 422

    def test_rejects_extra_field(self, client):
        r = client.post("/api/v2/scenarios/gallery", json={
            "title": "x", "description": "y", "is_featured": True,
        })
        # `is_featured` is not in the request schema — extra="forbid" → 422.
        assert r.status_code == 422
