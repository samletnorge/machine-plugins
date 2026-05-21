import pytest
from machine_core.plugins.memory_support.in_memory_storage import InMemoryStorage


@pytest.fixture
def storage():
    return InMemoryStorage()
