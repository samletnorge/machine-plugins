"""Tests for merger.py — merging Brreg data per org number."""

from agent_brreg_expert.merger import merge_entities


def test_merge_basic():
    """Entities with matching sub-entities and roles are merged."""
    entities = [
        {
            "organisasjonsnummer": "123456789",
            "navn": "TestAS",
            "organisasjonsform": {"kode": "AS"},
        },
        {
            "organisasjonsnummer": "987654321",
            "navn": "AnnetAS",
            "organisasjonsform": {"kode": "AS"},
        },
    ]
    sub_entities = [
        {
            "organisasjonsnummer": "100000001",
            "overordnetEnhet": "123456789",
            "navn": "Sub1",
        },
        {
            "organisasjonsnummer": "100000002",
            "overordnetEnhet": "123456789",
            "navn": "Sub2",
        },
    ]
    roles = [
        {
            "organisasjonsnummer": "123456789",
            "rollegrupper": [
                {
                    "type": {"kode": "STYR"},
                    "roller": [
                        {"person": {"navn": {"fornavn": "Ola", "etternavn": "Nord"}}}
                    ],
                }
            ],
        },
    ]

    result = merge_entities(entities, sub_entities, roles)

    assert len(result) == 2
    test_as = next(r for r in result if r["organisasjonsnummer"] == "123456789")
    assert len(test_as["_underenheter"]) == 2
    assert len(test_as["_roller"]) == 1
    assert test_as["_underenheter"][0]["navn"] == "Sub1"

    annet_as = next(r for r in result if r["organisasjonsnummer"] == "987654321")
    assert annet_as["_underenheter"] == []
    assert annet_as["_roller"] == []


def test_merge_empty():
    """Empty input returns empty."""
    assert merge_entities([], [], []) == []


def test_merge_frivillig():
    """Frivillig data merges onto matching entity."""
    entities = [
        {"organisasjonsnummer": "111111111", "navn": "Forening"},
    ]
    frivillig = [
        {"orgnr": "111111111", "kategori": "Idrett"},
    ]

    result = merge_entities(entities, [], [], frivillig_records=frivillig)

    assert result[0]["_frivillig"] == {"orgnr": "111111111", "kategori": "Idrett"}


def test_merge_parti():
    """Parti data merges onto matching entity."""
    entities = [
        {"organisasjonsnummer": "222222222", "navn": "Partiet"},
    ]
    parti = [
        {"orgnr": "222222222", "partinavn": "Testpartiet"},
    ]

    result = merge_entities(entities, [], [], parti_records=parti)

    assert result[0]["_parti"] == {"orgnr": "222222222", "partinavn": "Testpartiet"}
