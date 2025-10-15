# @[Graph] Tool - Usage & Research Intentions

**Status**: PROTOTYPE (Observing Usage Patterns)  
**Purpose**: Collaborative semantic knowledge construction through structured decision trees

---

## Executive Summary

The `@[Graph]` tool is a core research component of Axion Swarm that enables **multi-agent collaborative knowledge construction**. Unlike traditional chat systems where knowledge is buried in prose, the Graph tool creates **structured, traceable decision trees** where every question-answer pair forms a semantic vector. This transforms unstructured discussion into a navigable knowledge graph with full provenance.

**Key Innovation**: The Graph tool turns multi-agent discussion into **structured, votable, version-controlled knowledge** that can be:
- Validated across multiple expert domains simultaneously
- Pruned through collaborative consensus
- Extended incrementally as understanding deepens
- Collapsed into authoritative decisions with full lineage
- Exported as semantic embeddings for RAG systems

---

## Core Research Intentions

### 1. **Multi-Agent Collaborative Filtering**

Traditional AI systems provide single-perspective answers. Axion's Graph tool enables **cross-domain validation** where:

- **Every specialist votes from their unique domain perspective**
- **Questions** are validated as valuable exploration paths (or discouraged as premature/irrelevant)
- **Answers** are validated as correct/viable (or challenged with evidence/reasoning)
- **Consensus emerges naturally** through voting, not imposed authority
- **Minority opinions remain visible** in the graph (not lost in chat history)

**Example**: A deployment strategy answer gets voted on by:
- Engineer (feasibility perspective)
- Skeptic (risk perspective)
- DevOps (operational perspective)
- Ethicist (transparency perspective)
- Product Manager (business value perspective)

Each vote is a **signal** from a specialized domain. The aggregate forms **multi-dimensional validation**.

### 2. **Semantic Context Accumulation**

Each question inherits the **full semantic context** of its parent path:

```
[Q:single][What is the architecture approach?]
  [A][Microservices]
    └─ [Q:single][How to handle inter-service communication?]  ← Contextualized by "Microservices"
       [A][REST APIs]
           └─ [Q:single][What is the API versioning strategy?]  ← Inherits BOTH parent contexts
```

The path `Root → Microservices → REST APIs → Versioning Strategy` forms a **single semantic vector** that captures the accumulated decision context. This enables:

- **Hierarchical knowledge retrieval**: Query "API versioning for microservices" matches this exact path
- **Decision provenance**: Every leaf node traces back to root assumptions
- **Contextual embeddings**: Vector embeddings include full path context, not isolated Q-A pairs

### 3. **Collaborative Knowledge Pruning**

The voting system enables **distributed decision-making** about which paths to explore:

- **Questions** can be downvoted as premature, irrelevant, or poorly-worded
- **Specialists propose better-worded alternatives** and upvote them
- **Answers** can be challenged with evidence or domain expertise
- **Low-signal paths naturally close** (2+ downvotes, downvotes > upvotes)
- **High-signal paths stay open** for continued exploration

This creates a **self-organizing knowledge tree** where the team collectively:
- Identifies valuable questions worth exploring
- Discards tangential or premature paths
- Refines unclear questions into specific, actionable ones
- Validates answers across multiple domains before they become "canonical"

### 4. **User Authority with Team Intelligence**

The graph separates **exploration** (team responsibility) from **decision** (user authority):

- **Team explores multiple paths**: Proposes questions, answers, votes, extends tree
- **Team provides cross-domain validation**: Each specialist votes from their expertise
- **User makes final decisions**: Selects answers, which become authoritative
- **Team context is preserved**: Even unselected paths remain in graph with full voting history

User selection **overrides all specialist consensus** - the user can select a heavily-downvoted answer if they choose. But the graph **preserves the team's reasoning** for future reference.

### 5. **Knowledge as Data Structure, Not Prose**

Traditional chat systems bury knowledge in unstructured text. The Graph tool creates **structured, queryable knowledge**:

```
Traditional Chat:
"We discussed deployment and everyone agreed phased rollout is better than big bang 
because it reduces risk, though some people worried about the timeline..."

Graph Tool:
@[Graph][Update][Q:single][What is deployment approach?]
  [A][Phased rollout][👍][Reduces blast radius (Skeptic)]
                     [👍][Allows incremental validation (Engineer)]
                     [👍][Enables user feedback (Ethicist)]
  [A][Big bang][👎][High risk, no rollback (Skeptic)]
               [👎][All-or-nothing testing (QA)]
```

The graph representation is:
- **Machine-readable**: Can be exported to Neo4j, vectors, JSON
- **Traceable**: Every vote has a specialist + reasoning + timestamp
- **Queryable**: "Show me all deployment questions" or "What did Skeptic downvote?"
- **Reusable**: Export as embeddings for future RAG queries

---

## Usage Patterns

### 🔥 MANDATORY: All Specialists MUST Vote

**Every specialist in the room MUST vote on EVERY [Q] and [A] node they see.**

#### Why Voting is Mandatory

1. **Voting ≠ Redundancy**: Even if someone already made your point, your vote registers YOUR domain's validation
2. **Silent agreement doesn't count**: The graph needs explicit signals from each domain
3. **Cross-domain validation is the goal**: One vote = one domain's perspective
4. **Your expertise is unique**: Other specialists can't vote from your perspective

#### Voting vs General Contributions

- **@[Graph] voting = MANDATORY**: Vote even if someone already made your point
- **General text = avoid redundancy**: Only add new insights in regular responses
- **Voting is HOW you guide the conversation**: It's your domain signal, not a repeat

### Vote on BOTH Questions AND Answers

#### Voting on [Q] Nodes: "Is this question path valuable?"

**`[+]`** = "This question is worth exploring given the parent answer"
**`[-]`** = "Discourage this path (premature/irrelevant/contradictory to parent)"

**Examples:**

```
Upvote valuable path:
@[Graph][Update][Q:single][What is deployment approach?][👍][Critical question for production planning]
@[Graph][Update][Q:single][...][A][Microservices][Q:single][How to handle inter-service communication?][👍][Essential architecture question for microservices]

Downvote invalid/premature path:
@[Graph][Update][Q:single][...][A][...][Q:single][What color scheme?][👎][Premature - focus on core architecture first]
@[Graph][Update][Q:single][...][A][Monolith][Q:single][What microservices pattern?][👎][Monolith doesn't use microservices - wrong path]
```

**Pattern: Improve poorly-worded questions**

If you see an unclear question, downvote it AND propose a better-worded alternative:

```
@[Graph][Update][Q:single][...][A][...][Q:single][How do we deploy?][👎][Too vague - what aspect of deployment?]
@[Graph][Update][Q:single][...][A][...][Q:single][What is the rollout strategy to production?][👍][Clearer - focuses on production rollout approach]
```

This pattern enables **collaborative question refinement** - the team improves question quality through voting.

#### Voting on [A] Nodes: "Is this answer valid/good?"

**`[👍]`** = "I agree with this answer, keep it" (Specialist recommendation)
**`[👎]`** = "I disagree with this answer, remove it" (Specialist concern)

