+++
claim_id = "pack-template-claim"
title = "Template arithmetic claim"
assumptions = ["none"]
quantifiers = []
dependencies = []
+++

## Statement

Two plus three equals five.

## Proof

The pinned Lean certifier checks the formal target.

## Certificate

```proofweave-lean
target = "(2 + 3 : Int) = 5"
tactic = "norm_num"
```
