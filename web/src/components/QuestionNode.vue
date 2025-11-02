<template>
  <!-- Show all questions from the graph, even without answers (user can dismiss if unwanted) -->
  <div class="question-node" :class="{ 'duplicate-node': isDuplicate(path) }" :style="{ marginLeft: level * 30 + 'px' }" ref="questionNodeRef" :title="isDuplicate(path) ? `Duplicate - use canonical path: ${getCanonicalPath(path)}` : ''">
    <div class="question-header" @click="toggleExpanded">
      <span v-if="directAnswers.length > 0" class="expand-icon">{{ isExpanded ? '▼' : '▶' }}</span>
      <div class="vote-badge" :class="voteBadgeClass">
        {{ netVotes >= 0 ? '+' : '' }}{{ netVotes }}
      </div>
      <span v-if="hasNewDescendants" class="new-badge">
        NEW
        <span class="new-count">{{ newDescendantsCount }}</span>
      </span>
      <span v-if="isPending" class="pending-badge-question">
        PENDING
      </span>
      <h3 class="question-text">
        <span :class="{ 'question-text-strikethrough': isDuplicate(path) }">{{ questionText }}</span>
        <span v-if="isDuplicate(path)" class="duplicate-indicator" title="Marked as duplicate by Chair">🧹</span>
      </h3>
      <div class="question-actions">
        <button 
          v-if="!isDuplicate(path)"
          @click.stop="handleQuestionVote('X')" 
          class="vote-button vote-exclude"
          :class="{ 'active': userQuestionVote === 'X' }"
          title="Dismiss this question"
        >
          ❌
        </button>
      </div>
    </div>
    <div class="question-meta">
      <span class="question-type">Type: <em>{{ questionType }}</em></span>
      <span class="vote-details">
        👍 {{ tally.upvotes || 0 }} / 👎 {{ tally.downvotes || 0 }}
        <span 
          v-if="tally.duplicates > 0" 
          class="duplicate-badge"
          title="Marked as duplicate by Chair"
        >
          🧹
        </span>
      </span>
      <span v-if="votedBy.length > 0" class="voted-by">
        Voted by: {{ votedBy.join(', ') }}
      </span>
    </div>

    <!-- Question vote comments -->
    <div v-if="getQuestionVoteComments().length > 0" class="agent-comments question-comments">
      <details class="comment-details">
        <summary class="comment-summary">
          💬 {{ getQuestionVoteComments().length }} agent response{{ getQuestionVoteComments().length !== 1 ? 's' : '' }}
        </summary>
        <div class="comment-list">
          <div 
            v-for="(comment, idx) in getQuestionVoteComments()" 
            :key="idx"
            class="comment-item"
          >
            <div class="comment-header">
              <span class="comment-vote">{{ comment.vote }}</span>
              <strong>{{ comment.specialist }}</strong>
              <span class="comment-phase">Phase {{ comment.phase }}</span>
            </div>
            <div class="comment-text">"{{ comment.comment }}"</div>
          </div>
        </div>
      </details>
    </div>

    <!-- User thoughts on question -->
    <div v-if="getUserThoughts(path).length > 0" class="user-thoughts">
      <details class="thought-details">
        <summary class="thought-summary">
          👤 Your thoughts ({{ getUserThoughts(path).length }})
        </summary>
        <div class="thought-list">
          <div 
            v-for="(thought, idx) in getUserThoughts(path)" 
            :key="idx"
            class="thought-item"
          >
            <div class="thought-header">
              <strong>{{ thought.specialist }}</strong>
              <span class="thought-time">{{ formatTimestamp(thought.timestamp) }}</span>
            </div>
            <div class="thought-text">"{{ thought.comment }}"</div>
          </div>
        </div>
      </details>
    </div>

    <!-- Add thought button and form for question (hidden for Q:open - free-text input IS the response) -->
    <div v-if="!isDuplicate(path) && questionType !== 'open'" class="add-thought-section">
      <button 
        v-if="!showQuestionThoughtForm"
        @click.stop="showQuestionThoughtForm = true"
        class="add-thought-button"
        title="Add your thought on this question"
      >
        💭 Add thought
      </button>
      <div v-if="showQuestionThoughtForm" class="thought-form">
        <textarea
          v-model="questionThoughtText"
          placeholder="Share your thoughts on this question..."
          rows="3"
          class="thought-textarea"
          @click.stop
        ></textarea>
        <div class="thought-form-actions">
          <button 
            @click.stop="submitQuestionThought"
            class="submit-thought-button"
            :disabled="!questionThoughtText.trim()"
          >
            Submit
          </button>
          <button 
            @click.stop="cancelQuestionThought"
            class="cancel-thought-button"
          >
            Cancel
          </button>
        </div>
      </div>
    </div>

    <!-- Answers (collapsible) -->
    <div v-if="isExpanded && directAnswers.length > 0" class="answers-container">
      <div v-if="questionType === 'open'" class="open-answer">
        <textarea
          v-model="questionThoughtText"
          :name="sanitizeId(path)"
          rows="3"
          placeholder="Enter your response..."
          class="open-textarea"
        ></textarea>
        <button 
          @click.stop="submitQuestionThought"
          :disabled="!questionThoughtText.trim()"
          class="submit-open-button"
        >
          Submit Response
        </button>
      </div>

      <div v-else class="answer-options">
        <div
          v-for="answerPath in directAnswers"
          :key="answerPath"
          class="answer-item"
          :class="answerBadgeClass(answerPath)"
        >
          <div class="answer-wrapper" :class="{ 'duplicate-node': isDuplicate(answerPath) }">
            <label class="answer-label" :title="isDuplicate(answerPath) ? `Duplicate - use canonical path: ${getCanonicalPath(answerPath)}` : ''">
              <input
                :type="questionType === 'single' ? 'radio' : 'checkbox'"
                :name="sanitizeId(path)"
                :value="answerPath"
                :checked="isSelected(answerPath)"
                @change="handleSelectionChange(answerPath, $event.target.checked)"
                :disabled="isDuplicate(answerPath)"
                class="answer-input"
              />
              <div class="answer-content">
                <div class="answer-header">
                <span class="vote-badge-small" :class="answerBadgeClass(answerPath)">
                  {{ getAnswerNetVotes(answerPath) >= 0 ? '+' : '' }}{{ getAnswerNetVotes(answerPath) }}
                </span>
                <span class="answer-text">
                  <span v-if="hasNewDescendantsForAnswer(answerPath)" class="new-badge">
                    NEW
                    <span class="new-count">{{ getNewDescendantsCountForAnswer(answerPath) }}</span>
                  </span>
                  <span :class="{ 'answer-text-strikethrough': isDuplicate(answerPath) }">{{ extractAnswerText(answerPath) }}</span>
                  <span v-if="isDuplicate(answerPath)" class="duplicate-indicator" title="Marked as duplicate by Chair">🧹</span>
                </span>
                <div class="answer-actions">
                  <button 
                    v-if="!isDuplicate(answerPath)"
                    @click.stop="handleAnswerVote(answerPath, 'X')" 
                    class="vote-button-small vote-exclude"
                    :class="{ 'active': getUserAnswerVote(answerPath) === 'X' }"
                    title="Dismiss this answer"
                  >
                    ❌
                  </button>
                </div>
              </div>
              <div class="answer-meta">
                👍 {{ getAnswerTally(answerPath).upvotes || 0 }} / 
                👎 {{ getAnswerTally(answerPath).downvotes || 0 }}
                <span 
                  v-if="getAnswerTally(answerPath).duplicates > 0" 
                  class="duplicate-badge"
                  title="Marked as duplicate by Chair"
                >
                  🧹
                </span>
                <span v-if="getAnswerVotedBy(answerPath).up.length > 0" class="voted-for">
                  | For: {{ getAnswerVotedBy(answerPath).up.join(', ') }}
                </span>
                <span v-if="getAnswerVotedBy(answerPath).down.length > 0" class="voted-against">
                  | Against: {{ getAnswerVotedBy(answerPath).down.join(', ') }}
                </span>
              </div>

              <!-- Agent comments/reasoning for votes -->
              <div v-if="getAnswerVoteComments(answerPath).length > 0" class="agent-comments">
                <details class="comment-details">
                  <summary class="comment-summary">
                    💬 {{ getAnswerVoteComments(answerPath).length }} agent response{{ getAnswerVoteComments(answerPath).length !== 1 ? 's' : '' }}
                  </summary>
                  <div class="comment-list">
                    <div 
                      v-for="(comment, idx) in getAnswerVoteComments(answerPath)" 
                      :key="idx"
                      class="comment-item"
                    >
                      <div class="comment-header">
                        <span v-if="['👍', '+', '✅'].includes(comment.vote)" class="comment-vote">👍</span>
                        <span v-else-if="['👎', '-', '❌'].includes(comment.vote)" class="comment-vote">👎</span>
                        <span class="comment-specialist">{{ comment.specialist }}</span>
                        <span class="comment-phase">Phase {{ comment.phase }}</span>
                      </div>
                      <div class="comment-text">
                        "{{ comment.comment }}"
                      </div>
                    </div>
                  </div>
                </details>
              </div>

              <!-- User thoughts on answer -->
              <div v-if="getUserThoughts(answerPath).length > 0" class="user-thoughts">
                <details class="thought-details">
                  <summary class="thought-summary">
                    👤 Your thoughts ({{ getUserThoughts(answerPath).length }})
                  </summary>
                  <div class="thought-list">
                    <div 
                      v-for="(thought, idx) in getUserThoughts(answerPath)" 
                      :key="idx"
                      class="thought-item"
                    >
                      <div class="thought-header">
                        <strong>{{ thought.specialist }}</strong>
                        <span class="thought-time">{{ formatTimestamp(thought.timestamp) }}</span>
                      </div>
                      <div class="thought-text">"{{ thought.comment }}"</div>
                    </div>
                  </div>
                </details>
              </div>
              </div>
            </label>

            <!-- Add thought button and form for answer (outside label to prevent checkbox toggle) -->
            <div v-if="!isDuplicate(answerPath)" class="add-thought-section">
                <button 
                  v-if="!answerThoughtForms[answerPath]"
                  @click.stop="showAnswerThoughtForm(answerPath)"
                  class="add-thought-button"
                  title="Add your thought on this answer"
                >
                  💭 Add thought
                </button>
                <div v-if="answerThoughtForms[answerPath]" class="thought-form">
                  <textarea
                    v-model="answerThoughtTexts[answerPath]"
                    placeholder="Share your thoughts on this answer..."
                    rows="3"
                    class="thought-textarea"
                    @click.stop
                  ></textarea>
                  <div class="thought-form-actions">
                    <button 
                      @click.stop="submitAnswerThought(answerPath)"
                      class="submit-thought-button"
                      :disabled="!answerThoughtTexts[answerPath] || !answerThoughtTexts[answerPath].trim()"
                    >
                      Submit
                    </button>
                    <button 
                      @click.stop="cancelAnswerThought(answerPath)"
                      class="cancel-thought-button"
                    >
                      Cancel
                    </button>
                  </div>
                </div>
              </div>

            <!-- Recursive: Follow-up questions for this answer -->
            <div v-if="getFollowUpQuestions(answerPath).length > 0" class="follow-ups">
              <QuestionNode
                v-for="followUpPath in getFollowUpQuestions(answerPath)"
                :key="followUpPath"
                :path="followUpPath"
                :graph-data="graphData"
                :vote-tally="voteTally"
                :user-selections="userSelections"
                :layer-interaction-state="layerInteractionState"
                :questions-to-force-expand="questionsToForceExpand"
                :questions-to-collapse="questionsToCollapse"
                :last-submission-timestamp="lastSubmissionTimestamp"
                :selections-at-last-submit="selectionsAtLastSubmit"
                :graph-change-log="graphChangeLog"
                :hide-duplicates="hideDuplicates"
                :is-question-pending="isQuestionPending"
                :update-question-expanded-state="updateQuestionExpandedState"
                :level="level + 1"
                @update-selection="$emit('update-selection', $event)"
                @update-vote="$emit('update-vote', $event)"
                @immediate-submit="$emit('immediate-submit', $event)"
                @submit-thought="$emit('submit-thought', $event)"
              />
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import { computed, ref, reactive, watch, onMounted, onUnmounted } from 'vue'

