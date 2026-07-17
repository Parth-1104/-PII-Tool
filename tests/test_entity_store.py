import json
import pytest
from src.anonymizers.entity_store import EntityMappingStore
from src.anonymizers.fake_operators import StatefulFakerOperator


def test_deterministic_mapping_consistency(entity_store):
    faker_op = StatefulFakerOperator(entity_store=entity_store)

    # Generate synthetic alternative for "John Doe"
    fake1 = faker_op.generate("PERSON", "John Doe")
    
    # Generate again for exact same string
    fake2 = faker_op.generate("PERSON", "John Doe")
    assert fake1 == fake2

    # Generate for normalized variation (different spacing / case)
    fake3 = faker_op.generate("PERSON", "   john doe  ")
    assert fake1 == fake3

    # Generate for a completely different person
    fake_other = faker_op.generate("PERSON", "Alice Smith")
    assert fake_other != fake1


def test_uppercase_preservation(entity_store):
    faker_op = StatefulFakerOperator(entity_store=entity_store)
    
    fake_upper = faker_op.generate("PERSON", "JOHN DOE")
    assert fake_upper.isupper()
    
    # Verify mapping store stored the base mapped value correctly
    assert entity_store.get_fake("PERSON", "John Doe") == fake_upper


def test_entity_store_persistence(tmp_path):
    vault_path = tmp_path / "persistent_vault.json"
    store1 = EntityMappingStore(persistence_path=str(vault_path))
    
    # Register synthetic mappings
    store1.register_fake("EMAIL_ADDRESS", "test@acme.com", "fake@domain.org")
    store1.register_fake("PHONE_NUMBER", "555-0199", "555-8888")
    
    # Ensure file was created and written
    assert vault_path.exists()
    
    # Load into a fresh store instance pointing to same vault path
    store2 = EntityMappingStore(persistence_path=str(vault_path))
    assert store2.get_fake("EMAIL_ADDRESS", "test@acme.com") == "fake@domain.org"
    assert store2.get_fake("PHONE_NUMBER", "555-0199") == "555-8888"


def test_entity_store_metrics(entity_store):
    faker_op = StatefulFakerOperator(entity_store=entity_store)
    faker_op.generate("PERSON", "John Doe")
    faker_op.generate("PERSON", "John Doe")  # repeated query
    faker_op.generate("EMAIL_ADDRESS", "john@doe.com")
    
    metrics = entity_store.get_metrics()
    assert metrics["PERSON"] == 2
    assert metrics["EMAIL_ADDRESS"] == 1
