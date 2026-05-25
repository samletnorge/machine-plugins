import pytest
from memory_support.in_memory_storage import InMemoryStorage


@pytest.fixture
def storage():
    return InMemoryStorage()
