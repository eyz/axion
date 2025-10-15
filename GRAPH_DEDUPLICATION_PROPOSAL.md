# Graph Semantic Deduplication Proposal

## Problem Statement

During multi-agent discussions, specialists may propose semantically similar or duplicate questions/answers using different wording. For example:

```
[Q:single][What emergency authorization limit should sitter have?]
  [A][No authorization - must reach owner first]        (3 upvotes)
  [A][No authorization -- must reach owner first]       (1 upvote)  ← Duplicate
```

These duplicates fragment the decision tree and dilute voting signals, making it harder for the User to see the actual consensus.

## Proposed Solution: Chair-Directed Cleanup

### Core Concept

**Key insight:** The Chair already reviews all specialist proposals and synthesizes consensus. This makes them the perfect arbiter for identifying and marking duplicate graph updates.

**Human-in-the-loop workflow:**
1. **Specialists propose answers** → Graph accumulates nodes (may include duplicates)
2. **Chair reviews graph** → Identifies duplicate paths using human judgment
3. **Chair marks duplicates** → Uses cleanup emoji (🧹) on the newer/less-voted duplicate
4. **Web UI hides cleaned nodes** → User only sees canonical paths (like clicking X, but no downvote)
5. **Votes remain on canonical** → The better-voted path keeps all its votes

**Why Chair is the perfect arbiter:**
- Already has full context of the discussion
- Understands subtle differences vs true duplicates
- Can judge domain-specific nuances (numbers, negations, requirements vs preferences)
- Natural part of Chair's synthesis role
- No false positives from automated similarity

### When Deduplication Runs

**Critical: Deduplication happens BEFORE graph updates reach the Web UI**

The user should never see duplicate paths. Deduplication is a backend preprocessing step that runs:

**Automatic trigger points:**
1. **After each specialist phase completes** - Before sending graph update to UI
2. **After Chair synthesizes** - Before final graph state is pushed
3. **On initial graph load** - When user first opens session

**Where it happens:**
- In `axion_swarm/graph.py` - before `emit_graph_update()` websocket call
- Transparent to specialists and user
- No `@[Graph][Update][🧹]` messages needed - it's invisible

### Embedding Strategy

**Full path embedding - the complete decision chain:**

```python
# Example path:
# [Q:single][What is access method?][A][Smart-lock code][Q:single][When to revoke?][A][Immediately at trip end]

path_text = " | ".join([
    "What is access method?",    # Q1
    "Smart-lock code",            # A1  
    "When to revoke?",            # Q2
    "Immediately at trip end"     # A2
])

embedding = model.encode(path_text)
# Result: Single vector representing the ENTIRE semantic concept
```

**Why embed the complete path?**
- The semantic meaning is in the full decision chain, not isolated pieces
- "Immediately" has different meaning under different parent contexts
- Two paths with different question wording but same intent should match
- Prevents comparing unrelated answers from different branches

**Examples of duplicate paths:**

| Path A | Path B | Semantic Match? |
|--------|--------|-----------------|
| `[Q][What authorization?] → [A][No authorization - call owner]` | `[Q][What authorization limit?] → [A][Must reach owner first]` | ✅ Yes (0.89 similarity) |
| `[Q][What authorization?] → [A][$250 limit]` | `[Q][What authorization?] → [A][$250 emergency cap]` | ✅ Yes (0.92 similarity) |
| `[Q][What authorization?] → [A][$250]` | `[Q][What authorization?] → [A][$500]` | ❌ No (different values) |

**Embedding model:**
- Use OpenAI `text-embedding-3-small` (1536-dim, fast, cost-effective)
- Alternative: `text-embedding-3-large` (3072-dim, more accurate but pricier)
- Cost: ~$0.02 per 1M tokens (very cheap - entire session might be $0.001)

**Why OpenAI embeddings?**
- Already using OpenAI API for LLM calls
- No additional dependencies or model downloads
- High quality semantic understanding
- Same API infrastructure

