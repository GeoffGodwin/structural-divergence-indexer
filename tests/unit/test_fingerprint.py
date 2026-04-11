"""Unit tests for PatternFingerprint and structural hash computation."""

from __future__ import annotations

import pytest

from sdi.patterns.fingerprint import (
    PatternFingerprint,
    compute_structural_hash,
    fingerprint_from_instance,
)


# ---------------------------------------------------------------------------
# compute_structural_hash — normalization and hashing
# ---------------------------------------------------------------------------


def test_identical_structure_same_hash_different_identifiers():
    """Same node types with different identifier text → same hash."""
    d1 = {
        "type": "try_statement",
        "children": [{"type": "identifier", "text": "foo"}],
    }
    d2 = {
        "type": "try_statement",
        "children": [{"type": "identifier", "text": "bar"}],  # different name
    }
    r1 = compute_structural_hash(d1)
    r2 = compute_structural_hash(d2)
    assert r1 is not None
    assert r2 is not None
    assert r1 == r2


def test_different_node_types_different_hash():
    """Different root node types → different hashes."""
    d1 = {"type": "try_statement", "children": []}
    d2 = {"type": "with_statement", "children": []}
    r1 = compute_structural_hash(d1)
    r2 = compute_structural_hash(d2)
    assert r1 is not None
    assert r2 is not None
    assert r1 != r2


def test_different_child_structure_different_hash():
    """Same root type but different child structure → different hashes."""
    d1 = {"type": "try_statement", "children": [{"type": "except_clause"}]}
    d2 = {"type": "try_statement", "children": [{"type": "finally_clause"}]}
    r1 = compute_structural_hash(d1)
    r2 = compute_structural_hash(d2)
    assert r1 is not None
    assert r2 is not None
    assert r1 != r2


def test_literal_stripping_string():
    """Same structure with different string literal values → same hash."""
    d1 = {
        "type": "try_statement",
        "children": [{"type": "string", "text": '"hello"'}],
    }
    d2 = {
        "type": "try_statement",
        "children": [{"type": "string", "text": '"world"'}],
    }
    r1 = compute_structural_hash(d1)
    r2 = compute_structural_hash(d2)
    assert r1 == r2


def test_literal_stripping_integer():
    """Same structure with different integer literals → same hash."""
    d1 = {"type": "return_statement", "children": [{"type": "integer", "text": "1"}]}
    d2 = {"type": "return_statement", "children": [{"type": "integer", "text": "99"}]}
    assert compute_structural_hash(d1) == compute_structural_hash(d2)


def test_literal_stripping_float():
    """Same structure with different float literals → same hash."""
    d1 = {"type": "assignment", "children": [{"type": "float", "text": "1.5"}]}
    d2 = {"type": "assignment", "children": [{"type": "float", "text": "3.14"}]}
    assert compute_structural_hash(d1) == compute_structural_hash(d2)


def test_literal_stripping_boolean():
    """True and false literal nodes both normalize to _BOOL_ token."""
    d1 = {"type": "try_statement", "children": [{"type": "true"}]}
    d2 = {"type": "try_statement", "children": [{"type": "false"}]}
    assert compute_structural_hash(d1) == compute_structural_hash(d2)


def test_min_nodes_filters_small_patterns():
    """A single-node descriptor below min_nodes threshold returns None."""
    d = {"type": "identifier", "text": "x"}  # 1 node
    result = compute_structural_hash(d, min_nodes=5)
    assert result is None


def test_min_nodes_default_one_passes_single_node():
    """Default min_nodes=1 allows single-node descriptors."""
    d = {"type": "try_statement"}
    result = compute_structural_hash(d, min_nodes=1)
    assert result is not None
    hash_val, node_count = result
    assert node_count == 1


def test_min_nodes_passes_when_count_equals_threshold():
    """Descriptor with node_count == min_nodes passes the filter."""
    d = {
        "type": "try_statement",
        "children": [
            {"type": "except_clause", "children": []},
            {"type": "finally_clause", "children": []},
        ],
    }  # 3 nodes
    result = compute_structural_hash(d, min_nodes=3)
    assert result is not None