export default {
  name: 'QuestionNode',
  props: {
    path: {
      type: String,
      required: true
    },
    graphData: {
      type: Object,
      required: true
    },
    voteTally: {
      type: Object,
      required: true
    },
    userSelections: {
      type: Object,
      required: true
    },
    layerInteractionState: {
      type: Object,
      required: true
    },
    questionsToForceExpand: {
      type: Object,
      required: true
    },
    questionsToCollapse: {
      type: Object,
      required: true
    },
    lastSubmissionTimestamp: {
      type: Number,
      required: true
    },
    selectionsAtLastSubmit: {
      type: Object,
      required: true
    },
    graphChangeLog: {
      type: Object,
      required: true
    },
    updateQuestionExpandedState: {
      type: Function,
      required: false,
      default: () => (path, isExpanded) => {
        console.warn(`⚠️⚠️⚠️ NO-OP DEFAULT CALLED for "${path}" (isExpanded=${isExpanded})`)
      }
    },
    level: {
      type: Number,
      default: 0
    },
    hideDuplicates: {
      type: Boolean,
      default: false
    },
    isQuestionPending: {
      type: Function,
      required: true
    }
  },
  emits: ['update-selection', 'update-vote', 'immediate-submit', 'submit-thought', 'viewport-change'],
  setup(props, { emit }) {
    
    // Check if this question OR any nested questions under selected answers are pending
    const isPending = computed(() => {
      // Force Vue to track changes to selectionsAtLastSubmit (watch for any key changes)
      const submittedKeys = Object.keys(props.selectionsAtLastSubmit)
      
      // First check if this question itself is pending
      if (props.isQuestionPending(props.path)) {
        return true
      }
      
      // Then check if any nested questions under selected answers are pending
      // Only check under SELECTED answers (not all answers)
      const selection = props.selectionsAtLastSubmit[props.path]
      if (!selection) return false // No selection, so no selected answer paths to check
      
      const selectedAnswers = Array.isArray(selection.answers) ? selection.answers : [selection.answers]
      
      // For each selected answer, check if there are pending nested questions
      for (const answerPath of selectedAnswers) {
        // Build FULL answer path (answer paths in selections are SHORT, relative to parent question)
        const fullAnswerPath = props.path + answerPath
        
        // Find all nested questions under this selected answer
        for (const nodePath in props.graphData.nodes) {
          if (nodePath.startsWith(fullAnswerPath + '[Q:')) {
            // Force reactivity by directly checking conditions instead of calling isQuestionPending
            // This ensures Vue tracks all the dependencies properly
            
            // Skip if dismissed
            const nodeData = props.graphData.nodes[nodePath]
            if (!nodeData) continue
            
            const voteTally = props.voteTally[nodePath]
            if (voteTally && voteTally.user_dismissed > 0) continue
            
            // Skip if has user thoughts
            if (nodeData.user_thoughts && nodeData.user_thoughts.length > 0) continue
            
            // Skip if has submitted selection
            if (props.selectionsAtLastSubmit[nodePath]) continue
            
            // This nested question is pending!
            return true
          }
        }
      }
      
      return false
    })
    
    // Track local expansion state
    const isExpanded = ref(true)
    const userManuallyToggled = ref(false) // Track if user manually clicked this specific question
    
    // VIEWPORT-BASED PINNING: Pin only when in viewport
    // Unpin when off-screen (regardless of expansion state)
    // If user can't see it, it's safe to reorder
    const questionNodeRef = ref(null)
    const isInViewport = ref(false)
    const pinnedAnswerOrder = ref(null) // Frozen order when visible
    
    // Thought form state
    const showQuestionThoughtForm = ref(false)
    const questionThoughtText = ref('')
    const answerThoughtForms = reactive({})
    const answerThoughtTexts = reactive({})
    
    // Helper to get layer path for this question
    function getLayerPath() {
      const matches = props.path.match(/^(.*?)(\[Q:[^\]]+\]\[[^\]]+\])$/)
      return matches ? matches[1] : ''
    }
    
    const questionType = computed(() => {
      const match = props.path.match(/\[Q:(single|multiple|open)\]/)
      return match ? match[1] : 'single'
    })

    const questionText = computed(() => {
      // Parse brackets iteratively
      const brackets = []
      let i = 0
      const path = props.path
      while (i < path.length) {
        if (path[i] === '[') {
          const end = path.indexOf(']', i)
          if (end === -1) break
          brackets.push(path.substring(i + 1, end))
          i = end + 1
        } else {
          i++
        }
      }
      
      // Find LAST [Q:type] followed by text (for nested questions, we want the actual question, not parent)
      let questionText = null
      for (let i = 0; i < brackets.length; i++) {
        if (brackets[i].startsWith('Q:')) {
          if (i + 1 < brackets.length) {
            const nextBracket = brackets[i + 1]
            // Question text should not be a structural marker
            if (!nextBracket.startsWith('Q:') && 
                !nextBracket.startsWith('A:') && 
                nextBracket !== 'A') {
              questionText = nextBracket  // Keep updating to get the last one
            }
          }
        }
      }
      
      if (questionText) return questionText
      
      return props.path
    })

    const tally = computed(() => {
      return props.graphData.vote_tally[props.path] || { upvotes: 0, downvotes: 0, up_by: [], down_by: [] }
    })

    const netVotes = computed(() => {
      return (tally.value.upvotes || 0) - (tally.value.downvotes || 0)
    })

    const voteBadgeClass = computed(() => {
      if (netVotes.value >= 3) return 'badge-strong-positive'
      if (netVotes.value > 0) return 'badge-positive'
      if (netVotes.value <= -3) return 'badge-strong-negative'
      if (netVotes.value < 0) return 'badge-negative'
      return 'badge-neutral'
    })

    // Check if this question has new descendants (at any depth)
    const hasNewDescendants = computed(() => {
      const count = props.graphChangeLog.recursiveNewCounts[props.path] || 0
      return count > 0
    })
    
    // Get the count of new descendants for this question
    const newDescendantsCount = computed(() => {
      return props.graphChangeLog.recursiveNewCounts[props.path] || 0
    })
    
    // Check if an answer has new descendants (at any depth)
    function hasNewDescendantsForAnswer(answerPath) {
      const count = props.graphChangeLog.recursiveNewCounts[answerPath] || 0
      return count > 0
    }
    
    // Get the count of new descendants for an answer
    function getNewDescendantsCountForAnswer(answerPath) {
      return props.graphChangeLog.recursiveNewCounts[answerPath] || 0
    }

    const votedBy = computed(() => {
      const up = tally.value.up_by || []
      const down = tally.value.down_by || []
      return [...new Set([...up, ...down])]
    })

    function isNodeXed(path) {
      // Check if node has been marked with [❌] (dismissed)
      // First check user's pending vote (optimistic UI)
      const userVote = props.userSelections[`vote:${path}`]
      if (userVote === 'X' || userVote === '❌') return true
      
      // Then check backend data
      const node = props.graphData.nodes[path]
      if (!node || !node.votes) return false
      return node.votes.some(vote => vote.vote === '❌' || vote.vote === 'X')
    }

    const directAnswers = computed(() => {
      const qPath = props.path
      const shouldHideDupes = props.hideDuplicates
      const answers = []
      
      for (const path in props.graphData.nodes) {
        if (!path.startsWith(qPath + '[A')) continue
        
        // Parse to check if this is actually a direct answer (not a nested question)
        // Direct answer: [Question][A][AnswerText] - ends there OR has nested content
        // NOT an answer: [Question][A][AnswerText][Q:...] - this is a question node
        
        const afterQuestion = path.substring(qPath.length)
        
        // Parse brackets to find structure
        const brackets = []
        let i = 0
        while (i < afterQuestion.length) {
          if (afterQuestion[i] === '[') {
            const end = afterQuestion.indexOf(']', i)
            if (end === -1) break
            brackets.push(afterQuestion.substring(i + 1, end))
            i = end + 1
          } else {
            i++
          }
        }
        
        // Direct answer must have: [A or A:type][text], not followed by [Q:...]
        if (brackets.length >= 2 && 
            (brackets[0] === 'A' || brackets[0].startsWith('A:')) &&
            !brackets[0].startsWith('Q:')) {
          // Check if this is a question node (has Q: after the answer text)
          const isQuestionNode = brackets.length > 2 && brackets[2] && brackets[2].startsWith('Q:')
          
          // Filter out question nodes, X'd nodes, and duplicates
          if (isQuestionNode || isNodeXed(path)) continue
          if (shouldHideDupes && isDuplicate(path)) continue
          
          answers.push(path)
        }
      }
      
      // VIEWPORT PINNING: If question is in viewport, freeze the answer list
      // Do NOT add new nodes while user is viewing this question
      if (isInViewport.value && pinnedAnswerOrder.value && pinnedAnswerOrder.value.length > 0) {
        // Return pinned answers + any NEW answers not in pinned list (same fix as root questions)
        const pinnedStillExist = pinnedAnswerOrder.value.filter(a => answers.includes(a))
        const pinnedSet = new Set(pinnedStillExist)
        const newAnswers = answers.filter(a => !pinnedSet.has(a))
        const result = [...pinnedStillExist, ...newAnswers]
        return result
      }
      
      // Off-screen - compute fresh sorted order
      // Sort answers with user selection priority (only from last submit, not current selections)
      const sorted = answers.sort((a, b) => {
        // Use selections from LAST SUBMIT, not current selections
        // This prevents jarring reordering while user is still deciding
        const submittedSelection = props.selectionsAtLastSubmit ? props.selectionsAtLastSubmit[props.path] : null
        
        // Check if nodes have new content (self or descendants not yet seen)
        const aHasNew = hasNewDescendantsForAnswer(a)
        const bHasNew = hasNewDescendantsForAnswer(b)
        
        // New nodes go at the end (after existing nodes)
        // This prevents disruption while user is still deciding
        if (aHasNew && !bHasNew) return 1   // a has new, goes after b
        if (bHasNew && !aHasNew) return -1  // b has new, goes after a
        
        // If both new or both existing, continue with normal sorting
        
        // For single-choice: user's submitted selection comes first
        if (questionType.value === 'single' && submittedSelection) {
          const aIsSelected = submittedSelection.answers === a
          const bIsSelected = submittedSelection.answers === b
          
          if (aIsSelected && !bIsSelected) return -1  // a selected, comes first
          if (bIsSelected && !aIsSelected) return 1   // b selected, comes first
          // If neither or both selected, fall through to vote sorting
        }
        
        // For multiple-choice: all user's submitted selections come first (as a group)
        if (questionType.value === 'multiple' && submittedSelection && Array.isArray(submittedSelection.answers)) {
          const aIsSelected = submittedSelection.answers.includes(a)
          const bIsSelected = submittedSelection.answers.includes(b)
          
          if (aIsSelected && !bIsSelected) return -1  // a selected, comes first
          if (bIsSelected && !aIsSelected) return 1   // b selected, comes first
          // If both selected or both unselected, fall through to vote sorting
        }
        
        // Sort by net votes (highest first)
        const aNet = getAnswerNetVotes(a)
        const bNet = getAnswerNetVotes(b)
        if (bNet !== aNet) return bNet - aNet
        
        // Tiebreaker: newest first (higher timestamp = more recent)
        // Extract timestamp from node if available
        const aNode = props.graphData.nodes[a]
        const bNode = props.graphData.nodes[b]
        const aTime = aNode?.timestamp || 0
        const bTime = bNode?.timestamp || 0
        return bTime - aTime  // Newer nodes first
      })
      
      // Update pinned order based on viewport visibility
      if (isInViewport.value) {
        // In viewport - only update if we don't have a pinned order yet
        if (!pinnedAnswerOrder.value) {
          pinnedAnswerOrder.value = sorted
        }
      } else {
        // Off-screen - update with latest sort
        // This is when reordering happens (user can't see it)
        pinnedAnswerOrder.value = sorted
      }
      
      return sorted
    })

    function getFollowUpQuestions(answerPath) {
      const questions = []
      const shouldHideDupes = props.hideDuplicates
      
      // Helper: count Q and A markers by parsing brackets character by character
      function countQADepth(str) {
        const brackets = []
        let i = 0
        while (i < str.length) {
          if (str[i] === '[') {
            const end = str.indexOf(']', i)
            if (end === -1) break
            brackets.push(str.substring(i + 1, end))
            i = end + 1
          } else {
            i++
          }
        }
        
        // Count Q: and A (with or without :type)
        let count = 0
        for (const bracket of brackets) {
          if (bracket.startsWith('Q:') || bracket === 'A' || bracket.startsWith('A:')) {
            count++
          }
        }
        return count
      }
      
      for (const path in props.graphData.nodes) {
        if (!path.startsWith(answerPath + '[Q:')) continue
        
        const baseDepth = countQADepth(answerPath)
        const pathDepth = countQADepth(path)
        
        // Direct child: exactly one level deeper
        // Filter out dismissed questions (user doesn't want to see them anymore)
        if (pathDepth !== baseDepth + 1 || isNodeXed(path)) continue
        
        // Filter out duplicates if hideDuplicates is enabled
        if (shouldHideDupes && isDuplicate(path)) {
          continue
        }
        
        questions.push(path)
      }
      
      // Sort by net votes (highest first)
      return questions.sort((a, b) => {
        const aTally = props.graphData.vote_tally[a] || {}
        const bTally = props.graphData.vote_tally[b] || {}
        const aNet = (aTally.upvotes || 0) - (aTally.downvotes || 0)
        const bNet = (bTally.upvotes || 0) - (bTally.downvotes || 0)
        return bNet - aNet
      })
    }
    
    // Helper: Gather metrics about this question for logging
    function getQuestionMetrics() {
      const answers = directAnswers.value
      const answerCount = answers.length
      
      // Count nested questions across all answers
      let nestedQuestionCount = 0
      for (const answer of answers) {
        nestedQuestionCount += getFollowUpQuestions(answer.path).length
      }
      
      // Get NEW count from graphChangeLog
      const newCount = props.graphChangeLog?.recursiveNewCounts?.[props.path] || 0
      
      // Get vote tally for this question
      const questionNode = props.graphData.nodes[props.path]
      const voteStats = questionNode?.vote_tally || { '👍': 0, '👎': 0, '❌': 0 }
      
      return {
        answers: answerCount,
        nestedQuestions: nestedQuestionCount,
        newCount: newCount,
        votes: `👍${voteStats['👍']} 👎${voteStats['👎']} ❌${voteStats['❌']}`
      }
    }
    
    function toggleExpanded() {
      const beforeExpanded = isExpanded.value
      const metrics = getQuestionMetrics()
      
      isExpanded.value = !isExpanded.value
      userManuallyToggled.value = true // Mark that user manually toggled THIS question
      
      console.log(`👤 User manually ${isExpanded.value ? 'expanded' : 'collapsed'}: "${props.path}"`)
      console.log(`  📊 Before: expanded=${beforeExpanded} | ${metrics.answers} answers, ${metrics.nestedQuestions} nested Q's | NEW=${metrics.newCount} | ${metrics.votes}`)
      console.log(`  📊 After:  expanded=${isExpanded.value} | (composition unchanged) | NEW=${metrics.newCount} | ${metrics.votes}`)
      
      // Don't affect layer state - each question is independent for manual toggles
    }
    
    // Watch for layer state changes to determine if we should collapse/expand
    // BUT only if user hasn't manually toggled this specific question
    watch(() => {
      const layerPath = getLayerPath()
      const layerState = props.layerInteractionState[layerPath]
      // Watch both questionsToForceExpand and questionsToCollapse for changes
      // Both are now objects with timestamps (not Sets) for reliable Vue 3 reactivity
      return { 
        layerState: layerState ? { ...layerState } : null,
        forceExpandTimestamp: props.questionsToForceExpand ? props.questionsToForceExpand[props.path] : null,
        collapseTimestamp: props.questionsToCollapse ? props.questionsToCollapse[props.path] : null
      }
    }, ({ layerState, forceExpandTimestamp, collapseTimestamp }) => {
      const beforeExpanded = isExpanded.value
      const beforeMetrics = getQuestionMetrics()
      
      // PRIORITY 1: Force-expand if this question has NEW descendants
      // (This overrides everything, including manual collapse)
      if (forceExpandTimestamp) {
        console.log(`🔓 Auto-expanding question with NEW items: "${props.path}"`)
        console.log(`  📊 Before: expanded=${beforeExpanded} | ${beforeMetrics.answers} answers, ${beforeMetrics.nestedQuestions} nested Q's | NEW=${beforeMetrics.newCount} | ${beforeMetrics.votes}`)
        isExpanded.value = true
        userManuallyToggled.value = false
        console.log(`  📊 After:  expanded=${isExpanded.value} | (composition unchanged) | NEW=${beforeMetrics.newCount} | ${beforeMetrics.votes}`)
        return
      }
      
      // PRIORITY 2: Collapse if user interacted with this question on submit
      // If collapseTimestamp exists (truthy), user interacted with this question
      if (collapseTimestamp) {
        // If user manually toggled this question, respect that
        if (!userManuallyToggled.value) {
          console.log(`📦 Auto-collapsing interacted question: "${props.path}"`)
          console.log(`  📊 Before: expanded=${beforeExpanded} | ${beforeMetrics.answers} answers, ${beforeMetrics.nestedQuestions} nested Q's | NEW=${beforeMetrics.newCount} | ${beforeMetrics.votes}`)
          isExpanded.value = false
          console.log(`  📊 After:  expanded=${isExpanded.value} | (composition unchanged) | NEW=${beforeMetrics.newCount} | ${beforeMetrics.votes}`)
        } else {
          console.log(`📦 Skipping auto-collapse for: "${props.path}" (user manually toggled, respecting their choice)`)
        }
        return
      }
      
      // PRIORITY 3: If user manually toggled this question, RESPECT IT
      // Don't auto-expand/collapse based on layer state or other logic
      if (userManuallyToggled.value) {
        // Only log if state would have changed (avoid spam)
        return
      }
      
      // PRIORITY 4: Apply layer-based collapse logic (for questions user hasn't touched)
      // BUT: If ANY collapse directives are active, skip layer-based logic entirely
      // (we're in post-submit cleanup phase, don't interfere)
      const anyCollapseDirectivesActive = collapseTimestamp || Object.keys(props.questionsToCollapse || {}).length > 0
      
      if (anyCollapseDirectivesActive) {
        // We're in post-submit cleanup - don't run layer-based expansion/collapse
        // Let the collapse directives and current state handle everything
        return
      }
      
      if (!layerState) {
        // No tracking for this layer - default to expanded for new questions
        if (!beforeExpanded) {
          console.log(`📂 Defaulting to expanded (no layer tracking): "${props.path}"`)
          console.log(`  📊 Before: expanded=${beforeExpanded} | ${beforeMetrics.answers} answers, ${beforeMetrics.nestedQuestions} nested Q's | NEW=${beforeMetrics.newCount} | ${beforeMetrics.votes}`)
        }
        isExpanded.value = true
        return
      }
      
      // Legacy layer-based collapse logic (for dismissed nodes, etc.)
      // Check if this node existed at first click
      const existedAtFirstClick = layerState.nodesAtFirstClick && layerState.nodesAtFirstClick.has(props.path)
      
      if (existedAtFirstClick) {
        // This node existed when user first clicked in this layer
        if (layerState.shouldCollapse) {
          // User submitted - collapse nodes that existed at first click
          if (beforeExpanded) {
            console.log(`📦 Layer-based collapse (existed at first click): "${props.path}"`)
            console.log(`  📊 Before: expanded=${beforeExpanded} | ${beforeMetrics.answers} answers, ${beforeMetrics.nestedQuestions} nested Q's | NEW=${beforeMetrics.newCount} | ${beforeMetrics.votes}`)
          }
          isExpanded.value = false
        }
      } else {
        // This is a NEW node that appeared after first click - expand it
        if (!beforeExpanded) {
          console.log(`🆕 Layer-based expand (appeared after first click): "${props.path}"`)
          console.log(`  📊 Before: expanded=${beforeExpanded} | ${beforeMetrics.answers} answers, ${beforeMetrics.nestedQuestions} nested Q's | NEW=${beforeMetrics.newCount} | ${beforeMetrics.votes}`)
          isExpanded.value = true
        }
      }
    }, { deep: true, immediate: true })
    
    // Report expanded state changes to parent (for collapse logic)
    watch(isExpanded, (newValue) => {
      console.log(`📡 Watcher fired for "${props.path}": expanded=${newValue}`)
      console.log(`  🔎 Function check: exists=${!!props.updateQuestionExpandedState}, type=${typeof props.updateQuestionExpandedState}, name="${props.updateQuestionExpandedState?.name}"`)
      if (props.updateQuestionExpandedState && typeof props.updateQuestionExpandedState === 'function') {
        try {
          console.log(`  🔄 Calling updateQuestionExpandedState...`)
          const result = props.updateQuestionExpandedState(props.path, newValue)
          console.log(`  ✅ Called successfully, returned:`, result)
        } catch (err) {
          console.error(`❌ Error reporting expanded state for "${props.path}":`, err)
        }
      } else {
        console.warn(`⚠️  updateQuestionExpandedState not available for "${props.path}"`, {
          exists: !!props.updateQuestionExpandedState,
          type: typeof props.updateQuestionExpandedState
        })
      }
    }, { immediate: true })
    
    // Clear manual toggle flag when user submits
    // This allows auto-collapse to work on next submission even if user manually toggled before
    watch(() => props.lastSubmissionTimestamp, () => {
      if (userManuallyToggled.value) {
        console.log(`🔄 Clearing manual-toggle flag for "${props.path}" (submission complete)`)
        userManuallyToggled.value = false
      }
    })

    function extractAnswerText(path) {
      // Parse brackets iteratively instead of complex regex
      const brackets = []
      let i = 0
      while (i < path.length) {
        if (path[i] === '[') {
          const end = path.indexOf(']', i)
          if (end === -1) break
          brackets.push(path.substring(i + 1, end))
          i = end + 1
        } else {
          i++
        }
      }
      
      // Find last [A] or [A:type] followed by text
      for (let i = brackets.length - 1; i >= 0; i--) {
        const bracket = brackets[i]
        if (bracket === 'A' || bracket.startsWith('A:')) {
          // Check if next bracket is the answer text (not another marker)
          if (i + 1 < brackets.length) {
            const nextBracket = brackets[i + 1]
            // Answer text should not be a structural marker
            if (!nextBracket.startsWith('Q:') && 
                !nextBracket.startsWith('A:') && 
                nextBracket !== 'A') {
              return nextBracket
            }
          }
        }
      }
      
      // Fallback: if no answer found, return the path
      return path
    }

    function getAnswerTally(answerPath) {
      return props.graphData.vote_tally[answerPath] || { upvotes: 0, downvotes: 0, up_by: [], down_by: [] }
    }

    function getAnswerNetVotes(answerPath) {
      const tally = getAnswerTally(answerPath)
      return (tally.upvotes || 0) - (tally.downvotes || 0)
    }

    function getAnswerVotedBy(answerPath) {
      const tally = getAnswerTally(answerPath)
      return {
        up: [...new Set(tally.up_by || [])],
        down: [...new Set(tally.down_by || [])]
      }
    }

    function getAnswerVoteComments(answerPath) {
      const node = props.graphData.nodes[answerPath]
      if (!node || !node.votes) return []
      
      return node.votes
        .filter(v => v.comment)
        .map(v => ({
          specialist: v.specialist,
          vote: v.vote,
          comment: v.comment,
          phase: v.phase,
          timestamp: v.timestamp
        }))
    }

    function getQuestionVoteComments() {
      const node = props.graphData.nodes[props.path]
      if (!node || !node.votes) return []
      
      return node.votes
        .filter(v => v.comment)
        .map(v => ({
          specialist: v.specialist,
          vote: v.vote,
          comment: v.comment,
          phase: v.phase,
          timestamp: v.timestamp
        }))
    }

    function getUserThoughts(nodePath) {
      const node = props.graphData.nodes[nodePath]
      if (!node || !node.user_thoughts) return []
      return node.user_thoughts
    }

    function formatTimestamp(timestamp) {
      // Parse timestamp like "2025-10-26 14:48:09.674"
      if (!timestamp) return ''
      try {
        const parts = timestamp.split(' ')
        if (parts.length >= 2) {
          const timePart = parts[1].split(':')
          return `${timePart[0]}:${timePart[1]}`  // HH:MM
        }
        return timestamp
      } catch (e) {
        return timestamp
      }
    }

    function answerBadgeClass(answerPath) {
      const net = getAnswerNetVotes(answerPath)
      if (net >= 3) return 'badge-strong-positive'
      if (net > 0) return 'badge-positive'
      if (net <= -3) return 'badge-strong-negative'
      if (net < 0) return 'badge-negative'
      return 'badge-neutral'
    }

    function isSelected(answerPath) {
      const selection = props.userSelections[props.path]
      if (!selection) return false
      
      if (selection.type === 'single') {
        return selection.answers === answerPath
      } else {
        return (selection.answers || []).includes(answerPath)
      }
    }
    
    function isDuplicate(nodePath) {
      if (!props.voteTally || !nodePath) return false
      const tally = props.voteTally[nodePath]
      return tally && tally.duplicates > 0
    }
    
    function getCanonicalPath(nodePath) {
      // Get the canonical path for a duplicate node
      if (!props.voteTally || !nodePath) return null
      const tally = props.voteTally[nodePath]
      return tally && tally.canonical_path ? tally.canonical_path : null
    }

    function handleSelectionChange(answerPath, checked) {
      emit('update-selection', {
        questionPath: props.path,
        answerPath: answerPath,
        selected: checked,
        isMultiple: questionType.value === 'multiple'
      })
    }

    function sanitizeId(path) {
      return path.replace(/[^\w-]/g, '_')
    }

    // Track user votes (separate from selections)
    const userQuestionVote = computed(() => {
      return props.userSelections[`vote:${props.path}`]
    })

    function getUserAnswerVote(answerPath) {
      return props.userSelections[`vote:${answerPath}`]
    }

    function handleQuestionVote(voteType) {
      // Toggle vote if clicking the same button, otherwise set new vote
      const currentVote = userQuestionVote.value
      const newVote = currentVote === voteType ? null : voteType
      
      emit('update-vote', {
        path: props.path,
        vote: newVote
      })
      
      // Auto-submit dismissals immediately
      if (voteType === 'X' && newVote === 'X') {
        emit('immediate-submit', {
          path: props.path,
          vote: '❌'
        })
      }
    }

    function handleAnswerVote(answerPath, voteType) {
      // Toggle vote if clicking the same button, otherwise set new vote
      const currentVote = getUserAnswerVote(answerPath)
      const newVote = currentVote === voteType ? null : voteType
      
      emit('update-vote', {
        path: answerPath,
        vote: newVote
      })
      
      // Auto-submit dismissals and duplicates immediately
      if (voteType === 'X' && newVote === 'X') {
        emit('immediate-submit', {
          path: answerPath,
          vote: '❌'
        })
      }
      if (voteType === '🧹' && newVote === '🧹') {
        emit('immediate-submit', {
          path: answerPath,
          vote: '🧹'
        })
      }
    }

    // Thought form methods for question
    function submitQuestionThought() {
      if (!questionThoughtText.value.trim()) return
      
      emit('submit-thought', {
        path: props.path,
        comment: questionThoughtText.value.trim()
      })
      
      // Reset form
      questionThoughtText.value = ''
      // For Q:open, keep textarea visible; for others, hide the form
      if (questionType.value !== 'open') {
        showQuestionThoughtForm.value = false
      }
    }

    function cancelQuestionThought() {
      questionThoughtText.value = ''
      showQuestionThoughtForm.value = false
    }

    // Thought form methods for answers
    function showAnswerThoughtForm(answerPath) {
      answerThoughtForms[answerPath] = true
      answerThoughtTexts[answerPath] = ''
    }

    function submitAnswerThought(answerPath) {
      const text = answerThoughtTexts[answerPath]
      if (!text || !text.trim()) return
      
      emit('submit-thought', {
        path: answerPath,
        comment: text.trim()
      })
      
      // Reset form
      delete answerThoughtTexts[answerPath]
      delete answerThoughtForms[answerPath]
    }

    function cancelAnswerThought(answerPath) {
      delete answerThoughtTexts[answerPath]
      delete answerThoughtForms[answerPath]
    }

    // Set up Intersection Observer to detect viewport visibility
    let intersectionObserver = null
    
    onMounted(() => {
      if (questionNodeRef.value) {
        // Create observer - consider visible if any part is in viewport
        intersectionObserver = new IntersectionObserver(
          (entries) => {
            entries.forEach(entry => {
              const wasVisible = isInViewport.value
              isInViewport.value = entry.isIntersecting
              
              // Log visibility changes
              if (!wasVisible && entry.isIntersecting) {
                console.log(`👁️ Entered viewport: "${props.path}" - pinning answer order`)
                // Pin current order when entering viewport
                pinnedAnswerOrder.value = directAnswers.value.slice()
                // Emit to parent (only for root questions - level 0)
                if (props.level === 0) {
                  emit('viewport-change', { path: props.path, inViewport: true })
                }
              } else if (wasVisible && !entry.isIntersecting) {
                console.log(`🙈 Left viewport: "${props.path}" - allowing reordering`)
                // Emit to parent (only for root questions - level 0)
                if (props.level === 0) {
                  emit('viewport-change', { path: props.path, inViewport: false })
                }
              }
            })
          },
          {
            threshold: 0, // Trigger as soon as any part enters/leaves viewport
            rootMargin: '100px' // Add 100px buffer - start pinning slightly before visible
          }
        )
        
        intersectionObserver.observe(questionNodeRef.value)
      }
    })
    
    onUnmounted(() => {
      if (intersectionObserver && questionNodeRef.value) {
        intersectionObserver.unobserve(questionNodeRef.value)
        intersectionObserver.disconnect()
      }
    })

    return {
      isExpanded,
      toggleExpanded,
      questionType,
      questionText,
      tally,
      netVotes,
      voteBadgeClass,
      votedBy,
      isPending,
      hasNewDescendants,
      newDescendantsCount,
      hasNewDescendantsForAnswer,
      getNewDescendantsCountForAnswer,
      directAnswers,
      getFollowUpQuestions,
      extractAnswerText,
      getAnswerTally,
      getAnswerNetVotes,
      getAnswerVotedBy,
      getAnswerVoteComments,
      getQuestionVoteComments,
      getUserThoughts,
      formatTimestamp,
      answerBadgeClass,
      isSelected,
      handleSelectionChange,
      sanitizeId,
      userQuestionVote,
      getUserAnswerVote,
      handleQuestionVote,
      handleAnswerVote,
      showQuestionThoughtForm,
      questionThoughtText,
      answerThoughtForms,
      answerThoughtTexts,
      submitQuestionThought,
      cancelQuestionThought,
      showAnswerThoughtForm,
      submitAnswerThought,
      cancelAnswerThought,
      questionNodeRef,
      isDuplicate,
      getCanonicalPath
    }
  }
}
</script>