### Similarity Detection

**Cosine similarity thresholds:**
- `>= 0.95`: Exact duplicates (typo variations, punctuation differences)
- `>= 0.85`: Semantic duplicates (paraphrases, rewordings)
- `< 0.85`: Distinct answers (keep both)

**Examples:**

| Answer A | Answer B | Similarity | Action |
|----------|----------|------------|--------|
| "No authorization - call first" | "No authorization -- call first" | 0.98 | Merge |
| "$250 spending limit" | "$250 emergency authorization" | 0.89 | Merge |
| "$250 spending limit" | "$500 spending limit" | 0.75 | Keep both |
| "Provide references" | "Submit background check" | 0.42 | Keep both |

### Duplicate Resolution Algorithm

**Step 1: Identify duplicate path clusters**
```python
def find_duplicate_path_clusters(leaf_paths, threshold=0.85):
    """
    Group semantically similar complete paths.
    
    Args:
        leaf_paths: List of complete paths like:
                   "[Q][What?][A][Answer1]"
                   "[Q][What?][A][Answer1][Q][When?][A][Now]"
    """
    # Compute embedding for each complete path
    embeddings = []
    for path in leaf_paths:
        # Extract all Q and A text from path
        path_components = extract_path_components(path)
        # Join as: "Q1 text | A1 text | Q2 text | A2 text | ..."
        path_text = " | ".join(path_components)
        embedding = model.encode(path_text)
        embeddings.append(embedding)
    
    # Compute cosine similarity matrix
    similarity_matrix = cosine_similarity(embeddings)
    
    # Union-find to cluster similar paths
    clusters = []
    for i in range(len(leaf_paths)):
        for j in range(i+1, len(leaf_paths)):
            if similarity_matrix[i][j] >= threshold:
                merge_into_cluster(clusters, i, j)
    
    return clusters
```

**Step 2: Select canonical path per cluster**
```python
def select_canonical_path(cluster_paths, graph):
    """
    Keep path with highest total vote activity.
    
    Vote activity = sum of all votes on ALL nodes in this path
    (not just the leaf answer, but all intermediate answers too)
    """
    def total_vote_activity(path):
        activity = 0
        # Walk through path, count votes on each node
        for node_path in get_all_nodes_in_path(path):
            node = graph.nodes[node_path]
            upvotes = len([v for v in node.votes if v.vote == '👍'])
            downvotes = len([v for v in node.votes if v.vote == '👎'])
            rejects = len([v for v in node.votes if v.vote == '❌'])
            activity += upvotes + downvotes + rejects
        return activity
    
    return max(cluster_paths, key=total_vote_activity)
```

**Why total activity instead of net score?**
- Net score = 5 could be (5 up, 0 down) or (10 up, 5 down)
- The latter has more engagement and discussion
- Preserves the answer that specialists actually debated

**Step 3: Merge paths - transfer all content and references**
```python
def merge_duplicate_paths(canonical_path, duplicate_path, graph):
    """
    Transfer all content from duplicate path to canonical path.
    
    What gets merged:
    1. All votes (👍, 👎, ❌) with full attribution
    2. All nested questions/answers under this path
    3. User selections pointing to duplicate path
    4. Conversation references (if any specialist mentioned this path)
    """
    canonical_node = graph.nodes[canonical_path]
    duplicate_node = graph.nodes[duplicate_path]
    
    # 1. Transfer all votes (preserve specialist attribution and timestamps)
    for vote in duplicate_node.votes:
        canonical_node.votes.append(vote)
    
    # 2. Transfer nested content
    # Find all child paths starting with duplicate_path
    for child_path in graph.nodes.keys():
        if child_path.startswith(duplicate_path + "["):
            # Remap child to be under canonical path
            new_child_path = canonical_path + child_path[len(duplicate_path):]
            graph.nodes[new_child_path] = graph.nodes[child_path]
            del graph.nodes[child_path]
    
    # 3. Update user selections
    for question_path, selection in user_selections.items():
        if isinstance(selection['answers'], list):
            # Multiple choice - update any references
            selection['answers'] = [
                canonical_path if ans == duplicate_path else ans
                for ans in selection['answers']
            ]
        elif selection['answers'] == duplicate_path:
            # Single choice - redirect to canonical
            selection['answers'] = canonical_path
    
    # 4. Mark duplicate path for deletion
    graph.nodes[duplicate_path].status = 'merged_into'
    graph.nodes[duplicate_path].merged_into = canonical_path
    
    # 5. Emit cleanup directive
    emit_cleanup_directive(duplicate_path, canonical_path)
```

