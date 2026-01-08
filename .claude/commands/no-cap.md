# No Cap - Post-Task Verification Check

Perform a thorough verification of the work just completed. This is a "bullshit check" to ensure everything is properly implemented.

## Verification Checklist

Go through each item and actively verify by reading the relevant code:

### 1. Implementation Matches Plan
- Does the implementation match what we discussed and planned?
- Are all the agreed-upon features/fixes actually implemented?
- Did anything get skipped or forgotten?

### 2. No Hacks or Workarounds
- No temporary fixes that should be permanent solutions
- No "quick and dirty" code that needs proper implementation
- No hardcoded values that should be configurable
- No copy-pasted code that should be abstracted

### 3. No Placeholders
- No `TODO` comments left behind (unless intentionally deferred)
- No `FIXME` markers
- No stub functions that don't actually do anything
- No placeholder text or values
- No `console.log` statements left for debugging
- No commented-out code blocks

### 4. No Fake Implementations
- Code that looks like it works but doesn't actually function
- Functions that return dummy data
- Error handlers that swallow errors silently
- Conditionals that always take one path
- Features that are wired up in UI but do nothing

### 5. No Silent Failures
- Errors are properly caught AND logged/handled
- Failed operations don't just disappear
- User gets feedback when something goes wrong
- Network/API failures are handled gracefully

### 6. Proper Error Handling
- All error cases are considered
- Errors are logged with useful context
- Recovery or fallback behavior is appropriate
- No bare `catch {}` blocks that swallow everything

### 7. Edge Cases Handled
- Null/undefined inputs handled
- Empty arrays/objects handled
- Boundary conditions considered
- Invalid input validation

### 8. Type Safety (TypeScript)
- No `any` types unless absolutely necessary
- Proper type definitions for all interfaces
- No type assertions that hide problems (`as any`, `!`)

## Output Format

After verification, report:

1. **Status**: VERIFIED or ISSUES FOUND
2. **Files Checked**: List the files you reviewed
3. **Issues** (if any): Describe each problem found with file:line references
4. **Recommendations**: Specific fixes needed

Be honest and thorough. The whole point is to catch problems before they become production bugs.
