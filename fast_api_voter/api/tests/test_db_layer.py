"""Phase 4.5.b.2 — smoke test for the new Flask-independent async DB layer."""
import pytest
import pytest_asyncio
from sqlalchemy import select
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.pool import StaticPool

from api.db import Base, GalleryScenario, SimulationScenario, User
from api.db import session as db_session


@pytest_asyncio.fixture
async def session():
    """In-memory aiosqlite engine with the schema created; swapped into the
    module-level engine so async_session_maker() uses it."""
    engine = create_async_engine(
        "sqlite+aiosqlite://",
        poolclass=StaticPool,
        connect_args={"check_same_thread": False},
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    db_session.set_engine(engine)
    async with db_session.async_session_maker()() as s:
        yield s
    await engine.dispose()


@pytest.mark.asyncio
async def test_user_roundtrip_and_password_alias(session):
    session.add(User(username="alice", email="a@x.io", hashed_password="hpw", role="User"))
    await session.commit()

    got = (await session.execute(select(User).where(User.email == "a@x.io"))).scalar_one()
    assert got.hashed_password == "hpw"
    assert got.password_hash == "hpw"      # legacy alias attribute
    assert got.is_active is True            # python default applied
    assert got.is_superuser is False


@pytest.mark.asyncio
async def test_user_column_is_password_hash(session):
    # The attribute is hashed_password but the DB column must stay password_hash.
    cols = {c.name for c in User.__table__.columns}
    assert "password_hash" in cols
    assert "hashed_password" not in cols


@pytest.mark.asyncio
async def test_scenario_and_gallery_roundtrip(session):
    session.add(User(username="bob", email="b@x.io", hashed_password="h", role="User"))
    await session.commit()
    uid = (await session.execute(select(User.id).where(User.email == "b@x.io"))).scalar_one()

    session.add(SimulationScenario(user_id=uid, name="S1", config={"n": 1}))
    session.add(GalleryScenario(title="G1", description="d"))
    await session.commit()

    sc = (await session.execute(select(SimulationScenario))).scalar_one()
    assert sc.to_summary()["name"] == "S1"
    g = (await session.execute(select(GalleryScenario))).scalar_one()
    assert g.to_dict()["tags"] == []       # list default
    assert g.views == 0