### Logging and Transparency

**Backend logs (for debugging):**
```
[DEDUP] Found 2 duplicate path clusters
[DEDUP] Cluster 1 (similarity=0.91):
  - KEEP: [Q:single][What authorization?][A][No authorization - must reach owner first] (5 votes)
  - MERGE: [Q:single][What authorization limit?][A][Must reach owner first] (2 votes)
[DEDUP] Merged 2 votes into canonical path
[DEDUP] Final canonical path has 7 total votes (5👍 + 2👍)
```

**User-facing: No visible indication**
- User sees only canonical paths
- Vote counts reflect merged totals
- No "merged from N duplicates" badges (keeps UI clean)
- If needed later, can add optional debug view

**Specialist-facing: Transparent**
- Specialists continue proposing naturally
- Don't need to worry about duplicates
- Graph stays clean automatically

### Backend Implementation

**New module: `axion_swarm/graph_dedup.py`**

```python
from openai import OpenAI
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np

class GraphDeduplicator:
    def __init__(self, similarity_threshold=0.85):
        self.client = OpenAI()  # Uses same API key as rest of system
        self.embedding_model = "text-embedding-3-small"
        self.threshold = similarity_threshold
    
    def deduplicate_leaf_paths(self, graph_nodes):
        """
        Find and merge semantically duplicate complete paths in the graph.
        
        Args:
            graph_nodes: Dict of {path: node} for entire graph
        
        Returns:
            List of cleanup directives: [(dup_path, canonical_path, similarity), ...]
        """
        # Find all leaf paths (paths ending in answers with no nested questions)
        leaf_paths = self._find_leaf_paths(graph_nodes)
        
        if len(leaf_paths) < 2:
            return []  # Nothing to deduplicate
        
        # Group by depth (only compare paths of same depth)
        paths_by_depth = {}
        for path in leaf_paths:
            depth = path.count('[Q:') + path.count('[Q]')
            if depth not in paths_by_depth:
                paths_by_depth[depth] = []
            paths_by_depth[depth].append(path)
        
        cleanup_directives = []
        
        # Deduplicate within each depth level
        for depth, paths in paths_by_depth.items():
            if len(paths) < 2:
                continue
            
            # Compute embeddings for complete paths
            path_texts = [self._extract_full_path_text(path) for path in paths]
            embeddings = self._get_embeddings_batch(path_texts)
            
            # Find duplicate clusters
            clusters = self._find_clusters(paths, embeddings)
            
            # For each cluster, select canonical and create merge directives
            for cluster in clusters:
                if len(cluster) < 2:
                    continue  # No duplicates
                
                canonical = self._select_canonical_path(cluster, graph_nodes)
                duplicates = [p for p in cluster if p != canonical]
                
                for dup_path in duplicates:
                    dup_idx = paths.index(dup_path)
                    can_idx = paths.index(canonical)
                    similarity = cosine_similarity(
                        [embeddings[dup_idx]], 
                        [embeddings[can_idx]]
                    )[0][0]
                    
                    cleanup_directives.append({
                        'duplicate': dup_path,
                        'canonical': canonical,
                        'similarity': similarity
                    })
        
        return cleanup_directives
    
    def _find_leaf_paths(self, graph_nodes):
        """Find all paths that end in answers (no nested questions)."""
        leaf_paths = []
        for path in graph_nodes.keys():
            # Check if this is an answer path
            if '[A]' not in path and '[A:' not in path:
                continue
            # Check if no other path starts with this path + "[Q"
            is_leaf = True
            for other_path in graph_nodes.keys():
                if other_path.startswith(path + '[Q'):
                    is_leaf = False
                    break
            if is_leaf:
                leaf_paths.append(path)
        return leaf_paths
    
    def _get_embeddings_batch(self, texts):
        """
        Get embeddings for a batch of texts using OpenAI API.
        Batch processing is more efficient than individual calls.
        """
        response = self.client.embeddings.create(
            model=self.embedding_model,
            input=texts
        )
        # Extract embeddings in order
        embeddings = [item.embedding for item in response.data]
        return np.array(embeddings)
    
    def _extract_full_path_text(self, path):
        """
        Extract all Q and A text from a complete path.
        
        Example:
        "[Q:single][What access?][A][Smart-lock][Q:single][When revoke?][A][Immediately]"
        -> "What access? | Smart-lock | When revoke? | Immediately"
        """
        components = []
        # Parse path and extract text from [Q:type][text] and [A][text]
        # ... regex parsing ...
        return " | ".join(components)
    
    def _find_clusters(self, paths, embeddings):
        """Use cosine similarity + union-find to cluster duplicates."""
        similarity_matrix = cosine_similarity(embeddings)
        # ... union-find implementation ...
    
    def _select_canonical_path(self, cluster_paths, graph_nodes):
        """Select path with most total vote activity across all nodes."""
        def total_vote_activity(path):
            # Count votes on all nodes in this path
            activity = 0
            # Walk through each node in the path
            # ... count votes ...
            return activity
        
        return max(cluster_paths, key=total_vote_activity)
```

