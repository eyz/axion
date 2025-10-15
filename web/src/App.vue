<template>
  <div class="app-container">
    <!-- Loading Overlay -->
    <div v-if="isLoading" class="loading-overlay">
      <div class="loading-content">
        <div class="loading-spinner"></div>
        <h2>Loading Graph Data...</h2>
        <p>Replaying graph.log history</p>
      </div>
    </div>

    <!-- New Content Modal Overlay -->
    <div v-if="showNewContentModal" class="new-content-overlay">
      <div class="new-content-modal">
        <div class="modal-icon">🆕</div>
        <h2>New Content Added</h2>
        <p class="modal-message">
          Specialists have added <strong>{{ newContentCount }}</strong> new {{ newContentCount === 1 ? 'item' : 'items' }} to the decision tree.
        </p>
        <p class="modal-submessage">
          The tree will update when you acknowledge.
        </p>
        <button @click="acknowledgeNewContent" class="acknowledge-button">
          Acknowledge & Continue
        </button>
      </div>
    </div>

    <div class="page-wrapper">
      <header class="app-header">
        <h1>📊 Graph Decision Form</h1>
        <p class="subtitle">Make selections based on specialist voting and consensus. Questions and answers are sorted by vote strength (highest positive votes first).</p>
        <div class="status-bar">
          <div class="connection-status">
            <span :class="['status-indicator', connectionStatus]"></span>
            {{ connectionStatusText }}
          </div>
          <div class="phase-status" :class="phaseStatusClass">
            <span class="phase-indicator">{{ phaseStatusIcon }}</span>
            <span class="phase-text">{{ phaseStatusText }}</span>
          </div>
        </div>
      </header>

      <div class="content-wrapper" :class="{ 'dimmed': isLoading }">
        <aside class="sidebar">
        <!-- Hide Duplicates Toggle -->
        <div class="toggle-panel">
          <label class="toggle-switch" @click.prevent="toggleHideDuplicates">
            <input type="checkbox" :checked="hideDuplicates" @click.stop>
            <span class="toggle-slider"></span>
          </label>
          <span class="toggle-label">Hide Duplicates 🧹 ({{ hideDuplicates ? 'ON' : 'OFF' }})</span>
        </div>
        
        <div class="stats-panel">
          <h3>📈 Statistics</h3>
          <div class="stat-item">
            <label>Total Questions:</label>
            <span>{{ rootQuestions.length }}</span>
          </div>
          <div class="stat-item">
            <label>Total Votes:</label>
            <span>{{ totalVotes }}</span>
          </div>
          <div class="stat-item">
            <label>Active Specialists:</label>
            <span>{{ Object.keys(graphData.specialist_stats).length }}</span>
          </div>
        </div>

        <div class="specialists-panel">
          <h3>🎭 Specialists</h3>
          <div v-for="(stats, specialist) in graphData.specialist_stats" :key="specialist" class="specialist-item">
            <div class="specialist-name">{{ specialist }}</div>
            <div class="specialist-votes">
              <span class="vote-up">✅ {{ stats.upvotes }}</span>
              <span class="vote-down">❌ {{ stats.downvotes }}</span>
            </div>
          </div>
        </div>
      </aside>

      <main class="main-content">
        <div v-if="rootQuestions.length === 0" class="empty-state">
          <p>Waiting for agents to propose questions...</p>
          <div class="spinner"></div>
        </div>

        <form v-else @submit.prevent="handleSubmit" class="decision-form">
          <!-- Vote Status Legend -->
          <div class="legend">
            <strong>Vote Status Legend:</strong><br>
            <div class="legend-item">
              <span class="legend-badge" style="background: #28a745;"></span>
              <strong>Strong Consensus</strong> (net +3 or more)
            </div>
            <div class="legend-item">
              <span class="legend-badge" style="background: #17a2b8;"></span>
              <strong>Positive</strong> (net +1 to +2)
            </div>
            <div class="legend-item">
              <span class="legend-badge" style="background: #6c757d;"></span>
              <strong>Neutral</strong> (net 0)
            </div>
            <div class="legend-item">
              <span class="legend-badge" style="background: #dc3545;"></span>
              <strong>Rejected</strong> (net -3 or less)
            </div>
          </div>
          <QuestionNode
            v-for="questionPath in displayedRootQuestions"
            :key="questionPath"
            :path="questionPath"
            :graph-data="graphData"
            :vote-tally="graphData.vote_tally"
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
            @update-selection="updateSelection"
            @update-vote="updateVote"
            @immediate-submit="handleImmediateSubmit"
            @submit-thought="handleThoughtSubmit"
            @viewport-change="handleRootQuestionViewportChange"
          />

          <div class="submit-section">
            <button type="submit" class="submit-button" :disabled="!hasChanges">
              Submit Decisions to Swarm
              <span v-if="pendingDecisionCount > 0" class="decision-count-badge">
                {{ pendingDecisionCount }}
              </span>
            </button>
            <p class="help-text">
              Your selections will be sent as @[Graph] commands to the agent chat.
            </p>
            
            <button 
              type="button" 
              @click="handleContinuePhase" 
              class="continue-button"
              :class="{ 'has-pending': unansweredQuestionCount > 0 }"
              :disabled="!phaseStatus.waiting"
            >
              Continue to Next Phase
              <span v-if="unansweredQuestionCount > 0" class="pending-badge">
                ⚠️ {{ unansweredQuestionCount }} pending
              </span>
              <span v-else class="all-answered-badge">
                ✅ All answered
              </span>
            </button>
            <p class="help-text continue-help">
              <span v-if="phaseStatus.waiting">
                Signals the swarm to proceed. You can skip unanswered questions.
              </span>
              <span v-else>
                Waiting for current phase to complete...
              </span>
            </p>
          </div>
        </form>
      </main>
    </div>
    </div>
  </div>
</template>

<script>
import { ref, reactive, computed, watch, onMounted, onUnmounted, nextTick } from 'vue'
import { io } from 'socket.io-client'
import QuestionNode from './components/QuestionNode.vue'

