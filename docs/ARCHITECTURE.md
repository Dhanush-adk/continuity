# Continuity architecture

## Problem and threat model

Continuity authorizes a proposed consequential action for a specific deployed agent. It addresses deployment changes hidden behind one Agent ID, capability expansion, financial-limit expansion, newly introduced sensitive tools, mandate violations, policy violations, ambiguous extraction, and the need to explain historical decisions.

It does not currently solve compromised hosts, stolen credentials, authentication, malicious administrators, payment fraud or AML/KYC, provider compromise, jailbreak prevention, or global agent reputation.

## Identity and trust

An `Agent` is a stable logical identity; immutable `AgentVersion` records identify deployments. A deterministic SHA-256 fingerprint covers model, prompt/code hashes, tools, capabilities, and permissions. Trust is attached to capabilities, not permanently to an Agent ID. Continuity evaluation inherits unchanged capabilities, restricts expanded authority to the previous trusted envelope, and requires explicit reauthorization for new sensitive capabilities.

## Intent and authorization

Gemini (or the mock provider) converts natural language into a candidate structured mandate. Raw output is retained. A deterministic canonicalizer maps only explicit aliases (`get`/`buy` → `purchase`, `GPUs` → `gpu`) and fail-closes on unknown critical values. A mandate must be explicitly activated before use.

`POST /authorize` then verifies deployment relationships, mandate status/expiry, capability trust and envelope, mandate constraints, and organization policy. Decisions are deterministic with precedence `DENY > REVIEW > ALLOW`; the LLM is never consulted for this decision.

## Evidence and review

Each authorization stores immutable snapshots of the proposed action, mandate, policy, capability trust, extraction evidence, and reason codes. A separate review record stores human approve/deny actions, reviewer identity, timestamp, and reason without mutating the original authorization result.

## Current limitations and future work

This is an experimental prototype with procurement-focused policy rules, minimal review, and no authentication/RBAC. Future work may add transaction history and velocity signals, anomaly detection, enterprise policy integrations, agent-runtime adapters, and payment-provider adapters.