**Integration point: `axion_swarm/graph.py`**

Hook into the graph update emission pipeline:

```python
def emit_graph_update(session_id: str, graph_nodes: dict):
    """
    Send graph update to web UI via websocket.
    
    NOW WITH DEDUPLICATION:
    1. Run deduplication on graph_nodes
    2. Merge duplicate paths silently
    3. Send clean graph to UI
    """
    # Deduplicate before sending to UI
    deduplicator = GraphDeduplicator(similarity_threshold=0.85)
    cleanup_directives = deduplicator.deduplicate_leaf_paths(graph_nodes)
    
    # Apply all merges
    for directive in cleanup_directives:
        merge_duplicate_paths(
            canonical_path=directive['canonical'],
            duplicate_path=directive['duplicate'],
            graph=graph_nodes
        )
        
        # Log for debugging
        logger.info(
            f"[DEDUP] Merged duplicate path (similarity={directive['similarity']:.2f}): "
            f"{directive['duplicate']} → {directive['canonical']}"
        )
    
    # Remove merged (now-empty) duplicate nodes
    graph_nodes = {
        path: node for path, node in graph_nodes.items()
        if not (hasattr(node, 'status') and node.status == 'merged_into')
    }
    
    # Send clean graph to UI
    websocket_manager.send_to_session(session_id, {
        'type': 'graph_update',
        'nodes': graph_nodes
    })
    
    if cleanup_directives:
        logger.info(f"[DEDUP] Merged {len(cleanup_directives)} duplicate path(s)")
```

**Alternative: Dedicated preprocessing step**

If we want to run deduplication separately (e.g., for testing):

