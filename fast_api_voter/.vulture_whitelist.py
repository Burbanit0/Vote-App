# Vulture whitelist — confirmed false positives, not dead code.
#
# vulture flags these because it can't see that the values are required by a
# language protocol or a shared call signature rather than being genuinely
# unused:
#   - exc_type / tb / exc_info: required by the context-manager `__exit__`
#     protocol (see domain/polity/llm_client.py, journal.py) even when the
#     implementation doesn't need to inspect the exception.
#   - kwargs: voting-method functions in engine/utils/simulation_ranked_utils.py
#     are called uniformly through a shared dispatch table with a common
#     **kwargs signature; not every method needs every keyword.
#
# Add an entry here only after confirming (like the above) that the symbol
# truly needs to exist but is never read — do not use this file to silence a
# real finding you haven't investigated. Regenerate candidates with:
#   vulture api/ --config pyproject.toml --make-whitelist

exc_type
tb
exc_info
kwargs
