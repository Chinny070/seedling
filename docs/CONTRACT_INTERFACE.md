# SEEDLING deployment-candidate interface

Deployment candidate: `contracts/seedling.py`  
Contract class: `Seedling`  
Constructor: `Seedling()` — no arguments  
Public ABI: 56 methods (33 views, 23 writes). All methods return `str`; structured
records are JSON-encoded strings. No method is payable.

Types below use `str`, `int`, `bool`, and `list[str]` exactly as exposed by the
GenVM schema.

## Write methods

| Method and ordered parameters | Return |
|---|---|
| `pause()` | `str` |
| `unpause()` | `str` |
| `create_observation_policy(name:str, candidate_types:list[str], minimum_evidence_categories:int, minimum_independent_sources:int, latent_rules:str, impact_rules:str, lineage_rules:str, gaming_rules:str, substitute_rules:str, checkpoint_interval:int)` | `str` |
| `version_observation_policy(policy_id:str, name:str, candidate_types:list[str], minimum_evidence_categories:int, minimum_independent_sources:int, latent_rules:str, impact_rules:str, lineage_rules:str, gaming_rules:str, substitute_rules:str, checkpoint_interval:int)` | `str` |
| `set_observation_policy_status(policy_id:str, active:bool)` | `str` |
| `create_funding_policy(name:str, latent_cap_bps:int, watching_cap_bps:int, emerging_cap_bps:int, material_cap_bps:int, systemic_cap_bps:int, minimum_public_value_bps:int, maximum_gaming_risk_bps:int, minimum_attribution_confidence_bps:int)` | `str` |
| `version_funding_policy(funding_policy_id:str, name:str, latent_cap_bps:int, watching_cap_bps:int, emerging_cap_bps:int, material_cap_bps:int, systemic_cap_bps:int, minimum_public_value_bps:int, maximum_gaming_risk_bps:int, minimum_attribution_confidence_bps:int)` | `str` |
| `set_funding_policy_status(funding_policy_id:str, active:bool)` | `str` |
| `register_candidate(name:str, description:str, candidate_type:str, primary_artifact_url:str, origin_date:str, public_access:bool, observation_policy_id:str, funding_policy_id:str)` | `str` |
| `submit_candidate_evidence(candidate_id:str, source_type:str, source_url:str, content_hash:str, summary:str, period_start:int, period_end:int)` | `str` |
| `freeze_latent_evidence(candidate_id:str)` | `str` |
| `evaluate_latent_value(candidate_id:str)` | `str` |
| `open_checkpoint(candidate_id:str, period_start:int, period_end:int)` | `str` |
| `submit_checkpoint_evidence(checkpoint_id:str, source_type:str, source_url:str, content_hash:str, summary:str, period_start:int, period_end:int)` | `str` |
| `freeze_checkpoint(checkpoint_id:str)` | `str` |
| `evaluate_public_value(checkpoint_id:str)` | `str` |
| `register_contribution_node(candidate_id:str, contributor:str, artifact_type:str, artifact_url:str, artifact_hash:str, role:str, summary:str)` | `str` |
| `register_lineage_edge(candidate_id:str, from_node_id:str, to_node_id:str, relationship_type:str, evidence_refs:list[str], claimed_strength_bps:int)` | `str` |
| `evaluate_lineage(checkpoint_id:str)` | `str` |
| `calculate_funding(checkpoint_id:str)` | `str` |
| `open_appeal(candidate_id:str, checkpoint_id:str, ground:str, supporting_refs:list[str], statement:str)` | `str` |
| `evaluate_appeal(appeal_id:str)` | `str` |
| `finalize_checkpoint(candidate_id:str, checkpoint_id:str)` | `str` |

## View methods

