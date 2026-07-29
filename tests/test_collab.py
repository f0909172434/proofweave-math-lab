from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from mathlab.collab import CollaborationArtifacts
from mathlab.errors import ValidationError


def result(**changes):
    value = {
        "request_id": "request-1",
        "job_id": "console-job-1",
        "task_id": "task-1",
        "status": "completed",
        "research_status": "PROPOSED",
        "summary": "A bounded proposed result.",
        "reasoning_summary": "Provider supplied a short evidence summary.",
        "primary": {"provider": "DeepSeek", "model": "v4", "model_family": "DeepSeek"},
        "requested_effort": {"profile": "standard", "level": "medium"},
        "effective_effort": {"profile": "deep", "level": "provider"},
        "usage": {"input_tokens": 100, "cached_input_tokens": 0, "output_tokens": 50, "duration_ms": 1000},
        "reviewer": None,
        "review_state": "not_required",
        "disagreements": [],
        "artifacts": [],
        "evidence_status": "PROPOSED",
        "spend": {"actual_usd": 0.2, "actual_cny": 1.4, "http_status": 200, "retry_count": 0},
        "fallback": "proofweave_native",
    }
    value.update(changes)
    return value


class CollaborationArtifactTests(unittest.TestCase):
    digest = "sha256:" + "a" * 64

    def test_prepare_uses_the_fixed_private_bounded_policy(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            request = CollaborationArtifacts(temp).prepare(
                "t1", "Implement a narrow adapter.", context_packet_digest=self.digest
            )
        self.assertEqual("private", request["sensitivity"])
        self.assertEqual("existing_balance", request["spend"]["authorization"])
        self.assertEqual(0.70, request["spend"]["maximum_usd"])
        self.assertEqual(5.0, request["spend"]["maximum_cny"])
        self.assertFalse(request["workspace_operations"]["enabled"])
        self.assertEqual("proofweave_native", request["fallback"])
        self.assertNotIn("workspace_id", request)
        self.assertEqual(self.digest, request["context_packet_digest"])
        self.assertEqual(16000, request["limits"]["max_input_tokens"])
        self.assertEqual("medium", request["effort"]["requested"])

    def test_workspace_id_cannot_be_guessed_or_attached(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            with self.assertRaises(ValidationError):
                CollaborationArtifacts(temp).prepare(
                    "t1", "x", context_packet_digest=self.digest, workspace_id="from-a-path"
                )

    def test_restricted_without_local_lane_stops_without_a_job_id(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            saved = CollaborationArtifacts(temp).needs_attention(
                "restricted-1",
                "No qualified local Qwen or gpt-oss lane.",
                requested_profile="max",
                context_packet_digest=self.digest,
            )
            self.assertEqual("needs_attention", saved["status"])
            self.assertIsNone(saved["job_id"])
            self.assertIsNone(saved["primary"])
            self.assertEqual("NONE", saved["evidence_status"])

    def test_completed_is_limited_to_proposed_or_computational(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            artifacts = CollaborationArtifacts(temp)
            artifacts.ingest(result())
            saved = artifacts.ingest(
                result(
                    job_id="console-job-2",
                    research_status="COMPUTATIONAL",
                    evidence_status="COMPUTATIONAL",
                )
            )
            self.assertEqual("COMPUTATIONAL", saved["research_status"])
            with self.assertRaises(ValidationError):
                artifacts.ingest(result(job_id="console-job-3", research_status="VERIFIED"))
            with self.assertRaises(ValidationError):
                artifacts.ingest(result(job_id="console-job-4", research_status="OPEN"))

    def test_review_and_manual_statuses_have_safe_conclusions(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            artifacts = CollaborationArtifacts(temp)
            review = artifacts.ingest(result(status="needs_review", research_status="PROPOSED"))
            self.assertEqual("OPEN", review["research_status"])
            self.assertEqual("OPEN", review["evidence_status"])
            manual = artifacts.ingest(result(job_id="console-job-2", status="awaiting_manual", research_status=None))
            self.assertIsNone(manual["research_status"])
            self.assertEqual("NONE", manual["evidence_status"])
            with self.assertRaises(ValidationError):
                artifacts.ingest(result(job_id="console-job-3", status="needs_attention", research_status="PROPOSED"))

    def test_high_risk_without_independent_reviewer_is_forced_open(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            saved = CollaborationArtifacts(temp).ingest(result(risk="high"))
            self.assertEqual("needs_review", saved["status"])
            self.assertEqual("OPEN", saved["research_status"])
            self.assertEqual("OPEN", saved["evidence_status"])
            self.assertEqual("pending", saved["review_state"])

    def test_rejects_verified_raw_reasoning_unknown_reviewer_and_retries(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            artifacts = CollaborationArtifacts(temp)
            with self.assertRaises(ValidationError):
                artifacts.ingest(result(research_status="VERIFIED"))
            with self.assertRaises(ValidationError):
                artifacts.ingest(result(chain_of_thought="hidden"))
            with self.assertRaises(ValidationError):
                artifacts.ingest(result(reviewer={"provider": "x", "model": "y", "model_family": "UNKNOWN", "independent": True}))
            with self.assertRaises(ValidationError):
                artifacts.ingest(result(reviewer={"provider": "deepseek", "model": "deepseek-review", "model_family": "DeepSeek", "independent": True}))
            with self.assertRaises(ValidationError):
                artifacts.ingest(result(reviewer={"provider": "microsoft", "model": "copilot-auto", "model_family": "Microsoft", "independent": True}))
            with self.assertRaises(ValidationError):
                artifacts.ingest(result(spend={"actual_usd": 0.71, "actual_cny": 1.0, "http_status": 200, "retry_count": 0}))
            with self.assertRaises(ValidationError):
                artifacts.ingest(result(spend={"actual_usd": 0.0, "actual_cny": 0.0, "http_status": 402, "retry_count": 1}))
            with self.assertRaisesRegex(ValidationError, "must conclude needs_attention"):
                artifacts.ingest(
                    result(
                        spend={
                            "actual_usd": 0.0,
                            "actual_cny": 0.0,
                            "http_status": 402,
                            "retry_count": 0,
                        }
                    )
                )
            with self.assertRaisesRegex(ValidationError, "evidence_status must match"):
                artifacts.ingest(result(evidence_status="COMPUTATIONAL"))
            with self.assertRaisesRegex(ValidationError, "primary model metadata"):
                artifacts.ingest(
                    result(
                        status="needs_attention",
                        research_status=None,
                        primary=None,
                        reviewer={
                            "provider": "review-provider",
                            "model": "review-model",
                            "model_family": "review-family",
                            "independent": True,
                        },
                    )
                )

    def test_internal_attention_record_redacts_secret_like_summary(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            saved = CollaborationArtifacts(temp).needs_attention(
                "restricted-1",
                "provider api_key=super-secret-value",
                requested_profile="max",
                context_packet_digest=self.digest,
            )
            self.assertIn("[REDACTED]", saved["summary"])
            self.assertNotIn("super-secret-value", saved["summary"])

    def test_unavailable_record_has_no_fabricated_job_id_and_ledger_is_append_only(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            artifacts = CollaborationArtifacts(temp)
            unavailable = artifacts.prepare(
                "t1", "x", context_packet_digest=self.digest, console_available=False
            )
            self.assertEqual("COLLAB_UNAVAILABLE", unavailable["status"])
            self.assertIsNone(unavailable["job_id"])
            first_text = (Path(temp) / "state" / "collab_jobs.jsonl").read_text(encoding="utf-8")
            artifacts.ingest(result())
            final_text = (Path(temp) / "state" / "collab_jobs.jsonl").read_text(encoding="utf-8")
            self.assertTrue(final_text.startswith(first_text))
            self.assertEqual(2, len([json.loads(line) for line in final_text.splitlines()]))
            self.assertEqual("PASS", artifacts.audit()["status"])
            self.assertEqual(2, len(artifacts.history()))


if __name__ == "__main__":
    unittest.main()