```python
def preprocess_graph_for_ui(graph_nodes: dict) -> dict:
    """
    Preprocess graph before sending to UI.
    Currently: deduplication only.
    Future: could add other preprocessing steps.
    """
    deduplicator = GraphDeduplicator(similarity_threshold=0.85)
    cleanup_directives = deduplicator.deduplicate_leaf_paths(graph_nodes)
    
    for directive in cleanup_directives:
        merge_duplicate_paths(
            canonical_path=directive['canonical'],
            duplicate_path=directive['duplicate'],
            graph=graph_nodes
        )
    
    # Remove merged nodes
    return {
        path: node for path, node in graph_nodes.items()
        if not (hasattr(node, 'status') and node.status == 'merged_into')
    }

# Usage:
def emit_graph_update(session_id: str, graph_nodes: dict):
    clean_graph = preprocess_graph_for_ui(graph_nodes)
    websocket_manager.send_to_session(session_id, {
        'type': 'graph_update',
        'nodes': clean_graph
    })
```

### User Interface Implications

**Web UI changes: MINIMAL (it just works!)**

Since deduplication happens in the backend before graph updates reach the UI:

1. **No UI changes required** - User just sees clean graph
2. **Vote counts are already merged** - No special handling needed
3. **User selections work normally** - Backend already remapped paths
4. **No "merged" badges or indicators** - Keeps UI simple and clean

**Optional future enhancements:**

1. **Debug view (for admins):**
   - Show which paths were merged
   - Display similarity scores
   - View merge history

2. **Manual merge tool (advanced users):**
   - Drag-and-drop to merge paths
   - Backend applies same merge logic
   - Useful if automatic deduplication misses something

3. **Undo merges (edge cases):**
   - If automatic merge was incorrect
   - Admin can split paths back apart
   - Restore original vote attribution

### Edge Cases and Considerations

**1. Nested content under duplicates**

If duplicates have nested questions:
```
[A][Phased approach] (5 votes)
  [Q][What are phases?]
    [A][Stage 1, 2, 3]

[A][Phased implementation] (2 votes)  ← Duplicate
  [Q][What are the stages?]
    [A][Three stages]
```

**Resolution:**
- Merge both nested questions under canonical answer
- Keep both nested questions even if they're similar (user already made choices)
- Happens silently - user just sees consolidated tree

**2. User has selected a duplicate**

If User selected a duplicate that gets merged:
```
User selected: [A][No authorization -- must reach owner first]
Canonical kept: [A][No authorization - must reach owner first]
```

**Resolution:**
- Backend automatically updates `userSelections` to point to canonical (see Step 3 in merge algorithm)
- User's choice is preserved semantically
- No notice needed - happens silently
- When user reloads page, their selection appears on the canonical path

**3. False positives (similar but distinct)**

```
[A][$250 spending limit]
[A][$300 spending limit]  ← Similar embedding but distinct values!
```

**Prevention:**
- Lower threshold to 0.85 (catches paraphrases, not semantic variations)
- Whitelist patterns that should never merge:
  - Numeric values: `$250` vs `$300`
  - Ranges: `10-20 minutes` vs `20-30 minutes`
  - Negations: `Yes` vs `No`, `Allow` vs `Prohibit`

```python
def should_skip_merge(answer_a, answer_b):
    """Prevent merging answers with critical differences."""
    # Extract numbers
    nums_a = extract_numbers(answer_a)
    nums_b = extract_numbers(answer_b)
    if nums_a != nums_b and (nums_a or nums_b):
        return True  # Different numeric values
    
    # Check for negations
    if has_negation(answer_a) != has_negation(answer_b):
        return True  # One is negated, other isn't
    
    return False
```

**4. Timing: When to run deduplication**

**Option A: After each phase (RECOMMENDED)**
- Pro: Keeps graph clean continuously
- Pro: Prevents vote fragmentation from accumulating
- Con: Slight processing overhead

**Option B: On-demand only**
- Pro: No performance impact
- Con: Duplicates accumulate, harder to merge later

**Recommendation:** Run after Phase 2 and beyond (not Phase 1)
- Phase 1: Let specialists explore freely
- Phase 2+: Start consolidating as patterns emerge

### Configuration

**New config options in `config.py`:**