| Method and ordered parameters | Return |
|---|---|
| `get_protocol_info()` | `str` |
| `get_candidate(candidate_id:str)` | `str` |
| `list_candidates(offset:int, limit:int)` | `str` |
| `get_evidence(evidence_id:str)` | `str` |
| `list_candidate_evidence(candidate_id:str, offset:int, limit:int)` | `str` |
| `get_latent_evidence_set(candidate_id:str)` | `str` |
| `get_latent_assessment(assessment_id:str)` | `str` |
| `list_candidate_latent_assessments(candidate_id:str, offset:int, limit:int)` | `str` |
| `get_checkpoint(checkpoint_id:str)` | `str` |
| `list_checkpoints(candidate_id:str, offset:int, limit:int)` | `str` |
| `list_checkpoint_evidence(checkpoint_id:str, offset:int, limit:int)` | `str` |
| `get_checkpoint_evidence_set(checkpoint_id:str)` | `str` |
| `get_impact_verdict(verdict_id:str)` | `str` |
| `list_checkpoint_impact_verdicts(checkpoint_id:str, offset:int, limit:int)` | `str` |
| `get_lineage_verdict(lineage_verdict_id:str)` | `str` |
| `list_candidate_lineage_verdicts(candidate_id:str, offset:int, limit:int)` | `str` |
| `get_funding_calculation(funding_calculation_id:str)` | `str` |
| `list_candidate_funding_calculations(candidate_id:str, offset:int, limit:int)` | `str` |
| `get_candidate_funding_summary(candidate_id:str)` | `str` |
| `get_appeal(appeal_id:str)` | `str` |
| `list_candidate_appeals(candidate_id:str, offset:int, limit:int)` | `str` |
| `get_funding_preview(checkpoint_id:str)` | `str` |
| `get_checkpoint_finalization(checkpoint_id:str)` | `str` |
| `get_contribution_node(node_id:str)` | `str` |
| `list_contribution_nodes(candidate_id:str, offset:int, limit:int)` | `str` |
| `get_lineage_edge(edge_id:str)` | `str` |
| `list_lineage_edges(candidate_id:str, offset:int, limit:int)` | `str` |
| `get_observation_policy(policy_id:str)` | `str` |
| `list_observation_policies(offset:int, limit:int)` | `str` |
| `get_observation_policy_history(family_id:str)` | `str` |
| `get_funding_policy(funding_policy_id:str)` | `str` |
| `list_funding_policies(offset:int, limit:int)` | `str` |
| `get_funding_policy_history(family_id:str)` | `str` |

## Frontend-read map

- Discovery/dashboard: `list_candidates`, `get_candidate`, `get_protocol_info`.
- Candidate detail: candidate plus `get_latent_evidence_set`, latent-assessment
  history, checkpoints, contribution nodes, lineage edges, funding summary, appeals.
- Evidence: `get_evidence`, `list_candidate_evidence`,
  `list_checkpoint_evidence`, `get_checkpoint_evidence_set`.
- Checkpoints: `get_checkpoint`, `list_checkpoints`, impact verdicts,
  `get_checkpoint_finalization`.
- Lineage: contribution-node and edge getters/lists, lineage-verdict history.
- Funding: calculation getter/list, candidate summary, and effective
  `get_funding_preview`.
- Appeals: appeal getter/list and checkpoint finalization state.

The frontend must submit transactions directly to the write methods above. There
is no backend API or database for canonical protocol state.

## Lifecycle and error handling

Candidate states: `DISCOVERED`, `LATENT`, `WATCHING`, `EMERGING`, `MATERIAL`,
`SYSTEMIC`, `STALLED`, `DECLINED`, `ARCHIVED`. Checkpoint terminal states are
`FINALIZED` and `VOIDED`; appeal decisions are `UPHOLD`, `MODIFY`, `VOID`.

Expected transaction failures include paused protocol, missing/inactive policy,
duplicate candidate artifact, duplicate evidence/artifact/edge, insufficient frozen
evidence diversity, invalid lifecycle transition, malformed adjudication output,
unauthorized policy/finalization operation, active checkpoint conflict, storage cap,
and replay against finalized state. Clients should display the contract error and
refresh canonical state rather than predicting or replacing contract validation.