def test_empty_descriptor_returns_none():
    """Empty dict is not a valid descriptor — returns None."""
    assert compute_structural_hash({}) is None


def test_descriptor_without_type_key_returns_none():
    """Descriptor without 'type' key is invalid — returns None."""
    assert compute_structural_hash({"children": []}) is None


def test_returns_tuple_hash_and_node_count():
    """Return value is a (hash_str, int) tuple when descriptor is valid."""
    d = {"type": "try_statement", "children": [{"type": "except_clause"}]}
    result = compute_structural_hash(d)
    assert result is not None
    hash_val, node_count = result
    assert isinstance(hash_val, str)
    assert len(hash_val) == 16  # SHA-256 hexdigest[:16]
    assert node_count == 2  # try_statement + except_clause


# ---------------------------------------------------------------------------
# PatternFingerprint — creation and equality
# ---------------------------------------------------------------------------


def test_fingerprint_equality_based_on_hash():
    """Two fingerprints with the same structural_hash are equal."""
    fp1 = PatternFingerprint(
        category="error_handling", structural_hash="abc123", node_count=10
    )
    fp2 = PatternFingerprint(
        category="error_handling", structural_hash="abc123", node_count=99
    )
    assert fp1 == fp2


def test_fingerprint_inequality_different_hash():
    """Two fingerprints with different structural hashes are not equal."""
    fp1 = PatternFingerprint(
        category="error_handling", structural_hash="abc123", node_count=10
    )
    fp2 = PatternFingerprint(
        category="logging", structural_hash="def456", node_count=10
    )
    assert fp1 != fp2


def test_fingerprint_hashable():
    """PatternFingerprint can be used in sets and as dict keys."""
    fp1 = PatternFingerprint(category="error_handling", structural_hash="abc123")
    fp2 = PatternFingerprint(category="logging", structural_hash="abc123")
    # Same hash → same set entry
    assert len({fp1, fp2}) == 1


def test_fingerprint_default_node_count_zero():
    """node_count defaults to 0 when not provided."""
    fp = PatternFingerprint(category="error_handling", structural_hash="abc123")
    assert fp.node_count == 0


# ---------------------------------------------------------------------------
# fingerprint_from_instance
# ---------------------------------------------------------------------------


def test_fingerprint_from_instance_basic():
    """Creates a PatternFingerprint from a standard pattern_instance dict."""
    instance = {
        "category": "error_handling",
        "ast_hash": "abcd1234ef567890",
        "location": {"line": 10, "col": 0},
    }
    fp = fingerprint_from_instance(instance, min_nodes=1)
    assert fp is not None
    assert fp.category == "error_handling"
    assert fp.structural_hash == "abcd1234ef567890"


def test_fingerprint_from_instance_filtered_by_node_count():
    """Instance with node_count below min_nodes is filtered out (returns None)."""
    instance = {
        "category": "error_handling",
        "ast_hash": "abcd1234ef567890",
        "location": {"line": 1, "col": 0},
        "node_count": 2,
    }
    fp = fingerprint_from_instance(instance, min_nodes=5)
    assert fp is None


def test_fingerprint_from_instance_absent_node_count_passes():
    """Absent node_count always passes the min_nodes filter."""
    instance = {
        "category": "error_handling",
        "ast_hash": "abcd1234ef567890",
        "location": {"line": 1, "col": 0},
        # No 'node_count' key
    }
    fp = fingerprint_from_instance(instance, min_nodes=100)
    assert fp is not None


def test_fingerprint_from_instance_node_count_equals_threshold_passes():
    """node_count exactly equal to min_nodes passes the filter."""
    instance = {
        "category": "logging",
        "ast_hash": "xyz987",
        "location": {"line": 5, "col": 0},
        "node_count": 5,
    }
    fp = fingerprint_from_instance(instance, min_nodes=5)
    assert fp is not None