export default {
  name: 'App',
  components: {
    QuestionNode
  },
  setup() {
    const graphData = reactive({
      nodes: {},
      vote_tally: {},
      specialist_stats: {}
    })

    const userSelections = reactive({})
    const lastSubmittedState = reactive({}) // Track what was last submitted
    
    // Track layer interaction state for auto-collapse/expand behavior
    // Key: layer path (parent path), Value: { clickedAt: timestamp, nodesAtClick: Set<string> }
    const layerInteractionState = reactive({})
    
    // Track which questions we actually interacted with (for smart collapse on submit)
    // Includes: selections, votes, thoughts
    const interactedQuestions = reactive(new Set())
    
    // Track which specific questions should collapse on submit (not entire layers)
    // Use object with timestamps instead of Set for reliable Vue 3 reactivity
    const questionsToCollapse = reactive({})
    
    // Track last submission timestamp for "NEW" badge detection
    // Initialize to 0 so nodes added after page load show as "NEW"
    const lastSubmissionTimestamp = ref(0)
    
    // Track which selections existed at last submission (for sort priority)
    const selectionsAtLastSubmit = reactive({})
    const socket = ref(null)
    const connectionStatus = ref('disconnected')
    const isLoading = ref(true)
    const showNewContentModal = ref(false)
    const newContentCount = ref(0)
    const pendingNewNodes = ref([])
    
    // Track phase execution status
    const phaseStatus = reactive({
      waiting: false,        // Is swarm blocked waiting for user?
      currentPhase: 0,       // Current phase number
      isFinal: false         // Is this the final phase?
    })
    
    // Local backing object: tracks entire graph change log and current state
    const graphChangeLog = reactive({
      // Snapshot of node paths at last submission for "new" detection
      nodesAtLastSubmit: new Set(),
      // Map of node path -> recursive new count (includes all descendants)
      recursiveNewCounts: {},
      // Set of nodes that user has "seen" (engaged with by selecting an answer in their group)
      seenNodes: new Set()
    })

    const connectionStatusText = computed(() => {
      return {
        connected: 'Connected',
        connecting: 'Connecting...',
        disconnected: 'Disconnected'
      }[connectionStatus.value]
    })
    
    const phaseStatusIcon = computed(() => {
      if (phaseStatus.waiting) return '⏸️'
      if (phaseStatus.isFinal) return '🏁'
      return '▶️'
    })
    
    const phaseStatusText = computed(() => {
      if (phaseStatus.waiting) {
        return `Phase ${phaseStatus.currentPhase} Complete - Waiting for Continue`
      }
      if (phaseStatus.isFinal) {
        return `Final Phase ${phaseStatus.currentPhase} Complete`
      }
      if (phaseStatus.currentPhase > 0) {
        return `Phase ${phaseStatus.currentPhase} Running`
      }
      return 'Ready to Start'
    })
    
    const phaseStatusClass = computed(() => {
      if (phaseStatus.waiting) return 'waiting'
      if (phaseStatus.isFinal) return 'final'
      return 'running'
    })

    function isNodeXed(path) {
      // Check if node has been marked with [❌] (dismissed)
      // First check user's pending vote (optimistic UI)
      const userVote = userSelections[`vote:${path}`]
      if (userVote === 'X' || userVote === '❌') return true
      
      // Then check backend data
      const node = graphData.nodes[path]
      if (!node || !node.votes) return false
      return node.votes.some(vote => vote.vote === '❌' || vote.vote === 'X')
    }
    
    // Get all descendants of a node (children, grandchildren, etc.)
    function getAllDescendants(nodePath) {
      const descendants = []
      for (const path in graphData.nodes) {
        if (path.startsWith(nodePath) && path !== nodePath) {
          descendants.push(path)
        }
      }
      return descendants
    }
    
    // Check if a node is new (added since last submission AND not yet seen by user)
    function isNodeNew(path) {
      return !graphChangeLog.nodesAtLastSubmit.has(path) && !graphChangeLog.seenNodes.has(path)
    }
    
    // Check if a node would be visible in the UI
    function isNodeVisible(path) {
      // Only X'd out nodes are invisible
      // Everything else (including questions without answers) is visible
      return !isNodeXed(path)
    }
    
    // Compute recursive new counts for all nodes
    // This counts how many new nodes (Q or A) exist within this node at any depth
    // ONLY counts nodes that are visible (not X'd out and have visible content)
    function computeRecursiveNewCounts() {
      const counts = {}
      
      // For each node in the graph
      for (const nodePath in graphData.nodes) {
        let newCount = 0
        
        // Check if this node itself is new AND visible
        if (isNodeNew(nodePath) && isNodeVisible(nodePath)) {
          newCount = 1
        }
        
        // Get all descendants and count how many are new AND visible
        const descendants = getAllDescendants(nodePath)
        for (const descPath of descendants) {
          if (isNodeNew(descPath) && isNodeVisible(descPath)) {
            newCount++
          }
        }
        
        counts[nodePath] = newCount
      }
      
      // Update reactive state
      Object.keys(graphChangeLog.recursiveNewCounts).forEach(key => {
        delete graphChangeLog.recursiveNewCounts[key]
      })
      Object.assign(graphChangeLog.recursiveNewCounts, counts)
    }
    
    // Get all ancestor question paths for a given node
    function getParentQuestion(nodePath) {
      // Find the immediate parent question of a node
      // Example: [Q:single][Q1][A][A1] → [Q:single][Q1]
      // Example: [Q:single][Q1][A][A1][Q:single][Q2][A][A2] → [Q:single][Q1][A][A1][Q:single][Q2]
      
      // Find all question matches
      const qMatches = [...nodePath.matchAll(/\[Q:[^\]]+\]\[[^\]]+\]/g)]
      
      if (qMatches.length === 0) return null
      
      // Get the last question match
      const lastQ = qMatches[qMatches.length - 1]
      const parentQuestionEnd = lastQ.index + lastQ[0].length
      
      return nodePath.substring(0, parentQuestionEnd)
    }
    
    function getAncestorQuestions(nodePath) {
      const ancestors = []
      
      // Parse the path to find all parent questions
      // Example: [Q:single][Q1][A][A1][Q:single][Q2][A][A2]
      // Ancestors: [Q:single][Q1][A][A1][Q:single][Q2], [Q:single][Q1]
      
      const qMatches = [...nodePath.matchAll(/\[Q:[^\]]+\]\[[^\]]+\]/g)]
      
      for (let i = 0; i < qMatches.length; i++) {
        const qMatch = qMatches[i]
        const qEnd = qMatch.index + qMatch[0].length
        const ancestorPath = nodePath.substring(0, qEnd)
        if (ancestorPath !== nodePath) {
          ancestors.push(ancestorPath)
        }
      }
      
      return ancestors
    }
    
    // Get all direct answers for a question
    function getDirectAnswers(questionPath) {
      const answers = []
      const qCount = (questionPath.match(/\[Q:/g) || []).length
      
      for (const path in graphData.nodes) {
        if (!path.startsWith(questionPath + '[A')) continue
        
        const pathQCount = (path.match(/\[Q:/g) || []).length
        const pathACount = (path.match(/\[A\]|\[A:/g) || []).length
        
        // Direct answer: same Q count, A count = Q count
        if (pathQCount === qCount && pathACount === qCount) {
          answers.push(path)
        }
      }
      
      return answers
    }
    
    // Mark all answers in a question group as "seen" (user engaged with them)
    // This cascades upward to update recursive new counts
    // NOTE: Descendants (nested questions/answers) are NOT marked as seen automatically
    // They remain "new" until user explicitly engages with them
    function markAnswerGroupAsSeen(questionPath) {
      // Mark the question itself as seen
      graphChangeLog.seenNodes.add(questionPath)
      
      // Get all direct answers for this question
      const answers = getDirectAnswers(questionPath)
      
      // Mark all direct answers as seen (but NOT their descendants)
      for (const answerPath of answers) {
        graphChangeLog.seenNodes.add(answerPath)
      }
      
      // Recompute recursive new counts to cascade changes upward
      computeRecursiveNewCounts()
      
      console.log(`👁️  Marked question and ${answers.length} direct answer(s) as seen: ${questionPath}`)
    }

    const hideDuplicates = ref(true)
    
    function toggleHideDuplicates() {
      hideDuplicates.value = !hideDuplicates.value
    }
    
    function acknowledgeNewContent() {
      console.log(`✅ User acknowledged ${newContentCount.value} new node(s) - applying changes`)
      showNewContentModal.value = false
      newContentCount.value = 0
      pendingNewNodes.value = []
    }
    
    function checkViewportConflict(newNodes) {
      // Check if any new nodes would appear in the currently visible viewport
      // If yes, we need to show the modal overlay before allowing user interaction
      
      if (rootQuestionsInViewport.size === 0) {
        // No questions in viewport - no conflict
        return false
      }
      
      for (const nodePath of newNodes) {
        // Find which root question this node belongs to
        const rootQuestion = getRootQuestionForNode(nodePath)
        
        // If the root question is in viewport, this is a conflict
        if (rootQuestion && rootQuestionsInViewport.has(rootQuestion)) {
          console.log(`  ⚠️  Viewport conflict: "${nodePath.substring(0, 60)}..." belongs to visible root question`)
          return true
        }
      }
      
      return false
    }
    
    function getRootQuestionForNode(nodePath) {
      // Extract the root question path from any node path
      // Root question: [Q:type][Question Text] (first Q in the path)
      const match = nodePath.match(/^(\[Q:[^\]]+\]\[[^\]]+\])/)
      return match ? match[1] : null
    }
    
    // Compute ALL root questions (source of truth)
    const rootQuestions = computed(() => {
      return Object.keys(graphData.nodes).filter(path => {
        const qCount = (path.match(/\[Q:/g) || []).length
        const aCount = (path.match(/\[A\]|\[A:/g) || []).length
        // Don't show if it's been X'd out
        if (isNodeXed(path)) return false
        // Don't show if it's a duplicate and hideDuplicates is enabled
        if (hideDuplicates.value && isDuplicateNode(path)) return false
        return qCount === 1 && aCount === 0
      }).sort((a, b) => {
        const aNet = getNetVotes(a)
        const bNet = getNetVotes(b)
        return bNet - aNet
      })
    })
    
    // Track viewport state for root questions
    const rootQuestionsInViewport = reactive(new Set())
    const pinnedRootQuestionOrder = ref(null)
    
    // What to DISPLAY (may be pinned or live)
    const displayedRootQuestions = computed(() => {
      const hasAnyInViewport = rootQuestionsInViewport.size > 0
      
      console.log(`📋 Computing displayedRootQuestions:`)
      console.log(`   Total questions: ${rootQuestions.value.length}`)
      console.log(`   Questions in viewport: ${rootQuestionsInViewport.size}`)
      console.log(`   Pinned order exists: ${!!pinnedRootQuestionOrder.value}`)
      
      // If any root question is in viewport AND we have a pinned order, use it
      if (hasAnyInViewport && pinnedRootQuestionOrder.value) {
        console.log(`   ✅ Using pinned order (viewport active)`)
        // Return pinned order, filtering out any that no longer exist
        const pinnedStillExist = pinnedRootQuestionOrder.value.filter(q => rootQuestions.value.includes(q))
        
        // CRITICAL FIX: Add any NEW questions that appeared after pinning (e.g., from Phase 2)
        const pinnedSet = new Set(pinnedStillExist)
        const newQuestions = rootQuestions.value.filter(q => !pinnedSet.has(q))
        
        const result = [...pinnedStillExist, ...newQuestions]
        console.log(`   Pinned result: ${result.length} questions (${pinnedStillExist.length} pinned + ${newQuestions.length} new)`)
        return result
      }
      
      console.log(`   ✅ Using live order (no viewport freeze)`)
      // Not pinned - return live computed list
      return rootQuestions.value
    })
    
    function isDuplicateNode(nodePath) {
      const tally = graphData.vote_tally[nodePath]
      return tally && tally.duplicates > 0
    }
    
    function handleRootQuestionViewportChange({ path, inViewport }) {
      console.log(`🔄 Root question viewport change: "${path.substring(0, 60)}..." → ${inViewport ? 'IN' : 'OUT'}`)
      
      if (inViewport) {
        rootQuestionsInViewport.add(path)
        // Pin the CURRENT order when FIRST root question enters viewport
        if (!pinnedRootQuestionOrder.value) {
          pinnedRootQuestionOrder.value = rootQuestions.value.slice()
          console.log(`📌 Pinned root question order (${pinnedRootQuestionOrder.value.length} questions)`)
        }
      } else {
        rootQuestionsInViewport.delete(path)
        // Unpin when ALL root questions leave viewport
        if (rootQuestionsInViewport.size === 0) {
          console.log(`📌 Unpinned root question order (all questions left viewport)`)
          pinnedRootQuestionOrder.value = null
        }
      }
    }

    const totalVotes = computed(() => {
      return Object.values(graphData.nodes).reduce((sum, node) => {
        return sum + (node.votes?.length || 0)
      }, 0)
    })

    const hasSelections = computed(() => {
      return Object.keys(userSelections).length > 0
    })
    
    const hasChanges = computed(() => {
      // Check if current state differs from last submitted state
      const selectionKey = (questionPath, type, answers) => {
        if (type === 'single') {
          return `${questionPath}:single:${answers}`
        } else {
          const sortedAnswers = Array.isArray(answers) ? [...answers].sort().join(',') : ''
          return `${questionPath}:multiple:${sortedAnswers}`
        }
      }
      
      // Build current state snapshot
      const currentState = {}
      for (const [key, selection] of Object.entries(userSelections)) {
        if (key.startsWith('vote:')) {
          currentState[key] = selection
        } else {
          const stateKey = selectionKey(key, selection.type, selection.answers)
          currentState[stateKey] = true
        }
      }
      
      // Compare current state with last submitted state
      const currentKeys = Object.keys(currentState)
      const lastKeys = Object.keys(lastSubmittedState)
      
      // Different number of selections/votes
      if (currentKeys.length !== lastKeys.length) return true
      
      // Check if any keys are different
      for (const key of currentKeys) {
        if (key.startsWith('vote:')) {
          // Vote changed
          if (lastSubmittedState[key] !== currentState[key]) return true
        } else {
          // Selection changed
          if (!lastSubmittedState[key]) return true
        }
      }
      
      // Check if any keys were removed
      for (const key of lastKeys) {
        if (!currentState[key]) return true
      }
      
      return false
    })
    
    // Check if a specific question is "pending" (needs answer along active decision path)
    // A question is pending if:
    // 1. Not dismissed
    // 2. No SUBMITTED selection AND no user thoughts
    // 3. All ancestor questions have SUBMITTED selections (making this question visible/reachable)
    function isQuestionPending(questionPath) {
      try {
        // Skip if dismissed
        if (isNodeXed(questionPath)) return false
        
        // Check if user has added thoughts to this question (counts as engagement)
        const node = graphData.nodes[questionPath]
        if (node && node.user_thoughts && node.user_thoughts.length > 0) {
          return false // User engaged with a thought, not pending
        }
        
        // Check if this question has a SUBMITTED selection
        // selectionsAtLastSubmit is a copy of userSelections structure with question paths as keys
        if (selectionsAtLastSubmit[questionPath]) return false
        
        // Check if all ancestors have SUBMITTED selections (making this question reachable)
        const ancestors = getAncestorQuestions(questionPath)
        
        for (const ancestorPath of ancestors) {
          // If any ancestor is dismissed, this question is not reachable
          if (isNodeXed(ancestorPath)) return false
          
          // Check if ancestor has SUBMITTED selection
          const ancestorSelection = selectionsAtLastSubmit[ancestorPath]
          
          // If any ancestor has no submitted selection, this question is not reachable yet
          if (!ancestorSelection) return false
          
          // Check if the path from ancestor to this question goes through a submitted answer
          const afterAncestor = questionPath.substring(ancestorPath.length)
          const answerMatch = afterAncestor.match(/^\[A(?::[^\]]+)?\]\[[^\]]+\]/)
          
          if (answerMatch) {
            const answerPath = ancestorPath + answerMatch[0]
            const selectedAnswers = Array.isArray(ancestorSelection.answers) 
              ? ancestorSelection.answers 
              : [ancestorSelection.answers]
            
            // Check if this answer path is in the submitted selections
            if (!selectedAnswers.includes(answerPath)) {
              return false // This path is not selected, question not reachable
            }
          }
        }
        
        // All ancestors answered, this question is reachable and unanswered → pending
        return true
      } catch (error) {
        console.error(`Error checking if question is pending: ${questionPath}`, error)
        return false // Fail safe - don't show PENDING if error
      }
    }
    
    // Recursively count unanswered questions along active decision paths
    // For each question in the tree:
    // - If dismissed → skip entire subtree
    // - If no selection → count it
    // - If HAS selection → recurse into selected answer's nested questions
    const unansweredQuestionCount = computed(() => {
      const countUnansweredInSubtree = (questionPath) => {
        // Skip if question is dismissed
        if (isNodeXed(questionPath)) return 0
        
        // Check SUBMITTED selection, not current selection
        const selection = selectionsAtLastSubmit[questionPath]
        
        // No SUBMITTED selection on this question → count it
        if (!selection) {
          console.log(`⚠️  Question counted as unanswered: "${questionPath}"`)
          console.log(`   selectionsAtLastSubmit has NO entry for this question`)
          return 1
        }
        
        // Has SUBMITTED selection → check for nested questions under selected answers
        let nestedCount = 0
        const selectedAnswers = Array.isArray(selection.answers) ? selection.answers : [selection.answers]
        
        console.log(`✅ Question has submitted selection: "${questionPath}"`)
        console.log(`   Selected answers (${selectedAnswers.length}):`, selectedAnswers.map(a => a.substring(a.lastIndexOf('[A]') || a.lastIndexOf('[A:'))))
        
        for (const answerPath of selectedAnswers) {
          // Find nested questions under this answer
          const answerPrefix = answerPath
          for (const nodePath in graphData.nodes) {
            // Check if this is a direct nested question under the selected answer
            if (nodePath.startsWith(answerPrefix + '[Q:')) {
              const isDirectChild = nodePath.match(/\[Q:[^\]]+\]\[[^\]]+\]$/);
              if (isDirectChild) {
                // Count how many [Q: are before and after the answer
                const answerQCount = (answerPath.match(/\[Q:/g) || []).length
                const nodeQCount = (nodePath.match(/\[Q:/g) || []).length
                // Direct child has exactly 1 more Q: than the answer path
                if (nodeQCount === answerQCount + 1) {
                  const childCount = countUnansweredInSubtree(nodePath)
                  if (childCount > 0) {
                    console.log(`   ⬇️  Found unanswered nested question under "${answerPath.substring(answerPath.lastIndexOf('[A]') || answerPath.lastIndexOf('[A:'))}"`)
                  }
                  nestedCount += childCount
                }
              }
            }
          }
        }
        
        return nestedCount
      }
      
      let totalCount = 0
      const pendingQuestions = []
      // Start from root questions
      for (const questionPath of rootQuestions.value) {
        const count = countUnansweredInSubtree(questionPath)
        if (count > 0) {
          pendingQuestions.push(questionPath)
          console.log(`⚠️  Counting as pending: "${questionPath}" (count: ${count})`)
          console.log(`   Has selection in selectionsAtLastSubmit:`, !!selectionsAtLastSubmit[questionPath])
          console.log(`   Selection:`, selectionsAtLastSubmit[questionPath])
        }
        totalCount += count
      }
      
      if (totalCount > 0) {
        console.log(`📊 Total unanswered count: ${totalCount} from ${pendingQuestions.length} root question(s)`)
      }
      
      return totalCount
    })
    
    // Count pending decisions to submit (selections and votes that differ from last submission)
    const pendingDecisionCount = computed(() => {
      let count = 0
      
      // Helper to create a comparable key for a selection
      const selectionKey = (questionPath, type, answers) => {
        if (type === 'single') {
          return `${questionPath}:single:${answers}`
        } else {
          const sortedAnswers = Array.isArray(answers) ? [...answers].sort().join(',') : ''
          return `${questionPath}:multiple:${sortedAnswers}`
        }
      }
      
      // Build current state snapshot
      const currentState = {}
      for (const [key, selection] of Object.entries(userSelections)) {
        if (key.startsWith('vote:')) {
          currentState[key] = selection
        } else {
          const stateKey = selectionKey(key, selection.type, selection.answers)
          currentState[stateKey] = true
        }
      }
      
      // Count new or changed selections/votes
      for (const key of Object.keys(currentState)) {
        if (key.startsWith('vote:')) {
          if (lastSubmittedState[key] !== currentState[key]) count++
        } else {
          if (!lastSubmittedState[key]) count++
        }
      }
      
      // Count removed selections/votes
      for (const key of Object.keys(lastSubmittedState)) {
        if (!currentState[key]) count++
      }
      
      return count
    })

    function getNetVotes(path) {
      const tally = graphData.vote_tally[path]
      if (!tally) return 0
      return (tally.upvotes || 0) - (tally.downvotes || 0)
    }
    
    function handleContinuePhase() {
      if (!socket.value) {
        console.error('Socket not connected')
        return
      }
      
      console.log(`🚀 User clicked Continue to Next Phase (${unansweredQuestionCount.value} pending questions)`)
      
      // Optimistically update UI
      phaseStatus.waiting = false
      
      socket.value.emit('continue_phase', {
        unanswered_count: unansweredQuestionCount.value
      })
    }

    function updateSelection({ questionPath, answerPath, selected, isMultiple }) {
      // Track layer interaction for auto-collapse behavior
      // Get the parent path (layer) for this question
      const layerPath = getLayerPath(questionPath)
      
      // If this is the FIRST selection click in this layer, record it
      if (!layerInteractionState[layerPath]) {
        // First click in this layer - capture all sibling questions at this moment
        const siblingQuestions = getSiblingQuestions(questionPath)
        layerInteractionState[layerPath] = {
          firstClickAt: Date.now(),
          nodesAtFirstClick: new Set(siblingQuestions),
          shouldCollapse: false, // Will be set to true on submit
          userClickedToExpand: false // Track if user manually expanded
        }
      }
      
      // Mark all answers in this group as "seen" since user is engaging with them
      markAnswerGroupAsSeen(questionPath)
      
      // Mark the specific answer being selected as seen (removes NEW badge)
      if (selected && answerPath) {
        graphChangeLog.seenNodes.add(answerPath)
        // Recompute recursive counts - this will cascade up naturally
        // Parent answers only lose NEW badge when ALL their descendants are seen
        computeRecursiveNewCounts()
      }
      
      // Track that we interacted with this question (for smart collapse on submit)
      interactedQuestions.add(questionPath)
      
      if (!userSelections[questionPath]) {
        userSelections[questionPath] = {
          type: isMultiple ? 'multiple' : 'single',
          answers: isMultiple ? [] : null
        }
      }

      if (isMultiple) {
        if (selected) {
          if (!userSelections[questionPath].answers.includes(answerPath)) {
            userSelections[questionPath].answers.push(answerPath)
          }
          // CASCADING SELECTION: Check parent checkboxes when child is checked
          // (but don't uncheck parents when children are unchecked)
          selectParentCheckboxes(answerPath)
        } else {
          const idx = userSelections[questionPath].answers.indexOf(answerPath)
          if (idx > -1) {
            userSelections[questionPath].answers.splice(idx, 1)
          }
        }
        // Clean up empty multiple selections
        if (userSelections[questionPath].answers.length === 0) {
          delete userSelections[questionPath]
        }
      } else {
        // Single choice: set selection
        userSelections[questionPath].answers = answerPath
        
        // CASCADING SELECTION: Select all parent radio buttons in the path
        // Walk backwards through the answerPath to find parent questions
        if (selected && answerPath.startsWith(questionPath)) {
          // This answer is nested - find parent questions by analyzing the path
          selectParentRadioButtons(answerPath)
        }
      }
    }
    
    function getLayerPath(questionPath) {
      // Extract the parent path (everything before this question)
      // Example: [Q:single][Q1][A][A1][Q:single][Q2] -> [Q:single][Q1][A][A1]
      const matches = questionPath.match(/^(.*?)(\[Q:[^\]]+\]\[[^\]]+\])$/)
      return matches ? matches[1] : '' // Return parent path or empty for root
    }
    
    function getSiblingQuestions(questionPath) {
      // Get all questions at the same level (same parent)
      const layerPath = getLayerPath(questionPath)
      const qDepth = (questionPath.match(/\[Q:/g) || []).length
      
      return Object.keys(graphData.nodes).filter(path => {
        // Must be a question (not an answer)
        if (!path.match(/\[Q:[^\]]+\]\[[^\]]+\]$/)) return false
        
        // Must have same parent
        if (getLayerPath(path) !== layerPath) return false
        
        // Must be at same depth
        const pathDepth = (path.match(/\[Q:/g) || []).length
        return pathDepth === qDepth
      })
    }

    function selectParentRadioButtons(answerPath) {
      // Parse the path to find all parent questions
      // Example: [Q:single][Q1][A][A1][Q:single][Q2][A][A2]
      //   - First Q at [Q:single][Q1] with answer [Q:single][Q1][A][A1]
      //   - Second Q at [Q:single][Q1][A][A1][Q:single][Q2] with answer [Q:single][Q1][A][A1][Q:single][Q2][A][A2]
      
      // Find all question positions in the path
      const qMatches = [...answerPath.matchAll(/\[Q:[^\]]+\]\[[^\]]+\]/g)]
      
      for (let i = 0; i < qMatches.length; i++) {
        const qMatch = qMatches[i]
        const qStart = qMatch.index
        const qEnd = qStart + qMatch[0].length
        
        // Find the corresponding answer for this question
        // Look for the next [A] or [A:...] after this question
        const remainingPath = answerPath.substring(qEnd)
        const aMatch = remainingPath.match(/^(\[A[^\]]*\](?:\[[^\]]+\])?)/)
        
        if (aMatch) {
          const questionPath = answerPath.substring(0, qEnd)
          const answerPathForThisQ = answerPath.substring(0, qEnd + aMatch[0].length)
          
          // Check if this question is single-choice
          const isSingle = qMatch[0].includes('[Q:single]')
          
          if (isSingle) {
            // Auto-select this parent answer
            if (!userSelections[questionPath]) {
              userSelections[questionPath] = {
                type: 'single',
                answers: answerPathForThisQ
              }
            } else {
              userSelections[questionPath].answers = answerPathForThisQ
            }
          }
        }
      }
    }
    
    function selectParentCheckboxes(answerPath) {
      // Similar to selectParentRadioButtons, but for multiple-choice questions
      // When a child checkbox is checked, automatically check parent checkboxes
      // Example: [Q:multiple][Q1][A][A1][Q:multiple][Q2][A][A2]
      //   - If user checks answer A2 in nested Q2, also check answer A1 in parent Q1
      
      // Find all question positions in the path
      const qMatches = [...answerPath.matchAll(/\[Q:[^\]]+\]\[[^\]]+\]/g)]
      
      for (let i = 0; i < qMatches.length; i++) {
        const qMatch = qMatches[i]
        const qStart = qMatch.index
        const qEnd = qStart + qMatch[0].length
        
        // Find the corresponding answer for this question
        // Look for the next [A] or [A:...] after this question
        const remainingPath = answerPath.substring(qEnd)
        const aMatch = remainingPath.match(/^(\[A[^\]]*\](?:\[[^\]]+\])?)/)
        
        if (aMatch) {
          const questionPath = answerPath.substring(0, qEnd)
          const answerPathForThisQ = answerPath.substring(0, qEnd + aMatch[0].length)
          
          // Check if this question is multiple-choice
          const isMultiple = qMatch[0].includes('[Q:multiple]')
          
          if (isMultiple) {
            // Auto-check this parent checkbox (if not already checked)
            if (!userSelections[questionPath]) {
              userSelections[questionPath] = {
                type: 'multiple',
                answers: [answerPathForThisQ]
              }
            } else if (!userSelections[questionPath].answers.includes(answerPathForThisQ)) {
              userSelections[questionPath].answers.push(answerPathForThisQ)
            }
          }
        }
      }
    }

    function updateVote({ path, vote }) {
      const voteKey = `vote:${path}`
      if (vote === null) {
        delete userSelections[voteKey]
      } else {
        userSelections[voteKey] = vote
      }
      
      // Track interaction: if voting on a question, track it; if voting on an answer, track its parent question
      if (path.match(/\[Q:[^\]]+\]\[[^\]]+\]$/)) {
        // This is a question - track it directly
        interactedQuestions.add(path)
      } else if (path.match(/\[A(?::[^\]]+)?\]\[[^\]]+\]$/)) {
        // This is an answer - find its parent question
        const questionMatch = path.match(/^(.*?\[Q:[^\]]+\]\[[^\]]+\])/)
        if (questionMatch) {
          interactedQuestions.add(questionMatch[1])
        }
      }
      
      // Recalculate NEW badge counts immediately (optimistic UI)
      // Dismissed items (vote='X' or '❌') will be marked as invisible and won't count as NEW
      computeRecursiveNewCounts()
    }

    function handleImmediateSubmit({ path, vote }) {
      // Immediately submit a dismissal command without waiting for form submit
      // NOTE: Don't add @[Graph][Update] prefix here - webserver adds it
      const command = `${path}[${vote}]`
      
      if (!socket.value) {
        console.error('Socket not connected')
        return
      }
      
      console.log(`🚀 Immediate submit: ${command}`)
      
      socket.value.emit('submit_decisions', {
        commands: [command],
        timestamp: new Date().toISOString()
      })
      
      // Update last submitted state to track this dismissal
      // CRITICAL: Store the actual vote value from userSelections (emoji), not internal code
      // This ensures diff tracking in handleSubmit() correctly skips already-sent dismissals
      const voteKey = `vote:${path}`
      lastSubmittedState[voteKey] = userSelections[voteKey] || vote
      
      // Check if we should collapse parent layer (if all siblings are now dismissed)
      checkAndCollapseEmptyParent(path)
    }

    function handleThoughtSubmit({ path, comment }) {
      // Submit user thought/comment on a graph node
      if (!socket.value) {
        console.error('Socket not connected')
        return
      }
      
      console.log(`💭 Submitting thought for ${path}: "${comment}"`)
      
      socket.value.emit('submit_thought', {
        path: path,
        comment: comment,
        timestamp: new Date().toISOString()
      })
      
      // Track interaction: if thought on a question, track it; if on an answer, track its parent question
      if (path.match(/\[Q:[^\]]+\]\[[^\]]+\]$/)) {
        // This is a question - track it directly
        interactedQuestions.add(path)
      } else if (path.match(/\[A(?::[^\]]+)?\]\[[^\]]+\]$/)) {
        // This is an answer - find its parent question
        const questionMatch = path.match(/^(.*?\[Q:[^\]]+\]\[[^\]]+\])/)
        if (questionMatch) {
          interactedQuestions.add(questionMatch[1])
        }
      }
      
      // Mark this specific node as "seen" IMMEDIATELY - user engaged with it deeply
      // This removes the NEW badge since they've interacted with it
      if (!graphChangeLog.seenNodes.has(path)) {
        console.log(`👁️  Marking node as seen (thought added): ${path.substring(0, 80)}...`)
        graphChangeLog.seenNodes.add(path)
        
        // Surgically decrement the count for this node by 1
        if (graphChangeLog.recursiveNewCounts[path] > 0) {
          console.log(`   Decrementing NEW count for node: ${graphChangeLog.recursiveNewCounts[path]} → ${graphChangeLog.recursiveNewCounts[path] - 1}`)
          graphChangeLog.recursiveNewCounts[path]--
        }
        
        // Cascade -1 upward to all ancestors
        let currentPath = path
        while (currentPath) {
          const parentMatch = currentPath.match(/^(.+)\[(?:Q:[^\]]+|A(?::[^\]]+)?)\]\[[^\]]+\]$/)
          if (parentMatch) {
            const parentPath = parentMatch[1]
            if (graphChangeLog.recursiveNewCounts[parentPath] > 0) {
              graphChangeLog.recursiveNewCounts[parentPath]--
            }
            currentPath = parentPath
          } else {
            break
          }
        }
        
        console.log(`👁️  Marked node as seen (added thought): ${path}`)
      }
    }
    
    function checkAndCollapseEmptyParent(dismissedPath) {
      // Get the layer this node belongs to
      const layerPath = getLayerPath(dismissedPath)
      
      // Get all sibling questions at this layer
      const siblings = getSiblingQuestions(dismissedPath)
      
      // Check if all siblings are now dismissed (X'd)
      const allDismissed = siblings.every(siblingPath => {
        // Check if this sibling is dismissed
        const userVote = userSelections[`vote:${siblingPath}`]
        if (userVote === 'X' || userVote === '❌') return true
        
        // Check backend data
        const node = graphData.nodes[siblingPath]
        if (!node || !node.votes) return false
        return node.votes.some(vote => vote.vote === '❌' || vote.vote === 'X')
      })
      
      if (allDismissed && layerPath) {
        // All siblings dismissed - collapse parent layer
        if (layerInteractionState[layerPath]) {
          layerInteractionState[layerPath].shouldCollapse = true
          layerInteractionState[layerPath].userClickedToExpand = false
        }
        
        // Recursively check parent's parent
        checkAndCollapseEmptyParent(layerPath)
      }
    }

    function handleSubmit() {
      const graphCommands = []

      // Helper to create a comparable key for a selection
      const selectionKey = (questionPath, type, answers) => {
        if (type === 'single') {
          return `${questionPath}:single:${answers}`
        } else {
          const sortedAnswers = Array.isArray(answers) ? [...answers].sort().join(',') : ''
          return `${questionPath}:multiple:${sortedAnswers}`
        }
      }

      // Build current state snapshot
      const currentState = {}
      
      for (const [key, selection] of Object.entries(userSelections)) {
        if (key.startsWith('vote:')) {
          // Votes
          currentState[key] = selection
        } else {
          // Selections
          const questionPath = key
          const stateKey = selectionKey(questionPath, selection.type, selection.answers)
          currentState[stateKey] = true
        }
      }

      // Process votes - only send if changed
      for (const [key, vote] of Object.entries(userSelections)) {
        if (!key.startsWith('vote:')) continue
        
        // Check if this vote is different from last submission
        if (lastSubmittedState[key] === vote) {
          continue // Skip unchanged votes
        }
        
        const path = key.substring(5) // Remove "vote:" prefix
        // Convert internal vote codes to emoji
        const voteEmoji = {
          '+': '✅',
          '-': '👎',
          'X': '❌',
          '=': '➖'
        }[vote] || vote
        graphCommands.push(`${path}[${voteEmoji}]`)
      }

      // Process selections - only send if changed
      for (const [key, selection] of Object.entries(userSelections)) {
        if (key.startsWith('vote:')) continue // Already handled
        
        const questionPath = key
        const currentKey = selectionKey(questionPath, selection.type, selection.answers)
        
        // Check if this selection changed from last submission
        if (lastSubmittedState[currentKey]) {
          continue // Skip unchanged selections
        }
        
        // Get all answer options for this question
        const allAnswers = Object.keys(graphData.nodes).filter(path => {
          if (!path.startsWith(questionPath + '[A')) return false
          const qCount = (questionPath.match(/\[Q:/g) || []).length
          const pathQCount = (path.match(/\[Q:/g) || []).length
          const pathACount = (path.match(/\[A\]|\[A:/g) || []).length
          return pathQCount === qCount && pathACount === qCount
        })

        if (selection.type === 'single') {
          // Single choice: mark selected with [✅] (this is my choice)
          const selectedAnswer = selection.answers
          if (selectedAnswer) {
            // CRITICAL: Don't send selection if user also dismissed this node
            // Dismissal (❌) takes precedence over selection (✅)
            const dismissVoteKey = `vote:${selectedAnswer}`
            const dismissVote = userSelections[dismissVoteKey]
            if (dismissVote !== 'X' && dismissVote !== '❌') {
              const command = `${selectedAnswer}[✅]`
              graphCommands.push(command)
            }
            // else: User dismissed this, ❌ command already sent in vote processing
          }
        } else {
          // Multiple choice: [✅] for selected, [➖] for deselected items user previously approved
          const selectedAnswers = selection.answers || []
          
          // Find what was selected in last submission for this question
          // Look in selectionsAtLastSubmit which has the actual selection objects
          const lastSelection = selectionsAtLastSubmit[questionPath]
          const lastSelectedAnswers = (lastSelection && lastSelection.type === 'multiple') 
            ? (lastSelection.answers || [])
            : []
          
          // Send [✅] for newly selected items (not in last submission)
          for (const answerPath of selectedAnswers) {
            if (!lastSelectedAnswers.includes(answerPath)) {
              // CRITICAL: Don't send selection if user also dismissed this node
              // Dismissal (❌) takes precedence over selection (✅)
              const dismissVoteKey = `vote:${answerPath}`
              const dismissVote = userSelections[dismissVoteKey]
              if (dismissVote !== 'X' && dismissVote !== '❌') {
                graphCommands.push(`${answerPath}[✅]`)
              }
              // else: User dismissed this, ❌ command already sent in vote processing
            }
          }
          
          // Send [➖] for items that were selected in last submission but now deselected
          for (const answerPath of lastSelectedAnswers) {
            if (!selectedAnswers.includes(answerPath)) {
              // CRITICAL: Don't send [➖] if user dismissed this node
              // Dismissal (❌) takes precedence over neutral (➖)
              const dismissVoteKey = `vote:${answerPath}`
              const dismissVote = userSelections[dismissVoteKey]
              if (dismissVote !== 'X' && dismissVote !== '❌') {
                graphCommands.push(`${answerPath}[➖]`)
              }
              // else: User dismissed this, ❌ command already sent in vote processing
            }
          }
        }
      }

      // Check for completely deselected questions (were in last submission but not in current)
      // NOTE: For single-choice (radio buttons), changing from Answer A to Answer B
      // only sends [✅] for Answer B. The new selection implicitly replaces the old one.
      // We only send [➖] if the question is completely removed from selections.
      for (const lastKey of Object.keys(lastSubmittedState)) {
        if (lastKey.startsWith('vote:')) continue
        
        // Extract question path from last state key
        // Key format is: "questionPath:single:answer" or "questionPath:multiple:answers"
        let questionPath
        if (lastKey.includes(':single:')) {
          questionPath = lastKey.split(':single:')[0]
        } else if (lastKey.includes(':multiple:')) {
          questionPath = lastKey.split(':multiple:')[0]
        } else {
          continue // Invalid key format
        }
        
        // Only send [➖] if this question is COMPLETELY REMOVED from current selections
        // (not just changed to a different answer)
        if (!userSelections[questionPath]) {
          // Question was removed entirely - send [➖] to clear the old answer
          if (lastKey.includes(':single:')) {
            const lastAnswer = lastKey.split(':single:')[1]
            if (lastAnswer) {
              graphCommands.push(`${lastAnswer}[➖]`)
            }
          }
          // For multiple-choice, removal is already handled in the main loop above
        }
      }

      // Send commands via WebSocket (only if there are changes)
      if (graphCommands.length > 0) {
        if (socket.value && socket.value.connected) {
          socket.value.emit('submit_decisions', {
            commands: graphCommands,
            timestamp: new Date().toISOString()
          })

          console.log('✅ Submitted', graphCommands.length, 'decision(s) to the swarm')
          console.log('Commands:', graphCommands)
        }
      } else {
        console.log('ℹ️ No changes to submit (but still updating UI state)')
      }
      
      // ALWAYS update state (even if no changes) to trigger collapse and reset "NEW" badges
      // Update last submitted state to current state
      Object.keys(lastSubmittedState).forEach(key => delete lastSubmittedState[key])
      Object.assign(lastSubmittedState, currentState)
      
      // Update submission timestamp for "NEW" badge detection
      // Use the LATEST node timestamp in the graph (not current time)
      // This ensures only nodes created AFTER this submit will be marked as "NEW"
      let latestTimestamp = 0
      for (const node of Object.values(graphData.nodes)) {
        if (node.timestamp) {
          const nodeTime = new Date(node.timestamp).getTime()
          if (nodeTime > latestTimestamp) {
            latestTimestamp = nodeTime
          }
        }
      }
      lastSubmissionTimestamp.value = latestTimestamp || Date.now()
      
      // Snapshot current selections for sort priority
      Object.keys(selectionsAtLastSubmit).forEach(key => delete selectionsAtLastSubmit[key])
      Object.assign(selectionsAtLastSubmit, JSON.parse(JSON.stringify(userSelections)))
      
      // Update graph change log: snapshot current nodes
      graphChangeLog.nodesAtLastSubmit.clear()
      for (const nodePath in graphData.nodes) {
        graphChangeLog.nodesAtLastSubmit.add(nodePath)
      }
      
      // Recompute recursive new counts (should be all 0 now)
      computeRecursiveNewCounts()
      
      // Clear force-expand markers so collapse can take effect
      // (Auto-expand will re-trigger when truly NEW content arrives in next phase)
      const forceExpandCount = Object.keys(questionsToForceExpand).length
      if (forceExpandCount > 0) {
        console.log(`🧹 Clearing ${forceExpandCount} force-expand directive(s) (submit complete)`)
      }
      for (const key in questionsToForceExpand) {
        delete questionsToForceExpand[key]
      }
      
      // Smart collapse: collapse ONLY questions we interacted with
      // Questions we didn't touch stay expanded (user still considering them)
      console.log(`📦 Marking ${interactedQuestions.size} interacted question(s) for collapse`)
      
      // Clear previous collapse markers (from last submit)
      const oldCollapseCount = Object.keys(questionsToCollapse).length
      if (oldCollapseCount > 0) {
        console.log(`  🧹 Clearing ${oldCollapseCount} old collapse directive(s) from previous submit`)
      }
      for (const key in questionsToCollapse) {
        delete questionsToCollapse[key]
      }
      
      // Mark interacted questions AND their EXPANDED ancestors for collapse
      // (If you interacted with a nested question and its ancestor was expanded, you saw it)
      const questionsToCollapseSet = new Set()
      const orphanedInteractions = []
      
      for (const questionPath of interactedQuestions) {
        // Edge case: Check if question still exists
        if (!graphData.nodes[questionPath]) {
          orphanedInteractions.push(questionPath)
          continue
        }
        
        // Mark the interacted question itself
        questionsToCollapseSet.add(questionPath)
        
        // Mark all EXPANDED ancestors (they were visible in the path)
        const ancestors = getAncestorQuestions(questionPath)
        for (const ancestorPath of ancestors) {
          if (expandedQuestions.has(ancestorPath)) {
            questionsToCollapseSet.add(ancestorPath)
          }
        }
      }
      
      // Convert to timestamp-based object for reactivity
      for (const questionPath of questionsToCollapseSet) {
        questionsToCollapse[questionPath] = Date.now()
        console.log(`  ✅ Will collapse: ${questionPath}`)
      }
      
      if (orphanedInteractions.length > 0) {
        console.warn(`  ⚠️  Edge case: ${orphanedInteractions.length} interacted question(s) no longer exist in graph`, orphanedInteractions)
      }
      
      console.log(`  📊 Checked ${expandedQuestions.size} expanded question(s), marked ${questionsToCollapseSet.size} for collapse`)
      
      // Clear interaction tracking for next submission cycle
      interactedQuestions.clear()
        
      // Check if any layers should collapse due to all siblings being dismissed
      checkAllLayersForDismissals()
    }
    
    function checkAllLayersForDismissals() {
      // Check all tracked layers to see if all siblings are dismissed
      for (const layerPath in layerInteractionState) {
        const layerState = layerInteractionState[layerPath]
        if (!layerState.nodesAtFirstClick) continue
        
        // Get all nodes in this layer
        const nodesInLayer = Array.from(layerState.nodesAtFirstClick)
        
        // Check if all are dismissed
        const allDismissed = nodesInLayer.every(nodePath => {
          const userVote = userSelections[`vote:${nodePath}`]
          if (userVote === 'X' || userVote === '❌') return true
          
          const node = graphData.nodes[nodePath]
          if (!node || !node.votes) return false
          return node.votes.some(vote => vote.vote === '❌' || vote.vote === 'X')
        })
        
        if (allDismissed) {
          // All siblings dismissed - ensure layer stays collapsed
          layerState.shouldCollapse = true
          layerState.userClickedToExpand = false
        }
      }
    }

    function restoreUserSelectionsFromGraph() {
      // Scan all nodes for user's votes and replay them in chronological order
      console.log('🔄 Restoring user selections from graph.log...')
      
      // Collect all user votes with their paths and timestamps
      const allUserVotes = []
      for (const [path, node] of Object.entries(graphData.nodes)) {
        if (!node.votes) continue
        
        // Find user's votes (look for User or Web UI in specialist name)
        const userVotes = node.votes.filter(vote => 
          vote.specialist && (
            vote.specialist === 'User' || 
            vote.specialist.includes('User') ||
            vote.specialist.includes('Web UI')
          )
        )
        
        for (const vote of userVotes) {
          allUserVotes.push({ path, vote })
        }
      }
      
      // Sort by timestamp to replay in chronological order
      allUserVotes.sort((a, b) => {
        const aTime = a.vote.timestamp || 0
        const bTime = b.vote.timestamp || 0
        return aTime < bTime ? -1 : aTime > bTime ? 1 : 0
      })
      
      // Replay votes in order
      for (const { path, vote: latestVote } of allUserVotes) {
        
        // User uses [✅] for selections, [➖] for neutral/deselection (specialists use [👍]/[👎])
        if (latestVote.vote === '✅') {
          // This is a user selection - restore it
          // Determine if this is a question or answer
          const isAnswer = path.match(/\[A\]|\[A:/)
          
          if (isAnswer) {
            // Extract question path
            const questionMatch = path.match(/^(.*?\[Q:[^\]]+\]\[[^\]]+\])/)
            if (questionMatch) {
              const questionPath = questionMatch[1]
              const questionNode = graphData.nodes[questionPath]
              
              if (questionNode) {
                const questionType = questionPath.match(/\[Q:(single|multiple|open)\]/)?.[1] || 'single'
                
                if (questionType === 'single') {
                  // Single choice - set this as the selected answer
                  userSelections[questionPath] = {
                    type: 'single',
                    answers: path
                  }
                  // Mark this answer as seen (removes NEW badge)
                  graphChangeLog.seenNodes.add(path)
                } else if (questionType === 'multiple') {
                  // Multiple choice - add to selected answers
                  if (!userSelections[questionPath]) {
                    userSelections[questionPath] = {
                      type: 'multiple',
                      answers: []
                    }
                  }
                  if (!userSelections[questionPath].answers.includes(path)) {
                    userSelections[questionPath].answers.push(path)
                  }
                  // Mark this answer as seen (removes NEW badge)
                  graphChangeLog.seenNodes.add(path)
                }
                
                // Track this layer as having been interacted with
                // This is needed for collapse-on-submit to work
                const layerPath = getLayerPath(questionPath)
                if (!layerInteractionState[layerPath]) {
                  // Get all sibling questions that exist NOW (at page load)
                  const siblingQuestions = getSiblingQuestions(questionPath)
                  layerInteractionState[layerPath] = {
                    firstClickAt: Date.now(),
                    nodesAtFirstClick: new Set(siblingQuestions),
                    shouldCollapse: false,
                    userClickedToExpand: false
                  }
                }
              }
            }
          }
        } else if (latestVote.vote === '➖') {
          // User marked this as neutral/deselected - ensure it's removed from selections
          const isAnswer = path.match(/\[A\]|\[A:/)
          
          if (isAnswer) {
            const questionMatch = path.match(/^(.*?\[Q:[^\]]+\]\[[^\]]+\])/)
            if (questionMatch) {
              const questionPath = questionMatch[1]
              
              if (userSelections[questionPath] && userSelections[questionPath].type === 'multiple') {
                // Remove from multiple choice selections
                const idx = userSelections[questionPath].answers.indexOf(path)
                if (idx !== -1) {
                  userSelections[questionPath].answers.splice(idx, 1)
                }
                // If no answers left, remove the question entirely
                if (userSelections[questionPath].answers.length === 0) {
                  delete userSelections[questionPath]
                }
              } else if (userSelections[questionPath] && userSelections[questionPath].answers === path) {
                // Remove single choice selection
                delete userSelections[questionPath]
              }
            }
          }
        }
      }
      
      // Recompute recursive NEW counts after marking restored selections as seen
      // This will cascade the "seen" status up to parent answers
      computeRecursiveNewCounts()
      
      console.log(`✅ Restored ${Object.keys(userSelections).length} user selection(s)`)
    }
    
    function updateGraphData(newData) {
      // Preserve user selections - NEVER clear their choices
      // Only add new nodes/questions
      
      // Track which nodes are new
      const oldNodePaths = new Set(Object.keys(graphData.nodes))
      const newNodePaths = Object.keys(newData.nodes || {})
      const addedNodes = newNodePaths.filter(path => !oldNodePaths.has(path))
      
      // If this is the first load (no existing nodes), restore user selections from graph data
      const isFirstLoad = oldNodePaths.size === 0
      
      Object.assign(graphData.nodes, newData.nodes || {})
      Object.assign(graphData.vote_tally, newData.vote_tally || {})
      Object.assign(graphData.specialist_stats, newData.specialist_stats || {})
      
      // Restore user selections from graph on first load OR if we have data but selections are empty
      // (handles case where first graph_update has 0 nodes, real data comes on second update)
      const hasSelectionsRestored = Object.keys(userSelections).filter(k => !k.startsWith('vote:')).length > 0
      const hasNodesToRestore = Object.keys(graphData.nodes).length > 0
      
      if (isFirstLoad || (hasNodesToRestore && !hasSelectionsRestored)) {
        restoreUserSelectionsFromGraph()
        // On first load, set lastSubmissionTimestamp to NOW so existing nodes from graph.log
        // are NOT marked as "new". Only nodes added AFTER this point will be marked as NEW.
        lastSubmissionTimestamp.value = Date.now()
        // Populate nodesAtLastSubmit with ALL current nodes so they're not marked as NEW
        graphChangeLog.nodesAtLastSubmit.clear()
        for (const nodePath in graphData.nodes) {
          graphChangeLog.nodesAtLastSubmit.add(nodePath)
        }
      }
      
      // Compute recursive new counts for all nodes
      computeRecursiveNewCounts()
      
      // AUTO-EXPANSION LOGIC: When ANY node gets marked as "NEW", force user to see it
      // by expanding all parent questions from deepest to root
      if (addedNodes.length > 0 && !isFirstLoad) {
        console.log(`🆕 Detected ${addedNodes.length} new node(s):`, addedNodes)
        
        // Check if any new nodes would appear in the current viewport
        // If yes, show modal overlay before updating the UI
        const hasViewportConflict = checkViewportConflict(addedNodes)
        
        if (hasViewportConflict) {
          console.log(`⚠️  New nodes detected in active viewport - showing modal overlay`)
          newContentCount.value = addedNodes.length
          pendingNewNodes.value = addedNodes
          showNewContentModal.value = true
          // Don't return - continue with expansion logic so nodes render behind modal
        }
        
        // Strategy: Work from deepest NEW nodes outward
        // For each NEW node (question or answer), expand the parent question chain
        // so the NEW node becomes visible to the user
        
        const questionsToExpand = new Set()
        
        // 1. Process each NEW node to determine what needs to be expanded
        for (const nodePath of addedNodes) {
          const isQuestion = nodePath.match(/\[Q:[^\]]+\]\[[^\]]+\]$/)
          
          if (isQuestion) {
            // NEW question node
            // Example: [Q:single][Parent][A][Answer1][Q:single][NewChild]
            // Must expand: [Q:single][Parent][A][Answer1][Q:single][NewChild] (the question itself)
            //              [Q:single][Parent] (so NewChild is visible)
            questionsToExpand.add(nodePath)
            console.log(`  🆕 NEW question: "${nodePath}"`)
          } else {
            // NEW answer node  
            // Example: [Q:single][Parent][A][NewAnswer]
            // Must expand: [Q:single][Parent] (so NewAnswer is visible)
            //              and any ancestors of Parent
            const parentQuestion = getParentQuestion(nodePath)
            if (parentQuestion) {
              questionsToExpand.add(parentQuestion)
              console.log(`  🆕 NEW answer under: "${parentQuestion}"`)
            }
          }
        }
        
        // 2. Belt and suspenders: Also find existing questions with NEW descendants
        //    (recursiveNewCounts tracks propagation up the tree)
        for (const nodePath in graphData.nodes) {
          if (!nodePath.match(/\[Q:[^\]]+\]\[[^\]]+\]$/)) continue
          
          const newCount = graphChangeLog.recursiveNewCounts[nodePath] || 0
          if (newCount > 0) {
            questionsToExpand.add(nodePath)
          }
        }
        
        if (questionsToExpand.size > 0) {
          const activeCollapseCount = Object.keys(questionsToCollapse).length
          console.log(`📂 Auto-expanding ${questionsToExpand.size} question(s) with NEW items (deepest → root)`)
          if (activeCollapseCount > 0) {
            console.log(`  ⚠️  ${activeCollapseCount} active collapse directive(s) will be checked for conflicts`)
          }
        }
        
        // 3. Expand all identified questions AND their ancestor chains
        //    expandQuestionAndAllAncestors adds timestamps to questionsToForceExpand
        //    which triggers watchers in QuestionNode.vue to set isExpanded=true
        for (const questionPath of questionsToExpand) {
          expandQuestionAndAllAncestors(questionPath)
        }
        
        // 4. Edge case detection: Log final state of directive maps after processing
        const finalForceExpandCount = Object.keys(questionsToForceExpand).length
        const finalCollapseCount = Object.keys(questionsToCollapse).length
        
        if (finalForceExpandCount > 0 || finalCollapseCount > 0) {
          console.log(`📊 Final directive state: ${finalForceExpandCount} force-expand, ${finalCollapseCount} collapse`)
          
          // Edge case: Detect orphaned collapse directives (collapse for questions that don't exist)
          const orphanedCollapse = []
          for (const path in questionsToCollapse) {
            if (!graphData.nodes[path]) {
              orphanedCollapse.push(path)
            }
          }
          if (orphanedCollapse.length > 0) {
            console.warn(`⚠️  Edge case: ${orphanedCollapse.length} orphaned collapse directive(s) (questions don't exist)`, orphanedCollapse)
            // Clean them up
            for (const path of orphanedCollapse) {
              delete questionsToCollapse[path]
            }
          }
          
          // Edge case: Detect if same question in BOTH maps (should never happen)
          const conflicts = []
          for (const path in questionsToForceExpand) {
            if (questionsToCollapse[path]) {
              conflicts.push(path)
            }
          }
          if (conflicts.length > 0) {
            console.error(`🚨 Critical edge case: ${conflicts.length} question(s) in BOTH force-expand AND collapse!`, conflicts)
          }
        }
      } else if (!isFirstLoad) {
        console.log(`✅ No new nodes detected (vote-only update) - layers remain as-is`)
        
        // Edge case: If this is a vote-only update, force-expand directives should be cleared
        // (they're only for NEW content arrival)
        const lingering = Object.keys(questionsToForceExpand).length
        if (lingering > 0) {
          console.warn(`  ⚠️  Edge case: ${lingering} lingering force-expand directive(s) on vote-only update (should have been cleared on submit)`)
        }
      }
    }
    
    function expandLayerAndParents(layerPath) {
      // Expand the given layer
      if (layerInteractionState[layerPath]) {
        layerInteractionState[layerPath].shouldCollapse = false
        layerInteractionState[layerPath].userClickedToExpand = true
      }
      
      // Walk up to root, expanding all parent layers
      let currentPath = layerPath
      while (currentPath) {
        const parentPath = getLayerPath(currentPath)
        if (layerInteractionState[parentPath]) {
          layerInteractionState[parentPath].shouldCollapse = false
          layerInteractionState[parentPath].userClickedToExpand = true
        }
        currentPath = parentPath
      }
    }
    
    function expandParentsOnly(layerPath) {
      // Expand parent layers to make new nodes visible
      // BUT respect shouldCollapse flag for layers that user has already collapsed
      // This prevents re-expanding already-selected questions when new siblings appear
      
      // Walk up to root, expanding parent layers only
      let currentPath = layerPath
      while (currentPath) {
        const parentPath = getLayerPath(currentPath)
        if (parentPath !== undefined && layerInteractionState[parentPath]) {
          // Only set userClickedToExpand if layer is NOT marked for collapse
          if (!layerInteractionState[parentPath].shouldCollapse) {
            layerInteractionState[parentPath].shouldCollapse = false
            layerInteractionState[parentPath].userClickedToExpand = true
          }
          // If shouldCollapse is true, leave it alone - existing nodes stay collapsed
          // but new nodes (which have existedAtFirstClick = false) will still expand
        }
        currentPath = parentPath
      }
    }
    
    // Track which specific questions should be force-expanded (not entire layers)
    // Use object with timestamps instead of Set for reliable Vue 3 reactivity
    const questionsToForceExpand = reactive({})
    
    // Track which questions are currently expanded (actual state, not directives)
    // QuestionNode components will report their expanded state here
    const expandedQuestions = reactive(new Set())
    
    function updateQuestionExpandedState(questionPath, isExpanded) {
      console.log(`🔔 updateQuestionExpandedState ENTERED: path="${questionPath}", isExpanded=${isExpanded}, currentSize=${expandedQuestions.size}`)
      if (isExpanded) {
        expandedQuestions.add(questionPath)
        console.log(`📂 Tracking expanded: "${questionPath}" (total: ${expandedQuestions.size})`)
      } else {
        expandedQuestions.delete(questionPath)
        console.log(`📁 Tracking collapsed: "${questionPath}" (total: ${expandedQuestions.size})`)
      }
      console.log(`🔔 updateQuestionExpandedState EXITED: currentSize=${expandedQuestions.size}`)
    }
    
    function expandQuestionAndAllAncestors(questionPath) {
      // Expand a specific question (because it has new descendants at ANY depth)
      // and ALL its ancestor questions (to make it visible)
      // but NOT sibling questions at any level
      
      const pathsToCleanup = []
      const duplicates = []
      
      // Edge case: Detect if already in force-expand (shouldn't happen often but track it)
      if (questionsToForceExpand[questionPath]) {
        duplicates.push(questionPath)
      }
      
      // Add this question to the force-expand map with timestamp
      questionsToForceExpand[questionPath] = Date.now()
      
      // Clear any collapse directive for this question (force-expand overrides)
      if (questionsToCollapse[questionPath]) {
        delete questionsToCollapse[questionPath]
        pathsToCleanup.push(questionPath)
      }
      
      // Get all ancestor questions
      const ancestors = getAncestorQuestions(questionPath)
      
      // Add all ancestors to force-expand map with timestamps
      for (const ancestorPath of ancestors) {
        // Edge case: Track duplicates
        if (questionsToForceExpand[ancestorPath]) {
          duplicates.push(ancestorPath)
        }
        
        questionsToForceExpand[ancestorPath] = Date.now()
        
        // Clear collapse directives for ancestors too
        if (questionsToCollapse[ancestorPath]) {
          delete questionsToCollapse[ancestorPath]
          pathsToCleanup.push(ancestorPath)
        }
      }
      
      console.log(`  🔓 Force-expanding question "${questionPath}" and ${ancestors.length} ancestor(s)`)
      if (pathsToCleanup.length > 0) {
        console.log(`  🧹 Cleaned ${pathsToCleanup.length} stale collapse directive(s) (force-expand overrides)`)
      }
      if (duplicates.length > 0) {
        console.log(`  ⚠️  Edge case: ${duplicates.length} question(s) already in force-expand (updating timestamp)`)
      }
    }

    function connectWebSocket() {
      const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
      const wsUrl = import.meta.env.DEV 
        ? 'http://localhost:5000'
        : `${protocol}//${window.location.host}`

      socket.value = io(wsUrl, {
        transports: ['websocket'], // Force WebSocket only, no polling fallback
        autoConnect: false, // Don't connect immediately - set up handlers first
        reconnection: true,
        reconnectionAttempts: Infinity, // Never stop trying to reconnect
        reconnectionDelay: 500, // Start reconnecting after 500ms
        reconnectionDelayMax: 2000, // Max 2s between reconnection attempts
        timeout: 20000, // Increased from 5s to 20s
        forceNew: true // Force new connection instead of reusing
      })

      // Set up ALL event handlers BEFORE connecting
      socket.value.on('graph_update', (data) => {
        const now = new Date()
        const timestamp = `${now.getHours().toString().padStart(2,'0')}:${now.getMinutes().toString().padStart(2,'0')}:${now.getSeconds().toString().padStart(2,'0')}.${now.getMilliseconds().toString().padStart(3,'0')}`
        const startTime = performance.now()
        const nodeCount = Object.keys(data.nodes || {}).length
        console.log(`🕐 [${timestamp}] 📥 Received graph_update with ${nodeCount} nodes`)
        console.log(`🔄 isLoading was ${isLoading.value}`)
        
        // Remove loading overlay IMMEDIATELY when data arrives
        // Don't wait for rendering to complete
        if (isLoading.value) {
          console.log('✅ Removing loading overlay')
          isLoading.value = false
        }
        
        updateGraphData(data)
        const dataUpdateTime = performance.now()
        console.log(`⏱️  Data update: ${(dataUpdateTime - startTime).toFixed(2)}ms`)
        
        // Measure Vue rendering time separately (non-blocking)
        nextTick(() => {
          const renderTime = performance.now()
          const renderTimestamp = new Date()
          const renderTs = `${renderTimestamp.getHours().toString().padStart(2,'0')}:${renderTimestamp.getMinutes().toString().padStart(2,'0')}:${renderTimestamp.getSeconds().toString().padStart(2,'0')}.${renderTimestamp.getMilliseconds().toString().padStart(3,'0')}`
          console.log(`🕐 [${renderTs}] ⏱️  Vue render: ${(renderTime - dataUpdateTime).toFixed(2)}ms`)
          console.log(`⏱️  Total time: ${(renderTime - startTime).toFixed(2)}ms`)
        })
      })

      socket.value.on('connect', () => {
        try {
          const transport = socket.value.io?.engine?.transport?.name || 'unknown'
          console.log(`✅ Connected to Axion Swarm server via ${transport}`)
        } catch (e) {
          console.log(`✅ Connected to Axion Swarm server`)
        }
        console.log(`🔄 isLoading = ${isLoading.value}`)
        connectionStatus.value = 'connected'
        
        // ALWAYS request initial state on connect to ensure we have data
        console.log('📤 Requesting initial graph state...')
        const requestTime = performance.now()
        socket.value.emit('request_initial_state')
        console.log(`⏱️  Request sent at ${requestTime}ms`)
        
        // Set a timeout to warn if no response
        setTimeout(() => {
          if (isLoading.value) {
            console.warn('⚠️  Still loading after 3 seconds - no graph_update received?')
          }
        }, 3000)
      })

      socket.value.on('disconnect', (reason) => {
        const now = new Date()
        const timestamp = `${now.getHours().toString().padStart(2,'0')}:${now.getMinutes().toString().padStart(2,'0')}:${now.getSeconds().toString().padStart(2,'0')}.${now.getMilliseconds().toString().padStart(3,'0')}`
        console.log(`🕐 [${timestamp}] ⚠️  Disconnected from server. Reason: ${reason}`)
        connectionStatus.value = 'disconnected'
        
        // Immediately try to reconnect if disconnect wasn't intentional
        if (reason === 'io server disconnect') {
          console.log('🔄 Server closed connection, reconnecting...')
          socket.value.connect()
        } else if (reason === 'transport close' || reason === 'ping timeout') {
          console.log('🔄 Connection lost, auto-reconnecting...')
        }
      })
      
      socket.value.on('reconnect_attempt', (attemptNumber) => {
        console.log(`🔄 Reconnection attempt #${attemptNumber}...`)
        connectionStatus.value = 'connecting'
      })
      
      socket.value.on('reconnect', (attemptNumber) => {
        const now = new Date()
        const timestamp = `${now.getHours().toString().padStart(2,'0')}:${now.getMinutes().toString().padStart(2,'0')}:${now.getSeconds().toString().padStart(2,'0')}.${now.getMilliseconds().toString().padStart(3,'0')}`
        console.log(`🕐 [${timestamp}] ✅ Reconnected after ${attemptNumber} attempt(s)`)
        connectionStatus.value = 'connected'
        
        // Request fresh state after reconnection
        console.log('📤 Requesting fresh state after reconnection...')
        socket.value.emit('request_initial_state')
      })

      socket.value.on('connect_error', (error) => {
        console.error('❌ Connection error:', error)
        console.error('Error type:', error.type)
        console.error('Error message:', error.message)
        connectionStatus.value = 'disconnected'
        
        // If still loading after connection error, remove overlay and show error state
        if (isLoading.value) {
          console.warn('⚠️  Connection failed during initial load')
          isLoading.value = false
        }
      })
      
      socket.value.on('connect_timeout', () => {
        console.error('❌ Connection timeout')
        if (isLoading.value) {
          console.warn('⚠️  Connection timed out during initial load')
          isLoading.value = false
        }
      })
      
      socket.value.on('error', (error) => {
        console.error('❌ Socket error:', error)
      })

      socket.value.on('submission_success', (data) => {
        console.log('✅ Submission successful:', data.commands.length, 'decision(s) submitted')
      })

      socket.value.on('submission_error', (data) => {
        console.error('Submission error:', data)
        alert(`❌ Error submitting decisions: ${data.error}`)
      })
      
      socket.value.on('continue_success', (data) => {
        console.log('✅ Continue signal sent to swarm')
      })
      
      socket.value.on('continue_error', (data) => {
        console.error('Continue error:', data)
        alert(`❌ Error continuing phase: ${data.error}`)
      })
      
      // Phase status updates from backend
      socket.value.on('phase_status', (data) => {
        phaseStatus.waiting = data.waiting || false
        phaseStatus.currentPhase = data.phase || 0
        phaseStatus.isFinal = data.is_final || false
        console.log(`📊 Phase status update: Phase ${phaseStatus.currentPhase}, waiting=${phaseStatus.waiting}, final=${phaseStatus.isFinal}`)
      })

      // NOW connect after all handlers are registered
      socket.value.connect()
    }

    onMounted(() => {
      connectionStatus.value = 'connecting'
      connectWebSocket()
    })

    onUnmounted(() => {
      if (socket.value) {
        socket.value.disconnect()
      }
    })

    return {
      graphData,
      userSelections,
      layerInteractionState,
      lastSubmissionTimestamp,
      selectionsAtLastSubmit,
      graphChangeLog,
      questionsToForceExpand,
      questionsToCollapse,
      connectionStatus,
      connectionStatusText,
      phaseStatus,
      phaseStatusIcon,
      phaseStatusText,
      phaseStatusClass,
      isLoading,
      showNewContentModal,
      newContentCount,
      acknowledgeNewContent,
      rootQuestions,
      totalVotes,
      hasSelections,
      hasChanges,
      unansweredQuestionCount,
      pendingDecisionCount,
      isQuestionPending,
      hideDuplicates,
      toggleHideDuplicates,
      displayedRootQuestions,
      updateSelection,
      updateVote,
      handleImmediateSubmit,
      handleThoughtSubmit,
      handleSubmit,
      handleContinuePhase,
      updateQuestionExpandedState,
      handleRootQuestionViewportChange
    }
  }
}
</script>

