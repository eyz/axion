# Graph Tool - Complete Architecture

**Version**: 1.0  
**Last Updated**: 2025-10-24

---

## Document Navigation

**This is the comprehensive technical architecture document.**

For different levels of detail:
- **Quick Overview**: See `EXECUTIVE_SUMMARY.md` - Concise bulleted summary for executives
- **Scientific Format**: See `GRAPH_TOOL_PAPER.md` - Formal academic paper with theorems and proofs
- **Concrete Example**: See `GRAPH_DEMO_FROM_CHECKPOINT.md` - Real conversation mapped to graph
- **Detailed Walkthrough**: See `GRAPH_PROVENANCE_ANALYSIS.md` - Step-by-step provenance analysis
- **Quick Reference**: See `GRAPH_TOOL_SUMMARY.md` - One-page cheat sheet

---

## Table of Contents

1. [Executive Summary](#executive-summary)
2. [Core Insight: Semantic Vector Architecture](#core-insight-semantic-vector-architecture)
3. [Fundamental Concepts](#fundamental-concepts)
4. [Neo4j Schema](#neo4j-schema)
5. [Bracket Syntax Specification](#bracket-syntax-specification)
6. [Question Types & Selection Modes](#question-types--selection-modes)
7. [Voting & Relevance System](#voting--relevance-system)
8. [User Authority](#user-authority)
9. [Decision Collapse & Preservation](#decision-collapse--preservation)
10. [Validation & Discovery](#validation--discovery)
11. [User TUI Design](#user-tui-design)
12. [Real-World Example: Checkpoint Analysis](#real-world-example-checkpoint-analysis)
13. [Implementation Guide](#implementation-guide)
14. [Integration with Axion Swarm](#integration-with-axion-swarm)

---

## Executive Summary

The `@[Graph]` tool is a **collaborative semantic embedding builder** where specialists and users work together to construct a structured knowledge base through question-answer pairs.

### The Breakthrough Insight

```
Each Q->A pair = One semantic vector embedding
All open paths = The scoped vector space being explored
Final selected Q->A pairs = The complete embedded knowledge base (THE OUTPUT)
```

**The graph isn't just tracking decisions - it's building a vector database collaboratively in real-time.**

### Key Features

- **Semantic Vector Building**: Each question-answer pair is a semantic vector
- **Multi-Agent Collaboration**: Specialists propose, vote, and refine vectors
- **User Authority**: User has absolute override on all specialist consensus
- **Hierarchical Paths**: Composite keys (e.g., `[Q1][A1][Q2][A1]`) embed full context
- **Progressive Validation**: Invalid paths return available options for discovery
- **Decision Collapse**: Linear chains compress into decisions while preserving provenance
- **Visual Graph DB**: Neo4j provides real-time visualization of semantic space
- **Primary Deliverable**: The graph IS the output, not a planning artifact

---

## Core Insight: Semantic Vector Architecture

### Each Q->A Pair is a Single Vector Embedding

**Every question-answer pair is encoded as ONE vector** - this is literal, not metaphorical.

```
Question: "What is deployment timeline?"
Answer:   "Timeline: 4 weeks"

Combined for embedding:
  "Question: What is deployment timeline?
   Answer: Timeline: 4 weeks"
   
    ↓ (sentence transformer)
    
Vector (384 dimensions):
  [0.023, -0.145, 0.891, ..., 0.234, -0.067, 0.445]
```

**This single vector encodes:**
- Semantic meaning: urgency, timeline constraint
- Domain context: deployment, planning  
- Decision weight: aggressive timeline choice
- Relationships: similar to other timeline vectors

**Why combine Q+A into single vector?**
- `embed("4 weeks")` → ambiguous (4 weeks for what?)
- `embed("Question: deployment timeline?\nAnswer: 4 weeks")` → contextually complete ✓

### Graph Hierarchy = Context Accumulation

**CRITICAL INSIGHT**: The hierarchical structure isn't just logical dependencies - it's **semantic context accumulation**.

```
[Q1] What is autonomy level?
  [A1] Advisory-only with mandatory human approval
    └─ [Q2] Who approves actions?
         [A2] Managers with documented authorization

Traditional view:
  Q2 depends on A1 (logical dependency)

Deeper truth:
  Q2 embedding INCLUDES A1 as context (semantic depth)
```

**Context-aware embedding:**

```python
# Without parent context (ambiguous)
embed("Question: Who approves actions?\nAnswer: Managers")
# → Generic vector about managers and approval

# With parent context (specific)
embed("""
Context: System is advisory-only with mandatory human approval
Question: Who approves actions?  
Answer: Managers with documented authorization
""")
# → Specific vector about manager approval in advisory AI systems
```

**The path IS the context:**

```
[Q1][A1][Q2][A2] = Context chain

When embedding Q2→A2:
  1. Extract parent path: [Q1][A1]
  2. Get parent Q→A text
  3. Include as context in embedding
  4. Result: Contextually rich vector, not standalone

Root nodes:   Context depth 0 (foundational, broad)
Child nodes:  Context depth 1 (includes parent)
Leaf nodes:   Context depth N (deeply contextualized, specific)
```

### Open Paths = Scoped Vector Space

The graph structure defines **what's in scope** for reasoning:

```
Closed paths = Vectors removed from semantic space
Open paths = Vectors available for retrieval/reasoning
User-selected = Vectors LOCKED IN to final output
```

**Voting is semantic relevance scoring:**
- Upvote = "This vector should be in the semantic space"
- Downvote = "This vector is not semantically relevant"
- Close = "Remove this vector from the space"

### Decisions = Compressed Vectors with English Labels

**A Decision node is THREE things simultaneously:**

1. **Compressed vector embedding**: 3 Q→A vectors → 1 Decision vector
2. **English-language summary**: Human-readable interpretation
3. **Provenance chain**: Full audit trail preserved

```
Before collapse: [Q1][A1][Q2][A2][Q3][A3]
  V1 = embed(Q1→A1)
  V2 = embed(Q1→A1 context + Q2→A2)  
  V3 = embed(Q1→A1→Q2→A2 context + Q3→A3)
  
  Total: 3 vectors × 384 dims = 1,152 numbers

After collapse: [D1] "Autonomy and Approval Policy"
  D1 = embed(summary + description + all Q→A pairs)
  
  Total: 1 vector × 384 dims = 384 numbers
  Compression: 3:1
  Information retained: ~90% (semantic essence preserved)
```

**The English label IS the human interpretation of the vector:**

```python
decision_vector = [0.189, 0.074, 0.316, ..., 0.237]
       ↕ (represents same semantics as) ↕
english_label = "Autonomy and Approval Policy"

Vector = Machine-readable semantic representation
English = Human-readable semantic representation
SAME CONTENT, different forms!
```

### Decision Validation Through Vector Similarity

**We can test if an English summary accurately represents the underlying Q→A chain:**

```python
# Ground truth: detailed chain
detailed_vec = embed_qa_chain(qa_pairs)

# Candidate: proposed summary
summary_vec = embed("Advisory System with Manager Approval")

# Validation
similarity = cosine_similarity(detailed_vec, summary_vec)

if similarity > 0.85:  ✓ Good match
if similarity < 0.70:  ❌ Needs refinement
```

**Iterative refinement workflow:**

1. Chair proposes decision summary
2. System validates semantic match (vector similarity)
3. If low, generate alternative candidates
4. Test each candidate, pick best match
5. Create decision with validated summary

**Quality guaranteed through vector similarity!**

### Final Output = Vector Collection

The complete set of selected Q->A pairs is the **embedded knowledge base**:

```
Final Output = ⋃ (all selected Q→A vectors + collapsed Decision vectors)

Example (forestry assistant from checkpoint):
  [Q1][Autonomy?][A][Advisory-only]              ← Vector 1 (root, broad)
  [Q2][Primary users?][A][Dispatchers]           ← Vector 2 (includes V1 context)
  [Q3][Has PII?][A][Yes-contracts]               ← Vector 3 (includes V1+V2 context)
  [D1] "User Access Policy"                      ← Compressed V1+V2+V3
  [Q4][Deployment?][A][Internal-only]            ← Vector 4
  [Q5][Retrieval?][A][RAG-hybrid]                ← Vector 5
  [D2] "Technical Architecture"                  ← Compressed V4+V5
  ...
  
Combined = Complete semantic specification of the solution
         = Multi-resolution vector space
         = Context-aware embedded knowledge base
```

**This collection IS the system's knowledge base.**

---

## Fundamental Concepts

### 1. Graph as Primary Deliverable

**Paradigm shift**: The graph is not a planning tool - it IS the output.

```
Traditional approach:
  Discussion → Decisions → Document → Implementation

Graph tool approach:
  Discussion → Graph (IS the decisions) → Export vectors → Done
```

The graph serves as:
- User's to-do/workflow UI
- Specialist research frontier
- System specification
- Embedded knowledge base
- Audit trail

### 2. Composite Hierarchical Paths

Node IDs embed their full context:

```
Dot notation (internal):    Q1.A1.Q2.A1
Bracket notation (tool):    [Q1][A1][Q2][A1]
```

**Benefits:**
- Self-documenting: ID contains full provenance
- Unique: No collisions across graph
- Context-rich: Specialists don't lose scope
- Queryable: Can extract path segments

### 3. Collaborative Vector Building

```
Context specialist → Proposes question
  ↓
Multiple specialists → Propose alternative answers
  ↓
All specialists → Vote on relevance
  ↓
User → Selects final answer(s)
  ↓
Selected Q->A pairs → Become embedded knowledge
```

### 4. Research Frontier

**Open leaf nodes = Research frontier**

Specialists focus exploration on open edges:
```
[Q1][A1] ← Selected
  └─ [Q2] ← Pending (FRONTIER - needs attention)
       ├─ [A1] ← Open (proposed)
       └─ [A2] ← Open (proposed)

[Q1][A2] ← Closed (path locked, not frontier)
  └─ [Q3] ← Closed (entire subtree locked)
```

---

## Neo4j Schema

### Node Types

#### Question Node

```cypher
CREATE (q:Question {
  id: STRING,                    // Composite path: "Q1.A1.Q2" or "[Q1][A1][Q2]"
  text: STRING,                  // Question text
  selection_mode: STRING,        // "single" | "multi" | "open"
  min_selections: INTEGER,       // Minimum answers required
  max_selections: INTEGER,       // Maximum answers allowed (null = unlimited)
  
  // State
  status: STRING,                // "pending" | "answered" | "not_applicable"
  state: STRING,                 // "open" | "closed" | "user_closed"
  
  // Voting
  upvoters: [STRING],            // List of specialist names who upvoted
  downvoters: [STRING],          // List of specialist names who downvoted
  relevance_votes: INTEGER,      // Count of upvotes
  not_applicable_votes: INTEGER, // Count of downvotes
  
  // Metadata
  requester: STRING,             // Specialist who created this question
  phase: INTEGER,                // Phase number when created
  priority: STRING,              // "normal" | "high" | "critical"
  created_at: DATETIME,
  answered_at: DATETIME,
  answered_by: STRING,           // "USER" | specialist name
  last_vote_comment: STRING,
  last_voted_at: DATETIME,
  
  // Context for embedding
  parent_path: STRING,           // Path to parent: "[Q1][A1]" (for context accumulation)
  context_depth: INTEGER,        // Depth in graph: 0=root, 1=child, etc.
  
  // Vector embedding (not typically stored for questions alone)
  embedding: [FLOAT],            // Optional: vector representation of question
  embedded_at: DATETIME
})
```

#### Answer Node

**This is where Q→A pair vectors are stored!**

```cypher
CREATE (a:Answer {
  id: STRING,                    // Composite path: "Q1.A1" or "[Q1][A1]"
  text: STRING,                  // Answer text (context-rich)
  question_text: STRING,         // Parent question text (for context)
  
  // Selection
  is_selected: BOOLEAN,          // User selected this answer
  selected: BOOLEAN,             // Alias for is_selected
  user_override: BOOLEAN,        // User overrode specialist consensus
  override_reason: STRING,       // Why user overrode
  
  // State
  state: STRING,                 // "open" | "closed" | "selected" | "user_closed" | "archived"
  
  // Voting
  upvoters: [STRING],            // Specialists who upvoted
  downvoters: [STRING],          // Specialists who downvoted
  relevance_votes: INTEGER,      // Count of upvotes
  not_applicable_votes: INTEGER, // Count of downvotes
  
  // Metadata
  created_at: DATETIME,
  last_vote_comment: STRING,
  last_voted_at: DATETIME,
  
  // ===== CRITICAL: VECTOR EMBEDDING =====
  // This stores the Q→A pair as a single semantic vector
  embedding: [FLOAT],            // Vector: embed(parent_context + question + answer)
  embedded_at: DATETIME,
  embedded_with_context: BOOLEAN, // Was parent context included in embedding?
  context_depth: INTEGER,        // How many ancestors in context (0=root, 1=child, etc.)
  parent_context: STRING,        // Text of parent Q→A pairs used as context
  
  // Decision tracking
  archived_into_decision: STRING // Decision ID if this was collapsed
})
```

**How the embedding is created:**

```python
# Root answer (no parent context)
embedding = embed("Question: {q.text}\nAnswer: {a.text}")
# → context_depth = 0

# Child answer (includes parent context)
parent_context = get_parent_qa_text(parent_path)
embedding = embed(f"""
Context: {parent_context}
Question: {q.text}
Answer: {a.text}
""")
# → context_depth = 1

# Each answer node stores ONE vector representing the complete Q→A pair
# with accumulated context from ancestors.
```

#### Decision Node

**Decisions are compressed vectors with human-readable labels!**

```cypher
CREATE (d:Decision {
  id: STRING,                    // "D1", "D2", etc.
  title: STRING,                 // Short decision summary (human-readable form)
  description: STRING,           // Full decision text
  
  // Collapsed path
  collapsed_path: [STRING],      // List of node IDs in original sequence
  collapsed_path_brackets: STRING, // Full bracket notation: "[Q1][A1][Q2][A1]..."
  original_qa_pairs: [MAP],      // [{q: "text", a: "text"}, ...]
  
  // State
  state: STRING,                 // "active" | "archived" | "expanded"
  
  // Provenance
  collapsed_at: DATETIME,
  collapsed_by: STRING,          // Usually "Chair"
  collapsed_phase: INTEGER,
  
  // References to original nodes (for expansion/forking)
  original_question_ids: [STRING],
  original_answer_ids: [STRING],
  
  // ===== CRITICAL: COMPRESSED VECTOR =====
  // This stores the ENTIRE decision chain as a single vector
  embedding: [FLOAT],            // Vector: embed(summary + description + all Q→A pairs)
  embedded_at: DATETIME,
  embedding_method: STRING,      // "combined_text_with_summary" | "averaged_qa_vectors"
  
  // Validation metadata
  summary_similarity: FLOAT,     // How well title matches underlying chain (0-1)
  validated_at: DATETIME
})
```

**Decision embedding creation:**

```python
# Method 1: Hierarchical embedding (recommended)
decision_embedding = embed(f"""
Decision: {title}

Summary: {description}

Details:
{format_all_qa_pairs(original_qa_pairs)}
""")

# Method 2: Average existing Q→A vectors
qa_vectors = [get_embedding(qa) for qa in original_qa_pairs]
decision_embedding = weighted_average(summary_vector, qa_vectors)

# The decision vector compresses 3-5 Q→A vectors into 1
# Semantic compression ratio: 3:1 to 5:1
# Information retention: ~90% (semantic essence preserved)
```

### Relationships

```cypher
// Question to Answer
CREATE (q:Question)-[:HAS_ANSWER]->(a:Answer)

// Answer to child Question (dependency)
CREATE (a:Answer)-[:LEADS_TO]->(q:Question)

// Decision to original nodes (provenance)
CREATE (d:Decision)-[:COLLAPSED_FROM]->(q:Question)
CREATE (d:Decision)-[:COLLAPSED_FROM]->(a:Answer)

// Decision replacement
CREATE (d:Decision)-[:REPLACES]->(q:Question)

// Forking
CREATE (q:Question)-[:FORKED_FROM]->(d:Decision)
```

### Key Indexes

```cypher
// Performance
CREATE INDEX question_id FOR (q:Question) ON (q.id);
CREATE INDEX answer_id FOR (a:Answer) ON (a.id);
CREATE INDEX decision_id FOR (d:Decision) ON (d.id);

// State queries
CREATE INDEX question_status FOR (q:Question) ON (q.status);
CREATE INDEX question_state FOR (q:Question) ON (q.state);
CREATE INDEX answer_state FOR (a:Answer) ON (a.state);

// Vector search
CREATE VECTOR INDEX question_embedding FOR (q:Question) ON (q.embedding)
  OPTIONS {indexConfig: {`vector.dimensions`: 384, `vector.similarity_function`: 'cosine'}};
CREATE VECTOR INDEX answer_embedding FOR (a:Answer) ON (a.embedding)
  OPTIONS {indexConfig: {`vector.dimensions`: 384, `vector.similarity_function`: 'cosine'}};
```

---

## Bracket Syntax Specification

### Design Philosophy

Inspired by HL7 medical coding standards: **pure bracket-nested token structure**.

Every element (tool, action, question, answer, parameters) is wrapped in `[ ]`.

### Operations

#### 1. Update (Create/Modify Nodes)

**Create question:**
```
@[Graph][Update][Q][What is your deployment timeline?]
```

**Create question with mode:**
```
@[Graph][Update][Q][What is your deployment timeline?][mode:single]
```

**Create answer under question:**
```
@[Graph][Update][Q][What is your deployment timeline?][A][Timeline: 4 weeks]
```

**Create nested question under answer:**
```
@[Graph][Update][Q][What is deployment?][A][Timeline: 4 weeks][Q][What features in 4 weeks?]
```

**Vote on node:**
```
@[Graph][Update][Q][What is deployment?][A][Timeline: 4 weeks][vote:relevant][comment:Aggressive but achievable]
```

#### 2. Select (User Selection)

**User selects an answer:**
```
@[Graph][Select][Q][What is deployment?][A][Timeline: 4 weeks]
```

#### 3. Complete (Finish Multi/Open Question)

**Mark multi-choice question complete:**
```
@[Graph][Complete][Q][What MVP features?]
```

#### 4. List (Query Graph)

**List all pending questions:**
```
@[Graph][List][pending]
```

**List answers for a question:**
```
@[Graph][List][Q][What is deployment?]
```

**List frontier (open leaf nodes):**
```
@[Graph][List][frontier]
```

#### 5. Because (Reference/Citation)

**Reference a graph path in reasoning:**
```
@[Graph][Because][Q][What is deployment?][A][Timeline: 4 weeks]

As stated earlier @[Graph][Because][Q][What is deployment?][A][Timeline: 4 weeks], 
we have an aggressive timeline...
```

This is non-actionable - it's for citing graph context.

#### 6. Collapse (Create Decision)

**Collapse a linear path into decision:**
```
@[Graph][Collapse][Q1][A1][Q2][A1][Q3][A1][title:User persona and permissions]
```

#### 7. Revisit (Query Decision)

**Query collapsed decision:**
```
@[Graph][Revisit][D1]
```

Returns the full bracket path and original Q->A pairs.

### Progressive Validation with Discovery

**If any layer doesn't exist, system returns available options:**

```
Specialist: @[Graph][Update][Q][What is timeline?][A][5 weeks][vote:relevant]
                                                        ↑
                                            This answer doesn't exist

System response:
  Path invalid at layer [A]. Available answers for [Q][What is timeline?]:
    - [A][Timeline: 4 weeks] (3 upvotes)
    - [A][Timeline: 3 months] (1 upvote)
    - [A][Timeline: 6 months] (0 upvotes, 2 downvotes)
```

**This turns errors into guided discovery.**

---

## Question Types & Selection Modes

### Type 1: Single-Choice (Mutually Exclusive)

**User picks ONE answer, all others auto-lock immediately.**

```json
{
  "selection_mode": "single",
  "min_selections": 1,
  "max_selections": 1
}
```

**Use cases:**
- Binary decisions (yes/no)
- Exclusive options (timeline: 4 weeks XOR 3 months)
- Configuration choices (database: Postgres XOR MongoDB)

**Behavior:**
```
Before selection:
  [Q1] Deployment? (single)
    [A1] "4 weeks" 🔓
    [A2] "3 months" 🔓

User selects [A1]:
  [Q1] Deployment? ✓ answered
    [A1] "4 weeks" ✓ SELECTED
    [A2] "3 months" 🔒 LOCKED (auto-closed)
    
Question auto-completes, unselected answers auto-close.
```

### Type 2: Multi-Choice (Additive)

**User can select MULTIPLE answers, explicit completion required.**

```json
{
  "selection_mode": "multi",
  "min_selections": 1,
  "max_selections": null
}
```

**Use cases:**
- Feature selection (Auth AND CRUD AND Search)
- Technology stack (Python AND JavaScript AND SQL)
- Requirements gathering (Security AND Performance)

**Behavior:**
```
Before:
  [Q5] What features? (multi)
    [A1] "Auth" 🔓
    [A2] "CRUD" 🔓
    [A3] "Search" 🔓

User selects [A1]:
  [Q5] What features? (partially answered)
    [A1] "Auth" ✓ SELECTED
    [A2] "CRUD" 🔓 still open
    [A3] "Search" 🔓 still open

User selects [A2]:
  [Q5] What features? (partially answered)
    [A1] "Auth" ✓ SELECTED
    [A2] "CRUD" ✓ SELECTED
    [A3] "Search" 🔓 still open

User marks complete:
  [Q5] What features? ✓ answered
    [A1] "Auth" ✓ SELECTED
    [A2] "CRUD" ✓ SELECTED
    [A3] "Search" 🔒 LOCKED (not selected)
```

### Type 3: Open (Unlimited)

**User adds unlimited custom answers.**

```json
{
  "selection_mode": "open",
  "min_selections": 0,
  "max_selections": null
}
```

**Use cases:**
- Brainstorming (What features to prioritize?)
- Data sources (What systems to integrate?)
- Constraints (What limitations exist?)

**Behavior:**
```
Initially:
  [Q8] What data sources? (open)
    (no answers yet)

User adds custom answers:
  [Q8] What data sources? (open)
    [A1] "Internal CRM" ✓ (user added)
    [A2] "Vendor DB" ✓ (user added)
    [A3] "External API" ✓ (user added)

User marks complete:
  [Q8] What data sources? ✓ answered
    All answers selected (user-created)
```

---

## Voting & Relevance System

### Vote Types

**Two vote types per node:**

1. **Relevant** (`upvote`): "This node should be in the semantic space"
2. **Not Applicable** (`downvote`): "This node should be removed from scope"

### State Computation

**Automatic state based on vote balance:**

```python
if downvotes >= 2 AND downvotes > upvotes:
    state = "closed"
else:
    state = "open"
```

**Examples:**
```
3 upvotes, 0 downvotes → open
3 upvotes, 1 downvote → open
2 upvotes, 2 downvotes → open (tie)
1 upvote, 2 downvotes → closed
0 upvotes, 2 downvotes → closed
```

### Vote Changes (Reopening Paths)

Specialists can change their votes:

```
Initial: 2 upvotes, 3 downvotes → closed

Skeptic changes vote: downvote → upvote
Result: 3 upvotes, 2 downvotes → REOPENED (open)
```

This mirrors specialists changing their minds as discussion evolves.

### Mandatory Comments

**Every vote requires a comment explaining rationale:**

```
@[Graph][Update][Q][What is deployment?][A][Timeline: 6 months][vote:not_applicable][comment:Too long for MVP iteration]
```

Comments are stored with the vote and displayed in the TUI.

### Tracking Individual Voters

Nodes track who voted:

```json
{
  "upvoters": ["Engineer", "Research", "Context"],
  "downvoters": ["Skeptic", "Ethicist"],
  "last_vote_comment": "Skeptic: Too long for MVP iteration"
}
```

This enables:
- Transparency (who supports what)
- Conflict detection (divided opinions)
- Vote change tracking
- Authority resolution (user overrides)

---

## User Authority

### Absolute Override Power

**User vote = ABSOLUTE authority, overrides ALL specialist consensus.**

```
Specialists unanimous (5 upvotes): [A1] "Use MongoDB"
User selects: [A2] "Use PostgreSQL"

Result: [A2] selected, [A1] locked
  - User choice wins
  - System issues warning: "Overriding specialist consensus"
  - Specialists MUST adapt recommendations to PostgreSQL
```

### User Vote Capture

**User selections = Explicit upvotes:**
```json
{
  "upvoters": ["Engineer", "Research", "USER"],
  "user_override": false
}
```

**User rejections = Implicit downvotes:**
```json
// User selected A1, rejected A2
{
  "id": "A2",
  "downvoters": ["Skeptic", "USER"],
  "state": "user_closed",
  "rejected_by": "USER"
}
```

### User Authority Examples

#### Example 1: User Agrees with Consensus

```
Question: "Use advisory-only mode?"
Specialists: 5 upvotes for [A1] "Advisory-only"
User selects: [A1] "Advisory-only"

Result:
  [A1] {
    "upvoters": ["Context", "Research", "Engineer", "Skeptic", "Ethicist", "USER"],
    "selected": true,
    "user_override": false
  }
```

#### Example 2: User Overrides Consensus

```
Question: "What deployment timeline?"
Specialists: 4 upvotes for [A1] "4 weeks"
             1 upvote for [A2] "3 months"
User selects: [A2] "3 months"

Result:
  [A2] {
    "upvoters": ["Skeptic", "USER"],
    "selected": true,
    "user_override": true,
    "override_reason": "User selected despite 4 specialists recommending [A1]"
  }
  
System message: "⚠️ USER OVERRIDE: Selected [A2] despite specialist recommendation for [A1]"
Specialists: Must adapt all future recommendations to 3-month timeline
```

#### Example 3: User Closes Critical Question

```
Question: "Should we include PII masking?"
Specialists: 5 upvotes (unanimous: "critical for ethics")
User response: Closes question without answering

Result:
  Question {
    "state": "user_closed",
    "status": "not_applicable",
    "closed_by": "USER"
  }
  
System message: "⚠️ User closed critical safety question [Q5]"
Specialists: Cannot reopen, must adapt recommendations
```

### User Cannot Be Overridden

**Specialists CANNOT override user decisions.**

```
User selects [A1]
Engineer: "@[Graph][Update][Q][...][A][A2][vote:relevant][comment:Better choice]"

Result: A2 can be proposed, voted on, but A1 remains selected.
         Engineer's vote does NOT change user's selection.
         User must explicitly change selection to override themselves.
```

---

## Decision Collapse & Preservation

### Linear Path Collapsing

**Unbranched Q->A->Q->A sequences collapse into a single Decision node.**

```
Before collapse:
  [Q1] What is autonomy level?
    [A1] "Advisory-only" ✓
      └─ [Q2] Who approves actions?
           [A1] "Managers with documented authorization" ✓
                └─ [Q3] What approval workflow?
                     [A1] "Preview → Review → Sign-off → Execute" ✓

After collapse:
  [D1] "Autonomy and Approval Policy"
       Summary: Advisory-only system with manager sign-off workflow
       
       Collapsed path: [Q1][A1][Q2][A1][Q3][A1]
       Original Q->A pairs preserved inside decision node
```

**Benefits:**
- Reduces cognitive load for user
- Simplifies graph visualization
- Makes progress visible
- Retains full provenance

### Decision Preservation

**Collapsed decisions preserve EVERYTHING:**

```json
{
  "id": "D1",
  "title": "Autonomy and Approval Policy",
  "description": "Advisory-only system with manager sign-off workflow",
  
  "collapsed_path": ["Q1", "A1", "Q2", "A1", "Q3", "A1"],
  "collapsed_path_brackets": "[Q1][A1][Q2][A1][Q3][A1]",
  
  "original_qa_pairs": [
    {
      "question": "What is autonomy level?",
      "answer": "Advisory-only with mandatory human approval",
      "upvoters": ["Context", "Research", "Engineer", "Skeptic", "Ethicist", "USER"],
      "phase": 1
    },
    {
      "question": "Who approves actions?",
      "answer": "Managers with documented authorization",
      "upvoters": ["Context", "Engineer", "USER"],
      "phase": 2
    },
    {
      "question": "What approval workflow?",
      "answer": "Preview → Review → Sign-off → Execute",
      "upvoters": ["Engineer", "USER"],
      "phase": 2
    }
  ]
}
```

### Audit Trail ("How did we decide?")

```
User/Specialist: @[Graph][Revisit][D1]

System returns:
  Decision D1: "Autonomy and Approval Policy"
  
  Full provenance:
    [Q1] What is autonomy level?
      → [A1] Advisory-only (5 specialist upvotes + USER)
        [Q2] Who approves actions?
          → [A1] Managers with documented authorization (2 specialist + USER)
            [Q3] What approval workflow?
              → [A1] Preview → Review → Sign-off → Execute (1 specialist + USER)
  
  Can expand, fork, or reference any step.
```

### Expansion & Forking

**Expand decision back to original nodes:**
```
@[Graph][Expand][D1]

Result: D1 archived, original Q1->A1->Q2->A1->Q3->A1 restored
        All nodes return to "open" state for re-evaluation
```

**Fork from decision to explore alternatives:**
```
@[Graph][Fork][D1][at:Q2]

Result: Creates new branch from Q2 with alternative answers
        Original decision remains intact
```

### Chair's Collapse Role

**Chair synthesizes discussion by collapsing linear consensus paths:**

```
Phase 3 Chair message:
  "I observe strong consensus on autonomy policy (5 unanimous votes across 3 questions).
   
   @[Graph][Collapse][Q1][A1][Q2][A1][Q3][A1][title:Autonomy and Approval Policy][description:Advisory-only system requiring manager sign-off with preview-review-execute workflow]
   
   This simplifies the user's view while preserving full provenance for audit."
```

---

## Validation & Discovery

### Progressive Validation

**System validates each layer of bracket path sequentially:**

```
Specialist: @[Graph][Update][Q][What is timeline?][A][5 weeks][vote:relevant]

Validation:
  Layer 1: [Graph] ✓ Valid tool
  Layer 2: [Update] ✓ Valid operation
  Layer 3: [Q][What is timeline?] ✓ Question exists
  Layer 4: [A][5 weeks] ✗ INVALID - Answer doesn't exist
           
System returns available answers at Layer 3 (parent level)
```

### Discovery Feedback

**Invalid paths return what DOES exist:**

```
System response:
  ❌ Path invalid at [A][5 weeks]
  
  Available answers for [Q][What is timeline?]:
    - [A][Timeline: 4 weeks] (3 upvotes, 0 downvotes) ⭐ RECOMMENDED
    - [A][Timeline: 3 months] (1 upvote, 0 downvotes)
    - [A][Timeline: 6 months] (0 upvotes, 2 downvotes) 🔒 CLOSED
  
  Use exact bracket notation to reference existing nodes.
```

### Unified Discovery Interface

**Failed updates automatically trigger list operation:**

```
Attempt: @[Graph][Update][Q][What is timeline?][A][5 weeks][vote:relevant]
         (Answer doesn't exist)

System behavior:
  1. Detect invalid path
  2. Automatically run: @[Graph][List][Q][What is timeline?]
  3. Return available options
  
This combines "update" and "list" in one interaction.
```

### Fuzzy Matching (Future)

**Potential enhancement: Suggest similar nodes for typos:**

```
Input: @[Graph][Update][Q][What is timline?]  ← typo
                                   ↑

System: Did you mean [Q][What is timeline?] (similarity: 0.95)
```

---

## User TUI Design

### Core Philosophy

**The TUI is the user's interface to the graph - their to-do list and workflow UI.**

### Main Screen

```
╔══════════════════════════════════════════════════════════════╗
║  Axion - Forestry Assistant Design                           ║
╠══════════════════════════════════════════════════════════════╣
║                                                               ║
║  Progress: ████████░░░░░░░░░░  8/15 questions answered (53%) ║
║                                                               ║
║  📊 PENDING QUESTIONS (7)                                     ║
║                                                               ║
║  🔥 [Q1] What is your deployment timeline? (HIGH PRIORITY)   ║
║      Specialists recommend: "4 weeks" [👍 4 👎 0]             ║
║      → [View details] [Answer now]                            ║
║                                                               ║
║  🔥 [Q2] Who are the primary users? (HIGH PRIORITY)          ║
║      Specialists recommend: "Dispatchers" [👍 5 👎 0]         ║
║      → [View details] [Answer now]                            ║
║                                                               ║
║  ⚠️  [Q3] Does vendor DB contain PII? (CRITICAL)              ║
║      Ethicist flagged: "Required for compliance"             ║
║      → [View details] [Answer now]                            ║
║                                                               ║
║  📋 [Q4] What MVP features do you need? (NORMAL)             ║
║      Specialists recommend: Auth + CRUD [👍 4 👎 0]           ║
║      → [View details] [Answer now]                            ║
║                                                               ║
║  ... (3 more)                                                 ║
║                                                               ║
║  ✓ DECISIONS MADE (8)                                        ║
║                                                               ║
║  [D1] Autonomy Policy: Advisory-only                         ║
║       → [View provenance] [Revisit] [Expand]                 ║
║                                                               ║
║  [D2] Retrieval Method: RAG with hybrid search               ║
║       → [View provenance] [Revisit] [Expand]                 ║
║                                                               ║
║  ... (6 more)                                                 ║
║                                                               ║
║  [Answer next question] [View graph] [Export] [Help]         ║
║                                                               ║
╚══════════════════════════════════════════════════════════════╝
```

### Question Detail View

```
╔══════════════════════════════════════════════════════════════╗
║  [Q1] What is your deployment timeline?                      ║
╠══════════════════════════════════════════════════════════════╣
║                                                               ║
║  Selection mode: SINGLE (pick one)                           ║
║  Priority: HIGH                                               ║
║  Asked by: Context specialist (Phase 1)                      ║
║                                                               ║
║  WHY THIS MATTERS:                                            ║
║  Specialists flagged this as the most critical decision      ║
║  affecting architecture, UX, and safety controls.            ║
║                                                               ║
║  AVAILABLE OPTIONS:                                           ║
║                                                               ║
║  ( ) [A1] Timeline: 4 weeks [👍 4 👎 0] ⭐ RECOMMENDED         ║
║      "Aggressive but achievable with reduced scope"          ║
║                                                               ║
║      Supporters:                                              ║
║        • Engineer: "Achievable with MVP focus"               ║
║        • Research: "Fast iteration validates approach"       ║
║        • Context: "Aligns with agile best practices"         ║
║        • Skeptic: "Risk acceptable with clear scope limits"  ║
║                                                               ║
║      ⚠️  Selecting this will unlock:                          ║
║        → [Q5] What features fit in 4 weeks?                  ║
║        → [Q6] What can we defer?                             ║
║                                                               ║
║  ( ) [A2] Timeline: 3 months [👍 1 👎 0]                      ║
║      "More realistic for production-ready system"            ║
║                                                               ║
║      Supporters:                                              ║
║        • Ethicist: "More time for proper consent framework"  ║
║                                                               ║
║      ⚠️  Selecting this will unlock:                          ║
║        → [Q7] What phased rollout approach?                  ║
║                                                               ║
║  ( ) [A3] Timeline: 6 months [👍 0 👎 2] 🔒 DISCOURAGED       ║
║      "Too long for MVP iteration"                            ║
║                                                               ║
║      Critics:                                                 ║
║        • Skeptic: "Delays validation, increases risk"        ║
║        • Research: "MVP should be faster to test hypothesis" ║
║                                                               ║
║      ⚠️  Selecting this will LOCK all other timelines         ║
║          and 8 dependent questions.                          ║
║                                                               ║
║  [ ] Custom answer: _______________________                  ║
║                                                               ║
║  [Confirm selection] [Back] [View graph] [Ask specialists]   ║
║                                                               ║
╚══════════════════════════════════════════════════════════════╝
```

### Override Warning

```
╔══════════════════════════════════════════════════════════════╗
║  ⚠️  OVERRIDE CONSENSUS WARNING                               ║
╠══════════════════════════════════════════════════════════════╣
║                                                               ║
║  You selected: [A3] Timeline: 6 months                       ║
║                                                               ║
║  4 specialists recommended: [A1] Timeline: 4 weeks           ║
║                                                               ║
║  IMPACT OF YOUR CHOICE:                                      ║
║  • Overrides unanimous specialist recommendation             ║
║  • Will lock 2 alternative timeline paths                    ║
║  • Will close 8 dependent questions                          ║
║  • All future specialist recommendations will adapt          ║
║                                                               ║
║  SPECIALIST CONCERNS:                                        ║
║  • Skeptic: "Delays validation, increases risk"              ║
║  • Research: "6 months too long to test hypothesis"          ║
║                                                               ║
║  YOUR DECISION IS FINAL - specialists cannot override you.   ║
║                                                               ║
║  Are you sure?                                                ║
║                                                               ║
║  [Yes, I'm sure] [Cancel, go back] [Ask for clarification]   ║
║                                                               ║
╚══════════════════════════════════════════════════════════════╝
```

### Auto-Pruning Confirmation

```
╔══════════════════════════════════════════════════════════════╗
║  ✓ Answer recorded                                            ║
╠══════════════════════════════════════════════════════════════╣
║                                                               ║
║  You selected: [A1] Timeline: 4 weeks                        ║
║                                                               ║
║  AUTOMATIC CHANGES:                                          ║
║  ✓ Question [Q1] marked as answered                          ║
║  ✓ Answer [A1] locked in as selected                         ║
║  🔒 Answer [A2] "3 months" closed (not selected)             ║
║  🔒 Answer [A3] "6 months" closed (not selected)             ║
║  🔒 2 dependent questions under [A2] locked                  ║
║  🔒 1 dependent question under [A3] locked                   ║
║  🔓 2 dependent questions under [A1] opened                  ║
║                                                               ║
║  NEXT QUESTIONS UNLOCKED:                                    ║
║  → [Q5] What features fit in 4 weeks?                        ║
║  → [Q6] What can we defer?                                   ║
║                                                               ║
║  Progress: 9/15 answered (60%)                               ║
║                                                               ║
║  [Answer next question] [Back to overview] [View graph]      ║
║                                                               ║
╚══════════════════════════════════════════════════════════════╝
```

---

## Real-World Example: Checkpoint Analysis

### Context

Analyzed `.axion_checkpoint.json` - a real conversation where specialists designed a forestry logistics AI assistant.

**Key insight**: The conversation was BUILDING a semantic vector space, not just discussing ideas.

### Identified Semantic Vectors

#### Vector 1: Autonomy Level

```
[Q][Autonomy: autonomous or advisory?]
  [A1][Fully autonomous] 
        Status: Not selected (implied downvotes)
  [A2][Advisory-only with human approval] ⭐
        Upvoters: Context, Research, Engineer, Skeptic, Ethicist (unanimous)
        Embedding: safety_policy, risk_tolerance, human_oversight
        Status: STRONG CONSENSUS, awaiting user confirmation
  [A3][Hybrid: low-risk auto, high-risk approval]
        Upvoters: Context, Research
        Status: Moderate support, alternative option

Insight: This vector defines the entire safety architecture.
```

#### Vector 2: Primary Users

```
[Q][Who are primary users?]
  [A1][Dispatchers/planners] ⭐
        Upvoters: Context, Research, Engineer, Ethicist, User Comm (5)
        Embedding: user_persona, permissions, workflow_context
  [A2][Procurement]
        Upvoters: Context, User Comm
  [A3][Managers/approvers]
        Upvoters: Context, User Comm
  [A4][Field crews]
        Upvoters: Research
  [A5][Vendors (future)]
        Upvoters: Ethicist
        
Selection mode: MULTI (user can select multiple)
Status: Needs user multi-select

Insight: This vector scopes ALL UX and permission design.
```

#### Vector 3: Data Sensitivity

```
[Q][Does vendor DB contain PII/contracts?]
  [A][Assumption: Yes - contains PII/contracts] ⭐
        Upvoters: Context, Research, Ethicist (implied)
        Embedding: privacy_requirements, ethical_controls, compliance
        Status: Strong assumption, needs user confirmation
        
Insight: This vector triggers entire ethical/legal control framework.
```

#### Vector 4: Deployment Scope

```
[Q][Internal-only or external access?]
  [A1][Internal staff only (MVP)] ⭐
        Upvoters: Context, Research, Engineer, Skeptic, Ethicist, User Comm (6)
        Embedding: security_boundary, access_control, trust_model
        Status: UNANIMOUS CONSENSUS
  [A2][External vendors/customers]
        Status: Future consideration, not for MVP
        
Insight: This vector defines entire security perimeter.
```

#### Vector 5: Retrieval Strategy

```
[Q][How should system retrieve information?]
  [A][Hybrid: RAG with vector + sparse search + structured DB queries] ⭐
        Upvoters: Research, Engineer (explicit), Context (implicit)
        Embedding: technical_approach, accuracy_method, provenance
        Status: STRONG TECHNICAL CONSENSUS
        
Insight: This vector specifies core AI architecture.
```

#### Vector 6: Safety Gates

```
[Q][What safety controls are required?]
  [A][Operational Safety Gate: freshness, constraints, verification, approval] ⭐
        Upvoters: Skeptic, Research, Context, Engineer (4)
        Embedding: risk_mitigation, validation_rules, approval_workflow
        Status: STRONG CONSENSUS
        
Components:
  - Data freshness & provenance
  - Constraint/conflict checks
  - Live vendor verification
  - Approval + rollback
  
Insight: This vector defines operational risk controls.
```

#### Vector 7: Ethical Controls

```
[Q][What ethical safeguards are needed?]
  [A][Vendor consent, PII masking, transparency, appeals process] ⭐
        Upvoters: Ethicist, Research, Context (3)
        Embedding: ethical_framework, fairness, accountability
        Status: STRONG CONSENSUS
        
Components:
  - Default PII masking
  - Visible provenance
  - Vendor consent/appeals
  - Transparency in ranking
  
Insight: This vector defines ethical framework.
```

#### Vector 8: Provenance Requirements

```
[Q][How should system show its reasoning?]
  [A][Source citations + timestamps + confidence scores + verbatim evidence] ⭐
        Upvoters: Research, Skeptic, Context, Engineer (4)
        Embedding: transparency, auditability, trust
        Status: STRONG CONSENSUS
        
Insight: This vector ensures explainability.
```

### Pending User Vectors

**Questions awaiting user input:**

```
[Q][Specific permission mappings?]
  Bracket: [Q][Permission mappings?][A][?]
  Status: Pending user clarification
  
[Q][Vendor DB schema details?]
  Bracket: [Q][Vendor DB schema?][A][?]
  Status: Pending user confirmation
  
[Q][Are documents indexed?]
  Bracket: [Q][Documents indexed?][A][?]
  Status: Pending infrastructure readiness check
  
[Q][Vendor contracts permit AI use?]
  Bracket: [Q][Vendor contracts permit AI?][A][?]
  Status: Pending legal clearance
```

### Current Semantic Space

**High-confidence vectors (~60% complete):**

```
Semantic model built by specialists:
  - autonomy_policy = "advisory-only with mandatory human approval"
  - retrieval_method = "RAG with hybrid search + structured DB"
  - safety_gate = "operational gate with freshness + verification"
  - ethical_controls = "PII masking + vendor consent + transparency"
  - deployment_scope = "internal-only (MVP)"
  - primary_users = "dispatchers, planners, procurement, managers"
  - provenance = "source citations + timestamps + confidence"
  - audit_trail = "immutable logs of all interactions"
  
Pending user vectors (~40% remaining):
  - permission_mappings = ?
  - vendor_db_schema = ?
  - vendor_db_has_pii = ? (needs confirmation)
  - documents_indexed = ?
  - legal_clearance = ?
```

### Key Insights from Analysis

1. **Specialists built 60% of the semantic space autonomously**
   - Strong consensus on core architecture
   - Unanimous on safety/ethical requirements
   - Clear technical direction

2. **Remaining 40% requires user input**
   - Organizational details (permissions, roles)
   - Infrastructure readiness
   - Legal/contractual constraints

3. **The graph would guide user efficiently**
   - 7 high-confidence questions with clear recommendations
   - Each answer unlocks dependent questions
   - User can complete in ~15 minutes with confidence

4. **Vector collection = Complete system spec**
   - Final graph literally defines the assistant
   - Can export as structured requirements doc
   - Can use as LLM system context
   - Serves as audit trail

---

## Implementation Guide

### Phase 1: Core Graph Operations

**File**: `axion_swarm/graph_tool.py`

1. **Implement QuestionGraph class**
   - Neo4j connection management
   - Node creation (Question, Answer, Decision)
   - Relationship management
   - State computation

2. **Implement bracket parser**
   - `detect_graph_requests()` - Extract @[Graph] mentions
   - `parse_bracket_path()` - Parse nested bracket structure
   - Progressive validation with discovery feedback

3. **Implement operations**
   - `create_question_node()`
   - `create_answer_node()`
   - `vote_on_node()` with vote tracking
   - `user_select_answer()` with auto-pruning
   - `collapse_path()` for decision creation
   - `list_nodes()` with filtering

4. **Implement vector embeddings**
   ```python
   from sentence_transformers import SentenceTransformer
   model = SentenceTransformer('all-MiniLM-L6-v2')
   
   def embed_qa_pair(question_text, answer_text):
       text = f"Question: {question_text}\nAnswer: {answer_text}"
       return model.encode(text)
   ```

5. **Implement semantic search**
   ```python
   def find_similar_vectors(query, threshold=0.7):
       query_vec = model.encode(query)
       # Neo4j vector similarity search
       return graph.run("""
           MATCH (a:Answer)
           WHERE a.state = 'selected'
           WITH a, gds.similarity.cosine(a.embedding, $vec) AS sim
           WHERE sim > $threshold
           RETURN a ORDER BY sim DESC
       """, vec=query_vec, threshold=threshold)
   ```

### Phase 2: Agent Integration

**File**: `axion_swarm/agents.py`

1. **Import graph_tool functions**
2. **Detect @[Graph] in specialist messages**
3. **Process operations before Chair executes**
4. **Inject tool results as AIMessages**

### Phase 3: Prompt Documentation

**File**: `axion_swarm/prompts.py`

Add to BASE_INSTRUCTION:

```python
BASE_INSTRUCTION += """

## @[Graph] Tool - Collaborative Vector Building

You have access to @[Graph] for building a semantic knowledge base.

**Core concept**: Each Q->A pair is a semantic vector. The final selected 
pairs become the embedded knowledge base (the OUTPUT).

**Syntax** (pure bracket notation):
  @[Graph][Update][Q][question text]
  @[Graph][Update][Q][question text][A][answer text]
  @[Graph][Update][Q][...][A][...][vote:relevant][comment:why]
  @[Graph][List][pending]
  @[Graph][Because][Q][...][A][...] (for citing in reasoning)

**Question types**:
  - single: User picks ONE, others auto-lock
  - multi: User picks MULTIPLE, explicit completion
  - open: User adds unlimited custom answers

**Voting**:
  - relevant: This vector should be in semantic space
  - not_applicable: This vector should be removed
  - Always include [comment:your reasoning]

**State**: Automatic open/closed based on vote balance.
  - 2+ downvotes AND downvotes > upvotes → closed
  - Otherwise → open

**User authority**: User selections override ALL specialist consensus.

Use @[Graph] to build the semantic space collaboratively.
"""
```

### Phase 4: User TUI

**File**: `axion_swarm/tui.py` (new)

Use `textual` framework:

```python
from textual.app import App, ComposeResult
from textual.widgets import Header, Footer, Static, Button, RadioSet

class AxionGraphTUI(App):
    """User interface for answering graph questions."""
    
    def __init__(self, graph: QuestionGraph):
        super().__init__()
        self.graph = graph
    
    def compose(self) -> ComposeResult:
        yield Header()
        yield QuestionList(self.graph)
        yield Footer()
    
    def on_answer_selected(self, event):
        # Handle user selection
        # Auto-prune unselected paths
        # Update progress
        pass
```

### Phase 5: Neo4j Setup

**Script**: `scripts/setup_neo4j.sh`

```bash
#!/bin/bash
# Launch Neo4j with APOC and GDS plugins
docker run -d \
  --name axion-neo4j \
  -p 7474:7474 -p 7687:7687 \
  -e NEO4J_AUTH=neo4j/password \
  -e NEO4J_PLUGINS='["apoc", "graph-data-science"]' \
  neo4j:latest
```

### Phase 6: Vector Export

**Function**: `export_final_vectors()`

```python
def export_final_vectors(graph: QuestionGraph) -> Dict:
    """Export all selected Q->A vectors as system specification."""
    
    selected = graph.run("""
        MATCH (q:Question)-[:HAS_ANSWER]->(a:Answer)
        WHERE a.state = 'selected'
        RETURN q.text AS question, 
               a.text AS answer,
               a.embedding AS vector,
               q.phase AS phase
        ORDER BY phase, q.created_at
    """)
    
    vectors = []
    context_parts = []
    
    for record in selected:
        vectors.append({
            "question": record["question"],
            "answer": record["answer"],
            "vector": record["vector"],
            "phase": record["phase"]
        })
        context_parts.append(f"- {record['question']}: {record['answer']}")
    
    return {
        "vectors": vectors,
        "context": "\n".join(context_parts),
        "count": len(vectors)
    }
```

---

## Multi-Perspective Semantic Space Exploration

**Three ways to understand the same system:**

1. **[The Mathematical Reality](#the-mathematical-reality)** - Embedding spaces, vectors, projections
2. **[The Intuitive Understanding](#the-intuitive-understanding)** - Simple analogies for the concepts
3. **[The Practical Tool](#the-practical-tool-usage)** - How `@[Graph]` enables exploration

Each perspective illuminates the same underlying architecture from different angles.

---

### The Mathematical Reality

**What's actually happening: Collaborative navigation through high-dimensional embedding space.**

> **See also**: [The Intuitive Understanding](#the-intuitive-understanding) for a simpler mental model of these concepts.

#### Each Specialist Has Their Own Embedding Space

```python
# Research specialist's internal LLM
research_space = {
    "RAG": [0.23, -0.15, 0.89, ...],           # 384-dim vector
    "vector_db": [0.34, -0.08, 0.72, ...],
    "hybrid_search": [0.28, -0.12, 0.81, ...]
}

# Skeptic specialist's internal LLM  
skeptic_space = {
    "safety_gate": [0.45, 0.23, -0.34, ...],
    "validation": [0.38, 0.19, -0.28, ...],
    "risk_assessment": [0.41, 0.21, -0.31, ...]
}

# Ethicist specialist's internal LLM
ethicist_space = {
    "consent": [-0.12, 0.56, 0.23, ...],
    "transparency": [-0.08, 0.52, 0.27, ...],
    "fairness": [-0.10, 0.54, 0.25, ...]
}
```

**Each specialist navigates from their unique embedding space.**

> **Intuitive equivalent**: Think of each specialist as a bird with its own flight path and navigation skills. See [The Intuitive Understanding](#the-intuitive-understanding).

#### Specialists Project Into Shared Graph Space

```python
# Research proposes a vector
research_proposal = research_space["RAG"]  # Internal space

# Project into shared graph space
graph_vector = project(research_proposal, 
                      from_space=research_internal,
                      to_space=graph_shared)

# Other specialists validate
for specialist in [skeptic, ethicist, engineer]:
    # Project graph vector into their internal space
    their_view = project(graph_vector,
                        from_space=graph_shared,
                        to_space=specialist.internal)
    
    # Measure coherence in their space
    coherence = specialist.measure_coherence(their_view)
    
    # Vote based on coherence
    if coherence > threshold:
        vote("relevant")  # "Yes, this fits"
    else:
        vote("not_applicable")  # "No, this doesn't fit"
```

**The graph is the intersection of specialist perspectives.**

> **Practical tool**: Specialists use `@[Graph][Update][Q][...][A][...]` to project their proposals. See [The Practical Tool Usage](#the-practical-tool-usage).

#### The User Navigates Semantic Space

```python
# Current graph state = Current position in space
current_vectors = get_selected_vectors()
current_position = np.mean(current_vectors, axis=0)  # Centroid

# User selects answer: "Advisory-only"
user_selection = embed("Advisory-only with mandatory approval")

# This MOVES the collective position
new_position = current_position + α * (user_selection - current_position)

# Specialists now explore NEAR this new position
for specialist in specialists:
    nearby_questions = specialist.search_near(new_position, radius=threshold)
    propose(nearby_questions)
```

**The user is navigating the collective through semantic space.**

> **Intuitive equivalent**: User is the destination setter for the flock. See [Specialist Roles](#specialist-roles-in-semantic-navigation).

#### Specialists Explore the Frontier

```python
# Current selected vectors (known space)
known_space = {V1, V2, V3, ...}
space_centroid = np.mean(list(known_space), axis=0)

# Frontier = vectors near current position but unexplored
for specialist in specialists:
    # Search in specialist's internal space
    candidates = specialist.internal_search(
        query="What's near current position?",
        context=known_space
    )
    
    # Filter to vectors close to centroid
    for candidate in candidates:
        candidate_vec = embed(candidate)
        distance = cosine_distance(candidate_vec, space_centroid)
        
        if distance < frontier_threshold:
            # Close enough = frontier question
            propose_question(candidate)
        else:
            # Too far = tangent, not relevant
            skip(candidate)
```

**Specialists explore the edges of the current vector sum.**

> **Practical tool**: Frontier exploration happens through `@[Graph][List][frontier]` and proximity-based proposals. See [The Practical Tool Usage](#the-practical-tool-usage).

#### Voting is Cross-Validation Across Embedding Spaces

```python
# Research proposes: "Use RAG with hybrid search"
proposal_vec = embed("RAG with hybrid search")

# Engineer validates
engineer_projection = project(proposal_vec, 
                             to_space=engineer.internal)
engineer_similarity = cosine_similarity(
    engineer_projection, 
    engineer.implementation_concepts
)
if engineer_similarity > 0.7:
    engineer.vote("relevant")  # "Makes sense from my view"

# Skeptic validates
skeptic_projection = project(proposal_vec,
                            to_space=skeptic.internal)
skeptic_similarity = cosine_similarity(
    skeptic_projection,
    skeptic.risk_concepts
)
if skeptic_similarity > 0.6:
    skeptic.vote("relevant")  # "I can see safety controls for this"
```

**Voting = "Does this vector project coherently into my embedding space?"**

> **Practical tool**: Voting uses `@[Graph][Update][Q][...][A][...][vote:relevant][comment:...]`. See [Voting & Relevance System](#voting--relevance-system).

---

### The Intuitive Understanding

> **Mathematical basis**: This is a simplified mental model of the embedding space concepts described in [The Mathematical Reality](#the-mathematical-reality).

**Think of it like a flock of birds navigating together:**

- **Each specialist = bird with own trajectory** (their embedding space)
- **Collective graph = flock's shared path** (the graph space)
- **User = destination setter** (guides overall direction)
- **Chair = lead coordinator** (synthesizes, maintains cohesion)
- **Voting = staying together** (alignment, coherence)
- **Proposals = exploring while staying near flock** (frontier search)

**The flock moves through semantic space, and the graph records their flight path.**

> **Mathematical reality**: The "flock" is actually coordinated navigation through 384-dimensional embedding space. See [The Mathematical Reality](#the-mathematical-reality).

> **Practical tool**: The flight path is recorded using `@[Graph]` operations that create Question and Answer nodes. See [The Practical Tool Usage](#the-practical-tool-usage).

### Specialist Roles in Semantic Navigation

#### Core Team (Always Present)

**Core specialists maintain baseline coherence:**

```python
core_team = {
    "Context": {
        "role": "Foundational framing",
        "expertise": ["problem_definition", "assumptions", "scope"],
        "always_active": True
    },
    "Research": {
        "role": "Current knowledge search",
        "expertise": ["best_practices", "recent_approaches", "validation"],
        "always_active": True
    },
    "Skeptic": {
        "role": "Risk identification",
        "expertise": ["failure_modes", "edge_cases", "validation"],
        "always_active": True
    },
    "Ethicist": {
        "role": "Ethical grounding",
        "expertise": ["fairness", "consent", "transparency", "harm_prevention"],
        "always_active": True
    },
    "User Comm": {
        "role": "User interface",
        "expertise": ["question_framing", "clarity", "user_needs"],
        "always_active": True
    }
}
```

**Core team = Baseline multi-perspective intelligence**

#### Available Specialists (Join Temporarily)

**Available specialists provide deep expertise for specific semantic regions:**

```python
available_specialists = {
    "DB Architect": {
        "expertise_region": ["database", "schema", "queries", "optimization"],
        "join_when": lambda pos: in_region(pos, "database"),
        "status": "available"  # Can be "in" when active
    },
    "Backend Engineer": {
        "expertise_region": ["API", "services", "integration", "auth"],
        "join_when": lambda pos: in_region(pos, "backend"),
        "status": "available"
    },
    "Cloud Architect": {
        "expertise_region": ["infrastructure", "deployment", "scaling"],
        "join_when": lambda pos: in_region(pos, "cloud"),
        "status": "available"
    }
}
```

**Specialist joining workflow:**

```python
def manage_specialist_participation(current_position, active_specialists):
    """Bring specialists in/out based on semantic region."""
    
    current_region = identify_region(current_position)
    
    # Who should be active for this region?
    needed = get_specialists_for_region(current_region)
    
    # Invite if not active
    for specialist in needed:
        if specialist.status == "available":
            specialist.status = "in"
            specialist.receive_context(current_graph_state)
            print(f"@[{specialist.name}], join us in {current_region} region")
    
    # Release if no longer needed
    for specialist in active_specialists:
        if specialist not in needed and specialist not in core_team:
            specialist.status = "available"
            print(f"@[{specialist.name}], thank you. Returning to available.")
    
    return active_specialists

# Example flow:
# Position moves to [database region]
#   → Invite DB Architect
#   → DB Architect steers flock through database territory
#   → Database decisions made
# Position moves to [API region]  
#   → Release DB Architect
#   → Invite Backend Engineer
#   → Backend Engineer steers through API territory
```

**Dynamic composition: Right expert at right time**

#### Chair's Coordination Role

**Chair maintains collective coherence:**

```python
class ChairCoordinator:
    """Maintains flock coherence and synthesizes progress."""
    
    def find_centroid(self, specialist_proposals):
        """Where is the collective positioned?"""
        all_vectors = []
        for specialist, vectors in specialist_proposals.items():
            all_vectors.extend(vectors)
        
        centroid = np.mean(all_vectors, axis=0)
        coherence = measure_spread(all_vectors, centroid)
        
        return {
            "position": centroid,
            "coherence": coherence,
            "region": identify_region(centroid)
        }
    
    def set_direction(self, current_centroid, user_selection):
        """Guide collective toward user's goal."""
        direction = user_selection - current_centroid
        
        return {
            "from_region": identify_region(current_centroid),
            "to_region": identify_region(user_selection),
            "guidance": f"Explore near {identify_region(user_selection)}"
        }
    
    def consolidate_path(self, linear_vectors):
        """Compress sequential vectors into decision."""
        decision_vector = embed_decision(linear_vectors)
        decision_label = generate_summary(linear_vectors)
        
        # Validate summary matches vectors
        similarity = cosine_similarity(decision_vector, 
                                      np.mean(linear_vectors, axis=0))
        
        if similarity > 0.85:
            return create_decision(decision_vector, decision_label)
        else:
            # Refine summary
            return refine_summary(linear_vectors, decision_label)
    
    def detect_fragmentation(self, specialist_proposals):
        """Are specialists diverging?"""
        centroids = {s: np.mean(vecs, axis=0) 
                    for s, vecs in specialist_proposals.items()}
        
        max_distance = max(cosine_distance(c1, c2) 
                          for c1, c2 in combinations(centroids.values(), 2))
        
        if max_distance > fragmentation_threshold:
            return "FRAGMENTATION RISK: Specialists diverging"
        else:
            return "COHERENT: Specialists aligned"
```

**Chair = Cohesion coordinator, not domain expert**

> **Mathematical reality**: Chair computes centroids, measures coherence, and compresses vectors. See [The Mathematical Reality](#the-mathematical-reality).

> **Practical tool**: Chair uses `@[Graph][Collapse]` to consolidate paths. See [Decision Collapse & Preservation](#decision-collapse--preservation).

### The Complete Multi-Agent Semantic Process

**Phase-by-phase:**

```
Phase 1: Initial Exploration
─────────────────────────────
Active: Core team (5 specialists)
Position: Origin → [autonomy, users, deployment]
Method: Each specialist explores independently from origin
Result: 10 foundational vectors proposed
        Voting establishes consensus on 6 vectors
        User hasn't selected yet (exploration phase)

Phase 2: Convergence
─────────────────────────────
Active: Core team + DB Architect (6 specialists)
Position: [autonomy, users] → [database, schema, queries]
Method: DB Architect joins (entered database semantic region)
        DB Architect steers toward optimal database vectors
        Core validates from their perspectives
Result: Database architecture vectors added
        Decision [D1] "Database Architecture" created
        DB Architect departs (exits database region)

Phase 3: Integration
─────────────────────────────
Active: Core team (5 specialists)  
Position: [integrated_architecture] → frontier
Method: Core synthesizes across all specialist contributions
        User selects final vectors
        Chair consolidates into decisions
Result: Complete multi-perspective specification
        17 vectors total (10 from Phase 1-2, 7 from user input)
        5 decisions (compressed from 17 vectors)
        Final output ready
```

### Final Output: Multi-Resolution Vector Space

```python
final_output = {
    "selected_qa_vectors": [
        {"id": "[Q1][A1]", "embedding": [...], "context_depth": 0},
        {"id": "[Q2][A2]", "embedding": [...], "context_depth": 1},
        {"id": "[Q3][A3]", "embedding": [...], "context_depth": 2},
        # ... 17 total
    ],
    
    "decisions": [
        {
            "id": "D1",
            "title": "Autonomy and Approval Policy",
            "embedding": [...],  # Compressed from 3 Q→A vectors
            "original_path": "[Q1][A1][Q2][A2][Q3][A3]"
        },
        # ... 5 total
    ],
    
    "semantic_properties": {
        "total_vectors": 17,
        "compression_ratio": 3.4,  # 17 vectors → 5 decisions
        "context_depth_range": [0, 4],
        "multi_perspective": ["technical", "safety", "ethical", "practical"],
        "cross_validated": True,
        "user_curated": True
    }
}
```

**This is:**
- Multi-perspective (5+ specialist views)
- Cross-validated (voting across embedding spaces)
- User-curated (ground truth validation)
- Context-aware (hierarchical embeddings)
- Compressed (decisions reduce cognitive load)
- Auditable (full provenance preserved)

**The graph is collaborative semantic space exploration with emergent collective intelligence.**

> **See also**: [The Practical Tool Usage](#the-practical-tool-usage) for how specialists actually interact with this system.

---

### The Practical Tool Usage

**How specialists use `@[Graph]` to navigate semantic space:**

> **Mathematical basis**: Each `@[Graph]` operation manipulates vectors in embedding space. See [The Mathematical Reality](#the-mathematical-reality).

> **Intuitive model**: Think of `@[Graph]` operations as how the flock communicates and coordinates. See [The Intuitive Understanding](#the-intuitive-understanding).

#### 1. Proposing Vectors (Creating Q→A Pairs)

**Specialist proposes a question:**

```
Context specialist:
  @[Graph][Update][Q][What is your deployment timeline?]
```

**What this does mathematically:**
- Creates Question node in graph
- Establishes position for future Answer vectors to branch from
- Sets up context accumulation point

**Intuitive model**: Bird proposes a direction to explore.

**Specialist proposes answer vectors:**

```
Context specialist:
  @[Graph][Update][Q][What is your deployment timeline?][A][Timeline: 4 weeks]
  
Research specialist:
  @[Graph][Update][Q][What is your deployment timeline?][A][Timeline: 3 months]
```

**What this does mathematically:**
- Embeds each Q→A pair as single vector: `embed("Q: deployment timeline?\nA: 4 weeks")`
- Stores in Answer node with 384-dimensional embedding
- These are candidate vectors for the semantic space

**Intuitive model**: Birds propose different flight paths from current position.

> **See**: [Each Q->A Pair is a Single Vector Embedding](#each-q-a-pair-is-a-single-vector-embedding) for embedding details.

#### 2. Validating Vectors (Voting)

**Specialist validates proposed vector:**

```
Engineer specialist:
  @[Graph][Update][Q][What is your deployment timeline?][A][Timeline: 4 weeks][vote:relevant][comment:Aggressive but achievable with reduced scope]
```

**What this does mathematically:**
- Projects proposal vector into Engineer's internal embedding space
- Measures coherence: `cosine_similarity(proposal_vec, engineer_space) > threshold`
- Upvote if coherent, downvote if not
- Tracks individual voters for cross-validation

**Intuitive model**: Bird checks if proposed path makes sense from their perspective, votes to stay together.

> **See**: [Voting is Cross-Validation Across Embedding Spaces](#voting-is-cross-validation-across-embedding-spaces).

#### 3. Navigating Space (User Selection)

**User selects answer:**

```
User (via TUI):
  Selects: [A1] "Timeline: 4 weeks"
```

**What this does mathematically:**
- Adds V1 = `embed("Timeline: 4 weeks")` to selected vectors
- Updates centroid: `new_centroid = mean([existing_vectors, V1])`
- Moves collective position in semantic space
- All future proposals must be near new centroid (proximity search)

**Intuitive model**: Lead bird (user) sets direction, flock follows.

> **See**: [The User Navigates Semantic Space](#the-user-navigates-semantic-space).

#### 4. Exploring Frontier (Proposing Next Questions)

**Specialist proposes next question:**

```
Engineer specialist:
  @[Graph][Update][Q][Timeline: 4 weeks][A][Timeline: 4 weeks][Q][What features fit in 4 weeks?]
```

**What this does mathematically:**
- Context-aware embedding: includes parent `[Q1][A1]` in context
- New question vector near current centroid
- Frontier exploration: `distance(new_q_vec, centroid) < threshold`
- Creates branching path in graph

**Intuitive model**: Bird explores near current position while staying with flock.

> **See**: [Graph Hierarchy = Context Accumulation](#graph-hierarchy--context-accumulation).

#### 5. Cross-Perspective Validation (Multi-Specialist Voting)

**Multiple specialists vote on same proposal:**

```
Research: @[Graph][Update][...][vote:relevant][comment:Matches RAG best practices]
Engineer: @[Graph][Update][...][vote:relevant][comment:Implementable with current stack]
Skeptic: @[Graph][Update][...][vote:relevant][comment:Manageable risks with proper controls]
```

**What this does mathematically:**
- Each specialist projects proposal into their unique embedding space
- Cross-validates coherence across multiple perspectives
- Proposal accepted if coherent in multiple spaces simultaneously
- Creates multi-perspective validated vector

**Intuitive model**: Multiple birds agree path is safe from their different vantage points.

> **See**: [Voting & Relevance System](#voting--relevance-system).

#### 6. Dynamic Membership (Specialist Join/Leave)

**Chair invites specialist:**

```
Chair: @[DB Architect], we're entering database territory. 
       Join us to guide through vendor data schema decisions.
       
       Current position: [advisory, dispatchers, PII]
```

**What this does mathematically:**
- Detects region change: `identify_region(current_centroid) = "database"`
- Invites specialist with relevant expertise: `DB_Architect.expertise_region.overlap("database") > threshold`
- DB Architect receives current graph state (all vectors)
- DB Architect proposes vectors near current position
- Temporarily steers flock direction with database expertise

**Intuitive model**: Expert guide joins flock for specific leg of journey.

> **See**: [Available Specialists (Join Temporarily)](#available-specialists-join-temporarily).

#### 7. Consolidating Progress (Decision Collapse)

**Chair collapses linear path:**

```
Chair:
  @[Graph][Collapse][Q1][A1][Q2][A2][Q3][A3][title:Autonomy and Approval Policy]
```

**What this does mathematically:**
- Compresses 3 Q→A vectors into 1 Decision vector
- Decision embedding: `embed(summary + description + all_qa_pairs)`
- Validation: `cosine_similarity(decision_vec, mean([V1,V2,V3])) > 0.85`
- Creates compressed representation preserving 90% semantic content
- Archives original vectors but preserves provenance

**Intuitive model**: Flock consolidates their traveled path into a milestone.

> **See**: [Decisions = Compressed Vectors with English Labels](#decisions--compressed-vectors-with-english-labels).

#### 8. Querying State (Frontier Detection)

**Specialist checks frontier:**

```
Research specialist:
  @[Graph][List][frontier]
```

**What this does mathematically:**
- Finds open leaf nodes: nodes with no children and state="open"
- Returns questions near current centroid that need exploration
- Sorts by distance from centroid (closest = most relevant)
- Provides specialists with next areas to explore

**Intuitive model**: Birds check which unexplored areas are nearest to flock.

> **See**: [Specialists Explore the Frontier](#specialists-explore-the-frontier).

#### 9. Referencing Context (Because Operation)

**Specialist cites graph path:**

```
Skeptic:
  Given @[Graph][Because][Q][What is autonomy?][A][Advisory-only], 
  we need strong validation controls...
```

**What this does mathematically:**
- Retrieves vector from graph: `get_embedding("[Q1][A1]")`
- Includes in specialist's reasoning context
- No state change, pure reference operation
- Maintains semantic coherence in discussion

**Intuitive model**: Bird references earlier part of flight path in current decision.

> **See**: [Bracket Syntax Specification](#bracket-syntax-specification).

### The Complete Tool Workflow

**Putting it all together:**

```
Phase 1: Core Exploration
──────────────────────────
Context: @[Graph][Update][Q][What is autonomy level?]
Research: @[Graph][Update][Q][What is autonomy level?][A][Advisory-only]
Skeptic: @[Graph][Update][Q][...][A][Advisory-only][vote:relevant][comment:Reduces risk]
User: Selects [A1] "Advisory-only"

Result: V1 added to semantic space, centroid updated

Phase 2: Contextual Expansion
──────────────────────────────
Engineer: @[Graph][Update][Q][...][A][Advisory-only][Q][Who approves actions?]
Context: @[Graph][Update][Q][Who approves actions?][A][Managers with authorization]
Research: @[Graph][Update][Q][...][A][...][vote:relevant][comment:Standard practice]
User: Selects [A1] "Managers"

Result: V2 added (with V1 context), centroid updated, space refined

Phase 3: Specialist Territory
──────────────────────────────
Chair: @[DB Architect], join us in database region
DB Architect: @[Graph][Update][Q][What is database schema?]
DB Architect: @[Graph][Update][Q][What is database schema?][A][Normalized relational]
Engineer: @[Graph][Update][Q][...][A][...][vote:relevant][comment:Works with our stack]
User: Selects [A1] "Normalized relational"

Result: V3 added (specialist-guided), DB territory mapped

Phase 4: Consolidation
──────────────────────────────
Chair: @[Graph][Collapse][Q1][A1][Q2][A2][Q3][A3][title:Architecture Foundation]

Result: D1 decision created (compressed V1+V2+V3), provenance preserved
```

**Each operation manipulates vectors in semantic space while maintaining human-readable representation.**

> **Mathematical view**: See [The Complete Multi-Agent Semantic Process](#the-complete-multi-agent-semantic-process) for vector-level details.

> **Intuitive view**: See [Specialist Roles in Semantic Navigation](#specialist-roles-in-semantic-navigation) for coordination model.

### Tool Design Principles

**Why this syntax and workflow enables semantic exploration:**

1. **Hierarchical bracket notation preserves context:**
   - `[Q1][A1][Q2][A2]` embeds full path in ID
   - Context accumulates naturally
   - No specialist needs to track parent IDs manually

2. **Voting integrates multi-perspective validation:**
   - Each specialist validates from their embedding space
   - Cross-validation emerges naturally
   - No central authority needed

3. **Progressive validation provides guidance:**
   - Invalid paths return available options
   - Turns errors into discovery
   - Specialists learn the space by exploring

4. **Decision collapse reduces cognitive load:**
   - Compresses vectors without losing information
   - User sees clean decisions, not raw vectors
   - Audit trail preserved for provenance

5. **Dynamic membership optimizes intelligence:**
   - Right expert at right time
   - Efficient resource usage
   - Maintains coherence across transitions

**The tool is designed to make collaborative semantic space exploration feel natural and intuitive.**

---

## Integration with Axion Swarm

### How @[Graph] Fits Core Architecture

**Axion's core differentiators:**
1. Autonomous multi-agent collaboration ✓
2. Real-time search and verification ✓
3. Explicit assumption-stating ✓
4. Risk-first orientation ✓
5. Ethical framework grounding ✓
6. Triage before solving ✓
7. No premature consensus ✓
8. Candid internal discussion ✓

**@[Graph] enhances ALL of these:**

1. **Autonomous collaboration** → Specialists build graph independently
2. **Real-time search** → Enriches Q->A vectors with current data
3. **Explicit assumptions** → Questions capture assumptions, answers lock them in
4. **Risk-first** → Safety-critical questions flagged with HIGH priority
5. **Ethical grounding** → Ethical questions explicitly in graph
6. **Triage** → Question voting IS triage (relevant vs not_applicable)
7. **No premature consensus** → Multiple answer branches explored
8. **Candid discussion** → Vote comments capture honest specialist views

### Graph as Axion's Memory

**Traditional Axion**: Specialists discuss in messages, Chair synthesizes

**Graph-enhanced Axion**: Specialists discuss AND build semantic graph simultaneously

```
Phase 1:
  Specialists propose questions/answers
  Vote on relevance
  Graph captures semantic space being explored
  
Phase 2:
  Specialists refine based on votes
  Add dependent questions
  Vote changes reopen/close paths
  Graph evolves
  
Phase N:
  Chair collapses consensus chains
  User sees clean decision list
  Graph = Complete embedded knowledge
```

### Why This Is Powerful for Axion

1. **Structured async collaboration**
   - Graph persists across sessions
   - User can answer questions days later
   - Specialists continue exploring open frontiers

2. **Explicit knowledge capture**
   - Every decision has provenance
   - Assumptions explicit in Q->A pairs
   - Audit trail built-in

3. **User-centric output**
   - User sees progress (X/Y questions answered)
   - Clear next actions (pending questions)
   - Confidence in recommendations (vote counts)

4. **Reusable semantic space**
   - Final vectors = System specification
   - Can be used as LLM context for future queries
   - Can be exported as requirements doc

5. **Visual understanding**
   - Neo4j visualization shows semantic structure
   - Users see branching discussions
   - Clear view of consensus vs divergence

---

## Conclusion

The `@[Graph]` tool transforms Axion from a discussion system into a **collaborative semantic embedding builder**.

**Key insights:**
- Each Q→A pair is a semantic vector
- Open paths define the scoped vector space
- Final selected pairs = Embedded knowledge base
- User has absolute authority over the space
- Graph IS the output, not a planning artifact

**This makes Axion uniquely powerful for:**
- Complex decision-making with provenance
- Async collaboration across timezones
- Structured knowledge capture
- Explainable AI system design
- User-driven semantic space construction

The graph tool is the natural evolution of Axion's multi-agent architecture, making implicit knowledge explicit and ephemeral discussions permanent.

---

## Related Documentation

**Essential Reading**:
- `EXECUTIVE_SUMMARY.md` - Quick overview with bullet points (468 lines)
- `GRAPH_TOOL_PAPER.md` - Formal scientific paper with proofs (548 lines)
- `GRAPH_ARCHITECTURE.md` - This document (2,400+ lines)

**Examples & Validation**:
- `GRAPH_DEMO_FROM_CHECKPOINT.md` - Real conversation mapped to graph (896 lines)
- `GRAPH_PROVENANCE_ANALYSIS.md` - Detailed provenance walkthrough (1,852 lines)

**Quick Reference**:
- `GRAPH_TOOL_SUMMARY.md` - One-page cheat sheet (100 lines)

**Supporting Documents**:
- `NEO4J_SETUP.md` - Database setup instructions
- `COMPOSITE_KEY_DESIGN.md` - Composite path design rationale

**Total Documentation**: ~6,300 lines across 8 documents

---

*For implementation, start with Section 13 (Implementation Guide) in this document.*

