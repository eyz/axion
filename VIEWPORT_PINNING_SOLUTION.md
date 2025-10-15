# Viewport-Based Pinning Solution

> **⚠️ EXPERIMENTAL UX FEATURE - TESTING IN PROGRESS**
> 
> This is an initial implementation to address reordering issues. The behavior may be adjusted based on real-world testing and user feedback. Current approach uses Intersection Observer API to detect viewport visibility with a 100px buffer. We may refine the buffer size, threshold, or overall strategy as we observe how it performs in practice.

## Problem
Components in the Vue frontend were reordering based on importance/votes while visible on screen, causing items to move "out from under" the user as they tried to click them - creating a frustrating UX.

## Solution
Implemented a **viewport-based pinning mechanism** that:
1. **Detects when questions are in the viewport** using Intersection Observer API
2. **Freezes the sort order** when visible (regardless of expansion state)
3. **Allows reordering to happen** when off-screen (user can't see it)
4. **Prevents any visible reordering** - items only reorder when scrolled out of view

## How It Works

### Key Components

#### 1. Hover Detection (`QuestionNode.vue`)
- Listens for mouseenter/mouseleave events on each question node
- 150ms delay before unpinning to handle brief mouse movements
- Prevents accidental unpinning if component shifts slightly
- Timing based on UX latency guidelines (immediate: 0-100ms, natural: 100-1000ms)

#### 2. Pinned Order State
```javascript
const questionNodeRef = ref(null)            // Template ref to question node
const isHovering = ref(false)                // Is user hovering?
const pinnedAnswerOrder = ref(null)          // Frozen order when hovering
let hoverTimeout = null                      // Delay before unpinning
```

#### 3. Smart Sorting Logic (`directAnswers` computed)
```javascript
// When hovering: Use pinned order
if (isHovering.value && pinnedAnswerOrder.value) {
  // Keep pinned order, append new items at end
  return [...pinnedOrder, ...newItems]
}

// When not hovering: Compute fresh sort
const sorted = answers.sort(/* normal sorting logic */)

// Update pinned order when not hovering
if (!isHovering.value) {
  pinnedAnswerOrder.value = sorted
}

return sorted
```

### Behavior

**When user hovers over a question:**
- Current order is "pinned" (frozen) immediately
- All answers and nested questions stay in their positions
- Items don't move even if votes/importance changes
- New items appear at the end (don't disrupt existing layout)
- 150ms grace period before unpinning on mouse leave

**When user moves mouse away:**
- After 150ms delay, reordering is allowed to happen
- Sort order updates based on votes/importance
- Pinned order is updated to the new sorted order

**When user hovers again:**
- They see the updated order (reordering happened while not hovering)
- Order is immediately pinned again

## Benefits

1. **No visible reordering** - Users never see items jumping around while hovering over them
2. **Still maintains importance sorting** - Items reorder when not hovering, so most important items bubble up
3. **Smooth UX** - No jarring movements or "chasing" items with the mouse
4. **Intent-based** - Pinning happens when user shows interest (hovering), not just visibility
5. **Performance efficient** - Simple DOM events, no polling or observers needed
6. **Works recursively** - Each nested question has its own pinning behavior
7. **Grace period** - 150ms delay prevents accidental unpinning from brief mouse movements
8. **UX-optimized timing** - Follows latency guidelines (0-100ms immediate, 100-1000ms natural)

## Technical Details

### Files Modified
- `/web/src/components/QuestionNode.vue`
  - Added hover detection with mouseenter/mouseleave events
  - Modified `directAnswers` computed property to use pinned order when hovering
  - Added lifecycle hooks for event listener setup/cleanup
  - Added 150ms delay before unpinning on mouse leave

### Configuration
```javascript
const UNPIN_DELAY = 150  // milliseconds before unpinning after mouse leave
                         // Based on UX latency guidelines:
                         // - 0-100ms: Feels immediate
                         // - 100-1000ms: Natural progression
                         // 150ms balances responsiveness with stability
```

### Edge Cases Handled
- New items added while hovering (appended to end)
- Items removed while hovering (filtered from pinned order)
- Component unmounting (timeout cleanup, event listener removal)
- Rapid hover in/out (timeout cleared on re-enter)
- Component shifting due to changes above (150ms grace period)
- Brief mouse movements outside component (150ms delay prevents accidental unpin)

## Testing Recommendations

> **🧪 UX TESTING FOCUS AREAS**
> 
> We're actively testing this implementation to validate the approach. Key areas to observe:

1. **Hover test**: Hover over questions while votes are changing - items should stay stable
2. **Mouse away reorder**: Move mouse away, wait for reorder, hover again - should see new order
3. **New items**: Add new answers while hovering - should appear at end without disrupting existing items
4. **Component shift**: Test with components above expanding/collapsing - grace period should handle it
5. **Performance**: Monitor with many questions/answers - simple events should be very efficient
6. **Grace period feel**: Does 150ms feel right? Too short? Too long?
7. **User frustration**: Are items still moving unexpectedly in any scenarios?
8. **Alternative triggers**: Should we also pin on click/focus, not just hover?
9. **Timing validation**: Does the 150ms align with UX latency guidelines in practice?

**Please report any issues or unexpected behavior - this will inform future refinements.**

## Addressing the "Component Shift" Concern

**Question**: Is the viewport stable if components above are changing?

**Answer**: The hover-based approach handles this well:

1. **300ms grace period** - If the component shifts and mouse briefly leaves, it won't unpin
2. **Intent-based** - Pinning is based on user actively hovering, not just viewport position
3. **Internal stability** - Even if the component moves, its internal order stays frozen
4. **Quick re-hover** - If mouse does leave, user can quickly move back to re-pin

**Comparison to viewport-based:**
- Viewport-based would have the same issue (component shifts, leaves viewport)
- Hover-based is actually **better** because it's tied to user intent, not screen position
- The grace period specifically addresses brief interruptions

## Future Enhancements (Optional)

1. **Configurable delay**: Allow adjusting the 300ms unpin delay
2. **Pin on focus**: Also pin when any input/button inside gets keyboard focus
3. **Smooth transitions**: Add CSS transitions when reordering happens (when not hovering)
4. **User preference**: Allow users to disable auto-reordering entirely
5. **Visual indicator**: Show a subtle indicator when order is pinned

