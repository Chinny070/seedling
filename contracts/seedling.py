# v0.2.16
# { "Depends": "py-genlayer:1jb45aa8ynh2a9c9xn3b7qqh8sm5q93hwfp7jqmwsfhh8jpz09h6" }

# SEEDLING — reusable latent-public-goods discovery, lineage-attribution,
# and progressive retroactive-funding primitive.
#
# STAGES IMPLEMENTED SO FAR:
#   Stage 1 — storage scaffolding + protocol control.
#   Stage 2 — candidate lifecycle registration + reusable, versioned
#             ObservationPolicy and FundingPolicy primitives.
#   Stage 3 — candidate evidence collection + latent-evidence freeze.
#
# Stage 3 deliberately does NOT implement: latent-value adjudication (Stage 4),
# contribution lineage, checkpoints, public-value adjudication, funding
# calculation, appeals, or a frontend. In particular there is NO GenLayer
# adjudication yet — Stage 3 only collects, validates, and permanently freezes
# the latent evidence set so Stage 4 can evaluate a fixed input.
# The file stays a valid, deployable gl.Contract so the repository remains
# functional after every stage.

from genlayer import *

import json
import time


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

# Reusable-policy lifecycle. Historical version records are immutable; only
# this operational flag (tracked in a dedicated status map) ever changes.
POLICY_STATUSES = ["ACTIVE", "INACTIVE"]

# Candidate evidence lifecycle (Stage 3). A submitted record is write-once; its
# effective status is DERIVED from the owning candidate's latent-freeze flag, so
# freezing never rewrites evidence rows (the strongest immutability guarantee).
EVIDENCE_STATUSES = ["SUBMITTED", "FROZEN"]

# Canonical empty/null checkpoint reference. Latent-stage evidence is not
# attached to any impact checkpoint, so checkpoint_id is stored as this exact
# sentinel rather than a fabricated id. Real checkpoint ids are 1-based decimal
# strings, so "" can never collide with a genuine checkpoint id.
NULL_CHECKPOINT_ID = ""

# ---------------------------------------------------------------------------
# Deterministic bounds — single source of truth for the scaffold, exposed via
# get_protocol_info() and enforced by Stage 2 validation.
# ---------------------------------------------------------------------------
BPS_DENOMINATOR = 10000
MAX_EVIDENCE_PER_CANDIDATE = 64
MAX_EVIDENCE_PER_CHECKPOINT = 64
MAX_CONTRIBUTION_NODES = 64
MAX_LINEAGE_EDGES = 128
MAX_CHECKPOINTS_PER_CANDIDATE = 48
MIN_CHECKPOINT_INTERVAL = 86400          # 1 day
MAX_CHECKPOINT_INTERVAL = 157680000      # ~5 years

# String / collection bounds (Stage 2)
MAX_NAME_LEN = 120
MAX_DESCRIPTION_LEN = 2000
MAX_URL_LEN = 400
MAX_ORIGIN_DATE_LEN = 40
MAX_POLICY_NAME_LEN = 120
MAX_RULE_LEN = 2000
MAX_INDEPENDENT_SOURCES = 100
MAX_LIST_LIMIT = 50                      # pagination page-size ceiling for views

