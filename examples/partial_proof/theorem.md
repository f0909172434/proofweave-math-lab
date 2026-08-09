+++
claim_id = "partial-example"
title = "A deliberately partial proof"
assumptions = ["x is an integer"]
quantifiers = ["for every integer x"]
dependencies = []
+++

## Statement

For every integer x, a stated but unformalized semantic argument implies x = x.

## Proof

### semantic-step [semantic]

Use the unformalized semantic argument.

### computation [computational]
Depends: semantic-step

Check the reflexive arithmetic endpoint.

```proofweave-lean
target = "forall x : Int, x = x"
tactic = "ring"
```
