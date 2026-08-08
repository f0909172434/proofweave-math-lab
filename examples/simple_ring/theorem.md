+++
claim_id = "square-successor"
title = "Square of a successor"
assumptions = ["x is an integer"]
quantifiers = ["for every integer x"]
dependencies = []
+++

## Statement

For every integer x, (x + 1)^2 = x^2 + 2x + 1.

## Proof

Expand the square and collect like terms.

## Certificate

```proofweave-lean
target = "forall x : Int, (x + 1)^2 = x^2 + 2*x + 1"
tactic = "ring"
```