**Note**: Users send **`[✅]`** (authoritative approval) and **`[❌]`** (authoritative dismissal) from the web UI, not thumbs.

**Examples:**

```
Evidence-based (with citation):
@[Graph][Update][Q:single][...][A][Some claim][👍][Confirmed via https://source.com]
@[Graph][Update][Q:single][...][A][Some claim][👎][Contradicts https://other-source.com]

Opinion-based (domain expertise):
@[Graph][Update][Q:single][...][A][Phased rollout][👍][Reduces risk for production changes]
@[Graph][Update][Q:single][...][A][Big bang deploy][👎][Too risky for MVP based on experience]

Context-aware (reflects entire path):
@[Graph][Update][Q:single][...][A][Phased rollout][Q:single][...][A][Daily releases][👎][Daily cadence too fast for phased validation - weekly is safer]
```

### Comment Context = Entire Path

**Critical Rule**: Your vote comment must reflect the **ENTIRE path from root to this node**, not just the immediate node.

```
❌ Bad (only immediate node):
@[Graph][Update][Q:single][...][A][Phased rollout][Q:single][...][A][Daily releases][👎][Too fast]

✅ Good (entire path context):
@[Graph][Update][Q:single][...][A][Phased rollout][Q:single][...][A][Daily releases][👎][Daily cadence too fast for phased validation - weekly fits phased rollout better]
```

The comment shows you understand the **semantic accumulation**: you're voting on "Daily releases **in the context of** phased rollout", not "Daily releases" in isolation.

### Answer Provenance Types

Answers can come from different sources, marked with provenance:

