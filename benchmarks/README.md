# Model benchmark suite

The public seed cases exercise the ten required categories and are intended to
validate the harness, not rank models. They were created during initialization
and therefore require independent human review before being treated as an
answer key. Hidden evaluation items belong outside the model-visible repository
and must carry a dataset version and reviewer provenance.

`python -m mathlab models benchmark` validates coverage and summarizes already
recorded results. It does **not** invoke a model. Live execution is disabled by
default and no ranking is emitted until at least two models each have the
configured minimum number of independently keyed cases.

