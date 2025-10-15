# Graph Tool - Composite Key Design

## Core Principle

**Node identity = full path through the tree**

Every question and answer is identified by its complete path from root, making each node unique AND contextually rich for LLMs.

## Path Structure

```
Q1: "What is autonomy preference?"
├─ Q1.A1: "Fully autonomous"
│  ├─ Q1.A1.Q1: "What safety gates?"
│  │  ├─ Q1.A1.Q1.A1: "Pre-execution validation"
│  │  └─ Q1.A1.Q1.A2: "Real-time monitoring"
│  └─ Q1.A1.Q2: "What rollback mechanism?"
│     └─ Q1.A1.Q2.A1: "Automatic rollback on error"
├─ Q1.A2: "Advisory only (human approval)"
│  ├─ Q1.A2.Q1: "What approval workflow?"
│  │  ├─ Q1.A2.Q1.A1: "RBAC-based"
│  │  └─ Q1.A2.Q1.A2: "Manager-only"
│  └─ Q1.A2.Q2: "What notification system?"
└─ Q1.A3: "Hybrid (policy-based)"
   └─ Q1.A3.Q1: "How to classify risk levels?"
```

**Key insight**: `Q1.A1.Q1` and `Q1.A2.Q1` are DIFFERENT questions because they exist in different contexts!

- `Q1.A1.Q1` asks about safety gates in an autonomous context
- `Q1.A2.Q1` asks about approval workflow in an advisory context

## Benefits for LLM Context

### 1. Full Context in Every Path

When an LLM sees path `Q1.A2.Q1.A1`, it can infer:
```
"In response to Q1, user chose A2 (advisory only),
 then for follow-up Q1, they're considering A1 (RBAC-based)"
```

The path IS the context chain!

### 2. Prevents Ambiguity

Without paths:
```
Q5: "What approval workflow?" 
→ Which path are we on? Autonomous? Advisory? Hybrid?
```

With paths:
```
Q1.A2.Q1: "What approval workflow?"
→ Clear: This is in the "advisory only" branch
```

### 3. Natural Scope Enforcement

Specialists write more specific questions because they see the context:

**Bad (flat):**
```
Q5: "What about security?"  // Too vague
```

**Good (composite):**
```
Q1.A1.Q3: "What security validation for autonomous execution?"  // Scoped
```

The path structure encourages clarity!

## Implementation

### Schema

```python
# Neo4j node structure
{
  "path": "Q1.A2.Q1.A1",              # Unique identifier (full path)
  "text": "RBAC-based approval",       # Human-readable
  "node_type": "Answer",               # Question or Answer
  "parent_path": "Q1.A2.Q1",          # Immediate parent
  "depth": 4,                          # Q -> A -> Q -> A = depth 4
  "state": "open",                     # open or closed
  "upvoters": ["Context", "Skeptic"],
  "downvoters": [],
  "created_at": "2025-10-24T...",
  "created_by": "Engineer specialist",
  "phase": 2
}
```

### Specialist Usage

```python
# Create root question (no parent)
@[Graph][Update: Question "What is deployment timeline?"]
→ System: Q1 (assigns next available root Q number)
→ Output: ✓ Q1: "What is deployment timeline?"

# Create answers (parent = last question in context)
@[Graph][Update: Answer "MVP in 4 weeks"]
→ System: Q1.A1 (first answer under Q1)
→ Output: ✓ Q1.A1: "MVP in 4 weeks"

@[Graph][Update: Answer "Full launch in 3 months"]
→ System: Q1.A2 (second answer under Q1)
→ Output: ✓ Q1.A2: "Full launch in 3 months"

# Create follow-up question (specify parent answer)
@[Graph][Update: Question "What MVP features scope?" -> parent: Q1.A1]
→ System: Q1.A1.Q1 (first question under Q1.A1)
→ Output: ✓ Q1.A1.Q1: "What MVP features scope?" (child of Q1.A1)

# Create answers to that follow-up
@[Graph][Update: Answer "Core workflow only" -> parent: Q1.A1.Q1]
→ System: Q1.A1.Q1.A1
→ Output: ✓ Q1.A1.Q1.A1: "Core workflow only"

# Vote on any node by path
@[Graph][Update: Q1.A1 -> vote: relevant, comment: "Realistic timeline"]
@[Graph][Update: Q1.A1.Q1 -> vote: relevant, comment: "Critical for scoping"]
```

### Automatic Context Tracking

```python
class GraphContext:
    """Track current position in graph for convenience."""
    
    def __init__(self):
        self.current_question = None  # e.g., "Q1.A1.Q2"
        self.path_stack = []          # For nested operations
    
    def create_question(self, text, parent=None):
        if parent is None:
            # Root question
            path = self._next_root_id()
        else:
            # Child of an answer node
            path = self._next_child_id(parent, "Q")
        
        self.current_question = path
        return path
    
    def create_answer(self, text, parent=None):
        if parent is None:
            parent = self.current_question  # Use last question
        
        path = self._next_child_id(parent, "A")
        return path
```

### Path Parsing

