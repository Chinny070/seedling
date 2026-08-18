# v0.2.16
# { "Depends": "py-genlayer:1jb45aa8ynh2a9c9xn3b7qqh8sm5q93hwfp7jqmwsfhh8jpz09h6" }

# SEEDLING — reusable latent-public-goods discovery, lineage-attribution,
# and progressive retroactive-funding primitive.
#
# STAGE 1 SCOPE: storage scaffolding + protocol control only.
#   - Full on-chain storage model for all 12 core records (declared below).
#   - Domain vocabulary (lifecycle, types, evidence categories, tiers,
#     reason codes, lineage relationships, appeal grounds/decisions).
#   - Constructor + owner-gated pause/unpause + get_protocol_info().
# Candidate/policy/evidence/adjudication/funding/appeal methods arrive in
# later stages (2-10). This file is a valid, deployable gl.Contract so the
# repository stays functional after every stage.

from genlayer import *

import json


# ---------------------------------------------------------------------------
# Protocol / spec versions
# ---------------------------------------------------------------------------
PROTOCOL_VERSION = 1          # on-chain contract revision
SPEC_VERSION = 1              # product/protocol spec revision this implements


# ---------------------------------------------------------------------------
# Candidate dormant-value lifecycle (spec ss.3)
#   DISCOVERED -> LATENT -> WATCHING -> EMERGING -> MATERIAL -> SYSTEMIC
#   decline:   LATENT->STALLED, EMERGING->DECLINED, WATCHING->ARCHIVED
# ---------------------------------------------------------------------------
CANDIDATE_STATUSES = [
    "DISCOVERED",
    "LATENT",
    "WATCHING",
    "EMERGING",
    "MATERIAL",
    "SYSTEMIC",
    "STALLED",
    "DECLINED",
    "ARCHIVED",
]

# Progressive-funding tiers (spec ss.4). Each maps to a monotonic cap in a
# FundingPolicy: latent <= watching <= emerging <= material <= systemic <= 10000.
FUNDING_TIERS = ["LATENT", "WATCHING", "EMERGING", "MATERIAL", "SYSTEMIC"]

# ---------------------------------------------------------------------------
# Candidate types (spec ss.9) — must stay generic, never GitHub-only.
# ---------------------------------------------------------------------------
CANDIDATE_TYPES = [
    "OPEN_SOURCE_LIBRARY",
    "DATASET",
    "RESEARCH",
    "DOCUMENTATION",
    "DEVELOPER_TOOL",
    "PUBLIC_ARCHIVE",
    "COMMUNITY_INFRASTRUCTURE",
    "PROTOCOL_COMPONENT",
    "EDUCATIONAL_RESOURCE",
    "CUSTOM",
]

# ---------------------------------------------------------------------------
# Evidence categories (spec ss.13)
# ---------------------------------------------------------------------------
EVIDENCE_CATEGORIES = [
    "SOURCE_REPOSITORY",
    "PACKAGE_REGISTRY",
    "DEPENDENCY_GRAPH",
    "DOWNSTREAM_REPOSITORY",
    "TECHNICAL_DOCUMENTATION",
    "PUBLIC_ARTICLE",
    "PUBLIC_DATASET",
    "RESEARCH_CITATION",
    "PRODUCTION_REFERENCE",
    "ECOSYSTEM_DOCUMENTATION",
    "ARCHIVED_EVIDENCE",
    "MAINTAINER_HISTORY",
    "ALTERNATIVE_PROJECT",
    "PUBLIC_USAGE_RECORD",
]

# ---------------------------------------------------------------------------
# Lineage relationships (spec ss.17). Claimed lineage is never authoritative.
# ---------------------------------------------------------------------------
LINEAGE_RELATIONSHIPS = [
    "FORKED_FROM",
    "DERIVED_FROM",
    "REWRITES",
    "EXTENDS",
    "INCORPORATES",
    "DOCUMENTS",
    "MAINTAINS",
    "MIGRATES",
    "REPLACES",
    "INSPIRES",
]

# ---------------------------------------------------------------------------
# Reason codes (spec ss.18/19)
# ---------------------------------------------------------------------------
POSITIVE_REASON_CODES = [
    "EARLY_INDEPENDENT_REUSE",
    "TECHNICALLY_UNIQUE",
    "LIMITED_SUBSTITUTES",
    "DEPENDENCY_GROWTH_ORGANIC",
    "DOWNSTREAM_EXPERIMENTATION",
    "CROSS_ORG_ADOPTION",
    "PERSISTENT_USAGE",
    "FOUNDATIONAL_DESIGN",
    "PUBLIC_ACCESS_CONFIRMED",
    "SYSTEMIC_DEPENDENCY",
    "REPLACEMENT_DIFFICULT",
    "ORIGINAL_CONTRIBUTION_SURVIVES",
]

