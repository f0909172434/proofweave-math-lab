import Mathlib
set_option autoImplicit false

theorem pw_1_3f4b715d9c : (forall x : Int, (x + 1)^2 = x^2 + 2*x + 1) := by
  intros <;> ring
