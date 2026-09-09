"""
RFC 7396 (JSON Merge Patch) helpers used by `lep dynamo update`.

The Dynamo update route applies a merge patch to the current user spec:
``null`` deletes a key, nested objects merge recursively, and arrays are
replaced whole. :func:`build_merge_patch` derives such a patch from two plain
dicts (the current spec and the desired spec), emitting only changed paths,
exactly like the dashboard's edit overlay.
"""

from copy import deepcopy
from typing import Any, Dict

from pydantic import BaseModel


def spec_to_dict(spec: BaseModel) -> Dict[str, Any]:
    """JSON-ready dict of a spec, aliases honored and ``None`` fields dropped."""
    return spec.model_dump(mode="json", exclude_none=True, by_alias=True)


def build_merge_patch(original: Any, desired: Any) -> Dict[str, Any]:
    """
    Return the merge patch that turns ``original`` into ``desired``.

    - keys present in ``original`` but absent from ``desired`` become ``None``
    - keys absent from ``original`` are added with their desired value
    - nested dicts recurse; unchanged paths are omitted
    - lists and scalars are compared by equality and replaced whole

    Returns ``{}`` when nothing changed. Both arguments should come from
    :func:`spec_to_dict` (or the same serialization) so ``None`` never appears
    as a value in ``desired`` unless it means "delete".
    """
    if not isinstance(original, dict) or not isinstance(desired, dict):
        raise ValueError("build_merge_patch expects two dicts at the top level.")
    return _diff_dict(original, desired)


def _diff_dict(original: Dict[str, Any], desired: Dict[str, Any]) -> Dict[str, Any]:
    patch: Dict[str, Any] = {}
    for key in original:
        if key not in desired or desired[key] is None:
            patch[key] = None
    for key, value in desired.items():
        if value is None:
            # Deleting a key that does not exist is a no-op.
            continue
        if key not in original:
            patch[key] = deepcopy(value)
            continue
        current = original[key]
        if isinstance(current, dict) and isinstance(value, dict):
            sub = _diff_dict(current, value)
            if sub:
                patch[key] = sub
        elif current != value:
            patch[key] = deepcopy(value)
    return patch


def deep_merge_patch(base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
    """
    Combine two merge patches; ``override`` wins on conflicts. A ``None`` in
    ``override`` (delete) replaces whatever ``base`` had for that key.
    """
    result = deepcopy(base)
    for key, value in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = deep_merge_patch(result[key], value)
        else:
            result[key] = deepcopy(value)
    return result


def apply_merge_patch(target: Any, patch: Any) -> Any:
    """
    Apply an RFC 7396 merge patch to ``target`` and return the result (a new
    object). Used to preview what the server will store.
    """
    if not isinstance(patch, dict):
        return deepcopy(patch)
    result = dict(target) if isinstance(target, dict) else {}
    for key, value in patch.items():
        if value is None:
            result.pop(key, None)
        else:
            result[key] = apply_merge_patch(result.get(key), value)
    return result