ANTI_GAMING_REASON_CODES = [
    "BOT_ACTIVITY_SUSPECTED",
    "DOWNLOAD_NOISE_HIGH",
    "DEPENDENCY_INFLATION_SUSPECTED",
    "COMMON_OWNER_DEPENDENCIES",
    "AUTOMATIC_BUNDLING_EFFECT",
    "DUPLICATE_FORK_ACTIVITY",
    "TEMPORARY_HYPE",
    "CIRCULAR_ADOPTION",
    "PACKAGE_SPLITTING",
    "ARTIFICIAL_REPOSITORY_ACTIVITY",
    "BENCHMARK_MISUSE",
    "PUBLIC_VALUE_NOT_INDEPENDENT",
]

ALL_REASON_CODES = POSITIVE_REASON_CODES + ANTI_GAMING_REASON_CODES

# ---------------------------------------------------------------------------
# Appeals (spec ss.20)
# ---------------------------------------------------------------------------
APPEAL_GROUNDS = [
    "IMPACT_OVERSTATED",
    "IMPACT_UNDERSTATED",
    "LINEAGE_MISATTRIBUTED",
    "ORIGINAL_CONTRIBUTION_IGNORED",
    "DERIVATIVE_WORK_OVERWEIGHTED",
    "INDEPENDENCE_MISCLASSIFIED",
    "GAMING_RISK_MISCLASSIFIED",
    "SUBSTITUTE_ANALYSIS_WRONG",
    "EVIDENCE_OMITTED",
    "INVALID_EVIDENCE_USED",
    "FUNDING_POLICY_MISAPPLIED",
]
APPEAL_DECISIONS = ["UPHOLD", "MODIFY", "VOID"]

# ---------------------------------------------------------------------------
# Sub-object status machines
# ---------------------------------------------------------------------------
LATENT_STATUSES = ["OPEN", "EVIDENCE_FROZEN", "EVALUATED"]
CHECKPOINT_STATUSES = [
    "OPEN",
    "EVIDENCE_FROZEN",
    "EVALUATING",
    "PUBLIC_VALUE_SET",
    "LINEAGE_SET",
    "FINALIZED",
    "VOIDED",
]
APPEAL_STATUSES = ["OPEN", "EVALUATING", "RESOLVED"]

# ---------------------------------------------------------------------------
# Deterministic bounds (used by later stages; declared here as the single
# source of truth for the scaffold and exposed via get_protocol_info()).
# ---------------------------------------------------------------------------
BPS_DENOMINATOR = 10000
MAX_EVIDENCE_PER_CANDIDATE = 64
MAX_EVIDENCE_PER_CHECKPOINT = 64
MAX_CONTRIBUTION_NODES = 64
MAX_LINEAGE_EDGES = 128
MAX_CHECKPOINTS_PER_CANDIDATE = 48
MIN_CHECKPOINT_INTERVAL = 86400          # 1 day
MAX_CHECKPOINT_INTERVAL = 157680000      # ~5 years


