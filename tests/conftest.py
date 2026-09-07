import os
import sys

import pytest_asyncio

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_API_APP_DIR = os.path.join(_ROOT, "apps", "api")

if _API_APP_DIR not in sys.path:
    sys.path.insert(0, _API_APP_DIR)


@pytest_asyncio.fixture
async def db_session():
    from app.db.session import AsyncSessionLocal

    async with AsyncSessionLocal() as session:
        yield session
        await session.rollback()