<style scoped>
.question-node {
  background: white;
  border-radius: 8px;
  padding: 0.75rem;
  margin-bottom: 0.75rem;
  border-left: 4px solid #4a90e2;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
  transition: transform 0.2s, box-shadow 0.2s;
}

.question-node:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 8px rgba(0, 0, 0, 0.15);
}

.question-header {
  display: flex;
  align-items: flex-start;
  gap: 0.5rem;
  margin-bottom: 0.5rem;
  cursor: pointer;
  user-select: none;
}

.expand-icon {
  font-size: 0.875rem;
  color: #4a90e2;
  padding-top: 0.25rem;
  transition: transform 0.2s;
}

.vote-badge {
  padding: 0.25rem 0.75rem;
  border-radius: 6px;
  font-weight: 600;
  font-size: 0.875rem;
  color: white;
  min-width: 50px;
  text-align: center;
  flex-shrink: 0;
}

.badge-strong-positive {
  background: #48bb78;
}

.badge-positive {
  background: #38b2ac;
}

.badge-neutral {
  background: #718096;
}

.badge-negative {
  background: #fc8181;
}

.badge-strong-negative {
  background: #f56565;
}

.question-text {
  font-size: 1.125rem;
  font-weight: 600;
  margin: 0;
  color: #2d3748;
  flex: 1;
  line-height: 1.5;
}

