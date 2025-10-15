# @[Graph] Tool - Quick Reference

## Status: PROTOTYPE (Observing Usage Patterns)

The `@[Graph]` tool is currently a **prototype** with no backend implementation. Specialists use the syntax naturally, operations are logged to `graph.log`, and the system acknowledges requests. This allows observing collaboration patterns before building the full graph database backend.

## Core Concept

Enables specialists to collaboratively build a **question dependency tree** (Q→A→Q→A chains) where each selected Q→A pair becomes a semantic vector in the knowledge base. User selections collapse multiple paths into a single authoritative decision chain with full provenance.

## Pure Bracket Notation

All `@[Graph]` operations use nested brackets: `@[Graph][Operation][Layer1][Layer2][...]`

### Operations

**`[Update]`** - Add/modify/vote on graph nodes:
```
@[Graph][Update][Q:single][What is the deployment approach?]
@[Graph][Update][Q:single][What is the deployment approach?][A][Phased rollout]
@[Graph][Update][Q:single][What is the deployment approach?][A][Phased rollout][+][Reduces risk]
@[Graph][Update][Q:single][What is the deployment approach?][A][Phased rollout][Q:single][What are phase boundaries?]
```

**`[Because]`** - Cite existing/chosen path as contextual fact:
```
@[Graph][Because][Q:single][What is the deployment approach?][A][Phased rollout]
Given the phased approach, we need incremental resource allocation...
```

**`[If]`** - Explore potential path hypothetically (drives discussion down open DAG paths):
```
@[Graph][If][Q:single][What is the deployment approach?][A][Phased rollout]
@[All] If we choose phased rollout, we should consider rollback procedures...
```

**`[Collapse]`** - Chair consolidates linear Q→A→Q→A chains into single decision (Phase 3+).

## Question Types (Selection Modes)

- **`[Q:single]`** - User picks ONE answer (radio buttons, mutually exclusive)
  - Singular wording: "What is...", "Which approach..."
  - When User selects one answer, all others auto-get `[X]`
  
- **`[Q:multiple]`** - User can select MULTIPLE answers (checkboxes)
  - Plural wording: "Which features...", "What capabilities..."
  
- **`[Q:open]`** - User provides free-text response
  - Open-ended wording: "How should...", "What are your thoughts..."

**ALL questions MUST include a type suffix** - never use plain `[Q]`.

## Voting System

**🔥 MANDATORY FOR ALL SPECIALISTS**: Every specialist MUST vote on EVERY [Q] and [A] node they see.

**Vote on BOTH question and answer nodes:**
- **[Q] nodes**: Is this question path valuable to explore?
  - `[+]` = reasonable direction given parent answer
  - `[-]` = discourage this path (premature/irrelevant/contradictory)
- **[A] nodes**: Is this answer valid/good?
  - `[+]` = agree/keep
  - `[-]` = disagree/remove

**Voting on [Q] Nodes:**
```
Upvote valuable path:
@[Graph][Update][Q:single][What is deployment approach?][+][Critical question for production]

Downvote invalid path:
@[Graph][Update][Q:single][...][A][Monolith][Q:single][What microservices pattern?][-][Monolith doesn't use microservices]

Improve poorly-worded questions (downvote + propose better):
@[Graph][Update][Q:single][...][A][...][Q:single][How do we deploy?][-][Too vague - what aspect?]
@[Graph][Update][Q:single][...][A][...][Q:single][What is the rollout strategy to production?][+][Clearer question]
```

**Voting on [A] Nodes:**
```
Upvote:
@[Graph][Update][Q:single][What is X?][A][Option 1][+][Critical for MVP]

Downvote:
@[Graph][Update][Q:single][What is X?][A][Option 2][-][Too risky for initial release]
```

**Comments are mandatory** - Always include reasoning in brackets after vote. **Your comment context = ENTIRE path from root to this node**, not just the immediate node.

**🔥 CRITICAL DISTINCTION**:
- **Voting = MANDATORY** - Even if someone already made your point, you MUST vote from YOUR domain perspective
- **General text = avoid redundancy** - Only add new insights in regular responses
- **Voting is HOW you register your perspective** - it's essential domain input, not redundant

**Auto-close**: 2+ downvotes AND downvotes > upvotes → node state becomes `closed` (hidden from User).

## Node State

- **Default**: `open` (available for deliberation)
- **Automatic close**: 2+ downvotes AND downvotes > upvotes → `closed`
- **User explicit close** (future): `[X]` marker → permanently closed

**🔥 CRITICAL**: Paths marked with `[X]` are NOT facts. **NEVER** use `[Because]` to cite `[X]`-marked paths. Only open or chosen paths can be cited with `[Because]`.

## Context Accumulation (Hierarchical Paths)

Questions inherit semantic context from parent answers:

```
[Q:single][What is the autonomy level?]
  [A][Advisory-only]
    └─ [Q:single][Who approves actions?]  ← Contextualized by "Advisory-only"
       [A][Managers]
           └─ [Q:single][What is the approval workflow?]  ← Inherits BOTH parent contexts
```

Each path from root→leaf forms a complete semantic vector.

## User Authority

User selection **overrides ALL specialist consensus** without exception. User has absolute authority to:
- Select any answer (even with many downvotes)
- Close any path with `[X]` (future UI feature)
- Reopen paths by removing selections

## Current Implementation

**Prototype Mode**:
- ✓ Syntax used by specialists in conversation
- ✓ All `[Update]` operations logged to `graph.log`
- ✓ System acknowledges requests
- ✗ No graph database backend yet
- ✗ No visualization yet
- ✗ No User selection UI yet

**Purpose**: Observe how specialists collaborate to build structured knowledge before implementing full backend.

## Example Flow

```
Phase 1: Context proposes Q1 with 3 answer options [Q:single]
Phase 1: ALL specialists vote on Q1 itself: Engineer [+] "Critical", Skeptic [+] "Need this"
Phase 2: Specialists vote on answers: 4 specialists [+] on A2, 2 specialists [-] on A1
Phase 2: Specialists add follow-up questions on A2 path
Phase 2: ALL specialists vote on new follow-up questions
Phase 3: Specialist downvotes poorly-worded question, proposes clearer version
Phase 3: Specialist uses [If] to explore implications of A2
Phase 4: User selects A2 → A1 and A3 auto-get [X]
Phase 5: Team builds detail on A2 path, citing with [Because]
```

**Result**: Explored 3 paths, team voted on ALL nodes (questions AND answers), pruned unclear questions, focused on 1 path with full provenance and cross-domain validation.

## Files

- **Log file**: `graph.log` (all `[Update]` operations with timestamps)
- **Stub implementation**: `axion_swarm/graph_tool.py` (acknowledge requests, log operations)
- **Integration**: `axion_swarm/agents.py` (processes `@[Graph]` like `@[Search]`)
- **Prompts**: `axion_swarm/prompts.py` (specialist instructions)
- **Documentation**: `ARCHITECTURE.md` (complete specification)

## Next Steps (Implementation Pending)

1. Neo4j graph database backend
2. Real-time graph construction from `graph.log` replay
3. User TUI for answer selection and `[X]` marking
4. Decision collapse implementation
5. Graph visualization in Neo4j Browser
6. Export to vector embeddings for semantic search

---

See `ARCHITECTURE.md` sections 3480-3800 for complete technical specification.