<style scoped>
/* Loading Overlay */
.loading-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.85);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 9999;
  backdrop-filter: blur(4px);
}

.loading-content {
  text-align: center;
  color: white;
}

.loading-content h2 {
  margin-top: 1.5rem;
  font-size: 1.5rem;
  font-weight: 600;
}

.loading-content p {
  margin-top: 0.5rem;
  color: rgba(255, 255, 255, 0.7);
  font-size: 0.95rem;
}

/* New Content Modal Overlay */
.new-content-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.75);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 9998;
  backdrop-filter: blur(3px);
  animation: fadeIn 0.3s ease-out;
}

.new-content-modal {
  background: white;
  border-radius: 12px;
  padding: 2rem;
  max-width: 500px;
  box-shadow: 0 20px 60px rgba(0, 0, 0, 0.3);
  text-align: center;
  animation: slideUp 0.3s ease-out;
}

.modal-icon {
  font-size: 3rem;
  margin-bottom: 1rem;
  animation: pulse-new 2s ease-in-out infinite;
}

.new-content-modal h2 {
  margin: 0 0 1rem 0;
  font-size: 1.5rem;
  color: #2d3748;
}

.modal-message {
  font-size: 1rem;
  color: #4a5568;
  margin-bottom: 0.5rem;
  line-height: 1.6;
}

