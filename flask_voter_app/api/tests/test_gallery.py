"""Tests for the public scenario gallery on FastAPI (async DB, Phase 4.5.b.2)."""


# ── /featured ──────────────────────────────────────────────────────────────

class TestFeatured:
    def test_empty_when_nothing_featured(self, client):
        r = client.get("/api/v2/scenarios/gallery/featured")
        assert r.status_code == 200, r.text
        assert r.json() == []

    def test_returns_featured_only_sorted_by_views(self, client, seed_gallery):
        seed_gallery(title="Quiet",    is_featured=True,  views=5)
        seed_gallery(title="Hot",      is_featured=True,  views=100)
        seed_gallery(title="Unlisted", is_featured=False, views=50)
        r = client.get("/api/v2/scenarios/gallery/featured")
        assert r.status_code == 200, r.text
        body = r.json()
        assert [s["title"] for s in body] == ["Hot", "Quiet"]
        assert all(s["is_featured"] for s in body)

    def test_limit_clamped_to_20(self, client):
        assert client.get("/api/v2/scenarios/gallery/featured?limit=999").status_code == 422


# ── /{id} ──────────────────────────────────────────────────────────────────

class TestGetScenario:
    def test_returns_detail_and_increments_views(self, client, seed_gallery):
        sid = seed_gallery(title="Cyclic", views=0)
        r = client.get(f"/api/v2/scenarios/gallery/{sid}")
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["title"] == "Cyclic"
        assert body["views"] == 1   # incremented from 0
        assert "params" in body     # detail view includes params

        r2 = client.get(f"/api/v2/scenarios/gallery/{sid}")
        assert r2.json()["views"] == 2

    def test_not_found(self, client):
        assert client.get("/api/v2/scenarios/gallery/99999").status_code == 404


# ── / (list) ───────────────────────────────────────────────────────────────

class TestList:
    def test_default_recent_pagination(self, client, seed_gallery):
        for i in range(25):
            seed_gallery(title=f"S{i}")
        r = client.get("/api/v2/scenarios/gallery")
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["total"] == 25
        assert body["page"] == 1
        assert body["per_page"] == 20
        assert body["pages"] == 2
        assert len(body["items"]) == 20

    def test_per_page_clamped(self, client):
        assert client.get("/api/v2/scenarios/gallery?per_page=999").status_code == 422

    def test_tag_filter(self, client, seed_gallery):
        seed_gallery(title="Arrow1", tags=["arrow"])
        seed_gallery(title="Cond1",  tags=["condorcet"])
        r = client.get("/api/v2/scenarios/gallery?tag=arrow")
        assert r.status_code == 200, r.text
        titles = [s["title"] for s in r.json()["items"]]
        assert "Arrow1" in titles
        assert "Cond1" not in titles

    def test_sort_popular(self, client, seed_gallery):
        seed_gallery(title="Quiet", views=1)
        seed_gallery(title="Hot",   views=100)
        r = client.get("/api/v2/scenarios/gallery?sort=popular")
        assert r.status_code == 200
        assert [s["title"] for s in r.json()["items"]][0] == "Hot"


# ── POST / (create) ────────────────────────────────────────────────────────

class TestCreate:
    def test_creates_and_returns_detail(self, client):
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
        assert body["is_featured"] is False
        assert body["views"] == 0
        assert body["tags"] == ["arrow", "polarization"]
        assert body["params"] == {"num_voters": 200, "ideology": "polarized"}

    def test_tags_capped_at_10(self, client):
        r = client.post("/api/v2/scenarios/gallery", json={
            "title": "Too tagged", "description": "x",
            "tags": [f"tag{i}" for i in range(20)],
        })
        assert r.status_code == 422

    def test_rejects_empty_title(self, client):
        assert client.post("/api/v2/scenarios/gallery", json={
            "title": "", "description": "x",
        }).status_code == 422

    def test_rejects_extra_field(self, client):
        r = client.post("/api/v2/scenarios/gallery", json={
            "title": "x", "description": "y", "is_featured": True,
        })
        assert r.status_code == 422
