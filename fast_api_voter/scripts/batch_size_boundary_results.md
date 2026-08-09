# Batch-size boundary sweep -- model=qwen3:8b, dims=20, candidates=2, sizes=[20, 21, 22, 23, 24, 25], repeats=2

size=20 rep=1/2: PASS elapsed=201.0s -- ok
size=20 rep=2/2: PASS elapsed=160.9s -- ok
size=21 rep=1/2: PASS elapsed=236.0s -- ok
size=21 rep=2/2: PASS elapsed=363.7s -- ok
size=22 rep=1/2: PASS elapsed=415.1s -- ok
size=22 rep=2/2: PASS elapsed=172.2s -- ok
size=23 rep=1/2: PASS elapsed=281.5s -- ok
size=23 rep=2/2: PASS elapsed=360.6s -- ok
size=24 rep=1/2: PASS elapsed=542.7s -- ok
size=24 rep=2/2: PASS elapsed=279.8s -- ok
size=25 rep=1/2: PASS elapsed=302.3s -- ok
size=25 rep=2/2: PASS elapsed=517.4s -- ok

## Summary

| size | passes | failures | failure rate |
|------|--------|----------|--------------|
| 20 | 2 | 0 | 0/2 |
| 21 | 2 | 0 | 0/2 |
| 22 | 2 | 0 | 0/2 |
| 23 | 2 | 0 | 0/2 |
| 24 | 2 | 0 | 0/2 |
| 25 | 2 | 0 | 0/2 |
