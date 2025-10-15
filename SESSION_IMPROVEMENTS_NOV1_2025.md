# Session Improvements - November 1, 2025 (Evening)

## Overview

Major improvements to graph de-duplication, Web UI functionality, and architectural evolution toward graph-native user interaction.

## 1. De-Duplication System Fixes

### Prompt Structure Redesign
**Problem:** Chair was responding conversationally instead of de-duplicating, even with pure graph schema input.

**Solution:** Restructured `CHAIR_DEDUPE_PASS_SYSTEM` prompt with proper ordering:
```
1. Context: WHO YOU ARE (role definition)
2. Requirements: WHAT YOU MUST DO (task rules)
3. Graph Context: THE DATA (comparison rules)
4. Expectations: OUTPUT FORMAT (command syntax)
5. Data Input: GRAPH PATHS (the actual data)
```

**Key Changes:**
- System instructions FIRST (establishes mode/role)
- User data LAST (prevents contamination)
- Multiple task resets before output
- Explicit "DATA STRUCTURES to analyze, NOT questions to answer"
- Removed all user natural language context (pure graph schema only)

**Files:** `axion_swarm/prompts.py` (lines 2979-3110), `axion_swarm/agents.py` (lines 3380-3408)

### Chair Duplicate Marking Syntax
**Problem:** Chair marking same path as duplicate of itself (wrong canonical selection).

**Solution:** Added explicit examples:
```
CRITICAL: The duplicate and canonical must be DIFFERENT paths!
If item 1 and item 14 are duplicates, mark item 14 (newer) as duplicate of item 1 (older):
@[Graph][Update][item_14_path][🧹][item_1_path]
```

**Files:** `axion_swarm/prompts.py` (lines 3053-3059)

### UnboundLocalError Fix
**Problem:** Local `import re` statements inside functions shadowing global import, causing `UnboundLocalError` at line 3066.

**Solution:** Removed all unnecessary local `import re` at lines 528, 1892, 1944, 3469.

**Files:** `axion_swarm/agents.py`

### Auto-Clear User Selections
**Problem:** When Chair marks duplicates, user's prior selections on those paths should be neutralized.

**Solution:** 
- After writing duplicate marker to graph.log, check if user selected that path
- Write `@[Graph][Update][duplicate_path][➖][Auto-cleared...]` as **User (Web UI)**
- Appears as user action in the room (not system message)

**Files:** `axion_swarm/graph_tool.py` (lines 507-532)

## 2. Web UI Enhancements

### Hide Duplicates Toggle (Finally Working!)
**Problem:** Toggle existed but didn't hide anything.

**Root Causes:**
1. `voteTally` prop missing from QuestionNode
2. Props not exposed in App.vue return statement
3. Double-toggle from event bubbling

**Solutions:**
- Added `voteTally` prop to QuestionNode and passed recursively
- Exposed `hideDuplicates` and `toggleHideDuplicates` in return statement
- Fixed event propagation with `@click.prevent` and `@click.stop`
- Filters duplicates in `directAnswers`, `getFollowUpQuestions`, and `rootQuestions`

**Files:** 
- `web/src/components/QuestionNode.vue` (lines 329-332, 367-372, 541-543, 672-674)
- `web/src/App.vue` (lines 333-337, 340-354, 1569, 1617)

**Behavior:** 
- Default: ON (duplicates hidden by default)
- Toggle OFF: Shows duplicates with visual styling
- Toggle ON: Completely removes duplicates from DOM

### Duplicate Visual Styling
**Improvements:**
- Opacity: `0.85` (was 0.35 - much more readable)
- Background: `#e8edf2` (lighter gray)
- Filter: `brightness(0.75)` (darkens instead of grayscale wash)
- Strike-through: Only on text content (not emoji/badges)
- Text color: `#4a5568` (darker, readable)
- Tooltips: Work on hover (show canonical path)

**Files:** `web/src/components/QuestionNode.vue` (lines 1783-1816)

### Viewport Freezing
**Problem:** New nodes appearing while user viewing that section, causing jarring changes.

**Solution:**
- **Answer-level:** When question in viewport, freeze answer list (no new answers added)
- **Root question-level:** When any root question in viewport, freeze root question order
- Separate `rootQuestions` (source) from `displayedRootQuestions` (what renders)
- Emits viewport change events from QuestionNode to App.vue

**Files:**
- `web/src/App.vue` (lines 340-406)
- `web/src/components/QuestionNode.vue` (lines 549-555, 1095-1109)