def test_fingerprint_from_instance_node_count_stored():
    """node_count from instance is reflected in the fingerprint."""
    instance = {
        "category": "data_access",
        "ast_hash": "da_hash_001",
        "location": {"line": 1, "col": 0},
        "node_count": 12,
    }
    fp = fingerprint_from_instance(instance, min_nodes=5)
    assert fp is not None
    assert fp.node_count == 12


# ---------------------------------------------------------------------------
# compute_structural_hash — deeply nested serialized form verification
# ---------------------------------------------------------------------------


def test_deeply_nested_descriptor_produces_expected_serialized_hash():
    """compute_structural_hash on a 5-level descriptor produces the exact expected hash.

    Validates that _normalize_serialize correctly recurses through all node types,
    substituting identifiers with _ID_, literals with type tokens, and producing
    a deterministic string that is then SHA-256 hashed.

    Descriptor structure:
        function_definition
            name ("my_func")                  → _ID_
            parameters
                identifier ("self")           → _ID_
                identifier ("value")          → _ID_
            block
                try_statement
                    except_clause
                        identifier ("Error")  → _ID_
                        block
                            return_statement
                                none          → _NONE_

    Expected normalized form:
        function_definition(_ID_,parameters(_ID_,_ID_),block(try_statement(except_clause(_ID_,block(return_statement(_NONE_))))))
    """
    import hashlib

    descriptor = {
        "type": "function_definition",
        "children": [
            {"type": "name", "text": "my_func"},
            {
                "type": "parameters",
                "children": [
                    {"type": "identifier", "text": "self"},
                    {"type": "identifier", "text": "value"},
                ],
            },
            {
                "type": "block",
                "children": [
                    {
                        "type": "try_statement",
                        "children": [
                            {
                                "type": "except_clause",
                                "children": [
                                    {"type": "identifier", "text": "Error"},
                                    {
                                        "type": "block",
                                        "children": [
                                            {
                                                "type": "return_statement",
                                                "children": [
                                                    {"type": "none", "text": "None"}
                                                ],
                                            }
                                        ],
                                    },
                                ],
                            }
                        ],
                    }
                ],
            },
        ],
    }

    # Trace through _normalize_serialize manually to derive the expected string:
    # - "name" is in _IDENTIFIER_TYPES → "_ID_"
    # - "identifier" is in _IDENTIFIER_TYPES → "_ID_"
    # - "none" is in _LITERAL_TOKENS → "_NONE_"
    # All other types are kept verbatim and wrapped with their children.
    expected_normalized = (
        "function_definition("
        "_ID_,"
        "parameters(_ID_,_ID_),"
        "block(try_statement(except_clause(_ID_,block(return_statement(_NONE_)))))"
        ")"
    )
    expected_hash = hashlib.sha256(expected_normalized.encode()).hexdigest()[:16]
    # 12 nodes: function_definition, name, parameters, identifier×2, block (outer),
    # try_statement, except_clause, identifier (Error), block (inner),
    # return_statement, none
    expected_node_count = 12

    result = compute_structural_hash(descriptor)
    assert result is not None, "compute_structural_hash returned None for a 12-node descriptor"
    hash_val, node_count = result
    assert hash_val == expected_hash, (
        f"Hash mismatch — normalized form may have changed.\n"
        f"Expected: {expected_normalized!r}\n"
        f"Expected hash: {expected_hash!r}\n"
        f"Got hash: {hash_val!r}"
    )
    assert node_count == expected_node_count


def test_name_node_type_treated_as_identifier():
    """'name' node type is normalized to _ID_ the same as 'identifier'."""
    d_name = {"type": "try_statement", "children": [{"type": "name", "text": "foo"}]}
    d_ident = {"type": "try_statement", "children": [{"type": "identifier", "text": "foo"}]}
    assert compute_structural_hash(d_name) == compute_structural_hash(d_ident)


def test_none_and_null_literal_types_normalize_to_same_token():
    """Both 'none' and 'null' node types normalize to _NONE_."""
    d_none = {"type": "return_statement", "children": [{"type": "none"}]}
    d_null = {"type": "return_statement", "children": [{"type": "null"}]}
    assert compute_structural_hash(d_none) == compute_structural_hash(d_null)
