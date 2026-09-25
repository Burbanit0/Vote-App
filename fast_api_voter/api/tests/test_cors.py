"""The browser app (localhost:3000) calls the API cross-origin under `npm start`
and in any split-origin deploy. The e2e suite no longer shows this: it serves a
production build, whose calls are same-origin through vite preview's proxy, so
no preflight is ever sent. A regression in main.py's CORSMiddleware would pass
every other gate."""
from fastapi.testclient import TestClient

from api.main import fastapi_app


def test_the_frontend_origin_passes_a_json_post_preflight():
    response = TestClient(fastapi_app).options(
        "/api/v2/election/profile-simulate",
        headers={
            "Origin": "http://localhost:3000",
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "content-type",
        },
    )
    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "http://localhost:3000"