```python
# Graph deduplication settings
ENABLE_DEDUPLICATION = True
DEDUP_SIMILARITY_THRESHOLD = 0.85  # 0.0 to 1.0
DEDUP_MIN_ANSWERS = 3  # Only dedupe if 3+ answers exist
DEDUP_SKIP_PHASE_1 = True  # Let Phase 1 explore freely
DEDUP_NUMERIC_TOLERANCE = 0.05  # 5% difference prevents merge
```

### Rollout Plan

**Phase 1: Foundation (Week 1)**
- Implement `GraphDeduplicator` class with OpenAI embeddings
- Add batch embedding computation
- Write unit tests with known duplicate pairs
- Dependencies: `openai`, `scikit-learn`, `numpy` (already in use)

**Phase 2: Integration (Week 2)**
- Hook deduplication into `emit_graph_update()` pipeline
- Add backend logging for merge tracking
- Test on pet sitter scenario
- Monitor embedding API costs (should be minimal)

**Phase 3: Safety (Week 3)**
- Add false-positive prevention (numbers, negations)
- Tune similarity thresholds based on real data
- Add config flags for gradual rollout
- Test with edge cases (nested content, user selections)

**Phase 4: Polish (Week 4)**
- Optimize batch processing for large graphs
- Add optional debug view in UI
- Performance tuning (cache embeddings if needed)
- Document merge behavior for users

### Metrics to Track

**Effectiveness:**
- Number of merges per session
- Average similarity score of merged pairs
- Vote consolidation (total votes before/after)
- Graph size reduction (nodes before/after deduplication)

**Quality:**
- False positive rate (incorrect merges)
- False negative rate (obvious duplicates missed)
- User feedback on merge decisions

**Performance:**
- Embedding API latency (should be <1s for typical session)
- Embedding API cost per session (target: <$0.01)
- Total deduplication processing time

### Alternative Approaches Considered

**1. Fuzzy string matching (Levenshtein distance)**
- ❌ Only catches typos, not semantic paraphrases
- ❌ "No authorization - call first" vs "Must reach owner first" = low match

**2. LLM-based comparison**
- ✅ Most accurate semantic understanding
- ❌ Too slow (100ms+ per pair)
- ❌ Expensive (API costs)
- Use case: Manual review of borderline cases (0.75-0.85 similarity)

**3. Specialist voting on merges**
- ✅ Human-in-the-loop validation
- ❌ Adds friction to workflow
- ❌ Slows down discussion
- Use case: Controversial merges only (when votes are close)

### Open Questions

1. **Should we deduplicate questions too, or just complete paths?**
   - Currently: Only leaf paths (complete Q→A→Q→A chains)
   - Could extend to: Questions with same wording at same level
   - Recommendation: Start with leaf paths only, expand later if needed

2. **What if canonical path is downvoted and duplicate is upvoted?**
   - Current rule: Keep most total activity (up + down + reject)
   - Alternative: Keep highest net score (up - down - reject)
   - Trade-off: Activity = engagement, Net = approval
   - Recommendation: Use activity, but add config option

3. **Should deduplication run during active session?**
   - Option A: Only deduplicate between phases (current proposal)
   - Option B: Continuously deduplicate in real-time
   - Trade-off: Real-time is smoother, but more processing overhead
   - Recommendation: Start with per-phase, optimize to real-time later

4. **How to handle deduplication if User is actively viewing?**
   - If user is looking at path A and it gets merged to path B
   - Backend could notify UI to redirect focus
   - Or: Skip deduplication if user has that path open
   - Recommendation: Just merge silently - user refresh shows clean graph

### Success Criteria

This feature is successful if:

1. ✅ Reduces duplicate answers by 40%+ in typical sessions
2. ✅ False positive rate < 5% (user undoes merge)
3. ✅ Vote consolidation improves consensus clarity
4. ✅ No user complaints about losing their selections
5. ✅ Processing overhead < 500ms per phase

---

**Proposal Status:** Draft for review  
**Author:** AI Assistant  
**Date:** 2025-11-01  
**Next Steps:** Review with team, prototype `GraphDeduplicator` class

