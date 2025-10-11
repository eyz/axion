# Axion Swarm - Architecture Documentation

## Project Overview

Axion Swarm is a multi-agent discussion system using LangGraph where specialized AI agents collaborate through multiple phases to provide comprehensive answers to user questions. Each agent has complete isolation with fresh LLM instances per invocation, seeing only what's explicitly shared in the public discussion.

**Ideal Use Cases**: Complex multi-domain questions where different specialists contribute independent expertise—architecture decisions, team planning, technical assessments, compliance strategies. The system excels when the answer requires multiple perspectives that benefit from cross-pollination (Phase 2) before converging into a synthesized recommendation (Chair's final output).

### Project Goal: Natural Human-Like Expert Discussion

**Primary Goal**: Create natural, human-like conversations that feel like real expert collaboration.

**Acceptance Criteria**:
1. **Clear Personas**: Specialists have easy-to-define personas with distinct expertise
2. **Natural Transcript**: The chat transcript (what specialists share) reads naturally and feels human, not robotic or academic
3. **Deep Thinking**: Specialists think deeply using native reasoning (GPT-5) or `<think>` tags (other models), showing thorough expert analysis
4. **Expert Advisory Dynamic**: The conversation feels like a supportive CEO consulting with their expert advisory panel

**Design Philosophy**:
- User is the client - specialists exist to support the User's success
- Specialists work collectively while thinking independently
- Professional but conversational tone, with good rapport
- Answer with stated assumptions rather than blocking on perfect information

### The Fundamental Model: Internal Expert Team with Async Collaboration

**User Pattern:**
The User asks a question and typically won't respond for hours or days (minimum 3 hours, average 1.5 days). However, **the system fully supports ongoing User participation**—Users can respond at any phase, clarify requirements, answer specialist questions, or provide additional context. The async pattern is the **expected default**, but synchronous collaboration is fully supported when User is available.

**Conversation Duration (Empirical)**: In real-world async collaboration (observed across engineering teams, support contexts, and distributed work), conversations typically span **0.75 hours to 1.2 weeks** and may never formally "end" - ongoing collaboration with multiple rounds of internal deliberation and User input. Each internal deliberation round completes in <1 minute, then system waits for User's next input (3h-1.5d typical gap).

**Team Model:**
The User doesn't see the multi-phase specialist discussion—this is **internal team collaboration**. Think of it like a distributed expert team working together while the client is away:

- **Specialists speak candidly** - User only sees Chair's final synthesis, so specialists can flag concerns, debate approaches, and challenge assumptions openly during internal discussion
- **Autonomous operation** - Team must deliver complete answers without synchronous user interaction, using @[Search] for current information and making well-stated assumptions about gaps
- **Iterative social context** - Each phase builds collective understanding, not just sequential individual contributions
- **Progressive convergence** - Multiple phases let the team refine toward the best answer through cross-pollination and iteration

**Why This Architecture:**

This async collaboration pattern drives key architectural decisions:

1. **@[Search] tool is essential** - Specialists need current information without waiting for User to provide it
2. **"Answer with stated assumptions" is mandatory** - Can't block waiting for perfect information when User is away for days
3. **Phase-gated visibility prevents groupthink** - Phase 1 independent perspectives establish baseline before Phase 2 cross-pollination
4. **Chair synthesizes for User** - Specialists do thorough internal analysis, Chair translates into customer-facing response
5. **Convergence detection is necessary** - **Because specialists must be autonomous until User responds (minimum 3h, average 1.5d), Chair gradually moves discussion toward final round**. System can't wait indefinitely for User input, so Chair's stagnation detection recognizes when internal team has reached consensus and triggers final synthesis. This ensures User gets a complete answer when they return, rather than an incomplete discussion. **Critical trade-off**: End too early and miss insights that could re-engage User attention; end too late and waste resources on repetitive discussion. The equation infers "most likely" end of current interaction round while recognizing that compelling new insights may bring User back for another round.

**Phases Build Shared Context:**

This isn't specialists contributing once and being done—it's **iterative collective learning**:

- **Phase 1**: Individual perspectives establish baseline (no groupthink, complete isolation)
- **Phase 2**: Specialists SEE what others contributed, use that to refine thinking (cross-pollination creates shared understanding)
- **Phase 3+**: Team converges through refinement, each phase adding to collective knowledge
- **Passing means team consensus**, not personal exhaustion—when discussion plateaus collectively, that's convergence

**Result:** Comprehensive, well-reasoned answers that synthesize multiple expert perspectives, delivered while User is away.

### How the Architecture Supports Collaborative User Participation

While the async pattern (User away for hours/days) is the expected default, the architecture **fully supports ongoing User collaboration** at any phase:

**1. User Can Speak at Any Phase:**
- User input is accepted at Phase 1, 2, 3+, or even during Final Phase
- No "conversation locked" state - discussion remains open until explicit conclusion
- Specialists see User messages immediately in next phase (User messages always visible, never filtered)

**2. Specialists Actively Invite User Clarification:**
- Specialists use `@[User]` to ask clarifying questions throughout discussion
- Questions appear at end of specialist messages: "Analysis... @[User], what is your [specific detail]?"
- This creates natural invitation for User to provide additional context

**3. User Input Resets Convergence:**
- If User speaks during Phase 3+ or Final Phase, system reverts to active discussion mode
- Final Phase is **invalidated** by new User input (specialists cannot conclude while User has unaddressed concerns)
- Stagnation detection recognizes recent User engagement as justification signal (discussion should continue)
- System never "closes" discussion while User is actively participating

**4. Checkpoint System Enables Pause/Resume:**
- Discussion can be paused after any phase (automatic checkpoint save)
- User can respond hours or days later, discussion resumes from checkpoint
- Supports natural async collaboration pattern without forcing synchronous participation

**5. Progressive Interaction Pattern:**
- Phase 1-2: Specialists establish baseline understanding (may ask initial clarifying questions)
- Phase 3+: User can provide clarification, specialists refine based on new information
- **Multiple phases between User input and Chair response**: When User contributes, specialists may discuss internally for several phases (N, N+1, N+2...) before Chair synthesizes back to User with team's refined thinking
- Iteration continues until User is satisfied or all specialists pass (implicit consensus)
- Chair synthesis incorporates all User input throughout discussion

**Implementation:**
- User messages tagged with `<from>User</from>` in conversation history
- Phase system treats User input as priority signal (never filtered, always visible)
- Convergence logic explicitly checks for User engagement before triggering Final Phase
- No artificial "turns" limitation - discussion continues as long as productive

**Collaborative Flow Example:**
1. User asks initial question (Phase 1)
2. Specialists provide independent perspectives (Phase 1)
3. Specialists cross-pollinate, may ask `@[User]` clarifying questions (Phase 2)
4. User provides clarification (Phase 3)
5. Specialists discuss User's clarification internally (Phase 3, 4, 5, 6... as needed - **all happens in < 1 minute**)
6. Chair synthesizes team's refined thinking back to User (Phase N)
7. User reviews Chair's synthesis of new quorum, decides if satisfied or continues discussion
8. Cycle repeats until User is satisfied or team reaches consensus

**Key Point:** There may be **multiple phases of internal team discussion** between when User contributes and when Chair reports back what the team thinks. This allows specialists to digest User input, debate implications, and converge on best answer before synthesizing back to User. **The entire internal discussion (multiple phases) completes in under a minute**, making real-time chat UI interaction viable.

**Timing Pattern:**
- **System response time**: < 1 minute (internal multi-phase team discussion is fast, even with 3-6 phases)
- **User response time**: Flexible - can be seconds (active chat), minutes, hours, or days (async consultation)
- **Architecture supports both**: Real-time chat UI where User gets responses in ~30-60 seconds, OR async consultation where User takes days to respond

**Chat UI Pattern:**
User sends message → System shows "thinking..." → Internal team discusses (phases N, N+1, N+2...) → Chair synthesizes → User sees new quorum/synthesis (30-60 seconds later) → User immediately responds or takes time to consider

**Result:** System supports both async (specialists work autonomously) and sync (User actively participates) collaboration patterns seamlessly, adapting to User availability without architectural changes.

## Terminology: Phase vs. Stage

**Critical Distinction:**

- **Phase** (numeric): The round number in the discussion (1, 2, 3, 4, 5, 6... N)
  - Increments sequentially: Phase 1 → Phase 2 → Phase 3 → etc.
  - Stored as integer in message metadata: `additional_kwargs={"phase": 3}`
  - Visible to specialists in XML tags: `<phase>5</phase>`
  - **Dynamic and unbounded** - discussions can go to Phase 10, 15, or beyond if needed
  - Used for filtering, context trimming, and temporal tracking

- **Stage** (behavioral mode): The conceptual behavior pattern of that phase
  - **Stage 1**: Phase 1 only - Independent Fresh Perspectives (isolation)
  - **Stage 2**: Phase 2 only - Review Others (cross-pollination)
  - **Stage 3**: Phase 3+ (any phase >= 3) - Continuing Conversation (iterative discussion with passing)
  - **Stage 4**: **Final Phase** (DYNAMIC - can occur at ANY phase number)
    - Can be triggered at Phase 4, 5, 6, 10, or any other phase number
    - Depends on four triggering conditions: convergence, stagnation, token limits, or hard stop
    - NOT a fixed phase number - completely dynamic based on discussion progression

**Examples:**
- "We're in Phase 5" = numeric round counter
- "We're in Stage 3 (iterative discussion mode)" = behavioral mode (Phase 5 is still part of Stage 3)
- "We're in the Final Phase" = Stage 4 (settlement mode) - could be Phase 4, 5, 6, 10, etc.

**Why This Matters:**
- Phase numbers are used for technical implementation (filtering, metadata, trimming)
- Stages describe how specialists should behave and what rules apply
- **Final Phase is NOT "Phase 7"** - it's whatever phase number the discussion reaches when one of the four trigger conditions occurs

**In Code:**
```python
current_phase = 5  # Numeric counter
is_final = state.get("final_phase_needed", False)  # Behavioral mode flag

if is_final:
    # Stage 4: Final Phase (settlement mode) - happens at current_phase (5 in this example)
elif current_phase == 1:
    # Stage 1: Independent perspectives
elif current_phase == 2:
    # Stage 2: Cross-pollination
else:  # current_phase >= 3
    # Stage 3: Iterative discussion
```

## Core Architecture

### Multi-Agent Culture (Shared Foundation)
All agents operate under shared Operating Principles:
- **DIGNITY**: Respect the inherent worth of all people
- **NON-HARM**: Prioritize safety and avoid causing damage
- **CONSENT**: Honor autonomy and informed choice
- **TRANSPARENCY**: Be clear and honest about limitations and uncertainties
- **CONTEXT**: Consider circumstances and nuance
- **PURPOSE**: Focus on helping the User achieve their goals

### Agent Roster (Dynamic)

**Note**: The specific roster of specialist agents is **dynamic and configurable**. Specialists are added/removed based on project needs by modifying the `AGENT_ROSTER` constant in `agents.py`. The architectural system supports any number and type of specialists.

**Permanent Architectural Elements**:
- **User** - The human asking the question (foundational - all discussions center on User's needs)
- **Chair** - Coordinator and synthesizer (architectural requirement - speaks last when participating, synthesizes perspectives, has tabling authority, only participates when specialist responses exist to synthesize)
- **Notice** - System-generated phase transition messages (architectural mechanism - never filtered)

**Research: Architectural Consideration (Under Evaluation)**:

Research specialist may warrant elevation to system-level architectural role alongside Chair:

**Arguments for system-level status:**
- Universal across all domains (legal, medical, business, technical - every domain needs current information)
- Foundational capability (without it, team limited to LLM training cutoff)
- Other specialists depend on it (provides current facts they interpret)
- Special relationship with external system (@[Search] tool, analogous to Chair's relationship with convergence detection)

**Arguments against (current state):**
- Participates in phases like regular specialists (no special coordination role)
- Can be "available" vs "in" (Chair is always present)
- No special authorities (doesn't synthesize, table debates, or control flow)
- Domain expertise still required (provides facts, others interpret)

**Current status:** Research is **core team** (always starts "in"), positioned as essential but not yet architectural. The system supports elevating it to architectural status if needed (always present, potentially special timing, mandatory vs optional).

**Decision pending:** Observe usage patterns to determine if Research should become architectural alongside Chair.

**Core Team vs. Domain-Specific Specialists**:

The roster is divided into two types:

1. **Core Team (Domain-Agnostic)**: General specialists that work across any domain
   - **Context** - Identifies ambiguities, clarifies scope, enables team to make good assumptions
   - **Research** - Uses @[Search] for current information, fact-checks, admits uncertainty
   - **Skeptic** - Challenges assumptions, identifies risks, suggests safer alternatives
   - **Ethicist** - Evaluates against ethical principles (DIGNITY, NON-HARM, CONSENT, etc.)
   - **Engineer** - Implementation focus (NOTE: "Engineer" is domain-agnostic - means "implementer" in any field, not software-specific)
   
   These roles use general language and work equally well for legal analysis, medical research, business strategy, creative projects, technical work, or any other domain.

2. **Non-Core Specialists (Domain-Specific)**: Configured based on use case, brought in by Chair when needed
   - **Current roster** (Database Architect, Cloud Architect, Backend Engineer, etc.) are **technical specialists for test case only**
   - In real use, you'd configure specialists for your actual domain:
     - Legal domain → Legal Research, Compliance, Contract Analysis specialists
     - Medical domain → Clinical, Research, Bioethics specialists
     - Business domain → Market Analysis, Finance, Operations specialists
   - Non-core specialists auto-dismiss after contributing (unless re-mentioned)

**Current Implementation**: See `ROLE_DESCRIPTIONS` in `prompts.py` for all defined roles. The current non-core technical specialists (DB, Cloud, Backend, DevOps, etc.) demonstrate the architecture with a technical use case but are not prescriptive.

### Role Description System - Dual Perspective Architecture

**Purpose**: Provide each specialist with clear self-identity (first-person) and awareness of other specialists' expertise (third-person) through a single maintainable data structure.

**Data Structure** (`ROLE_DESCRIPTIONS` in `prompts.py`):
```python
ROLE_DESCRIPTIONS = {
    "specialist_key": {
        "first_person": "You [do X, focus on Y]...",   # For self-identity
        "third_person": "[Does X, focuses on Y]...",   # For others' awareness
    },
    # ... all 16 specialists
}
```

**First-Person Usage (Self-Identity)**:
- Injected into each specialist's own system prompt
- Appears right after "You are [Name]." in their persona
- Format: `"Your role in this discussion: {first_person description}"`
- Purpose: Clear self-identity and role understanding
- Example: "You coordinate discussions, synthesize perspectives, guide the panel toward consensus..."

**Third-Person Usage (Awareness of Others)**:
- Compiled into specialist roster shown to ALL other specialists
- Appears in BASE_INSTRUCTION under "OTHER SPECIALISTS IN THIS DISCUSSION (CORE SPECIALTIES):"
- Format: `"- [Display Name]: {third_person description}"`
- Purpose: Understand what expertise is available from peers
- Example: "- Chair: Coordinates discussions, synthesizes perspectives, guides the panel toward consensus..."

**Specialist Roster Generation**:
- Dynamically generated per specialist using `generate_specialist_roster(exclude_role_key=current_specialist)`
- Shows all OTHER specialists (excludes current specialist from their own roster)
- Uses third-person descriptions for external perspective
- Updates automatically when roles are added/modified in ROLE_DESCRIPTIONS

**Benefits**:
1. **Single Source of Truth**: Both perspectives defined together per role
2. **Consistency**: First and third-person versions stay in sync
3. **Easy Maintenance**: Update one structure to change how a role is presented
4. **Self-Awareness**: Each specialist knows "who I am" clearly
5. **Group-Awareness**: Each specialist knows "who others are" and what expertise to leverage
6. **Prevents Duplication**: No hardcoded role descriptions scattered across codebase

**Example in Practice**:

*Example - Chair's Own Prompt*:
```
You are Chair.

Your role in this discussion: You coordinate discussions, synthesize perspectives...
```

*Example - What Another Specialist Sees About Chair*:
```
OTHER SPECIALISTS IN THIS DISCUSSION (CORE SPECIALTIES):
- Chair: Coordinates discussions, synthesizes perspectives...
- [Specialist A]: [Third-person description of Specialist A's role]...
- [Specialist B]: [Third-person description of Specialist B's role]...
[... all other specialists, excluding the current specialist]
```

### Execution Order Per Phase

**Architectural Requirement**: Chair speaks **last** when participating, but only participates when there are specialist responses to synthesize.

**Order**: `[Specialist 1] → [Specialist 2] → ... → [Specialist N] → Chair (conditional)`

- Specialists execute sequentially in the order defined by `AGENT_ROSTER` (in `agents.py`)
- Chair is always positioned last in the roster
- Order is configurable by modifying `AGENT_ROSTER`

**Execution**: **SEQUENTIAL** - All phases execute agents one at a time in canonical order
- Agents are completely isolated (no shared state)
- Each agent gets full GPU resources
- Chair participation is **conditional**:
  - **Phase 1**: Skips silently (no specialist responses exist yet to synthesize)
  - **Phase 2+**: Participates and synthesizes all specialist contributions from prior phases + current phase (critical coordination role)
  - **Final**: Always participates (mandatory contributions guarantee specialist responses exist)

**Chair's Conditional Participation Logic**:
```python
# Chair only participates if specialist responses exist to synthesize
# Rationale: All Chair functions (synthesis, likelihood assessment, conflict resolution)
# require specialist responses to exist first. In Phase 1, specialists are isolated and
# cannot conflict with each other, making all Chair functions impossible to perform.
visible_specialist_responses = count_non_chair_specialist_messages(state)

if visible_specialist_responses == 0:
    # Skip silently - nothing to synthesize, no conflicts possible
    log_to_stderr("[CHAIR] Skipping - no specialist responses to synthesize yet")
    return no_op
else:
    # Proceed normally - synthesize specialist responses, assess likelihood, resolve conflicts if needed
    log_to_stderr(f"[CHAIR] Participating - {count} specialist response(s) to synthesize")
    invoke_chair_llm(state)
```

**Rationale**: 
- Sequential execution ensures stable performance with Ollama and prevents VRAM thrashing
- Chair's core functions (synthesis, coordination, likelihood assessment, conflict resolution) require specialist responses to exist first
- Phase 1 has no specialist responses yet (specialists execute sequentially, Chair would go last and see none)
- **Conflicts are impossible in Phase 1** - specialists are completely isolated, see only User message, have no awareness of each other
- All Chair functions become actionable starting Phase 2 when specialists can see each other's contributions
- Skipping Phase 1 saves one LLM call (~6-8 seconds) per conversation with no loss of functionality

### Chair's Tabling Authority - Conflict Resolution

**Purpose**: Prevent unproductive cyclical debates between specialists while preserving productive exploration.

**Chair's Authority**:
- Chair has authority to "table" topics that become cyclical debates without progress BETWEEN SPECIALISTS
- This power applies only to specialist-to-specialist debates, not to the User
- Used judiciously - only for true cyclical debates that aren't making progress

**How Tabling Works**:
- **When to Table**: Chair detects specialists repeatedly debating a topic without progress or resolution
- **Format**: Chair calls out specific specialists by name: `@[Specialist A], @[Specialist B], please table the [topic] debate for now`
- **Scope**: Only the named specialists must stop discussing that topic
- **Phase Application**: Tabling applies in **Phase 3+ onwards** (after the mandatory Phase 1-2)
  - **Phase 1**: No tabling possible (specialists isolated, no conflicts)
  - **Phase 2**: No tabling needed (first cross-pollination, fresh perspectives)
  - **Phase 3+**: Tabling available (iterative discussion, conflicts may emerge)
  - **Final Phase**: Tabling NOT available (conversation settling, all must speak)
- **Other Specialists**: Specialists NOT involved in the debate may still discuss the tabled topic

**Tabling Release in Final Phase**:
- **Prior tabling restrictions are RELEASED in Final Phase**
- Specialists who were tabled in Phase 3+ CAN speak to those topics again in their final comments
- Final Phase provides opportunity to address previously tabled topics with fresh perspective
- **Chair cannot issue NEW tablings in Final Phase** - it's the settlement phase where everyone must contribute

**Important Limitations**:
- **User is NOT subject to tabling**: Chair may request the User table a concern, but the User is a human (not a controllable specialist agent), so tabling authority does not apply to them
- **Not a censorship mechanism**: Tabling is temporary de-escalation, not permanent topic suppression

**Example**:
```
Chair: "@[Specialist A], @[Specialist B], please table the [specific technical debate] for now"

Result:
- Specialist A and Specialist B must stop debating that topic in Phase 4+
- Other specialists can still discuss related approaches
- In Final Phase, both specialists can address the topic again if relevant
```

**Design Rationale**: Prevents endless back-and-forth between specialists while:
- Preserving group exploration (others can still discuss)
- Allowing fresh perspective in Final Phase
- Maintaining forward momentum in discussion
- Respecting User autonomy (cannot table User concerns)

### Chair's On-Topic Enforcement

**Purpose**: Keep specialists focused on the User's explicit request, preventing tangential discussions that waste time without helping the User.

**Chair's Authority**:
- Chair has authority to redirect specialists who discuss off-topic content
- This applies to ALL phases (including Final Phase)
- Used when specialists discuss topics that do NOT directly support answering the User's explicit request

**How On-Topic Enforcement Works**:
- **Detection**: Chair monitors all specialist contributions for relevance to User's EXPLICIT concerns
- **Intervention**: If specialist goes off-topic, Chair calls them out by name
- **Format**: `@[Specialist Name], please stay on-topic. The User asked about [explicit concern]. Please focus on [specific aspect] that addresses their question.`
- **Compliance**: Specialists MUST comply immediately (implemented as CRITICAL thinking step)
- **Balance**: Chair allows reasonable context-setting but prevents rabbit holes unrelated to User's goal

**Specialist Compliance Requirements**:
- **CRITICAL thinking step**: Before contributing, specialists must check if Chair has asked them to stay on-topic in recent messages
- If redirected by Chair, specialists have TWO options:
  1. **Comply if off-topic**: Acknowledge and refocus immediately
  2. **Defend if pertinent**: Explain WHY the topic directly helps answer User's explicit concern with specific justification

**Example 1 - Compliance**:
```
@[Chair]: "@[Specialist Name specialist], please stay on-topic. @[User] asked about [topic A]. Please focus on [specific aspect], not [tangential concern]."

Specialist (next contribution): "Understood. Refocusing on [topic A]: [on-topic contribution]."
```

**Example 2 - Defending Relevance**:
```
@[Chair]: "@[Specialist Name specialist], please stay on-topic. @[User] asked about [topic A]. Please focus on [topic A], not [topic B]."

Specialist (next contribution): "@[Chair], I believe [topic B] is pertinent because @[User]'s request requires [connection], and [topic B] directly determines [relevant outcome]. [Continues with relevant contribution]."
```

**Design Rationale**: 
- Prevents wasting User's time on tangential discussions
- Ensures all specialist contributions directly help answer User's question
- Allows specialists to defend genuinely pertinent topics that Chair may have misjudged
- Creates healthy dynamic where Chair can redirect while specialists can justify relevance
- Maintains discussion quality and relevance without being too heavy-handed
- Complements tabling authority (tabling = cyclical debates, on-topic = relevance)

**Implementation**:
- Chair system prompt includes on-topic monitoring responsibility (`prompts.py::CHAIR_SYSTEM_BASE`)
- Chair must acknowledge if specialist justifies relevance in next synthesis
- Specialist system prompt includes compliance requirement with defense option (`prompts.py::BASE_INSTRUCTION`)
- Specialists have CRITICAL thinking step to check for Chair's on-topic guidance before each contribution
- Specialists can respond with `@[Chair], I believe [topic] is pertinent because [reason]...` if they disagree with redirection

### Chair's Stagnation Detection (Phase 4+)

**Purpose**: **CRITICAL for autonomous operation** - Recognize when internal team has completed their deliberation and can deliver final synthesis to User. Because specialists work autonomously while User is away (minimum 3h, average 1.5d), Chair must detect when the team has reached consensus and is ready to conclude, ensuring User receives a complete answer rather than an incomplete discussion.

**Critical Balance**: Must infer "most likely" end of current User interaction round while recognizing that compelling new insights in Final Phase may re-engage User attention for another round. **Trade-off**: End too early → miss insights that could bring User back; end too late → waste resources on repetitive discussion.

**Secondary Goal**: Detect when discussion has stagnated (specialists rehashing without new progress) to prevent wasted computation and move efficiently toward final synthesis.

**When Active**: Phase 4 and later (requires comparison between Chair's Phase N-1 and Phase N syntheses)

**Why This Is Critical**: Without convergence detection, autonomous team would either:
- Continue indefinitely (wasting tokens/time waiting for User who won't respond)
- Stop arbitrarily at fixed phase (risking incomplete analysis)
- Chair's equation balances: complete deliberation vs efficient conclusion

**How It Works (Hybrid Architecture)**:

**Overview**: Stagnation detection uses a **hybrid approach** combining deterministic local computation (quantitative signals) with LLM semantic judgment (synthesis comparison). This combines the benefits of observable, tunable math with nuanced content understanding.

1. **Chair generates normal synthesis** for current phase
2. **Local Python Analysis** (`agents.py::check_discussion_stagnation`, lines 1600-1840):
   - **Deterministic computation** analyzes conversation state by scanning message history
   - **Counts observable patterns**: User messages, question marks, conditional phrases, search results
   - **Computes continuous probability** (0.0-1.0) from weighted equation
   - **Result**: Observable, tunable, data-driven quantitative signal
   
3. **System computes stagnation probability** from 5 stagnation signals (POSITIVE, push toward final) and 4 justification signals (NEGATIVE, allow continuation):
   
  **Stagnation Signals** (increase probability):
  - **User silence** (+0.40 max): 8% per phase, caps at 40% after 5 phases (tuned 2025-10-12 for thoroughness)
  - **Phase progression** (UNBOUNDED): 25% per check, reaches 100% at Phase 8 baseline
   - **Low user engagement** (+0.20): Flat score if phase≥6 and user_messages≤1
   - **Specialist questions** (+0.15 max): Based on question marks in recent phases
   - **Conditional planning** (+0.06 max): Based on conditional phrases in recent phases (tuned 2025-10-12, reduced from 0.10)
   
   **Justification Signals** (decrease probability, allow Phase 8+ continuation):
   - **Recent User response** (-0.30): User active in current/last phase
   - **Recent User 1 phase ago** (-0.15): User responded 1 phase ago
   - **High User engagement** (-0.20): User has sent 3+ messages
   - **Research activity** (-0.15): 2+ searches in last 2 phases (new info justifies exploration)
   - **Answer mode** (-0.10): ≤2 questions in last 2 phases (specialists providing answers, not asking)
   
4. **Full equation**: `P(stagnation) = max(0.0, min(Σ(stagnation) + Σ(justification), 1.0))`

5. **LLM Decision (Chair)** (`agents.py`, lines 2153-2300):
   - **Receives**: Computed probability, threshold guidance, previous synthesis (Phase N-1), current synthesis (Phase N), User concerns
   - **Does NOT receive**: Raw signal values (only in debug output for tuning)
   - **Semantic judgment**: Compares synthesis content to detect "rehashing same points" vs genuine progress
   - **Threshold calibration**: Probability guides how strict Chair should be:
     - HIGH (75%+) → "any hint of stagnation should trigger"
     - MODERATE (40-60%) → "substantial stagnation should trigger"
     - LOW (<40%) → "need CLEAR, OBVIOUS stagnation"
   - **Returns**: `<stagnated>yes</stagnated>` or `<stagnated>no</stagnated>`

6. **System processes decision**:
   - If yes: System sets `final_phase_needed=True` and adds Notice message
   - If no: Discussion continues to next phase normally

**Why Hybrid?**
- ✅ **Local computation** provides quantitative baseline that is deterministic, observable, and tunable
- ✅ **LLM decision** adds semantic understanding that pure math cannot capture
- ✅ **Example**: Math says "34% probability" but LLM reads syntheses and sees specialists asking same questions repeatedly → triggers despite low probability
- ✅ **Example**: Math says "75% probability" but LLM reads syntheses and sees breakthrough insights emerging → continues despite high probability
- ✅ **Calibration**: Probability informs LLM's threshold, creating data-driven semantic judgment
- ✅ **Tunability**: Adjust weights (±3-5%) based on observed false positives/negatives without retraining LLM

**CONVERGENCE WITH JUSTIFICATION (AGGRESSIVE)**: 
- **Baseline convergence**: Phase progression reaches 100% at Phase 8
- **With justification**: Can reduce to 25% (100% - 75% max justification), allowing Phase 8+ to continue
- **Phase 8+ allowed when**: Active User + research activity + specialists providing answers (not spinning)
- **Typical pattern**: Most discussions end Phase 5-7, justified productive discussions can reach Phase 10+
- **Philosophy**: "Answer with assumptions" for early conclusion, but allow genuinely productive continuation

**LONG-TERM TUNING PROJECT**:
This linear equation model is designed for iterative refinement based on real-world data:
- **All weights are tunable constants** in `agents.py` (~lines 1641-1792)
- **Comprehensive DEBUG output** shows all terms, formulas, intermediate calculations for observability
- **Measurement infrastructure**: Each stagnation check logs full equation state for post-hoc analysis
- **Expected iteration**: Adjust weights based on observed false positives (ended too early) vs false negatives (ran too long)

**DATA COLLECTION LOG** (track each conversation for tuning analysis):

| Date | Phase | Probability | Top Signals | User Msgs | Assessment | Notes |
|------|-------|-------------|-------------|-----------|------------|-------|
| 2025-10-11 | 6 | ~1.00 | phase_prog(100%), user_silence(?), low_engagement(?) | ? | ✅ Good | Comprehensive Chair synthesis, actionable deliverables. First real-world test of model. |
| 2025-10-12 | 6 | 56.0% | phase_prog(30%), low_engagement(20%), questions(15%) | 1 | ⚠️ Too early | Comprehensive multi-track historical question: Triggered immediately after heavy research phase (8 searches), before specialists could present synthesized findings. Research justification (-15%) was active but insufficient to overcome stacked stagnation signals (71% - 15% = 56%). Specialists were in productive autonomous work mode (gathering sources, building frameworks) rather than blocked-waiting mode. Research→synthesis is a natural two-phase pattern that needs protection. |

**Collection Protocol:**
1. After each discussion, record: Phase triggered, Probability (from DEBUG), Top 3 signals, User message count
2. Qualitative assessment: ✅ Perfect timing, ⚠️ Too early (premature), ⚠️ Too late (spinning)
3. After observations, consider minor adjustments (±3-5% per term)
4. Document any equation structure experiments below

**EQUATION STRUCTURE EXPERIMENTS** (document attempts to improve the model):

| Date | Change Description | Rationale | Observations | Keep/Revert |
|------|-------------------|-----------|--------------|-------------|
| 2025-10-11 | Initial model: 5 stagnation + 4 justification signals, phase_weight=0.25 | Baseline aggressive convergence (Phase 8) with justification extension | TBD after observations | Active |
| 2025-10-12 | Research justification: -0.15 → -0.18 (+3% boost) | Protect research→synthesis pattern. Observed -15% insufficient when stagnation signals stack (71% - 15% = 56% triggered immediately after research burst). Conservative +3% boost gives research-intensive discussions more runway for synthesis phase. Would have resulted in 71% - 18% = 53%. | TBD - observe whether this prevents premature triggering in research-heavy discussions without allowing true stagnation to persist | Active |

**Experiment Guidelines:**
- Experiment with different equation structures (new signals, different formulas, interaction terms)
- BUT: Individual term weight changes should stay within ±3-5% per iteration
- Document each structural experiment: what changed, why, observations, keep/revert decision
- Examples of structural experiments: Adding new signals, changing signal formulas, adding multiplicative terms
- Examples of weight tuning: Adjusting 0.25 → 0.23 or 0.27 (within guidelines, not structural)

**Stagnation Detection Prompt**:
```
CONTEXT:
You are analyzing two syntheses you wrote in consecutive phases. Each synthesis is a SUMMARY 
of an ongoing multi-phase conversation where specialists discuss the User's concerns.

Compare these summaries to determine: Is the discussion making NEW progress on the User's 
concerns between phases, or are specialists rehashing the same points without advancing 
toward an answer?

<user_concerns>
<message><from>User</from><timestamp_iso>2025-10-11T14:30:00.123</timestamp_iso><phase>0</phase><content>User's initial question...</content></message>

<message><from>User</from><timestamp_iso>2025-10-11T14:35:22.456</timestamp_iso><phase>2</phase><content>User's follow-up clarification...</content></message>

[All User messages in full <message> XML format]
</user_concerns>

<previous_synthesis>
<message><from>Chair</from><timestamp_iso>2025-10-11T14:38:45.789</timestamp_iso><phase>N-1</phase><content>Chair's previous synthesis content...</content></message>
</previous_synthesis>

<current_synthesis>
<message><from>Chair</from><timestamp_iso>2025-10-11T14:42:15.234</timestamp_iso><phase>N</phase><content>Chair's current synthesis content...</content></message>
</current_synthesis>

Respond with ONLY:
<stagnated>yes</stagnated>  (move to final round)
OR
<stagnated>no</stagnated>   (continue discussion)
```

**Notice Message When Stagnation Detected**:
```
Notice: Based on discussion stagnation analysis, we are moving to the final round. 
All specialists, please provide your concluding assessment.
```

**Console Output (stderr) - Comprehensive DEBUG Information**:

Every stagnation check outputs detailed computation to stderr for observability and tuning:

```
================================================================================
[DEBUG] STAGNATION PROBABILITY COMPUTATION (Phase 7)
================================================================================

STATE TRACKING & CONTEXT:
  Current Phase: 7
  Stagnation Check Phase: Phase 7 (check #4)
  First Check: Phase 4 (stagnation detection starts here)
  Last User Phase: 1 (most recent User message)
  User Silence: 6 phases since last User message
  Total User Messages: 1
  Recent Phases: [6, 7] (last 2 phases for analysis)
  Total Conversation Messages: 45

EQUATION: P(stagnation) = max(0.0, min(Σ(stagnation_signals) + Σ(justification_signals), 1.0))
Where each signal contributes a weighted score based on observable metrics.
Stagnation signals (POSITIVE): Push toward final phase
Justification signals (NEGATIVE): Allow Phase 8+ continuation

RAW INPUTS:
  user_silence_phases = 6
  current_phase = 7
  last_user_phase = 1
  user_message_count = 1
  phases_since_check_started = 4
  recent_question_count = 7
  conditional_count = 3
  search_tool_count = 0

SIGNAL COMPUTATIONS:
  1. User Silence (CONSERVATIVE):
     Formula: min(user_silence_phases * 0.08, 0.40)
     Calculation: min(6 * 0.08, 0.40) = 0.4000
     Contribution: 0.4000 (40.0%)
     Note: Caps at 40% after 5 phases - favors thoroughness over efficiency

  2. Phase Progression (UNBOUNDED - AGGRESSIVE):
     Formula: (phases_since_check - 1) * 0.25
     Calculation: (4 - 1) * 0.25 = 0.7500
     Contribution: 0.7500 (75.0%)
     Schedule: Ph4=0%, Ph5=25%, Ph6=50%, Ph7=75%, Ph8=100% (GUARANTEED)

  3. Low User Engagement:
     Formula: 0.20 (flat score if phase≥6 AND user_msgs≤1)
     Triggered: phase=7≥6, msgs=1≤1
     Contribution: 0.2000 (20.0%)

  4. Specialist Questions:
     Formula: min(question_count / 20.0, 0.15)
     Calculation: min(7 / 20.0, 0.15) = 0.1500
     Contribution: 0.1500 (15.0%)

  5. Conditional Planning:
     Formula: min(conditional_count / 15.0, 0.10)
     Calculation: min(3 / 15.0, 0.10) = 0.0667
     Contribution: 0.0667 (6.7%)

  SUBTOTAL (stagnation signals): 1.6667 (166.7%)

JUSTIFICATION SIGNALS (negative contributions):
  1. Recent User Response: +0.0000 (not active, silence=6)
  2. High User Engagement: +0.0000 (msgs=1<3)
  3. Recent Research Activity: +0.0000 (searches=0<2)
  4. Answer Mode: -0.1000 (-10.0%) [specialists providing answers]

  SUBTOTAL (justification): -0.1000 (-10.0%)

FULL EQUATION SUMMATION:
  P(stagnation) = 0.5000 + 0.7500 + 0.2000 + 0.1500 + 0.0667 + (-0.1000)
  P(stagnation) = 1.6667 + (-0.1000)
  P(stagnation) = 1.6667 - 0.1000
  P(stagnation) = 1.5667 (before bounds)
  P(stagnation) = min(1.5667, 1.0) = 1.0000 (capped at ceiling)

FINAL STAGNATION PROBABILITY: 1.0000 (100.0%)

THRESHOLD MAPPING:
  0.00-0.20 (0-20%):   🟢 LOW → HIGH threshold (need obvious stagnation)
  0.20-0.40 (20-40%):  🟡 LOW-MOD → MODERATE-HIGH threshold
  0.40-0.60 (40-60%):  🟠 MODERATE → MODERATE threshold
  0.60-0.75 (60-75%):  🔴 MOD-HIGH → LOW-MODERATE threshold
  0.75-1.00 (75-100%): 🔴 HIGH → LOW threshold (any hint triggers)
  Current: 🔴 HIGH (75-100%)

WEIGHT CONFIGURATION (CONSERVATIVE):
  STAGNATION SIGNALS (positive, push toward final):
    • SILENCE_WEIGHT = +0.40 max  (8%/phase, caps at 5 phases - favors thoroughness)
    • PHASE_WEIGHT = UNBOUNDED   (25%/check, reaches 100% at Phase 8)
    • LOW_ENGAGEMENT_WEIGHT = +0.20  (flat score)
    • MAX_QUESTION_WEIGHT = +0.15 (caps at 20 questions)
    • MAX_CONDITIONAL_WEIGHT = +0.10 (caps at 15 phrases)
  
  JUSTIFICATION SIGNALS (negative, allow continuation):
    • RECENT_USER_RESPONSE = -0.30 (if User in current/last phase)
    • RECENT_USER_1PHASE = -0.15 (if User 1 phase ago)
    • HIGH_USER_ENGAGEMENT = -0.20 (if user_msgs >= 3)
    • RESEARCH_ACTIVITY = -0.15 (if searches >= 2 in last 2 phases)
    • ANSWER_MODE = -0.10 (if questions <= 2 in last 2 phases)
  
  MAX JUSTIFICATION = -0.75 (all signals active)
  NET EFFECT: Can extend Phase 8+ if justified (100% - 75% = 25%)
  
  BASELINE CONVERGENCE: Phase 8 (100% from phase_score alone)
  WITH JUSTIFICATION: Phase 8+ possible if User active + research + answers
  TARGET: Most discussions end Phase 5-7, justified Phase 8-10 allowed
  PHILOSOPHY: 'Answer with assumptions' + allow productive continuation

TUNING NOTES (for intuitive iteration):
  Observe this output over multiple conversations, then consider:
    • Ending too early? Maybe adjust PHASE_WEIGHT down slightly next time
    • Ending too late? Maybe adjust PHASE_WEIGHT up slightly next time
    • Specific signal misbehaving? Maybe tweak that signal's weight

  Expect minor adjustments only - typically ±3-5% per term per iteration
  No strict thresholds - just observe, discuss, and make small changes
  SEE: ARCHITECTURE.md 'EXPERIMENTAL REPRODUCIBILITY REQUIREMENTS' for data capture

EXPERIMENTAL REPRODUCIBILITY REQUIREMENTS:
  Every experiment MUST capture for tuning analysis:
  
  1. EQUATION STATE (printed above in debug output):
     - All weight values (SILENCE_GROWTH, MAX_SILENCE, PHASE_WEIGHT, etc.)
     - All raw inputs (user_silence_phases, current_phase, question_count, etc.)
     - All signal computations (formulas, calculations, contributions)
     - Final probability and decision
     - Current date/time for version tracking
  
  2. FULL MESSAGE CONTEXT:
     - Complete conversation history (all phases)
     - Each message with: speaker, phase, timestamp, content
     - Specialist participation pattern (who spoke when, who passed)
     - Search tool usage (queries, results, timing)
     - User input timing (when User spoke, phase gaps)
  
  3. OUTCOME ASSESSMENT:
     - Was final phase triggered at right time? (subjective)
     - Were final phase contributions substantive or repetitive?
     - Did specialists produce actionable deliverables?
     - User satisfaction (if available)
  
  HOW TO CAPTURE:
  - Debug output (above) is printed to stderr - redirect to file
  - Full transcript with phases/timestamps in stdout
  - Checkpoint files contain full state
  - Manually assess outcome quality in ARCHITECTURE.md validation sections
  
  TUNING WORKFLOW:
  1. Run experiment, capture debug output + transcript
  2. Assess: "Did it converge too early/late/just right?"
  3. Identify which signal(s) drove the decision
  4. Adjust ONE weight by ±3-5% (conservative)
  5. Document in ARCHITECTURE.md "Recent Changes"
  6. Run 3-5 more experiments to validate
  7. Iterate
  
  Without this data capture, tuning is guesswork - equation needs observable outcomes
  
  PRACTICAL CAPTURE EXAMPLE:
  ```bash
  # Capture both stdout (transcript) and stderr (debug) to files
  python -m axion_swarm "your question here" 2> debug_$(date +%Y%m%d_%H%M%S).log | tee transcript_$(date +%Y%m%d_%H%M%S).txt
  
  # debug_*.log contains: equation weights, raw inputs, signal computations, decision
  # transcript_*.txt contains: full conversation with phases, timestamps, speakers
  # .axion_checkpoint.json contains: full state including all messages
  
  # After experiment: manually assess outcome and document in ARCHITECTURE.md
  ```

================================================================================
```

This comprehensive output provides complete visibility into:
- **State tracking**: Phase numbers, User activity, message counts
- **Raw inputs**: All metrics feeding into the equation
- **Signal computations**: Detailed formula, calculation, and contribution for each signal
- **Equation summation**: Step-by-step calculation with bounds
- **Final probability**: Continuous value (0.0-1.0) sent to Chair
- **Weight configuration**: All tunable constants for iteration
- **Tuning guidance**: How to adjust weights based on observed behavior

**Design Rationale**:
- **CRITICAL for autonomous operation**: Specialists must work independently for 3h-1.5d while User is away (average 1.5d). Chair's convergence detection ensures team knows when they've completed deliberation and can deliver final answer.
- **Prevents indefinite discussion**: Without this, autonomous team would continue indefinitely waiting for User who won't respond for hours/days
- Chair (coordinator) is best positioned to assess if synthesis is evolving across phases
- Comparing syntheses (not individual specialist messages) focuses on big-picture progress
- Phase 4+ requirement ensures discussion has matured (Phase 1-2-3 for exploration)
- **Tuning is critical**: Equation must balance complete deliberation vs efficient conclusion. Too aggressive = incomplete answers. Too lenient = wasted computation.
- Conservative approach: only triggers when Chair explicitly identifies stagnation
- Distinct from convergence (specialists passing) - stagnation is Chair-detected lack of progress

**Distinction from Convergence**:
- **Convergence** (Path 1): Specialists explicitly pass → natural agreement to conclude
- **Stagnation** (Path 2): Chair detects lack of progress → coordinator-initiated conclusion
- Both trigger Final Phase, but through different mechanisms

**Benefits**:
- Saves time when discussion plateaus
- Prevents circular rehashing without progress
- Maintains discussion quality by moving to conclusion when appropriate
- User still gets comprehensive final round with all specialist input

**Implementation** (`agents.py`):
- `check_discussion_stagnation()`: Performs stagnation analysis via second Chair LLM call
- `chair_agent()`: Calls stagnation check after synthesis generation in Phase 4+
- XML parsing: Extracts `<stagnated>yes/no</stagnated>` from Chair's response
- Fallback: Plain text "yes" matching if XML parsing fails
- Error handling: If stagnation check fails, discussion continues without detection

---

#### Mathematical Model Details

**Full Equation**:
```
P(stagnation) = max(0.0, min(Σ(stagnation_signals) + Σ(justification_signals), 1.0))
```

**Stagnation Signals** (positive contributions, increase P(stagnation)):
1. **User Silence**: `min(silence_phases * 0.08, 0.40)`
   - 8% per phase of User silence (tuned 2025-10-12)
   - Caps at 40% after 5 phases
   - Rationale: User likely unavailable to unblock discussion; conservative weight favors thoroughness

2. **Phase Progression**: `(checks - 1) * 0.25` (UNBOUNDED)
   - 25% per stagnation check
   - Phase 4 (check #1): 0%, Phase 5: 25%, Phase 6: 50%, Phase 7: 75%, Phase 8: 100%
   - Rationale: Discussions should converge, ensures Phase 8 maximum

3. **Low User Engagement**: `0.20` (flat score if phase≥6 AND user_msgs≤1)
   - Activated when User has sent ≤1 message by Phase 6+
   - Rationale: Minimal User participation suggests disengagement

4. **Specialist Questions**: `min(recent_questions / 20.0, 0.15)`
   - Counts `?` marks in specialist messages from last 2 phases
   - Activates at ≥5 questions, caps at 15%
   - Rationale: Many questions suggest need for User answers

5. **Conditional Planning**: `min(recent_conditionals / 15.0, 0.06)`
   - Counts phrases: "if you", "pending", "once you", "after you confirm", "when you decide"
   - In specialist messages from last 2 phases
   - Activates at ≥3 phrases, caps at 6%
   - Rationale: Plans contingent on undefined User decisions
   - Note: Reduced from 10% to 6% (2025-10-12) because conditional language often accompanies good "answer with assumptions" behavior

**Justification Signals** (negative contributions, decrease P(stagnation)):
1. **Recent User Response**: `-0.30` (User in current or last phase)
   - Strong signal of productive engagement
   - If User spoke 1 phase ago: `-0.15` instead
   
2. **High User Engagement**: `-0.20` (if user_message_count ≥ 3)
   - Multiple User inputs show active collaboration
   
3. **Research Activity**: `-0.15` (if searches ≥ 2 in last 2 phases)
   - New external information from `Search tool` messages
   - Justifies exploration with fresh data
   
4. **Answer Mode**: `-0.10` (if questions ≤ 2 in last 2 phases)
   - Specialists providing answers rather than asking questions
   - Indicates productive progress

**Maximum Justification**: -0.75 total (all 4 signals active)
- Can reduce 100% baseline (Phase 8) to 25%, allowing Phase 8+ continuation

**Threshold Mapping** (Probability → Chair Guidance):
- 0-20%: 🟢 HIGH threshold (need obvious stagnation)
- 20-40%: 🟡 MODERATE-HIGH threshold (need substantial stagnation)
- 40-60%: 🟠 MODERATE threshold (minor but definite stagnation)
- 60-75%: 🔴 LOW-MODERATE threshold (even minor hints)
- 75-100%: 🔴 LOW threshold (any hint triggers)

**CRITICAL DESIGN PRINCIPLE**: Categories are ONLY for human display. Chair receives the actual continuous `total_probability` value (0.0-1.0 float) in its prompt and makes decisions based on the precise value, NOT binned categories. All computations use continuous values; binning only occurs at the final display layer.

**How Chair Applies Threshold** (fixed 2025-10-12): Chair's prompt provides explicit calibration instructions mapping each probability range to specific decision criteria. For example, at 30% probability (20-40% range = MODERATE-HIGH threshold), Chair is instructed to "trigger ONLY if synthesis comparison shows SUBSTANTIAL stagnation" and to "allow discussion to continue unless clearly blocked." The Chair compares previous and current syntheses for stagnation patterns, then applies the threshold calibration to make a decision. Previously, the prompt contained hardcoded overrides (e.g., "if user_silence ≥ 1 → use LOW threshold") that ignored the computed guidance, causing premature triggers. This was fixed to respect the computed threshold across all probability ranges.

**Convergence Schedule Examples**:

| Scenario | Phase 8 Probability | Can Continue? |
|----------|-------------------|---------------|
| User silent, no justification | 100% + 40% = 100% (capped) | ❌ Triggers |
| User active, no justification | 100% - 30% = 70% | ⚠️ Likely triggers |
| User active + research + answers | 100% - 75% = 25% | ✅ Can continue |
| User engaged, Phase 10 | 100% + (7×25%) - 75% = 100%+ | ❌ Eventually triggers |

---

#### Tuning Guide

**All weights are configurable constants** in `agents.py` (~lines 1641-1792).

**Current weight configuration**:
```python
# Phase progression formula (primary convergence control):
phase_score = (checks - 1) * 0.25  # Current: reaches 100% at Phase 8

# Stagnation signals (current values):
SILENCE_GROWTH = 0.08              # 8% per phase (tuned 2025-10-12)
MAX_SILENCE = 0.40                 # Caps at 40% (favors thoroughness)
LOW_ENGAGEMENT_WEIGHT = 0.20       # Flat 20% penalty
MAX_QUESTION_WEIGHT = 0.15         # Max from questions
MAX_CONDITIONAL_WEIGHT = 0.10      # Max from conditionals

# Justification signals (current values):
RECENT_USER_RESPONSE = -0.30       # User in current/last phase
RECENT_USER_1PHASE = -0.15         # User 1 phase ago
HIGH_USER_ENGAGEMENT = -0.20       # 3+ User messages
RESEARCH_ACTIVITY = -0.15          # 2+ searches
ANSWER_MODE = -0.10                # ≤2 questions
```

**Tuning philosophy**:
- Observe behavior over multiple conversations
- Make minor adjustments only: ±3-5% per term per iteration
- Intuitive, discussion-based approach (not prescriptive rules)
- Consider small changes based on patterns, not rigid thresholds
- See DEBUG output and DATA COLLECTION LOG for observation data

**Performance Indicators (Stagnation Model PKIs)**:

Inspired by SRE practices, we track Key Performance Indicators for the stagnation detection system. These PKIs guide iterative tuning of all term multipliers.

**Primary PKIs** (quantitative, measured per discussion):
1. **Trigger Phase** (discrete)
   - Definition: Which phase triggered final phase
   - Target: p50 = 6, p90 = 8, p99 ≤ 10
   - Collection: Log from `final_phase_needed` flag, record phase number
   - Use: Detect drift in convergence behavior

2. **Stagnation Probability at Trigger** (continuous 0.0-1.0)
   - Definition: `total_probability` value when Chair said "stagnated"
   - Target: p50 = 0.60-0.80 (confident decisions)
   - Collection: Log from DEBUG output at trigger
   - Use: Identify if thresholds are calibrated correctly

3. **False Positive Rate** (discussions ended too early)
   - Definition: % discussions where User or reviewer felt it ended prematurely
   - Target: <5% of discussions
   - Collection: Post-discussion User feedback + manual review
   - Use: Tune signals down if too high (especially phase_score multiplier)

4. **False Negative Rate** (discussions ran too long)
   - Definition: % discussions that should have ended earlier (spinning/blocking)
   - Target: <10% of discussions
   - Collection: Manual review of Phase 9+ discussions
   - Use: Tune signals up if too high

5. **Phase Duration Distribution** (discrete distribution)
   - Definition: Histogram of trigger phases across all discussions
   - Target: 60% in Phase 5-7, 30% in Phase 8-9, <10% in Phase 10+
   - Collection: Aggregate trigger phase logs
   - Use: Overall health check of convergence model

**Secondary PKIs** (signal-specific, for debugging):
6. **Signal Activation Rates**
   - Definition: How often each signal is non-zero
   - Target: Varies by signal (User silence 40%, questions 30%, etc.)
   - Collection: Count from DEBUG output
   - Use: Identify signals that never/always fire

7. **Signal Contribution Distribution**
   - Definition: Average contribution of each signal when active
   - Target: No single signal dominates (no signal >50% of total)
   - Collection: Parse DEBUG output, compute mean contributions
   - Use: Rebalance weights if one signal dominates

8. **Justification Effectiveness**
   - Definition: % of Phase 8+ discussions that had justification signals active
   - Target: >80% (justification should be working)
   - Collection: Check justification subtotal in DEBUG output
   - Use: Validate justification signals are preventing premature Phase 8 triggers

**Operational PKIs** (system health):
9. **Chair Agreement Rate**
   - Definition: % of stagnation checks where Chair agrees with computed probability direction
   - Target: >90% (high P → Chair says yes, low P → Chair says no)
   - Collection: Compare `total_probability` to Chair's `<stagnated>` response
   - Use: Validate probability model aligns with Chair's judgment

10. **Cost Per Discussion**
    - Definition: Total tokens (input + output) per discussion
    - Target: Median <20k tokens (aggressive convergence working)
    - Collection: Sum tokens across all specialist calls + Chair
    - Use: Measure cost impact of convergence changes

**Logging Infrastructure** (to implement):
```python
# In agents.py after stagnation check:
log_stagnation_event({
    "timestamp": datetime.now().isoformat(),
    "discussion_id": generate_discussion_id(),
    "phase": current_phase,
    "total_probability": total_probability,
    "chair_decision": stagnation_response,  # "yes" or "no"
    "signals": {
        signal["factor"]: signal["probability"] 
        for signal in stagnation_signals + justification_signals
    },
    "raw_inputs": {
        "user_silence_phases": user_silence_phases,
        "user_message_count": user_message_count,
        "recent_question_count": recent_question_count,
        "conditional_count": conditional_count,
        "search_tool_count": search_tool_count,
    }
})
```

**Analysis Workflow** (future implementation):
1. **Daily**: Aggregate PKIs from last 24h discussions
2. **Weekly**: Review trends, identify anomalies
3. **Monthly**: Formal weight tuning based on PKI targets
4. **Quarterly**: Re-evaluate signal design, consider new signals

**Tuning Decision Matrix** (example):

| PKI Observation | Diagnosis | Action |
|-----------------|-----------|--------|
| Median trigger = Phase 9 | Too conservative | Increase phase_score multiplier: 0.25 → 0.28 |
| False positive rate = 12% | Too aggressive | Decrease silence_growth: 0.10 → 0.08 |
| Phase 8+ always has justification | Justification too strong | Reduce justification weights by 20% |
| User silence signal never fires | Threshold too high or not activating | Check logic, reduce cap threshold |
| Questions signal always maxed | Cap too low | Increase cap: 0.15 → 0.20 |
| Cost per discussion increasing | Convergence degrading | Review all signals, check for drift |

This framework enables data-driven iteration on all term multipliers over time, inspired by SRE observability practices

**DEBUG Output** (every stagnation check logs to stderr):
```
================================================================================
[DEBUG] STAGNATION PROBABILITY COMPUTATION (Phase 6)
================================================================================
RAW INPUTS: user_silence=3, phase=6, user_msgs=1, questions=8, conditionals=4

SIGNAL COMPUTATIONS:
  1. User Silence: 0.3000 (30.0%)
  2. Phase Progression: 0.5000 (50.0%)  
  3. Low User Engagement: 0.2000 (20.0%)
  4. Specialist Questions: 0.1500 (15.0%)
  5. Conditional Planning: 0.0600 (6.0%)
  
  SUBTOTAL (stagnation): 1.2100 (121.0%)
  
JUSTIFICATION SIGNALS:
  1. Recent User Response: +0.0000 (silence=3)
  2. High User Engagement: +0.0000 (msgs=1<3)
  3. Research Activity: +0.0000 (searches=0<2)
  4. Answer Mode: +0.0000 (questions=8>2)
  
  SUBTOTAL (justification): 0.0000 (0.0%)

SUMMATION: 1.2100 + 0.0000 = 1.2100 → 1.0000 (capped)
FINAL PROBABILITY: 1.0000 (100.0%)

WEIGHT CONFIGURATION:
  MAX JUSTIFICATION = -0.75 (all signals active)
  NET EFFECT: Can extend Phase 8+ if justified (100% - 75% = 25%)
  CONVERGENCE GUARANTEE: Phase 8 baseline
  WITH JUSTIFICATION: Phase 8-12 possible if User active + research + answers
================================================================================
```

---

#### Search Results Integration

**Research Activity Justification**:
Search results (`name="Search tool"`) count toward justification when:
- ≥2 searches in last 2 phases
- Reduces P(stagnation) by 15%

**Format** (from `search.py`):
```xml
<results query="..." requester="@[Specialist name]">
    <answer>AI-generated summary</answer>
    <result url="..." title="...">Content excerpt</result>
</results>
```

**Unicode Normalization**: All search text normalized to ASCII-like characters before XML escaping:
- Smart quotes " " → straight quotes "
- Em/en dashes – — → hyphen -
- Ellipsis … → three dots ...
- HTML entities decoded first, then normalized

---

### Model Configuration (Current)
- **Model**: `hf.co/bartowski/Qwen_Qwen3-30B-A3B-Thinking-2507-GGUF:Q4_K_M`
  - 30B parameter thinking model (Q4_K_M quantization)
  - Changed from 8B model for better reasoning
  - Note: "Thinking" models may have longer first-token latency
- **Context Window**: 50,560 tokens
- **Sampling Parameters**:
  - Temperature: 0.6
  - Top-P: 0.95
  - Top-K: 20
  - Min-P: 0.0

## The 4-Stage Conversation System

### Overview: Atomic Phases with Self-Awareness vs Group-Awareness Architecture

The system uses strategic **message filtering** to control what each specialist sees at different stages. This creates varying levels of self-awareness and group-awareness to optimize discussion quality. **Phases are atomic**: specialists only see messages from PRIOR completed phases, not the current phase they're in (except Chair, who goes last and sees current phase).

**Conceptual Framework - The Meeting Metaphor**:
- **Phase 1 & 2**: Initial assessments (mandatory) - Everyone provides their first take, then reviews others' perspectives
- **Phase 3+**: Continuing conversation (iterative, optional) - Discussion continues as long as specialists have new contributions
- **Final Phase**: Wrap up the meeting (settlement) - Specialists provide final assessments when no further user input is expected

**Key Concepts**:
- **Phase**: One complete cycle where all specialists have the opportunity to contribute. The system progresses through multiple phases for iterative refinement.
- **Atomic Phases**: Specialists only see messages from PRIOR completed phases, not current phase (prevents premature responses)
- **Chair Exception**: Chair goes LAST in each phase and CAN see current phase messages (to synthesize what others just said)
- **Pass** (verb): To skip contributing by saying "I have no further comments at this time"
- **Self-Awareness**: Can the specialist see their own previous contributions?
- **Group-Awareness**: Can the specialist see what others have said?
- **Filtering**: Selectively removing messages from history before showing to specialist
- **User Messages**: ALWAYS visible, never filtered (the foundation of every discussion)
- **Notice Messages**: ALWAYS visible, never filtered (they mark phases for everyone)
- **Phase Metadata**: Every message is tagged with its phase number for reliable tracking and filtering
- **User Input Resets Convergence**: If User speaks during Phase 3+ or Final, system reverts to Phase 3+ (Final Phase invalidated)

### Stage 1: Phase 1 - Independent Fresh Perspectives (Initial Assessment)

**Purpose**: Initial mandatory assessment - everyone provides their first take without anchoring to others

**History Visibility**: USER MESSAGE ONLY (Specialist Isolation)

**Filtering Logic**:
```python
# Show only the User's message, no other history
if current_phase == 1:
    # Find and display User message
    user_message = find_message_by_name(history_messages, "User")
    messages.append(HumanMessage(content=format_user_message(user_message)))
    messages.append(HumanMessage(content="Provide your initial fresh perspective..."))
```

**What Specialist Sees**:
- System prompt (role description + BASE_INSTRUCTION)
- **User's question** (shown in conversation history format)
- Instruction to provide initial perspective
- **No specialist responses** - complete isolation from other specialists

**Self-Awareness**: NO (no previous contributions exist yet - this is their first contribution)
**Group-Awareness**: NO (other specialists' messages not visible yet - they haven't posted)

**Important Note**: In Phase 1, specialists don't see their own messages simply because they haven't contributed yet, not because of active filtering. Each specialist contributes exactly once during Phase 1 in sequential order. This is fundamentally different from Phase 2 and Final Phase where own messages are actively filtered out.

**System Prompt**: Full role-specific system prompt with iterative discussion rules

**Characteristics**:
- Each specialist provides initial independent perspective
- No conversation history shown (only User message visible)
- No self-awareness (can't see own contributions - first time contributing)
- No awareness of what other specialists said (they haven't all posted yet, and execution is sequential)
- Each specialist contributes exactly once in Phase 1 (sequential execution order)
- Mandatory contribution - cannot pass
- Notice message exists in state but NOT shown to specialist

**Purpose**: Get fresh, unbiased initial viewpoints without anchoring or groupthink

**Algorithm Note**: Phase 1 has no active message filtering, but implementation deliberately shows ONLY User message to maintain complete isolation. Specialists execute sequentially (Context → Research → ... → [other specialists]), and each specialist sees ONLY the User message, not any prior specialists' Phase 1 responses. This ensures true independent thinking without any anchoring effects.

**Chair Does Not Participate in Phase 1**: Chair is positioned last in the execution order, but **skips Phase 1 silently**. Rationale:
- Chair's core functions are **synthesis, coordination, on-topic enforcement, likelihood assessment, and conflict resolution**
- **Chair needs specialists to have completed cross-pollination before synthesis is meaningful**:
  - Phase 1 is just initial independent assessments (specialists see only User, isolated)
  - Phase 2 is when specialists review what OTHERS said in Phase 1 and respond (cross-pollination begins)
  - Chair synthesizes in Phase 2 after specialists have had one full phase to contribute back
  - **Without Phase 2 cross-pollination, there's no discussion to coordinate** - just isolated independent assessments
- **All Chair functions require cross-pollination to be actionable**:
  - **Synthesis**: No discussion yet - just independent assessments with no interaction
  - **On-topic enforcement**: Need to see how specialists respond to each other, not just initial takes
  - **Conflict resolution**: Conflicts are IMPOSSIBLE in Phase 1 - specialists see only User message, have no awareness of each other, cannot disagree or debate
  - **Likelihood assessment**: Works best when specialists have reacted to each other's concerns
- Chair will see ALL Phase 1 responses AND Phase 2 responses when participating in Phase 2
- This saves one LLM call (~6-8 seconds) with no loss of information or functionality
- Chair's synthesis after Phase 2 is more valuable - captures both initial takes AND cross-pollinated discussion

**Instructions Given**:
```
This is your initial fresh perspective as {name}.
CRITICAL: You MUST provide substantive commentary.
DO NOT respond with "I have no further comments at this time" - that phrase is FORBIDDEN.
```

**Orthogonal Perspectives in Phases 1-6**:

Specialists are encouraged to leverage their unique roles to provide **distinct, non-overlapping viewpoints**, especially in early phases (1-6):

**Key Principles**:
- Each specialist brings their domain expertise and professional lens
- Aim for unique angles based on role-specific concerns
- **However**: Overlapping is better than holding back - contribute even if some overlap exists
- Specialists have access to each other's role descriptions in the XML `<from>` tags and can infer what perspectives others might offer
- Priority: Valuable contribution > Perfect orthogonality

**Examples of Orthogonal Perspectives**:
- User asks: "How should I structure my SaaS team?"
  - **Context**: Clarifies assumptions (stage, scale, constraints)
  - **Research**: Finds industry patterns and team composition data
  - **Skeptic**: Identifies risks in common team structures
  - **Ethicist**: Raises concerns about fair hiring, diversity, contractor treatment

- User asks: "Should I use microservices or monolith?"
  - **Context**: Clarifies team size, existing systems, urgency
  - **Research**: Provides patterns and tradeoff data
  - **Skeptic**: Identifies failure modes and over-engineering risks
  - **Database Architect**: Considers data consistency and transaction boundaries

**Final Phase (Dynamic - Can Occur at ANY Phase Number) Exception**:
- The **final phase** is triggered dynamically when one of four conditions occurs (see "Stage 4: Final Phase" section)
- Can happen at Phase 4, 5, 6, 10, or any other phase - completely dependent on discussion progression
- In Final Phase, specialists provide **comprehensive, detailed responses**
- Capture all processing effort - thoroughness is prioritized over conciseness
- Serves two purposes: (1) Complete answer if User is satisfied, (2) Rich context if User responds

**Implementation Note**:
This guidance is embedded in `BASE_INSTRUCTION` section "🎯 ORTHOGONAL PERSPECTIVES - BRING YOUR UNIQUE ANGLE (PHASES 1-6)" in `prompts.py`.

---

### Stage 2: Phase 2 - Review Others (Initial Assessment, Cross-Pollination)

**Purpose**: Mandatory cross-pollination - review what others said in Phase 1 and build on their perspectives

**History Visibility**: OTHER specialists from Phase 1 ONLY (Self-Filtered, Current Phase Filtered)

**Key Innovation - Atomic Phases**: 
- Non-Chair specialists see ONLY Phase 1 messages (prior phase), NOT current Phase 2 messages
- Chair sees Phase 1 AND Phase 2 messages (goes last, can synthesize current phase)
- This prevents premature responses and makes phases truly atomic

**Filtering Logic**:
```python
# Chair sees current phase (goes last), others see only prior phases
is_chair = (name == "Chair")

# Filter OUT own messages AND current phase messages (unless Chair)
for msg in history_messages:
    if speaker == "User" or speaker == "Notice":
        visible = True  # Always show User and Notice
    elif speaker == name:
        visible = False  # Never show own messages
    elif is_chair:
        visible = True  # Chair sees all (goes last)
    elif msg_phase < current_phase:
        visible = True  # Others only see PRIOR phases
    else:
        visible = False  # Current phase filtered for non-Chair
```

**What Non-Chair Specialist Sees**:
- System prompt (role description + BASE_INSTRUCTION)
- User's question
- **Notice messages** from Phase 1 and Phase 2 start
- Phase 1 responses from OTHER specialists (NOT their own)
- **NO Phase 2 messages yet** (atomic phases - current phase not visible)
- Instruction to review what others said in Phase 1

**What Chair Sees** (goes last):
- System prompt (role description + BASE_INSTRUCTION)
- User's question
- **Notice messages** from Phase 1 and Phase 2 start
- Phase 1 responses from OTHER specialists (NOT their own)
- **Phase 2 responses from all other specialists** (can synthesize current phase)
- Instruction to synthesize what others said

**Self-Awareness**: NO (own Phase 1 message filtered out for all)
**Group-Awareness**: 
- Non-Chair: YES for Phase 1 only
- Chair: YES for Phase 1 AND Phase 2 (goes last)

**System Prompt**: Full role-specific system prompt with iterative discussion rules

**Message Count Visibility (Non-Chair)**:
- Specialist sees: 1 User + 2 Notices + (N-1) Phase 1 specialists
- Reality in state: 1 User + 2 Notices + N Phase 1 + partial Phase 2 specialists
- **Own Phase 1 message invisible, ALL Phase 2 messages invisible**

**Message Count Visibility (Chair)**:
- Chair sees: 1 User + 2 Notices + (N-1) Phase 1 + (N-1) Phase 2 specialists
- Reality in state: 1 User + 2 Notices + N Phase 1 + N Phase 2 specialists
- **Own Phase 1 message invisible, other Phase 2 messages visible**

**Characteristics**:
- Non-Chair specialists see what OTHERS said in Phase 1 ONLY
- Chair sees what others said in Phase 1 AND Phase 2 (goes last, can synthesize)
- Own Phase 1 response is **completely hidden** from self for all specialists
- Can respond to what other specialists contributed in Phase 1
- Prevents self-anchoring and defensiveness
- Prevents premature responses (can't react to current phase messages)
- Mandatory contribution - cannot pass
- Notice messages visible (knows this is Phase 2)

**Purpose**: Build on others' ideas without self-referential bias or defending own position. Atomic phases prevent premature reactions.

**Chair's Critical Role in Phase 2**: Chair continues their synthesis role in Phase 2. Chair synthesizes what ALL other specialists said in both Phase 1 and Phase 2. 

**Important Distinction - Synthesis vs Compression**:
- **Synthesis** (Chair's normal job): Chair summarizes what specialists said - happens in EVERY phase (1, 2, 3+, Final)
- **Compression** (filtering mechanism): Specialist messages before a compression point are filtered out - happens at SPECIFIC points only
- **Phase 2 Compression Point**: When `COMPRESS_HISTORY_AFTER_PHASE3=true`, Chair's Phase 2 synthesis becomes the compression point
  - In Phase 3+, specialists see only User/Notice/Chair messages (Phase 1-2 specialist messages filtered out)
  - Chair always sees full history regardless of compression

**Instructions Given (Non-Chair)**:
```
You've seen what OTHER specialists said in Phase 1 (above).
You do NOT see your own Phase 1 response - only what others contributed.
You do NOT see Phase 2 messages yet - only completed Phase 1.
Provide your perspective considering what the other specialists have said.
```

**Instructions Given (Chair)**:
```
You've seen what OTHER specialists said in Phase 1 AND Phase 2 (above).
You go last - you can synthesize what everyone said in this phase.
Your Phase 2 synthesis becomes the compression point for Phase 3+ (when compression enabled).
Be comprehensive - capture ALL key points from both phases.
```

**Critical Design Decision**: By hiding their own Phase 1 contribution and filtering current phase:
- Can't defend or double-down on initial position
- Can't contradict themselves awkwardly
- Must genuinely engage with others' ideas
- Avoid circular self-referential reasoning
- Prevent premature reactions to incomplete discussions
- Chair can synthesize complete current phase (goes last)

---

### Stage 3: Phase 3+ - Continuing Conversation (Iterative Discussion)

**Purpose**: Iterative optional discussion - continue as long as specialists have new contributions, natural convergence through passing

**History Visibility**: FULL or COMPRESSED (based on configuration), with ATOMIC phase filtering

**Key Innovation - Atomic Phases Continue**: 
- Non-Chair specialists see ONLY PRIOR phases (not current phase)
- Chair sees PRIOR phases AND current phase (goes last, can synthesize)
- This prevents premature responses in all phases

**History Compression (Optional - Enabled by Default)**:

When `compress_history_after_phase3 = true` (default), Phase 3+ agents see:
- ✅ User's original question
- ✅ Notice messages (all phases)
- ✅ **Chair's Phase 2 synthesis** (comprehensive summary of all Phase 1 & 2 contributions)
- ✅ All Phase 3+ messages FROM PRIOR PHASES (atomic filtering)
- ✅ Chair sees current phase messages too (goes last)
- ❌ Individual Phase 1 specialist responses (compressed into Chair's synthesis)
- ❌ Individual Phase 2 specialist responses (compressed into Chair's synthesis)

**Rationale**: The Chair in Phase 2 has access to ALL Phase 1 and Phase 2 specialist responses and synthesizes them comprehensively. Phase 3+ becomes an "open table" discussion where specialists build on this foundation rather than re-reading all the individual details. This dramatically reduces context size while preserving all key points. Atomic phases prevent premature reactions.

**Filtering Logic** (when compression enabled):
```python
# Show User, Notices, Chair's Phase 2 response, and all Phase 3+ messages FROM PRIOR PHASES
# Hide Phase 1 & 2 individual specialist responses
# Chair sees current phase, others see only prior phases
# Uses phase metadata instead of position-based calculation
is_chair = (name == "Chair")

for msg in messages_to_show:
    msg_phase = msg.additional_kwargs.get("phase", "unknown")
    speaker = msg.name
    
    if speaker == "User" or speaker == "Notice":
        include_message(msg)  # Always visible
    elif msg_phase == 2 and speaker == "Chair":
        include_message(msg)  # Chair's Phase 2 synthesis is the compression point
    elif msg_phase in [1, 2]:
        skip_message(msg)  # Other Phase 1 & 2 responses hidden (compressed)
    elif msg_phase >= current_phase and not is_chair:
        skip_message(msg)  # Current phase filtered for non-Chair (atomic phases)
    else:
        include_message(msg)  # All Phase 3+ PRIOR phase messages visible
```

**Filtering Logic** (when compression disabled):
```python
# Show everything from PRIOR phases (atomic filtering still applies)
# Chair sees current phase, others see only prior phases
is_chair = (name == "Chair")

# Build history text from messages (in XML format for agents)
for msg in history_messages:
    msg_phase = msg.additional_kwargs.get("phase", "unknown")
    speaker = msg.name
    
    # Always show User and Notice
    if speaker == "User" or speaker == "Notice":
        visible = True
    # Filter out current phase for non-Chair (atomic phases)
    elif msg_phase >= current_phase and not is_chair:
        visible = False
    else:
        visible = True  # Show all prior phases
    
    if visible:
        timestamp = datetime.now().isoformat(timespec='milliseconds')
        xml_msg = f"<message><from>{speaker}</from><timestamp_iso>{timestamp}</timestamp_iso><phase>{msg_phase}</phase><content>{msg.content}</content></message>"
        conversation_text += xml_msg + "\n\n"
```

**What Non-Chair Specialist Sees**:
- System prompt (role description + BASE_INSTRUCTION with full iterative rules)
- User's question
- **Conversation history from PRIOR phases only** (atomic phases):
  - All Notice messages (Phase 1, Phase 2, Phase 3, etc.)
  - Specialist responses from PRIOR PHASES (not current phase)
  - **Including their own previous contributions** from prior phases
  - **NOT including current phase specialist messages** (atomic phases)

**What Chair Sees** (goes last):
- System prompt (role description + BASE_INSTRUCTION with full iterative rules)
- User's question
- **Complete conversation history including current phase**:
  - All Notice messages (Phase 1, Phase 2, Phase 3, etc.)
  - Specialist responses from ALL phases including current
  - **Including their own previous contributions** from prior phases
  - **Including current phase specialist messages** (goes last, can synthesize)

**Self-Awareness**: 
- Non-Chair: YES for PRIOR phases (sees own previous from completed phases)
- Chair: YES for PRIOR phases (current phase specialists visible but own filtered)

**Group-Awareness**: 
- Non-Chair: YES for PRIOR phases only (current phase filtered)
- Chair: YES for all phases including current (goes last, can synthesize)

**System Prompt**: Full role-specific system prompt with COMPLETE iterative discussion rules and progressive retraction guidance

**Message Count Example (Phase 3)**:
- Initial: 1 User + 1 Notice = 2 messages
- Phase 1: N specialists
- Phase 2: 1 Notice + N specialists
- Phase 3 start: 1 Notice = 1 message
- **Non-Chair sees**: User + all Notices + PRIOR phase specialists (not current Phase 3)
- **Chair sees**: User + all Notices + all specialists including current Phase 3 (goes last)

**Characteristics**:
- **Non-Chair specialists see PRIOR phases only** (atomic phases prevent premature responses)
- **Chair sees all phases including current** (goes last, can synthesize current phase)
- Can see own previous contributions from completed prior phases
- Can see all other specialists' contributions from prior phases
- Chair can see current phase specialists' contributions (goes last)
- Can see all Notice messages showing phase transitions
- Progressive retraction encouraged
- **Optional contribution** - can pass if nothing new to add
- System uses full iterative rules with passing mechanics

**Purpose**: Iteratively refine discussion with natural convergence through passing. Atomic phases prevent premature reactions to incomplete discussions.

**Progressive Retraction Mechanics**:
```
Phase 1-2: Mandatory collaborative phases - cannot pass
Phase 3: Early optional phase - passing rare
Phase 4-5: Middle phases - passing more common
Phase 6+: Later phases - most specialists passing, discussion winding down
```

**Instructions Given (Non-Chair)**:
```
The conversation history from PRIOR phases is shown above with timestamps and Notice messages.
Current phase messages are NOT visible yet (atomic phases).

YOUR PROCESS:
1. READ the conversation history from PRIOR phases above carefully
2. CRITICAL: Check what YOU ({name}) have already said in PRIOR phases - DO NOT REPEAT IT
3. Check what OTHER SPECIALISTS have said in PRIOR phases
4. THINK through NEW perspectives you haven't shared yet
5. SELF-ASSESS: Will I add genuine value if I contribute?
6. GAUGE PROGRESSION: Based on phase number (from Notice), is discussion reaching convergence?
7. BE INCREASINGLY CRITICAL: As phases increase, bar for "new insight" gets HIGHER
8. Contribute ONLY if you have something SUBSTANTIALLY NEW

You may PASS by saying: "I have no further comments at this time"
```

**Instructions Given (Chair, goes last)**:
```
The conversation history INCLUDING CURRENT PHASE is shown above with timestamps and Notice messages.
You go last - you can see what everyone said in this phase.

YOUR PROCESS:
1. READ the conversation history including current phase above carefully
2. SYNTHESIZE what other specialists said in the current phase
3. Check what YOU have already said in PRIOR phases - DO NOT REPEAT IT
4. THINK through NEW perspectives or synthesis you haven't shared yet
5. SELF-ASSESS: Can I add value through synthesis or new insights?
6. GAUGE PROGRESSION: Based on phase number (from Notice), is discussion reaching convergence?
7. Contribute synthesis or new insights

You may PASS by saying: "I have no further comments at this time"
```

**Critical Design Decision**: Atomic phase filtering with Chair exception enables:
- **Prevents premature responses**: Specialists can't react to incomplete current-phase discussions
- **Chair can synthesize**: Chair goes last and sees complete current phase to synthesize
- **Self-awareness**: Specialists avoid repeating themselves (see own prior phases)
- **Pattern recognition**: Specialists see topic exhaustion from prior phases
- **Natural convergence**: Specialists pass when truly nothing new to add
- **Authentic engagement**: Specialists build on complete prior context
- **Token savings**: Current phase filtering reduces context size for non-Chair specialists

---

### Stage 4: Final Phase - Wrap Up Without Further User Input (Settlement)

**Purpose**: Settlement phase - specialists provide final assessments when no further user input is expected, Chair delivers PRIMARY OUTPUT

**History Visibility**: OTHER specialists only (Self-Filtered, like Phase 2)

**Triggering Conditions** (Four Paths to Final Phase):

The transition to Final Phase follows a two-step pattern:
1. **Chair publicly announces the decision** (explains WHY)
2. **Notice announces the phase transition** (declares we're NOW in final phase)

This separation ensures:
- Chair is the "public face" of decisions - provides reasoning and context
- Notice is the "announcement system" - pure fact declarations, no explanations
- Think of Notice like a "speaker box" or "lunch bell" - signals phase transitions but doesn't participate in discussion

**Path 1: Natural Convergence - All Specialists Pass**:
```python
# In check_continuation node:
recent_messages = all_messages[-6:]  # Last complete phase
pass_count = sum(1 for msg in recent_messages 
                 if "no further comments" in msg.content.lower())

if pass_count == 6:  # ALL specialists passed
    print("[INFO] All specialists passed, triggering FINAL PHASE")
    return {"continue_discussion": True, "final_phase_needed": True}
```
**Announcement**: Notice directly announces final phase (no Chair announcement needed - passing is self-explanatory)

**Path 2: Stagnation Detection - Chair Detects Lack of Progress (Phase 4+)**:
```python
# In chair_agent(), after Chair generates synthesis:
if current_phase >= 4 and not state.get("final_phase_needed", False):
    stagnation_result = check_discussion_stagnation(state, chair_content, current_phase, config)
    
    if stagnation_result["stagnated"]:
        # Discussion has stagnated - trigger final phase
        result["final_phase_needed"] = True
        
        # Chair publicly announces the decision
        stagnation_announcement = AIMessage(
            content="Based on discussion stagnation analysis, we should move to the final discussion phase to provide concluding assessments.",
            name="Chair",
            additional_kwargs={"phase": current_phase, "timestamp": ...}
        )
        result["messages"].append(stagnation_announcement)
        # Then Notice announces phase transition in next cycle
```
**Announcement**: Chair explains stagnation → Notice announces phase transition

**Path 3: Token Limit Warning - Conversation Complexity 80-90%**:
```python
# In start_phase(), before executing phase:
if utilization_percent_min >= 80.0 and utilization_percent_min < 90.0:
    # Force final phase - Chair announces transition
    return {
        "agents_remaining": ["chair"],  # ONLY Chair speaks
        "final_phase_needed": True,
        "token_limit_triggered": True,  # Signal to Chair
    }
    # Chair sees token_limit_triggered flag and announces complexity concern
    # Then next cycle: Notice announces final phase transition
```
**Announcement**: Chair explains token complexity concern → Notice announces phase transition

**Path 4: Token Limit Hard Stop - Conversation Complexity ≥90%**:
```python
# In start_phase(), before executing phase:
if utilization_percent_min >= 90.0:
    # No room for final phase - Chair announces hard stop
    return {
        "agents_remaining": ["chair"],  # ONLY Chair speaks
        "continue_discussion": False,  # STOP after Chair
        "token_limit_hard_stop": True,  # Signal to Chair
    }
    # Chair sees token_limit_hard_stop flag and announces conversation must end
```
**Announcement**: Chair explains hard stop (no room for final phase) → Conversation ends

**Distinction**:
- **Natural Convergence**: Specialists explicitly pass (natural agreement) - no Chair explanation needed
- **Stagnation**: Chair detects rehashing without progress - Chair explains analysis
- **Token Warning (80-90%)**: System enforces token limits - Chair explains complexity
- **Token Hard Stop (≥90%)**: No room for final phase - Chair explains constraint

**Filtering Logic** (Same as Phase 2):
```python
# Filter OUT own messages, keep everything else
other_messages = [msg for msg in history_messages 
                  if not (hasattr(msg, 'name') and msg.name == name)]

conversation_text = "WHAT OTHER SPECIALISTS DISCUSSED\n"
conversation_text += "(Your own previous contributions are hidden - you're seeing only what others said)\n"
# Same display logic as Phase 2...
```

**What Specialist Sees**:
- **DIFFERENT system prompt** - clean, focused synthesis prompt WITHOUT iterative rules
- User's question
- **Complete discussion history** from OTHER specialists (all phases)
- All Notice messages
- **Own contributions completely hidden** from all phases
- Instruction for final synthesis

**Self-Awareness**: NO (all own messages from all phases filtered out)
**Group-Awareness**: YES (sees complete discussion from all other specialists)

**CRITICAL: Clean System Prompt (No Iterative Rules)**

```python
if is_final:
    # Extract ONLY role description, strip out BASE_INSTRUCTION
    role_description = extract_role_only(system_prompt)
    
    final_system_prompt = f"""{role_description}

FINAL ASSESSMENT PHASE:
You are providing your final assessment after reviewing the discussion.
Your perspective is crucial - every specialist must contribute their viewpoint.

IMPORTANT: You do NOT have access to your own previous contributions.
You are seeing only what OTHER specialists said. Provide a fresh assessment based on:
- The user's concern
- What other specialists have discussed  
- Your specialist role's unique perspective

Do NOT reference or recall your own earlier contributions. Provide your current assessment.
"""
```

**System Prompt Stripping Process**:
1. Parse system prompt to find role description
2. Find where BASE_INSTRUCTION starts (marker: "CRITICAL RULES:")
3. Extract only role description portion
4. Build new clean prompt focused on synthesis
5. **Remove all**:
   - Progressive retraction rules
   - Passing mechanics
   - Iterative discussion guidance
   - Convergence checking
   - Self-repetition warnings

**Message Count Example (Final Phase)**:
- State has: 1 User + all Notices + (N specialists × number of phases)
- Each specialist sees: User + all Notices + all other specialists' responses
- Each specialist DOES NOT see: Their own messages from prior phases

**Characteristics**:
- Triggered when ALL specialists pass in a single round
- Each specialist provides concluding assessment
- Own previous contributions **completely hidden** from all phases
- Sees full discussion from OTHER specialists (all phases, all contributions)
- **Clean focused system prompt** without iterative/passing rules
- Mandatory contribution - cannot pass
- Fresh perspective without anchoring to own previous positions
- **Tabling restrictions released**: Specialists previously tabled from discussing specific topics CAN address those topics again in Final Phase

**Chair's Special Role in Final Phase**:
- Chair speaks LAST (after all other specialists' final assessments)
- Chair's final response is the **PRIMARY OUTPUT** for the User
- Must provide **COMPREHENSIVE SUMMARY** including:
  - All key points from all specialists
  - All important questions raised
  - Areas of agreement and disagreement
  - Practical recommendations and next steps
  - Critical concerns or risks identified

**Purpose**: Fresh final synthesis without anchoring to own previous positions, using clean focused prompt

**Instructions Given**:
```
FINAL ASSESSMENT PHASE:
You are providing your final assessment after reviewing the discussion.

CONTEXT: Above, you have seen the discussion from OTHER specialists (not your own contributions).

Your fresh assessment is crucial. Provide your perspective based on:
- The user's concern
- What you've read from other specialists
- Your role's unique viewpoint

CRITICAL: You MUST provide substantive commentary.
DO NOT respond with "I have no further comments at this time" - that phrase is FORBIDDEN.
```

**Critical Design Decisions**:

1. **Self-Filtering Returns**: Like Phase 2, specialists can't see their own contributions
   - Prevents anchoring to previous positions
   - Enables fresh synthesis
   - Avoids defensive rehashing

2. **Clean System Prompt**: Strip out all iterative discussion rules
   - No progressive retraction guidance (not needed - must contribute)
   - No passing mechanics (passing forbidden in final)
   - No self-repetition warnings (can't see own contributions anyway)
   - Focus purely on synthesis and assessment
   - Cleaner, simpler prompt reduces cognitive load

3. **Mandatory Contribution**: Cannot pass
   - Every specialist must provide final assessment
   - Ensures all perspectives represented
   - No one can "skip out" of synthesis

4. **Complete Group Visibility**: Sees entire discussion from others
   - Can synthesize across all phases
   - Can identify key themes and consensus
   - Can spot gaps or concerns
   - Has full context to provide informed assessment

**Why This Stage Exists**:
- **Wrap up the meeting** when no further user input is expected
- After natural convergence (all passed in Phase 3+), need one more round for settlement
- Final synthesis with fresh eyes (not anchored to own prior statements)
- Clean prompts enable focused responses
- Ensures every specialist's voice in conclusion
- Prevents silent agreement - everyone must affirm or dissent explicitly
- **Critical**: Final Phase is ONLY valid when User has no more input - if User speaks during Final, phase is immediately invalidated and discussion reverts to Phase 3+

**Multi-Turn Interaction Vision (Future)**:

The Final Phase represents the specialists' **final internal iteration** before awaiting the next User interaction. This design supports a natural async collaboration pattern:

**Current Behavior**:
- User poses question → Specialists discuss internally (Phase 1 through Final) → Discussion ends with comprehensive answer
- Final Phase produces detailed, actionable responses from all specialists
- Chair's final synthesis serves as the primary output

**Future Multi-Turn Vision** (not yet implemented):
- User poses question → Specialists discuss internally → **Final Phase prepares comprehensive answer and WAITS**
- Specialists' Final Phase responses sit ready for User review
- **When User responds again** (provides feedback, asks follow-up, or gives new information):
  - New discussion cycle begins at Phase 3+ (iterative discussion)
  - Specialists incorporate User's new input and continue from current context
  - Can trigger another Final Phase when natural convergence occurs again
- This creates a **natural async dialog pattern**: internal team deliberation → comprehensive answer → User feedback → refined deliberation → updated answer

**Key Design Principles**:
- **Final Phase is NOT the end** - it's the end of one internal deliberation cycle
- **Comprehensive detail in Final Phase** serves two purposes:
  1. Provides complete answer if User is satisfied and doesn't respond
  2. Captures all processing effort for context if User does respond with follow-up
- **Specialists expect async gaps** - Final Phase assumes minimum 3h to ~1.5 days before possible User response
- **No premature closure** - Chair should NOT signal "wrapping up" or "finalizing" in non-final phases, only in Final Phase

**Why This Matters**:
- Specialists prepare their most thorough, detailed analysis in Final Phase
- User can review comprehensive output and decide whether to engage further
- System naturally supports iterative refinement through multiple User interactions
- Async collaboration pattern matches real-world usage (meetings, context switches, time zones)

## Primary Output

### Chair's Final Response
The **Chair's final phase response** is the primary output of the entire discussion system.

**When it appears**:
- After all specialists pass in a single round (triggering final phase)
- Chair speaks last in the final phase, after all other specialists' final assessments
- Appears as: `[timestamp] Chair said: [comprehensive summary]`

**What it contains**:
- Synthesis of ALL key points from all specialists across all phases
- Summary of ALL important questions raised to the User
- Areas where specialists agreed
- Areas where specialists disagreed or had different perspectives  
- Practical recommendations and next steps
- Critical concerns or risks identified

**Usage**:
- Users can read the entire discussion for full context
- Or focus on Chair's final response for a complete summary
- Chair's response is comprehensive (displayed as single line with whitespace collapsed for console viewing, but can be multi-line in original)

## Output Stream Architecture

### STDOUT (Light Green) - Public Conversation Log
**Purpose**: Clean chat log for piping/saving
**Contains**:
- Notice messages announcing phases
- Specialist responses with timestamps
- All public-facing conversation

**Format**:
```
[2025-10-08 14:32:15.234 EDT] Notice: We are starting discussion phase 1. All specialists, provide your initial independent perspective.
[2025-10-08 14:32:15.456 EDT] User: Specialists, please help me with this concern: "How should I structure my team?"
[2025-10-08 14:32:20.123 EDT] Specialist A said: @[User]. [response with all whitespace collapsed to single line]
[2025-10-08 14:32:27.891 EDT] Specialist B said: @[User]. [response with all whitespace collapsed to single line]
```

### STDERR (Mixed Colors) - Debug/Status Information
**Purpose**: Debug output, status updates, internal reasoning
**Contains**:
- Yellow: Status messages, phase headers, agent metadata
- Dark Green: Internal reasoning (NOT shared with other agents)
  - GPT-5: Native `<reasoning>` tokens (chain-of-thought from model)
  - Other models: `<think>` blocks (explicit reasoning tags)
- Agent invocation details (phase number, context size, message count)

**Note**: Internal reasoning is stripped from agent responses before being shared. This allows agents (especially Chair) to privately assess the discussion state without influencing other agents.

**Detailed Debug Output** (controlled by `SHOW_MESSAGE_DEBUG` environment variable):
- **Disabled by default** - raw message XML objects and execution summaries are hidden
- When enabled (`SHOW_MESSAGE_DEBUG=true`):
  - Message previews showing visibility (VISIBLE/FILTERED) for each message
  - Tabular format with checkmark/X in left column, grey vertical separator, then message details
  - XML format with `<from>`, `<timestamp_iso>`, and `<content>` tags
  - Plain "---" separators between each XML message for visual clarity
  - Agent execution summary boxes (AGENT, PHASE, INPUT TOKENS, REASONING TOKENS, OUTPUT TOKENS, etc.)
- **Default behavior** (`SHOW_MESSAGE_DEBUG=false`):
  - Only shows per-agent reasoning/thinking blocks (dark green) on stderr:
    - GPT-5: `<reasoning>` (native chain-of-thought)
    - Other models: `<think>` tags (explicit reasoning)
  - Agent execution summary boxes are completely hidden
  - Raw XML message objects are completely hidden
  - Human-readable conversation still appears on stdout (unchanged)

**Format**:
```
================================================================================
AGENT: Context
PASS: 1
CONVERSATION HISTORY: NO - Fresh independent response
OWN CONTRIBUTIONS: NO - No history available
INPUT CONTEXT: ~450 tokens (~1,800 chars)
MESSAGE COUNT: 3 messages being sent to LLM
================================================================================
✗ | FILTERED: <message><from>Notice</from><timestamp_iso>2025-10-08T12:55:05.123</timestamp_iso><phase>1</phase><content>Notice: We are starting discussion phase 1. All specialists, provide your initial independent perspective.</content></message>
---
✓ | VISIBLE: <message><from>User</from><timestamp_iso>2025-10-08T12:55:10.123</timestamp_iso><phase>0</phase><content>Specialists, please help me with this concern: "How should I structure my team?"</content></message>
---
✗ | FILTERED: <message><from>Specialist A</from><timestamp_iso>2025-10-08T12:55:15.456</timestamp_iso><phase>1</phase><content>@[User]. Need clarification on budget and timeline.</content></message>
================================================================================

<think>
[Internal reasoning - dark green]
</think>
```

**Tabular Format Details**:
- Left column: ✓ (visible, yellow) or ✗ (filtered, red)
- Separator: ` | ` (plain grey text, vertical bar with spaces)
- Right column: Status and XML message (colored to match left column)

## Colorization System

### ANSI Color Codes (`axion_swarm/colors.py`)
- **Dark Green** (`\033[32m`): `<think>` blocks (internal reasoning)
- **Light Green** (`\033[92m`): Public conversation messages
- **Yellow** (`\033[93m`): Status/debug messages
- **Reset** (`\033[0m`): Return to default

### Color Usage
- User input prompts: Default (no color)
- Notice messages: Light green on stdout, visible to users and agents
- Specialist responses: Light green on stdout
- Agent status headers: Yellow on stderr
- Thinking blocks: Dark green on stderr
- Debug messages: Default on stderr

## Timestamp System

### Purpose
Provides temporal context for both users and agents to:
- Track conversation pacing
- Observe response patterns
- Identify temporal clustering
- Understand discussion duration

### Implementation

**Two Different Formats**:
1. **XML Format (for Agents)**: ISO 8601 with milliseconds in `<timestamp_iso>` tag
   - Format: `YYYY-MM-DDTHH:MM:SS.mmm` (e.g., `2025-10-08T12:55:10.123`)
   - ALL message types (Notice, User, Specialist) have this tag
2. **Console Format (for Humans)**: Local timezone with milliseconds in brackets
   - Format: `[YYYY-MM-DD HH:MM:SS.mmm TZ]` (e.g., `[2025-10-08 12:55:10.123 EDT]`)
   - Prepended to all message content on stdout

**Generation**:
- Timestamps generated dynamically at display time (not stored in message state)
- Same message may show different timestamps to different agents (displayed when their turn occurs)
- Ensures consistent XML structure across all message types

**In Conversation History**:
```
[14:32:15.234] Notice: We are starting discussion phase 1...
[14:32:15.456] Context said:
[response content]

[14:32:27.891] Research said:
[response content]
```

## Internal Reasoning & Thinking

### Purpose
Specialists think deeply about the User's concern using internal reasoning that is NOT shared with other agents. This allows for:
- Thorough expert analysis without influencing others
- Private assessment of discussion state (especially for Chair)
- Transparent problem-solving visible to humans (on stderr)
- Independent thinking without anchoring to visible reasoning

### Implementation

**Dual System - GPT-5 and Other Models**:

1. **GPT-5/o1 Models** (native reasoning):
   - Model generates internal `reasoning_tokens` as part of its chain-of-thought process
   - Extracted from `response.response_metadata['reasoning']` or `response.response_metadata['usage']['reasoning_tokens']`
   - Displayed as `<reasoning>...</reasoning>` in dark green on stderr
   - Automatically stripped from the public response (never shared with other agents)
   - Token count tracked separately: `INPUT TOKENS + REASONING TOKENS + OUTPUT TOKENS = TOTAL`

2. **Other Models** (explicit tags):
   - Models use explicit `<think>...</think>` tags for internal reasoning
   - Extracted via regex pattern matching
   - Displayed in dark green on stderr
   - Stripped from public response before sharing with other agents
   - Reasoning tokens not separately tracked (included in output tokens)

**Display Format** (always visible on stderr, regardless of `SHOW_MESSAGE_DEBUG`):
```
<reasoning>
[GPT-5's internal chain-of-thought reasoning]
</reasoning>

<think>
[Model's explicit reasoning using tags]
</think>
```

**Key Properties**:
- ✅ Always displayed on stderr in dark green
- ✅ Visible to humans watching the conversation
- ❌ NOT included in conversation history
- ❌ NOT visible to other agents
- ❌ NOT shared in the public response

### Benefits

1. **Independent Thinking**: Agents think without being influenced by others' reasoning
2. **Transparent Process**: Humans can see the expert analysis behind each response
3. **Chair's Private Assessment**: Chair can assess convergence without signaling it publicly
4. **Quality Control**: Shows depth of analysis even when public response is concise
5. **Debugging**: Helps identify when agents are overthinking or underthinking

### Backward Compatibility

Both reasoning systems are supported simultaneously:
- GPT-5 models will primarily use native reasoning tokens
- Other models continue using `<think>` tags
- If both exist in a single response (rare), both are displayed
- Allows gradual migration as models add native reasoning support

## User Message

### Purpose
The user's question appears as a natural "User" participant in the conversation, making the discussion more intuitive and reducing prompt redundancy.

### Critical Importance
**User messages have the same permanent visibility as Notice messages:**
- **ALWAYS visible** in every pass and every phase
- **NEVER filtered** regardless of stage or agent
- Provides the foundational context for all specialist contributions
- Ensures agents never lose sight of what they're helping the User with

### Implementation
- Created by `start_phase()` function in `agents.py` at the start of Phase 1
- Added as `AIMessage` with `name="User"`
- Format: `Specialists, please help me with this concern: "{user_question}"`
- Appears in conversation history for all phases

### Key Benefits
- **Natural conversation flow**: User appears as a participant, not just metadata
- **Eliminates redundancy**: Question no longer repeated in every instruction message
- **Always visible**: Never filtered out - all agents see the User's request
- **Cleaner prompts**: Agents reference "the User's concern" naturally from history

### Filtering Behavior
**Universal Rules (Never Filtered)**:
- ✅ User messages: **PERMANENT VISIBILITY** (like Notice messages)
- ✅ Notice messages: **PERMANENT VISIBILITY** (like User messages)

**Phase-Dependent Filtering**:
- ⚠️ Specialist messages: May be filtered depending on phase (own messages hidden in Phase 2 and Final)
- All agents see the User message in ALL passes - it's the foundation of the discussion
- This ensures agents always understand what they're helping the User with

### Interactive Clarification (Optional)
- Agents can ask clarifying questions to the User in their responses
- Agents continue analysis without waiting for User responses
- If the User provides additional information (appears as new "User:" message), agents incorporate it in later phases
- This allows asynchronous clarification while keeping the discussion flowing

**Critical Design Principle - User Messages Always Reset Convergence**:
- User messages are ALWAYS incorporated and addressed
- **If User speaks after Phase 2** (whether during Phase 3+ OR during Final Phase):
  - System IMMEDIATELY reverts to Phase 3+ iterative logic
  - Final Phase is **invalidated** - we are no longer in Final Phase
  - Cannot remain in Final Phase while new User input exists
  - Discussion continues at Phase 3+ level until new User input is addressed
- **Final Phase only valid when**: all specialists pass AND no new User messages exist to address
- **Never regress to Phase 2**: If User speaks during Phase 3+ or Final, we stay at Phase 3+ (never go backwards)
- **Future Implementation**: Add User message detection in continuation logic (see "Continuation Logic" section)
- Rationale: User input always takes priority - specialists cannot conclude until User's concerns are addressed. Final Phase represents settlement, which is impossible with unaddressed User input.

## Notice Messages

### Purpose
System-generated messages that inform specialists (and users) about conversation phase transitions.

### Implementation
- Created by `start_pass()` function in `agents.py` with plain content (no embedded timestamp)
- Timestamps added dynamically at display time (both XML for agents and console for humans)
- Added to conversation state as `AIMessage` with `name="Notice"`
- Appear in both:
  - **Stdout**: Light green with timestamp prefix, visible to users
  - **Agent history**: Included in conversation context with `<timestamp_iso>` tag in XML format

### Message Content by Phase
```python
Phase 1: "We are starting discussion phase 1. All specialists, provide your initial independent perspective."
Phase 2: "We are starting discussion phase 2. All specialists, review what other specialists said and provide your perspective."
Phase 3+: "We are starting discussion phase {N}. All specialists, continue discussion or pass if you have nothing new to add per the guidelines and your perspectives."
Final: "We are starting the final discussion phase. All specialists, please provide your concluding assessment."
```

### Display Format
- **To Users (Console)**: Timestamp prepended in local timezone format: `[YYYY-MM-DD HH:MM:SS.mmm TZ] Notice: [message content]`
- **To Agents (XML)**: Same structure as all messages: `<message><from>Notice</from><timestamp_iso>[ISO 8601]</timestamp_iso><phase>N</phase><content>[message content]</content></message>`

### Filtering Logic
Notice messages are:
- ✅ Included in Phase 2 history (filtered to show only other specialists)
- ✅ Included in Phase 3+ history (full history)
- ✅ Included in Final Pass history (filtered to show only other specialists)
- ✅ Displayed on stdout for users

## Response Format Requirements

### Response Format
Specialists write naturally in their responses:
- ✅ Newlines are allowed and handled properly in XML `<content>` tags
- ✅ Agents see full multi-line responses preserved in XML structure
- ✅ Human console display collapses responses to single line for compact viewing
- ❌ No markdown formatting (bold, italics, headers, bullet points)
- ✅ **EXCEPTION**: Triple backticks (```) for structured/preformatted blocks (use sparingly)
- ✅ Multiple sentences allowed, natural paragraph structure fine
- ⚠️ **CRITICAL**: Keep responses CONCISE - this is text chat with humans reading (2-4 sentences ideal)

### Triple Backticks for Structured Content

**Purpose**: Present structured information (team lists, feature breakdowns, step-by-step plans) with preserved formatting.

**Format**:
```
Regular text here gets collapsed to single line.

```
Structured Content:
- Item 1: Description
- Item 2: Description
  - Nested item
```

More regular text that gets collapsed.
```

**Behavior**:
- Text **outside** triple backticks: Collapsed to single line (compact)
- Text **inside** triple backticks: Preserves newlines and indentation
- Human console: Indented 4 spaces for visual distinction
- Agents in XML: See full content with all formatting preserved

**Example Console Output**:
```
[2025-10-08 12:55:10.123 EDT] Specialist A said: Based on the requirements, here's the recommended approach:

    Key Considerations:
    - Aspect A: Define initial requirements
    - Aspect B: Core implementation approach
    - Aspect C: Data structure considerations
    - Aspect D: Infrastructure needs

Each aspect should be addressed systematically.
```

**Guidelines**:
- Use VERY sparingly - only when structured format significantly aids understanding
- Ideal for: team rosters, service tier comparisons, technical specifications
- NOT for: explanations, reasoning, opinions, recommendations (use prose instead)
- Keep blocks CONCISE - 5-10 lines maximum in most cases
- Don't use for regular conversational prose
- Open with ``` on its own line, close with ``` on its own line
- Agents can use multiple backtick blocks in one response if needed
- When in doubt: use prose, not a ``` block

**Conciseness Reminder**:
This is TEXT CHAT communication. Humans are reading specialist responses in a chat interface.
- Think deeply (use `<think>` tags), but write concisely
- 2-4 sentences for most responses is ideal
- Be respectful of the user's time and attention

### No Self-Labeling or XML Tags
Specialists must NOT include their name, role, or XML in responses:
- ❌ BAD: "Specialist A: The concern here is..."
- ❌ BAD: "Specialist B: Here's my input..."
- ❌ BAD: "As the Specialist, I believe..."
- ❌ BAD: "As Specialist A, here's my focused input..."
- ❌ BAD: "From my perspective as Specialist..."
- ❌ BAD: "<message>The concern here is...</message>"
- ✅ GOOD: "@[User], the concern here is..."
- ✅ GOOD: "@[User], based on available information..."

**Rationale**: The system automatically wraps responses in compact XML format for agent viewing:
```xml
<message><from>Specialist A</from><timestamp_iso>2025-10-08T12:56:15.237</timestamp_iso><phase>N</phase><content>The concern here is...</content></message>
```

If agents include their name or XML tags, it creates malformed structure or duplicate prefixes.

**Critical Understanding**: Each specialist name is UNIQUE in the session. The `<from>` tag already identifies them uniquely. Self-labeling suggests the agent doesn't understand:
1. They cannot be confused with another specialist (each name is unique)
2. The system already shows their role to all readers
3. The transcript structure makes speaker identity unambiguous

**Complete Isolation Principle**: Each specialist is a separate LLM instance with NO shared context outside the visible transcript. Agents must:
- Always check `<from>` tags to know WHO said each message
- Never assume others share their knowledge or jargon
- Never assume the User shares their technical background
- Understand that the transcript is the ONLY shared knowledge base

### Two Distinct Views

**Agent View (XML Format)**:
Agents see conversation history in compact XML (no indentation, saves tokens). ALL messages have the same structure:
```xml
<message><from>Notice</from><timestamp_iso>2025-10-08T12:55:05.123</timestamp_iso><phase>1</phase><content>Notice: We are starting discussion phase 1. All specialists, provide your initial independent perspective.</content></message>

<message><from>User</from><timestamp_iso>2025-10-08T12:55:10.123</timestamp_iso><phase>0</phase><content>Specialists, please help me with this concern: "How should I structure my team?"</content></message>

<message><from>Specialist A</from><timestamp_iso>2025-10-08T12:55:15.456</timestamp_iso><phase>1</phase><content>@[User]. Need clarification on budget and timeline.</content></message>
```

**XML Element Details**:
- `<from>`: Speaker identifier ("Notice", "User", or specialist role like "Specialist A")
- `<timestamp_iso>`: ISO 8601 timestamp with milliseconds (e.g., `2025-10-08T20:15:30.456`)
  - **ALL message types** have this tag: Notice, User, and Specialist messages
  - Generated dynamically at display time for consistency
- `<phase>`: Phase number when message was created (User=0, Phase 1=1, Phase 2=2, etc.)
  - Stored in message metadata at creation time for reliable tracking
  - Used for compression filtering and temporal context
  - LLMs can see which phase each message came from
- `<content>`: The actual message content - can contain newlines, they are preserved in XML
- Format: One message per XML block, no indentation (optimized for LLM parsing and token efficiency)
- The `<content>` tags provide clear boundaries, so multi-line content is handled properly

**Console View (Traditional Chat)**:
Users see traditional timestamped chat format on stdout with ALL whitespace collapsed for compact viewing:
```
[2025-10-08 12:55:05.123 EDT] Notice: We are starting discussion phase 1. All specialists, provide your initial independent perspective.
[2025-10-08 12:55:10.123 EDT] User: Specialists, please help me with this concern: "How should I structure my team?"
[2025-10-08 12:55:15.456 EDT] Specialist A said: @[User]. Need clarification on budget and timeline.
```

**Console Formatting**:
- Timestamps shown in local timezone: `YYYY-MM-DD HH:MM:SS.mmm TZ` (e.g., `2025-10-08 12:55:10.123 EDT`)
- All newlines, tabs, and multiple spaces are collapsed to single spaces
- This creates compact single-line display for human readability
- The original multi-line content is preserved in state for agents to see

### Explicit Addressing with @ Mentions

**Purpose**: Make it 100% clear who each part of a message is directed to, enabling natural group discussion flow.

**Format**: `@[Name], message content`
- Brackets `[ ]` provide visual distinction
- Comma `,` provides natural flow (like "Dear John, ..." - addressing then message)
- Messages are isolated in `<content>` XML tags (structural clarity)
- Familiar pattern (like addressing someone in email/chat)

**@ Mention Targets**:
- `@[User], ` - Address the User (their explicit question or request)
- `@[Other specialist name], ` - Address specific specialist (full role name with "specialist")
- `@[Chair], ` - Address Chair (coordinator)
- `@[All], ` - Address everyone (optional, for general observations)

**Usage by Pass**:
- **Phase 1**: Only `@[User], ` (independent assessments, only talking to User)
- **Phase 2**: Primarily `@[User], ` (still focused on User's request)
- **Phase 3+**: Can use `@[User], `, `@[Specialist name], `, or `@[All], ` (open discussion phase)

**When to Use @[User] vs Speaking "To All"**:
- **Use `@[User]` mention**: Only for unanswered items that need User input (questions, clarification requests, information gaps)
- **Speak "to all" (no mention)**: When providing answers, insights, or information in response to the User's question
- **Rationale**: Answers are for everyone's benefit in the discussion. Direct mentions should be reserved for interactive dialogue requiring user response.
- **Examples**:
  - ✅ "@[User], [clarifying question about missing detail]?" (question - needs input)
  - ✅ "[Technical recommendation with reasoning]." (answer - no mention)
  - ✅ "[Insight or observation about the approach]." (insight - no mention)

**Message Structure - Statements First, Then Engage Individuals**:
- **Start with statements and answers**: Provide insights, recommendations, and observations WITHOUT mentions (speaking to all)
- **Then mention individuals to engage further**: Place `@[User]` or `@[Other specialist]` mentions at the END to ask questions or seek engagement
- **Structure**: `[Statements/answers without mention]. [More insights without mention]. @[User], [clarifying question]?`
- **Rationale**: Provides value upfront to everyone, then engages specific individuals for further dialogue at the end

**Multiple Recipients**:
Specialists can address multiple people in the same response - this is encouraged for natural discussion.

**Use numbered format for clarity** (recommended when addressing 2+ recipients):
```
1) @[User], [answer or recommendation]. 2) @[Other specialist], [response to their suggestion or acknowledgment].
```

**Why numbering helps:**
With complex sentences containing their own punctuation (colons, semicolons, commas), numbering makes it crystal clear where one recipient's content ends and another begins.

**Example showing the clarity gain:**
```
1) @[Other specialist], [response to their suggestion with details]. 2) @[Chair], [acknowledgment or question]. 3) @[User], [clarifying question]?
```

Without numbers, complex punctuation creates ambiguity about which content goes with which @ mention.

**Examples**:
```xml
<!-- Phase 1 - Only asking clarification (needs input - use @[User]) -->
<content>@[User], [specific clarifying question about missing information]?</content>

<!-- Phase 3 - Only providing answer (no mention needed - speaking to all) -->
<content>[Technical recommendation with supporting reasoning and specific details].</content>

<!-- Phase 3 - Answer FIRST, then question to User at END (preferred structure) -->
<content>[Technical recommendation or insight without mention]. [Additional supporting detail]. @[User], [clarifying question]?</content>

<!-- Phase 3 - Asking another specialist a question (needs input - use mention) -->
<content>@[Other specialist], [question about their earlier statement or suggestion]?</content>

<!-- Phase 3 - Raising concern to all (no mention - general observation) -->
<content>[Concern or consideration about the approach being discussed].</content>

<!-- Phase 3 - Multiple insights FIRST, then questions at END (numbered for clarity) -->
<content>1) [Technical insight without mention]. 2) [Additional insight without mention]. 3) @[Other specialist], [question about their approach]? 4) @[User], [clarifying question]?</content>
```

**Natural Flow Guidance**:
Write @ mentions as if you're addressing someone, then continue naturally with a new sentence:
- ✅ `@[User], [your message content]...` (natural - addressing with comma)
- ✅ `@[Other specialist], [your message content]...` (addressing with comma)
- ✅ `[Statement or insight without mention].` (speaking to all - no mention)
- ❌ `@[User]: [content]:` (double colon creates ambiguity about context changes)
- ❌ `@[User]. [content]:` (period then colon is awkward)

The @ mention is a complete addressing statement (like "Dear John."), then start your message.

**Inter-Specialist Questions & Clarifications (Phase 3+)**:
Specialists can ask each other questions and respond to each other in later passes:
- `@[Other specialist], [question about their earlier statement or suggestion]?`
- `@[Chair], [response or clarification about earlier point]...`
- Natural collaborative flow where specialists build on each other's points
- Each specialist is a separate LLM instance - @ mentions make it explicit who should respond

**Benefits**:
- User immediately sees what's directed at them vs. specialist-to-specialist dialogue
- Other specialists (separate LLM instances) know when they're being asked a question
- Supports natural multi-party conversation with clear audience identification
- Multiple sentences can contain different @ mentions to different recipients
- Creates authentic group discussion dynamic
- Enables specialists to clarify each other's technical terms and build shared understanding
- Comma provides natural flow for addressing recipients

**What Specialists See**:
When others mention them: `@[Their role name], ...` (their full role name in brackets with comma)

### Identity Analysis Requirement (2025-10-08)

**Critical Thinking Steps**: Agents must explicitly analyze message identities in their `<think>` blocks:

**Phase 1**:
- Check `<from>` tag to identify User and infer their role/background

**Phase 2**:
- Check `<from>` tags to identify who said each message
- Map specialist names to their contributions

**Phase 3+**:
1. Check `<from>` tags in EVERY message
2. Find own messages with `<from>{name}</from>`
3. Map each OTHER specialist to their contributions
4. Check for `@[{name}]` mentions
5. Decide WHO they're responding to

**Purpose**: Forces deliberate analysis of speaker identity, prevents assumptions about shared knowledge, ensures agents understand they're separate LLM instances.

### Enforcement
- Explicit instructions in BASE_INSTRUCTION with XML format examples
- Prominent 🚫 warnings before every response in all phases
- Identity section clarifies automatic XML wrapping and complete isolation
- Multiple instruction points reinforce requirement
- Explicit thinking steps require identity analysis
- "WHY SELF-LABELING IS FORBIDDEN" explanations added

## Agent Isolation & Fresh LLM Instances

### Per-Invocation Fresh Instances
```python
def get_llm(agent_name: str, agent_config: AgentConfig) -> ChatOllama:
    # ALWAYS create a fresh instance - no context leakage
    llm = ChatOllama(...)
    return llm
```

### Key Points
- Each agent invocation gets completely new LLM instance
- Zero context sharing between invocations
- Agents only know what's in conversation history
- No hidden state or memory between turns

### Message Filtering by Stage

**Terminology**:
- **Phase** (noun): One complete cycle where all specialists have the opportunity to contribute. Multiple phases enable iterative refinement of the discussion.
- **Pass** (verb): To skip contributing by saying "I have no further comments at this time"

**Universal Rules (All Passes)**:
- ✅ User messages: **PERMANENT VISIBILITY** (never filtered, always visible like Notice messages)
- ✅ Notice messages: **PERMANENT VISIBILITY** (never filtered, always visible like User messages)

**Pass-Specific Filtering (Specialist Messages Only)**:
- **Phase 1**: Show User only (no filtering needed - specialists are contributing for the first time sequentially)
- **Phase 2**: Show User + Notice + other specialists (**ACTIVE FILTERING**: filter out own Phase 1 response)
- **Phase 3+**: Show User + Notice + all specialists (no filtering, full history)
- **Final**: Show User + Notice + other specialists (**ACTIVE FILTERING**: filter out all own previous responses)

**Filtering Logic**:
```python
# Filters out only the specialist's own messages, keeps User + Notice + others
# Note: Active filtering only happens in Phase 2 and Final Pass
# Phase 1 has no filtering (specialists contributing for first time)
# Phase 3+ has no filtering (full history shown)
filtered = [msg for msg in history if not (msg.name == specialist_name)]
```

**Key Principles**: 
- User and Notice messages anchor every pass, providing consistent context throughout the discussion
- Phase 1: No filtering (first-time contributions, sequential execution)
- Phase 2 & Final: Active filtering (own messages deliberately hidden for fresh perspective)
- Phase 3+: No filtering (full awareness for convergence)

## Progressive Retraction System

### Staying On Topic: Explicit vs Implicit Concerns

**Understanding the User's Request** (BASE_INSTRUCTION - all agents):
- Consider BOTH the User's explicit request (what they stated directly) AND implicit concerns (underlying unknowns or needs)
- Primary focus is the EXPLICIT request - stay on topic
- Think about what might be implied or what the User might not know to ask about
- Only raise implicit concerns if they are PERTINENT to answering the explicit request
- Avoid tangents - everything said should help address what the User explicitly asked

**Asking Clarifying Questions and Providing Assessments**:
- Agents can MIX clarifying questions with substantive assessments in the same response
- **Provide definitive answers first**: Answer what you can definitively, then ask about what's unclear
- Only ask questions that are PERTINENT to answering the User's explicit request
- Avoid questions about tangential or unlikely scenarios
- Asking focused questions shows thoroughness; asking tangential questions wastes time
- **IMPORTANT**: If you have no reasonable clarifying questions linked to answering the explicit request, and no substantive insights to add, you should PASS instead of contributing questions just to participate
- This is especially important as passes progress - avoid rabbit holes

### Providing Definitive Answers with Transparency

**Core Principle**: Answer as definitively as possible based on available information, while being transparent about limitations.

**Guidance**:
- **Answer what you can**: Provide definitive answers for everything you can assess with confidence
- **Partial answers are allowed**: If you can only answer part of the question, do so
- **Identify blocking concerns**: Raise major concerns that prevent a complete assessment
- **Be transparent about gaps**: If you cannot give a complete answer, clearly state:
  - What parts you CAN answer definitively
  - What information is missing
  - Why the missing information matters
  - What major concerns remain
- **When unable to answer but not passing**: If you cannot answer the User's explicit concern(s) but are still contributing (not passing), concisely specify what information would be needed before you could answer, **if it's within your role to answer at all**
  - First assess: Is this question within my specialist expertise?
  - If yes and missing info: "To answer [User's question], I would need to know [specific information]."
  - If no (outside expertise): Pass instead of attempting to answer

**Example format**: "Based on available information, I can say [definitive answer to part A]. However, I cannot fully assess [part B] because [reason], which is critical for [why it matters]."

**When Missing Critical Information**: "To answer [User's specific question], I would need to know [specific missing information]. Without this, I can only address [what you can answer]."

**Purpose**: Users get maximum value from partial information while understanding exactly what's known vs. uncertain, and what specific information would unlock fuller answers.

### Changing Your Mind

**Agents are allowed to change their perspective** as the discussion progresses and new information emerges.

**When changing your mind, you MUST explicitly state**:
1. That you've changed your mind
2. Your old perspective
3. Your new perspective
4. Why you changed your mind

**Example format**: "I've changed my mind. Previously I thought [old view], but now I believe [new view] because [reason]."

**Purpose**: Transparency about perspective evolution helps the User understand the reasoning process and builds trust in the final recommendations.

### Skill-Set Relevance

**Core Principle**: Agents should contribute based on whether their specific expertise applies to the User's question.

**Guidance**:
- **Contribute when expertise applies**: Each specialist should assess whether their skill-set is relevant to the discussion
- **Pass gracefully if expertise doesn't apply**: If a specialist's knowledge doesn't add value to the current question, they should pass
- **Examples**:
  - Platform-specific specialists should pass on questions unrelated to their platform
  - Architecture specialists should pass on questions about specific implementation details outside their domain
  - Ethics specialists should pass on purely technical implementation details
  - Research specialists should pass if no facts need verification
- **Purpose**: Ensures all contributions are substantive and relevant, preventing "participation for participation's sake"

**Self-Assessment Questions**:
- "Does this discussion benefit from MY specific expertise?"
- "Does my {specialist} expertise add value to this discussion?"
- "Does my {specialist} expertise still add value to this evolving discussion?"

**Implementation**: Included as a thinking step in all pass templates, with explicit guidance to pass if expertise doesn't apply.

### Realism and Pragmatism
To prevent infinite discussion about unlikely scenarios:

**Shared guidance (BASE_INSTRUCTION - all agents):**
- Focus on realistic scenarios and practical concerns
- As passes increase, prioritize likely situations over edge cases
- Self-assess: "Is this realistic or an unlikely edge case?"
- Self-assess: "Is this pertinent to their explicit concern or a tangent?"
- Balance thoroughness with pragmatism
- Avoid spiraling into improbable "what-if" scenarios

**Chair-specific role (unique to Chair):**
- Assess and communicate likelihood of concerns raised by OTHER specialists (high/moderate/low)
- Example: "Specialist A raised X (highly relevant), Specialist B noted Y (less likely edge case)"
- Guides discussion toward practical, actionable concerns
- **Tabling authority**: Can table cyclical debates between specialists (see "Chair's Tabling Authority - Conflict Resolution" section)

**Phase 3+ reinforcement:**
- REALISM added as explicit thinking step during critical convergence phase
- Keeps agents focused when it matters most

**Purpose**: Ground discussion in actionable, practical guidance for the User

### Natural Reasoning (No Explicit Meta-Info)
Agents infer conversation stage from:
- Notice messages (indicate phase number)
- Timestamps (show conversation pacing)
- Message count (observable in history)
- Content patterns (topic exhaustion)

**NOT told explicitly**:
- ❌ "You are in phase 5"
- ❌ "There are 30 messages in history"
- ❌ "This is the convergence phase"

### Human-Like Reasoning Prompts
- "Looking at phase number (from Notice), timestamps, and conversation flow..."
- "Check Notice messages - if FINAL PHASE, I MUST contribute"
- "As phases increase (observe Notice messages), be MORE LIKELY to pass"

### Passing Mechanics
**Specialists can pass by saying**: "I have no further comments at this time"

**When to pass**:
- Would repeat previous contribution
- No new insights to add
- Others already covered the point
- Discussion reaching convergence
- **Only have tangential questions without substantive insights**
- **Would be going down rabbit holes unrelated to explicit request**
- **No reasonable clarifying questions linked to answering explicit request**
- **Tabled from discussing a specific topic** (Chair's tabling authority - applies until Final Phase)

**Code-Enforced Passing Rules**:
```python
# From agents.py - actual implementation
is_mandatory = is_final or current_phase_check <= 2

# Phases 1-2: Mandatory contribution (passing rejected by code)
# Phase 3+: Optional contribution (passing allowed)
# Final Phase: Mandatory contribution (passing rejected by code)
```

**Practical Progressive Likelihood**:
- **Phase 1-2**: Cannot pass (code enforcement) - must contribute substantive insights or pertinent questions
- **Phase 3+**: Can pass - specialists increasingly likely to pass as discussion progresses:
  - Phase 3: Rare, only if truly nothing to add
  - Phase 4-5: More common as topics exhaust (bar for "substantive" increases)
  - Phase 6+: Very common, expected behavior (avoid rabbit holes, pass if only tangential questions)
- **Final Phase**: Cannot pass (code enforcement) - all specialists must contribute

### Consensus Detection (Implicit, System-Level)
When all specialists pass in a single round:
- Triggers Final Phase automatically
- System message logged to stderr
- One more round for concluding assessments

**Important**: Consensus detection is purely system-level. Agents should NEVER publicly declare whether consensus is or isn't possible, as this could bias subsequent phases and undermine independent judgment. The system detects consensus implicitly through the progressive retraction mechanism (all agents passing).

**Chair's Consensus Assessment**:
- Chair MAY privately assess consensus likelihood in `<think>` tags (visible in console logs for observability)
- Chair must NOT mention consensus in public response (shared with other agents)
- This maintains system observability without creating bias

## Message History Construction

### Stage-Dependent History Text
Built dynamically when agent is invoked:

```python
# Phase 2 or Final (XML format for agents)
other_messages = [msg for msg in history if msg.name != agent_name]
for msg in other_messages:
    # All messages get timestamps and phase metadata in XML format
    timestamp = datetime.now().isoformat(timespec='milliseconds')
    msg_phase = msg.additional_kwargs.get("phase", "unknown")
    xml_msg = f"<message><from>{msg.name}</from><timestamp_iso>{timestamp}</timestamp_iso><phase>{msg_phase}</phase><content>{msg.content}</content></message>"
    text += xml_msg + "\n\n"
```

### Key Implementation Details
- **Timestamps**: Generated dynamically at display time (not stored in message state)
  - **ALL message types** (Notice, User, Specialist) have `<timestamp_iso>` tag in XML format
  - ISO 8601 format with milliseconds: `2025-10-08T12:55:10.123`
  - Same message structure for all types ensures consistency
- **Phase Metadata**: Stored in message at creation time, visible in XML
  - Tagged via `additional_kwargs={"phase": N}` when message is created
  - Extracted and displayed as `<phase>N</phase>` tag in XML
  - User message = phase 0, Phase 1 messages = phase 1, etc.
- **XML Format**: Messages shown to agents in compact XML structure (no indentation)
  - Every message: `<message><from>...</from><timestamp_iso>...</timestamp_iso><phase>...</phase><content>...</content></message>`
- **Filtering**: Applied before building text based on stage (Phase 1, Phase 2, Phase 3+, Final)
  - Uses phase metadata for compression filtering (no position calculations)
- **No numbering**: Messages shown to agents don't have message numbers, only timestamps and phase
- **Debug output**: Debug logs (stderr) include "---" separators between messages and VISIBLE/FILTERED indicators

## Configuration System

### Files
- `config.py`: Model and sampling parameter configuration
- `.env`: Environment variable overrides (optional)

### Configuration Architecture

**Model + Context Window Tuple**: The model and context window are paired together as a tuple since the optimal context window is specific to each model/quantization combination. Sampling parameters (temperature, top_p, etc.) are shared across all models and can be reused.

**Where to Pick Combinations**: Model+context tuples are defined at the top of `config.py` (lines 8-30). To change models:
1. **Easiest**: Change line 27: `DEFAULT_MODEL_TUPLE = MODEL_QWEN3_30B_Q4` to point to a different combination
2. Add your own model+context tuple at the top of the file, then point `DEFAULT_MODEL_TUPLE` to it
3. Override via environment variables `DEFAULT_MODEL` and `OLLAMA_NUM_CTX`

### Environment Variables
```bash
# Model + Context Window Tuple (paired because context is optimized per quantization)
DEFAULT_MODEL=hf.co/bartowski/Qwen_Qwen3-30B-A3B-Thinking-2507-GGUF:Q4_K_M
OLLAMA_NUM_CTX=50560  # Optimized for Q4_K_M quantization

# Sampling parameters (shared across all models)
OLLAMA_TEMPERATURE=0.6
OLLAMA_TOP_P=0.95
OLLAMA_TOP_K=20
OLLAMA_MIN_P=0.0

# History compression (default: true)
# When enabled, Phase 4+ hides Phase 1, 2, & 3 individual responses, showing only Chair's Phase 3 synthesis
COMPRESS_HISTORY_AFTER_PHASE3=true  # Set to "false" to disable compression

# Ollama server
OLLAMA_BASE_URL=http://localhost:11434

# Per-agent overrides (optional)
CHAIR_MODEL=...
CHAIR_NUM_CTX=...  # Must be specified if CHAIR_MODEL is changed
RESEARCH_MODEL=...
RESEARCH_NUM_CTX=...
```

### Agent Configuration Dataclass
```python
@dataclass
class AgentConfig:
    model: str
    num_ctx: int  # Context window - paired with model/quantization
    temperature: float = 0.6  # Sampling parameters (reusable)
    top_p: float = 0.95
    top_k: int = 20
    min_p: float = 0.0
    base_url: str = "http://localhost:11434"
```

### Predefined Model-Context Combinations

**Location**: Top of `config.py` (easy to find and modify)

```python
# Qwen3 30B A3B Thinking - Q4_K_M quantization (default)
MODEL_QWEN3_30B_Q4 = (
    "hf.co/bartowski/Qwen_Qwen3-30B-A3B-Thinking-2507-GGUF:Q4_K_M",
    50560  # Optimized for Q4_K_M quantization
)

# Add more model+context combinations as needed
# Example format:
# MODEL_YOUR_MODEL = ("model_name", context_size)
```

**How to Select** (at top of `config.py`, line 27):
```python
# -----------------------------------------------------------------------------
# SELECT DEFAULT MODEL HERE - Change this line to switch models
# -----------------------------------------------------------------------------
DEFAULT_MODEL_TUPLE = MODEL_QWEN3_30B_Q4  # ← Just change this!
# -----------------------------------------------------------------------------
```

**To add a new model**:
1. Define the tuple above the selection line
2. Change `DEFAULT_MODEL_TUPLE` to point to your new model

## State Management

### LangGraph State (TypedDict)
```python
class OverallState(TypedDict):
    messages: Annotated[list[BaseMessage], add_messages]  # Conversation history (with phase metadata)
    user_goal: str                    # The user's question
    phase_number: int                 # Current phase number (1, 2, 3, ...)
    agents_remaining: list[str]       # Agents who haven't spoken this phase
    continue_discussion: bool         # Whether to continue or end
    final_phase_needed: bool          # Trigger for final phase
    final_phase_done: bool            # Track if final phase completed
    specialist_presence: dict[str, str]  # Specialist room presence: {"context": "in", "cloud": "available", ...}
    last_compression_message_index: int  # Index of last compression point (Chair summary)
    rate_limit_compression_pending: bool # True if we need to do rate-limit compression
```

### Message Types in State
- `AIMessage(content=..., name="User", additional_kwargs={"phase": 0})`: User's question (added at start of Phase 1)
- `AIMessage(content=..., name="Notice", additional_kwargs={"phase": N})`: Notice messages with phase number
- `AIMessage(content=..., name="Context", additional_kwargs={"phase": N})`: Specialist responses with phase number
- `AIMessage(content=..., name="Research", additional_kwargs={"phase": N})`: Specialist responses with phase number
- etc.

**Phase Metadata**: All messages include `additional_kwargs={"phase": N}` where:
- User message: phase = 0 (before phases start)
- Phase 1 messages: phase = 1
- Phase 2 messages: phase = 2
- etc.

This metadata enables:
- Reliable compression filtering without position-based calculations
- Temporal context for LLMs (they see which phase each message came from)
- Simplified message tracking and debugging

### State Updates
- `add_messages` annotation: Messages are appended, not replaced
- Each node can add messages to state with phase metadata
- `start_phase`: Adds Notice message with current phase number
- Each agent: Adds their response message with current phase number

### Specialist Room Presence

**Purpose**: Control which specialists actively participate in phase rotations versus those available to be brought in on-demand.

**Concept**: Specialists exist in two states:
- **"in"**: Actively participating in phase rotations (speak each phase)
- **"available"**: Can be brought into the room by Chair when needed

**State Management**:
```python
specialist_presence: dict[str, str]  # {"context": "in", "research": "in", "cloud": "available", ...}
```

**Key Characteristics**:
- Chair is ALWAYS present and not tracked in `specialist_presence` dict
- All specialists (both "in" and "available") see the full specialist roster in their prompts
- Only "in" specialists are added to `agents_remaining` for phase execution
- Status changes are persisted in checkpoints

**Core Team Configuration** (`config.py`):
```python
DEFAULT_CORE_TEAM = [
    "context",
    "research",
    "skeptic",
    "ethicist",
]

def get_core_team() -> list[str]:
    """Get core team from config or environment variable CORE_TEAM."""
    env_core = os.getenv("CORE_TEAM", "")
    if env_core:
        return [s.strip() for s in env_core.split(",")]
    return DEFAULT_CORE_TEAM

def initialize_specialist_presence() -> dict[str, str]:
    """Initialize presence mapping with core team 'in', others 'available'."""
    # Returns: {"context": "in", "research": "in", ..., "cloud": "available", ...}
```

**Direct Specialist-to-Specialist Collaboration**:

Specialists can @mention ANY specialist from the full roster (both "in" and "available") when their expertise would help address the User's concerns:

- **Purpose**: Ensures the right expertise addresses each aspect of the User's concerns
- **Pattern**: `"@[Specialist Name], [your question about their domain]?"`
- **Examples**:
  - `"@[Specialist Name specialist], what's your perspective on [topic within their domain]?"` (if "in")
  - `"@[Specialist Name specialist], how would [specific concern] affect [aspect of discussion]?"` (available or "in")
  - `"@[Research specialist], do you have sources on [topic being discussed]?"` (if "in")

**Important distinctions**:

- **For specialists "in" the room**: They will see your @mention and can respond in the next phase
- **For "available" specialists**: You can @mention them, but Chair decides whether to bring them in
  - If Chair agrees they're needed, Chair will @mention them too (which brings them into the room)
  - If you want to explicitly request an "available" specialist, ask Chair: `"@[Chair], please bring in @[Specialist Name] to help with [reason]."`
  - Chair has final authority on bringing "available" specialists into active participation

- **When to use**: When your contribution or answer to the User depends on understanding another specialist's domain expertise
- **Distinction from deferral**: This is actively seeking collaboration, not stepping back from a topic

**Tavily Search Tool - Real-Time LLM-Optimized Information**:

Specialists have access to Tavily Search for current, real-time information specifically optimized for LLM applications.

**Tavily** is a search API purpose-built for AI agents, providing structured, citation-ready results with relevance scoring and LLM-optimized content snippets from multiple trusted sources.

**CRITICAL - ALL SPECIALISTS MUST UNDERSTAND**:
- **Search results are CURRENT INTERNET KNOWLEDGE** - not from LLM training data
- **Search results are AUTHORITATIVE** - they represent live, real-time web content retrieved specifically for this discussion
- **ALL specialists must HEAVILY VALUE search results** - they override outdated training knowledge
- **When search results conflict with training data, DEFER TO SEARCH RESULTS**
- **Search results must be MERGED INTO ANALYSIS** - treat them as ground truth and integrate with conversation context
- **Any specialist can request searches** - not just Research (though Research has primary fact-checking responsibility)
- **Search results are visible to the entire room** - all specialists see them and should reference them when relevant

**When Specialists Should Search - Recognize Training Limitations**:
- **Training data has a cutoff date** - specialists may not know the latest state-of-the-art
- **The world evolves rapidly** - best practices, standards, methodologies, and available resources change frequently
- **Specialists should proactively search** when uncertain about currency of their knowledge
- **Better to search than guess** - especially for topics involving "latest", "current", "recent", or "best practices"
- **Key signals to search**: Discussing versions, pricing, availability, new approaches, resources, methodologies, regulatory changes
- Pattern: If you find yourself saying "as of my training data" or "last I knew", search instead

**INPUT - How Specialists Use Search**:

- **Syntax**: `@[Search][exact query here]`
- **Primary User**: Research specialist (with explicit fact-checking responsibility), but any specialist can use it
- **Usage Examples**:
  - `@[Search][current information about topic X]`
  - `@[Search][latest updates on subject Y]`
  - `@[Search][recent changes to topic Z]`
- **In Practice**: Specialist includes `@[Search][query]` anywhere in their response message
- **Multiple Searches**: Can include multiple `@[Search]` requests in a single message
- **Example Research specialist usage**:
  ```
  Building on @[Other Specialist]'s claim about [topic], I want to verify this. 
  @[Search][latest best practices for topic 2025]
  ```

**RESEARCH SPECIALIST - EXPLICIT SEARCH ACKNOWLEDGMENT PATTERN**:

The Research specialist is instructed to **explicitly acknowledge the `@[Search tool]` when referencing search findings** in subsequent messages. This serves multiple critical purposes:

- **Signal to other specialists**: Makes it clear that information came from real-time research, not training data
- **Reinforce tool availability**: Reminds the room that current information is accessible
- **Build confidence**: Establishes factual foundation with verifiable sources
- **Distinguish data sources**: Helps specialists understand when to trust currency of information

**Interpreting Search Results - Two-Layer Approach**:

When @[Search tool] responds with structured XML, Research specialist should leverage both components:

1. **`<answer>` element** - PRIMARY content to defer to:
   - This is Tavily's AI-generated synthesis of all search results
   - Research should **heavily weight and quote this synthesis** in their analysis
   - Pattern: "According to @[Search tool]'s synthesis: '[quote from <answer>]'..."
   - This represents the most reliable consolidated view from multiple sources

2. **`<result>` elements** - Supporting evidence for group discussion:
   - Individual source citations with URLs and content snippets
   - Research should **present these to the room** for specialists to consider
   - Pattern: "@[All], @[Search tool] found several perspectives: [cite key results with titles/URLs]"
   - Encourages specialists to verify and discuss multiple viewpoints

**Best Practice Pattern**:
```
@[All], according to @[Search tool]'s synthesis: "[quote from <answer>]"

Supporting sources include:
- [Source 1 title]: [key point] (URL)
- [Source 2 title]: [key point] (URL)

This suggests that [analysis]...
```

**Pattern Examples**:
- ✅ "According to @[Search tool]'s synthesis: '[direct quote from <answer> element]'"
- ✅ "@[Specialist Name specialist], regarding your statement about [topic], @[Search tool]'s synthesis states: '[quote]', with supporting evidence from [cite result sources]"
- ✅ "I've verified with @[Search tool] that [specialist's statement] is accurate. The `<answer>` confirms: '[quote]'"
- ❌ "Based on search results..." (too vague, doesn't signal tool usage or cite structure)
- ❌ "I found that..." (ambiguous whether from training data or search)

**Why This Matters**:
When Research explicitly references "@[Search tool]", defers to the `<answer>` synthesis, and presents `<result>` citations for group discussion:
1. Other specialists see that current information was consulted
2. The `<answer>` provides authoritative synthesis to defer to
3. Individual `<result>` citations allow specialists to verify and discuss nuances
4. Room gains confidence in factual claims backed by real-time research with transparent sources
5. Discussion quality improves through clear attribution and multi-source verification

**OUTPUT - Search Results to the Room**:

After a specialist's message containing `@[Search][query]`, the system automatically:
1. Detects ALL search requests in the message (can be multiple)
2. For EACH search query found:
   - Calls Tavily API with that query
   - Formats results as clean XML
   - **Adds a separate "Notice:" message to the room** providing search context
   - Each search gets its own independent Notice message
3. Messages appear from "Search tool:" and are visible to all specialists (both in agent context and human console)

**Important**: If a specialist includes multiple `@[Search]` requests in their message, EACH one is evaluated and generates its own separate Notice message. They are NOT combined.

**Phase-Level Deduplication**:
- The system processes ALL specialist messages in a phase before executing tool requests
- If multiple specialists request the SAME search query in the same phase, it's fetched only once
- All requesters are listed in the result: `requester="@[Specialist A] @[Specialist B]"`
- This prevents duplicate API calls while ensuring all requesters see they're included
- Each unique query is still fetched separately (refinement is good, duplication is prevented)

**Search Results Format** - Clean XML optimized for token efficiency and clarity:

A message is added to the room from "Search tool:" for EACH search query, in this format:
```
Recent search results: <results query="[the search query]" requester="@[Specialist Name]"><answer>AI-generated synthesis summarizing key points from multiple sources with factual information relevant to the query.</answer><result url="https://example.com/article-1" title="Article Title 1">Clean plain text snippet from first source with key information extracted from the page.</result><result url="https://example.com/article-2" title="Article Title 2">Clean plain text snippet from second source providing additional context and perspective.</result><result url="https://example.com/article-3" title="Article Title 3">Clean plain text snippet from third source offering supporting evidence or alternative viewpoint.</result></results>
```

Note: The entire message (all XML) is on a single line with no line breaks. The "Search tool:" speaker identification makes the source clear without needing "Notice:" prefix.

**Result Components**:
- **Message prefix**: "Recent search results:" - concise introduction (no redundant "Notice:" since "Search tool:" speaker makes context clear)
- **Query attribute**: The search query is stored in the `<results query="...">` tag attribute
- **Requester attribute**: The specialist who requested the search, formatted as `requester="@[Specialist Name]"`
- **Answer element** (optional): `<answer>Tavily's LLM-generated summary</answer>` - AI-generated summary of all results combined (primary content)
- **Results block**: Contains `<answer>` (if available) followed by multiple `<result>` elements (default: 5, configurable up to 20), all on one line
- **Each Result attributes**: 
  - `url`: Source URL for citation and verification
  - `title`: Page/article title for source identification and credibility assessment
- **Each Result content**: Clean plain text optimized for specialist clarity (all broken markdown/formatting removed, no HTML entities or excessive Unicode)

**Phase-Based Trimming Strategy - Progressive Token Optimization**:

To balance detail with token efficiency, search results use a phase-aware trimming strategy:

1. **Fresh Searches** (current or previous phase):
   - **FULL format**: All `<result>` tags with URLs, titles, and content excerpts included
   - Specialists have ONE complete phase to work with detailed results
   - Example: Phase 3 search → Phase 4 specialists see full detail

2. **Older Searches** (2+ phases old):
   - **TRIMMED format**: Only `<results>`, `<answer>`, and ellipsis indicator (`…`) retained
   - Individual `<result>` tags removed to save tokens
   - Query and synthesis always preserved for reference and duplicate prevention
   - Example: Phase 3 search → Phase 5+ specialists see trimmed version

**Implementation**: The `cleanup_old_search_results()` function in `agents.py` removes `<result>` tags when `current_phase - msg_phase >= 2`. This ensures specialists can respond to fresh research while dramatically reducing token usage from historical searches.

**Trimmed Format Example**:
```
<results query="older search query" requester="@[Research specialist]"><answer>According to sources...</answer>…</results>
```

**Rationale**: Specialists need detailed URLs/titles/excerpts to work with new information, but after they've had a chance to respond, only the query and synthesis are needed to prevent duplicate searches.

**Clarity Optimization Pipeline - Token Efficiency Through Clean Content**:

**Design Principle**: Clarity helps discussion quality AND saves costs. Every token sent to specialists is an API cost. Clean, readable content means specialists understand results better (higher quality discussion) and consume fewer tokens (lower cost).

The search results undergo aggressive cleaning to maximize clarity and minimize token waste:

1. **Query Cleaning (Before Tavily)**:
   - Unescape HTML entities: `&quot;` → `"`, `&#x27;` → `'`
   - Normalize Unicode punctuation: Smart quotes → straight quotes, em-dashes → hyphens
   - **Goal**: Tavily receives clean plain text queries (as they expect) for better search results

2. **Content Cleaning (From Tavily)**:
   - **Decode HTML entities**: `&quot;` → `"`, `&amp;` → `&` (prevent double-escaping)
   - **Normalize Unicode**: Smart quotes, em-dashes, ellipsis → ASCII equivalents (cleaner for LLMs and humans)
   - **Remove broken markdown**: `[](https:`, `[.webp)`, `[ [ [`, standalone brackets/parens
   - **Strip URLs**: `https://...`, `www.example.com`, query parameters, tracking codes
   - **Remove media references**: `.jpg`, `.webp`, `.pdf` extensions (no informational value)
   - **Discard pure junk**: If content is only URL fragments/domains with zero readable prose → replace with "Content not available after cleaning web artifacts."
   - **Goal**: Specialists see only readable prose, no formatting artifacts or broken markup

3. **Minimal XML Escaping (To Specialists)**:
   - **Attributes**: Only escape `&`, `<`, `>`, `"` (not single quotes since we use double-quoted attributes)
   - **Element content**: Only escape `&`, `<`, `>` (quotes are safe in content)
   - **Goal**: Clean, readable XML that's valid but not over-escaped

**Why This Matters**:
- **Clarity → Quality**: Specialists read clean prose, not `&#x27;ll` or `[ [ [` artifacts
- **Clarity → Efficiency**: Fewer tokens per message (no junk content, no redundant escaping)
- **Clarity → Demos**: Human-readable output for presentations and debugging

**Key Details**:
- **Message Type**: Search results to the room (provides context from real-time information)
- **Message Author**: "Search tool:" (appears in light blue in console)
- **Content Format**: Clean plain text wrapped in minimal XML tags for structure
- **XML Display**: Readable XML visible in both agent context and human console output
- **XML Escaping**: Minimal escaping for validity (no over-escaping that hurts readability)
- **Visibility**: Public to entire room - all specialists and the User see search results
- **Timing**: Appears immediately after the specialist's message that contained `@[Search]`
- **Multiple Queries**: Each `@[Search]` request generates its own separate "Search tool:" message - they are evaluated independently and NOT combined
- **Processing**: As soon as a message is added to the room history containing `@[Search][...]`, the system detects ALL occurrences and performs each search

**Console Color Coding** (for human readability):
- **Message prefix**: "Search tool:" appears in **light blue**
- **XML structure**: Tags, brackets, and attribute names appear in **light green** (default)
- **Primary content** (highlighted in **white**):
  - `query="..."` attribute value → **White** (what was searched)
  - `<answer>...</answer>` content → **White** (Tavily's main answer/summary from all results)
- **Supporting evidence** (light grey for readability):
  - `<result>...</result>` content → **Light grey** (supporting evidence excerpts - brighter for readability)
- **Metadata** (dark grey, subdued):
  - `url="..."` and `title="..."` attribute values → **Dark grey** (source metadata)
  - `requester="..."` attribute value → **Dark grey** base, but specialist mentions within get their own colors
- **Specialist mentions** in `requester` attribute (e.g., `@[Research specialist]`):
  - In-room specialists → **Light purple** (overrides dark grey)
  - Available specialists → **Red** (overrides dark grey)
  - User mention → **Light blue** (overrides dark grey)

**Setup**: Requires `TAVILY_API_KEY` environment variable and `pip install tavily-python`

**Configuration**: `TAVILY_MAX_RESULTS` (default: 5, max: 20 results per query)

**Implementation**: `search.py` module with Tavily client, detection in `agents.py` after specialist responses

**Key Benefits**:
- Aggregates 20+ trusted sources per query
- Returns only the most relevant content (no noise)
- Includes relevance scoring for quality assessment
- Structured XML format for easy parsing
- All content properly escaped for XML safety
- Designed specifically for LLM fact-checking and analysis

**Content Cleaning - Plain Text Only**:

All search results undergo automatic content cleaning to provide specialists with clean, readable plain text:

**What Gets Removed**:
- **All markdown formatting**: Images (`![alt](url)`), bold (`**text**`), italic (`*text*`), headers (`## Header`), code blocks (` ```code``` `), list markers (`- item`, `1. item`), blockquotes (`> text`)
- **HTML tags**: Any `<tag>` syntax that leaked through from web pages
- **HTML entities**: All HTML entities are decoded (e.g., `&#x27;` → `'`, `&amp;` → `&`, `&quot;` → `"`)
- **Unicode punctuation**: All Unicode punctuation is normalized to ASCII equivalents (e.g., smart quotes `"` → `"`, em dash `—` → `-`, ellipsis `…` → `...`)
- **Navigation artifacts**: Common web navigation text patterns (breadcrumbs, "you are here", repeated menu items)
- **Standalone URLs**: Lines containing only URLs (often leftover from image cleanup)
- **Excessive whitespace**: Multiple spaces/newlines collapsed to single space for readability

**What Gets Preserved**:
- **Plain text content**: The actual text inside `<result>` tags (decoded and normalized to ASCII)
- **URLs**: Preserved in `url` attribute for citation and verification (decoded and normalized)
- **Titles**: Preserved in `title` attribute for source identification (decoded and normalized)
- **Answer summary**: Preserved in `answer` attribute if provided by Tavily (decoded and normalized)
- **Structure**: XML structure and attributes remain intact

**Why Content Cleaning Matters**:
1. **Readability**: Specialists need clean, readable text without web artifacts and formatting noise
2. **Focus**: Removes distracting markdown images (often dozens of `![image](url)` patterns from modern websites)
3. **Consistency**: Provides uniform plain text across all sources regardless of original formatting
4. **Efficiency**: Reduces token usage by removing formatting markup that doesn't add semantic value
5. **Usability**: Makes it easy for specialists to quickly scan and internalize search results
6. **Citations**: URLs and titles remain accessible as attributes for proper source citation

**Example Transformation**:
```
Before: ![](https://cdn.example.com/image.webp) [![Top Companies](url)] **Create** a *Minimum* Viable Product using &#x27;agile&#x27; methods—delivering value…
After: Create a Minimum Viable Product using 'agile' methods-delivering value...
```

**Unicode Punctuation Normalization**:

All search result fields (content, URLs, titles, answer summaries) undergo automatic normalization from Unicode punctuation to ASCII equivalents for maximum compatibility and readability:

| Unicode Character | ASCII Equivalent | Description |
|------------------|------------------|-------------|
| `"` `"` (U+201C, U+201D) | `"` | Smart double quotes → straight quotes |
| `'` `'` (U+2018, U+2019) | `'` | Smart single quotes → straight quotes |
| `—` (U+2014) | `-` | Em dash → hyphen |
| `–` (U+2013) | `-` | En dash → hyphen |
| `…` (U+2026) | `...` | Ellipsis → three dots |
| `«` `»` (U+00AB, U+00BB) | `"` | Guillemets → straight quotes |
| `•` (U+2022) | `*` | Bullet → asterisk |
| `·` (U+00B7) | `*` | Middle dot → asterisk |
| Non-breaking space (U+00A0) | Regular space | Non-breaking → regular space |

**Why Normalize to ASCII**:
1. **Compatibility**: ASCII punctuation works consistently across all terminals, editors, and display systems
2. **Simplicity**: Specialists see familiar, straightforward punctuation without rendering issues
3. **Copy/Paste**: ASCII text copies cleanly into code, commands, and documentation
4. **Clarity**: Removes ambiguity from visually similar Unicode characters
5. **Performance**: ASCII is more efficient for processing and pattern matching

**Processing Pipeline**:
1. **Decode HTML entities** (e.g., `&#x27;` → `'`, `&amp;` → `&`)
2. **Normalize Unicode punctuation** to ASCII equivalents
3. **Clean all markdown/HTML formatting** and navigation artifacts
4. **Re-escape for XML safety** (to prevent malformed messages)

The cleaning is performed by `clean_search_content()` and `normalize_unicode_punctuation()` in `search.py` and ensures all content in `<result>` tags is clean, ASCII-normalized plain text.

**Dual-Audience Architecture - XML Encoding Strategy**:

Search results are formatted differently for two audiences:

**For LLMs (Specialists) - XML-Encoded**:
- **Format**: Properly XML-encoded entities
- **Example**: `network &amp; data isolation`, `5 &lt; 10`, `"quotes"`
- **Why**: Valid XML that won't break parsing when stored in messages
- **Implementation**: `search.py::format_search_results()` uses `escape_xml_content()` and `escape_xml_attribute()`
- **Characters encoded**: `&` → `&amp;`, `<` → `&lt;`, `>` → `&gt;`, `"` → `&quot;` (in attributes)
- **LLM understanding**: LLMs are trained on XML/HTML and understand entities correctly

**For Humans (Console) - Fully Decoded**:
- **Format**: Decoded HTML/XML entities for maximum readability
- **Example**: `network & data isolation`, `5 < 10`, `"quotes"`
- **Why**: Humans read text more naturally without entity encoding
- **Implementation**: `main.py` uses `html.unescape()` before displaying Search tool messages
- **Unicode handling**: Preserved if no ASCII equivalent exists

**Why Not CDATA?**
- Alternative: `<result><![CDATA[raw & < > text]]></result>` would avoid encoding
- **Trade-offs**:
  - ✅ LLMs see fully decoded text
  - ❌ Can't use CDATA in attributes (query, url, title would still need encoding)
  - ❌ If content contains `]]>`, it breaks CDATA parsing
  - ❌ More complex parsing logic
- **Decision**: XML entities are standard, safe, and LLM-understood; no benefit to CDATA complexity

**Content Semantics Preserved**:
Both representations are semantically identical - LLMs understand `&amp;` means `&` just as humans understand the unencoded character. The encoding is purely a transport/safety mechanism.

**Time-Aware Searches - Using Timestamps for Current Date/Time**:

The Research specialist (and any specialist using search) can determine the current date and time by checking message timestamps:

- **Purpose**: Construct year-aware search queries for current, relevant results
- **How**: Check the `<timestamp_iso>` field in ANY message in the conversation history
- **Format**: Timestamps use ISO 8601 format: `YYYY-MM-DDTHH:MM:SS.mmm`
- **Example**: If timestamp shows `2025-10-11T13:18:13.256`, the current year is 2025
- **Best Practice**: Include year ranges in searches when currency matters
  - ✅ Good: `@[Search][topic best practices 2024-2025]`
  - ❌ Less effective: `@[Search][topic best practices]`
- **Why This Matters**: 
  - Specialists need context about the current date for time-sensitive topics
  - Message timestamps provide this context
  - Time-aware searches return more relevant, current information
  - Critical for topics like "best practices", "current standards", "latest versions"
  - Prevents outdated results from years past

The Research specialist has explicit guidance to check timestamps and include year ranges in searches to ensure fact-checking is based on current information.

See `TAVILY_SEARCH_SETUP.md` for detailed setup instructions.

**Documentation**: https://docs.tavily.com

---

### URL Content Reading (@[ReadURL] TOOL)

The `@[ReadURL][url]` tool allows specialists to fetch full page content from specific URLs, complementing the search tool by providing deep access to promising sources.

**Purpose - Two-Step Information Gathering**:

1. **@[Search][query]** - Find candidate URLs and get summaries/snippets
2. **@[ReadURL][url]** - Read full content from promising URLs for deeper analysis

**When Search Isn't Enough**:

- **Search gives snippets** - short excerpts that may lack context
- **ReadURL gives full content** - complete articles, documentation, guides
- **Use ReadURL when**:
  - Search snippets are incomplete or lack critical details
  - You need full context, methodology, or implementation details
  - Official documentation, research papers, or detailed guides found in search
  - Multiple specialists need to reference the same detailed source
  - Verifying specific claims or finding information not in snippets

**INPUT - How Specialists Use ReadURL**:

- **Syntax**: `@[ReadURL][https://exact-url-here.com/page]`
- **Any specialist can use it** (not just Research)
- **Usage Examples**:
  - `@[ReadURL][https://docs.example.com/implementation-guide]`
  - `@[ReadURL][https://research.org/detailed-methodology]`
  - `@[ReadURL][https://standards.body.org/specification]`
- **In Practice**: Specialist includes `@[ReadURL][url]` anywhere in their response message
- **Multiple URLs**: Can include multiple `@[ReadURL]` requests in a single message
- **Recommended inline pattern** (document reasoning with request):
  ```
  @[ReadURL][https://docs.example.com/best-practices] looks promising because it provides the methodology I need to evaluate the User's question.
  ```
- **Complete workflow example**:
  ```
  Phase N: @[Search][implementation best practices 2025]
  Phase N: [Search tool returns results with URLs]
  Phase N+1: @[ReadURL][https://docs.example.com/best-practices] looks most relevant because it provides detailed methodology addressing the User's question.
  Phase N+1: [ReadURL tool returns full page content]
  Phase N+2: Based on the guide I requested, the recommended approach is... [analysis]
  ```

**CRITICAL - Specialist Responsibility**:

- **If YOU request a URL, YOU MUST analyze the content**
- **Don't request and ignore** - URL reads are for YOUR use, not for others to process
- **Read, analyze, integrate** - Extract key points and explain what you learned
- **Decide what it means** - You determine if content supports your recommendation or reveals gaps

**OUTPUT - URL Content to the Room**:

After a specialist's message containing `@[ReadURL][url]`, the system automatically:
1. Detects ALL ReadURL requests in the message (can be multiple)
2. For EACH URL found:
   - Fetches page content via Jina AI Reader API
   - Extracts clean, readable markdown (removes ads, navigation, boilerplate)
   - Creates a "ReadURL tool:" message with full content
   - Each URL gets its own independent message
3. Messages appear from "ReadURL tool:" and are visible to all specialists (both in agent context and human console)

**URL Content Format** - Clean XML with full markdown content:

```xml
URL content: <content url="https://..." title="Page Title" requester="@[Research specialist]">
# Article Title

Full markdown content extracted from page...

## Section Headings Preserved

- Lists maintained
- Formatting cleaned
- Ads/navigation removed

Content continues...
</content>
```

The `<content>` element contains the full markdown with all metadata as attributes (url, title, requester, optional description), making it self-contained.

**Key Features**:

- **Clean Extraction**: Jina AI removes ads, navigation, footers, sidebars
- **Markdown Format**: Preserves headings, lists, emphasis for readability
- **Word Count**: Shows content size (helps specialists gauge reading time)
- **Requester Tracking**: Shows who requested each URL (like search results)
- **Error Handling**: Clear error messages if URL fails to load
- **Timeout**: 15-second maximum per URL (prevents hanging)

**Multiple URLs** - Each `@[ReadURL]` request generates its own separate "ReadURL tool:" message with full content. They are evaluated independently and NOT combined.

**Phase-Level Deduplication**:
- The system processes ALL specialist messages in a phase before executing tool requests
- If multiple specialists request the SAME URL in the same phase, it's fetched only once
- All requesters are listed in the result: `requester="@[Specialist A] @[Specialist B]"`
- This prevents duplicate API calls and saves massive tokens (URL content can be 1000s of words)
- Each unique URL is still fetched separately

**Configuration**:

- **Environment Variable**: `JINA_API_KEY` (optional but recommended)
- **Without API Key**: 20 requests/minute rate limit
- **With API Key**: 500 requests/minute rate limit
- **Setup**: https://jina.ai/reader/ (sign up for free API key)
- **Cost**: Free tier available, pay-as-you-go pricing for high volume

**Technical Implementation**:

- **API**: Jina AI Reader API (`https://r.jina.ai/[url]`)
- **Method**: Simple HTTPS GET request
- **Response**: JSON with title, content, description, usage metadata
- **Processing**: Minimal cleanup (excessive newlines removed, content preserved)
- **Integration**: Processed same way as search tool in `agents.py`

**Best Practices**:

- **Search first, read second** - Don't blindly read URLs without search context
- **Be selective** - Only read URLs where snippets are insufficient
- **Document your selection** - Explicitly note promising URLs with reasoning before requesting (preserves your logic after search results are trimmed)
  - Example: "The source at https://example.com looks most relevant because it provides the methodology we need. @[ReadURL][https://example.com]"
- **Follow up on your requests** - Always analyze content you requested
- **Cite findings** - Reference the URL and explain key insights in your analysis
- **Share with room** - Explain why the full content matters to the discussion

**Difference from Search Tool**:

| Feature | @[Search][query] | @[ReadURL][url] |
|---------|------------------|-----------------|
| **Purpose** | Find relevant sources | Read full content |
| **Input** | Search query | Exact URL |
| **Output** | Multiple snippets + synthesis | Full page content |
| **When to Use** | Don't know which URLs are relevant | Know the URL, need full details |
| **Content Length** | Short excerpts (~200-500 words) | Full article (500-10,000+ words) |
| **API** | Tavily Search API | Jina AI Reader API |

**Documentation**: https://jina.ai/reader/

---

**Bringing Specialists Into the Room**:

1. **Request Pattern** - Any "in" specialist can request:
   ```
   "@[Chair], please bring in @[Specialist Name] to help with [reason]."
   ```

2. **Chair Brings Specialists In** - Chair @mentions available specialists:
   - Example: Chair says `"@[Specialist Name specialist], can you help with [question]?"`
   - Any @mention of an available specialist by Chair automatically brings them into the room
   - System detects the @mention and changes status from "available" → "in"
   - Specialist participates starting next phase

3. **Detection Logic** (`detect_specialist_additions()` in `agents.py`):
   - Scans Chair's response for all `@[...]` mentions
   - Maps display names to role keys (e.g., "Research specialist" → "research")
   - Checks if mentioned specialist is currently "available"
   - Returns list of specialists to bring in and Notice messages

4. **Chair Updates State** (`chair_agent()` in `agents.py`):
   ```python
   added_specialists, notice_messages = detect_specialist_additions(chair_content, state)
   
   if added_specialists:
       updated_presence = state["specialist_presence"].copy()
       for role_key in added_specialists:
           updated_presence[role_key] = "in"
       
       result["specialist_presence"] = updated_presence
       result["messages"] = chair_messages + notice_messages
   ```

5. **Notice Message Format**:
   - Singular: `"Notice: [Specialist] has joined the discussion, you may now directly ask them to assist. Current team: [list]"`
   - Plural: `"Notice: [Spec1], [Spec2] have joined the discussion, you may now directly ask them to assist. Current team: [list]"`

**Phase Execution Integration**:

1. **`start_phase()`** - Filters active specialists:
   ```python
   active_specialists = get_active_specialists(state)  # Only "in" specialists
   agents_for_phase = active_specialists + ["chair"]
   
   result = {
       "agents_remaining": agents_for_phase,  # Only active specialists participate
       # ...
   }
   ```

2. **`execute_phase_parallel()`** - Propagates state updates and auto-dismisses non-core specialists:
   ```python
   # CRITICAL: Collect Chair's specialist_presence update
   chair_presence_update = chair_result.get("specialist_presence")
   
   # Auto-dismiss non-core specialists who responded
   state_for_dismiss = dict(state)
   if chair_presence_update is not None:
       state_for_dismiss["specialist_presence"] = chair_presence_update
   
   dismiss_presence_update, dismiss_notices = auto_dismiss_non_core_specialists(
       specialist_messages,  # Only specialist messages (before Chair)
       state_for_dismiss     # State with Chair's additions already applied
   )
   
   # Combine updates: Chair's additions first, then auto-dismissals
   specialist_presence_update = chair_presence_update or state["specialist_presence"]
   if dismiss_presence_update is not None:
       specialist_presence_update.update(dismiss_presence_update)
   
   # Add dismiss notices and return updated presence
   if dismiss_notices:
       all_messages.extend(dismiss_notices)
   
   if specialist_presence_update is not None:
       result["specialist_presence"] = specialist_presence_update
   ```
   
   **Note**: Without propagating these updates, newly added specialists won't appear in the next phase's `agents_remaining` list, and dismissed specialists will incorrectly remain active.

**Helper Functions** (`agents.py`):

```python
def get_active_specialists(state: OverallState) -> list[str]:
    """Return list of specialists currently 'in' the room."""
    presence = state.get("specialist_presence", {})
    active = []
    for role in AGENT_ROSTER:
        if role == "chair":
            continue
        if presence.get(role) == "in":
            active.append(role)
    return active

def get_available_specialists(state: OverallState) -> list[str]:
    """Return list of specialists currently 'available' to be brought in."""
    presence = state.get("specialist_presence", {})
    available = []
    for role in AGENT_ROSTER:
        if role == "chair":
            continue
        if presence.get(role) == "available":
            available.append(role)
    return available

def get_display_name(role_key: str) -> str:
    """Map role_key to display name (e.g., 'productmanager' → 'Product Manager specialist')."""
    
def find_role_key_by_display_name(display_name: str) -> str | None:
    """Map display name to role_key (e.g., 'Product Manager specialist' → 'productmanager')."""

def auto_dismiss_non_core_specialists(
    specialist_messages: list[BaseMessage],
    state: OverallState
) -> tuple[dict[str, str] | None, list[AIMessage]]:
    """
    Auto-dismiss non-core team specialists after they respond.
    
    Non-core specialists who responded are automatically changed to "available" status,
    keeping the discussion focused on the core team. Returns updated presence dict and
    Notice messages for dismissed specialists.
    """
```

**Prompt Integration** (`prompts.py`):

All specialists receive `ROOM_PRESENCE_SECTION` in `BASE_INSTRUCTION`:
- Explains "in" vs "available" distinction
- Shows full specialist roster (everyone's roles visible regardless of presence)
- Provides pattern for requesting Chair to bring in specialists
- Emphasizes only requesting if genuinely needed for User's concerns

Chair receives `MANAGING_ROOM_COMPOSITION` in `CHAIR_SYSTEM_BASE`:
- Authority to bring specialists into the room
- Pattern to use when bringing them in
- Guidance on when to expand the team
- Reminds to generate Notice messages
- **CRITICAL**: Informed that non-core specialists only participate for ONE PHASE, then auto-dismiss
- Must explicitly bring dismissed specialists back in if they're mentioned or needed in later phases
- **REFLECTION PERIOD**: Must allow at least one full phase for core team to digest specialist's contribution before re-inviting

**Display at Startup** (`main.py`):

```python
def display_initial_room_composition():
    """Display core team and available specialists at startup."""
    # Shows:
    # CORE TEAM (In the Room): [active specialists]
    # AVAILABLE SPECIALISTS: [available specialists]
```

**Checkpoint Persistence**:

- `specialist_presence` is part of `OverallState` and automatically saved/restored
- `compute_config_checksum()` includes `DEFAULT_CORE_TEAM` for validation
- Resuming from checkpoint preserves exact room composition

**Auto-Dismissal for Non-Core Specialists**:

Non-core specialists automatically self-dismiss after responding ONE TIME, keeping discussions focused:

- **Behavior**: Non-core team specialists participate for ONLY ONE PHASE after being brought in, then automatically return to "available" status UNLESS they were @mentioned in that phase
- **Mention-Aware Dismissal**: If anyone @mentions a non-core specialist in the current phase, they stay "in" to respond in the next phase
- **Core Team**: Defined in `DEFAULT_CORE_TEAM` in `config.py`; these specialists remain "in" throughout and never auto-dismiss
- **Re-invitation Required**: If a dismissed specialist is mentioned or needed in later phases, Chair must explicitly bring them back in again
- **Reflection Period**: Chair should allow AT LEAST ONE FULL PHASE for core team to reflect on and digest a dismissed specialist's contribution before bringing them back in
- **Notice**: System generates dismissal Notice informing everyone of status change
- **Implementation**: `auto_dismiss_non_core_specialists()` in `agents.py` processes dismissals after Chair responds, checks all phase messages for @mentions
- **Timing**: Dismissals happen AFTER Chair's additions, so newly brought-in specialists aren't immediately dismissed
- **Example**: 
  - Phase 3: Bring in Specialist X → responds about their domain → no mentions → auto-dismisses
  - Phase 4: Someone says "@[Specialist X], can you clarify [aspect]?" → Chair brings them back in
  - Phase 5: Specialist X responds → was mentioned in Phase 4, so stays "in" for Phase 6
  - Phase 6: No mentions of Specialist X → auto-dismisses after responding

**Benefits**:

1. **Focused Discussions**: Start with small core team, expand as needed, auto-reduce when expertise no longer needed
2. **Cost Efficiency**: Fewer LLM calls - specialists only participate when actively needed
3. **Reduced Noise**: Only core team + currently relevant specialists participate
4. **Dynamic Expansion**: Chair brings in experts as topic evolves, they self-dismiss when done
5. **Full Awareness**: All specialists know what expertise is available
6. **Natural Flow**: Mimics real meetings where people join as needed, then return to other work
7. **Prevents Bloat**: Discussion doesn't accumulate specialists over time unnecessarily
8. **Thoughtful Integration**: Reflection period ensures specialist contributions are properly digested before re-engagement

**Edge Cases**:

- If Chair tries to bring in already-"in" specialist: Handled gracefully (status stays "in")
- If Chair tries to bring in non-existent specialist: `find_role_key_by_display_name()` returns None, ignored
- If multiple specialists brought in simultaneously: All processed, single Notice with list
- If multiple specialists dismiss simultaneously: Single Notice lists all dismissed specialists
- Core team specialist dismissal: Never happens - core team check prevents it
- Chair is never in `specialist_presence`: Always present, special-cased in filtering logic

## Graph Workflow

### Node Structure
```
start_phase → context → update_context → research → update_research → ...
    ↑                                                                    ↓
    └──────────────────── check_continuation ←───────────────────────────┘
                                    ↓
                                  END
```

### Key Nodes
- **start_phase**: Initialize phase, add Notice message with phase metadata, reset agents_remaining
- **{agent}**: Invoke specialist (context, research, engineer, etc.), adds response with phase metadata
- **update_{agent}**: Remove agent from agents_remaining list
- **check_continuation**: Decide if continue or trigger final phase or end
- **save_checkpoint**: Save conversation state to disk, then prompt user to press ENTER before continuing to next phase

### User Control
After Phase 3+ completes and checkpoint is saved, the system prompts:
```
⏸️  Press ENTER to continue to next phase (or Ctrl+C to stop):
```

**When prompt appears**:
- **Phase 1-2**: Auto-continues (mandatory assessment phases, no pause)
- **Phase 3+**: Shows prompt (iterative discussion phases, user can review)
- **Final Phase**: Auto-continues (conclusion phase, no pause)

This gives the user control over:
- When to proceed during iterative discussion phases (3+)
- Time to review specialist responses before continuing
- Ability to stop the discussion cleanly at phase boundaries
- Checkpoint is already saved, so stopping is safe and resumable

### Routing Logic
```python
def route_next_agent(state):
    remaining = state.get("agents_remaining", [])
    if not remaining:
        return "check_continuation"
    return remaining[0]  # Next agent in order

def route_continuation(state):
    if state.get("continue_discussion"):
        return "start_phase"  # Another phase
    return "__end__"  # Discussion complete
```

### Phase Tracking
```python
# Phase number is tracked directly in state (no calculation needed)
# Phase is incremented by start_phase() function and stored in state
# Each message includes phase metadata when created

# Get current phase from state
current_phase = state.get("phase_number", 1)

# Phase metadata is added to each message at creation time
AIMessage(
    content=response_content,
    name=specialist_name,
    additional_kwargs={"phase": current_phase}
)
```

**Benefits of Phase Metadata**:
- No complex position-based calculations
- Reliable filtering based on direct metadata lookup
- Phase information visible to LLMs in XML
- Simpler, more maintainable code
- Future-proof for adding more metadata

### Continuation Logic
```python
# In check_continuation node:
# Number of specialists is dynamically inferred from AGENT_ROSTER
num_specialists = len(AGENT_ROSTER)
recent_messages = all_messages[-num_specialists:]  # Last phase
pass_count = count_passes(recent_messages)  # Count specialists who passed (verb)

if pass_count == num_specialists:  # All specialists passed (skipped contribution)
    # TODO: Check for new User messages before triggering Final Phase
    # If User spoke after Phase 2, revert to Phase 3+ logic (don't trigger Final)
    # Only trigger Final Phase when no new User messages exist to address
    return {"continue_discussion": True, "final_phase_needed": True}
elif final_phase_done:
    # TODO: Before ending, check if User spoke during Final Phase
    # If yes, revert to Phase 3+ logic (set final_phase_done=False, continue_discussion=True)
    # User input always resets convergence
    return {"continue_discussion": False}
else:
    return {"continue_discussion": True}
```

**Future Enhancement - User Message Detection**:
```python
# Check if User has contributed new messages since discussion started
def has_new_user_messages(messages, initial_user_message_count=1):
    """Check if User has added new messages during discussion.
    
    Returns True if User messages exist beyond the initial question.
    If True, discussion should continue (revert to Phase 3+ logic) rather
    than trigger Final Phase, because User has provided new information
    that specialists need to address.
    """
    user_messages = [msg for msg in messages if msg.name == "User"]
    return len(user_messages) > initial_user_message_count

# Enhanced continuation logic:
if pass_count == num_specialists:
    # All specialists passed - check if Final Phase appropriate
    if has_new_user_messages(all_messages):
        # User spoke after Phase 2 - continue iterating
        # Revert to Phase 3+ logic to address new User input
        return {"continue_discussion": True, "final_phase_needed": False}
    else:
        # No new User messages - trigger Final Phase
        return {"continue_discussion": True, "final_phase_needed": True}
elif final_phase_done:
    # Final Phase completed - check if User spoke during it
    if has_new_user_messages(all_messages):
        # User spoke during Final Phase - REVERT to Phase 3+ logic
        # Cannot conclude while new User input exists
        return {
            "continue_discussion": True, 
            "final_phase_needed": False,
            "final_phase_done": False  # Reset Final Phase flag
        }
    else:
        # No new User messages - discussion can conclude
        return {"continue_discussion": False}
else:
    return {"continue_discussion": True}
```

**Rationale**: User messages are ALWAYS incorporated into the discussion for context. If the User provides additional information:
- **Before Final Phase trigger**: Continue with Phase 3+ instead of triggering Final
- **During Final Phase**: Final Phase is IMMEDIATELY invalidated, revert to Phase 3+ iterative logic, reset all Final Phase flags
- User input always takes priority - specialists cannot conclude until ALL User concerns are addressed
- Final Phase represents settlement - impossible when new User input exists
- We never regress to Phase 2 - always continue at Phase 3+ level when User speaks

## Potential Enhancements

### User Message Detection in Continuation Logic (Future Implementation)

**Current Limitation**: Final Phase triggers when all specialists pass, regardless of whether User has provided new information during the discussion.

**Enhancement**: Add detection for new User messages to properly handle User input during discussion.

**Implementation** (see "Continuation Logic" section for code):
1. Track initial User message count (should be 1 at Phase 1 start)
2. **Before triggering Final Phase**: Check if additional User messages exist
   - If User spoke after Phase 2: Continue with Phase 3+ (don't trigger Final)
   - If no new User messages: Trigger Final Phase
3. **After Final Phase completes**: Check if User spoke during Final Phase
   - If User spoke during Final: **IMMEDIATELY revert to Phase 3+** (invalidate Final Phase)
   - Reset `final_phase_done` flag to `False`
   - Continue discussion until User input is addressed
4. **Never regress**: If User speaks during Phase 3+ or Final, stay at Phase 3+ level (never go back to Phase 2)

**Benefit**: Ensures User input always takes priority. Final Phase is **invalidated** the moment User provides new input. Specialists cannot conclude discussion while unaddressed User concerns exist.

**Current Workaround**: User messages are always visible in conversation history (never filtered), so specialists will see new User input in subsequent phases. However, without explicit detection, the system might incorrectly remain in or trigger Final Phase when User input exists.

### Cloud Provider Parallelization (Future Improvement)

**Opportunity**: Atomic phases create a natural parallelization opportunity for cloud-based LLM providers.

**Key Insight**: Since atomic phases ensure all non-Chair specialists see **identical input** (prior phases only), they can be invoked in parallel without any dependencies.

**Current Architecture**:
```
Phase 1 (sequential):
Context → Research → Engineer → Skeptic → ... (no Chair - skips Phase 1)
  ↓         ↓          ↓          ↓
5-10s     5-10s      5-10s      5-10s
Total: 75-150 seconds for 15 domain specialists

Phase 2+ (sequential):
Context → Research → Engineer → Skeptic → ... → Chair (participates)
  ↓         ↓          ↓          ↓               ↓
5-10s     5-10s      5-10s      5-10s           5-10s
Total: 80-160 seconds for 16 specialists (15 domain + 1 coordinator)
```

**Parallel Architecture (Cloud APIs)**:
```
Phase 1 (parallel):
                    ┌→ Context    ─┐
                    ├→ Research   ─┤
                    ├→ Engineer   ─┤
Snapshot state →    ├→ Skeptic    ─┤ All parallel (5-10s)
                    ├→ Ethicist   ─┤
                    └→ ... (11 more) ─┘
                            ↓
                 Wait for all to complete
                            ↓
                    Phase complete → Progress to Phase 2
                    (Chair skipped - nothing to synthesize yet)
Total: ~10 seconds (no Chair in Phase 1)

Phase 2+ (parallel):
                    ┌→ Context    ─┐
                    ├→ Research   ─┤
                    ├→ Engineer   ─┤
Snapshot state →    ├→ Skeptic    ─┤ All parallel (5-10s)
                    ├→ Ethicist   ─┤
                    └→ ... (11 more) ─┘
                            ↓
                 Wait for all to complete
                            ↓
                    Collect responses
                            ↓
                         Chair (sequential - sees all current phase)
                            ↓
                    Phase complete → Progress to next phase
Total: 10-20 seconds per phase (10-15x faster!)
```

**Why This Works**:
- **Atomic phases**: Non-Chair specialists only see prior completed phases (identical input)
- **No dependencies**: Each specialist's input is independent of others in same phase
- **Chair conditional participation**: Chair only participates when specialist responses exist to synthesize
  - Phase 1: Chair skips (no specialists visible yet)
  - Phase 2+: Chair participates (specialist responses from Phase 1+ exist)
- **Chair waits for all**: When participating, Chair invocation waits until all parallel non-Chair specialists complete
- **Chair goes last**: Chair sees ALL collected current phase responses sequentially (needs synthesis context)
- **Phase progression**: Only after Chair completes (or skips) does the phase end and next phase begin
- **State snapshot**: Freeze state before parallel invocations, collect results, invoke Chair if needed, then progress

**Benefits for Cloud Providers**:
1. **Speed**: 10-15x faster per phase (parallel network calls)
2. **Cost**: Same token cost, much faster wall-clock time
3. **Prompt caching**: All specialists send identical system prompts (Anthropic caching benefit)
4. **Scalability**: Easily handle 20+ specialists without proportional time increase

**Ollama Execution Strategy**:
- **Always use concurrency of 1** (sequential execution)
- **Rationale**: Prevents VRAM thrashing with large models and contexts
- Even with multi-GPU setups, sequential execution ensures maximum VRAM availability per specialist
- The 30B+ models with 50k+ context windows require careful memory management
- **Performance**: Slower than parallel, but stable and predictable on local hardware

**When to Use Parallel vs Sequential**:

| Scenario | Execution | Reason |
|----------|-----------|--------|
| **Cloud Providers** | | |
| OpenAI/Anthropic non-Chair | **Parallel** | Network latency, unlimited capacity, prompt caching |
| OpenAI/Anthropic Chair | **Sequential (when participating)** | Must see all current phase responses first |
| **Local Ollama** | | |
| Ollama (any GPU config) | **Sequential** | VRAM thrashing prevention, model size + context window constraints |
| **By Phase** | | |
| Phase 1 (domain specialists) | **Parallel (cloud only)** | All see User message only (identical input) |
| Phase 1 (Chair) | **Skip** | No specialist responses to synthesize yet |
| Phase 2 (non-Chair) | **Parallel (cloud only)** | All see Phase 1 only (identical input) |
| Phase 2 (Chair) | **Sequential (participates)** | Synthesizes Phase 1 + Phase 2 responses |
| Phase 3+ (non-Chair) | **Parallel (cloud only)** | All see Phase 1-2 compressed (identical input) |
| Phase 3+ (Chair) | **Sequential (participates)** | Synthesizes ongoing discussion |
| Final Phase (non-Chair) | **Parallel (cloud only)** | All see full prior history (identical input) |
| Final Phase (Chair) | **Sequential (always participates)** | PRIMARY OUTPUT - synthesizes entire discussion |

**Implementation Approach**:

**Option 1: LangGraph Fan-Out/Fan-In Pattern**
```python
# In graph.py
non_chair_specialists = [s for s in AGENT_ROSTER if s != "chair"]

# Fan-out: parallel branches (all non-Chair specialists)
for specialist in non_chair_specialists:
    graph.add_node(f"{specialist}_parallel", create_agent_node(specialist))
    graph.add_edge("snapshot_state", f"{specialist}_parallel")

# Fan-in: wait for ALL to complete, collect results
graph.add_node("collect_responses", collect_node)
for specialist in non_chair_specialists:
    graph.add_edge(f"{specialist}_parallel", "collect_responses")

# Chair goes sequential (waits for collect, then sees all current phase)
graph.add_edge("collect_responses", "chair")

# Phase progression (only after Chair completes)
graph.add_edge("chair", "check_continuation")
```

**Option 2: asyncio with Provider Detection**
```python
async def invoke_phase_parallel(state, config):
    if config.provider in ["openai", "anthropic"]:
        # Parallel execution for cloud (non-Chair specialists)
        non_chair = [s for s in AGENT_ROSTER if s != "chair"]
        tasks = [invoke_specialist_async(s, state) for s in non_chair]
        
        # Wait for ALL non-Chair specialists to complete
        results = await asyncio.gather(*tasks)
        
        # Update state with collected responses
        updated_state = merge_responses(state, results)
        
        # Chair goes sequential (waits for all, sees current phase)
        chair_result = await invoke_specialist_async("chair", updated_state)
        
        # Phase complete, return to continue
        return merge_responses(updated_state, [chair_result])
    else:
        # Sequential for Ollama (current behavior)
        results = []
        for specialist in AGENT_ROSTER:
            result = invoke_specialist(specialist, state)
            state = merge_responses(state, [result])
            results.append(result)
        return state
```

**Configuration Addition Needed**:
```python
# In config.py
@dataclass
class AgentConfig:
    provider: str = "ollama"  # or "openai", "anthropic"
    parallel_enabled: bool = False  # Auto-set based on provider
    cache_optimized: bool = False  # Use cache-friendly prompt structure
    
# In SwarmConfig.__init__()
self.parallel_execution = (
    os.getenv("PARALLEL_EXECUTION", "false").lower() == "true" or
    os.getenv("AGENT_PROVIDER", "ollama") in ["openai", "anthropic"]
)

self.cache_optimized = (
    os.getenv("CACHE_OPTIMIZED", "false").lower() == "true" or
    os.getenv("AGENT_PROVIDER", "ollama") in ["anthropic"]  # Anthropic has best caching
)

# In prompts.py - prompt building logic
def build_system_prompt(specialist_key: str, cache_optimized: bool = False):
    if cache_optimized:
        # Shared content FIRST (prefix caching)
        return f"{MULTI_AGENT_CULTURE}\n\n{BASE_INSTRUCTION}\n\nYOUR ROLE:\n{get_specialist_persona(specialist_key)}"
    else:
        # Current structure (specialist-specific first)
        return f"{get_specialist_persona(specialist_key)}\n\n{MULTI_AGENT_CULTURE}\n\n{BASE_INSTRUCTION}"
```

**Expected Performance (Cloud APIs)**:
- **Current (Sequential, no caching)**: 
  - Phase 1: 15 specialists × 8s = ~120 seconds (Chair skips)
  - Phase 2+: 16 specialists × 8s = ~128 seconds (Chair participates)
  - Cost: ~$0.24 per conversation (160k input tokens @ $1.50/M)
- **With Parallelization Only**: 
  - Phase 1: ~10 seconds (15 parallel, no Chair)
  - Phase 2+: ~10 seconds non-Chair + ~8s Chair sequential = ~18 seconds
  - **Speedup**: ~12x faster for Phase 1, ~7x faster for Phase 2+
  - Cost: Same ~$0.24 (no caching)
- **With Caching Only (Sequential)**: 
  - Time: Same as current (120-128s per phase)
  - Cost: ~$0.046 per conversation (**80% cheaper**)
- **With BOTH (Parallel + Caching)**: 
  - Phase 1: ~10 seconds (15 parallel, Chair skipped)
  - Phase 2+: ~18 seconds per phase (15 parallel + Chair sequential)
  - Cost: ~$0.046 per conversation (**80% cheaper**)
  - **Combined benefit**: Conversations complete in ~60 seconds (vs 8-10 min sequential), at 1/5th the cost
- **Ollama Performance (baseline)**:
  - Phase 1: ~120 seconds (15 specialists, Chair skips)
  - Phase 2+: ~128 seconds (16 specialists, Chair participates)
  - Cost: $0 (local, but slower)

**Prompt Caching Optimization (Major Cost Reduction)**:

**Current Challenge**: Large prompts (~2-3k tokens) sent repeatedly across all specialists and phases.

**Opportunity**: Most of the prompt content is SHARED across all specialists:
- `MULTI_AGENT_CULTURE` (~300 tokens) - identical for all
- `BASE_INSTRUCTION` (~1500+ tokens) - identical for all
- Shared formatting rules, examples, guidelines
- **Only ~200-400 tokens are specialist-specific** (role persona + role description)

**Anthropic Prompt Caching Details**:
- Caches based on **exact prefix matching** (beginning of prompt)
- Minimum cache size: 1024 tokens (Sonnet), 2048 tokens (Haiku/Opus)
- Cache TTL: 5 minutes of inactivity
- Cost: Cached tokens are ~90% cheaper than uncached
- **Key constraint**: Only the PREFIX (start) of the prompt gets cached

**Current Prompt Structure** (Sub-optimal for caching):
```python
SystemMessage:
  1. Role-specific persona (~200 tokens) ← UNIQUE (not cached)
  2. MULTI_AGENT_CULTURE (~300 tokens) ← SHARED (but not cached - wrong position!)
  3. BASE_INSTRUCTION (~1500 tokens) ← SHARED (but not cached - wrong position!)
```
**Problem**: Specialist-specific content at the START breaks caching for shared content

**Optimized Prompt Structure** (Cache-friendly):
```python
SystemMessage:
  1. MULTI_AGENT_CULTURE (~300 tokens) ← SHARED (CACHED! ✓)
  2. BASE_INSTRUCTION (~1500 tokens) ← SHARED (CACHED! ✓)
  3. Role-specific persona (~200 tokens) ← UNIQUE (not cached, but small)
```
**Benefit**: ~1800 tokens cached, only ~200 tokens vary per specialist

**Cache Efficiency Calculation**:
```
Without caching:
- 16 specialists × 5 phases × 2000 tokens = 160,000 tokens
- Cost: ~$0.24 (at $1.50/M input tokens for Claude Sonnet)

With optimized caching:
- Shared prefix: 1800 tokens × 16 specialists × 5 phases = 144,000 cached tokens
- Unique suffix: 200 tokens × 16 specialists × 5 phases = 16,000 uncached tokens
- Cached cost: 144,000 × $0.15/M = $0.022
- Uncached cost: 16,000 × $1.50/M = $0.024
- Total: $0.046 (80% cost reduction!)
```

**Implementation Requirements**:
```python
# In prompts.py - restructure system prompt building

# WRONG (current - specialist-specific first):
system_prompt = f"""
{SPECIALIST_PERSONA}  # Unique - breaks caching

{MULTI_AGENT_CULTURE}  # Shared - not cached
{BASE_INSTRUCTION}  # Shared - not cached
"""

# RIGHT (optimized - shared content first):
system_prompt = f"""
{MULTI_AGENT_CULTURE}  # Shared - CACHED ✓
{BASE_INSTRUCTION}  # Shared - CACHED ✓

YOUR ROLE:
{SPECIALIST_PERSONA}  # Unique - small, not cached (but minimal cost)
"""
```

**Additional Cache Benefits**:
1. **Faster response**: Cached tokens process ~10x faster
2. **Lower latency**: Skip tokenization and initial processing for cached content
3. **Consistent across phases**: Cache persists across phases (5 min TTL)
4. **Specialist-to-specialist**: Cache shared when invoking different specialists in same phase

**Expected Cost Impact**:
- **Sequential conversations**: 70-80% cost reduction on input tokens
- **Parallel conversations**: Same 70-80% reduction, but 12x faster
- **Combined**: ~80% cheaper AND 12x faster with cloud parallel execution

**Additional Optimizations**:
1. **Connection pooling**: Reuse HTTP connections for multiple parallel requests
2. **Batch requests**: Some providers support batching multiple completions
3. **Adaptive parallelism**: Auto-detect provider capabilities and optimize
4. **Cache warming**: Pre-cache shared content before first specialist call

**Trade-offs**:
- **Complexity**: More complex state management and error handling for parallel execution
- **Prompt restructuring**: Requires reordering system prompt components (shared content first)
- **Debugging**: Parallel execution harder to debug than sequential
- **Local models**: No parallelization benefit for Ollama (sequential always optimal for VRAM)
- **API rate limits**: Burst parallel requests may hit rate limits (easily managed)

**Design Philosophy**: 
The current sequential architecture is optimal for local Ollama (prevents VRAM thrashing with large models and contexts), but atomic phases were **intentionally designed** with cloud parallelization in mind. The architecture naturally supports both execution modes:
- **Ollama**: Sequential execution (concurrency=1), no caching, stable VRAM usage
- **Cloud**: Parallel execution + prompt caching, **~80% cost reduction + 12x speedup**

This dual-mode capability means the same codebase can run efficiently on local hardware OR leverage cloud advantages without architectural changes.

---

## Recent Changes & Potential Bug Areas

### Recent Changes (Session Summary)

**2025-10-12: Fixed Colorization Regex - Handles Nested Quotes in XML Attributes**

**Context**: Search results containing nested quotes in attribute values (e.g., `title="The new era of internet memes is the "Absurdist Era" : r/decadeology"`) were breaking colorization. The regex was operating on decoded HTML/XML entities, causing it to stop at the first inner quote.

**Root Cause**: 
1. XML content: `title="The &quot;Absurdist Era&quot;"` (properly escaped) ✓
2. Decode first: `title="The "Absurdist Era""` (nested quotes)
3. Colorize with regex `([^"]*)`: Stops at first quote ✗

**Changes Made**:

1. **main.py - Fixed Order of Operations (lines 411-421)**:
   - **Old order**: Decode HTML entities → Colorize (regex sees nested quotes)
   - **New order**: Colorize → Decode HTML entities (regex sees escaped XML)
   - Moved `html.unescape()` to AFTER `highlight_mentions()`
   - Added critical comment explaining order rationale

2. **main.py - Improved Attribute Regex (lines 52-72)**:
   - **Old regex**: `(\w+)="([^"]*)"` - matches any char except quote
   - **New regex**: `(\w+)="((?:[^"&]|&(?:quot|amp|lt|gt);)*)"` - explicitly handles XML entities
   - Pattern matches:
     - `[^"&]` = any char except quote or ampersand
     - `&(?:quot|amp|lt|gt);` = XML entities for quotes, ampersands, less-than, greater-than
   - Added detailed comment explaining regex structure

**Result**:
- Colorization now works correctly with nested quotes: `title="The &quot;Absurdist Era&quot;"` 
- Regex processes escaped XML: `&quot;` is treated as single entity, not quote boundary
- After colorization, `html.unescape()` converts to human-readable: `The "Absurdist Era"`
- Color codes preserved through decoding

**Schema Solidification**: The fix reinforces that all XML processing (colorization, parsing) must operate on **XML-encoded content** with proper entity escaping (`&quot;`, `&amp;`, `&lt;`, `&gt;`). HTML entity decoding is the **final step** for human display only - all programmatic operations happen before decoding.

**2025-10-12: Dynamic Phase Progression - Capped at 60% Instead of Forcing 100%**

**Context**: User feedback that Phase 8 = 100% was too rigid and deterministic. Phase number shouldn't force convergence - content quality should drive the decision. Redesigned phase progression to provide pressure without determinism.

**Changes Made**:

1. **agents.py - Phase Progression Signal (lines 1674-1689)**:
   - **Old approach**: Unbounded 25%/phase → 100% at Phase 8 (forced convergence)
   - **New approach**: Capped 15%/phase → 60% max at Phase 8+ (baseline pressure)
   - Formula changed: `(phases - 1) * 0.25` → `min((phases - 1) * 0.15, 0.60)`
   - Growth pattern:
     - Phase 4: 0%
     - Phase 5: 15%
     - Phase 6: 30%
     - Phase 7: 45%
     - Phase 8: 60% (capped)
     - Phase 9+: 60% (remains capped)
   - Rationale updated: "Baseline pressure increases with phase count (capped at 60% to allow content quality to drive convergence)"

2. **agents.py - Updated Debug Output (lines 1887-1896)**:
   - Changed header: "UNBOUNDED - AGGRESSIVE" → "CAPPED - MODERATE"
   - Updated formula display and calculation
   - Updated schedule: "Ph8=100% (GUARANTEED)" → "Ph8+=60% (CAPPED - content quality drives)"

3. **agents.py - Updated Weight Configuration Display (lines 2010-2032)**:
   - Changed section title: "MAX MODE - CONSERVATIVE" → "DYNAMIC CONVERGENCE"
   - Updated phase weight: "UNBOUNDED (25%/check, reaches 100% at Phase 8)" → "+0.60 max (15%/check, caps at Phase 8+ - content quality drives beyond baseline)"
   - Updated baseline: "Phase 8 (100% from phase_score alone)" → "Phase 8+ reaches 60% baseline (caps - no forced convergence)"
   - Updated convergence: "Content quality signals (engagement/questions/conditional) drive final decision"
   - Updated target: "Most discussions end Phase 5-7, justified Phase 8-9 allowed" → "Dynamic - stagnant discussions end early, productive ones continue naturally"
   - Updated philosophy: "'Answer with assumptions' + allow productive continuation" → "Phase provides pressure, content quality determines convergence"

**New Equation Dynamics**:

**Maximum Stagnation Probability** (all negative signals active):
- Phase progression: 60% (capped)
- Low engagement: +20%
- Questions: +15%
- Conditional: +6%
- **Total: 101%** → floored to 100%

**Minimum Probability** (all positive signals active at Phase 8+):
- Phase progression: 60%
- Research activity: -15%
- Answer mode: -10%
- **Total: 35%**

**Dynamic Range**: 35% to 100%+ depending on content quality

**Example Scenarios**:

*Productive discussion (Phase 8):*
- Phase: 60% + Research: -15% + Answer mode: -10% = **35%** → Continues

*Neutral discussion (Phase 8):*
- Phase: 60% = **60%** → Moderate-high probability, content determines

*Stagnant discussion (Phase 6):*
- Phase: 30% + Low engagement: +20% + Questions: +15% + Conditional: +6% = **71%** → Triggers early

*Very stagnant (Phase 5):*
- Phase: 15% + Low engagement: +20% + Questions: +15% + Conditional: +6% = **56%** → Moderate probability

**Rationale**: Old approach made phase number deterministic - Phase 8 = 100% regardless of discussion quality. New approach makes phase provide **baseline pressure** (60%) while **content quality signals** (engagement, questions, conditional, research, answer mode) determine actual convergence. This allows:
- Stagnant discussions to end early (Phase 5-6) when multiple quality signals fire
- Productive discussions to continue past Phase 8 when research/answer mode active
- Phase number no longer forces convergence - it sets a baseline that content quality modulates
- More natural, dynamic convergence based on actual discussion state rather than arbitrary phase count

**Cap Rationale**: 60% was chosen as a reasonable baseline pressure point - high enough to encourage convergence but low enough that content signals (+41% max from stagnation, -25% max from justification) have decisive influence on final decision. The specific cap value can be adjusted based on observed behavior (see tuning notes in debug output).

**2025-10-12: Disabled User Silence in Stagnation Calculation**

**Context**: Current implementation doesn't allow user interaction during multi-phase discussion. User provides initial question, then specialists discuss internally until Final Phase. User silence signals don't make sense in this context and will be re-enabled when interactive user participation is implemented.

**Changes Made**:

1. **agents.py - Disabled User Silence Stagnation Signal (lines 1660-1672)**:
   - Commented out: User silence contribution (0.0 to +0.40)
   - Added rationale comment explaining why disabled
   - Signal will be re-enabled when interactive user participation implemented

2. **agents.py - Disabled User Engagement Justification Signals (lines 1750-1783)**:
   - Commented out: Recent User response justification (-0.30 or -0.15)
   - Commented out: High User engagement justification (-0.20)
   - Added rationale comments explaining why disabled
   - Signals will be re-enabled when interactive user participation implemented

3. **agents.py - Updated Debug Output (lines 1885, 1935-1939, 2012, 2019-2021)**:
   - Changed stagnation signal output: "User Silence: DISABLED (no user interaction during multi-phase discussion)"
   - Changed justification signals output: All three user engagement signals show "DISABLED"
   - Updated weight configuration display: "SILENCE_WEIGHT = DISABLED"
   - Updated max justification: "-0.75 (all signals active)" → "-0.25 (both active signals)"
   - Updated net effect: "100% - 75% = 25%" → "100% - 25% = 75%"
   - Updated with justification text: "User active + research + answers" → "research + answer mode active"
   - Updated target: "Phase 8-10 allowed" → "Phase 8-9 allowed"

4. **agents.py - Updated Chair's Stagnation Prompt (lines 2173-2200)**:
   - Removed: Section 3 "User Disengagement Pattern" (User silence tracking)
   - Renumbered: Sections 4→3, 5→4
   - Removed from progress indicators: "User is actively engaged and answering questions (User NOT silent)"
   - Changed progress indicators to focus on stated assumptions and convergence
   - Removed: "Remember: You are in Phase {current_phase}. User has been silent for {user_silence_phases} phase(s)."
   - Updated: "Remember: You are in Phase {current_phase}." (no user silence reference)

**Rebalancing Analysis**:
- Removed stagnation signals: Up to +0.40 (user silence)
- Removed justification signals: Up to -0.50 (recent user response + high engagement)
- **No rebalancing needed**: Phase progression signal is UNBOUNDED and reaches 100% by Phase 8, which acts as forcing function
- Remaining signals still modulate based on content quality:
  - Stagnation: Phase progression (25%/check), low engagement (+0.20), questions (+0.15 max), conditional (+0.06 max), short messages (+0.30 max)
  - Justification: Research activity (-0.15), answer mode (-0.10)
- Net effect: Discussion still converges by Phase 8, with research/answer mode able to extend to Phase 8-9 if productive

**Rationale**: User silence signals were designed for async collaborative scenarios where user can respond during multi-phase discussion. Current implementation is specialists-only internal discussion until Final Phase. Including user silence signals would be misleading since user CAN'T respond during discussion phases. When interactive user participation is implemented (user can comment/respond during Phase 2+), these signals will be re-enabled to detect when user has disengaged from an active discussion.

**2025-10-12: Domain-Agnostic Language Audit - Base & Core Team Prompts**

**Context**: User requested verification that base prompts and core team prompts (Context, Research, Engineer, Skeptic, Ethicist, Chair) use domain-agnostic language, while non-core specialist prompts can be domain-specific.

**Changes Made**:

1. **prompts.py - ROLE_DESCRIPTIONS for Research specialist (lines 33-36)**:
   - Removed: "(versions, pricing, best practices)" from role description
   - Changed to: More concise "for current information" without product/tech-specific examples
   - Rationale: "versions, pricing" sounds product/technology-focused

2. **prompts.py - BASE_INSTRUCTION search examples (lines 186-188)**:
   - Removed: "Current versions, pricing, or availability"
   - Changed to: "Current state of methodologies or best practices"
   - Removed: "Recent best practices or domain standards"  
   - Changed to: "Recent standards or requirements in your domain"
   - Removed: "New approaches, resources, or methodologies"
   - Changed to: "New approaches, resources, or frameworks"

3. **prompts.py - BASE_INSTRUCTION search guidelines (line 195)**:
   - Removed: "versions, pricing, best practices"
   - Changed to: "standards, requirements, best practices"

4. **prompts.py - BASE_INSTRUCTION examples line 197**:
   - Removed: "Engineer, Skeptic, Context, Ethicist, or any domain specialist"
   - Changed to: "any specialist in the room can use search directly"
   - Rationale: Avoid listing specific core team names in examples

5. **prompts.py - BASE_INSTRUCTION specialist request examples (lines 260-262)**:
   - Removed: Specific technical specialists "Database Architect specialist", "Security specialist", "Cloud Architect specialist"
   - Changed to: Generic placeholders "Specialist Name specialist", "[specific concern]", "[topic]", "[aspect]"

6. **prompts.py - RESEARCH_SYSTEM_BASE (line 1019)**:
   - Removed: "versions, pricing, availability, best practices"
   - Changed to: "recent developments, best practices"

7. **prompts.py - RESEARCH_SYSTEM_BASE fact-checking examples (lines 1069-1072)**:
   - Removed: "Current versions, pricing, or availability"
   - Changed to: "Current state of methodologies or best practices"
   - Removed: "Best practices and industry standards"
   - Changed to: "Recent standards or requirements in the domain"
   - Removed: "Capabilities or limitations"
   - Changed to: "Current capabilities or limitations"

**Verified Clean**:
- ✅ BASE_INSTRUCTION: Now fully domain-agnostic
- ✅ Context specialist: Already domain-agnostic (ambiguities, contradictions, missing info)
- ✅ Research specialist: Now domain-agnostic (removed product/tech references)
- ✅ Engineer specialist: Already domain-agnostic (implementation steps, feasibility, testing, reversibility)
- ✅ Skeptic specialist: Already domain-agnostic (risks, edge cases, challenge assumptions)
- ✅ Ethicist specialist: Already domain-agnostic (ethical principles evaluation)
- ✅ Chair specialist: Already domain-agnostic (synthesis, coordination, order)
- ✅ Non-core specialists: Appropriately domain-specific (Azure, CI/CD, database, API, etc.)

**Rationale**: The system is designed to work across ANY domain (legal, medical, business, creative, technical, etc.). Base prompts and core team roles must use language that applies universally. Terms like "versions", "pricing", "availability" sound product/technology-focused. More generic terms like "methodologies", "standards", "requirements", "best practices", "frameworks" apply across all domains while preserving the same semantic meaning.

**2025-10-12: Chair Prompt - Anti-Convergence & Anti-Directive Language**

**Context**: User observed two Chair behaviors that go against design principles: (1) Chair saying "specialists converge on..." which explicitly declares convergence rather than letting it emerge naturally, and (2) Chair directing specialists on what to do next rather than just synthesizing what was discussed.

**Changes Made**:

1. **prompts.py - Updated Chair SYNTHESIS FOCUS guidance (lines 924-940)**:
   
   **Anti-Convergence Changes**:
   - Added "specialists converge" and "converging on" to forbidden consensus language list
   - Previous forbidden list: "the room is aligned", "we agree on", "consensus on one path", "everyone supports"
   - Updated forbidden list: Added "specialists converge", "converging on" to above
   - Changed guidance from "Simply summarize what was said" → "Simply summarize what was actually discussed"
   - Added explicit principle: "**Convergence should happen naturally from the discussion, not be explicitly declared**"
   - **Removed premature finalization language**: Changed "Later phases: 'Any additional insights before we finalize?'" → "All non-final phases: 'Specialists, any further concerns?' or 'Any additional insights?'"
   - Added prohibition: "❌ NEVER mention finalization/closure in non-final phases (e.g., 'before we finalize', 'wrapping up', 'nearly done')"
   - Added principle: "**Do NOT signal closure prematurely** - only the Final Phase should reference finalization"
   
   **Anti-Directive Changes**:
   - Removed: "Suggest which specialists might address remaining gaps" (line 930) - this was directive
   - Replaced with: "Bringing in specialists: Only when you observe specialists signaling (explicitly or implicitly) that specific expertise is needed"
   - Added domain-agnostic examples showing Chair responding to specialist signals: "Specialist A raises concerns about [specific topic] → signal that Specialist B's expertise may be needed"
   - Added principle: "You RESPOND to specialist signals, you don't proactively decide what expertise is needed"
   - Critical clarification: Chair can use judgment to bring in specialists based on signals, BUT does not tell them what to do
   - When bringing specialists in: "Discussion has touched on [topic]. @[Specialist Name]" (they read history and autonomously contribute)
   - Simplified neutral questions to be less directive: "Specialists, any further concerns?" instead of "do you have any further critical concerns?"
   - Added explicit prohibition: "❌ NEVER direct specialists on what to do next (e.g., 'we should address X', 'Specialist A, you should focus on Y')"
   - Added explicit principle: "**Your role is synthesis, not direction** - let specialists autonomously decide what to contribute next"
   - Added expanded FORBIDDEN section with examples: "Do NOT direct specialists on what to do - whether bringing them in OR already in the room"
     - ❌ When bringing in: "@[Specialist], can you address [task]?"
     - ✅ When bringing in: "Discussion touched on [topic]. @[Specialist]" (they autonomously assess)
   
   **Room Management Changes** (lines 856-906):
   - Changed: "YOU make the final decision on whether to bring them in" → "Your role is to RECOGNIZE these signals and bring in the appropriate specialist"
   - Updated example to domain-agnostic and non-directive: "@[Specialist A] raised concerns about [topic]. @[Specialist B]"
   - Added explicit instruction: "They will read the full discussion history and autonomously decide how to contribute"
   - Added principle: "You're responding to signals from specialists, not proactively deciding what expertise is needed"
   - Added principle: "**Do NOT tell them what to do** - just bring them in and let them assess how they can help"
   - Updated "WHAT YOU DO NOT DO" section: Added "❌ DO NOT direct specialists on what to do (whether bringing them in or already in the room)"
   - Updated "WHAT YOU DO NOT DO" section: Changed to "**Your role is neutral synthesis, not direction** - specialists autonomously decide what to contribute"
   - Updated: "Only bring specialists in when their expertise is genuinely needed" → "Only bring specialists in when you observe signals from current specialists"
   - Updated all example flows to show Chair responding to specialist signals, specialist reading history and autonomously contributing

**Rationale**: Chair was acting as a directive facilitator rather than a neutral synthesizer. By directing specialists on what to address next, suggesting who should cover topics, proactively deciding what expertise is needed, or signaling premature finalization, Chair was imposing their own judgment and creating artificial pressure on the conversation. 

**Chair's Role**:
- ✅ Synthesize what was actually discussed
- ✅ RESPOND to signals from specialists about what expertise is needed (explicit requests or implicit concerns)
- ✅ Use judgment to bring in specialists, BUT let them autonomously decide how to contribute
- ❌ Proactively decide what expertise is needed based on their own judgment alone
- ❌ Direct specialists on what to do - whether bringing them in OR already in the room
- ❌ Declare convergence explicitly
- ❌ Signal closure/finalization prematurely (only Final Phase should reference finalization)

This preserves specialist autonomy and candid discussion dynamics. Specialists drive what expertise is needed through their discussions and concerns. Chair recognizes those signals and acts on them, but doesn't impose their own view of what's needed. When Chair brings in a new specialist, that specialist reads the discussion history and autonomously determines how to contribute - Chair doesn't tell them what to do. Convergence and focus emerge naturally from the content, not from Chair's meta-commentary or direction. By avoiding premature finalization language ("before we finalize", "wrapping up"), Chair keeps the discussion open without creating pressure to close.

**Domain-Agnostic**: All examples in Chair's prompt now use generic placeholders ("Specialist A", "Specialist B", "[topic]") rather than specific specialist names or domain-specific examples, maintaining the system's domain-agnostic design.

**2025-10-12 Late Evening (Session 2): Output Formatting + Hybrid Architecture Documentation**

**Context**: Fixed output formatting issues (extra newlines) and fully documented the stagnation detection hybrid architecture after user question about how values are computed.

**Changes Made**:

1. **Output Formatting Improvements**:
   - `axion_swarm/search.py` line 319: Added `\n` after search timing output for better spacing
   - `axion_swarm/graph.py` lines 117, 119: Removed `\n` from [GRAPH] output (print() adds its own)
   - `main.py` line 294: Removed extra `print()` that was adding double blank line
   - `main.py` line 504: Added `print()` after user input for clean separation from [GRAPH] output
   - `axion_swarm/checkpoint.py` line 193: Removed `\n` from checkpoint save output
   - Result: Clean single blank lines throughout output, no duplicate spacing

2. **Debug Mode Gating**:
   - `main.py` lines 293-320: Added `DEBUG` environment variable check (`DEBUG=true` to enable)
   - Node execution debug output now gated behind `DEBUG=true`
   - Stagnation equation output remains always-on for tuning purposes (intentional)

3. **ARCHITECTURE.md - Documented Hybrid Stagnation Detection**:
   - Lines 401-450: Added comprehensive "How It Works (Hybrid Architecture)" section
   - **Local Python Analysis** (lines 406-410): Explains deterministic computation, message scanning, continuous probability
   - **LLM Decision** (lines 430-438): Explains Chair receives probability + syntheses, makes semantic judgment
   - **Why Hybrid?** (lines 444-450): Documents benefits of combining quantitative signals with semantic understanding
   - Includes concrete examples of how probability calibrates LLM threshold
   - Documents what Chair receives vs what's debug-only
   - Line 419: Updated conditional planning cap from 0.10 to 0.06 (reflecting earlier tuning)

4. **main.py - HTML Entity Decoding for Human Display** (line 406):
   - Added `html.unescape()` to decode XML/HTML entities before displaying Search tool messages
   - Humans now see: `network & data isolation` instead of `network &amp; data isolation`
   - LLMs still receive properly XML-encoded text (unchanged)
   - Improves human readability without affecting specialist functionality

5. **ARCHITECTURE.md - Documented Dual-Audience XML Architecture** (lines 2819-2848):
   - Added "Dual-Audience Architecture - XML Encoding Strategy" section
   - Explains why LLMs receive XML-encoded text (`&amp;`, `&lt;`, etc.)
   - Explains why humans see decoded text (`&`, `<`, etc.)
   - Documents CDATA trade-offs and why XML entities are preferred
   - Notes that both representations are semantically identical

**Rationale**: User asked "do we get values from LLM or local state?" revealing the hybrid architecture wasn't clearly documented. Added comprehensive explanation of how local Python computes observable signals, then LLM makes semantic judgment using those signals as guidance. This clarifies the design rationale: deterministic + tunable (local) combined with nuanced content understanding (LLM).

**2025-10-12 Late Evening (Session 1): Reduced Conditional Planning Weight**

**Context**: Reviewed Phase 4 stagnation detection from test case. System computed 34% probability (LOW-MODERATE) but triggered anyway. Analysis revealed equation was penalizing specialists for following prompt instructions: "Answer with stated assumptions, THEN ask clarifying questions" uses conditional language but IS desired behavior.

**Changes Made**:

1. **agents.py - Reduced Conditional Planning Weight (3 locations)**
   - Line 1733: Calculation `min(conditional_count / 15.0, 0.10)` → `min(conditional_count / 15.0, 0.06)`
   - Lines 1925-1928: Debug output formula updated to match
   - Line 2038: Documentation updated: `+0.10` → `+0.06`
   - Effect: At 3 conditional phrases (test case), contribution drops from 10% → 6% (-4 points)
   - Result: Pattern "Assuming X, recommend Y; if Z, then A" penalized less heavily

2. **ARCHITECTURE.md - Updated Stagnation Equation Documentation**
   - Line 746: Formula caps updated from 0.10 to 0.06
   - Line 749: Caps description updated from 10% to 6%
   - Line 751: Added note explaining rationale (conditional language accompanies good answers)
   - Lines 944, 946, 956: Example calculation updated to reflect new weight

**Rationale**: Conditional planning weight was misaligned with prompts. System explicitly asks specialists to "answer with assumptions and provide conditional paths." The 10% penalty contradicted this design - specialists providing flexible answers ("Assuming SMB multi-tenant, use shared schema; if enterprise, use schema-per-tenant") were being penalized for good behavior.

**Validation Plan**: Observe signal behavior over next 3-5 conversations. Conservative ±4% adjustment allows iterative refinement without destabilizing equation.

**2025-10-12 Evening: Stagnation Equation Tuning Based on Test Case Validation**

**Context**: After documenting full test case validation (Phase 1 → Final Phase), analyzed Chair's stagnation detection performance. Test triggered at Phase 4 with 55% probability - timing was good, but Phase 4 contributions were substantive and Final Phase output was massive (~11k words), suggesting room for one more iteration phase. User preference: "I would rather spend a bit more money on our LLM than end early" - favor thoroughness over efficiency.

**Changes Made**:

1. **agents.py - Reduced User Silence Weight (3 locations)**
   - Line 1664: Calculation `min(user_silence_phases * 0.10, 0.50)` → `min(user_silence_phases * 0.08, 0.40)`
   - Line 1883: Debug output formula updated to match
   - Line 2034: Documentation updated: "AGGRESSIVE" → "CONSERVATIVE", note "favors thoroughness"
   - Effect: At 3 phases silence, contribution drops from 30% → 24% (-6 points)
   - Result: Allows ~1 additional phase before typical convergence trigger

2. **ARCHITECTURE.md - Added Complete Test Case Validation**
   - Documented Phase 1 observations: 8 behaviors beyond single-LLM (parallel perspectives, autonomous search, explicit assumptions, risk-first, ethical grounding, triage-first, no premature consensus, candid discussion)
   - Documented Phase 2 observations: Iterative social context - building not repeating, explicit cross-referencing, refinement through addition, chair as true synthesizer
   - Documented Phase 4 observations: Autonomous convergence at 55%, new roles emerged organically, concrete deliverables crystallized, hard numbers with citations
   - Documented Final Phase observations: Complete gear shift to deliverables - all specialists produced ~2000-word comprehensive plans with JDs/budgets/checklists, Chair synthesized into master plan
   - Added Stagnation Equation Performance Analysis with tuning proposal

**Validation Plan**: Observe next 3-5 conversations to confirm Phase 5 contributions are substantive (not repetitive). If repetitive, may need to adjust back to 9%/phase as middle ground.

**2025-10-12: Documented Fundamental Model + Internal Team Architecture**

**Context**: Received external critique suggesting tests, schemas, benchmarks, and formal documentation. Assessed project state (4-day-old greenfield) and decided to focus on documenting fundamental mental model rather than premature formalization.

**Changes Made**:

1. **ARCHITECTURE.md - Added "The Fundamental Model" section (+137 lines)**
   - Documented User Pattern: async minimum 3h, average 1.5d response time (grounded in real-world async collaboration patterns observed across engineering teams and support contexts)
   - Documented Team Model: internal expert team collaboration while User away
   - Documented "Why This Architecture": 5 key decisions driven by async pattern (search, assumptions, phase-gating, Chair synthesis, convergence)
   - Documented "Phases Build Shared Context": iterative collective learning, not just sequential contributions
   - Added "How Architecture Supports Collaborative User Participation" with 7-step flow example
   - Clarified timing: system fast (<1 min), user flexible (seconds to days)
   - Added Chat UI pattern documentation

2. **ARCHITECTURE.md - Documented Core Team vs Domain-Specific Specialists**
   - Core team (Context, Research, Skeptic, Ethicist, Engineer) is domain-agnostic
   - Current technical specialists (DB, Cloud, Backend, etc.) are **test case only** - not prescriptive
   - System designed for ANY domain (legal, medical, business, creative, technical)
   - Added "Research: Architectural Consideration" section noting it may become system-level alongside Chair

3. **prompts.py - Added Internal Team Framing to BASE_INSTRUCTION (+36 lines)**
   - "YOU ARE AN INTERNAL EXPERT TEAM": User doesn't see multi-phase discussion, speak candidly, Chair synthesizes
   - "ASYNC WITH USER, REAL-TIME INTERNALLY": User won't respond for hours/days, deliver comprehensive answers
   - "PHASES BUILD SHARED CONTEXT": Phase 1 independent, Phase 2 cross-pollinate, Phase 3+ converge
   - Fixed Context specialist role from "need clarification BEFORE..." (blocker) to "identify gaps so team can make assumptions" (triage)

4. **agents.py - Added Roster Composition Comment (+9 lines)**
   - Documents core team vs non-core distinction
   - Notes technical specialists are test case validating architecture
   - Provides examples for other domains

5. **.env.example - Created (NEW FILE)**
   - Complete environment variable template
   - All Azure OpenAI, Ollama, Tavily configs

**What We Rejected**:
- Formal test infrastructure (premature for 4-day greenfield project)
- JSON schemas for Chair outputs (freeform is fine at this stage)
- Checkpoint versioning (not hitting drift yet, solve when needed)
- Provider parity benchmarks (high effort, unclear ROI)
- "Development Philosophy" meta-documentation (removed after adding - let patterns emerge naturally)

**Key Insights Documented**:
- Async pattern (minimum 3h, average 1.5d) is grounded in real-world distributed work patterns (context-switching, meetings, incidents, timezones, end-of-day boundaries) - timing applies broadly across domains where users face similar interruptions
- System responds fast (<1 min multi-phase discussion), User response time is flexible (supports both real-time chat and async consultation)
- Internal team collaboration allows specialists to speak candidly, debate, refine before Chair synthesizes for User
- Multiple phases may occur between User input and Chair response (team discusses User's clarification internally before synthesizing back)
- Architecture already supports ongoing User participation at any phase - async is default expectation, not limitation

**Rationale**: Documentation-first approach preserves conceptual progress. The fundamental mental model (internal expert team + async collaboration pattern) drives all architectural decisions and needed to be explicit in our single source of truth documentation. Changes are additive (no functionality removed), and domain-agnostic across all fields.

**Validation Against Test Case (2025-10-11 Evening):**

Ran SaaS team planning question (complex multi-domain: HR, tech stack, compliance, service tiers) to validate architecture. Observed behaviors that **cannot happen with sequential single-LLM**:

1. **Parallel Diverse Perspectives** - Context (triage), Research (search), Skeptic (risk), Ethicist (principles) assessed SIMULTANEOUSLY with different lenses. Single LLM does sequential or blended reasoning.

2. **Autonomous Real-Time Search BEFORE Responding** - Research specialist performed 4 targeted searches (SOC2 requirements, Azure patterns, team benchmarks, SaaS tiers) autonomously BEFORE writing response. Single LLM typically responds first, may suggest searches after.

3. **Explicit Assumption Stating with Confidence Levels** - Each specialist stated assumptions explicitly ("Assuming X, confidence: medium"). Single LLM embeds assumptions in prose without flagging uncertainty.

4. **Risk-First vs Feature-First Orientation** - Skeptic led with "Biggest single risk is underestimating security/compliance" rather than describing solution. Single LLM typically presents solution with risks buried in "considerations" section.

5. **Ethical Framework Grounding** - Ethicist tied Privacy Lead recommendation to explicit principles (DIGNITY, NON-HARM, CONSENT, TRANSPARENCY). Single LLM mentions compliance but doesn't ground in ethical framework.

6. **Triage Before Solving** - Context identified 6 critical ambiguities (timeline, budget, customer profile) and provided prioritized defaults BEFORE proposing team. Single LLM jumps to solution with embedded assumptions.

7. **No Premature Consensus** - Each specialist focused on their domain only, didn't try to provide "complete" answer. Single LLM attempts comprehensive response in one shot.

8. **Candid Internal Discussion** - Direct language ("Biggest single risk", "do not defer this", confidence levels). Single LLM typically more diplomatic/hedged in single-perspective output.

**Why These Behaviors Emerge**:
- Agent isolation prevents hidden coordination → genuine independent perspectives
- Phase-gated visibility (Phase 1) → no groupthink, can't see others yet
- Specialist personas → focused domain expertise without trying to cover everything
- Async autonomy requirement → must use @[Search] for current info, can't wait for user
- Internal team framing → candid discussion without diplomatic hedging

**Validation Conclusion**: Architecture produces observably different behavior patterns than single-LLM sequential reasoning. The multi-agent system exhibits parallel assessment, autonomous information-gathering, explicit uncertainty, risk-first thinking, and candid internal discussion that cannot be replicated with prompt engineering alone.

**Phase 2 Observations - Cross-Pollination (Iterative Social Context):**

Observed how specialists refined thinking after seeing Phase 1 responses. Behaviors demonstrating **iterative collective learning**:

1. **Building, Not Repeating** - Context specialist didn't repeat Phase 1 triage, instead **prioritized by impact** and assessed Research's baseline as "reasonable starting point but will shift". Added NEW layer without redundancy.

2. **Explicit Cross-Referencing** - Research: "based on recent searches AND room's input"; Skeptic: "Building on @[Research specialist] and @[Ethicist specialist]". Specialists explicitly acknowledged whose thinking they're building on.

3. **Refinement Through Addition** - Skeptic didn't contradict Research's "Security Lead" recommendation, added: "usually not sufficient - need AppSec/DevSecOps as separate role". Debate through layering, not replacement.

4. **Organizational Structure Emerged** - Ethicist added org structure (reporting lines, collaboration model) and sizing (0.5-1.0 FTE) that wasn't in Phase 1. Details emerged from seeing team structure develop.

5. **Increasing Specificity** - Context Phase 1: "6 ambiguities"; Phase 2: "prioritized by impact on headcount/role scope". Chair distilled into "5 specific questions". Focus sharpened through iteration.

6. **Evidence-Based Synthesis** - Research integrated search findings with team discussion: "SOC2 requires X + Azure guidance recommends Y + room consensus on Z = 11-role plan". Multi-source reasoning.

7. **Chair as True Synthesizer** - Organized disparate inputs into structure: Summary → Non-Negotiables → Immediate Priorities → Core Team → Tech Guidance → Tradeoffs → Next Steps. NO single specialist could produce this - it's genuine synthesis of collective knowledge.

8. **No Premature Consensus** - Each specialist maintained domain focus (Context: triage, Research: evidence, Skeptic: risk, Ethicist: ethics) while refining based on others. No bland "we all agree" - maintained tension while converging.

**Why Single-LLM Cannot Do This**:
- Single LLM has no memory of "what team already knows" → would repeat all information
- Single LLM attempts comprehensive response → wouldn't refine through iteration
- Single LLM blends perspectives → no explicit cross-referencing showing who influenced whom
- Single LLM has no true synthesis → would present one unified view, not organized collective wisdom

**Key Insight**: Phase 2 demonstrates **iterative social context** - collective understanding builds through specialists reacting to each other. This is NOT "multiple perspectives in sequence" - it's ACTUAL collaborative intelligence where each contribution creates context for the next, and synthesis emerges from genuine interaction.

**Phase 4 Observations - Autonomous Convergence Detection:**

Chair's stagnation detection triggered at **55% probability** and moved to final phase WITHOUT user intervention. This is the architecture's autonomous operation in real-time:

1. **Stagnation Equation Working** - Chair computed: User silence (3 phases) = +30%, Phase progression = +0%, Questions (18) = +15%, Conditional phrases (4) = +10% → **55% MODERATE threshold**. System decided "enough deliberation, time to synthesize" autonomously.

2. **New Roles Emerged Organically** - Context specialist added RevOps/Billing Engineer + SaaS/Privacy Legal Counsel that WEREN'T in Phase 1-3 recommendations. Team understanding deepened → new requirements surfaced. Not planned upfront, emerged through iteration.

3. **Concrete Deliverables Crystallized** - Ethicist: "Privacy & Trust Requirements Matrix" with specific contents (MVP vs Standard vs Premium vs Enterprise controls). Skeptic: "Tenant-Isolation CI Gate" with exact test requirements (evil-tenant tests, RLS verification, PII discovery). From concepts → executable specifications.

4. **Hard Numbers with Citations** - Research: "$30k-$120k", "6-12 months", "Type I 1-3 months" with THREE SOURCE URLS. Not generic advice - specific, defensible, citeable guidance.

5. **Engineering-Level Specificity** - Skeptic specified: "Row-level security verification for every data access path (ORM, direct SQL, background jobs)", "cache/session/feature-flag partitioning checks", "PII discovery checks in CI". Actionable technical requirements, not high-level recommendations.

6. **Multi-Source Reasoning** - Research integrated: search results + team discussion + budget constraints + timeline reality → synthesis. Example: "if Type II required at launch → hire now + budget $50k-$120k; else Type I → upgrade later". Decision tree from multiple inputs.

7. **Chair's Final Synthesis Actionable** - Three immediate actions with owners: (1) Create matrix, (2) Implement CI gate, (3) Make SOC2 decision. Plus condensed hiring priority with FTE vs contractor guidance. Single-LLM would give general advice; Chair gave **work plan**.

8. **Autonomous Phase Transition** - System detected "3 phases of user silence + 18 questions asked + conditionals accumulating = stagnation signal" and Chair moved to final phase. No user prompt needed. This is the async autonomy requirement in action - team concluded deliberation and prepared final synthesis.

**Why This Matters for Async Collaboration**:
- User last spoke in Phase 1, system continued autonomously through Phases 2-4
- Team built understanding, added roles, specified requirements, computed costs
- Chair detected "we've explored enough, time to deliver synthesis"
- **All in <7 minutes** while user was unavailable (remember: 3h-1.5d response time expected)
- Final phase trigger = "we're ready to present complete answer, but user can still redirect if needed"

**Validation**: Stagnation detection equation is working as designed - balancing thoroughness with efficiency, making autonomous convergence decisions that respect the async user pattern.

**Final Phase Observations - Complete Shift to Deliverables:**

After stagnation detection triggered, Notice announced "final discussion phase" and specialists **completely changed their output format**. This is NOT "more of the same" - it's a distinct mode:

1. **FINALIZED / CONDITIONAL / SPECULATIVE Structure** - ALL specialists (Context, Research, Skeptic, Ethicist) independently adopted the SAME three-tier confidence framework: "What I'm confident about / What depends on choices / What's speculative". No coordination needed - the final phase prompt triggered unified structure.

2. **Complete Job Descriptions** - Each specialist produced **paste-ready JDs** with responsibilities, requirements, 30/60/90-day deliverables. Context: 15 complete JDs. Research: full roles with deliverables. Skeptic: 15 roles with security focus. Ethicist: 15 roles with ethical responsibilities. This is 4x specialists independently producing near-identical comprehensive hiring plans.

3. **Actionable Checklists** - Every specialist gave "IMMEDIATE ACTIONS YOU CAN TAKE TODAY" with numbered steps. Context: 8 actions. Research: 6 actions. Skeptic: 7 actions. Ethicist: 6 actions. Not high-level advice - specific executable tasks like "Procure Drata/Secureframe/Vanta", "Retain pentest vendor", "Create Privacy Matrix".

4. **Budget Numbers with Ranges** - Research: "$30k-$120k+ for SOC2", "FY1 $1.2M-$2.5M", "$2k-$10k/month Azure". Skeptic: "$30k-$120k", "$1.5M-$2.5M lean, $2.5M-$5M enterprise". Ethicist: similar ranges. Concrete financial planning, not vague estimates.

5. **Decision Trees** - Specialists structured as: "If SMB → X, If Enterprise → Y, If Type II required → Z". Research: 4 conditional branches. Skeptic: 6 conditional sections. Ethicist: 8 conditional items. User can follow decision logic to their specific scenario.

6. **User Questions with Impact** - Each specialist asked 5-9 clarifying questions AND explained what each answer changes. Research: "Timeline + Budget + Segment changes headcount/contractor mix". Skeptic: "These three choices materially change hiring and timing". Not just "what do you want" - explained decision weight.

7. **Confidence Levels on Everything** - Research: "HIGH confidence: Azure choice / MEDIUM: exact headcount / LOW: precise FY1 cost". Skeptic: confidence levels on each recommendation. Ethicist: marked assumptions clearly. User knows what to trust vs validate.

8. **Multiple Deliverable Options** - Context, Research, Skeptic, Ethicist ALL offered "pick Option A/B/C and I'll produce X for you next". Specialists aren't just answering - they're offering to continue with specific work products based on user priorities.

9. **Chair's Master Synthesis** - Organized all specialist input into: Stack → Hires → JDs → Tiers → Tenancy → Compliance → Conditional → Speculative → Open Questions → Actions → Options. One coherent plan from 4 comprehensive specialist reports. This is REAL synthesis, not summary.

10. **Length Explosion** - Phase 1-4: specialists gave 1-3 paragraph responses. Final Phase: Context ~2000 words, Research ~2500 words, Skeptic ~2000 words, Ethicist ~2200 words, Chair ~2000 words. Total final phase output: **~11,000 words of structured, actionable planning**.

**Why Single-LLM Cannot Do This**:
- Single LLM would produce ONE comprehensive answer, not FOUR parallel comprehensive answers that Chair synthesizes
- Single LLM has no "gear shift" from iterative discussion → final deliverable mode
- Single LLM blends all perspectives into one voice; this shows Context/Research/Skeptic/Ethicist EACH producing complete plans from their domain focus
- Single LLM would pick ONE budget/timeline/approach; this gives decision trees with tradeoffs across all scenarios
- Single LLM produces "an answer"; this produces "a complete project planning package ready to execute"

**Key Insight**: Final phase isn't "summary of discussion" - it's **production mode**. Specialists shifted from "refining understanding" to "delivering complete work products". Each produced hiring plans, JDs, budgets, action checklists, and decision trees independently. Chair then synthesized into single coherent plan with user options (A/B/C deliverables). 

The async pattern requirement drove this: specialists KNOW user may not respond for 3h-1.5d, so final phase must be COMPLETE and ACTIONABLE without further input. This is the architecture's autonomous operation requirement manifest as comprehensive deliverables.

**Time Check**: Entire discussion (Phase 1 → Final Phase) completed in ~10 minutes while user was unavailable. System autonomously:
- Triaged ambiguities (Phase 1)
- Built collective understanding (Phase 2-3)
- Detected convergence opportunity (Phase 4, 55% stagnation)
- Produced complete project plan with JDs, budgets, action items (Final Phase)

This is the architecture working exactly as designed for async collaboration.

**Stagnation Equation Performance Analysis (2025-10-11 Test Case):**

The Chair's stagnation detection triggered at **Phase 4 with 55% probability**. Let's assess whether this was the right timing:

**What Actually Happened:**
- **Phase 4 contributions were substantive**: Context added RevOps/Billing + Legal roles not mentioned in Phase 1-3. Research provided hard SOC2 cost/timeline numbers ($30k-$120k, 6-12 months) with citations. Skeptic specified tenant-isolation CI gate with technical details. Ethicist produced Privacy & Trust Requirements Matrix specification.
- **Final Phase delivered complete work products**: All 4 specialists produced comprehensive hiring plans (~2000+ words each), paste-ready JDs, budgets, action checklists, decision trees. Chair synthesized into coherent plan. Total output: ~11,000 words of actionable planning.
- **User got complete answer**: System autonomously triaged, deliberated, converged, and produced project-ready deliverables in 10 minutes.

**Equation Components at Trigger:**
1. **User Silence: +30%** (3 phases) - Appropriate signal that user unavailable, team should conclude
2. **Phase Progression: +0%** (Phase 4, check #1) - Formula: `(1-1)*0.25 = 0%`. Allows early exploration before forcing conclusion
3. **Questions: +15%** (18 questions, capped at 15%) - Signals uncertainty/conditionals accumulating
4. **Conditionals: +10%** (4 conditional phrases) - "If SMB then X, if Enterprise then Y" planning
5. **Total: 55% = MODERATE threshold** → Chair triggered final phase

**Was Timing Right?**

**Evidence it was GOOD timing:**
- Phase 4 added new substantive content (not repetition)
- Final Phase produced exceptional deliverables (not premature)
- Specialists had explored sufficiently to give confident/conditional/speculative breakdowns
- User got actionable plan without unnecessary iteration

**Evidence for "could have gone one more phase":**
- Phase 4 still had new roles emerging (RevOps, Legal)
- 18 questions asked (still seeking information)
- Final Phase was ~11k words (specialists had a LOT saved up)

**Conservative Tuning Observations (NOT prescriptive changes):**

Given the excellent output quality, the current tuning appears sound. However, for **observational tracking**:

1. **User Silence Weight (currently +30% at 3 phases, caps at +50% at 5 phases):**
   - Observation: 3 phases of silence appropriately signaled "user won't respond soon"
   - Consider for next observation: Does the +10%/phase ramp feel right, or would +8%/phase (24% at 3 phases) allow one more iteration before triggering?
   - Status: **Likely appropriate as-is** - 30% at 3 phases contributed meaningfully without dominating

2. **Phase Progression Weight (currently 0% at Ph4, 25% at Ph5, 50% at Ph6, 75% at Ph7, 100% at Ph8):**
   - Observation: 0% at Phase 4 allowed substantive Phase 4 contributions before triggering
   - Consider for next observation: The guaranteed trigger at Phase 8 (100%) is appropriate for the "answer with assumptions" philosophy
   - Status: **Working as intended** - didn't force early conclusion, will force eventual convergence

3. **Questions Weight (currently +15% cap at 20 questions):**
   - Observation: 18 questions contributed +15%, signaling lots of conditionals/uncertainty
   - Consider for next observation: Were these "new questions" or "refinement questions"? If refinement, maybe questions in Final Phase should weight less
   - Status: **Monitor** - if questions in later phases are refinements not blockers, consider whether cap should be slightly lower (~12-13% instead of 15%)

4. **Conditionals Weight (currently +10% cap at 15 phrases):**
   - Observation: 4 conditionals contributed +10%, appropriate signal that planning has "if/then" branches
   - Status: **Appropriate as-is**

**Overall Assessment:**

The equation triggered at **the right time** - Phase 4 was substantive, Final Phase was comprehensive, and user got complete actionable plan. The 55% MODERATE threshold performed exactly as intended: allowed sufficient deliberation while respecting async user pattern.

**No changes recommended at this time.** Continue collecting observations across multiple conversations to see if patterns emerge. The conservative ±3-5% tuning philosophy means we should see this equation perform across 5-10+ conversations before considering any adjustments.

**Data Collection Guidance:**

For future tuning observations, track:
- Did Final Phase feel "rushed" or "over-baked"?
- Were Phase N contributions substantive or repetitive?
- Did specialists produce actionable deliverables or vague summaries?
- Was the phase count appropriate for question complexity?

Current test case: ✅ **Excellent performance** - triggered at right time, produced exceptional output, respected async pattern.

**Proposed Tuning Adjustment (Conservative, ±3-5% range):**

**Assessment**: Phase 4 contributions were substantive (new roles emerged, hard numbers provided, technical specs defined), and Final Phase output was massive (~11k words). Evidence suggests the system *could* have supported one more iteration phase before final synthesis without degrading quality.

**Proposed Change**: Reduce **User Silence Weight** from **10%/phase → 8%/phase** (cap at 40% instead of 50% at 5 phases)

**Rationale**:
1. **Conservative adjustment**: -20% to one component, well within ±3-5% per-term guideline
2. **Evidence-based**: 3 phases of silence appropriately signals async pattern, but shouldn't dominate the equation (was contributing 30% of the 55% total)
3. **Phase progression weight (25%/check) will still force convergence** at Phase 8 (100%), maintaining "answer with assumptions" philosophy
4. **Preserves other signals**: Questions (15% cap) and Conditionals (10% cap) worked well, leave unchanged

**Effect on Test Case** (simulated):
- Original: 30% (silence) + 0% (phase) + 15% (questions) + 10% (conditionals) = **55% → TRIGGERED**
- With adjustment: 24% (silence) + 0% (phase) + 15% (questions) + 10% (conditionals) = **49% → Would NOT trigger** at Phase 4
- Next iteration (Phase 5): 32% (silence at 4 phases) + 25% (phase progression) + questions + conditionals = likely **70-75% → WOULD trigger**

**Expected Outcome**: Allow one additional substantive phase before convergence, while still forcing conclusion by Phase 5-6 in typical cases (Phase 8 guaranteed via phase progression weight).

**Recommendation**: Update `SILENCE_WEIGHT` calculation in Chair's stagnation detection from `min(user_silence_phases * 0.10, 0.50)` to `min(user_silence_phases * 0.08, 0.40)`.

**Validation Plan**: Observe performance across next 3-5 conversations. Track whether Phase 5 contributions are substantive or repetitive. If repetitive, this adjustment may be too permissive (revert or adjust back to 9%/phase as middle ground).

**Status**: ✅ **IMPLEMENTED (2025-10-12)** - Updated `agents.py` lines 1664, 1883, 2034. User preference for thoroughness over efficiency ("I would rather spend a bit more money on our LLM than end early") drives this adjustment. Will observe performance across next 3-5 conversations to validate.

**Implementation Details:**
- Changed: `min(user_silence_phases * 0.10, 0.50)` → `min(user_silence_phases * 0.08, 0.40)`
- Effect: At 3 phases silence: 30% → 24% contribution (-6 percentage points)
- Result: Typical discussions will run one additional phase before convergence
- Phase 8 still guaranteed via phase_progression weight reaching 100%

0a. **CRITICAL BUG FIX: Final Phase State Propagation (2025-10-11)**
   - **BUG**: `check_continuation()` was unconditionally returning `{"final_phase_needed": False}`, overwriting Chair's explicit stagnation decision
   - **SYMPTOM**: Chair detected stagnation and set `final_phase_needed=True`, but next phase didn't recognize it as final phase
   - **ROOT CAUSE**: Line 2833 in `agents.py` blindly set flag to False instead of preserving existing value from state
   - **FIX**: Changed `check_continuation()` to preserve `final_phase_needed` value from state: `final_needed = state.get("final_phase_needed", False)`
   - **IMPACT**: Final phase now properly triggered when Chair forces it via stagnation detection
   - **RESULT**: Specialists now receive final phase prompt ("provide your concluding assessment") and passing is forbidden
   - **TEST**: Verified Chair's explicit `final_phase_needed=True` decision now propagates through graph workflow correctly

0. **Stagnation Threshold Logic Fix - Premature Trigger Prevention (2025-10-12)**
   - **BUG FIX**: Fixed critical disconnect between computed stagnation probability and Chair's decision threshold
   - **Problem Identified**: System computed sophisticated probability (e.g., 30%) with threshold guidance ("MODERATE-HIGH threshold - need substantial stagnation"), but Chair's prompt contained **hardcoded override logic** that ignored the computed guidance:
     ```python
     # OLD: Always used LOW threshold when user silent for 1+ phases
     "🔴 Use LOW threshold - any hint of stagnation should trigger final phase." 
     if user_silence_phases >= 1
     ```
     This caused premature triggers at Phase 4 with 30% probability (should require MODERATE-HIGH threshold) because Chair was told to use LOW threshold (trigger on any hint).
   - **Root Cause**: Probability equation and threshold guidance were computed correctly, but prompt instructions overrode them with hardcoded "if user_silence ≥ 1 → LOW threshold" logic
   - **Observable Symptom**: Phase 4 stagnation at 30% despite:
     - 5 active searches bringing fresh information (-15% justification)
     - 3 new specialists just brought in who hadn't contributed yet
     - No actual synthesis repetition or blocking patterns
     - System's own guidance saying "MODERATE-HIGH threshold - need substantial stagnation"
   - **Solution**: Removed hardcoded threshold overrides and made Chair respect the computed threshold guidance:
     1. **Replaced hardcoded logic** with dynamic threshold calibration based on computed probability ranges
     2. **Added explicit calibration framework** mapping each probability range (0-20%, 20-40%, etc.) to specific decision criteria
     3. **Added progress indicators** that were being tracked by justification signals:
        - New specialists just brought in who haven't contributed yet
        - Active research activity (external searches providing fresh information)
     4. **Removed blocking indicator overrides** (e.g., "🔴 If YES + User silent → STAGNATED") and replaced with "weigh severity based on computed probability"
   - **Expected Behavior Change**:
     - **Before**: 30% probability at Phase 4 → Triggered (hardcoded LOW threshold)
     - **After**: 30% probability at Phase 4 → Continue (requires SUBSTANTIAL stagnation per MODERATE-HIGH threshold)
     - System now respects its own computed thresholds across all probability ranges
   - **Threshold Mapping** (now properly applied):
     - 0-20%: HIGH threshold → Only trigger if synthesis shows CLEAR, OBVIOUS stagnation
     - 20-40%: MODERATE-HIGH threshold → Only trigger if SUBSTANTIAL stagnation (← 30% falls here)
     - 40-60%: MODERATE threshold → Trigger if minor but definite stagnation
     - 60-75%: LOW-MODERATE threshold → Trigger on minor hints
     - 75-100%: LOW threshold → Trigger on any hint
   - **Files Modified**:
     - `axion_swarm/agents.py`: Updated Chair's stagnation prompt (lines ~2175-2224) to remove hardcoded overrides and apply computed threshold guidance
   - **Impact**: Prevents premature convergence when specialists are actively researching and new experts are being brought in; system now allows productive Phase 4-7 discussions to continue appropriately

1. **Adaptive Stagnation Model with Justification - Long-Term Tuning Project (2025-10-11)**
   - **FEATURE**: Redesigned stagnation detection with probabilistic scoring, aggressive baseline convergence, and justification signals
   - **Core Innovation**: Linear equation model with 9 tunable signals (5 stagnation + 4 justification), Chair uses computed probability to infer judgment threshold
   - **Baseline Convergence**: Phase progression reaches 100% at Phase 8 (was Phase 14), but justification signals allow Phase 8+ continuation when productive
   - **Stagnation Signals** (POSITIVE, push toward final):
     1. User silence: `min(silence_phases * 0.08, 0.40)` - 8%/phase, caps at 40% after 5 phases (tuned 2025-10-12)
     2. Phase progression: `(checks - 1) * 0.25` - UNBOUNDED, 25%/check, baseline 100% at Phase 8
     3. Low user engagement: Flat +0.20 if phase≥6 and user_msgs≤1
     4. Specialist questions: `min(questions/20, 0.15)` - caps at 15%
     5. Conditional planning: `min(conditionals/15, 0.10)` - caps at 10%
   - **Justification Signals** (NEGATIVE, allow continuation):
     1. Recent User response: -0.30 if User in current/last phase
     2. Recent User 1 phase ago: -0.15 if User 1 phase silent
     3. High User engagement: -0.20 if user_msgs ≥ 3
     4. Research activity: -0.15 if searches ≥ 2 in last 2 phases
     5. Answer mode: -0.10 if questions ≤ 2 in last 2 phases (specialists answering, not asking)
   - **Full Equation**: `P(stagnation) = max(0.0, min(Σ(stagnation) + Σ(justification), 1.0))`
   - **Max justification**: -0.75 total, can reduce 100% baseline to 25%, allowing Phase 8+ when justified
   - **Threshold Mapping**: Probability → Chair guidance (0-20% HIGH, 20-40% MOD-HIGH, 40-60% MOD, 60-75% MOD-LOW, 75-100% LOW)
   - **Philosophy**: "Answer with assumptions" for early conclusion + allow genuinely productive continuation (active User, new research, specialists providing answers)
   - **Long-Term Tuning Framework**:
     - All 9 signal weights are tunable constants in `agents.py` (lines 1641-1792)
     - Comprehensive DEBUG output logs full equation state for every stagnation check
     - Designed for iterative refinement based on real-world discussion data
     - Target metrics: Median phase, % at Phase 8+, false positive/negative rates, User satisfaction
     - Future: May add signals (pass rate, synthesis delta, specialist diversity) as patterns emerge
   - **Expected Behavior**:
     - Silent User + stagnation: Triggers Phase 5-6
     - Active User + stagnation: Triggers Phase 7-8
     - Active User + productive (research, answers): Can continue Phase 8-10+
     - Spinning/blocking discussions: Hard stop by Phase 8 (justification won't save them)
   - **Comprehensive DEBUG Output**: Shows equation, raw inputs, all signal computations with formulas, subtotals, full summation, bounds, threshold mapping
   - **State Propagation Fix**: Added `final_phase_needed` propagation in `execute_phase_parallel()`
   - **Files Modified**:
     - `axion_swarm/agents.py`: Enhanced `check_discussion_stagnation()` with 9-signal model, justification logic, comprehensive DEBUG
     - `ARCHITECTURE.md`: Updated with full signal model and long-term tuning framework
   - **Documentation Created**:
     - `STAGNATION_PROBABILITY_MODEL.md`: Mathematical framework
     - `AGGRESSIVE_CONVERGENCE_MODEL.md`: Convergence analysis
     - `STAGNATION_COMPLETE.md`: Implementation summary
   - **Impact**: Cost savings (Phase 5-7 typical) + flexibility (Phase 8+ when justified) + measurement infrastructure for ongoing optimization

-3. **Emphasize Primary Content in Search Results - Color Hierarchy (2025-10-11)**
   - **UX ENHANCEMENT**: Updated search result color scheme to emphasize primary content (answer + query) in white while making supporting evidence readable in light grey
   - **Rationale**: The `<answer>` element contains Tavily's AI-generated summary of ALL results - this is the main takeaway. Individual `<result>` contents are supporting evidence and should be visually secondary but still readable.
   - **XML Structure Change**: Moved `answer` from attribute to child element `<answer>...</answer>` for cleaner color coding
   - **Color Hierarchy** (from most to least prominent):
     1. **White (primary)**: `query="..."` attribute and `<answer>...</answer>` content (main answer/summary)
     2. **Light grey (supporting)**: `<result>` content excerpts (supporting evidence - brighter for readability)
     3. **Dark grey (metadata)**: `url`, `title`, `requester` attributes (subdued metadata)
     4. **Light green (structure)**: XML tags, brackets, attribute names (default background)
     5. **Light purple/red/blue (special)**: `@[specialist]` mentions override dark grey for requester
   - **Visual Impact**: Specialists immediately see the main answer in white, with supporting evidence readable in light grey, and metadata subdued in dark grey
   - **Files Modified**:
     - `main.py`: Updated `highlight_mentions()` to handle `<answer>` element and `<result>` content in light grey
     - `search.py`: Restructured XML to use `<answer>` element instead of attribute
     - `colors.py`: Added `LIGHT_GREY` constant and `light_grey()` function
     - `prompts.py`: Updated specialist guidance to emphasize `<answer>` as primary, `<result>` as supporting evidence
   - **Documentation**: Updated ARCHITECTURE.md color coding section and search result format example

-2. **Prevent Search Result Impersonation - Simplified Prompts (2025-10-11)**
   - **PROMPT SECURITY**: Removed detailed search result XML examples from specialist prompts to prevent LLM impersonation of search results
   - **Problem Observed**: Research specialist generated fake search results in its own message instead of using `@[Search][query]` syntax:
     ```
     [2025-10-11 13:53:00.374 CDT] Research specialist said: Search tool: recent search results: <results>...
     ```
     This should have been TWO messages: (1) specialist requests with `@[Search][query]`, (2) "Search tool:" responds with results
   - **Root Cause**: Prompts included detailed examples of search result XML format, which inadvertently taught specialists how to generate fake results
   - **Solution**: Removed all detailed search result format examples from specialist prompts
   - **What Specialists See Now**:
     - **Request syntax ONLY**: `@[Search][query]` with examples of how to request searches
     - **High-level description of what's in results**: Each search response includes who requested it, the search term, and multiple results with URLs, titles, and content excerpts
     - **NO XML schemas**: No examples showing `<results>`, `<result>`, or attribute structures
     - **NO format details**: Specialists know WHAT information they'll get, not HOW it's formatted
     - **Clear boundaries**: Explicit warnings that specialists NEVER create `<from>Search tool</from>` messages
   - **Prompt Changes**:
     - Removed detailed `<result url="..." title="...">...</result>` examples
     - Removed attribute schema details (`answer`, `requester`, etc.) from specialist view
     - Added multiple warnings: "NEVER create fake search results", "NEVER generate XML result blocks"
     - Simplified "How Specialists Request Searches" to show ONLY the request side
     - Changed "Using Search Results" to emphasize reading results, not formatting them
     - **Changed search request examples to natural language format** (not wrapped in XML `<message>` blocks):
       - Before: `<message>...<content>Need to verify. @[Search][query]</content></message>`
       - After: `Need to verify. @[Search][query]` (plain text as specialists would write it)
     - **Added "What's in Search Results" section** describing content (requester, search term, URLs, titles, excerpts) without revealing XML structure
   - **Result Format Docs** (kept in ARCHITECTURE.md for humans, removed from LLM prompts):
     - Detailed XML schemas remain in documentation for user reference
     - Specialists just see "you'll get results from Search tool:" without format details
   - **Files Modified**:
     - `axion_swarm/prompts.py`: Updated `BASE_INSTRUCTION` and `CHAT SESSION FORMAT` sections
   - **Rationale**: Less information about result format = less temptation to impersonate. Specialists need to know HOW to request searches and WHAT information they'll get, but not the exact XML structure.
   - **Documentation**: This change logged in ARCHITECTURE.md Recent Changes

-1. **HTML Entity Decoding & Unicode Punctuation Normalization for Search Results (2025-10-11)**
   - **SEARCH ENHANCEMENT**: All search result fields now undergo HTML entity decoding and Unicode-to-ASCII punctuation normalization
   - **Problem**: Tavily search results contained HTML entities (`&#x27;`, `&amp;`, etc.) and Unicode punctuation (smart quotes `"`, em dashes `—`, ellipsis `…`) that cluttered output and caused compatibility issues
   - **Solution**: Implemented two-stage cleaning process:
     1. **HTML Entity Decoding**: Converts HTML entities to their character equivalents (e.g., `&#x27;` → `'`, `&amp;` → `&`)
     2. **Unicode Normalization**: Converts Unicode punctuation to ASCII equivalents (e.g., `"` → `"`, `—` → `-`, `…` → `...`)
   - **New Function**: `normalize_unicode_punctuation()` in `search.py` handles Unicode → ASCII conversion
   - **Applied To All Fields**:
     - `<result>` content text
     - `url` attribute values
     - `title` attribute values  
     - `answer` attribute values (Tavily summaries)
     - `query` attribute values
   - **Unicode Mappings Implemented**:
     - Smart quotes (`"` `"` `'` `'`) → straight quotes (`"` `'`)
     - Em/en dashes (`—` `–`) → hyphens (`-`)
     - Ellipsis (`…`) → three dots (`...`)
     - Guillemets (`«` `»`) → straight quotes (`"`)
     - Bullets (`•` `·`) → asterisks (`*`)
     - Non-breaking spaces → regular spaces
   - **Processing Pipeline**:
     1. Decode HTML entities (prevent double-escaping)
     2. Normalize Unicode punctuation to ASCII
     3. Clean markdown/HTML formatting
     4. Re-escape for XML safety
   - **Console Color Coding Updates**:
     - **Primary content in white**: `query="..."` and `<answer>...</answer>` (main takeaways)
     - **Supporting evidence in light grey**: `<result>` content (supporting evidence - brighter for readability)
     - **Metadata in dark grey**: `url="..."`, `title="..."`, `requester="..."` (source metadata)
     - `@[specialist]` mentions in requester → **Light purple** (overrides dark grey)
     - XML structure (tags, brackets, attribute names) → **Light green** (default)
   - **Files Modified**:
     - `axion_swarm/search.py`: Added `normalize_unicode_punctuation()`, updated `clean_search_content()` and `format_search_results()`
     - `axion_swarm/colors.py`: Added `DARK_GREY` constant and `dark_grey()` function
     - `main.py`: Updated `highlight_mentions()` to apply different colors to different XML attribute types
   - **Benefits**:
     - **Compatibility**: ASCII punctuation works consistently across all terminals and editors
     - **Clarity**: Eliminates visual ambiguity from Unicode characters
     - **Copy/Paste**: Clean ASCII text copies correctly into code and documentation
     - **Readability**: Familiar punctuation without rendering issues
     - **Performance**: ASCII is more efficient for processing
   - **Documentation**: Updated ARCHITECTURE.md with normalization table, processing pipeline, and color coding details

0. **Search Content Optimization - Clarity Through Aggressive Cleaning (2025-10-11)**
   - **CORE PRINCIPLE**: Clarity improves discussion quality AND reduces token costs
   - **Query Cleaning Pipeline** (before sending to Tavily):
     - Unescape HTML entities in specialist queries
     - Normalize Unicode punctuation to ASCII equivalents
     - Tavily receives clean plain text for optimal search results
   - **Content Cleaning Pipeline** (from Tavily to specialists):
     - Decode HTML entities: `&quot;` → `"`, `&amp;` → `&`, `&#x27;` → `'`
     - Normalize Unicode: Smart quotes → straight quotes, em-dashes → hyphens
     - Remove broken markdown: `[](https:`, `[.webp)`, `[ [ [`, standalone brackets/parens, trailing `)`
     - Strip URLs: `https://...`, `www.example.com`, query params, UTM tracking codes
     - Remove media references: `.jpg`, `.webp`, `.pdf` file extensions
     - Discard pure junk: Content with only URL fragments/domains → "Content not available after cleaning web artifacts."
     - Check for readable prose: Content must have actual words, not just URL components
   - **Minimal XML Escaping**:
     - Attributes: Only `&`, `<`, `>`, `"` (not single quotes - we use double-quoted attributes)
     - Element content: Only `&`, `<`, `>` (quotes safe in content)
     - Result: Clean, readable XML without over-escaping
   - **Message Format Optimization**:
     - Removed redundant "Notice:" prefix (speaker "Search tool:" makes context clear)
     - Changed to: "Recent search results: <results>..."
     - Every saved token = lower costs + cleaner specialist context
   - **Implementation**: `axion_swarm/search.py`
     - `normalize_unicode_punctuation()`: ASCII conversion for better LLM/human clarity
     - `clean_search_content()`: Aggressive markdown/URL artifact removal
     - `escape_xml_attribute()` / `escape_xml_content()`: Minimal escaping for validity
   - **Benefits**:
     - Specialists see clean prose: "we'll know" instead of `we&#x27;ll know` or `[ [ [ page.example.com?utm=...`
     - Fewer tokens per search result (no junk content, no over-escaping)
     - Human-readable demos (no gross formatting artifacts)
     - Better discussion quality (specialists understand results clearly)

1. **Migrated to Tavily Search API - LLM-Optimized Search with XML Format (2025-10-11)**
   - **SEARCH ENHANCEMENT**: Replaced Google Custom Search with Tavily Search API, specifically designed for LLM applications
   - **Why Tavily**:
     - Purpose-built for LLM and RAG applications
     - Provides LLM-optimized content snippets from multiple sources
     - Includes relevance scoring for each result
     - Aggregates 20+ trusted sources per query
     - Returns structured, citation-ready results
     - Optional LLM-generated summaries
   - **New XML Format for Search Results**:
     ```
     Notice: search [query] returned
     <summary>LLM-generated answer</summary>
     <results>
     <result>
     <title>Source Title</title>
     <relevance>85%</relevance>
     <content>LLM-optimized content snippet</content>
     <url>https://source-url.com</url>
     </result>
     </results>
     ```
   - **Configuration Changes**:
     - Environment variable: `TAVILY_API_KEY` (replaces `GOOGLE_SEARCH_API_KEY` and `GOOGLE_SEARCH_CX`)
     - Optional: `TAVILY_MAX_RESULTS` (default: 5, max: 20)
     - Python dependency: `tavily-python` (pip install tavily-python)
   - **Files Modified**:
     - `axion_swarm/search.py`: Complete rewrite for Tavily API with XML formatting and proper escaping
     - `axion_swarm/config.py`: Updated configuration for Tavily (lines 277-286)
     - `axion_swarm/prompts.py`: Updated BASE_INSTRUCTION search tool documentation (lines 130-154)
     - `TAVILY_SEARCH_SETUP.md`: New setup guide created
     - `GOOGLE_SEARCH_SETUP.md`: Deprecated (can be removed)
   - **Documentation**: https://docs.tavily.com
   - **Rationale**: Tavily is specifically designed for LLM applications, providing cleaner, more relevant results than traditional search APIs. XML format provides structured, parseable search results consistent with the system's message format.

2. **Research Specialist - Fact-Checking Responsibility with Search Tool (2025-10-11)**
   - **ROLE ENHANCEMENT**: Research specialist now has explicit fact-checking responsibilities using the @[Search][...] tool
   - **New Responsibilities**:
     - Use @[Search][...] proactively to fact-check statements made by other specialists
     - Focus on verifying best practices mentioned in the discussion
     - Check for recent and up-to-date information that supports or contradicts specialist statements
     - Search when information may be outdated or incorrect
   - **When Search Results Conflict with Specialist Statements**:
     - @mention the specialist by name
     - Present the conflicting information from search results
     - Ask for clarification
     - Example: "@[Specialist Name specialist], regarding your statement about [topic], my search shows [conflicting information]. Can you clarify?"
   - **Priority Areas for Fact-Checking**:
     - Current versions, pricing, or availability
     - Best practices and industry standards
     - Recent policy or regulatory changes
     - Technical capabilities or limitations
   - **If Search Confirms Statements**: May note this for the room's confidence
   - **Files Modified**:
     - `axion_swarm/prompts.py`: Updated Research role description (lines 33-36) and `RESEARCH_SYSTEM_BASE` (lines 871-896) with detailed fact-checking guidance
   - **Rationale**: Research specialist is best positioned to verify factual claims and ensure discussion is grounded in accurate, current information. This creates a natural quality control mechanism where specialists can be fact-checked in real-time.

1. **Removed Temporal References & Self-Referential Language - Real-Time Conversation Clarity (2025-10-11)**
   - **PROMPT ENHANCEMENT**: Updated all agent prompts to explicitly prohibit temporal/timeline references, external work assignments, and self-referential AI/LLM terminology
   - **Problem**: Chair was asking specialists to "commit to completing [task] within 3 business days" - treating them as consultants with schedules
   - **Solution**: Added "CRITICAL - REAL-TIME CONVERSATION" sections to both `BASE_INSTRUCTION` (all specialists) and `CHAIR_SYSTEM_BASE` (Chair), plus removed all AI/LLM self-references
   - **New Guidance**:
     - This is a REAL-TIME discussion happening NOW within conversation phases
     - All contributions happen WITHIN THIS DISCUSSION ONLY
     - Specialists do not have schedules or timelines - they provide analysis IN THEIR RESPONSES
     - ❌ DO NOT commit to completing tasks "within X days/weeks" or reference timelines
     - ❌ DO NOT accept/assign work "outside" the conversation (no take-away assignments)
     - ❌ DO NOT say things like "I'll complete this by next week" or "within 3 business days"
     - ✅ DO provide full analysis, recommendations, and assessments IN YOUR RESPONSE (Chair: "in your next response")
     - All thinking and recommendations happen within conversation phases - there is no work outside this discussion
   - **Language Cleanup**:
     - Removed all "AI agent", "LLM instance", "token cost" self-referential terminology from `BASE_INSTRUCTION`
     - Changed "separate LLM instances" → "separate team members"
     - Changed "separate LLM INSTANCE" → "SEPARATE SPECIALIST" / "SEPARATE TEAM MEMBER with different visibility"
     - Made Tavily Search examples completely general (no technical specifics in base prompts)
   - **Files Modified**:
     - `axion_swarm/prompts.py`: Added sections to `BASE_INSTRUCTION` (line 107) and `CHAIR_SYSTEM_BASE` (line 782), plus removed self-referential language throughout
   - **Rationale**: Specialists and Chair need to understand they operate within a real-time conversation where all contributions happen in responses. No schedules, timelines, or external assignments. Kept language general, avoided self-referential AI terminology, and ensured technical language appears only in specialist-specific roles where justified.

3. **Enhanced Specialist Collaboration Guidance - Direct @Mentioning (2025-10-11)**
   - **COMMUNICATION ENHANCEMENT**: Updated specialist prompts to explicitly encourage direct collaboration via @mentions
   - **New Guidance** (`prompts.py` - `BASE_INSTRUCTION`):
     - Added "COLLABORATING WITH OTHER SPECIALISTS - ASK QUESTIONS DIRECTLY" section
     - Specialists can @mention ANY specialist from the full roster (both "in" the room and "available")
     - Pattern: `"@[Specialist Name], [your question about their domain]?"`
     - Examples provided: Backend Engineer for API questions, Database Architect for schema questions, Research for sources
   - **Key Clarification**:
     - **For specialists "in" the room**: They will see the @mention and can respond directly in the next phase
     - **For "available" specialists**: Specialists can @mention them, but Chair decides whether to bring them in
     - Chair has final authority on bringing "available" specialists into active participation
     - Specialists can also explicitly request: `"@[Chair], please bring in @[Specialist Name] to help with [reason]."`
   - **Purpose**: Ensures right expertise addresses each aspect of User's concerns through active collaboration
   - **Distinction**:
     - **Direct collaboration** (NEW emphasis): Actively asking questions of any specialist (in room or available)
     - **Chair's authority** (maintained): Chair decides whether to bring "available" specialists into active participation
     - **Requesting via Chair** (existing): Explicit pattern for requesting specialists be brought in
     - **Deferring** (existing): Stepping back from a topic outside your domain
   - **Documentation** (`ARCHITECTURE.md`):
     - Added "Direct Specialist-to-Specialist Collaboration" section before "Bringing Specialists Into the Room"
     - Clear examples and patterns for @mentioning both "in" and "available" specialists
     - Emphasizes Chair's authority for bringing "available" specialists into the room
   - **Benefits**:
     - More effective cross-domain problem solving
     - Specialists leverage each other's expertise to provide better answers to User
     - Natural conversation flow with specialists building on each other's knowledge
     - Flexibility to @mention any specialist while preserving Chair's governance role
     - Clearer distinction between collaboration (active) and deferral (passive)
   - **Expected Impact**: Higher quality answers as specialists actively seek expertise from each other, more natural collaborative discussion, Chair maintains control over room composition

3. **Chair's Stagnation Detection - Automated Final Phase Trigger (2025-10-11)**
   - **FEATURE**: Chair now automatically detects discussion stagnation in Phase 4+ and can trigger early move to Final Phase
   - **Two Paths to Final Phase**:
     - **Path 1 - Convergence**: All specialists explicitly pass (existing behavior, natural agreement)
     - **Path 2 - Stagnation**: Chair detects lack of progress between phases (NEW behavior, coordinator-initiated)
   - **How It Works**:
     - After Chair generates normal synthesis in Phase 4+, system invokes Chair a second time
     - Chair compares previous synthesis (Phase N-1) vs current synthesis (Phase N) relative to User's concerns
     - Prompt provides: All User messages, previous synthesis, current synthesis
     - Chair responds with `<stagnated>yes</stagnated>` or `<stagnated>no</stagnated>`
     - If yes: Sets `final_phase_needed=True` and adds Notice to conversation
     - If no: Discussion continues normally to next phase
   - **Implementation**:
     - `check_discussion_stagnation()` in `agents.py`: Performs stagnation analysis via second Chair LLM call
     - XML prompt structure with `<user_concerns>`, `<previous_synthesis>`, `<current_synthesis>` sections
     - **All messages use consistent `<message>` XML format**: User messages, Chair previous synthesis, and Chair current synthesis all wrapped in `<message><from>...</from><timestamp_iso>...</timestamp_iso><phase>...</phase><content>...</content></message>`
     - XML parsing for `<stagnated>yes/no</stagnated>` response with plain text fallback
     - Error handling: If check fails, discussion continues without detection (non-blocking)
     - Notice message: "Based on discussion stagnation analysis, we are moving to the final round..."
   - **Console Output** (stderr):
     ```
     [CHAIR] Running stagnation analysis for Phase 4...
     [CHAIR] Stagnation analysis result: STAGNATED (moving to final round)
     [CHAIR] Stagnation detected in Phase 4 - moving to final round
     ```
   - **Console Output** (stdout):
     ```
     [timestamp] Notice: Based on discussion stagnation analysis, we are moving to the final round. 
     All specialists, please provide your concluding assessment.
     ```
   - **Benefits**:
     - Prevents lengthy discussions that aren't making progress (saves time and tokens)
     - Chair (coordinator) best positioned to assess synthesis evolution
     - Conservative: only triggers when Chair explicitly identifies stagnation
     - Maintains discussion quality by concluding when appropriate
     - User still gets comprehensive final round with all specialist input
   - **Design Rationale**:
     - Comparing syntheses (not individual messages) focuses on big-picture progress
     - Phase 4+ requirement ensures discussion has matured (Phase 1-2-3 for exploration)
     - Distinct from convergence - stagnation is Chair-detected, convergence is specialist-driven
     - Non-blocking error handling prevents stagnation check from disrupting discussion
   - **Documentation**:
     - Added "Chair's Stagnation Detection (Phase 4+)" section to ARCHITECTURE.md
     - Updated "Triggering Conditions" for Final Phase to show both paths
     - Documented console output behavior on stdout and stderr
   - **Expected Impact**: Discussions conclude more efficiently when plateauing, improving user experience without losing any final round coverage

2. **Conceptual Clarification: Chair vs Specialists - Role Nomenclature (2025-10-10)**
   - **CONCEPTUAL FRAMEWORK**: Clarified that Chair and User are special fixed roles, distinct from specialists
   - **Roles**:
     - **Special Roles** (singular, fixed, non-configurable): `@[User]`, `@[Chair]`
     - **Specialists** (multiple, configurable): `@[Context specialist]`, `@[Research specialist]`, etc.
     - **Core Team** (specialists who start "in" and never auto-dismiss)
     - **Available** (specialists who can be brought in by Chair)
   - **Nomenclature Change**: `@[Chair specialist]` → `@[Chair]`
     - Chair is a coordinator/facilitator, not a specialist with domain expertise
     - Specialists provide domain expertise; Chair synthesizes and coordinates
   - **Implementation** (comprehensive update across all files):
     - **Code files**: `agents.py`, `prompts.py`, `main.py`, `config.py` - all references updated
     - **Documentation**: `ARCHITECTURE.md`, `AZURE_OPENAI_IMPLEMENTATION.md`, `NEW_SPECIALISTS_SUMMARY.md`
   - **Generalization of Examples**:
     - All prompt examples now use generic placeholder names (e.g., `@[Specialist Name specialist]`)
     - Removed specific role names (Database Architect, Product Manager, etc.) from examples
     - Removed specific test scenarios (MVP, team hiring, schema design) from examples
     - **Purpose**: System is general-purpose with clear governance; examples should not bias toward specific domains
   - **Benefits**:
     - Clearer conceptual model: Chair coordinates, specialists contribute expertise
     - Consistent with governance structure: User requests, Chair facilitates, specialists provide domain knowledge
     - Examples remain general and applicable to any domain
   - **User Feedback**: "Chair is not a specialist, if we go through the entire project and agree that 'specialist' means a project-configurable persona"; "ensure none of our prompt examples are specific to individual roles (except User or Chair)"

3. **Simplified Chair Invitation Pattern (2025-10-10)**
   - **FEATURE**: Chair brings specialists into the room simply by @mentioning them
   - **How it works**: Any @mention of an available specialist by Chair automatically brings them in for the next phase
     - Example: Chair says `"@[Specialist Name specialist], can you help with [question]?"`
     - System detects the @mention and changes specialist from "available" → "in"
     - Specialist participates starting next phase
     - Notice message informs everyone of room composition change
   - **Implementation**:
     - Detection logic (`detect_specialist_additions()` in `agents.py`) scans Chair's response for any @mentions of available specialists
     - Updated all prompts and documentation to reflect @mention pattern
   - **Benefits**:
     - Natural: @mentioning someone means "I want to talk to you"
     - Simple: No special format to remember
     - Direct: One action (mention) does everything
   - **User Feedback**: "if chair mentions any specialists not in the room, consider that an implicit add"

4. **User Control - Phase Progression Prompt (2025-10-10, Updated 2025-10-11)**
   - **FEATURE**: Added user prompt to control phase progression in iterative phases only
   - **Implementation** (`main.py`):
     - After Phase 3+ checkpoint save, prompt user: `⏸️  Press ENTER to continue to next phase (or Ctrl+C to stop):`
     - **Phase 1-2**: Auto-continues without prompt (mandatory assessment phases)
     - **Phase 3+**: Shows prompt (iterative discussion phases where user may want to review)
     - **Final Phase**: Auto-continues without prompt (conclusion phase)
     - User must press ENTER before proceeding to next phase (when prompted)
     - Ctrl+C allows clean exit with message: "🛑 Discussion stopped by user."
     - Checkpoint already saved before prompt, so stopping is safe and resumable
   - **Benefits**:
     - Phase 1-2 flow quickly without interruption (mandatory phases)
     - User control during iterative discussion (Phase 3+) when decisions are most relevant
     - Final Phase flows to completion without interruption
     - Time to review specialist responses during iterative phases
     - Clean stop capability at iterative phase boundaries
     - Safe resume point (checkpoint saved before prompt)
   - **Documentation** (`ARCHITECTURE.md`):
     - Added "User Control" section to Graph Workflow with phase-specific behavior
     - Updated save_checkpoint node description
   - **Expected Impact**: Gives user control where it matters (iterative phases) while maintaining flow during mandatory and conclusion phases

2. **Specialist Room Presence - Dynamic Team Composition with Auto-Dismissal & Reflection Period (2025-10-10)**
   - **FEATURE**: Added ability to control which specialists actively participate in discussions versus those available to be brought in on-demand, with automatic dismissal and reflection period
   - **Concept**: Specialists exist in two states:
     - **"in"**: Actively participating in phase rotations (speak each phase)
     - **"available"**: Can be brought into the room by Chair when needed
   - **Implementation**:
     - **State Management** (`state.py`): Added `specialist_presence: dict[str, str]` to `OverallState`
     - **Configuration** (`config.py`):
       - `DEFAULT_CORE_TEAM = ["context", "research", "skeptic", "ethicist"]`
       - `get_core_team()`: Supports `CORE_TEAM` environment variable override
       - `initialize_specialist_presence()`: Sets up initial "in"/"available" mapping
     - **Core Logic** (`agents.py`):
       - `get_active_specialists()`: Filters specialists currently "in" the room
       - `get_available_specialists()`: Returns specialists available to join
       - `detect_specialist_additions()`: Parses Chair's response for bring-in requests
       - `chair_agent()`: Updates `specialist_presence` when Chair brings specialists in
       - `start_phase()`: Uses only active specialists for `agents_remaining`
       - `execute_phase_parallel()`: Propagates `specialist_presence` updates to state (CRITICAL: without this, newly added specialists won't appear in next phase)
       - `auto_dismiss_non_core_specialists()`: Auto-dismisses non-core specialists after they respond (keeps discussions focused)
     - **Prompts** (`prompts.py`):
       - `ROOM_PRESENCE_SECTION`: Added to `BASE_INSTRUCTION` for all specialists
       - `MANAGING_ROOM_COMPOSITION`: Added to `CHAIR_SYSTEM_BASE`
       - Updated prompts to guide gradual context building (one item per contribution)
       - Removed specific conversational examples, replaced with generic placeholders
     - **Display** (`main.py`):
       - `display_initial_room_composition()`: Shows core team and available specialists at startup
     - **Checkpoints** (`checkpoint.py`):
       - `compute_config_checksum()`: Includes `DEFAULT_CORE_TEAM` for validation
  - **Request Pattern**: Any "in" specialist can request: `"@[Chair], please bring in @[Specialist Name specialist] to help with [reason]."`
  - **Chair Pattern**: Chair @mentions available specialists to bring them in:
    - Example: `"@[Specialist Name specialist], can you help with [question]?"` → specialist joins next phase
    - Any @mention of an available specialist by Chair automatically brings them into the room
  - **Notice Messages**: 
    - When specialists brought in: `"Notice: [Names] have been brought in and will participate starting next phase. Current team: [list]"` (appears immediately after Chair's @mention to show causal relationship, but specialist participates next phase)
    - When specialists self-dismiss: `"Notice: [Names] have self-dismissed from the discussion and are now available to be brought back in if needed."`
    - When available specialists are @mentioned (to Chair): `"Notice: @[Chair], the following available specialists were @mentioned in this phase: [names]. Consider whether to bring them in based on discussion needs."`
   - **Auto-Dismissal**: Non-core team specialists participate for ONLY ONE PHASE after being brought in, then automatically return to "available" status. Chair must allow at least one full phase for core team to reflect on the specialist's contribution before re-inviting them.
   - **Benefits**:
     - Focused discussions with smaller initial team
     - Cost efficiency (fewer LLM calls - specialists only participate when needed)
     - Dynamic expansion as topic evolves, automatic contraction when done
     - Natural meeting flow where people join as needed, then return to other work
     - Prevents discussion bloat from accumulating specialists
   - **Bug Fixes During Implementation**:
     1. **Phase 3 Bug**: `execute_phase_parallel()` wasn't using `state["agents_remaining"]` (was using full `AGENT_ROSTER`), causing inactive specialists to respond
     2. **Phase 4 Bug**: `execute_phase_parallel()` wasn't propagating `specialist_presence` updates from `chair_result`, causing newly added specialists to not appear in next phase
     3. **UserWarning**: `reasoning_effort` was in `model_kwargs` instead of direct parameter to `AzureChatOpenAI`
   - **Expected Impact**: Enables flexible team composition that adapts to discussion needs, reducing noise and cost while maintaining full specialist awareness

2. **GPT-5 Native Reasoning Support (2025-10-10)**
   - **FEATURE**: Added support for GPT-5/o1 native reasoning tokens alongside existing `<think>` tag system
   - **Implementation** (`agents.py` lines 1091-1111, 1139-1142, 1152-1172):
     - Extract `reasoning_content` from `response.response_metadata['reasoning']` or `response.response_metadata['reasoning_content']`
     - Extract `reasoning_tokens` count from `response.response_metadata['usage']['reasoning_tokens']`
     - Display reasoning as `<reasoning>...</reasoning>` in dark green on stderr (same formatting as `<think>` blocks)
     - Track reasoning tokens separately: `INPUT + REASONING + OUTPUT = TOTAL`
     - Reasoning content automatically excluded from public response (just like `<think>` blocks)
   - **Backward Compatibility**:
     - Both systems work simultaneously (GPT-5 native reasoning + explicit `<think>` tags)
     - Non-GPT-5 models continue using `<think>` tags unchanged
     - If both exist, both are displayed (rare edge case)
   - **Documentation** (`ARCHITECTURE.md`):
     - New section: "Internal Reasoning & Thinking" explaining dual system
     - Updated key differentiators to mention both reasoning methods
     - Updated STDERR section to document `<reasoning>` display format
     - Updated debug output section to include REASONING TOKENS in token summary
   - **Expected Impact**: Seamless support for GPT-5's native chain-of-thought reasoning while maintaining full compatibility with existing models

3. **Stdout Flushing for Immediate Message Display (2025-10-10)**
   - **BUGFIX**: Added explicit `flush=True` to all stdout message prints to ensure immediate display
   - **Problem**: stdout is buffered by default, causing specialist chat messages to be delayed while stderr output (think blocks, Chair status) appeared immediately
   - **User Impact**: User would see phase start notice → think blocks → Chair status, but NOT the actual specialist chat messages (they appeared later due to buffering)
   - **Solution** (`main.py` lines 229, 233, 241, 278):
     - Added `flush=True` parameter to all `print()` statements for:
       - Notice messages
       - User messages  
       - Specialist chat messages
     - Also fixed timestamp retrieval to use stored timestamps from `additional_kwargs` instead of regenerating (lines 222-225, 237-241, 245-249)
   - **Expected Impact**: All messages appear immediately on stdout without buffering delays, providing real-time visibility into specialist responses

4. **Rate Limit Notice Deduplication - Thread-Safe (2025-10-10)**
   - **BUGFIX**: Eliminated duplicate "taking a break" and "we're back" notices when multiple agents hit rate limits simultaneously
   - **Problem**: In parallel execution, multiple specialists hitting rate limits would each issue their own Notice messages, creating duplicates
   - **Solution**: Added atomic tracking flags with mutex protection:
     - `_rate_limit_break_notice_issued`: Tracks if "taking a break" notice already issued for current wait period
     - `_rate_limit_back_notice_issued`: Tracks if "we're back" notice already issued for current wait period
     - All accesses protected by `_rate_limit_lock` using atomic check-and-set pattern
   - **Implementation** (`agents.py` lines 48-49, 75-101, 984-997, 1039-1053):
     - In `set_rate_limit()`: Only reset notice flags if NOT already in a wait state
     - In "break" notice logic: Atomic check-and-set - first agent to acquire lock issues notice, others skip
     - In "back" notice logic: Atomic check-and-set after wait completes - first agent issues notice, others skip
     - Pattern: Claim right to issue notice inside lock, issue outside lock (reduces contention)
   - **Thread Safety**: All operations use proper mutex locking
     - Read shared state inside lock, snapshot values
     - Atomic check-and-set pattern prevents race conditions
     - Wait operations happen outside lock to allow other threads to proceed
     - Documentation added with "THREAD-SAFE" comments at all critical sections
   - **Expected Impact**: Only ONE "taking a break" and ONE "we're back" notice per rate limit event, regardless of how many agents hit it simultaneously

5. **Enhanced Passing Requirements + No Public Convergence Commentary (2025-10-10)**
   - **IMPROVEMENT**: Strengthened requirements for specialists to pass when they have nothing new to add (Phase 3+)
   - **IMPROVEMENT**: Explicitly forbid public mentions of convergence, consensus, or discussion state
   - **IMPROVEMENT**: Specialists now explicitly instructed to USE phase numbers and timestamps for passing decisions
   - **IMPROVEMENT**: Chair now uses neutral questions instead of signaling alignment
   - **Core Principle**: Progressive retraction - as phases increase (3→4→5→6+), specialists MUST be increasingly selective and MORE likely to pass
   - **Key Changes**:
     1. **Passing is REQUIRED, not optional** (`prompts.py` lines 411-424, `agents.py` lines 855-864):
        - Phase 3+: Specialists MUST pass if they have nothing NEW to add toward User's explicit concern
        - Changed language from "should" to "MUST" and "REQUIRED" throughout
        - Clarified: Even extensive thinking that concludes "nothing new" → MUST still pass
        - Passing signals healthy implicit consensus (never stated publicly)
     2. **Private Convergence Assessment ONLY** (`prompts.py` lines 398-401, 418-420, 622-626):
        - ❌ ABSOLUTELY FORBIDDEN: Publicly mention "convergence", "consensus", "agreement", "settling", "winding down", or meta-commentary about discussion state
        - ✅ CORRECT: Privately observe patterns in `<think>` tags, assess independently whether YOU have new value
        - Simply pass with "I have no further comments at this time" - passing speaks for itself
     3. **Updated Thinking Process** (`agents.py` lines 807-842):
        - Step 12: Changed from "emerging consensus" → "Are others agreeing on approaches"
        - Step 13: "PRIVATE OBSERVATION" - note passing patterns but NEVER mention publicly
        - Step 18: "regardless of what others are doing" instead of "regardless of consensus"
     4. **Self-Assessment Requirements** (`prompts.py` lines 487-493):
        - Changed "I should PASS" → "I MUST PASS" for redundancy/tangents/circular discussions
        - Added "🎯 CRITICAL - Progressive Retraction" as REQUIRED behavior, not optional
     5. **Phase and Timestamp Awareness** (`prompts.py` lines 158-162, 424, 427, 493; `agents.py` lines 812-815, 840-841):
        - Added explicit section: "🎯 USE PHASE AND TIMESTAMP DATA FOR PASSING DECISIONS"
        - Specialists instructed to look at `<phase>` tags to identify current phase number
        - Specialists instructed to count messages per phase to detect declining contributions
        - Specialists instructed to look at `<timestamp_iso>` tags to observe timing patterns
        - Added 4 new thinking steps (5-8, 33) specifically for phase/timestamp analysis:
          - Step 5: Identify current phase number from Notice messages and <phase> tags
          - Step 6: Count messages per phase to detect if specialists are contributing less
          - Step 7: Analyze timestamps for timing patterns and gaps (indicates passing)
          - Step 8: Self-assess selectivity based on phase number (higher = more selective)
          - Step 33: Final passing calibration considering phase + timing + value
        - Guidance: "Higher phase numbers + fewer recent contributions = stronger signal to pass"
     6. **Chair Synthesis Guidance - Neutral Questions & No Task Execution** (`prompts.py` lines 25-27, 562-596, 620-627):
        - **Updated role description** (lines 25-27): "guide the panel toward consensus" → "maintain order and focus"
        - Changed "areas of agreement or disagreement" → "different perspectives raised (without declaring agreement/alignment)"
        - **NEW REQUIREMENT**: Chair must END synthesis with neutral question instead of signaling convergence
          - Phase 2-3: "Specialists, do you have any further critical concerns?"
          - Later phases: "Specialists, any additional insights before we finalize?"
        - ❌ FORBIDDEN for Chair: "the room is aligned", "we agree on", "consensus on one path", "everyone supports"
        - ✅ CORRECT: Simply summarize what was said, then ask if there are further concerns
        - **NEW CRITICAL RESTRICTION**: Chair must NOT offer to perform tasks (lines 568-573)
          - ❌ FORBIDDEN: "before I draft those job descriptions", "I'll create that plan", "I can write those docs"
          - ✅ CORRECT: Suggest specialists who can help: "@[HR], could you draft job descriptions?"
          - **Chair role is facilitation, not execution** - all actual work done by other specialists
        - Changed "Propose small, reversible next steps when appropriate" → "Suggest which specialists might address remaining gaps" (line 589)
        - Final Phase note: Can mention "finalized recommendations" or "group's best answer" but avoid "consensus"/"alignment"
        - **Rationale**: Prevents Chair from biasing specialists by declaring convergence; maintains independent assessment; ensures Chair stays in coordination role
   - **Rationale**: 
     - Each specialist decides independently when to pass - no public declarations that could bias others
     - Prevents groupthink and premature convergence signals
     - Natural discussion wind-down happens organically through independent passing decisions
     - Maintains system observability (console logs show thinking) while preventing bias
   - **Expected Impact**: 
     - More natural convergence without explicit coordination
     - Fewer unnecessary contributions in later phases
     - Cleaner, more focused discussions as phases progress
     - Specialists think independently rather than reacting to perceived group dynamics

6. **UnboundLocalError Fix - Config Variable (2025-10-10)**
   - **BUGFIX**: Fixed `UnboundLocalError: cannot access local variable 'config' where it is not associated with a value`
   - **Problem**: In `create_agent_func()`, the code tried to access `config.show_message_debug` at line 394 before `config` was defined
   - **Root Cause**: Added conditional checks for `config.show_message_debug` without first calling `config = get_config()`
   - **Solution**: 
     - Added `config = get_config()` at the start of the `agent` function (line 293)
     - Removed duplicate `config = get_config()` calls later in the same function (lines 552, 765, 897)
   - **Impact**: System now works correctly with `SHOW_MESSAGE_DEBUG` environment variable

7. **On-Topic Enforcement Enhancement - Specialist Defense Option (2025-10-10)**
   - **IMPROVEMENT**: Added ability for specialists to defend relevance when Chair redirects them for being off-topic
   - **Previous Behavior**: Specialists MUST comply immediately when Chair calls them out for being off-topic
   - **New Behavior**: Specialists now have TWO options when redirected:
     1. **Comply**: Acknowledge and refocus immediately (if they agree topic was off-topic)
     2. **Defend**: Explain WHY the topic is pertinent with specific justification (if they believe it's relevant to User's explicit concern)
   - **Implementation**:
     - Updated `CHAIR'S ON-TOPIC ENFORCEMENT` in `prompts.py` (line 431-445) to document both options
     - Updated Chair's `ON-TOPIC ENFORCEMENT` section (line 569-581) to acknowledge specialist justifications
     - Chair must note in synthesis: either "redirected [Specialist]" or "noted [Specialist]'s justification for [topic]'s relevance"
   - **Example Defense**: `"@[Chair], I believe [topic] is pertinent because [specific reason how it helps answer User's explicit concern]. [Continue with contribution]."`
   - **Benefits**:
     - Prevents Chair from being too heavy-handed and accidentally suppressing useful information
     - Creates healthy dynamic where specialists can justify genuinely pertinent topics
     - Maintains on-topic discipline while allowing justified technical depth
     - Encourages specialists to think critically about relevance rather than blind compliance
   - **Expected Impact**: More nuanced on-topic enforcement that respects specialist expertise while preventing tangents

8. **Prompt Consistency Fix - "Think Deeply, Write Concisely" (2025-10-10)**
   - **IMPROVEMENT**: Eliminated contradictions in prompts regarding response length
   - **Core Principle**: Specialists should think deeply (in `<think>` tags) but write concisely (in responses)
   - **Issue Found**: Several prompts used "comprehensive" which implied lengthy responses, contradicting BASE_INSTRUCTION's conciseness guidance
   - **Changes Made**:
     1. **Chair Final Phase** (`agents.py` line 330): Changed "COMPREHENSIVE SUMMARY" → "COMPLETE but CONCISE synthesis covering all key points"
     2. **Technical Writer Role** (`prompts.py` line 82): Changed "create clear, comprehensive documentation" → "provide guidance on documentation needs" (since they're advising in chat, not writing full docs)
     3. **Chair Phase 2** (`prompts.py` line 553): Changed "Be comprehensive" → "Be complete but concise - Cover all key points briefly"
     4. **Chair Compression Task** (`prompts.py` line 926): Changed "comprehensive summary" → "complete but concise summary" and "thorough summary" → "thorough yet brief summary"
   - **Rationale**: "Comprehensive" suggests both thoroughness AND length. "Complete but concise" emphasizes covering all key points (thoroughness) while staying brief (conciseness).
   - **Expected Impact**: More consistent specialist behavior - deep thinking combined with focused, brief responses that respect user's time

9. **Timestamp Fix + Message Debug Output Control (2025-10-10)**
   - **BUGFIX**: Timestamps now correctly captured at message creation time, not display time
   - **Implementation**: All messages store timestamp in `additional_kwargs["timestamp"]` when created
   - **Locations**: 
     - Line 1089 (`agents.py`): Specialist message timestamp captured at creation
     - Line 1415 (`agents.py`): Notice message timestamp captured at creation
     - Line 1436 (`agents.py`): User message timestamp captured at creation
   - **Display**: Timestamps retrieved from stored metadata using `msg.additional_kwargs.get("timestamp", ...)` with backwards-compatible fallback
   - **Benefit**: Same message shows same timestamp to all agents (consistent temporal context)
   - **NEW FEATURE**: Added `SHOW_MESSAGE_DEBUG` environment variable (default: `false`)
   - **Purpose**: Hide raw red/yellow XML message debug output and agent execution summaries by default
   - **When disabled** (default):
     - Only shows per-agent thinking blocks (dark green `<think>` tags) on stderr
     - Agent execution summary boxes (AGENT, PHASE, INPUT TOKENS, etc.) are hidden
     - Raw XML message visibility debug completely hidden
     - Human-readable conversation still appears on stdout (unchanged)
   - **When enabled** (`SHOW_MESSAGE_DEBUG=true`):
     - Shows detailed message visibility debug (VISIBLE/FILTERED indicators)
     - Shows raw XML message objects in red (filtered) and yellow (visible)
     - Shows agent execution summary boxes with token counts, phase info, and utilization percentages
     - Useful for debugging message filtering logic and performance analysis
   - **Configuration**: Set `SHOW_MESSAGE_DEBUG=true` in environment or `.env` file
   - **Implementation**: 
     - Conditional population of `debug_output_buffer` in `agents.py` based on `config.show_message_debug`
     - Agent execution summary boxes (lines 1054-1070 in `agents.py`) wrapped in `if config.show_message_debug:`
   - **Expected Impact**: Cleaner stderr output by default (only thinking blocks), detailed debug available when needed, consistent timestamps across all agents

0. **Chair Conditional Participation - Synthesis-Only Role (2025-10-08)**
   - **ARCHITECTURAL IMPROVEMENT**: Chair now only participates when specialist responses exist to synthesize
   - **Conditional Logic**: Chair checks for visible specialist responses before invoking LLM
   - **Phase 1 Behavior**: Chair **skips Phase 1 silently** - no specialist responses exist yet (specialists execute sequentially, Chair would go last and see none)
   - **Phase 2+ Behavior**: Chair **participates** - specialist responses from Phase 1+ are visible and can be synthesized
   - **Final Phase Behavior**: Chair **always participates** - mandatory contributions guarantee specialist responses exist
   - **Rationale**: 
     - Chair's core functions are **synthesis, coordination, likelihood assessment, and conflict resolution**
     - **All Chair functions require specialist responses to exist first**
     - Phase 1 has no discussion to synthesize (specialists haven't all responded yet)
     - **Conflicts are IMPOSSIBLE in Phase 1** - specialists are completely isolated, see only User message, have no awareness of each other
     - Chair will see ALL Phase 1 responses in Phase 2 when all Chair functions become actionable
     - Saves ~6-8 seconds per conversation with no information loss
   - **Implementation**: Added conditional check in `chair_agent()` function counting visible specialist messages
   - **Logging**: stderr messages indicate when Chair skips vs. participates with specialist count
   - **Benefits**:
     - Chair only speaks when they can perform their actual role (synthesis)
     - Efficiency gain (1 fewer LLM call per conversation)
     - Clearer conceptual model (Phase 1 = domain specialists only, Phase 2+ = Chair coordinates)
     - No functionality loss (Chair sees all Phase 1 in Phase 2 anyway)
   - **Expected Impact**: Faster Phase 1 execution, clearer role separation, Chair always has synthesis material when participating

0. **Deferring to Other Specialists + Strengthened @Mention Guidance (2025-10-08)**
   - **COMMUNICATION IMPROVEMENT**: Added explicit guidance for specialists to defer when topics are outside their domain
   - **Deferral Patterns**:
     - General deferral: "I defer to other specialists on [topic]." (no @mention - speaking to room)
     - Specific deferral: "I defer to @[Specialist name] on [topic]." (MUST use @[...] brackets when naming specific specialist)
   - **Purpose**: 
     - Makes it clear specialist is intentionally staying in their lane
     - Different from passing (specialist may still have contributions in other areas)
     - Helps direct conversation flow to appropriate experts
   - **Strengthened @Mention Requirement**: 
     - **CRITICAL**: ALWAYS use @[...] brackets when mentioning any specialist by name
     - Not just for questions - also for deferrals, references, and building on others' points
     - Examples: ✅ "@[Other Specialist] suggested..." ❌ "Other Specialist suggested..."
     - Ensures mentions are highlighted (User in blue, specialists in purple) for easy scanning
   - **Benefits**:
     - Clear signal of domain boundaries
     - Consistent @mention formatting enables visual highlighting
     - Helps route discussions to appropriate specialists
     - More transparent than simply not commenting
     - Maintains engagement while respecting expertise boundaries
   - **Expected Impact**: Clearer domain boundaries, better collaboration, more explicit knowledge routing, consistent formatting

0. **Message Structure Refinement - "Speaking to the Room" (2025-10-08)**
   - **COMMUNICATION IMPROVEMENT**: Clarified that specialists are always speaking to the entire room by default
   - **Key Principle**: User is present and listening - no need to address them specifically unless asking a question
   - **@Mention Usage**: 
     - Use `@[User]` ONLY when asking a clarifying question
     - Use `@[Specialist name]` ONLY when asking another specialist a question
     - Provide analysis/insights/recommendations without @mentions (everyone is listening)
   - **Message Structure**: Analysis first, questions at end
     - Start with observations, recommendations, insights (no @mentions)
     - End with targeted questions if needed (with @mentions)
   - **Updated Prompts**: 
     - All phase guidance updated to emphasize "speak to room" default
     - Examples made more general (not technology-specific)
     - Good/bad examples updated to show proper @mention usage
   - **Benefits**:
     - More natural conversation flow (like a meeting room)
     - Reduces unnecessary @mentions cluttering the discussion
     - Clear signal when someone needs specific information
     - Value-first communication (substance before questions)
   - **Expected Impact**: Cleaner conversation flow, more professional tone, easier to read transcripts

0. **@Mention Highlighting in Output (2025-10-08)**
   - **VISUAL ENHANCEMENT**: Added color-coded highlighting for @mentions in stdout conversation display
   - **User Mentions**: `@[User]` appears in light blue for easy identification of questions/clarifications to User
   - **Specialist Mentions**: `@[Specialist name]` appears in light purple for easy identification of inter-specialist communication
   - **Base Text**: All other conversation text remains in light green
   - **Implementation**: 
     - Added `LIGHT_BLUE` and `LIGHT_PURPLE` ANSI color codes to `colors.py`
     - Created `highlight_mentions()` function using regex to find all `@[...]` patterns
     - Applied highlighting to Notice, User, and Specialist message displays in `main.py`
   - **Benefits**:
     - Easier to visually scan who is being addressed in multi-party conversations
     - Clear distinction between User questions and specialist discussions
     - Improved readability of complex cross-referenced discussions
   - **Expected Impact**: Better user experience when reading conversation output, easier to follow discussion flow

0. **Accurate Token Counting with tiktoken (2025-10-08)**
   - **INFRASTRUCTURE IMPROVEMENT**: Replaced character-based approximation with accurate token counting
   - **Token Counter**: Using `tiktoken` library with `cl100k_base` encoding (GPT-3.5/4 standard)
   - **Functionality**: 
     - Created `count_tokens_in_messages()` function to count tokens in all messages being sent to LLM
     - Counts SystemMessage (prompts) + HumanMessages (history/instructions) accurately
     - Fallback to 4-chars-per-token approximation if tiktoken unavailable
   - **Display Update**: INPUT_CONTEXT debug header now shows exact token count instead of character approximation
   - **Added Dependency**: `tiktoken>=0.5.0` added to `pyproject.toml`
   - **Benefits**:
     - Accurate context window tracking for model limitations
     - Better understanding of prompt size for optimization
     - Reliable token counting for cost estimation
   - **Expected Impact**: More accurate context tracking, easier debugging of long conversations

0. **Atomic Phases + Phase 3 Removal + Chair Special Visibility (2025-10-08)**
   - **MAJOR ARCHITECTURAL SIMPLIFICATION**: Removed redundant Phase 3, consolidated to 4-stage system (was 5-stage)
   - **Atomic Phases**: Specialists now ONLY see messages from PRIOR completed phases, NOT current phase they're in
   - **Chair Exception**: Chair goes LAST in each phase and CAN see current phase messages (to synthesize what others just said)
   - **Phase Consolidation**: Old Phase 4+ becomes new Phase 3+ (progressive retraction phase)
   - **Compression Update**: History compression now happens after Phase 2 (Chair's Phase 2 synthesis), not Phase 3
   - **Filtering Logic**: 
     - Non-Chair: `msg_phase < current_phase` (only prior phases visible)
     - Chair: All phases visible including current (goes last)
     - User & Notice: Always visible (never filtered)
   - **Benefits**:
     - **Prevents premature responses**: Can't react to incomplete current-phase discussions
     - **Enables Chair synthesis**: Chair sees complete current phase to synthesize
     - **Reduces redundancy**: Phase 2 and old Phase 3 were nearly identical, now just Phase 2
     - **Token savings**: Current phase filtering reduces context size for non-Chair specialists
     - **Cleaner architecture**: More logical progression (independent → cross-pollinate → iterate)
   - **Mandatory Phases**: Phase 1-2 mandatory (cannot pass), Phase 3+ optional (can pass)
   - **Updated Throughout**: All prompts, documentation, and logic updated to reflect atomic phase filtering
   - **Expected Impact**: More atomic discussion phases, better Chair synthesis, token savings, clearer progression

1. **Role Description System - Dual Perspective Refactor + Clarification Guidance (2025-10-08)**
   - **ARCHITECTURAL IMPROVEMENT**: Refactored role descriptions into nested data structure with first-person and third-person perspectives
   - **Data Structure**: `ROLE_DESCRIPTIONS` now contains `{"first_person": "You...", "third_person": "Does..."}` for each specialist
   - **First-Person Usage**: Injected into specialist's own prompt right after "You are [Name]." for self-identity
   - **Third-Person Usage**: Compiled into specialist roster visible to all OTHER specialists in BASE_INSTRUCTION
   - **Dynamic Roster**: `generate_specialist_roster(exclude_role_key)` creates customized roster per specialist
   - **Single Source of Truth**: Both perspectives maintained together, stay in sync, easy to update
   - **Role Clarity**: Removed technical wording from non-technical specialist roles to ensure appropriate language per role type
   - **Display Updates**: Startup prompt display now shows role descriptions in correct position (after "You are [Name].")
   - **Full Roster Display**: BASE_INSTRUCTION display now shows complete roster using real `generate_specialist_roster()` function
   - **Transparency When Unable to Answer**: Added guidance that when specialists cannot answer User's explicit concerns but aren't passing, they should concisely specify what information would be needed to answer, **if it's within their role to answer at all**. Specialists must first assess if the question is within their expertise - if not, they should pass instead.
   - **Benefits**: 
     - Self-awareness: Each specialist knows "who I am"
     - Group-awareness: Each specialist knows "who others are" and what expertise to leverage
     - Maintainability: Update one structure to change role presentation everywhere
     - Consistency: No duplicate hardcoded descriptions
     - Scalability: Easy to add/modify specialist roles independently
     - Clarity: Users understand what specific information would unlock fuller answers
   - **Expected Impact**: Clearer role identity, better collaboration between specialists, easier maintenance, more actionable partial answers

1. **Phase Metadata Tagging System + Pass→Phase Terminology (2025-10-08)**
   - **MAJOR ARCHITECTURAL IMPROVEMENT**: All messages now include phase metadata at creation time
   - **Phase Metadata**: Every message tagged with `additional_kwargs={"phase": N}` where User=0, Phase 1=1, Phase 2=2, etc.
   - **XML Format Updated**: All messages now include `<phase>N</phase>` tag visible to LLMs
   - **Simplified Compression**: Filtering now uses `msg.additional_kwargs.get("phase")` instead of calculating from position
   - **Eliminated Calculations**: Removed all `messages_per_phase` calculations - phase is tracked directly in state
   - **Terminology Clarification**: "Phase" (noun) = discussion cycle, "Pass" (verb) = skip contributing
   - **State Fields Renamed**: `pass_number` → `phase_number`, `final_pass_needed` → `final_phase_needed`, `final_pass_done` → `final_phase_done`
   - **Function Names Updated**: `start_pass()` → `start_phase()`, all references updated throughout codebase
   - **Benefits**:
     - More reliable: Phase tagged at creation, not inferred from structure
     - LLM visibility: Agents can see which phase each message came from
     - Cleaner code: No complex position-based calculations
     - Easier debugging: Phase is explicit in every message
     - Future-proof: Can easily add more metadata
   - **Expected Impact**: More maintainable codebase, clearer terminology distinction, reliable compression filtering

2. **2-Phase Cross-Pollination + History Compression After Phase 2 + Technical Writer Specialist (2025-10-08)**
   - **SUPERSEDED BY ATOMIC PHASES UPDATE**: This entry describes the system before atomic phases were implemented
   - **Phase 1**: Independent assessment (see User only)
   - **Phase 2**: Cross-pollination (see other specialists' Phase 1 responses, own Phase 1 hidden, atomic filtering)
   - **Result**: By end of Phase 2, all specialists have responded to all other specialists' Phase 1 thinking. Chair synthesizes both phases.
   - **NEW FEATURE**: History compression enabled by default (`COMPRESS_HISTORY_AFTER_PHASE3=true` - config name unchanged)
   - Starting Phase 3+, specialists see only Chair's Phase 2 synthesis instead of all Phase 1 & 2 individual responses
   - **Rationale**: Chair in Phase 2 sees ALL Phase 1 & 2 responses (goes last) and synthesizes comprehensively. Phase 3+ becomes "open table" discussion building on this foundation.
   - **Context savings**: Can save 1000s of tokens in longer discussions while preserving all key information
   - **Chair receives special instructions** in Phase 2 to be comprehensive since their synthesis becomes the compression point
   - Messages visible in Phase 3+ when compressed: User question, Notice messages, Chair's Phase 2 synthesis, all Phase 3+ messages (from prior phases)
   - **Configurable**: Set `COMPRESS_HISTORY_AFTER_PHASE3=false` to disable and show full history
   - **NEW SPECIALIST**: Added Technical Writer specialist for API documentation, user guides, architecture docs, and technical content

1. **Identity Analysis + Anti-Self-Labeling + XML Newline + Timestamps + Triple Backticks (2025-10-08)**
   - **CRITICAL FIX**: Strengthened anti-self-labeling instructions to prevent agents from saying "as [role] specialist"
   - **Example violation fixed**: "As [Specialist Role], here's my input..." is now explicitly forbidden with prominent warnings
   - **XML Content Format Clarification**: `<content>` tags can contain newlines - they are preserved in XML for agents to see. The `<content>` tags provide clear boundaries, so multi-line responses work perfectly for LLM parsing.
   - **Human Console Display**: ALL whitespace (newlines, tabs, multiple spaces) is collapsed to single spaces for compact viewing on stdout
   - **Consistent XML Structure for ALL Messages**: ALL message types (Notice, User, Specialist) now use identical XML format:
     - `<message><from>[Name]</from><timestamp_iso>[ISO 8601]</timestamp_iso><phase>N</phase><content>[message content]</content></message>`
     - Notice messages no longer embed timestamps in content - they use `<timestamp_iso>` and `<phase>` tags like all other messages
     - Ensures LLMs see consistent, predictable structure without special cases
   - **ISO 8601 Timestamps in XML**: XML format uses ISO 8601 (`<timestamp_iso>2025-10-08T20:15:30.456</timestamp_iso>`) for consistency and machine-readability
   - **Local Timezone for Humans**: Console output shows local timezone format (`YYYY-MM-DD HH:MM:SS.mmm TZ` like `2025-10-08 12:55:10.123 EDT`) for human readability
   - Timestamps generated dynamically at display time for both XML (agents) and console (humans)
   - **Triple Backticks for Structured Content**: Agents can now use ``` blocks to preserve formatting for structured information (team lists, feature breakdowns, step-by-step plans). Text outside blocks collapses to single line, text inside blocks preserves all whitespace/newlines and is indented 4 spaces on console for visual distinction. Guidelines emphasize VERY sparing use - only when structure aids understanding significantly.
   - **Conciseness Guidelines - CRITICAL**: Strong emphasis added that this is TEXT CHAT communication with humans reading. Agents instructed to keep responses brief (2-4 sentences ideal), think deeply in `<think>` tags but write concisely, use ``` blocks sparingly (5-10 lines max), and be respectful of user's time. Reminder that humans read responses in chat interface.
   - **Benefit**: Agents can write naturally with paragraph breaks, agents see the full structure, humans see compact single-line output for prose and readable structured blocks for lists/tables. Concise responses keep chat readable and respect user attention.
   - **Identity Analysis in Thinking**: Added explicit thinking steps requiring agents to check `<from>` tags in EVERY message
   - **Phase 1**: Added "IDENTITY CHECK" step to identify User's role/background from what they said
   - **Phase 2**: Added "IDENTITY CHECK" and "ANALYZE MESSAGES" steps to map specialist names to contributions
   - **Phase 3+**: Added comprehensive identity analysis including:
     - Step 1: Check `<from>` tags in EVERY message, list User and all specialists
     - Step 2: Analyze own messages (find `<from>{name}</from>` tags)
     - Step 3: Analyze others' messages (map specialist name → contribution)
     - Step 4: Check for `@[{name}]` mentions to see if anyone addressed them
     - Step 28: Explicitly decide WHO they're responding to
   - **Final Phase**: Added identity analysis for all specialist contributions across all phases
   - **Complete Isolation Principle Emphasized**: 
     - Each specialist is a SEPARATE LLM INSTANCE with NO shared context outside transcript
     - Other specialists DO NOT share your knowledge, jargon, or role understanding
     - User does NOT necessarily share technical background
     - CANNOT infer if someone shares your role knowledge
     - The transcript is the ONLY shared knowledge base
     - Each specialist name is UNIQUE - cannot be confused with another
   - **Why Self-Labeling Is Forbidden**: Added explicit explanation:
     - `<from>` tag already identifies uniquely in every message
     - Self-labeling suggests misunderstanding that they cannot be confused with another specialist
     - Creates redundancy with automatic system labeling
   - **`<from>` Tag Analysis Required**: Agents must check `<from>` tags to know WHO said each message, never assume
   - **Expected Impact**: Eliminates self-labeling violations, forces deliberate identity analysis, prevents assumptions about shared knowledge

2. **Dynamic Agent Roster + Config Refactor + Phase 1 Clarification + Explicit/Implicit Focus (2025-10-06)**
   - **MAJOR IMPROVEMENT**: Eliminated all hardcoded specialist counts
   - Created centralized `AGENT_ROSTER` constant in `agents.py`
   - All roster size calculations now use `len(AGENT_ROSTER)` dynamically
   - Pass calculations automatically adjust based on actual roster
   - Consensus detection automatically adapts to roster size
   - Graph workflow uses `AGENT_ROSTER` for edge creation
   - **Adding/removing agents**: Simply modify `AGENT_ROSTER` and add/remove corresponding agent functions
   - **Configuration Refactor**: Model and context window now paired as tuple `(model, num_ctx)` since context window is specific to model/quantization. Sampling parameters remain shared/reusable across models.
   - **Phase 1 Documentation Clarity**: Clarified that Phase 1 has no active filtering because specialists haven't contributed yet (first-time contributions). This is distinct from Phase 2 & Final where own messages are actively filtered out.
   - **Chair Role in Phase 1**: Clarified that in Phase 1, Chair provides their own initial assessment of the User's concern (not synthesis, since they can't see others' responses yet). Starting Phase 2+, Chair can synthesize others' contributions.
   - **Explicit vs Implicit Concerns**: Agents now explicitly instructed to consider both User's explicit request (stated directly) and implicit concerns (underlying unknowns), but primary focus must remain on the explicit request. Only raise implicit concerns if pertinent to answering the explicit request. Clarifying questions must be pertinent, not tangential.
   - **Passing When Only Questions**: Agents should PASS if they only have questions without substantive insights, especially as passes progress. Avoids rabbit holes and unnecessary tangents. Questions without value don't justify participation.
   - **Mixing Questions and Assessments**: Agents can combine clarifying questions with substantive assessments in the same response. Not required to choose one or the other. Encouraged to provide definitive answers first, then ask clarifying questions.
   - **Changing Minds Explicitly**: Agents are allowed to change their perspective as discussion progresses. When changing their mind, they must explicitly state: (1) that they've changed their mind, (2) old perspective, (3) new perspective, (4) reason for change. Promotes transparency and trust.
   - **Definitive Answers with Transparency**: Agents encouraged to answer as definitively as possible based on available information. Partial answers are explicitly allowed - agents should answer what they can and be transparent about limitations. Must identify major concerns that prevent complete assessment and explain what's missing and why it matters.
   - **Skill-Set Relevance**: Agents must assess whether their specific expertise applies to the User's question. Should pass gracefully if their specialist knowledge doesn't add value to the discussion. Prevents "participation for participation's sake" and ensures all contributions are substantive. Includes self-assessment questions in all thinking templates.
   - **Specialist Roster Expansion**: Expanded roster to include additional specialized roles for cloud infrastructure, database architecture, frontend/backend development, testing, documentation, and HR. Demonstrates system scalability to accommodate multiple specialized roles. Current roster defined in `AGENT_ROSTER` in `agents.py`.
   - **Role Description Feature - Dual Perspective System**: Added centralized `ROLE_DESCRIPTIONS` data structure in prompts.py with nested first-person and third-person descriptions for each specialist. First-person descriptions ("You coordinate discussions...") are injected into each specialist's own prompt for self-identity. Third-person descriptions ("Coordinates discussions...") are compiled into a specialist roster shown to all OTHER specialists in BASE_INSTRUCTION under "OTHER SPECIALISTS IN THIS DISCUSSION (CORE SPECIALTIES):" section. This creates both self-awareness ("who I am") and group-awareness ("who others are") from a single maintainable data structure. The roster is dynamically generated per specialist using `generate_specialist_roster()`, excluding the current specialist from their own roster. Benefits: single source of truth, both perspectives stay in sync, easy maintenance, prevents duplication, enables specialists to know what expertise is available from peers.
   - **Startup Persona Display**: System now displays all specialist personas and their system prompts at startup (before asking for user input). First shows the common BASE_INSTRUCTION once (shared by all specialists), then shows each specialist's unique persona with their role description. Uses clear separators (═ and ─) to organize the display. Eliminates redundancy by not repeating the common instruction multiple times. Helps users understand how each agent is configured and what perspectives they bring to discussions. Displays all specialists in their canonical execution order.
   - **XML Message Format**: Changed conversation history format from plain text to compact XML structure to help LLMs better distinguish metadata from content. Each message uses `<message>`, `<from>`, `<timestamp_iso>`, and `<content>` tags with no indentation (optimized for token efficiency). The `<content>` tags can contain newlines - they provide clear boundaries for multi-line content. Element names indicate datatype (e.g., `timestamp_iso` = ISO 8601 timestamp format like `2025-10-08T13:22:52.184`). This explicit structure prevents confusion about where speaker names end and message content begins, reducing the likelihood of duplicate name prefixes in responses.
   - **Explicit Addressing with @ Mentions**: Implemented `@[Name].` format for specialists to explicitly address their audience in messages. Format uses brackets for visual distinction and period for natural break (complete addressing statement, then new sentence). Messages are isolated in `<content>` XML tags for structural clarity. Specialists use `@[User].` to address the User, `@[Specialist name].` to address other specialists, and `@[All].` for general observations. Phase 1 only uses `@[User].` (independent assessments), Phase 2 primarily `@[User].`, and Phase 3+ can address anyone. Multiple recipients in same response are encouraged for natural discussion flow - numbered format recommended for 2+ recipients (e.g., "1) @[User]. ... 2) @[Other specialist]. ...") to provide clear boundaries when complex punctuation exists within each recipient's content. Creates familiar group chat dynamic (like email/Slack) where it's 100% clear who each part of a message is directed to. Enables natural multi-party conversation with specialists asking each other questions and building on each other's points while maintaining clarity about audience. Includes comprehensive guidance in BASE_INSTRUCTION with pass-specific examples and multi-recipient patterns. Natural flow guidance emphasizes @ mentions should be complete addressing statements (like "Dear John.") followed by natural sentences - period avoids double-colon ambiguity that would occur with natural language colons (e.g., "@[User]. I have a concern about:" is clear vs "@[User]: Concern:" which creates context change ambiguity). Numbering prevents ambiguity about content boundaries when sentences contain their own punctuation (colons, semicolons, commas).
   - **Accessible Language - Critical Principle**: Added comprehensive guidance requiring specialists to NEVER assume readers (User or other specialists) know industry abbreviations or technical terms. Each specialist is a separate LLM instance with NO shared context outside the visible transcript. Rule: Always spell out abbreviations on first use with parenthetical explanation (e.g., "RLS (row-level security)", "MVP (Minimum Viable Product)"). Can re-use abbreviations already defined in visible transcript. Also requires brief inline explanations for technical concepts (e.g., "Blue-green deployment (keep old version running while testing new one)"). Pattern: Concept name (brief what-it-does explanation). Token cost is 5-10 extra tokens per concept, but clarity gain is massive - prevents misunderstanding between specialists and User. Reinforces that the transcript is the ONLY shared knowledge base.
   - **Expected Impact**: System is now truly scalable - no hardcoded dependencies on roster size; model/context pairing makes configuration more intuitive; agents stay focused on User's actual question while considering unstated needs; agents avoid rabbit holes by passing when they lack substantive contributions; agents can be flexible and transparent about perspective evolution; users get maximum value from partial information with clear understanding of certainty vs. uncertainty; all contributions are relevant and substantive based on specialist expertise; complete transparency about agent configuration at startup; XML format provides clearer structural boundaries that LLMs parse more reliably; @ mentions create natural group chat dynamics with 100% clarity on message recipients; accessible language ensures everyone (User and all specialists) understands all terms and concepts without guessing

3. **Model Change (8B → 30B Thinking Model)**
   - Changed default model to 30B "Thinking" variant
   - May have significantly longer first-token latency
   - "Thinking" models designed for extended internal reasoning

4. **Prompt Streamlining (2025-10-06)**
   - **MAJOR IMPROVEMENT**: Reduced prompt redundancy by 60-70%
   - User's question now appears as a "User" message in conversation history (natural chat format)
   - User message shown in Phase 1 (agents always see the User's request)
   - User and Notice messages NEVER filtered (always visible to all agents)
   - Eliminated repetitive question statements in every instruction message
   - Removed duplicate formatting instructions (was repeated 3 times)
   - Simplified BASE_INSTRUCTION from ~55 lines to ~35 lines (with identity context)
   - Phase 1: Reduced from 4 messages to 3 messages (~1300 → ~450 tokens)
   - Phase 2: Streamlined instructions, removed redundant question
   - Phase 3+: Reduced massive instruction block from ~150 lines to ~20 lines
   - Final Pass: Simplified system prompt from ~15 lines to ~10 lines
   - Removed unused `enumerate()` in history loops - agents see timestamps only, no numbering
   - Added explicit identity awareness: agents know their display name and message format
   - Agents see messages in XML format: `<message><from>Name specialist</from><timestamp_iso>2025-10-08T13:22:52.184</timestamp_iso><phase>N</phase><content>response</content></message>`
   - XML element names indicate datatype: `timestamp_iso` = ISO 8601 timestamp format, `phase` = phase number
   - Human console output uses local timezone format: `YYYY-MM-DD HH:MM:SS.mmm TZ` (e.g., `2025-10-08 13:22:52.184 EDT`)
   - Console output remains traditional: "[timestamp] Name specialist said: response"
   - Clear explanation of message types: User (question), Notice (system), Specialists (responses)
   - Clarified that agents respond naturally and system adds formatting (prevents duplication issue)
   - Added guidance: agents can ask clarifying questions but don't wait for responses
   - Agents can incorporate User's additional information if provided during discussion
   - Updated Chair role to explicitly speak LAST in every pass (Phase 1: own assessment; Phase 2+: synthesizes all other contributions)
   - Removed "note if consensus seems possible" - consensus detection is implicit/system-level only
   - Prevents bias from public consensus declarations affecting subsequent passes
   - Chair can privately assess consensus in <think> tags (console observability) but not in public response
   - **Final Pass - Chair's Special Role**: Chair's final response is PRIMARY OUTPUT for User
   - Chair must provide comprehensive summary of all points, questions, agreements, disagreements, and recommendations
   - **Expected Impact**: Faster generation, clearer instructions, better model focus, more natural conversation flow, comprehensive final output

5. **Timestamp System Added** (Updated 2025-10-08 for consistency)
   - Dynamic timestamp generation at display time
   - ALL messages now use `<timestamp_iso>` tag in XML format (Notice, User, Specialist)
   - Console display prepends timestamp in local timezone for all message types
   - **Note**: Originally Notice messages embedded timestamps in content, but updated to use `<timestamp_iso>` tag for consistency
   - **Potential Issue**: Generating timestamps at display time means same message shows different timestamps to different agents

6. **Realism and Pragmatism Framework (2025-10-06)**
   - **Shared guidance** in BASE_INSTRUCTION (applies to all agents):
     - Focus on realistic scenarios and practical concerns
     - Prioritize likely situations over unlikely edge cases
     - Assess realistic likelihood of concerns
     - Balance thoroughness with pragmatism
   - **Chair-specific role**: Assess likelihood (high/moderate/low) when synthesizing others' concerns
     - Example: "Context raised X (highly relevant), Skeptic noted Y (less likely edge case)"
     - Unique because Chair evaluates OTHERS' contributions, not just their own
   - **Phase 3+ reinforcement**: Added REALISM step to thinking structure (keeps focus during critical convergence phase)
   - **Design principle**: Single shared guidance in BASE_INSTRUCTION, only add agent-specific wording when role truly differs
   - **Expected Impact**: Prevents infinite discussion about unlikely scenarios, grounds discussion in practical guidance

7. **Multi-Agent Culture Architecture (2025-10-06)**
   - **New architectural pattern**: CULTURE + PERSONA + BASE_INSTRUCTION
   - **MULTI_AGENT_CULTURE**: Shared Operating Principles for ALL agents
     - DIGNITY, NON-HARM, CONSENT, TRANSPARENCY, CONTEXT, PURPOSE
     - Defines "who we are as a team" - shared values
   - **PERSONA** (agent-specific): Individual specialist focus and lens
     - Defines "who I am specifically" - unique role
   - **BASE_INSTRUCTION**: Shared operational guidelines for all agents
     - Defines "how we operate" - common behaviors
   - **Refactoring benefit**: Removed duplication (Chair and Ethicist had identical principle lists)
   - **Code maintainability**: Single source of truth for shared culture
   - **Distributed responsibility**: All agents embody shared principles, not just Ethicist
   - **Expected Impact**: Consistent cultural foundation, easier to update principles globally, clearer separation of concerns

8. **Notice Messages Added**
   - System messages announcing each phase
   - Added to conversation state and agent history
   - Complex display logic (already has timestamp, don't double-wrap)
   - **Potential Issue**: Notice message filtering/display logic

9. **Output Stream Separation**
   - STDOUT: Clean conversation log
   - STDERR: Debug/status information
   - Changed what goes where multiple times

10. **Response Format with XML Newline Handling**
   - Agents can write naturally with newlines - XML `<content>` tags handle them properly
   - Human console output collapses all whitespace to single spaces for compact display
   - Multiple sentences and natural paragraph structure allowed
   - No markdown or bullet points (plain text only)
   - Consolidated formatting guidance into BASE_INSTRUCTION (not repeated)

11. **Extensive Debug Output**
   - Shows exact messages sent to Ollama
   - Shows waiting/response status
   - Preview of message content

### Known Issues & Bug Areas

#### 1. **Current Hang Issue (CRITICAL)**
**Symptoms**: Hangs after "Invoking Ollama... waiting for response..."
**Possible Causes**:
- 30B Thinking model has very long first-token latency
- 50k context window too large for efficient processing
- Prompt complexity from Notice messages and timestamps
- Model spending excessive time in "thinking" mode
- Ollama server issue or timeout

**Debug Approach**:
- Check where hang occurs (see debug output)
- Try smaller model (8B) to isolate model vs. prompt issue
- Try smaller context window (reduce from 50560)
- Check Ollama logs: `ollama logs` or check server output
- Monitor GPU usage during hang

#### 2. **Timestamp Generation Issues** ✅ RESOLVED (2025-10-10)
**Problem**: Timestamps were being generated at display time, not message creation time
**Impact**: 
- Same message would show different timestamps to different agents
- Not consistent with actual time message was created
- Could confuse agents about temporal order

**Example of old behavior**:
```
Phase 1 Context creates message at 14:32:15
Phase 2 Research sees it with timestamp 14:32:30 (when Phase 2 starts)
Phase 3 Engineer sees it with timestamp 14:35:00 (when Phase 3 starts)
```

**Solution**: Timestamps now stored in `additional_kwargs["timestamp"]` at message creation time
**Implementation**:
- Specialist messages: Line 1089 + 1097 in `agents.py`
- Notice messages: Line 1415 + 1429 in `agents.py`
- User messages: Line 1436 + 1440 in `agents.py`
- Display retrieval: Lines 413, 496, 581 in `agents.py` with backwards-compatible fallback
- All agents now see the same timestamp for each message (consistent temporal context)

#### 3. **Notice Message Display Complexity**
**Problem**: Multiple conditional logic paths for showing Notice messages
**Issues**:
- Different handling in Phase 2 vs Phase 3+ vs Final
- Special case to not double-wrap timestamps
- Filtering logic spread across multiple locations

**Locations**:
- `agents.py` lines 154-160 (Phase 2/Final)
- `agents.py` lines 182-188 (Phase 3+)
- `main.py` lines 62-63 (Display to user)

**Potential Bugs**:
- Notice messages might not show correctly in all phases
- Double timestamps if logic fails
- Messages missing from agent context

#### 4. **Message Filtering Complexity**
**Problem**: Complex filtering logic for different stages
**Current Logic**:
```python
# Phase 2/Final: Filter own messages
other_messages = [msg for msg in history if msg.name != name]

# Phase 3+: Show all (no filtering)
messages_to_show = history_messages

# But then: Special handling for Notice in display loop
if speaker == "Notice":
    # Don't add timestamp
else:
    # Add timestamp
```

**Potential Issues**:
- Filtering not applied consistently
- Notice messages might be handled incorrectly
- Complex conditional chains prone to logic errors

#### 5. **Context Window Size vs Model Capacity**
**Problem**: 50k context window may be too aggressive
**Considerations**:
- 30B model may not efficiently handle 50k tokens
- Each pass adds ~1k-2k tokens (6 agents × ~200 tokens each)
- After 10 passes: ~20k tokens of history
- System prompts + instructions: ~1-2k tokens per agent
- Very long contexts slow down generation significantly

**Recommendation**: Try reducing to 32k or even 16k for testing

#### 6. **Progressive Retraction Inferencing**
**Problem**: Agents must infer conversation stage from context
**Complexity**:
- Must parse Notice messages to know phase number
- Must count messages to gauge progression
- Must interpret timestamps for pacing
- More cognitive load on model

**Potential Issues**:
- Agents may not correctly infer stage
- May not understand when to pass (skip contributing)
- Notice message parsing could fail
- Could contribute to slow generation

#### 7. **Mandatory Contribution Enforcement**
**Location**: `agents.py` lines ~477-486
```python
if is_mandatory and ("no further comments" in content.lower() or len(content) < 50):
    # Force a basic contribution
    content = f"From my perspective as {name}, this situation requires..."
```

**Issues**:
- Simple string matching for pass detection
- 50 character threshold arbitrary
- Fallback response is generic/low quality
- Could mask issues with agent not responding properly

#### 8. **Thinking Block Extraction**
**Location**: `agents.py` lines ~447-455
```python
think_blocks = re.findall(
    r'<\s*think\s*>.*?<\s*/\s*think\s*>',
    raw_content,
    flags=re.DOTALL | re.IGNORECASE
)
```

**Potential Issues**:
- Nested thinking blocks may not parse correctly
- Malformed tags could break extraction
- Thinking content might appear in public response if extraction fails

#### 9. **LangGraph State Mutations**
**Problem**: State updates through return dictionaries
**Complexity**:
- `add_messages` annotation merges messages
- Other fields directly replace
- Must return correct structure or state corruption

**Potential Issues**:
- Forgetting to include messages in return dict
- Wrong structure in return dict breaks state
- No validation of state structure

#### 10. **Agent Roster Management** ✅ RESOLVED
**Solution**: Centralized agent roster with dynamic calculations
**Location**: `agents.py` line 20-22

**Implementation**:
```python
# Agent roster - canonical execution order
AGENT_ROSTER = ["context", "research", "engineer", "skeptic", "ethicist", "chair"]
```

**Benefits**:
- Single source of truth for agent list
- All calculations dynamically infer roster size: `len(AGENT_ROSTER)`
- Pass calculations automatically adjust
- Consensus detection automatically adjusts
- To add/remove agents: modify AGENT_ROSTER and add/remove corresponding agent functions

## Debugging Guide

### Enable Full Debug Output
Already enabled in code:
- Message previews before sending to Ollama
- "Invoking Ollama" and "Got response" markers
- Agent status headers with context info

### Check Ollama Status
```bash
# Check if Ollama is running
curl http://localhost:11434/api/tags

# Check Ollama logs (if running as service)
journalctl -u ollama -f

# Check model is loaded
ollama list
```

### Test with Smaller Model
Edit `config.py`:
```python
default_model = "hf.co/bartowski/Qwen_Qwen3-8B-GGUF:Q4_K_M"
default_num_ctx = 16000
```

### Isolate Issues
1. **Model Issue**: Try 8B model with same prompts
2. **Context Issue**: Reduce context window to 16k
3. **Prompt Issue**: Simplify instructions temporarily
4. **Notice Issue**: Remove Notice messages from agent context
5. **Timestamp Issue**: Remove dynamic timestamps

### Check Message Flow
Add more debug output:
```python
print(f"[DEBUG] Building history for {name}, stage: {current_phase}", file=sys.stderr)
print(f"[DEBUG] Total messages in state: {len(history_messages)}", file=sys.stderr)
print(f"[DEBUG] Messages after filtering: {len(messages_to_show)}", file=sys.stderr)
```

### Monitor Performance
```bash
# Watch GPU usage
watch -n 0.5 nvidia-smi

# Watch CPU usage
htop

# Check Ollama API directly
curl -X POST http://localhost:11434/api/generate \
  -d '{"model": "hf.co/bartowski/Qwen_Qwen3-30B-A3B-Thinking-2507-GGUF:Q4_K_M", 
       "prompt": "Hello", 
       "stream": false}'
```

## Files Reference

### Core Implementation
- `main.py`: Entry point, user interaction, output display
- `axion_swarm/agents.py`: Agent functions, message history logic, LLM invocation
- `axion_swarm/config.py`: Model and sampling configuration
- `axion_swarm/graph.py`: LangGraph workflow definition
- `axion_swarm/state.py`: State TypedDict definition
- `axion_swarm/prompts.py`: System prompts for each agent
- `axion_swarm/colors.py`: ANSI color code utilities

### Supporting Files
- `.env`: Optional environment variable overrides
- `requirements.txt` or `pyproject.toml`: Dependencies

## Next Steps for Debugging Current Hang

### Immediate Actions
1. **Check debug output**: See if hang is before/during/after Ollama call
2. **Test with 8B model**: Rule out model size issue
3. **Reduce context window**: Try 16k tokens
4. **Check Ollama logs**: Look for errors or warnings
5. **Test Ollama directly**: Verify it's responding to simple prompts

### Potential Quick Fixes
1. Reduce context window: `50560 → 16000`
2. Switch to 8B model temporarily
3. Remove Notice messages from agent context (already tested, didn't fix)
4. Simplify system prompts
5. Reduce number of instruction reminders

### Long-Term Improvements Needed
1. Store timestamps with messages instead of generating at display
2. Simplify Notice message handling logic
3. Add streaming output for model responses
4. Add timeout handling for Ollama calls
5. Validate state structure between nodes
6. Add performance monitoring/logging
7. Create configuration profiles (fast/balanced/quality)
8. Add retry logic for failed LLM calls

## Prompt Optimization Summary (2025-10-06)

### What Was Improved

**Before**: Prompts contained significant redundancy
- User's question repeated 3 times per agent invocation
- Formatting requirements repeated 3 times
- BASE_INSTRUCTION contained ~55 lines of rules
- Phase 3+ instructions were ~150 lines of repetitive guidelines
- Total context per Phase 1 agent: ~1,300 tokens

**After**: Streamlined, focused prompts
- User's question stated once
- Formatting requirement in BASE_INSTRUCTION only
- BASE_INSTRUCTION reduced to ~24 focused lines
- Phase 3+ instructions reduced to ~20 clear lines
- Total context per Phase 1 agent: ~400 tokens

### Key Improvements by Pass

**Phase 1 (Initial Perspective)**:
```
Message 1: SystemMessage with role + BASE_INSTRUCTION
Message 2: Question + brief instruction + think template
Total: ~400 tokens (was ~1,300)
```

**Phase 2 (Review Others)**:
```
Message 1: SystemMessage with role + BASE_INSTRUCTION
Message 2: History (other specialists only)
Message 3: Question + instruction + think template
Total: Reduced by ~500 tokens in instructions
```

**Phase 3+ (Progressive Retraction)**:
```
Message 1: SystemMessage with role + BASE_INSTRUCTION
Message 2: Full history
Message 3: Question + streamlined process (4 steps vs 100+ lines)
Total: Reduced by ~800 tokens in instructions
```

**Final Pass (Synthesis)**:
```
Message 1: Clean system prompt (role only, ~6 lines vs ~15)
Message 2: History (other specialists only)
Message 3: Question + brief instruction
Total: Reduced by ~400 tokens
```

### Expected Benefits

1. **Performance**: 60-65% less instruction context = faster processing
2. **Clarity**: No contradictory or redundant rules to confuse model
3. **Focus**: Model can focus on task instead of parsing repetitive instructions
4. **Consistency**: Single source of truth for each rule (no contradictions)
5. **Maintainability**: Easier to update prompts without checking multiple locations

### New BASE_INSTRUCTION Structure

```
CORE RULES (5 items):
- Basic behavior expectations
- Formatting requirements
- Response guidelines

CONTRIBUTION GUIDELINES (4 items):
- When to contribute vs pass
- Progressive retraction concept

THINKING PROCESS (4 items):
- How to use <think> tags
- Self-assessment requirements
```

Total: ~24 lines (was ~55 lines with redundancy)

## Azure OpenAI Integration (2025-01-09)

### Rate Limit Handling (2025-01-09)

**Automatic Rate Limit Recovery**:

The system now automatically handles Azure OpenAI rate limit errors (429) with intelligent retry logic:
- **Global coordination**: When ANY agent hits rate limit, ALL parallel agents pause
- **Automatic retry**: Up to 5 retries with smart wait-and-retry logic
- **Smart parsing**: Extracts retry-after duration from error message and adds 1 second safety buffer
- **Sensible default**: If parsing fails, defaults to 60 seconds
- **No manual intervention**: System handles rate limits transparently
- **No data loss**: Conversation state preserved, retries seamlessly after waiting
- **Conversation continuity**: Adds a Notice message to conversation history documenting the pause

**Notice Messages for Rate Limits**:

When a rate limit is hit, the system adds two Notice messages to the conversation history:

**Before the wait**:
```
Notice: All specialists, let's take a brief break for the next 61 seconds, then let's return to continue thinking clearly about the tasks -- ensuring we are staying on topic about the User's explicit concerns.
```

**After the wait completes**:
```
Notice: All specialists are back, let's continue the discussion and remember to stay on topic about the User's explicit concerns.
```

**Benefits**:
- Provides context to specialists in future phases about what happened
- Makes the pause visible in the conversation record
- Human-like communication style (like a meeting break)
- Reinforces the importance of staying on topic about User's explicit concerns
- Clear bookends (before/after) make the pause period explicit
- Specialists will see both Notices in subsequent phases as part of their conversation history

**Implementation** (`agents.py`):
- Global `_rate_limit_lock` and `_rate_limit_until` for cross-agent coordination
- `wait_if_rate_limited()` called before each Azure OpenAI API call
- `set_rate_limit(duration)` sets global pause when rate limit hit
- Retry loop with `RateLimitError` exception handling
- Thread-safe with proper locking for parallel execution
- **First Notice** (break announcement) added to `additional_messages` on first retry attempt
- System waits for rate limit to expire (`wait_if_rate_limited()`)
- **Second Notice** (back to discussion) added to `additional_messages` after wait completes
- Both Notices returned alongside specialist's response in same message batch

**User Experience**: Clear status messages during rate limit handling, no crashes, automatic recovery, conversation record includes before/after pause documentation.

### Rate-Limit-Triggered History Compression (Experimental Feature)

**Concept**: When rate limits are hit, the system can automatically compress conversation history to reduce context size and prevent cascading rate limit issues.

**How It Works** (Phase 3+ only):
1. When ANY agent hits a 429 rate limit error, the system waits as usual (parsed duration + 1 second buffer, or 60 seconds default)
2. After waiting, if compression criteria are met (including phase ≥ 3), the system invokes ONLY the Chair to summarize recent discussion
3. Chair creates a comprehensive summary of all recent specialist contributions since the last compression point
4. All specialist messages BEFORE this new Chair summary are marked as not-visible (filtered out)
5. Normal phase execution resumes with compressed history

**Why Phase 3+ Only?**: Phases 1-2 already receive Chair's normal end-of-Phase-2 compression (when `COMPRESS_HISTORY_AFTER_PHASE3=true`), so rate-limit compression would be redundant. This feature only applies to Phase 3+ where we're working with already-compressed history and accumulating new context.

**Compression Criteria** (all must be true):
- Feature is enabled: `RATE_LIMIT_COMPRESSION=true` (disabled by default)
- Rate limit was hit during the current phase
- **Phase 3 or later**: Phases 1-2 already get Chair's normal end-of-Phase-2 compression, so rate-limit compression only applies in Phase 3+
- Enough messages accumulated: at least `RATE_LIMIT_COMPRESSION_MIN_MESSAGES` (default 10) since last compression
- Context is large: at least `RATE_LIMIT_COMPRESSION_MIN_TOKENS` (default 100,000) total tokens
- Chair hasn't just summarized: no Chair message in the last 5 messages

**Visible Messages After Compression**:
- ✅ User messages (always visible)
- ✅ Notice messages (always visible)
- ✅ Chair's new compression summary
- ✅ Any specialist messages AFTER the new Chair summary
- ❌ Specialist messages BEFORE the new Chair summary (filtered out)

**Benefits**:
- Prevents cascading rate limits by reducing context size going forward
- Makes forced wait time productive through compression
- Significantly lowers token usage in subsequent calls
- Uses the same proven compression mechanism as Phase 2
- Enables longer conversations without context explosion

**Trade-offs**:
- Adds 5-10 seconds for Chair compression during rate limit recovery
- Some nuanced details might be lost in Chair's summary
- Specialists can't reference recent contributions they made before compression
- Requires careful tuning of compression thresholds

**Configuration**:
```bash
# Enable rate-limit-triggered compression (default: false)
RATE_LIMIT_COMPRESSION=false

# Minimum messages since last compression to trigger (default: 10)
RATE_LIMIT_COMPRESSION_MIN_MESSAGES=10

# Minimum tokens to trigger compression (default: 100000)
RATE_LIMIT_COMPRESSION_MIN_TOKENS=100000
```

**Implementation** (`agents.py`):
- `should_compress_after_rate_limit(state)`: Evaluates compression criteria
- `CHAIR_RATE_LIMIT_COMPRESSION_SYSTEM`: Special prompt for Chair's compression task
- Integrated into `execute_phase_parallel()`: checks criteria, invokes Chair, updates `last_compression_message_index`
- Message filtering respects `last_compression_message_index`: messages before this index are filtered out (except User/Notice)

**State Variables**:
- `last_compression_message_index`: Marks the index of the last compression point (Chair's summary message)
- `rate_limit_compression_pending`: Flag indicating a rate limit was hit (reset at start of each phase)

**When to Use**: 
- Enable this feature if you frequently hit rate limits during long conversations (especially in Phase 3+)
- Keep disabled (default) if conversational continuity is more important than context size
- Monitor token usage with stderr output to determine if compression is needed
- **Note**: This feature only triggers in Phase 3+, since Phases 1-2 already get Chair's normal compression at end of Phase 2

### Overview

The system now supports **dual provider mode** with seamless switching between local Ollama and hosted Azure OpenAI:

- **Azure OpenAI** (hosted, parallel execution) - **DEFAULT**
- **Ollama** (local GPUs, sequential execution)

### Implementation Summary

**Files Modified**:
- `axion_swarm/config.py` - Provider selection, Azure OpenAI configuration
- `axion_swarm/agents.py` - `get_llm()` provider dispatch, parallel execution system
- `axion_swarm/graph.py` - Simplified graph with parallel execution node

**Key Changes**:

1. **Provider Configuration** (`config.py`):
   - Added `ProviderType.AZURE_OPENAI` and `ProviderType.OLLAMA`
   - Added `AzureOpenAIConfig` dataclass with gpt-5-mini specifications
   - Default provider: `AZURE_OPENAI`
   - Configurable via `PROVIDER` environment variable

2. **LLM Provider Support** (`agents.py`):
   - Updated `get_llm()` to return `ChatOllama` or `AzureChatOpenAI`
   - Provider detection based on `agent_config.provider`

3. **Parallel Execution System** (`agents.py`):
   - Added `invoke_agent_async()` - async wrapper with semaphore concurrency control
   - Added `execute_phase_parallel()` - executes specialists in parallel, Chair sequential
   - Added `execute_phase_parallel_sync()` - sync wrapper for LangGraph
   - **CRITICAL**: Chair executes AFTER all specialists complete as one atomic group

4. **Simplified Graph** (`graph.py`):
   - Replaced individual agent nodes with single `execute_phase` node
   - Simplified from 100+ edges to 3 nodes, 3 edges
   - Same code handles both parallel and sequential execution

### gpt-5-mini Model Specifications

- **Total context window**: 400,000 tokens
- **Max input**: 272,000 tokens
- **Max output**: 128,000 tokens
- **max_tokens parameter**: Controls OUTPUT tokens only (completion/response length)
- **Default max_tokens**: 128,000 (set to maximum allowed output)

**Sampling Parameters Limitation**:
- gpt-5-mini **only supports default sampling parameters**
- temperature: 1.0 (fixed, not configurable)
- top_p: default (fixed, not configurable)
- Custom temperature/top_p values will cause 400 Bad Request errors
- The system automatically omits these parameters when using Azure OpenAI

**Thinking/Non-Thinking Separation**:
- The `<think>` tag approach is **provider-agnostic** and works with both Ollama and Azure OpenAI
- Not an API feature - implemented via prompt engineering and text parsing
- Models (both Ollama and Azure OpenAI) understand and follow XML tag instructions
- System extracts `<think>` blocks from responses and displays them on stderr (dark green)
- Think blocks are stripped from final messages shared with other agents
- No special API calls or parameters required
- Works seamlessly across both providers without code changes

### Execution Modes

#### Azure OpenAI (Parallel)
- **Concurrency**: 15 specialists execute concurrently per phase
- **Chair**: Executes sequentially AFTER all specialists complete (atomic group)
- **Phase 1**: ~10-15 seconds (15 specialists parallel, Chair skips)
- **Phase 2+**: ~15-20 seconds (15 specialists parallel + Chair sequential)
- **Speedup**: **10-15x faster** than sequential Ollama

#### Ollama (Sequential)
- **Concurrency**: 1 (semaphore enforces sequential execution)
- **Chair**: Executes sequentially after all specialists (same as Azure)
- **Phase 1**: ~120 seconds (15 specialists sequential, Chair skips)
- **Phase 2+**: ~128 seconds (16 specialists sequential, Chair participates)
- **Rationale**: Prevents VRAM thrashing with large models and contexts

### Configuration

**Environment Variables**:

```bash
# Provider selection (default: azure_openai)
PROVIDER=azure_openai  # or "ollama"

# Azure OpenAI (REQUIRED: Get from Azure Portal > Your OpenAI Resource > Keys and Endpoint)
AZURE_OPENAI_ENDPOINT=https://[your-resource-name].cognitiveservices.azure.com/
AZURE_OPENAI_API_KEY=[key-from-azure-portal]
AZURE_OPENAI_MODEL=gpt-5-mini
AZURE_OPENAI_DEPLOYMENT=gpt-5-mini
AZURE_OPENAI_API_VERSION=2024-12-01-preview
AZURE_OPENAI_MAX_TOKENS=128000

# Ollama (when PROVIDER=ollama)
OLLAMA_BASE_URL=http://localhost:11434
DEFAULT_MODEL=hf.co/bartowski/Qwen_Qwen3-30B-A3B-Thinking-2507-GGUF:Q5_K_M
OLLAMA_NUM_CTX=36992

# Shared
TEMPERATURE=0.6
TOP_P=0.95
COMPRESS_HISTORY_AFTER_PHASE3=true
SHOW_MESSAGE_DEBUG=false  # Show raw XML messages with VISIBLE/FILTERED indicators

# Checkpoint system (default: true)
ENABLE_CHECKPOINTS=true  # Save conversation state after each phase
CHECKPOINT_FILE=.axion_checkpoint.json  # Checkpoint file location

# Rate-limit-triggered compression (default: false, experimental)
RATE_LIMIT_COMPRESSION=false  # Enable automatic history compression on rate limits
RATE_LIMIT_COMPRESSION_MIN_MESSAGES=10  # Minimum messages since last compression
RATE_LIMIT_COMPRESSION_MIN_TOKENS=100000  # Minimum tokens to trigger compression

# Debug output (default: false)
SHOW_MESSAGE_DEBUG=false  # Show raw XML message objects with VISIBLE/FILTERED indicators
```

### Parallel Execution Architecture

**Phase Execution Flow**:

```
Start Phase
    ↓
Create specialist tasks (15 tasks)
    ↓
Launch all specialists (parallel or sequential via semaphore)
    ↓
┌─────────────────────────────────────┐
│  Context   Research   Engineer      │  ← Concurrent (Azure)
│  Skeptic   Ethicist   Cloud         │  ← or Sequential (Ollama)
│  DB        Backend    Frontend      │  ← via Semaphore
│  DevOps    Product    QA            │  ← control
│  Tech      HR                       │  ← (15 tasks)
└─────────────────────────────────────┘
    ↓
asyncio.gather() - Wait for ALL to complete (atomic group)
    ↓
Collect all specialist messages in AGENT_ROSTER order
    ↓
Update state with specialist messages
    ↓
Chair executes (sees all specialist messages from current phase)
    ↓
Collect Chair message
    ↓
Return all messages to LangGraph
    ↓
Check Continuation
```

**CRITICAL Design Constraint**: Chair always executes **sequentially** AFTER all specialists complete as one atomic group. This ensures Chair can synthesize all specialist responses from the current phase. Implemented using `asyncio.gather()` to wait for all specialist tasks before Chair execution.

### Concurrency Control

**Semaphore-Based Approach**:
- **Azure OpenAI**: `Semaphore(15)` - up to 15 specialists execute concurrently
- **Ollama**: `Semaphore(1)` - enforces sequential execution
- Same code supports both modes transparently

**Benefits**:
- Prevents VRAM thrashing on Ollama (concurrency=1)
- Enables parallel execution on Azure OpenAI (concurrency=15)
- Chair always waits for complete atomic group regardless of provider

### Dependencies

All required dependencies already present in `pyproject.toml`:
- `langchain-openai>=0.2.0` - Azure OpenAI support
- `langchain-ollama>=0.1.0` - Ollama support

### Alignment with Architecture

This implementation realizes the "Cloud Provider Parallelization (Future Improvement)" section:
- ✅ Parallel execution for cloud providers (Azure OpenAI)
- ✅ Sequential execution for Ollama (concurrency=1)
- ✅ Chair goes last and sees all current phase messages
- ✅ Atomic phase groups via `asyncio.gather()`
- ✅ Same code supports both execution modes
- ✅ Configurable via environment variables
- ✅ No breaking changes to existing functionality

### Console Output Synchronization

**Thread-Safe Output with Mutex**:

When specialists execute in parallel (Azure OpenAI mode), their console output could interleave and become unreadable. To prevent this, a global threading lock serializes ALL console output per agent:

```python
# Global lock for console output (agents.py)
_console_output_lock = threading.Lock()

# Usage in agent execution (3-stage atomic output)
debug_output_buffer = []  # Collect visibility debug info during message prep
# ... buffer debug output while building messages ...

# After LLM completes, print everything atomically:
with _console_output_lock:
    # 1. Print buffered visibility debug output
    for line in debug_output_buffer:
        print(line, file=sys.stderr)
    
    # 2. Print token and execution info
    print(f"AGENT: {name}", file=sys.stderr)
    print(f"INPUT TOKENS: {input_tokens:,}", file=sys.stderr)
    # ... token stats ...
    
    # 3. Print thinking blocks
    for block in think_blocks:
        print(block, file=sys.stderr)
    
    sys.stderr.flush()
```

**Key Properties**:
- **Complete Atomicity**: All output for one agent (visibility + tokens + thinking) prints together
- **Buffered Approach**: Debug visibility collected in buffer, printed only under lock
- **Lock Duration**: Only held during print statements (~5-10ms total)
- **Lock NOT Held During**: LLM invocation, message preparation, token counting
- **Zero Performance Impact**: Parallel execution unaffected, only serializes output
- **No Interleaving**: Each agent's complete output block prints without interruption

**Output Sections Protected by Lock** (in order):
1. Message visibility debug (VISIBLE/FILTERED messages)
2. Agent debug headers (phase info, token counts, utilization)
3. Think blocks (internal reasoning, dark green)
4. Error messages (token limits, mandatory phase violations)
5. Chair participation messages

### Checkpoint and Resume System

**Automatic State Persistence**:

The system automatically saves conversation state after each phase completes, allowing you to resume multi-phase discussions if interrupted:

```python
# After each phase, before starting next phase:
save_checkpoint(state)  # Atomic write + fsync to disk
```

**Checkpoint Timing and Stagnation Detection**:

To ensure clean resumption, checkpoints are saved **before** stagnation detection runs (Phase 4+):

1. **Chair synthesis completes** → checkpoint saved with clean state
2. **Stagnation detection runs** → may set `final_phase_needed=True`
3. **Regular checkpoint skipped** → flag prevents double-save

This ensures that if a discussion is interrupted and resumed, it picks up from **before** the final round decision. On the second run, stagnation may be detected at a different phase or not at all, allowing the discussion to evolve differently.

**Configuration Checksum Validation**:

Checkpoints include a SHA256 checksum of the entire agent configuration (roster, role descriptions, all prompts). This ensures checkpoints are only loaded if they match the current code:

```python
config_checksum = compute_config_checksum()  # Hash of roster + prompts
checkpoint_data = {
    "config_checksum": config_checksum,
    "phase_number": state["phase_number"],
    "messages": [...],
    # ... other state
}
```

**Compatibility Check on Load**:
- If roster changes (add/remove agents): checkpoint rejected
- If role descriptions change: checkpoint rejected  
- If any prompt changes: checkpoint rejected
- If checksums match: checkpoint loaded and discussion resumes

**User Workflows - All Scenarios**:

**Scenario 1: No Checkpoint File**
```
$ python main.py
[Persona display...]

================================================================================
# 🤖 Axion Swarm - Multi-Agent Discussion System
================================================================================

Enter your discussion topic: █
```
- No checkpoint prompt shown
- Goes directly to asking for discussion topic
- Starts fresh conversation
- Checkpoint will be created after Phase 1 completes

**Scenario 2: Checkpoint Exists → User Resumes → Checksum Matches**
```
$ python main.py
[Persona display...]

================================================================================
# 🤖 Axion Swarm - Multi-Agent Discussion System
================================================================================

📂 Checkpoint file found!
Resume from checkpoint? (y/n): y
✅ Checkpoint loaded: .axion_checkpoint.json
   Phase: 3, Messages: 42, Saved: 2025-01-09T12:34:56
   Config checksum: a1b2c3d4e5f6g7h8... (matches)
✅ Resuming from Phase 3
================================================================================

[Discussion continues from Phase 3...]
```
- Checkpoint loaded successfully
- Discussion resumes from saved phase
- All messages restored

**Scenario 3: Checkpoint Exists → User Resumes → Checksum Mismatch**
```
$ python main.py
[Persona display...]

================================================================================
# 🤖 Axion Swarm - Multi-Agent Discussion System
================================================================================

📂 Checkpoint file found!
Resume from checkpoint? (y/n): y
⚠️  Checkpoint configuration mismatch!
   Checkpoint was created with a different agent roster or prompts.
   Checkpoint checksum: a1b2c3d4e5f6g7h8...
   Current checksum:    9z8y7x6w5v4u3t2s...
   The checkpoint cannot be used and will be ignored.
❌ Checkpoint is incompatible with current code.
🗑️  Checkpoint deleted
   Starting fresh conversation

Enter your discussion topic: █
```
- Checksum validation fails (roster/prompts changed)
- Checkpoint automatically deleted
- Falls through to prompt for new topic
- Starts fresh conversation

**Scenario 4: Checkpoint Exists → User Declines**
```
$ python main.py
[Persona display...]

================================================================================
# 🤖 Axion Swarm - Multi-Agent Discussion System
================================================================================

📂 Checkpoint file found!
Resume from checkpoint? (y/n): n
🗑️  Checkpoint deleted
   Starting fresh conversation

Enter your discussion topic: █
```
- User explicitly declines to resume
- Checkpoint deleted immediately
- Prompts for new discussion topic
- Starts fresh conversation

**Key Features**:
- **Atomic Writes**: Write to temp file, fsync, rename (ensures crash safety)
- **Directory Fsync**: Parent directory synced to ensure rename persists
- **Configuration Validation**: Prevents loading incompatible checkpoints
- **Transparent**: Enabled by default, can be disabled via `ENABLE_CHECKPOINTS=false`
- **Configurable Path**: Set via `CHECKPOINT_FILE` environment variable

**Technical Implementation**:
- File: `axion_swarm/checkpoint.py`
- Graph node: `save_checkpoint_node` (runs after `check_continuation`)
- Serialization: LangChain messages → JSON dicts
- Deserialization: JSON dicts → LangChain messages
- Checksum: SHA256 of JSON-serialized config (sorted keys for determinism)
- Files: `.axion_checkpoint.json` (checkpoint), `.axion_checkpoint.tmp` (temp during write)
- Git: Checkpoint files excluded in `.gitignore`

### Prompt Caching Optimization

**Cache-Optimized Prompt Structure**:

System prompts are structured to maximize caching efficiency with providers that support prefix caching (Anthropic, potentially Azure OpenAI):

```python
# Structure: Shared content FIRST (cached), specialist-specific LAST (not cached)
def build_system_prompt(cache_optimized=True):
    if cache_optimized:
        return BASE_INSTRUCTION.format(
            display_name=display_name,
            specialist_roster=specialist_roster
        ) + "\n\n" + persona_section
```

**Prompt Component Order** (cache-optimized mode):
1. **MULTI_AGENT_CULTURE** (~200 tokens) - Shared across all agents ✓ CACHED
2. **BASE_INSTRUCTION** core (~1300 tokens) - Shared instructions ✓ CACHED
3. **Identity section** (~100 tokens) - Contains {display_name} ✗ Not cached
4. **Specialist roster** (~500 tokens) - Contains {specialist_roster} ✗ Not cached
5. **Agent persona** (~200 tokens) - Role-specific ✗ Not cached

**Cache Efficiency**:
- ~1500 tokens cached out of ~2300 total
- ~65% cache hit rate per agent invocation
- Significant cost and latency reduction for repeated calls

**Legacy Mode** (Ollama):
- Persona first, shared content last
- No caching benefit (Ollama doesn't support prefix caching)

### Rate Limit Handling and Automatic Retry

**Global Rate Limit Management**:

When using Azure OpenAI, the system automatically handles API rate limits (429 errors) with intelligent retry logic:

```python
# Global rate limit state (shared across all parallel agents)
_rate_limit_lock = threading.Lock()
_rate_limit_until = 0.0  # Timestamp when rate limit expires

# Before each Azure OpenAI call
wait_if_rate_limited()  # Blocks if any agent hit rate limit

# On 429 RateLimitError
# Default: 60 seconds if can't parse
# Parsed: parsed_seconds + 1 (e.g., "60 seconds" → 61, "120 seconds" → 121)
set_rate_limit(retry_after)  # Block ALL agents
# Then retry up to 5 times
```

**Key Features**:
- **Global coordination**: When ANY agent hits rate limit, ALL agents pause
- **Automatic retry**: Up to 5 retries with parsed retry-after duration
- **No data loss**: Retries seamlessly after waiting the required duration
- **Parallel-safe**: Thread-safe lock ensures proper coordination across parallel agents
- **Smart parsing**: Extracts retry duration from error message ("retry after 60 seconds")
- **Safety buffer**: Adds 1 second to parsed duration (60 → 61, 120 → 121)
- **Sensible default**: If parsing fails, assumes 60 seconds

**User Experience** (when Azure says "retry after 60 seconds"):
```
⚠️  Rate limit encountered. Blocking all Azure OpenAI calls for 61 seconds.
⏸️  Rate limit active. Waiting 60.8 seconds before retry...
🔄 Retry 1/5 for QA Engineer specialist after rate limit...
```

**User Experience** (when error message doesn't specify duration):
```
⚠️  Rate limit encountered. Blocking all Azure OpenAI calls for 60 seconds.
⏸️  Rate limit active. Waiting 59.7 seconds before retry...
🔄 Retry 1/5 for QA Engineer specialist after rate limit...
```

### Token Limit Safety and Tracking

**Automatic Token Limit Enforcement**:

For Azure OpenAI, the system automatically checks input token counts before each LLM invocation:

```python
# Before invoking LLM
if input_tokens > 272000:  # gpt-5-mini max input
    print(f"❌ FATAL ERROR: Token limit exceeded")
    print(f"Input tokens: {input_tokens:,}")
    print(f"Max allowed: 272,000")
    sys.exit(1)
```

**Token Tracking in stderr**:

Every agent invocation displays detailed token usage:

```
================================================================================
AGENT: Context specialist
PHASE: 2
CONVERSATION HISTORY: YES - Sees PRIOR phases history only
OWN CONTRIBUTIONS: YES - Sees own previous from PRIOR phases
INPUT TOKENS: 15,432 tokens
OUTPUT TOKENS: 387 tokens
TOTAL TOKENS: 15,819 tokens
MESSAGE COUNT: 4 messages being sent to LLM
INPUT UTILIZATION: 5.7% of 272K max
OUTPUT UTILIZATION: 0.3% of 128K max
================================================================================
```

**Benefits**:
- Prevents costly API errors from oversized requests
- Provides visibility into token consumption per agent
- Helps identify when history compression is needed
- Tracks utilization percentages for capacity planning

### Testing

**Verify Provider Selection**:

```bash
# Azure OpenAI mode
export PROVIDER=azure_openai
python main.py
# Expected: "[GRAPH] Using parallel execution (Azure OpenAI mode)"

# Ollama mode
export PROVIDER=ollama
python main.py
# Expected: "[GRAPH] Using sequential execution (Ollama mode - concurrency=1)"
```

### Benefits

1. **Performance**: 10-15x speedup with Azure OpenAI parallel execution
2. **Flexibility**: Switch providers with single environment variable
3. **Cost Control**: Use local Ollama when cost is a concern
4. **Scalability**: Easy to add more specialists without proportional time increase (Azure)
5. **Stability**: Sequential Ollama prevents VRAM issues with large models
6. **Simplicity**: Same codebase supports both modes transparently

### Future Enhancements

- Dynamic concurrency adjustment based on load
- Cost tracking for Azure OpenAI usage
- Support for additional Azure OpenAI models
- Streaming support for real-time responses

#### Rate-Limit-Triggered History Compression (Future Concept)

**Concept**: Use rate limit events as natural compression points to reduce context size and prevent cascading rate limit issues.

**How It Would Work**:
1. When ANY agent hits a 429 rate limit error
2. Wait the required duration (as currently implemented)
3. **After waiting completes**, invoke ONLY the Chair (not all specialists)
4. Chair creates a comprehensive summary of all recent discussion
5. Mark all specialist messages **before this new Chair summary** as not-visible
6. Resume normal phase execution with compressed history

**This is analogous to the existing Phase 2 compression mechanism**, but triggered dynamically by rate limits rather than phase transitions.

**Visible After Compression**:
- ✅ User messages (always visible)
- ✅ Notice messages (always visible)
- ✅ Chair's new rate-limit-triggered summary
- ✅ Any specialist messages AFTER the new Chair summary
- ❌ Specialist messages BEFORE the new Chair summary (filtered out)

**Plusses**:
1. **Prevents cascading rate limits**: Reduces context size going forward, potentially preventing future 429 errors
2. **Productive wait time**: Makes forced pause useful by compressing history
3. **Cost reduction**: Significantly lowers token usage in subsequent calls
4. **Leverages existing pattern**: Uses same compression mechanism as Phase 2 (proven architecture)
5. **Natural checkpoint**: Rate limits are natural indicators that context is getting large
6. **Maintains key information**: Chair summary preserves all important points
7. **Scales better**: Enables longer conversations without context explosion

**Negatives**:
1. **Added complexity**: More sophisticated rate limit handling logic
2. **Additional latency**: Chair invocation adds 5-10 seconds to recovery time
3. **Potential context loss**: Some nuanced details might be lost in summary
4. **Conversation flow disruption**: Specialists can't reference recent contributions they made
5. **Risk of over-compression**: Could trigger too early if rate limit hit for other reasons
6. **Chair token cost**: Summary itself uses tokens (though fewer than all specialist messages combined)
7. **Specialist confusion**: Sudden loss of visibility to recent messages could be disorienting
8. **Compression decision complexity**: Need heuristics for when compression is beneficial vs. harmful

**Implementation Considerations**:

**When to apply compression**:
- Only compress if there are enough specialist messages to warrant it (e.g., >10 messages since last compression)
- Check current context size: only compress if above threshold (e.g., >100K tokens)
- Don't compress if Chair just summarized recently (e.g., within last 5 messages)
- Consider phase: may not want to compress during critical Phase 1/2

**Chair invocation**:
- Similar to Phase 2, but with special "rate-limit-triggered compression" prompt
- Chair sees ALL messages (including those about to be filtered)
- Chair creates summary of recent discussion since last compression point
- Chair's summary becomes new compression point

**Filtering logic** (after Chair compression):
```python
# After rate limit recovery + Chair compression
for msg in messages:
    if msg.speaker in ["User", "Notice"]:
        visible = True  # Always visible
    elif msg.speaker == "Chair" and msg.timestamp >= compression_timestamp:
        visible = True  # Chair's new summary and any Chair messages after
    elif msg.timestamp >= compression_timestamp:
        visible = True  # Any specialist messages AFTER compression
    else:
        visible = False  # Specialist messages BEFORE compression (filtered)
```

**Alternative approaches**:
1. **Threshold-based**: Only compress if context exceeds X tokens
2. **Frequency-limited**: Maximum one compression per N messages
3. **Phase-aware**: Only compress during Phase 3+ (not Phase 1/2)
4. **Specialist vote**: Let specialists indicate if they want compression (unlikely to work)

**Risks to consider**:
- **Back-reference loss**: Specialists building on each other's recent points lose that context
- **Conversational coherence**: Mid-discussion compression could break logical flow
- **Debug difficulty**: Harder to trace issues when messages disappear mid-phase
- **User confusion**: If User is watching transcript, sudden compression could be confusing

**Potential refinements**:
- **Graduated compression**: Keep last N specialist messages visible, compress older ones
- **Selective compression**: Only compress messages from specialists who haven't spoken recently
- **Compression notification**: Add Notice message explaining compression occurred
- **Undo mechanism**: Allow specialists to request "show recent history" if needed

**Decision criteria** (would need to be implemented):
```python
def should_compress_on_rate_limit(state):
    """Decide if rate-limit-triggered compression is beneficial."""
    messages_since_last_compression = count_messages_since_last_chair_summary(state)
    current_tokens = estimate_context_tokens(state)
    chair_just_spoke = chair_message_in_last_n(state, n=5)
    
    # Only compress if:
    # 1. Enough messages accumulated (worthwhile)
    # 2. Context is large (approaching limits)
    # 3. Chair hasn't just summarized (avoid redundant summaries)
    return (
        messages_since_last_compression > 10 and
        current_tokens > 100000 and
        not chair_just_spoke
    )
```

**Why this is worth exploring**:

Rate limits are often a symptom of large context windows. By using rate limit events as compression triggers, the system becomes self-regulating: when context gets too large (causing rate limits), it automatically compresses to reduce future problems. This creates a negative feedback loop that could enable much longer conversations without manual intervention.

However, the trade-off between context compression and conversational coherence needs careful consideration. This feature should be **optional and configurable**, allowing users to enable it when running into rate limit issues frequently, or disable it when conversational continuity is more important than context size.