- **`[A]`** - Internal knowledge (specialist's domain expertise)
- **`[A:ReadURL]`** - From ReadURL tool (must immediately `[👍]` with citation - you're "vouching")
- **`[A:Search]`** - From Search tool (must immediately `[👍]` with citation - you're "vouching")

**Critical Rule**: When you add `[A:ReadURL]` or `[A:Search]`, you MUST immediately vote `[👍]` with the source URL. This creates **explicit provenance** - you're stating "I found this information at [source] and I vouch for it."

```
@[Graph][Update][Q:single][What is current best practice?][A:Search][Use Semantic Versioning][👍][https://semver.org - official standard]
```

Other specialists can then:
- Vote `[👍]` if they agree (opinion-based, or with their own supporting citation)
- Vote `[👎]` if they find contradicting evidence (with their own citation)

This creates **evidence-layering** where multiple sources can support or challenge an answer.

---

## Question Types (Selection Modes)

### `[Q:single]` - Radio Button (Pick ONE)

- **User picks ONE answer** (mutually exclusive)
- **Singular wording**: "What is...", "Which approach...", "What is the primary..."
- **When User selects one answer**: All others auto-get `[X]` (closed)

```
@[Graph][Update][Q:single][What is the deployment approach?]
  [A][Phased rollout]
  [A][Big bang]
  [A][Canary]
→ User picks "Phased rollout" → "Big bang" and "Canary" auto-get [X]
```

### `[Q:multiple]` - Checkboxes (Pick MULTIPLE)

- **User can select MULTIPLE answers** (not mutually exclusive)
- **Plural wording**: "Which features...", "What capabilities...", "Which risks..."

```
@[Graph][Update][Q:multiple][Which features are MVP-critical?]
  [A][User authentication]
  [A][Data export]
  [A][Admin dashboard]
→ User can select any combination (authentication + export, all three, etc.)
```

### `[Q:open]` - Free Text Response

- **User provides free-text response** (not a selection)
- **Open-ended wording**: "How should...", "What are your thoughts...", "Describe..."

```
@[Graph][Update][Q:open][What is your target launch timeline?]
→ User types: "Q2 2026, with beta in Q1"
```

**ALL questions MUST include a type suffix** - never use plain `[Q]`.

---

## Citation Types: [Because] vs [If]

### `@[Graph][Because]` - Cite Chosen/Consensus Path as Fact

Use `[Because]` to reference a path that has been **chosen by the User** or has **strong consensus** as a contextual fact:

```
@[Graph][Because][Q:single][What is deployment approach?][A][Phased rollout]
@[All] Given the phased rollout approach, we need to define phase boundaries and rollback procedures...
```

**🔥 CRITICAL**: **NEVER** use `[Because]` to cite paths marked with `[X]`. The `[X]` marker means the User explicitly rejected that path. Closed paths are NOT facts.

### `@[Graph][If]` - Explore Potential Path Hypothetically

Use `[If]` to explore implications of a path that **hasn't been chosen yet** but is still open for deliberation:

```
@[Graph][If][Q:single][What is deployment approach?][A][Big bang deployment]
@[All] If we choose big bang deployment, we should consider comprehensive rollback automation and extensive pre-production testing...
```

`[If]` enables specialists to **drive discussion down different DAG paths** without waiting for User selection. This helps the User make informed decisions by seeing implications of each option.

---

## Node State

- **Default**: `open` (available for deliberation and consideration)
- **Automatic close**: 2+ downvotes AND downvotes > upvotes → `closed` (hidden from User)
- **User explicit close** (future): `[X]` marker → permanently closed, removed from consideration

**A node without `[X]` is an open path for deliberation** - specialists can continue proposing alternatives, voting, and extending the decision tree.

**Single-Choice Selection Behavior** (future UI): When User selects one answer from a `[Q:single]` question, the UI will automatically add `[X]` to all other unselected answers, closing off those paths.

---

## Operations

### `@[Graph][Update]` - Add/Modify/Vote

The primary operation for all specialists. Use `[Update]` to:

1. **Propose a question**:
   ```
   @[Graph][Update][Q:single][What is the deployment approach?]
   ```

2. **Propose an answer**:
   ```
   @[Graph][Update][Q:single][What is the deployment approach?][A][Phased rollout]
   ```

3. **Vote on a question or answer**:
   ```
   @[Graph][Update][Q:single][What is the deployment approach?][+][Critical production question]
   @[Graph][Update][Q:single][What is the deployment approach?][A][Phased rollout][+][Reduces risk]
   ```

4. **Extend the tree with follow-up questions**:
   ```
   @[Graph][Update][Q:single][What is the deployment approach?][A][Phased rollout][Q:single][What are the phase boundaries?]
   ```

### `@[Graph][Collapse]` - Chair Only (Phase 3+)

Chair can consolidate linear Q→A→Q→A chains into a single "Decision" node:

```
Before Collapse:
Q1 → A1 (unanimous) → Q2 → A2 (unanimous) → Q3 → ...

After Collapse:
Decision[Deployment Strategy] (preserves full provenance internally)
  └─ Q3 → ... (continues from there)
```

This reduces visual clutter while preserving full lineage.

---

## How This Guides Axion Swarm Research

### Multi-Agent Architecture Validation

The Graph tool **validates the multi-agent architecture** by creating observable differences from single-LLM systems:

1. **Parallel domain validation**: 5+ specialists vote on the same node simultaneously, each from their unique perspective
2. **Minority dissent preservation**: Downvotes remain visible even if majority upvotes
3. **Cross-domain consensus emergence**: Agreement forms through independent voting, not coordinated discussion
4. **Question quality improvement**: Specialists collaboratively refine unclear questions through downvote+propose pattern
5. **Evidence vs opinion separation**: Votes with citations are evidence-based; votes without are expert opinion

These behaviors are **architecturally impossible with single-LLM systems** - you can't get parallel independent domain validation from one model with one perspective.

### Async-First Knowledge Construction

The Graph tool aligns with Axion's **async user interaction pattern** (3h minimum, 1.5d average response time):

- **Team builds comprehensive graph while User is away** (Phase 1-3)
- **User returns to structured options** (not buried in prose)
- **User selections create new context** → Team extends that path
- **Knowledge persists across sessions** → Graph grows incrementally over days/weeks

This mirrors **real-world expert collaboration** - teams do preparatory work asynchronously, present structured options, get decisions, then continue.

### Research Questions the Graph Tool Explores

1. **Do specialists naturally vote from their domain perspective?** (Observing voting patterns in graph.log)
2. **Does cross-domain voting improve question quality?** (Comparing poorly-worded vs improved questions)
3. **Do minority opinions provide valuable signals?** (Analyzing paths with split votes)
4. **Does hierarchical context improve semantic coherence?** (Measuring embedding similarity in paths vs isolated Q-A)
5. **Can collaborative filtering prune low-value paths effectively?** (Comparing closed vs open path quality)
6. **Does explicit provenance (ReadURL/Search) increase answer trustworthiness?** (Evidence-based vs opinion-based vote analysis)

### Future Research Directions

1. **Neo4j Backend**: Full graph database with real-time updates
2. **Vector Embeddings**: Export paths as semantic vectors for RAG
3. **Graph Visualization**: Interactive exploration of decision trees
4. **Voting Analytics**: Cross-domain consensus patterns, minority insight detection
5. **Decision Replay**: Time-travel through graph evolution
6. **Semantic Search**: Query graph by concept ("show me all risk-related questions")
7. **Path Comparison**: Visual diff between explored but rejected paths
8. **Provenance Chains**: Full citation lineage from root to leaf

---

## Current Implementation (Prototype)

**Status**: Observing usage patterns before building full backend

✓ Specialists use syntax naturally in conversation  
✓ All `[Update]` operations logged to `graph.log`  
✓ System acknowledges requests  
✗ No graph database backend yet  
✗ No visualization yet  
✗ No User selection UI yet  

**Purpose**: Observe how specialists collaborate to build structured knowledge, validate voting patterns, identify useful vs premature features, before implementing full backend.

---

## Example: Complete Workflow

```
Phase 1: Context proposes root question
@[Graph][Update][Q:single][What is the deployment strategy?]
@[Graph][Update][Q:single][What is the deployment strategy?][A][Phased rollout]
@[Graph][Update][Q:single][What is the deployment strategy?][A][Big bang]

Phase 1: ALL specialists vote on question AND answers
@[Graph][Update][Q:single][What is the deployment strategy?][+][Critical for risk management (Skeptic)]
@[Graph][Update][Q:single][What is the deployment strategy?][A][Phased rollout][+][Reduces blast radius (Skeptic)]
@[Graph][Update][Q:single][What is the deployment strategy?][A][Phased rollout][+][Easier to test incrementally (Engineer)]
@[Graph][Update][Q:single][What is the deployment strategy?][A][Big bang][-][Too risky without rollback plan (Skeptic)]

Phase 2: Research validates with evidence
@[Graph][Update][Q:single][What is the deployment strategy?][A][Phased rollout][+][Industry standard per https://sre.google/book/ (Research)]

Phase 2: Specialists extend path with follow-up questions
@[Graph][Update][Q:single][What is the deployment strategy?][A][Phased rollout][Q:single][What are the phase boundaries?]
@[Graph][Update][Q:single][What is the deployment strategy?][A][Phased rollout][Q:single][What is the rollback procedure?]

Phase 2: ALL specialists vote on NEW questions
@[Graph][Update][Q:single][...][A][Phased rollout][Q:single][What are the phase boundaries?][+][Essential planning question (Product Manager)]
@[Graph][Update][Q:single][...][A][Phased rollout][Q:single][What is the rollback procedure?][+][Critical safety question (DevOps)]

Phase 3: Specialist proposes answer with poor wording
@[Graph][Update][Q:single][...][A][Phased rollout][Q:single][What are the phase boundaries?][A][Do it by region]

Phase 3: Another specialist downvotes + proposes clearer version
@[Graph][Update][Q:single][...][Q:single][What are the phase boundaries?][A][Do it by region][-][Too vague - which regions? what order?]
@[Graph][Update][Q:single][...][Q:single][What are the phase boundaries?][A][Roll out by geographic region: US-West, US-East, EU, APAC][+][Clear sequence with specific regions]

Phase 4: User returns, sees structured decision tree with full voting history

Phase 5: User selects "Phased rollout" → "Big bang" gets [X]

Phase 6: Team extends the selected path with detailed follow-up questions
@[Graph][Because][Q:single][What is the deployment strategy?][A][Phased rollout]
Given phased rollout, we should define monitoring thresholds between phases...
```

**Result**: 
- Explored 2 deployment strategies
- Team validated "Phased rollout" with 3+ domain perspectives (Risk, Engineering, Research)
- Team identified 2 critical follow-up questions
- Team improved answer quality through collaborative refinement
- User selected with confidence, knowing team validated across domains
- Team continues building detail on chosen path with full context

---

## Key Principles

1. **Vote on EVERYTHING** - Both questions and answers, from your domain perspective
2. **Comment with full path context** - Your vote reflects the entire chain, not just the immediate node
3. **Voting ≠ Redundancy** - Your domain signal is essential even if others made similar points
4. **Improve, don't just critique** - Downvote unclear questions AND propose better alternatives
5. **Evidence > Opinion** - Use ReadURL/Search to back claims when possible
6. **User has final authority** - Team explores, User decides, Team executes
7. **Graph is for structure** - Text is for discussion, Graph is for decision trees
8. **Preserve minority views** - Downvotes stay visible, dissent is valuable signal

---

## Files & Integration

- **Log file**: `graph.log` (all `[Update]` operations with timestamps, phase, specialist)
- **Stub implementation**: `axion_swarm/graph_tool.py` (acknowledges requests, logs operations)
- **Integration**: `axion_swarm/agents.py` (processes `@[Graph]` like `@[Search]`)
- **Prompts**: `axion_swarm/prompts.py` (specialist instructions with domain-specific examples)
- **Documentation**: `ARCHITECTURE.md` (sections 3480-3800, complete technical specification)
- **Summary**: `GRAPH_TOOL_SUMMARY.md` (one-page quick reference)
- **This file**: `graph-tool-usage.md` (comprehensive usage guide and research intentions)

---

## Analyzing and Visualizing graph.log

### Purpose

The `graph.log` file captures all `@[Graph][Update]` operations with timestamps, phase, and specialist. Before building the full Neo4j backend, we can analyze this log to:

1. **Validate that specialists use the tool correctly** (full path voting, domain-specific comments)
2. **Identify voting patterns** (consensus, contention, cross-domain validation)
3. **Measure graph health** (coverage, depth, branching)
4. **Inform backend design** (what queries matter, what analytics to support)

### Log Format

Each line follows this structure:

```
[timestamp] Phase N | Specialist name | @[Graph][Update][...path...][vote][comment]
```

Example:
```
[2025-10-25 18:40:57.413] Phase 4 | Research specialist | @[Graph][Update][Q:single][What should the MVP focus on?][A][Logistics optimization][+][Aligns with routing-first MVP]
```

### Critical Insight: Full Path = Node Identity

**The most important lesson from analyzing graph.log: Each node is uniquely identified by its COMPLETE PATH from root.**

```python
# ❌ WRONG: Treating answer text as node identity
node_id = "Logistics optimization"  # Too vague - which context?

# ✅ CORRECT: Full path is the node identity
node_id = "[Q:single][What should the MVP focus on?][A][Logistics optimization]"
```

**Why this matters:**

- The same answer text can appear in multiple paths with different context
- Votes apply to the **entire semantic chain**, not just the leaf
- When specialists vote on deep paths, they're evaluating accumulated context

Example of different paths with similar text:

```
[Q:single][What should the MVP focus on?][A][Contracts]
[Q:single][What integrations are needed?][A][Contracts]  ← Different question!
```

These are **two distinct nodes** with different semantic meaning.

### Python Example: Vote Tallying by Full Path

```python
import re
from collections import defaultdict

# Parse graph.log
with open('graph.log', 'r') as f:
    lines = f.readlines()

nodes = {}  # key: full_path_string, value: node data
vote_tally = defaultdict(lambda: {'upvotes': 0, 'downvotes': 0, 'up_by': [], 'down_by': []})

def build_full_path(brackets):
    """Build full path from bracket sequence, stopping at vote markers"""
    path_parts = []
    i = 0
    while i < len(brackets):
        item = brackets[i]
        
        # Stop at vote markers
        if item in ['+', '-']:
            break
        
        # Question with type
        if item.startswith('Q:'):
            if i + 1 < len(brackets) and brackets[i + 1] not in ['+', '-', 'Q:', 'A', 'A:']:
                path_parts.append(f"[{item}][{brackets[i + 1]}]")
                i += 2
            else:
                path_parts.append(f"[{item}]")
                i += 1
        # Answer with optional type
        elif item.startswith('A:') or item == 'A':
            if i + 1 < len(brackets) and brackets[i + 1] not in ['+', '-', 'Q:', 'A', 'A:']:
                path_parts.append(f"[{item}][{brackets[i + 1]}]")
                i += 2
            else:
                path_parts.append(f"[{item}]")
                i += 1
        else:
            i += 1
    
    return "".join(path_parts)

# Parse each log entry
for line in lines:
    line = line.strip()
    if not line:
        continue
    
    # Extract metadata
    match = re.match(r'\[([^\]]+)\] Phase (\d+) \| ([^|]+) \| @\[Graph\]\[Update\](.+)$', line)
    if not match:
        continue
    
    timestamp, phase, specialist, content = match.groups()
    specialist = specialist.strip()
    
    # Parse all bracketed content
    brackets = re.findall(r'\[([^\]]+)\]', content)
    
    if not brackets:
        continue
    
    # Build full path
    full_path = build_full_path(brackets)
    
    if not full_path:
        continue
    
    # Detect vote and comment
    vote = None
    vote_comment = None
    
    for i, item in enumerate(brackets):
        if item in ['+', '-']:
            vote = item
            if i + 1 < len(brackets):
                vote_comment = brackets[i + 1]
            break
    
    # Store node info
    if full_path not in nodes:
        nodes[full_path] = {
            'votes': [],
            'first_seen_phase': phase,
            'first_seen_specialist': specialist
        }
    
    # Record vote if present
    if vote:
        nodes[full_path]['votes'].append({
            'specialist': specialist,
            'vote': vote,
            'comment': vote_comment,
            'phase': phase,
            'timestamp': timestamp
        })
        
        if vote == '+':
            vote_tally[full_path]['upvotes'] += 1
            vote_tally[full_path]['up_by'].append(specialist)
        else:
            vote_tally[full_path]['downvotes'] += 1
            vote_tally[full_path]['down_by'].append(specialist)

# Report by depth
root_questions = [p for p in nodes if p.count('[Q:') == 1 and '[A]' not in p and '[A:' not in p]
depth_1_answers = [p for p in nodes if p.count('[Q:') == 1 and ('[A]' in p or '[A:' in p)]
depth_2_questions = [p for p in nodes if p.count('[Q:') == 2]
depth_2_answers = [p for p in nodes if p.count('[Q:') == 2 and p.count('[A]') + p.count('[A:') >= 2]

print(f"Root questions: {len(root_questions)}")
print(f"Depth 1 answers: {len(depth_1_answers)}")
print(f"Depth 2 questions: {len(depth_2_questions)}")
print(f"Depth 2+ answers: {len(depth_2_answers)}")

# Show strongest consensus
for path in sorted(nodes.keys(), key=lambda p: vote_tally[p]['upvotes'] - vote_tally[p]['downvotes'], reverse=True)[:5]:
    tally = vote_tally[path]
    net = tally['upvotes'] - tally['downvotes']
    print(f"\n✅ {path}")
    print(f"   Net: {net:+d} (+{tally['upvotes']} / -{tally['downvotes']})")
    print(f"   Endorsed by: {', '.join(set(tally['up_by']))}")
```

### Generating a Current Report

**Complete standalone script for analyzing graph.log:**

Save the following as `analyze_graph.py` in your project root:

```python
#!/usr/bin/env python3
"""
Analyze graph.log and produce a human-readable report.

Usage:
    python analyze_graph.py [path_to_graph.log]
    
If no path is provided, defaults to ./graph.log
"""

import re
import sys
from collections import defaultdict
from pathlib import Path

def build_full_path(brackets):
    """Build full path from bracket sequence, stopping at vote markers"""
    path_parts = []
    i = 0
    while i < len(brackets):
        item = brackets[i]
        
        if item in ['+', '-']:
            break
        
        if item.startswith('Q:'):
            if i + 1 < len(brackets) and brackets[i + 1] not in ['+', '-'] and not brackets[i + 1].startswith('Q:') and not brackets[i + 1].startswith('A'):
                path_parts.append(f"[{item}][{brackets[i + 1]}]")
                i += 2
            else:
                path_parts.append(f"[{item}]")
                i += 1
        elif item.startswith('A:') or item == 'A':
            if i + 1 < len(brackets) and brackets[i + 1] not in ['+', '-'] and not brackets[i + 1].startswith('Q:') and not brackets[i + 1].startswith('A'):
                path_parts.append(f"[{item}][{brackets[i + 1]}]")
                i += 2
            else:
                path_parts.append(f"[{item}]")
                i += 1
        else:
            i += 1
    
    return "".join(path_parts)

def analyze_graph_log(log_path):
    """Parse graph.log and return analysis data"""
    with open(log_path, 'r') as f:
        lines = f.readlines()
    
    nodes = {}
    vote_tally = defaultdict(lambda: {'upvotes': 0, 'downvotes': 0, 'up_by': [], 'down_by': []})
    specialist_stats = defaultdict(lambda: {'upvotes': 0, 'downvotes': 0, 'total': 0, 'by_phase': defaultdict(int)})
    
    for line in lines:
        line = line.strip()
        if not line:
            continue
        
        match = re.match(r'\[([^\]]+)\] Phase (\d+) \| ([^|]+) \| @\[Graph\]\[Update\](.+)$', line)
        if not match:
            continue
        
        timestamp, phase, specialist, content = match.groups()
        specialist = specialist.strip()
        
        brackets = re.findall(r'\[([^\]]+)\]', content)
        if not brackets:
            continue
        
        full_path = build_full_path(brackets)
        if not full_path:
            continue
        
        # Detect vote and comment
        vote = None
        vote_comment = None
        for i, item in enumerate(brackets):
            if item in ['+', '-']:
                vote = item
                if i + 1 < len(brackets):
                    vote_comment = brackets[i + 1]
                break
        
        # Store node info
        if full_path not in nodes:
            nodes[full_path] = {
                'votes': [],
                'first_seen_phase': phase,
                'first_seen_specialist': specialist
            }
        
        # Record vote if present
        if vote:
            nodes[full_path]['votes'].append({
                'specialist': specialist,
                'vote': vote,
                'comment': vote_comment,
                'phase': phase,
                'timestamp': timestamp
            })
            
            if vote == '+':
                vote_tally[full_path]['upvotes'] += 1
                vote_tally[full_path]['up_by'].append(specialist)
                specialist_stats[specialist]['upvotes'] += 1
            else:
                vote_tally[full_path]['downvotes'] += 1
                vote_tally[full_path]['down_by'].append(specialist)
                specialist_stats[specialist]['downvotes'] += 1
            
            specialist_stats[specialist]['total'] += 1
            specialist_stats[specialist]['by_phase'][phase] += 1
    
    return nodes, vote_tally, specialist_stats

def print_report(nodes, vote_tally, specialist_stats):
    """Print formatted report"""
    
    # Categorize nodes
    root_questions = [p for p in nodes if p.count('[Q:') == 1 and '[A]' not in p and '[A:' not in p]
    depth_1_answers = [p for p in nodes if p.count('[Q:') == 1 and ('[A]' in p or '[A:' in p) and p.count('[Q:') + p.count('[A]') + p.count('[A:') == 2]
    depth_2_questions = [p for p in nodes if p.count('[Q:') == 2 and p.count('[A]') + p.count('[A:') == 1]
    depth_2_plus = [p for p in nodes if p.count('[Q:') >= 2 and p.count('[A]') + p.count('[A:') >= 2]
    
    total_votes = sum(len(nodes[p]['votes']) for p in nodes)
    nodes_with_votes = len([p for p in nodes if nodes[p]['votes']])
    
    # Calculate max depth
    max_depth = max((p.count('[Q:') + p.count('[A]') + p.count('[A:')) for p in nodes) if nodes else 0
    
    print("╔═══════════════════════════════════════════════════════════════════════════════╗")
    print("║                         GRAPH STATE REPORT                                    ║")
    print("╚═══════════════════════════════════════════════════════════════════════════════╝")
    
    print("\n📊 METRICS")
    print("━" * 84)
    print(f"• Total nodes (by full path):    {len(nodes)}")
    print(f"• Nodes with votes:               {nodes_with_votes} ({100*nodes_with_votes/len(nodes):.1f}%)" if nodes else "• Nodes with votes:               0")
    print(f"• Total vote actions:             {total_votes}")
    print(f"• Root questions:                 {len(root_questions)}")
    print(f"• Depth 1 answers:                {len(depth_1_answers)}")
    print(f"• Depth 2 questions:              {len(depth_2_questions)}")
    print(f"• Depth 2+ answers:               {len(depth_2_plus)}")
    print(f"• Maximum depth:                  {max_depth}")
    
    print("\n🎭 SPECIALISTS")
    print("━" * 84)
    for specialist in sorted(specialist_stats.keys()):
        stats = specialist_stats[specialist]
        pct = 100 * stats['upvotes'] / stats['total'] if stats['total'] > 0 else 0
        print(f"{specialist:20} {stats['total']:3} votes ({stats['upvotes']:3} ✅ / {stats['downvotes']:3} ❌)  {pct:5.1f}% positive")
    
    print("\n⚖️  CONSENSUS")
    print("━" * 84)
    unanimous = len([p for p in nodes if vote_tally[p]['upvotes'] >= 4 and vote_tally[p]['downvotes'] == 0] + 
                   [p for p in nodes if vote_tally[p]['downvotes'] >= 4 and vote_tally[p]['upvotes'] == 0])
    split = len([p for p in nodes if vote_tally[p]['upvotes'] > 0 and vote_tally[p]['downvotes'] > 0])
    
    strongest_pos = max((vote_tally[p]['upvotes'] - vote_tally[p]['downvotes'] for p in nodes), default=0)
    strongest_neg = min((vote_tally[p]['upvotes'] - vote_tally[p]['downvotes'] for p in nodes), default=0)
    
    print(f"Unanimous votes:       {unanimous} paths")
    print(f"Split votes:           {split} paths")
    print(f"Strongest consensus:   {strongest_pos:+d} net")
    print(f"Strongest rejection:   {strongest_neg:+d} net")
    
    # Top endorsed paths
    print("\n🌳 TOP ENDORSED PATHS")
    print("━" * 84)
    top_endorsed = sorted(nodes.keys(), 
                         key=lambda p: vote_tally[p]['upvotes'] - vote_tally[p]['downvotes'], 
                         reverse=True)[:5]
    
    for i, path in enumerate(top_endorsed, 1):
        tally = vote_tally[path]
        net = tally['upvotes'] - tally['downvotes']
        if net <= 0:
            break
        # Truncate long paths
        display_path = path if len(path) <= 70 else path[:67] + "..."
        print(f"{i}. {display_path}")
        print(f"   Net: {net:+d} (+{tally['upvotes']} / -{tally['downvotes']}) | {', '.join(set(tally['up_by']))}")
    
    # Top rejected paths
    print("\n❌ TOP REJECTED PATHS")
    print("━" * 84)
    top_rejected = sorted(nodes.keys(), 
                         key=lambda p: vote_tally[p]['upvotes'] - vote_tally[p]['downvotes'])[:5]
    
    for i, path in enumerate(top_rejected, 1):
        tally = vote_tally[path]
        net = tally['upvotes'] - tally['downvotes']
        if net >= 0:
            break
        display_path = path if len(path) <= 70 else path[:67] + "..."
        print(f"{i}. {display_path}")
        print(f"   Net: {net:+d} (+{tally['upvotes']} / -{tally['downvotes']}) | {', '.join(set(tally['down_by']))}")
    
    # Contentious paths
    contentious = [(p, vote_tally[p]) for p in nodes if vote_tally[p]['upvotes'] > 0 and vote_tally[p]['downvotes'] > 0]
    if contentious:
        print("\n⚡ CONTENTIOUS PATHS (Split Votes)")
        print("━" * 84)
        for path, tally in sorted(contentious, key=lambda x: abs(x[1]['upvotes'] - x[1]['downvotes']))[:5]:
            display_path = path if len(path) <= 70 else path[:67] + "..."
            print(f"• {display_path}")
            print(f"  For: {', '.join(set(tally['up_by']))} | Against: {', '.join(set(tally['down_by']))}")
    
    print("\n🔍 OBSERVATIONS")
    print("━" * 84)
    
    # Check for cross-specialist agreement
    multi_specialist_paths = [p for p in nodes if len(set(vote_tally[p]['up_by'] + vote_tally[p]['down_by'])) >= 3]
    print(f"✅ {len(multi_specialist_paths)} paths voted on by 3+ specialists (cross-domain validation)")
    
    # Check for follow-ups
    follow_ups = [p for p in nodes if p.count('[Q:') >= 2]
    print(f"✅ {len(follow_ups)} follow-up questions proposed (autonomous exploration)")
    
    # Check for path-aware comments
    path_aware = sum(1 for p in nodes for v in nodes[p]['votes'] if v['comment'] and 'Path:' in v['comment'])
    print(f"✅ {path_aware} votes with path-aware comments (semantic context understanding)")
    
    if split == 0:
        print("⚠️  No split votes detected - consider harder trade-off questions to test system")
    
    print("\n" + "═" * 84)

def main():
    log_path = sys.argv[1] if len(sys.argv) > 1 else 'graph.log'
    
    if not Path(log_path).exists():
        print(f"Error: {log_path} not found")
        sys.exit(1)
    
    print(f"Analyzing {log_path}...\n")
    
    nodes, vote_tally, specialist_stats = analyze_graph_log(log_path)
    
    if not nodes:
        print("No graph data found in log file.")
        sys.exit(0)
    
    print_report(nodes, vote_tally, specialist_stats)

if __name__ == '__main__':
    main()
```

**To run the analysis:**

```bash
# Make it executable (first time only)
chmod +x analyze_graph.py

# Run the analysis
python analyze_graph.py

# Or specify a different log file
python analyze_graph.py /path/to/other/graph.log
```

### Using with Cursor (Recommended Workflow)

**Option 1: Run via Terminal in Cursor**

1. Open Cursor's integrated terminal (`` Ctrl+` `` or `Cmd+~`)
2. Run: `python analyze_graph.py`
3. View the formatted report in the terminal

**Option 2: Ask Cursor to Run It**

1. Select this entire section (from "Complete standalone script" through the closing triple-backticks)
2. Ask Cursor: "Run this analysis script on the current graph.log and show me the report"
3. Cursor will execute the script and display results

**Option 3: Create a Cursor Rule (`.cursorrules` file)**

Add to your `.cursorrules` file in the project root:

```
# Graph Analysis
When asked to "analyze the graph" or "generate graph report" or similar:
1. Run: python analyze_graph.py
2. Display the full output
3. Highlight any notable patterns (unanimous votes, contentious paths, coverage gaps)

When asked to "explain a graph path":
1. Find the full path in graph.log (remember: path = complete chain from root)
2. Show all votes on that path with specialist comments
3. Explain the accumulated semantic context
```

**Option 4: Cursor Composer Command**

Create a saved command in Cursor:

1. Open Command Palette (`Cmd+Shift+P` / `Ctrl+Shift+P`)
2. Add custom command: "Analyze Graph State"
3. Command: `python analyze_graph.py | less`

**Option 5: Quick Analysis Prompt Template**

Keep this prompt handy to paste into Cursor:

```
Analyze the current graph.log state:
1. Run analyze_graph.py (or use the inline Python from graph-tool-usage.md)
2. Show the formatted report
3. Identify:
   - Strongest consensus paths (net votes)
   - Any contentious/split votes
   - Coverage gaps (unvoted nodes)
   - Cross-domain validation patterns
4. Recommend next questions to explore based on current state
```

### Expected Output Format

The script produces a formatted report like:

```
╔═══════════════════════════════════════════════════════════════════════════════╗
║                         GRAPH STATE REPORT                                    ║
╚═══════════════════════════════════════════════════════════════════════════════╝

📊 METRICS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
• Total nodes (by full path):    57
• Nodes with votes:               55 (96.5%)
• Total vote actions:             173
• Root questions:                 8
• Depth 1 answers:                35
• Depth 2 questions:              8
• Depth 2+ answers:               6
• Maximum depth:                  4

🎭 SPECIALISTS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Context specialist       58 votes ( 52 ✅ /   6 ❌)   89.7% positive
Research specialist      20 votes ( 18 ✅ /   2 ❌)   90.0% positive
...

⚖️  CONSENSUS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Unanimous votes:       46 paths
Split votes:           0 paths
Strongest consensus:   +5 net
Strongest rejection:   -5 net

🌳 TOP ENDORSED PATHS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
1. [Q:single][What should the MVP focus on?][A][Logistics optimization]
   Net: +5 (+5 / -0) | Context specialist, Research specialist, Skeptic specialist, Ethicist specialist
...

🔍 OBSERVATIONS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
✅ 45 paths voted on by 3+ specialists (cross-domain validation)
✅ 14 follow-up questions proposed (autonomous exploration)
✅ 127 votes with path-aware comments (semantic context understanding)
```

### Key Metrics to Track

1. **Graph Coverage**
   - Total unique nodes (by full path)
   - Nodes with votes / total nodes
   - Vote actions per node (mean, median)

2. **Graph Structure**
   - Root questions (depth 0)
   - Answers per question (breadth)
   - Maximum depth reached
   - Branching factor

3. **Specialist Engagement**
   - Votes per specialist
   - Upvote/downvote ratio per specialist
   - Phase participation (which specialists active in which phases)

4. **Consensus Patterns**
   - Unanimous votes (+5 or -5 with 4 core specialists)
   - Split votes (contention signals)
   - Unvoted nodes (coverage gaps)

5. **Domain Validation**
   - Cross-specialist agreement on same paths
   - Domain-specific comment patterns (Skeptic mentions "risk", Ethicist mentions "harm")

### Lessons Learned from Current Graph State

**From analyzing the timber logistics platform MVP planning graph (57 nodes, 173 votes):**

#### 1. Full Path Tracking is Essential

**Problem observed:** Initial analysis collapsed nodes by answer text alone, missing context.

```
# These are DIFFERENT nodes with different semantic meaning:
[Q:single][What should the MVP focus on?][A][Logistics optimization]
[Q:single][What integrations?][A][Logistics optimization]
```

**Solution:** Always track and report by complete path from root.

#### 2. Specialists Vote from Domain Perspective

Each specialist brings a unique lens to the same path:

```
Path: [Q:single][Who is primary contracting party?][A][Service providers]

✅ Context: "Keeps contract templates focused, minimizes legal complexity"
✅ Research: "Aligns with logistics-first MVP, requires NIST identity proofing"
✅ Skeptic: "Lower provenance risk, reduces legal gating"
✅ Ethicist: "Lowers provenance burden, makes worker protections tractable"
```

This validates **multi-agent architecture value** - four distinct perspectives on the same decision.

#### 3. Unanimous Agreement Shows Maturity

Paths with +5 or -5 net votes (all specialists aligned) indicate:
- Clear trade-offs that all domains recognize
- Strong consensus on best practices
- Effective pruning of obviously poor options

Example from current graph:
```
❌ [Q:single][MVP focus?][A][Integrated platform] → -5 net
   All specialists downvoted: "Too broad for MVP"
```

#### 4. Follow-Up Questions Show Autonomous Thinking

Specialists extend promising paths without user prompting:

```
[Q:single][Binding policy?][A][Human review required]
  └─ Ethicist adds: [Q:single][What criteria allow auto-bind later?]
     └─ Ethicist proposes detailed answer with FSC/CoC, PIA, thresholds
        └─ All 4 specialists upvote the detailed criteria
```

This demonstrates **proactive multi-agent collaboration** building shared context.

#### 5. Comments Reflect Full Path Context

Good voting pattern observed:

```
✅ "Path: MVP→Contracts→Binding policy→Human review required→Criteria for auto-bind — 
    These criteria protect DIGNITY, NON-HARM, CONSENT, and TRANSPARENCY"
```

The comment shows the specialist understands the **accumulated decision chain**.

#### 6. Phase Progression Shows Building Context

- **Phase 1-2:** Context proposes root questions, all specialists vote
- **Phase 2-3:** Specialists extend paths with follow-ups
- **Phase 3-4:** Team votes on extended paths from multiple perspectives
- **Phase 4-5:** Deeper answers get detailed multi-criteria proposals

Each phase builds on previous consensus.

#### 7. No Contentious Votes (Yet)

Current graph shows **zero split votes** - all paths have unanimous direction.

**Possible interpretations:**
1. Questions are straightforward with clear best practices
2. Team has genuine alignment on fundamentals
3. **OR** we need harder trade-off questions to test the system

**To test:** Introduce questions with legitimate trade-offs (cost vs. safety, speed vs. thoroughness).

#### 8. Evidence-Based vs. Opinion-Based Votes

Research specialist frequently includes citations:

```
✅ Research: "Lacey Act strict-liability — see https://www.aphis.usda.gov/..."
✅ Research: "NIST SP 800-63 identity assurance — see https://pages.nist.gov/..."
```

Other specialists vote with domain expertise:

```
✅ Skeptic: "Lower provenance risk" (experience-based)
✅ Ethicist: "Protects DIGNITY, NON-HARM" (framework-based)
```

Both types are valuable; citations add external validation.

### Visualization Approaches

**1. Tree Diagram (ASCII)**

```
[Q:single][What should the MVP focus on?] (+5)
├─ [A][Logistics optimization] (+5)
│  └─ [Q:single][What integrations?] (+2)
├─ [A][Vendor marketplace] (+5)
│  ├─ [Q:single][What vetting criteria?] (+1)
│  └─ [Q:single][What transparency mechanisms?] (+1)
├─ [A][Contract generation] (+5)
│  └─ [Q:single][Binding policy?] (+4)
│     └─ [A][Human review required] (+4)
│        └─ [Q:single][Criteria for auto-bind?] (+3)
│           └─ [A][FSC/CoC + PIA + counsel + <$5k] (+4)
└─ [A][Integrated platform] (-5) ← Pruned by consensus
```

**2. Consensus Heatmap**

```
Path                                    | Context | Research | Skeptic | Ethicist | Net
----------------------------------------|---------|----------|---------|----------|-----
[Q][MVP focus?][A][Logistics]          |    ✅   |    ✅    |   ✅    |    ✅    | +5
[Q][MVP focus?][A][Marketplace]        |    ✅   |    ✅    |   ✅    |    ✅    | +5
[Q][MVP focus?][A][Integrated]         |    ❌   |    ❌    |   ❌    |    ❌    | -5
[Q][Jurisdiction?][A][Single-country]  |    ✅   |    ✅    |   ✅    |    ✅    | +5
[Q][Jurisdiction?][A][Multi-country]   |    ❌   |    ❌    |   ❌    |    ❌    | -5
```

**3. Specialist Participation by Phase**

```
Phase | Context | Research | Skeptic | Ethicist | Total Votes
------|---------|----------|---------|----------|-------------
  1   |   11    |    0     |    0    |    0     |     11
  2   |   47    |   20     |   21    |   28     |    116
  3   |    6    |    0     |    0    |    2     |      8
  4   |   14    |   10     |    6    |    6     |     36
  5   |    3    |    0     |    0    |    0     |      3
```

**4. Decision Provenance (Path Visualization)**

Show how a deep path accumulates context:

```
ROOT
  ↓
[Q:single][What should the contract binding policy be at launch?]
  • Question endorsed by: Context, Research, Skeptic, Ethicist (+4)
  • Critical gating decision for automation workflows
  ↓
[A][Human review required]
  • Answer endorsed by: Context, Research, Skeptic, Ethicist (+4)
  • Reduces legal/ethical exposure at MVP stage
  ↓
[Q:single][What criteria allow automated binding later?]
  • Follow-up endorsed by: Context, Research, Skeptic (+3)
  • Defines measurable preconditions for transitioning
  ↓
[A][Enable auto-bind only when vendor provenance is externally verified
    (e.g., FSC/CoC + insurance), PIA passed, immutable audit trail in place,
    explainability & appeal mechanism operational, counsel signs off,
    and contract value/risk is below validated low-risk threshold (<$5k)]
  • Detailed answer endorsed by: Context, Research, Skeptic, Ethicist (+4)
  • Aligns with NIST SP 800-63, FSC CoC, ACORD, ESIGN/UETA
  • Protects DIGNITY, NON-HARM, CONSENT, TRANSPARENCY

SEMANTIC VECTOR: "In the context of MVP contract generation, we chose human
review as the binding policy, and these specific criteria (provenance, PIA,
audit, explainability, counsel, value threshold) must be met before enabling
automated binding."

This is the FULL MEANING of the deepest node.
```

### Reporting Template

```
╔═══════════════════════════════════════════════════════════════════════════════╗
║                         GRAPH STATE REPORT                                    ║
╚═══════════════════════════════════════════════════════════════════════════════╝

📊 METRICS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
• Total nodes (by full path):    57
• Nodes with votes:               55 (96.5%)
• Total vote actions:             173
• Root questions:                 8
• Depth 1 answers:                35
• Depth 2 questions:              8
• Depth 2+ answers:               6
• Maximum depth:                  4 (ROOT → Q → A → Q → A)

🎭 SPECIALISTS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Context:      58 votes (52 ✅ / 6 ❌)  89.7% positive
Research:     20 votes (18 ✅ / 2 ❌)  90.0% positive
Skeptic:      21 votes (19 ✅ / 2 ❌)  90.5% positive
Ethicist:     28 votes (25 ✅ / 3 ❌)  89.3% positive

⚖️  CONSENSUS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Unanimous votes:       46 paths (100% of voted paths)
Split votes:           0 paths
Contentious votes:     0 paths
Strongest consensus:   +5 net (10 paths)
Strongest rejection:   -5 net (2 paths)

🌳 TOP ENDORSED PATHS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
1. [Q:single][What should the MVP focus on?][A][Logistics optimization]
   Net: +5 | All specialists endorsed
   
2. [Q:single][What jurisdictional scope?][A][Single-country launch]
   Net: +5 | All specialists endorsed
   
3. [Q:single][Binding policy?][A][Human review][Q][Criteria?][A][FSC/CoC+PIA...]
   Net: +4 | Deep path with full provenance criteria

❌ TOP REJECTED PATHS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
1. [Q:single][What should the MVP focus on?][A][Integrated platform]
   Net: -5 | "Too broad for MVP" - all specialists rejected
   
2. [Q:single][What jurisdictional scope?][A][Multi-jurisdiction launch]
   Net: -5 | "Multiplies legal complexity" - all specialists rejected

🔍 OBSERVATIONS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
✅ All specialists voting on same paths from distinct domain perspectives
✅ Follow-up questions proposed autonomously (6 depth-2 questions)
✅ Comments reflect full path context (semantic accumulation)
✅ Evidence-based votes include citations (Research specialist)
⚠️  No contentious votes yet - need harder trade-off questions to test system
```

### Integration with Backend (Future)

When the Neo4j backend is built, these analysis patterns inform queries:

```cypher
// Find all paths with split votes (contention signals)
MATCH path = (root:Question)-[*]->(node)
WHERE node.upvotes > 0 AND node.downvotes > 0
RETURN path, node.upvotes, node.downvotes

// Find paths where Skeptic and Ethicist disagree
MATCH (node)-[:VOTED_BY]->(v:Vote)
WHERE v.specialist IN ['Skeptic', 'Ethicist']
WITH node, 
     sum(CASE WHEN v.specialist = 'Skeptic' AND v.vote = '+' THEN 1 ELSE 0 END) as skeptic_up,
     sum(CASE WHEN v.specialist = 'Ethicist' AND v.vote = '-' THEN 1 ELSE 0 END) as ethicist_down
WHERE skeptic_up > 0 AND ethicist_down > 0
RETURN node

// Semantic path search: Find all paths about "legal" concerns
MATCH path = (root)-[*]->(node)
WHERE any(n IN nodes(path) WHERE n.text CONTAINS 'legal' OR n.text CONTAINS 'jurisdiction')
RETURN path
```

---

## Web Interface Visualization (2025-10-25)

The Graph tool now has **real-time web visualization** alongside the terminal interface.

### Three Viewing Modes

**1. Terminal Reports** (`python analyze_graph.py`)
- Quick analysis reports printed to console
- Top endorsed/rejected paths
- Specialist voting statistics
- Contentious nodes (split votes)
- Command-line friendly for scripting

**2. Static HTML Form** (`http://localhost:5000/form`)
- Snapshot of current graph state
- Interactive radio buttons/checkboxes
- Cascading selection (nested clicks auto-select parents)
- Shows graph commands on submission
- Good for quick testing/mockup

**3. Real-Time Vue.js App** (`http://localhost:5000/`)
- **Live updates** as agents vote (WebSocket)
- **Vote on any node** with 👍/👎/❌ buttons
- **Sacred user state** - your selections never cleared
- **Cascading selection** - nested choices auto-select parents
- **Multi-user support** - multiple people can view simultaneously
- **Bi-directional** - submit votes back to agents
- **Diff tracking** - only submits changes since last submission

### Running the Web Interface

```bash
# Terminal 1: Agent chat (TUI)
python main_tui.py

# Terminal 2: Web interface + TUI reports
python webserver.py

# Browser
http://localhost:5000/          # Vue.js real-time
http://localhost:5000/form      # Static HTML
```

### Benefits for Graph Research

The web interface provides **new observable artifacts** for research:

1. **User Decision Patterns**
   - How users navigate nested questions
   - Which paths users explore vs skip
   - Correlation between specialist votes and user selections
   
2. **Real-Time Collaboration**
   - Multiple users voting simultaneously
   - Consensus formation speed
   - Divergence patterns (different users select different paths)

3. **Interaction Metrics**
   - Time spent per decision
   - Scroll depth in nested trees
   - Back-navigation patterns (changing minds)

4. **Visual Validation**
   - Color-coded consensus instantly visible
   - Tree structure shows semantic hierarchy
   - Split votes highlight contentious nodes

### Cascading Selection

When users select nested radio buttons, **all parent selections automatically cascade**:

```
Before:
○ Microservices
  ○ REST APIs
    ○ HTTP/2 with gRPC  ← User clicks

After (automatic):
● Microservices        ← Auto-selected
  ● REST APIs          ← Auto-selected  
    ● HTTP/2 with gRPC ← User clicked
```

This enforces **semantic path integrity** - you can't select a nested answer without implicitly choosing its entire parent context. The interface makes semantic context accumulation **visually explicit**.

### Sacred User State

Critical design principle: **User selections are never cleared by incoming agent updates**.

- Agents vote → Graph updates → User sees new nodes
- But user's radio buttons/checkboxes remain unchanged
- Creates confidence for thoughtful decision-making
- Users can work at own pace without interruption

This separates **collaborative exploration** (agents propose) from **authoritative decision** (user selects).

### Documentation

- `WEB_UI_README.md` - Complete setup guide
- `WEB_IMPLEMENTATION_SUMMARY.md` - Technical architecture
- `setup_web.sh` - One-command installation

---

## Conclusion

The `@[Graph]` tool transforms Axion Swarm from a **chat-based multi-agent system** into a **collaborative knowledge construction platform**. By creating structured, votable, traceable decision trees with cross-domain validation, the Graph tool:

- **Makes expert reasoning explicit and queryable** (not buried in prose)
- **Enables parallel domain validation** (architecturally impossible with single-LLM)
- **Preserves minority dissent as valuable signal** (not lost to majority voice)
- **Creates semantic context accumulation** (hierarchical paths form coherent vectors)
- **Separates exploration from decision** (team proposes, user decides)
- **Produces machine-readable knowledge** (exportable to graphs, vectors, RAG systems)

This is the **research core** of Axion Swarm - exploring whether multi-agent architecture with structured collaborative tools produces **observably better knowledge construction** than single-agent systems with longer context windows.

The Graph tool is the **observable artifact** where we can measure:
- Cross-domain consensus patterns
- Question quality improvement through collaboration
- Evidence-based vs opinion-based validation
- Minority insight value
- Semantic coherence in hierarchical paths

All of this is currently being observed in **prototype mode** through `graph.log` before we build the full Neo4j backend. We're watching how specialists naturally use the tool to inform what the backend should actually do.

---

*For complete technical specification, see `ARCHITECTURE.md` sections 3480-3800.*  
*For quick reference, see `GRAPH_TOOL_SUMMARY.md`.*  
*For implementation details, see `axion_swarm/graph_tool.py` and `axion_swarm/agents.py`.*

