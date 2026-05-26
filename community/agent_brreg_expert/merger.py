"""Merge Brreg registry data per organisation number."""

from __future__ import annotations

from typing import Any


def merge_entities(
    entities: list[dict[str, Any]],
    sub_entities: list[dict[str, Any]],
    roles: list[dict[str, Any]],
    frivillig_records: list[dict[str, Any]] | None = None,
    parti_records: list[dict[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    """Merge sub-entities, roles, frivillig, and parti data onto main entities.

    Args:
        entities: Main entity records from Enhetsregisteret.
        sub_entities: Sub-entity records (have 'overordnetEnhet' linking to parent).
        roles: Role records (keyed by 'organisasjonsnummer').
        frivillig_records: Voluntary org records (keyed by 'orgnr').
        parti_records: Political party records (keyed by 'orgnr').

    Returns:
        List of merged entity dicts with _underenheter, _roller, _frivillig, _parti fields.
    """
    if not entities:
        return []

    # Index sub-entities by parent org number
    sub_by_parent: dict[str, list[dict[str, Any]]] = {}
    for sub in sub_entities:
        parent = sub.get("overordnetEnhet", "")
        if parent:
            sub_by_parent.setdefault(parent, []).append(sub)

    # Index roles by org number
    roles_by_org: dict[str, list[dict[str, Any]]] = {}
    for role_record in roles:
        org_nr = role_record.get("organisasjonsnummer", "")
        if org_nr:
            roles_by_org.setdefault(org_nr, []).append(role_record)

    # Index frivillig by org number
    frivillig_by_org: dict[str, dict[str, Any]] = {}
    if frivillig_records:
        for record in frivillig_records:
            org_nr = record.get("orgnr", "")
            if org_nr:
                frivillig_by_org[org_nr] = record

    # Index parti by org number
    parti_by_org: dict[str, dict[str, Any]] = {}
    if parti_records:
        for record in parti_records:
            org_nr = record.get("orgnr", "")
            if org_nr:
                parti_by_org[org_nr] = record

    # Merge
    merged: list[dict[str, Any]] = []
    for entity in entities:
        org_nr = entity.get("organisasjonsnummer", "")
        doc = {**entity}
        doc["_underenheter"] = sub_by_parent.get(org_nr, [])
        doc["_roller"] = roles_by_org.get(org_nr, [])

        if org_nr in frivillig_by_org:
            doc["_frivillig"] = frivillig_by_org[org_nr]
        if org_nr in parti_by_org:
            doc["_parti"] = parti_by_org[org_nr]

        merged.append(doc)

    return merged