**Behavior:**
- Nodes only appear when section is off-screen
- When you scroll back, new nodes become visible
- Prevents UI changes in your current view

### Thought Submission Marks as Seen
**Feature:** Adding a thought to a question/answer marks it as "seen" (decrements NEW badge).

**Files:** `web/src/App.vue` (lines 728-756)

**Note:** Code already existed, added debug logging for verification.

## 3. Prompt & Architecture Improvements

### Deprecated @[User] Prose Questions
**Major Shift:** User interaction moving from prose chat to graph-only.

**Changes:**
- Marked `@[User]` as **DEPRECATED** throughout prompts
- All user questions must be `@[Graph][Create]` nodes with answer options
- Updated all examples to show graph pattern instead of prose
- Removed `@[User]` from audience marker examples

**Rationale:**
- Chat interface going away, Web UI is primary
- Graph provides structured, clickable decisions
- Reduces token usage (graph syntax more compact than prose)
- Single unified knowledge graph

**Files:** `axion_swarm/prompts.py` (lines 753, 1410, 1418, 1709, 1760-1765, 1819-1839)

### Strengthened Anti-Echo Warnings
**Problem:** Specialists creating questions that just restate user's original question.

**Solution:** Much stronger language:
- "**NEVER** ECHO/RESTATE (VALIDATION ENFORCED)"
- "**FORBIDDEN**: User asks 'How should I approach [topic]?' → You create same"
- "This is LITERALLY RESTATING - adds zero value"
- "**If your question sounds like user's → DELETE IT**"
- Domain-agnostic examples (no pet sitter contamination)

**Files:** `axion_swarm/prompts.py` (lines 757-770)

### Balanced Create Encouragement
**Problem:** Too restrictive warnings made specialists afraid to create new paths.

**Solution:** Rebalanced messaging:
- "**Actively propose** new questions/answers from YOUR domain"
- "Before creating, do a **quick check**" (not exhaustive analysis)
- "**Don't hesitate** to create genuinely new ones"

**Files:** `axion_swarm/prompts.py` (lines 775-783)

### 400 Error Graceful Handling
**Problem:** BadRequestError crashes entire phase.

**Solution:** 
- Return synthetic "pass" message instead of raising
- Specialist posts: "@[All] I encountered a content policy issue..."
- Other specialists continue normally
- Error logged to 400s.log for analysis

**Files:** `axion_swarm/agents.py` (lines 1681-1703)

## 4. Key Architectural Direction

### Graph-Native User Interaction
The system is evolving toward **graph-only** user interaction:

**Before:**
- Mixed interface: Specialists ask "@[User], what is X?" in prose
- User might not see it (buried in conversation)
- Two interaction paths to maintain

**After:**
- Pure graph: Specialists create `@[Graph][Create][Q:single][What is X?][A][Option 1]`
- User sees clickable UI element
- Single unified knowledge graph
- Token-efficient structured data

**Benefits:**
1. Reduced tokens (graph syntax compact)
2. Better UX (click/select vs read/type)
3. Unified interface (everything through graph)
4. Searchable/queryable (structured nodes)
5. Persistent across context windows

## Files Modified

### Core System
- `axion_swarm/prompts.py` - De-dupe prompt restructure, @[User] deprecation, anti-echo strengthening
- `axion_swarm/agents.py` - De-dupe data ordering, UnboundLocalError fix, 400 handling, user context removal
- `axion_swarm/graph_tool.py` - Auto-clear duplicate selections

### Web UI
- `web/src/App.vue` - Hide duplicates toggle, viewport freezing, reactive state fixes
- `web/src/components/QuestionNode.vue` - Duplicate filtering, styling improvements, voteTally prop

## Performance Impact

- **De-duplication:** More consistent (Chair stays in task mode)
- **Web UI:** Smoother (no jarring changes in viewport)
- **Token usage:** Lower (graph syntax vs prose questions)
- **Error handling:** Robust (400s don't crash)

## Testing Status

All features tested and confirmed working:
- ✅ Hide Duplicates toggle hides/shows correctly
- ✅ Duplicates auto-clear user selections  
- ✅ Viewport freezing prevents jarring updates
- ✅ Duplicate styling readable and visually distinct
- ✅ Chair de-dupe prompt structure improved
- ✅ 400 errors continue gracefully
- ✅ Specialists encouraged to create new paths