# Evidence field bounds (Stage 3)
MAX_CONTENT_HASH_LEN = 128               # fits sha-256/512 hex and multibase CIDs
MAX_SUMMARY_LEN = 1000


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

    # -- policy enumeration, version history, and operational status (Stage 2) --
    observation_policy_index: TreeMap[str, str]         # ordinal -> policy_id (every version)
    funding_policy_index: TreeMap[str, str]             # ordinal -> funding_policy_id (every version)
    observation_policy_family_index: TreeMap[str, str]  # family_id -> [policy_id] (version order)
    funding_policy_family_index: TreeMap[str, str]      # family_id -> [funding_policy_id]
    observation_policy_status: TreeMap[str, str]        # policy_id -> ACTIVE|INACTIVE
    funding_policy_status: TreeMap[str, str]            # funding_policy_id -> ACTIVE|INACTIVE

    # -- Stage 3: latent-evidence duplicate guard + per-candidate freeze state --
    evidence_dedup: TreeMap[str, str]           # "cid@len:nurl:hash" -> evidence_id
    latent_freeze: TreeMap[str, str]            # candidate_id -> freeze snapshot JSON (presence => frozen)

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

    # ======================================================================
    # Internal guards / helpers
    # ======================================================================
    def _require_owner(self):
        if gl.message.sender_address.as_hex != self.config["owner"]:
            raise gl.vm.UserError("EXPECTED: only owner can call this")

    def _require_not_paused(self):
        if self.config["paused"] == "1":
            raise gl.vm.UserError("EXPECTED: protocol is paused")

    def _now(self) -> int:
        # GenVM provides a consensus-deterministic wall clock; same verified
        # pattern used by the deployed sibling contracts.
        return int(time.time())

    def _validate_http_url(self, url: str, field: str):
        if not url or len(url) > MAX_URL_LEN:
            raise gl.vm.UserError(f"EXPECTED: {field} must be 1-{MAX_URL_LEN} characters")
        lo = url.lower()
        if not (lo.startswith("http://") or lo.startswith("https://")):
            raise gl.vm.UserError(f"EXPECTED: {field} must be an http:// or https:// URL")
        for ch in url:
            if ch.isspace():
                raise gl.vm.UserError(f"EXPECTED: {field} must not contain whitespace")
        rest = url.split("://", 1)[1]
        host = rest.split("/", 1)[0]
        if not host or "." not in host:
            raise gl.vm.UserError(f"EXPECTED: {field} must include a valid host")

    def _normalize_source_host(self, url: str) -> str:
        # Deterministic host normalization used for source-independence checks.
        # Strips scheme, path, any user:pass@ userinfo, and the :port, then
        # lowercases and drops a trailing FQDN dot. Because independence is
        # measured on the normalized host (never the raw netloc), a different
        # port or userinfo on the same host can NOT fake an independent source.
        #
        # LIMITATION (deliberate): this enforces only obvious host-level
        # diversity. Distinct hosts or subdomains do NOT prove organizational
        # independence — two hosts can share an owner, and one org can span many
        # domains. Real independence is a Stage 4 GenLayer adjudication concern;
        # deterministic contract logic must not claim to decide it.
        rest = url.split("://", 1)[1]
        netloc = rest.split("/", 1)[0]
        if "@" in netloc:                       # drop user:pass@ userinfo
            netloc = netloc.rsplit("@", 1)[1]
        host = netloc.split(":", 1)[0]          # drop :port
        host = host.lower()
        while len(host) > 1 and host.endswith("."):
            host = host[:-1]
        return host

    def _normalize_url_for_dedup(self, url: str) -> str:
        # Conservative, deterministic URL canonicalization for duplicate
        # detection: lowercase the scheme + authority, drop the #fragment, and
        # trim a single trailing '/'. Path case and query string are preserved
        # so genuinely distinct resources are never collapsed (no overreach).
        u = url.split("#", 1)[0]
        parts = u.split("://", 1)
        scheme = parts[0].lower()
        rest = parts[1]
        slash = rest.find("/")
        if slash == -1:
            authority = rest
            path = ""
        else:
            authority = rest[:slash]
            path = rest[slash:]
        if "@" in authority:
            authority = authority.rsplit("@", 1)[1]
        authority = authority.lower()
        if len(path) > 1 and path.endswith("/"):
            path = path[:-1]
        return scheme + "://" + authority + path

    def _evidence_view(self, evidence_id: str) -> dict:
        # Load the write-once evidence row and merge the derived status.
        # Effective status is FROZEN iff the owning candidate's latent set is
        # frozen; the stored row itself is never mutated by a freeze.
        rec = json.loads(self.evidence[evidence_id])
        frozen = rec["candidate_id"] in self.latent_freeze
        rec["status"] = "FROZEN" if frozen else "SUBMITTED"
        return rec

    def _require_active_observation_policy(self, pid: str):
        if not pid or pid not in self.observation_policies:
            raise gl.vm.UserError("EXPECTED: observation_policy_id does not exist")
        if self.observation_policy_status[pid] != "ACTIVE":
            raise gl.vm.UserError("EXPECTED: observation policy is not active")

    def _require_active_funding_policy(self, fid: str):
        if not fid or fid not in self.funding_policies:
            raise gl.vm.UserError("EXPECTED: funding_policy_id does not exist")
        if self.funding_policy_status[fid] != "ACTIVE":
            raise gl.vm.UserError("EXPECTED: funding policy is not active")

    def _validated_observation_payload(
        self,
        name: str,
        candidate_types: list[str],
        minimum_evidence_categories: int,
        minimum_independent_sources: int,
        latent_rules: str,
        impact_rules: str,
        lineage_rules: str,
        gaming_rules: str,
        substitute_rules: str,
        checkpoint_interval: int,
    ) -> dict:
        if not name or len(name) > MAX_POLICY_NAME_LEN:
            raise gl.vm.UserError(f"EXPECTED: name must be 1-{MAX_POLICY_NAME_LEN} characters")
        if not candidate_types:
            raise gl.vm.UserError("EXPECTED: at least one candidate_type is required")
        if len(candidate_types) > len(CANDIDATE_TYPES):
            raise gl.vm.UserError("EXPECTED: too many candidate_types")
        seen = []
        for t in candidate_types:
            if t not in CANDIDATE_TYPES:
                raise gl.vm.UserError(f"EXPECTED: invalid candidate_type '{t}'")
            if t in seen:
                raise gl.vm.UserError(f"EXPECTED: duplicate candidate_type '{t}'")
            seen.append(t)
        if minimum_evidence_categories < 0 or minimum_evidence_categories > len(EVIDENCE_CATEGORIES):
            raise gl.vm.UserError(
                f"EXPECTED: minimum_evidence_categories must be 0-{len(EVIDENCE_CATEGORIES)}"
            )
        if minimum_independent_sources < 1 or minimum_independent_sources > MAX_INDEPENDENT_SOURCES:
            raise gl.vm.UserError(
                f"EXPECTED: minimum_independent_sources must be 1-{MAX_INDEPENDENT_SOURCES}"
            )
        for label, rule in (
            ("latent_rules", latent_rules),
            ("impact_rules", impact_rules),
            ("lineage_rules", lineage_rules),
            ("gaming_rules", gaming_rules),
            ("substitute_rules", substitute_rules),
        ):
            if len(rule) > MAX_RULE_LEN:
                raise gl.vm.UserError(f"EXPECTED: {label} must be at most {MAX_RULE_LEN} characters")
        if checkpoint_interval < MIN_CHECKPOINT_INTERVAL or checkpoint_interval > MAX_CHECKPOINT_INTERVAL:
            raise gl.vm.UserError(
                f"EXPECTED: checkpoint_interval must be {MIN_CHECKPOINT_INTERVAL}-{MAX_CHECKPOINT_INTERVAL} seconds"
            )
        return {
            "name": name,
            "candidate_types": candidate_types,
            "minimum_evidence_categories": minimum_evidence_categories,
            "minimum_independent_sources": minimum_independent_sources,
            "latent_rules": latent_rules,
            "impact_rules": impact_rules,
            "lineage_rules": lineage_rules,
            "gaming_rules": gaming_rules,
            "substitute_rules": substitute_rules,
            "checkpoint_interval": checkpoint_interval,
        }

    def _validated_funding_payload(
        self,
        name: str,
        latent_cap_bps: int,
        watching_cap_bps: int,
        emerging_cap_bps: int,
        material_cap_bps: int,
        systemic_cap_bps: int,
        minimum_public_value_bps: int,
        maximum_gaming_risk_bps: int,
        minimum_attribution_confidence_bps: int,
    ) -> dict:
        if not name or len(name) > MAX_POLICY_NAME_LEN:
            raise gl.vm.UserError(f"EXPECTED: name must be 1-{MAX_POLICY_NAME_LEN} characters")
        for label, v in (
            ("latent_cap_bps", latent_cap_bps),
            ("watching_cap_bps", watching_cap_bps),
            ("emerging_cap_bps", emerging_cap_bps),
            ("material_cap_bps", material_cap_bps),
            ("systemic_cap_bps", systemic_cap_bps),
            ("minimum_public_value_bps", minimum_public_value_bps),
            ("maximum_gaming_risk_bps", maximum_gaming_risk_bps),
            ("minimum_attribution_confidence_bps", minimum_attribution_confidence_bps),
        ):
            if v < 0 or v > BPS_DENOMINATOR:
                raise gl.vm.UserError(f"EXPECTED: {label} must be 0-{BPS_DENOMINATOR}")
        if not (latent_cap_bps <= watching_cap_bps <= emerging_cap_bps
                <= material_cap_bps <= systemic_cap_bps):
            raise gl.vm.UserError(
                "EXPECTED: caps must be monotonic: "
                "latent <= watching <= emerging <= material <= systemic"
            )
        return {
            "name": name,
            "latent_cap_bps": latent_cap_bps,
            "watching_cap_bps": watching_cap_bps,
            "emerging_cap_bps": emerging_cap_bps,
            "material_cap_bps": material_cap_bps,
            "systemic_cap_bps": systemic_cap_bps,
            "minimum_public_value_bps": minimum_public_value_bps,
            "maximum_gaming_risk_bps": maximum_gaming_risk_bps,
            "minimum_attribution_confidence_bps": minimum_attribution_confidence_bps,
        }

    # ======================================================================
    # Protocol control (owner-gated)
    # ======================================================================
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

    # ======================================================================
    # ObservationPolicy — reusable, versioned observation rules (spec ss.11)
    # ======================================================================
    @gl.public.write
    def create_observation_policy(
        self,
        name: str,
        candidate_types: list[str],
        minimum_evidence_categories: int,
        minimum_independent_sources: int,
        latent_rules: str,
        impact_rules: str,
        lineage_rules: str,
        gaming_rules: str,
        substitute_rules: str,
        checkpoint_interval: int,
    ) -> str:
        self._require_not_paused()
        payload = self._validated_observation_payload(
            name, candidate_types, minimum_evidence_categories, minimum_independent_sources,
            latent_rules, impact_rules, lineage_rules, gaming_rules, substitute_rules,
            checkpoint_interval,
        )
        n = int(self.observation_policy_count) + 1
        self.observation_policy_count = u256(n)
        pid = str(n)
        record = {
            "policy_id": pid,
            "family_id": pid,           # version 1 seeds its own family
            "version": 1,
            "creator": gl.message.sender_address.as_hex,
            "created_at": self._now(),
        }
        record.update(payload)
        self.observation_policies[pid] = json.dumps(record)
        self.observation_policy_status[pid] = "ACTIVE"
        self.observation_policy_index[str(n - 1)] = pid
        self.observation_policy_family_index[pid] = json.dumps([pid])
        return pid

    @gl.public.write
    def version_observation_policy(
        self,
        policy_id: str,
        name: str,
        candidate_types: list[str],
        minimum_evidence_categories: int,
        minimum_independent_sources: int,
        latent_rules: str,
        impact_rules: str,
        lineage_rules: str,
        gaming_rules: str,
        substitute_rules: str,
        checkpoint_interval: int,
    ) -> str:
        self._require_not_paused()
        if not policy_id or policy_id not in self.observation_policies:
            raise gl.vm.UserError("EXPECTED: observation policy does not exist")
        prev = json.loads(self.observation_policies[policy_id])
        caller = gl.message.sender_address.as_hex
        if caller != prev["creator"]:
            raise gl.vm.UserError("EXPECTED: only the policy creator can version it")
        family_id = prev["family_id"]
        versions = json.loads(self.observation_policy_family_index[family_id])
        if versions[-1] != policy_id:
            raise gl.vm.UserError("EXPECTED: can only version from the latest version of the family")
        payload = self._validated_observation_payload(
            name, candidate_types, minimum_evidence_categories, minimum_independent_sources,
            latent_rules, impact_rules, lineage_rules, gaming_rules, substitute_rules,
            checkpoint_interval,
        )
        n = int(self.observation_policy_count) + 1
        self.observation_policy_count = u256(n)
        new_pid = str(n)
        record = {
            "policy_id": new_pid,
            "family_id": family_id,
            "version": int(prev["version"]) + 1,
            "creator": caller,
            "created_at": self._now(),
        }
        record.update(payload)
        # Historical record is written once and never mutated. Only the
        # separate status map flips, so version history stays immutable.
        self.observation_policies[new_pid] = json.dumps(record)
        self.observation_policy_status[new_pid] = "ACTIVE"
        self.observation_policy_status[policy_id] = "INACTIVE"   # supersede previous
        self.observation_policy_index[str(n - 1)] = new_pid
        versions.append(new_pid)
        self.observation_policy_family_index[family_id] = json.dumps(versions)
        return new_pid

    @gl.public.write
    def set_observation_policy_status(self, policy_id: str, active: bool) -> str:
        self._require_not_paused()
        if not policy_id or policy_id not in self.observation_policies:
            raise gl.vm.UserError("EXPECTED: observation policy does not exist")
        prev = json.loads(self.observation_policies[policy_id])
        if gl.message.sender_address.as_hex != prev["creator"]:
            raise gl.vm.UserError("EXPECTED: only the policy creator can change its status")
        status = "ACTIVE" if active else "INACTIVE"
        self.observation_policy_status[policy_id] = status
        return status

    # ======================================================================
    # FundingPolicy — reusable, versioned deterministic funding rules (ss.12)
    # ======================================================================
    @gl.public.write
    def create_funding_policy(
        self,
        name: str,
        latent_cap_bps: int,
        watching_cap_bps: int,
        emerging_cap_bps: int,
        material_cap_bps: int,
        systemic_cap_bps: int,
        minimum_public_value_bps: int,
        maximum_gaming_risk_bps: int,
        minimum_attribution_confidence_bps: int,
    ) -> str:
        self._require_not_paused()
        payload = self._validated_funding_payload(
            name, latent_cap_bps, watching_cap_bps, emerging_cap_bps, material_cap_bps,
            systemic_cap_bps, minimum_public_value_bps, maximum_gaming_risk_bps,
            minimum_attribution_confidence_bps,
        )
        n = int(self.funding_policy_count) + 1
        self.funding_policy_count = u256(n)
        fid = str(n)
        record = {
            "funding_policy_id": fid,
            "family_id": fid,
            "version": 1,
            "creator": gl.message.sender_address.as_hex,
            "created_at": self._now(),
        }
        record.update(payload)
        self.funding_policies[fid] = json.dumps(record)
        self.funding_policy_status[fid] = "ACTIVE"
        self.funding_policy_index[str(n - 1)] = fid
        self.funding_policy_family_index[fid] = json.dumps([fid])
        return fid

    @gl.public.write
    def version_funding_policy(
        self,
        funding_policy_id: str,
        name: str,
        latent_cap_bps: int,
        watching_cap_bps: int,
        emerging_cap_bps: int,
        material_cap_bps: int,
        systemic_cap_bps: int,
        minimum_public_value_bps: int,
        maximum_gaming_risk_bps: int,
        minimum_attribution_confidence_bps: int,
    ) -> str:
        self._require_not_paused()
        if not funding_policy_id or funding_policy_id not in self.funding_policies:
            raise gl.vm.UserError("EXPECTED: funding policy does not exist")
        prev = json.loads(self.funding_policies[funding_policy_id])
        caller = gl.message.sender_address.as_hex
        if caller != prev["creator"]:
            raise gl.vm.UserError("EXPECTED: only the policy creator can version it")
        family_id = prev["family_id"]
        versions = json.loads(self.funding_policy_family_index[family_id])
        if versions[-1] != funding_policy_id:
            raise gl.vm.UserError("EXPECTED: can only version from the latest version of the family")
        payload = self._validated_funding_payload(
            name, latent_cap_bps, watching_cap_bps, emerging_cap_bps, material_cap_bps,
            systemic_cap_bps, minimum_public_value_bps, maximum_gaming_risk_bps,
            minimum_attribution_confidence_bps,
        )
        n = int(self.funding_policy_count) + 1
        self.funding_policy_count = u256(n)
        new_fid = str(n)
        record = {
            "funding_policy_id": new_fid,
            "family_id": family_id,
            "version": int(prev["version"]) + 1,
            "creator": caller,
            "created_at": self._now(),
        }
        record.update(payload)
        self.funding_policies[new_fid] = json.dumps(record)
        self.funding_policy_status[new_fid] = "ACTIVE"
        self.funding_policy_status[funding_policy_id] = "INACTIVE"   # supersede previous
        self.funding_policy_index[str(n - 1)] = new_fid
        versions.append(new_fid)
        self.funding_policy_family_index[family_id] = json.dumps(versions)
        return new_fid

    @gl.public.write
    def set_funding_policy_status(self, funding_policy_id: str, active: bool) -> str:
        self._require_not_paused()
        if not funding_policy_id or funding_policy_id not in self.funding_policies:
            raise gl.vm.UserError("EXPECTED: funding policy does not exist")
        prev = json.loads(self.funding_policies[funding_policy_id])
        if gl.message.sender_address.as_hex != prev["creator"]:
            raise gl.vm.UserError("EXPECTED: only the policy creator can change its status")
        status = "ACTIVE" if active else "INACTIVE"
        self.funding_policy_status[funding_policy_id] = status
        return status

    # ======================================================================
    # PublicGoodCandidate — registration + dormant-value lifecycle entry (ss.3)
    # ======================================================================
    @gl.public.write
    def register_candidate(
        self,
        name: str,
        description: str,
        candidate_type: str,
        primary_artifact_url: str,
        origin_date: str,
        public_access: bool,
        observation_policy_id: str,
        funding_policy_id: str,
    ) -> str:
        self._require_not_paused()
        if not name or len(name) > MAX_NAME_LEN:
            raise gl.vm.UserError(f"EXPECTED: name must be 1-{MAX_NAME_LEN} characters")
        if not description or len(description) > MAX_DESCRIPTION_LEN:
            raise gl.vm.UserError(f"EXPECTED: description must be 1-{MAX_DESCRIPTION_LEN} characters")
        if candidate_type not in CANDIDATE_TYPES:
            raise gl.vm.UserError(f"EXPECTED: invalid candidate_type '{candidate_type}'")
        self._validate_http_url(primary_artifact_url, "primary_artifact_url")
        if not origin_date or len(origin_date) > MAX_ORIGIN_DATE_LEN:
            raise gl.vm.UserError(f"EXPECTED: origin_date must be 1-{MAX_ORIGIN_DATE_LEN} characters")
        self._require_active_observation_policy(observation_policy_id)
        self._require_active_funding_policy(funding_policy_id)

        n = int(self.candidate_count) + 1
        self.candidate_count = u256(n)
        cid = str(n)
        if cid in self.candidates:
            # Unreachable with a monotonic counter; explicit no-silent-overwrite guard.
            raise gl.vm.UserError("EXPECTED: candidate id collision")
        candidate = {
            "candidate_id": cid,
            "submitter": gl.message.sender_address.as_hex,
            "name": name,
            "description": description,
            "candidate_type": candidate_type,
            "primary_artifact_url": primary_artifact_url,
            "origin_date": origin_date,
            "public_access": public_access,
            "observation_policy_id": observation_policy_id,
            "funding_policy_id": funding_policy_id,
            "status": "DISCOVERED",
            "created_at": self._now(),
        }
        self.candidates[cid] = json.dumps(candidate)
        self.candidate_index[str(n - 1)] = cid
        return cid

    # ======================================================================
    # Candidate evidence — latent-stage collection + permanent freeze (ss.13)
    #
    # The deterministic evidence layer that Stage 4 GenLayer adjudication will
    # later consume. It validates and stores real-world evidence, enforces
    # host-level source diversity, and then permanently freezes the latent
    # evidence set. It does NOT interpret evidence — evaluating latent value is
    # Stage 4 (evaluate_latent_value), which is intentionally not implemented
    # here. No evidence is ever deleted or mutated after submission.
    # ======================================================================
    @gl.public.write
    def submit_candidate_evidence(
        self,
        candidate_id: str,
        source_type: str,
        source_url: str,
        content_hash: str,
        summary: str,
        period_start: int,
        period_end: int,
    ) -> str:
        self._require_not_paused()
        # Rule 1: candidate must exist.
        if candidate_id not in self.candidates:
            raise gl.vm.UserError("EXPECTED: candidate not found")
        # Rule 3: no submission once the latent set is frozen. Checked before
        # the status read so a frozen candidate always reports the freeze reason.
        if candidate_id in self.latent_freeze:
            raise gl.vm.UserError("EXPECTED: latent evidence is frozen; no more submissions")
        candidate = json.loads(self.candidates[candidate_id])
        # Rule 2: candidate must still accept latent-stage evidence. Only
        # DISCOVERED does; a successful freeze moves it to LATENT.
        if candidate["status"] != "DISCOVERED":
            raise gl.vm.UserError("EXPECTED: candidate is not accepting latent-stage evidence")
        # Rule 4: source_type from the approved evidence-category allowlist.
        if source_type not in EVIDENCE_CATEGORIES:
            raise gl.vm.UserError(f"EXPECTED: invalid source_type '{source_type}'")
        # Rule 5: source_url must be a well-formed http(s) URL with a real host.
        self._validate_http_url(source_url, "source_url")
        # Rule 8: content_hash required, bounded, and whitespace-free.
        if not content_hash or len(content_hash) > MAX_CONTENT_HASH_LEN:
            raise gl.vm.UserError(f"EXPECTED: content_hash must be 1-{MAX_CONTENT_HASH_LEN} characters")
        for ch in content_hash:
            if ch.isspace():
                raise gl.vm.UserError("EXPECTED: content_hash must not contain whitespace")
        # Rule 9: summary required and bounded.
        if not summary or len(summary) > MAX_SUMMARY_LEN:
            raise gl.vm.UserError(f"EXPECTED: summary must be 1-{MAX_SUMMARY_LEN} characters")
        # Rule 10: deterministic period validation (0 <= start <= end <= now).
        now = self._now()
        if period_start < 0 or period_end < 0:
            raise gl.vm.UserError("EXPECTED: period_start and period_end must be non-negative")
        if period_start > period_end:
            raise gl.vm.UserError("EXPECTED: period_start must be <= period_end")
        if period_end > now:
            raise gl.vm.UserError("EXPECTED: period_end must not be in the future")
        # Rule 13: strict maximum evidence count per candidate.
        ids = (
            json.loads(self.candidate_evidence_ids[candidate_id])
            if candidate_id in self.candidate_evidence_ids
            else []
        )
        if len(ids) >= MAX_EVIDENCE_PER_CANDIDATE:
            raise gl.vm.UserError(
                f"EXPECTED: candidate already has the maximum {MAX_EVIDENCE_PER_CANDIDATE} evidence records"
            )
        # Rules 6/7: normalize and store the source host (port/userinfo stripped)
        # so ports cannot fake source independence.
        source_host = self._normalize_source_host(source_url)
        # Duplicate protection: reject an equivalent (normalized source URL +
        # content_hash) tuple already recorded for this candidate. The key is a
        # length-prefixed, injective encoding of (candidate_id, nurl, hash) so
        # distinct tuples can never collide into a false duplicate — the only
        # possible failure mode is over-rejection, never duplicate inflation.
        nurl = self._normalize_url_for_dedup(source_url)
        dedup_key = candidate_id + "@" + str(len(nurl)) + ":" + nurl + ":" + content_hash
        if dedup_key in self.evidence_dedup:
            raise gl.vm.UserError("EXPECTED: duplicate evidence (same normalized url + content_hash)")
        # Rules 11/12: monotonic, collision-safe id; never a silent overwrite.
        n = int(self.evidence_count) + 1
        self.evidence_count = u256(n)
        eid = str(n)
        if eid in self.evidence:
            raise gl.vm.UserError("EXPECTED: evidence id collision")
        record = {
            "evidence_id": eid,
            "candidate_id": candidate_id,
            "checkpoint_id": NULL_CHECKPOINT_ID,   # latent-stage: canonical null
            "submitter": gl.message.sender_address.as_hex,
            "source_type": source_type,
            "source_url": source_url,
            "source_host": source_host,
            "content_hash": content_hash,
            "summary": summary,
            "period_start": period_start,
            "period_end": period_end,
            "status": "SUBMITTED",                 # derived at read; baked for a complete row
            "submitted_at": now,
        }
        self.evidence[eid] = json.dumps(record)
        ids.append(eid)
        self.candidate_evidence_ids[candidate_id] = json.dumps(ids)
        self.evidence_dedup[dedup_key] = eid
        return eid

    @gl.public.write
    def freeze_latent_evidence(self, candidate_id: str) -> str:
        self._require_not_paused()
        if candidate_id not in self.candidates:
            raise gl.vm.UserError("EXPECTED: candidate not found")
        # Reject a double freeze — the set is sealed exactly once.
        if candidate_id in self.latent_freeze:
            raise gl.vm.UserError("EXPECTED: latent evidence already frozen")
        candidate = json.loads(self.candidates[candidate_id])
        if candidate["status"] != "DISCOVERED":
            raise gl.vm.UserError("EXPECTED: candidate is not in DISCOVERED state")
        ids = (
            json.loads(self.candidate_evidence_ids[candidate_id])
            if candidate_id in self.candidate_evidence_ids
            else []
        )
        total = len(ids)
        if total < 1:
            raise gl.vm.UserError("EXPECTED: cannot freeze with no evidence")
        # Aggregate distinct categories and distinct normalized hosts.
        categories = []
        hosts = []
        for eid in ids:
            rec = json.loads(self.evidence[eid])
            if rec["source_type"] not in categories:
                categories.append(rec["source_type"])
            if rec["source_host"] not in hosts:
                hosts.append(rec["source_host"])
        # Enforce the candidate's bound ObservationPolicy version. The exact
        # version referenced at registration governs (its rules are immutable);
        # we intentionally do NOT require it to still be ACTIVE, so a later
        # deactivation cannot strand a candidate mid-collection. This is the
        # policy gate — it cannot be bypassed.
        pid = candidate["observation_policy_id"]
        policy = json.loads(self.observation_policies[pid])
        min_cat = policy["minimum_evidence_categories"]
        min_src = policy["minimum_independent_sources"]
        if len(categories) < min_cat:
            raise gl.vm.UserError(
                f"EXPECTED: need >= {min_cat} distinct evidence categories, have {len(categories)}"
            )
        # Distinct-host diversity ONLY. This is obvious host-level independence,
        # not organizational independence (ambiguous independence is a Stage 4
        # GenLayer concern — see _normalize_source_host).
        if len(hosts) < min_src:
            raise gl.vm.UserError(
                f"EXPECTED: need >= {min_src} distinct source hosts, have {len(hosts)}"
            )
        now = self._now()
        snapshot = {
            "candidate_id": candidate_id,
            "frozen": True,
            "frozen_at": now,
            "observation_policy_id": pid,
            "evidence_count": total,
            "evidence_ids": ids,
            "distinct_category_count": len(categories),
            "distinct_categories": categories,
            "distinct_host_count": len(hosts),
            "distinct_hosts": hosts,
            "minimum_evidence_categories": min_cat,
            "minimum_independent_sources": min_src,
        }
        # Presence of this key IS the freeze flag; the snapshot is written once
        # and never mutated. Evidence rows are untouched (immutable), future
        # submissions are blocked, and every record is preserved historically.
        self.latent_freeze[candidate_id] = json.dumps(snapshot)
        # Lifecycle transition: DISCOVERED -> LATENT, only on a successful freeze.
        candidate["status"] = "LATENT"
        candidate["latent_frozen_at"] = now
        self.candidates[candidate_id] = json.dumps(candidate)
        return "LATENT"

    # ======================================================================
    # Views
    # ======================================================================
    @gl.public.view
    def get_candidate(self, candidate_id: str) -> str:
        if candidate_id not in self.candidates:
            raise gl.vm.UserError("EXPECTED: candidate not found")
        return self.candidates[candidate_id]

    @gl.public.view
    def list_candidates(self, offset: int, limit: int) -> str:
        total = int(self.candidate_count)
        o = max(0, offset)
        l = max(0, min(limit, MAX_LIST_LIMIT))
        items = []
        for i in range(o, min(o + l, total)):
            ordinal = str(i)
            if ordinal in self.candidate_index:
                cid = self.candidate_index[ordinal]
                if cid in self.candidates:
                    items.append(json.loads(self.candidates[cid]))
        return json.dumps({"items": items, "total": total})

    @gl.public.view
    def get_evidence(self, evidence_id: str) -> str:
        if evidence_id not in self.evidence:
            raise gl.vm.UserError("EXPECTED: evidence not found")
        return json.dumps(self._evidence_view(evidence_id))

    @gl.public.view
    def list_candidate_evidence(self, candidate_id: str, offset: int, limit: int) -> str:
        if candidate_id not in self.candidates:
            raise gl.vm.UserError("EXPECTED: candidate not found")
        ids = (
            json.loads(self.candidate_evidence_ids[candidate_id])
            if candidate_id in self.candidate_evidence_ids
            else []
        )
        total = len(ids)
        o = max(0, offset)
        l = max(0, min(limit, MAX_LIST_LIMIT))
        items = []
        for i in range(o, min(o + l, total)):
            eid = ids[i]
            if eid in self.evidence:
                items.append(self._evidence_view(eid))
        return json.dumps({
            "items": items,
            "total": total,
            "frozen": candidate_id in self.latent_freeze,
        })

    @gl.public.view
    def get_latent_evidence_set(self, candidate_id: str) -> str:
        # Minimal, safe inspection of the latent evidence set. Before freeze it
        # reports live progress toward the policy thresholds; after freeze it
        # returns the immutable snapshot captured at freeze time.
        if candidate_id not in self.candidates:
            raise gl.vm.UserError("EXPECTED: candidate not found")
        candidate = json.loads(self.candidates[candidate_id])
        if candidate_id in self.latent_freeze:
            snap = json.loads(self.latent_freeze[candidate_id])
            snap["candidate_status"] = candidate["status"]
            snap["requirements_met"] = True
            return json.dumps(snap)
        ids = (
            json.loads(self.candidate_evidence_ids[candidate_id])
            if candidate_id in self.candidate_evidence_ids
            else []
        )
        categories = []
        hosts = []
        for eid in ids:
            rec = json.loads(self.evidence[eid])
            if rec["source_type"] not in categories:
                categories.append(rec["source_type"])
            if rec["source_host"] not in hosts:
                hosts.append(rec["source_host"])
        pid = candidate["observation_policy_id"]
        policy = json.loads(self.observation_policies[pid])
        min_cat = policy["minimum_evidence_categories"]
        min_src = policy["minimum_independent_sources"]
        met = len(ids) >= 1 and len(categories) >= min_cat and len(hosts) >= min_src
        return json.dumps({
            "candidate_id": candidate_id,
            "frozen": False,
            "frozen_at": None,
            "candidate_status": candidate["status"],
            "observation_policy_id": pid,
            "evidence_count": len(ids),
            "distinct_category_count": len(categories),
            "distinct_categories": categories,
            "distinct_host_count": len(hosts),
            "distinct_hosts": hosts,
            "minimum_evidence_categories": min_cat,
            "minimum_independent_sources": min_src,
            "requirements_met": met,
        })

    @gl.public.view
    def get_observation_policy(self, policy_id: str) -> str:
        if policy_id not in self.observation_policies:
            raise gl.vm.UserError("EXPECTED: observation policy not found")
        rec = json.loads(self.observation_policies[policy_id])
        rec["status"] = self.observation_policy_status[policy_id]
        return json.dumps(rec)

    @gl.public.view
    def list_observation_policies(self, offset: int, limit: int) -> str:
        total = int(self.observation_policy_count)
        o = max(0, offset)
        l = max(0, min(limit, MAX_LIST_LIMIT))
        items = []
        for i in range(o, min(o + l, total)):
            ordinal = str(i)
            if ordinal in self.observation_policy_index:
                pid = self.observation_policy_index[ordinal]
                if pid in self.observation_policies:
                    rec = json.loads(self.observation_policies[pid])
                    rec["status"] = self.observation_policy_status[pid]
                    items.append(rec)
        return json.dumps({"items": items, "total": total})

    @gl.public.view
    def get_observation_policy_history(self, family_id: str) -> str:
        if family_id not in self.observation_policy_family_index:
            raise gl.vm.UserError("EXPECTED: observation policy family not found")
        versions = json.loads(self.observation_policy_family_index[family_id])
        out = []
        for pid in versions:
            rec = json.loads(self.observation_policies[pid])
            out.append({
                "policy_id": pid,
                "version": rec["version"],
                "status": self.observation_policy_status[pid],
                "created_at": rec["created_at"],
            })
        return json.dumps({"family_id": family_id, "versions": out})

    @gl.public.view
    def get_funding_policy(self, funding_policy_id: str) -> str:
        if funding_policy_id not in self.funding_policies:
            raise gl.vm.UserError("EXPECTED: funding policy not found")
        rec = json.loads(self.funding_policies[funding_policy_id])
        rec["status"] = self.funding_policy_status[funding_policy_id]
        return json.dumps(rec)

    @gl.public.view
    def list_funding_policies(self, offset: int, limit: int) -> str:
        total = int(self.funding_policy_count)
        o = max(0, offset)
        l = max(0, min(limit, MAX_LIST_LIMIT))
        items = []
        for i in range(o, min(o + l, total)):
            ordinal = str(i)
            if ordinal in self.funding_policy_index:
                fid = self.funding_policy_index[ordinal]
                if fid in self.funding_policies:
                    rec = json.loads(self.funding_policies[fid])
                    rec["status"] = self.funding_policy_status[fid]
                    items.append(rec)
        return json.dumps({"items": items, "total": total})

    @gl.public.view
    def get_funding_policy_history(self, family_id: str) -> str:
        if family_id not in self.funding_policy_family_index:
            raise gl.vm.UserError("EXPECTED: funding policy family not found")
        versions = json.loads(self.funding_policy_family_index[family_id])
        out = []
        for fid in versions:
            rec = json.loads(self.funding_policies[fid])
            out.append({
                "funding_policy_id": fid,
                "version": rec["version"],
                "status": self.funding_policy_status[fid],
                "created_at": rec["created_at"],
            })
        return json.dumps({"family_id": family_id, "versions": out})

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
                "policy_statuses": POLICY_STATUSES,
                "evidence_statuses": EVIDENCE_STATUSES,
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
                "max_name_len": MAX_NAME_LEN,
                "max_description_len": MAX_DESCRIPTION_LEN,
                "max_url_len": MAX_URL_LEN,
                "max_rule_len": MAX_RULE_LEN,
                "max_independent_sources": MAX_INDEPENDENT_SOURCES,
                "max_list_limit": MAX_LIST_LIMIT,
                "max_content_hash_len": MAX_CONTENT_HASH_LEN,
                "max_summary_len": MAX_SUMMARY_LEN,
            },
            "conventions": {
                "null_checkpoint_id": NULL_CHECKPOINT_ID,
            },
        })