.new-badge {
  display: inline-flex;
  align-items: center;
  gap: 0.25rem;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  font-size: 0.625rem;
  font-weight: 700;
  padding: 0.15rem 0.4rem;
  border-radius: 4px;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  box-shadow: 0 2px 4px rgba(102, 126, 234, 0.3);
  animation: pulse-new 2s ease-in-out infinite;
  flex-shrink: 0;
  margin-top: 0.15rem;
}

.new-count {
  display: inline-block;
  background: rgba(255, 255, 255, 0.25);
  padding: 0.1rem 0.35rem;
  border-radius: 10px;
  font-size: 0.6rem;
  font-weight: 800;
  min-width: 1.2rem;
  text-align: center;
}

@keyframes pulse-new {
  0%, 100% {
    opacity: 1;
    transform: scale(1);
  }
  50% {
    opacity: 0.85;
    transform: scale(1.05);
  }
}

.pending-badge-question {
  display: inline-flex;
  align-items: center;
  background: linear-gradient(135deg, #f59e0b 0%, #d97706 100%);
  color: white;
  font-size: 0.625rem;
  font-weight: 700;
  padding: 0.15rem 0.4rem;
  border-radius: 4px;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  box-shadow: 0 2px 4px rgba(245, 158, 11, 0.3);
  animation: pulse-pending 2s ease-in-out infinite;
  flex-shrink: 0;
  margin-top: 0.15rem;
}

@keyframes pulse-pending {
  0%, 100% {
    opacity: 1;
    transform: scale(1);
  }
  50% {
    opacity: 0.85;
    transform: scale(1.05);
  }
}

.question-meta {
  display: flex;
  gap: 0.5rem;
  flex-wrap: wrap;
  font-size: 0.875rem;
  color: #718096;
  margin-bottom: 0.5rem;
  margin-left: 4rem;
}

.question-type em {
  color: #4a5568;
  font-style: normal;
  font-weight: 500;
}

.vote-details {
  color: #4a5568;
}

.voted-by {
  color: #4a5568;
}

.duplicate-badge {
  display: inline-block;
  margin-left: 8px;
  padding: 2px 6px;
  background-color: #bee3f8;
  border-radius: 4px;
  font-size: 0.9rem;
  cursor: help;
  transition: background-color 0.2s;
}

.duplicate-badge:hover {
  background-color: #90cdf4;
}

.question-actions {
  display: flex;
  gap: 0.5rem;
  align-self: flex-start;
  margin-left: auto;
}

.vote-button {
  background: white;
  border: 2px solid #e2e8f0;
  border-radius: 6px;
  padding: 0.5rem 0.75rem;
  cursor: pointer;
  font-size: 1.25rem;
  transition: all 0.2s;
}

.vote-button:hover {
  background: #f7fafc;
  border-color: #cbd5e0;
  transform: scale(1.1);
}

.vote-button.vote-up.active {
  background: #c6f6d5;
  border-color: #48bb78;
}

.vote-button.vote-down.active {
  background: #fed7d7;
  border-color: #f56565;
}

.vote-button.vote-exclude.active {
  background: #feebc8;
  border-color: #ed8936;
}

.vote-button.vote-duplicate.active {
  background: #e6f3ff;
  border-color: #4299e1;
}

.answers-container {
  margin-top: 0.5rem;
}

.open-answer {
  margin-top: 0.5rem;
}

.open-textarea {
  width: 100%;
  max-width: 600px;
  padding: 0.75rem;
  border: 1px solid #cbd5e0;
  border-radius: 6px;
  font-family: inherit;
  font-size: 0.9375rem;
  resize: vertical;
}

.open-textarea:focus {
  outline: none;
  border-color: #4a90e2;
  box-shadow: 0 0 0 3px rgba(74, 144, 226, 0.1);
}

.answer-options {
  display: flex;
  flex-direction: column;
  gap: 0.4rem;
}

.answer-item {
  border-radius: 6px;
  border-left: 4px solid #cbd5e0;
  background: #f7fafc;
  transition: all 0.2s;
}

.answer-item.badge-strong-positive {
  border-left-color: #48bb78;
}

.answer-item.badge-positive {
  border-left-color: #38b2ac;
}

.answer-item.badge-neutral {
  border-left-color: #718096;
}

.answer-item.badge-negative {
  border-left-color: #fc8181;
}

.answer-item.badge-strong-negative {
  border-left-color: #f56565;
}

.answer-item:hover {
  background: #edf2f7;
}

.answer-label {
  display: flex;
  padding: 0.4rem;
  cursor: pointer;
  width: 100%;
}

.answer-input {
  margin-top: 0.25rem;
  margin-right: 0.75rem;
  cursor: pointer;
  width: 18px;
  height: 18px;
  flex-shrink: 0;
}

.answer-content {
  flex: 1;
}

.answer-header {
  display: flex;
  gap: 0.5rem;
  align-items: flex-start;
  margin-bottom: 0.25rem;
  flex-wrap: wrap;
}

.vote-badge-small {
  padding: 0.125rem 0.5rem;
  border-radius: 4px;
  font-weight: 600;
  font-size: 0.75rem;
  color: white;
  flex-shrink: 0;
  margin-top: 0.1rem;
}

.answer-text {
  font-weight: 500;
  color: #2d3748;
  flex: 1;
  display: flex;
  align-items: flex-start;
  gap: 0.5rem;
  line-height: 1.5;
}

.answer-actions {
  display: flex;
  gap: 0.25rem;
  margin-left: auto;
}

.vote-button-small {
  background: white;
  border: 1px solid #e2e8f0;
  border-radius: 4px;
  padding: 0.25rem 0.5rem;
  cursor: pointer;
  font-size: 1rem;
  transition: all 0.2s;
}

.vote-button-small:hover {
  background: #f7fafc;
  border-color: #cbd5e0;
  transform: scale(1.15);
}

.vote-button-small.vote-up.active {
  background: #c6f6d5;
  border-color: #48bb78;
}

.vote-button-small.vote-down.active {
  background: #fed7d7;
  border-color: #f56565;
}

.vote-button-small.vote-exclude.active {
  background: #feebc8;
  border-color: #ed8936;
}

.answer-meta {
  font-size: 0.8125rem;
  color: #718096;
  margin-top: 0.25rem;
}

.voted-for {
  color: #48bb78;
}

.voted-against {
  color: #f56565;
}

.follow-ups {
  margin-top: 1rem;
  padding-top: 1rem;
  border-top: 1px solid #e2e8f0;
}

/* Agent Comments Styles */
.agent-comments {
  margin-top: 0.75rem;
  margin-left: 1.75rem;
}

.comment-details {
  cursor: pointer;
}

.comment-summary {
  font-size: 0.85rem;
  color: #718096;
  user-select: none;
  list-style: none;
  padding: 0.25rem 0;
}

.comment-summary:hover {
  color: #4a5568;
}

.comment-summary::-webkit-details-marker {
  display: none;
}

.comment-list {
  margin-top: 0.5rem;
  padding: 0.5rem;
  background: white;
  border-radius: 6px;
  border-left: 3px solid #e2e8f0;
}

.comment-item {
  margin-bottom: 0.5rem;
  padding: 0.5rem;
  background: #f7fafc;
  border-radius: 4px;
}

.comment-item:last-child {
  margin-bottom: 0;
}

.comment-header {
  font-size: 0.8rem;
  display: flex;
  align-items: center;
  gap: 0.5rem;
  margin-bottom: 0.25rem;
}

.comment-vote {
  font-size: 1rem;
}

.comment-specialist {
  font-weight: 600;
  color: #2d3748;
}

.comment-phase {
  color: #a0aec0;
  margin-left: auto;
}

.comment-text {
  font-size: 0.85rem;
  color: #4a5568;
  line-height: 1.5;
  font-style: italic;
}

/* User Thoughts Styles */
.user-thoughts {
  margin-top: 0.75rem;
  margin-left: 1.75rem;
}

.thought-details {
  cursor: pointer;
}

.thought-summary {
  font-size: 0.85rem;
  color: #5a67d8;
  user-select: none;
  list-style: none;
  padding: 0.25rem 0;
}

.thought-summary:hover {
  color: #4c51bf;
}

.thought-summary::-webkit-details-marker {
  display: none;
}

.thought-list {
  margin-top: 0.5rem;
  padding: 0.5rem;
  background: white;
  border-radius: 6px;
  border-left: 3px solid #cbd5e0;
}

.thought-item {
  margin-bottom: 0.5rem;
  padding: 0.5rem;
  background: #edf2f7;
  border-radius: 4px;
}

.thought-item:last-child {
  margin-bottom: 0;
}

.thought-header {
  font-size: 0.8rem;
  display: flex;
  align-items: center;
  gap: 0.5rem;
  margin-bottom: 0.25rem;
  color: #2d3748;
}

.thought-time {
  color: #a0aec0;
  margin-left: auto;
}

.thought-text {
  font-size: 0.85rem;
  color: #4a5568;
  line-height: 1.5;
}

/* Add Thought Form Styles */
.add-thought-section {
  margin-top: 0.5rem;
  margin-left: 1.75rem;
}

.add-thought-button {
  font-size: 0.8rem;
  padding: 0.375rem 0.75rem;
  border: 1px solid #cbd5e0;
  border-radius: 4px;
  background: white;
  color: #5a67d8;
  cursor: pointer;
  transition: all 0.2s;
}

.add-thought-button:hover {
  background: #ebf4ff;
  border-color: #5a67d8;
}

.thought-form {
  margin-top: 0.3rem;
  padding: 0.4rem;
  background: white;
  border-radius: 6px;
  border: 1px solid #cbd5e0;
}

.thought-textarea {
  width: 100%;
  padding: 0.5rem;
  border: 1px solid #cbd5e0;
  border-radius: 4px;
  font-family: inherit;
  font-size: 0.875rem;
  resize: vertical;
  min-height: 60px;
}

.thought-textarea:focus {
  outline: none;
  border-color: #5a67d8;
  box-shadow: 0 0 0 3px rgba(90, 103, 216, 0.1);
}

.thought-form-actions {
  display: flex;
  gap: 0.5rem;
  margin-top: 0.5rem;
}

.submit-thought-button {
  padding: 0.375rem 0.875rem;
  border: none;
  border-radius: 4px;
  background: #5a67d8;
  color: white;
  cursor: pointer;
  font-size: 0.875rem;
  font-weight: 500;
  transition: background 0.2s;
}

.submit-thought-button:hover:not(:disabled) {
  background: #4c51bf;
}

.submit-thought-button:disabled {
  background: #a0aec0;
  cursor: not-allowed;
}

.submit-open-button {
  padding: 0.5rem 1rem;
  margin-top: 0.5rem;
  border: none;
  border-radius: 4px;
  background: #5a67d8;
  color: white;
  cursor: pointer;
  font-size: 0.875rem;
  font-weight: 500;
  transition: background 0.2s;
}

.submit-open-button:hover:not(:disabled) {
  background: #4c51bf;
}

.submit-open-button:disabled {
  background: #a0aec0;
  cursor: not-allowed;
}

.cancel-thought-button {
  padding: 0.375rem 0.875rem;
  border: 1px solid #cbd5e0;
  border-radius: 4px;
  background: white;
  color: #718096;
  cursor: pointer;
  font-size: 0.875rem;
  transition: all 0.2s;
}

.cancel-thought-button:hover {
  background: #f7fafc;
  border-color: #a0aec0;
}

/* Duplicate node styling - grayed out and non-interactive */
.duplicate-node {
  opacity: 0.85;
  background: #e8edf2;
  position: relative;
  filter: brightness(0.75);
}

.duplicate-node .answer-label {
  cursor: not-allowed;
}

.duplicate-node .answer-input {
  cursor: not-allowed;
  pointer-events: none;
}

.duplicate-node .vote-button,
.duplicate-node .vote-button-small,
.duplicate-node .add-thought-button {
  pointer-events: none;
}

.duplicate-node .answer-text {
  color: #4a5568;
}

.question-text-strikethrough {
  text-decoration: line-through;
}

.answer-text-strikethrough {
  text-decoration: line-through;
}

.duplicate-indicator {
  margin-left: 0.5rem;
  font-size: 1rem;
  cursor: help;
}

/* Allow expand/collapse to work on duplicates (only interactive element allowed) */
.duplicate-node .expand-icon {
  pointer-events: auto;
  cursor: pointer;
}

.duplicate-node .question-header {
  pointer-events: auto;
  cursor: pointer;
}
</style>