.modal-submessage {
  font-size: 0.9rem;
  color: #718096;
  margin-bottom: 1.5rem;
  font-style: italic;
}

.acknowledge-button {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  border: none;
  padding: 0.75rem 2rem;
  border-radius: 8px;
  font-size: 1rem;
  font-weight: 600;
  cursor: pointer;
  box-shadow: 0 4px 12px rgba(102, 126, 234, 0.4);
  transition: all 0.2s;
}

.acknowledge-button:hover {
  transform: translateY(-2px);
  box-shadow: 0 6px 16px rgba(102, 126, 234, 0.5);
}

.acknowledge-button:active {
  transform: translateY(0);
}

@keyframes fadeIn {
  from {
    opacity: 0;
  }
  to {
    opacity: 1;
  }
}

@keyframes slideUp {
  from {
    opacity: 0;
    transform: translateY(20px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

.loading-spinner {
  width: 60px;
  height: 60px;
  border: 4px solid rgba(255, 255, 255, 0.1);
  border-top-color: #667eea;
  border-radius: 50%;
  animation: spin 1s linear infinite;
  margin: 0 auto;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

.content-wrapper.dimmed {
  pointer-events: none;
  opacity: 0.5;
}

.app-container {
  min-height: 100vh;
  background: #f5f5f5;
}

.page-wrapper {
  max-width: 1200px;
  margin: 0 auto;
  padding: 20px;
}

.app-header {
  background: white;
  padding: 30px;
  border-radius: 8px;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
  margin-bottom: 30px;
  position: relative;
}

.app-header h1 {
  margin: 0 0 10px 0;
  color: #333;
  font-size: 1.75rem;
  font-weight: 600;
}

.app-header .subtitle {
  color: #666;
  font-size: 0.95em;
  margin: 0 0 1rem 0;
  line-height: 1.5;
}

.status-bar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 2rem;
  margin-top: 1rem;
}

.connection-status {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  font-size: 0.875rem;
  color: #666;
}

.phase-status {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  padding: 0.5rem 1rem;
  border-radius: 6px;
  font-size: 0.875rem;
  font-weight: 500;
  transition: all 0.3s;
}

.phase-status.waiting {
  background: #fed7aa;
  color: #7c2d12;
  border: 2px solid #fb923c;
}

.phase-status.running {
  background: #d1fae5;
  color: #065f46;
  border: 2px solid #34d399;
}

.phase-status.final {
  background: #ddd6fe;
  color: #4c1d95;
  border: 2px solid #a78bfa;
}

.phase-indicator {
  font-size: 1.2em;
}

.phase-text {
  font-weight: 600;
}

.status-indicator {
  width: 10px;
  height: 10px;
  border-radius: 50%;
  animation: pulse 2s infinite;
}

.status-indicator.connected {
  background: #48bb78;
}

.status-indicator.connecting {
  background: #ed8936;
}

.status-indicator.disconnected {
  background: #f56565;
}

@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.5; }
}

.content-wrapper {
  display: flex;
  gap: 20px;
}

.sidebar {
  width: 300px;
  background: white;
  border-radius: 8px;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
  padding: 1.5rem;
  height: fit-content;
  position: sticky;
  top: 20px;
}

.toggle-panel {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  padding: 1rem;
  background: #f8fafc;
  border-radius: 6px;
  margin-bottom: 1.5rem;
  border: 1px solid #e2e8f0;
}

.toggle-switch {
  position: relative;
  display: inline-block;
  width: 50px;
  height: 26px;
  flex-shrink: 0;
}

.toggle-switch input {
  opacity: 0;
  width: 0;
  height: 0;
}

.toggle-slider {
  position: absolute;
  cursor: pointer;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background-color: #cbd5e0;
  transition: 0.3s;
  border-radius: 26px;
}

.toggle-slider:before {
  position: absolute;
  content: "";
  height: 20px;
  width: 20px;
  left: 3px;
  bottom: 3px;
  background-color: white;
  transition: 0.3s;
  border-radius: 50%;
}

.toggle-switch input:checked + .toggle-slider {
  background-color: #4a90e2;
}

.toggle-switch input:checked + .toggle-slider:before {
  transform: translateX(24px);
}

.toggle-label {
  font-size: 0.9rem;
  color: #4a5568;
  font-weight: 500;
  user-select: none;
}

.stats-panel,
.specialists-panel {
  margin-bottom: 2rem;
}

.stats-panel h3,
.specialists-panel h3 {
  font-size: 1rem;
  margin-bottom: 1rem;
  color: #4a5568;
}

.stat-item {
  display: flex;
  justify-content: space-between;
  padding: 0.5rem 0;
  border-bottom: 1px solid #f7fafc;
}

.stat-item label {
  color: #718096;
  font-size: 0.875rem;
}

.stat-item span {
  font-weight: 600;
  color: #2d3748;
}

.specialist-item {
  padding: 0.75rem;
  background: #f7fafc;
  border-radius: 6px;
  margin-bottom: 0.5rem;
}

.specialist-name {
  font-weight: 500;
  margin-bottom: 0.25rem;
  color: #2d3748;
}

.specialist-votes {
  display: flex;
  gap: 1rem;
  font-size: 0.875rem;
}

.vote-up {
  color: #48bb78;
}

.vote-down {
  color: #f56565;
}

.main-content {
  flex: 1;
  background: white;
  padding: 30px;
  border-radius: 8px;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
}

.empty-state {
  text-align: center;
  padding: 4rem 2rem;
  color: #718096;
}

.spinner {
  margin: 2rem auto;
  width: 40px;
  height: 40px;
  border: 4px solid #e2e8f0;
  border-top-color: #667eea;
  border-radius: 50%;
  animation: spin 1s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

.decision-form {
  width: 100%;
}

.legend {
  background: #f8f9fa;
  padding: 15px;
  border-radius: 6px;
  margin-bottom: 20px;
  font-size: 0.9em;
}

.legend-item {
  display: inline-block;
  margin-right: 20px;
  margin-bottom: 5px;
}

.legend-badge {
  display: inline-block;
  width: 12px;
  height: 12px;
  border-radius: 2px;
  margin-right: 5px;
  vertical-align: middle;
}

.submit-section {
  margin-top: 40px;
  padding-top: 20px;
  border-top: 2px solid #e0e0e0;
  text-align: center;
}

.submit-button {
  background: #4a90e2;
  color: white;
  border: none;
  padding: 12px 40px;
  font-size: 1.1em;
  border-radius: 6px;
  cursor: pointer;
  transition: background 0.2s;
  display: flex;
  align-items: center;
  gap: 0.5rem;
  justify-content: center;
  width: 100%;
}

.submit-button:hover:not(:disabled) {
  background: #357abd;
}

.submit-button:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.decision-count-badge {
  background: rgba(255, 255, 255, 0.3);
  padding: 0.25rem 0.6rem;
  border-radius: 12px;
  font-size: 0.9em;
  font-weight: 600;
  min-width: 24px;
  text-align: center;
}

.continue-button {
  background: #48bb78;
  color: white;
  border: none;
  padding: 12px 40px;
  font-size: 1.1em;
  border-radius: 6px;
  cursor: pointer;
  transition: background 0.2s;
  margin-top: 1rem;
  display: flex;
  align-items: center;
  gap: 0.5rem;
  justify-content: center;
  width: 100%;
}

.continue-button:hover {
  background: #38a169;
}

.continue-button.has-pending {
  background: #ed8936;
}

.continue-button.has-pending:hover {
  background: #dd6b20;
}

.continue-button:disabled {
  opacity: 0.5;
  cursor: not-allowed;
  background: #9ca3af;
}

.pending-badge {
  background: rgba(255, 255, 255, 0.25);
  padding: 0.25rem 0.5rem;
  border-radius: 4px;
  font-size: 0.9em;
}

.all-answered-badge {
  background: rgba(255, 255, 255, 0.25);
  padding: 0.25rem 0.5rem;
  border-radius: 4px;
  font-size: 0.9em;
}

.help-text {
  margin-top: 0.75rem;
  color: #718096;
  font-size: 0.875rem;
}

.help-text.continue-help {
  margin-top: 0.5rem;
}
</style>

