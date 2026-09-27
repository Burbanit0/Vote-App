"""
api.schemas — the Pydantic models that define the HTTP contract for every
endpoint. Request models use `extra="forbid"` (an unknown key is a 422 on
purpose); responses declare a `response_model` so the frontend's TypeScript
types are generated from one source of truth.

Import from the module that owns the model, not from here:

    common.py       shared primitives (CandidateSpec, BlankVoteConfig, ErrorDetail,
                    WORKER_ERROR_RESPONSES, ...)
    election.py     /api/v2/election/*
    perturbers.py   the perturber family under /api/v2/election/*
    theory.py       /api/v2/theory/*
    simulations.py  /api/v2/simulations/*
    tech.py         /api/v2/tech/*
    public_api.py   the public /api/v1 surface

This file used to re-export all 128 of them, each name written twice (once in
the import, once in `__all__`), so adding a model meant editing two files. The
five route modules now import from the owning module directly.
"""
