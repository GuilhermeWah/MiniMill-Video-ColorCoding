# Implementation Anti-Patterns & Prevention Guide

## Purpose
This document captures lessons learned from implementation bugs and provides a checklist-driven approach to prevent similar issues across any development work.

---

## Pattern 1: Input-Output Disconnection

### What Happened
Inputs were defined (parameters, configs, API fields) but **never connected** to the actual logic that should consume them.

**Example:** `canny_low` and `canny_high` parameters existed in config, but:
- `get_params()` correctly read them
- **BUT** the algorithm used `hough_param1` instead
- `canny_low` was completely ignored

### Root Cause
- Parallel development without end-to-end verification
- Naming confusion (different names for same concept)
- No integration tests that verify input → output relationship

### Prevention Checklist
```
□ Trace data flow: Input Source → Transform → Handler → Algorithm → Output
□ For each input, identify which algorithm line consumes it
□ Write a test: change input value, verify output changes accordingly
□ Search codebase for parameter name - verify it's USED, not just DEFINED
□ If renaming: grep for all occurrences, update all of them
```

### Generalized Rule
**"Define once, trace everywhere"** - Every input must have a traceable path to where it affects output.

---

## Pattern 2: Interface Not Wired

### What Happened
Interfaces were **defined and called** but never **connected** to implementations.

**Example:** `calibration_changed` callback was defined, invoked, but nothing was registered to receive it. The action did nothing.

### Root Cause
- Easy to define an interface, forget to wire it
- No compile-time/runtime check for unconnected interfaces
- Works in isolation (calling nothing doesn't crash)

### Prevention Checklist
```
□ After adding an interface/callback/event: search for registration/subscription
□ Add test: trigger interface, verify handler executes
□ Maintain interface mapping table:
  | Interface | Producer | Consumer | Wired in |
```

### Generalized Rule
**"Interfaces need both ends"** - For every emit/publish/call, there must be a receive/subscribe/handler.

---

## Pattern 3: State Interference

### What Happened
One operation **unexpectedly modified** state needed by another feature.

**Example:** Setting cached data cleared temporary preview data as a "cleanup" side effect.

### Root Cause
- Hidden coupling between unrelated features
- No explicit state ownership
- Defensive coding gone wrong ("clear just in case")

### Prevention Checklist
```
□ When modifying state, ask: Who else reads/writes this?
□ A function should only modify state it "owns"
□ Side effects must be documented explicitly
□ Document state ownership:
  | State | Owner | Writers | Readers |
□ Before adding cleanup logic: verify nothing depends on that state
```

### Generalized Rule
**"Explicit ownership, explicit effects"** - Every piece of state has one owner; modifications by others require coordination.

---

## Pattern 4: Happy Path Tunnel Vision

### What Happened
Default/common case worked, but **non-default configurations** failed silently.

**Example:** Processing all items worked; processing every 10th item left gaps. Lookups for missing items returned empty instead of graceful fallback.

### Root Cause
- Only tested the default case
- Implicit assumptions about data completeness
- No fallback strategy defined

### Prevention Checklist
```
□ Test boundaries: minimum, maximum, middle, edge values
□ For lookup functions, define and document fallback behavior
□ Ask: What happens when data is missing/sparse/malformed?
□ Configuration matrix testing:
  | Config | Expected Behavior | Tested? |
```

### Generalized Rule
**"Test the boundaries, not just the center"** - If a value can vary, test its extremes.

---

## Pattern 5: Resource Lifetime Mismatch

### What Happened
Resources (objects, connections, handles) were **released** while still in use.

**Example:** Worker objects garbage collected while background threads still running.

### Root Cause
- Scope mismatch between creator and consumer
- Language GC vs framework lifecycle differences
- Local variables for long-lived resources

### Prevention Checklist
```
□ For any async/background work: store references that outlive the operation
□ Match resource lifetime to usage lifetime
□ Cleanup on explicit termination, not scope exit
```

```python
# ❌ BAD: Local variable, GC collects after function returns
worker = BackgroundWorker(...)

# ✅ GOOD: Instance variable, survives function scope
self._worker = BackgroundWorker(...)
```

### Generalized Rule
**"Resources live as long as their users"** - If something uses a resource asynchronously, keep the resource alive until done.

---

## Pattern 6: Asymmetric API

### What Happened
APIs had setters but **missing getters**, or write paths but no read paths.

**Example:** `set_calibration(value)` existed, `get_calibration()` did not. Code trying to read the value failed.

### Root Cause
- Built for one use case, didn't anticipate others
- Forgot to add the inverse operation

### Prevention Checklist
```
□ For every set_X, add get_X
□ For every write path, consider the read path
□ API completeness table:
  | Property | Write | Read | Notify |
```

### Generalized Rule
**"Symmetric APIs"** - If you can set it, you should be able to get it.

---

## Pattern 7: Documentation-Implementation Drift

### What Happened
Documentation described one behavior, implementation did another.

**Example:** Docstring said "returns 0 for all items" but implementation returned -1. Tests based on docs failed.

### Root Cause
- Docs written before implementation finalized
- Implementation changed, docs not updated
- No automated check for doc accuracy

### Prevention Checklist
```
□ Write tests based on documentation - they should pass
□ Update docs when changing behavior
□ Docstrings should describe ACTUAL behavior, not INTENDED behavior
□ Review: Does the code do what the comment says?
```

### Generalized Rule
**"Docs track code"** - If implementation changes, documentation must change with it.

---

## Pattern 8: Missing Error Path

### What Happened
Success path worked, but **error conditions** crashed or produced wrong results.

**Example:** Method assumed video file exists; when missing, cryptic crash instead of helpful error.

### Root Cause
- Only tested happy path
- No explicit error handling
- Assumptions about preconditions not validated

### Prevention Checklist
```
□ For each function, ask: What if inputs are invalid?
□ Validate preconditions explicitly
□ Return meaningful errors, not cryptic crashes
□ Test with: None, empty, invalid, missing inputs
```

### Generalized Rule
**"Errors are features"** - Plan for failure as carefully as success.

---

## Quick Checklist: Before Completing Any Feature

```markdown
### Data Flow ✓
[ ] Traced from input to algorithm to output
[ ] Test: changing input changes output

### Interfaces ✓
[ ] Every producer has at least one consumer
[ ] Test: trigger interface, verify handler runs

### State ✓
[ ] Documented what state this modifies
[ ] Checked for interference with other features

### Edge Cases ✓
[ ] Tested with non-default configurations
[ ] Fallback behavior defined for missing data

### API ✓
[ ] Every setter has a getter
[ ] Types consistent across interface boundaries

### Resources ✓
[ ] Async resources stored with appropriate lifetime
[ ] Cleanup happens on termination, not scope exit

### Errors ✓
[ ] Invalid inputs produce helpful errors
[ ] Missing data has defined behavior

### Documentation ✓
[ ] Docs match actual implementation
[ ] Tests based on docs pass
```

---

## The Core Insight

Most bugs came from **lack of end-to-end tracing**. Components were built in isolation, each working correctly alone, but nobody verified the connections between them.

**The fix is simple**: Before marking done, trace the full path from input to output, trigger to effect, request to response.

### The Three Questions
Before completing any feature, answer:
1. **Where does the input come from, and where does it go?**
2. **What state does this touch, and who else touches it?**
3. **What happens when things go wrong?**

If you can't answer these confidently, you're not done.