```python
def parse_path(path: str) -> dict:
    """Parse composite path into components.
    
    Example: "Q1.A2.Q3.A1" →
    {
      'full_path': 'Q1.A2.Q3.A1',
      'segments': ['Q1', 'A2', 'Q3', 'A1'],
      'depth': 4,
      'node_type': 'Answer',  # Last segment is A
      'parent_path': 'Q1.A2.Q3',
      'root': 'Q1'
    }
    """
    segments = path.split('.')
    return {
        'full_path': path,
        'segments': segments,
        'depth': len(segments),
        'node_type': 'Question' if segments[-1].startswith('Q') else 'Answer',
        'parent_path': '.'.join(segments[:-1]) if len(segments) > 1 else None,
        'root': segments[0]
    }

def get_next_id(parent_path: str, node_type: str) -> str:
    """Generate next ID for a node type under a parent.
    
    Examples:
      get_next_id(None, 'Q') → 'Q1' (first root question)
      get_next_id('Q1', 'A') → 'Q1.A1' (first answer to Q1)
      get_next_id('Q1.A1', 'Q') → 'Q1.A1.Q1' (first question under Q1.A1)
    """
    # Query Neo4j for existing children
    if parent_path is None:
        # Count root questions
        count = count_nodes_at_level(None, 'Q')
        return f"Q{count + 1}"
    else:
        # Count children of parent with this type
        count = count_nodes_at_level(parent_path, node_type)
        return f"{parent_path}.{node_type}{count + 1}"
```

## Collision Avoidance Through Scoping

The composite key system naturally encourages specific questions:

### Bad (Vague, Collision-Prone)

```
Q1: "What approach?"
├─ Q1.A1: "Option A"
│  └─ Q1.A1.Q1: "What details?"  ← Too vague!
└─ Q1.A2: "Option B"
   └─ Q1.A2.Q1: "What details?"  ← Same text, but different meaning!
```

While the paths are unique (`Q1.A1.Q1` vs `Q1.A2.Q1`), the text is confusing.

### Good (Specific, Context-Aware)

```
Q1: "What authentication method for internal users?"
├─ Q1.A1: "SSO (Azure AD)"
│  └─ Q1.A1.Q1: "What Azure AD tenant to use?"
└─ Q1.A2: "Magic link (passwordless)"
   └─ Q1.A2.Q1: "What email provider for magic links?"
```

Each question is scoped to its branch context!

## Voting and Selection

### Voting by Path

```python
@[Graph][Update: Q1 -> vote: relevant, comment: "Critical decision"]
@[Graph][Update: Q1.A2 -> vote: relevant, comment: "Best option for MVP"]
@[Graph][Update: Q1.A2.Q1 -> vote: relevant, comment: "Important follow-up"]
```

### Selection Propagation

When user selects an answer, ALL non-selected branches close:

```python
@[Graph][Update: Q1 -> select: Q1.A2]

Automatic effects:
- Q1.A2: marked selected
- Q1: marked answered
- Q1.A1: marked not_applicable (and state → closed)
- Q1.A1.Q1: marked not_applicable (parent closed)
- Q1.A1.Q1.A1: marked not_applicable (ancestor closed)
- Q1.A3: marked not_applicable
- ... (entire non-A2 subtree closes)

Open paths remaining:
- Q1.A2 (selected)
- Q1.A2.Q1 (child of selected)
- Q1.A2.Q1.A1 (grandchild of selected)
- ... (entire A2 subtree stays open)
```

## List Operations

### Show Full Tree

```python
@[Graph][List: all]

Output:
Q1: "What is authentication method?" [👍5] 🔓 OPEN
├─ Q1.A1: "SSO (Azure AD)" [👍3] 🔓 OPEN
│  ├─ Q1.A1.Q1: "What Azure AD tenant?" [👍2] 🔓 OPEN
│  │  ├─ Q1.A1.Q1.A1: "Production tenant" [👍1] 🔓 OPEN
│  │  └─ Q1.A1.Q1.A2: "Separate dev tenant" [👍1] 🔓 OPEN
│  └─ Q1.A1.Q2: "What MFA requirements?" [👍3] 🔓 OPEN
├─ Q1.A2: "Magic link" [👍2] 🔓 OPEN
│  └─ Q1.A2.Q1: "What email provider?" [👍1] 🔓 OPEN
└─ Q1.A3: "Username/password" [👎2] 🔒 CLOSED
   └─ Q1.A3.Q1: "Password policy?" [👎0] 🔒 CLOSED (parent closed)
```

### Show Pending Questions Only

```python
@[Graph][List: pending]

Output:
Pending questions with positive votes (sorted by votes):
1. Q1 [👍5]: "What is authentication method?"
2. Q1.A1.Q2 [👍3]: "What MFA requirements?"
3. Q1.A1.Q1 [👍2]: "What Azure AD tenant?"
```

## Neo4j Visualization

In Neo4j Browser, the composite keys create a beautiful hierarchy:

```cypher
// Show the tree structure
MATCH path = (root:Question)
WHERE NOT exists((root)<-[:CHILD_OF]-())
OPTIONAL MATCH (root)-[:CHILD_OF*]->(child)
RETURN root, child
```

Each node displays its full path, making the context chain visible!

## Migration from Flat IDs

If we already have flat IDs in use:

```python
# Old way (flat)
Q1, Q2, Q3, A1, A2, A3...

# New way (composite)
Q1, Q1.A1, Q1.A1.Q1, Q1.A2, Q2...

# Migration: Prefix all old flat IDs with "FLAT-"
# Then rebuild into composite structure
```

## Summary

**Composite keys = Context retention + Collision prevention + Natural scoping**

- **Path is identity**: `Q1.A2.Q1.A1` uniquely identifies a node AND its context
- **LLM-friendly**: Full decision chain visible in every path
- **Enforces clarity**: Specialists write scoped questions naturally
- **Clean visualization**: Neo4j shows true hierarchical structure
- **Auto-pruning**: Selecting an answer closes entire non-selected subtrees

The tradeoff (longer IDs) is worth it for the structural clarity and context preservation!