class Seedling(gl.Contract):
    # -- protocol config: owner, paused, protocol_version, spec_version --
    config: TreeMap[str, str]

    # -- monotonic id counters (ids are decimal strings) --
    candidate_count: u256
    observation_policy_count: u256
    funding_policy_count: u256
    evidence_count: u256
    latent_assessment_count: u256
    checkpoint_count: u256
    impact_verdict_count: u256
    contribution_node_count: u256
    lineage_edge_count: u256
    lineage_verdict_count: u256
    appeal_count: u256

    # -- canonical record stores (id -> JSON) --
    candidates: TreeMap[str, str]
    observation_policies: TreeMap[str, str]
    funding_policies: TreeMap[str, str]
    evidence: TreeMap[str, str]
    latent_assessments: TreeMap[str, str]
    checkpoints: TreeMap[str, str]
    impact_verdicts: TreeMap[str, str]
    contribution_nodes: TreeMap[str, str]
    lineage_edges: TreeMap[str, str]
    lineage_verdicts: TreeMap[str, str]
    funding_previews: TreeMap[str, str]     # keyed by checkpoint id
    appeals: TreeMap[str, str]

    # -- enumeration + parent->children index maps (key -> JSON list) --
    candidate_index: TreeMap[str, str]              # ordinal -> candidate_id
    candidate_evidence_ids: TreeMap[str, str]       # candidate_id -> [evidence_id]
    candidate_latent_ids: TreeMap[str, str]         # candidate_id -> [assessment_id] (append-only)
    candidate_checkpoint_ids: TreeMap[str, str]     # candidate_id -> [checkpoint_id]
    candidate_node_ids: TreeMap[str, str]           # candidate_id -> [node_id]
    candidate_edge_ids: TreeMap[str, str]           # candidate_id -> [edge_id]
    candidate_lineage_verdict_ids: TreeMap[str, str]  # candidate_id -> [verdict_id] (append-only)
    candidate_appeal_ids: TreeMap[str, str]         # candidate_id -> [appeal_id]
    checkpoint_evidence_ids: TreeMap[str, str]      # checkpoint_id -> [evidence_id]
    checkpoint_verdict_ids: TreeMap[str, str]       # checkpoint_id -> [impact_verdict_id] (append-only)

    def __init__(self):
        self.config["owner"] = gl.message.sender_address.as_hex
        self.config["paused"] = "0"
        self.config["protocol_version"] = str(PROTOCOL_VERSION)
        self.config["spec_version"] = str(SPEC_VERSION)
        self.candidate_count = u256(0)
        self.observation_policy_count = u256(0)
        self.funding_policy_count = u256(0)
        self.evidence_count = u256(0)
        self.latent_assessment_count = u256(0)
        self.checkpoint_count = u256(0)
        self.impact_verdict_count = u256(0)
        self.contribution_node_count = u256(0)
        self.lineage_edge_count = u256(0)
        self.lineage_verdict_count = u256(0)
        self.appeal_count = u256(0)

    # -- internal guards --
    def _require_owner(self):
        if gl.message.sender_address.as_hex != self.config["owner"]:
            raise gl.vm.UserError("EXPECTED: only owner can call this")

    # -- protocol control --
    @gl.public.write
    def pause(self) -> str:
        self._require_owner()
        self.config["paused"] = "1"
        return "paused"

    @gl.public.write
    def unpause(self) -> str:
        self._require_owner()
        self.config["paused"] = "0"
        return "unpaused"

    # -- introspection: health, versions, counters, and domain vocabulary --
    @gl.public.view
    def get_protocol_info(self) -> str:
        return json.dumps({
            "name": "SEEDLING",
            "owner": self.config["owner"],
            "paused": self.config["paused"] == "1",
            "protocol_version": int(self.config["protocol_version"]),
            "spec_version": int(self.config["spec_version"]),
            "counts": {
                "candidates": int(self.candidate_count),
                "observation_policies": int(self.observation_policy_count),
                "funding_policies": int(self.funding_policy_count),
                "evidence": int(self.evidence_count),
                "latent_assessments": int(self.latent_assessment_count),
                "checkpoints": int(self.checkpoint_count),
                "impact_verdicts": int(self.impact_verdict_count),
                "contribution_nodes": int(self.contribution_node_count),
                "lineage_edges": int(self.lineage_edge_count),
                "lineage_verdicts": int(self.lineage_verdict_count),
                "appeals": int(self.appeal_count),
            },
            "vocabulary": {
                "candidate_statuses": CANDIDATE_STATUSES,
                "funding_tiers": FUNDING_TIERS,
                "candidate_types": CANDIDATE_TYPES,
                "evidence_categories": EVIDENCE_CATEGORIES,
                "lineage_relationships": LINEAGE_RELATIONSHIPS,
                "positive_reason_codes": POSITIVE_REASON_CODES,
                "anti_gaming_reason_codes": ANTI_GAMING_REASON_CODES,
                "appeal_grounds": APPEAL_GROUNDS,
                "appeal_decisions": APPEAL_DECISIONS,
                "latent_statuses": LATENT_STATUSES,
                "checkpoint_statuses": CHECKPOINT_STATUSES,
                "appeal_statuses": APPEAL_STATUSES,
            },
            "bounds": {
                "bps_denominator": BPS_DENOMINATOR,
                "max_evidence_per_candidate": MAX_EVIDENCE_PER_CANDIDATE,
                "max_evidence_per_checkpoint": MAX_EVIDENCE_PER_CHECKPOINT,
                "max_contribution_nodes": MAX_CONTRIBUTION_NODES,
                "max_lineage_edges": MAX_LINEAGE_EDGES,
                "max_checkpoints_per_candidate": MAX_CHECKPOINTS_PER_CANDIDATE,
                "min_checkpoint_interval": MIN_CHECKPOINT_INTERVAL,
                "max_checkpoint_interval": MAX_CHECKPOINT_INTERVAL,
            },
        })
