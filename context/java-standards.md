# Java Code Style & Testing Standards

## Mockito Strictness
- Avoid `@MockitoSettings(strictness = Strictness.LENIENT)` at the class level
- Set up only the stubs each test actually needs
- Use helper methods (e.g., `stubSyncDependencies()`) for common stubs shared by multiple tests
- Use `lenient().when()` sparingly for specific stubs that may not always be used
- Keep tests compact — remove unnecessary empty lines between Given/When/Then blocks

## Testing Standards
- **Extract test constants:** Use `private static final` fields for constants reused across multiple tests (IDs, dates, values)
- **Use List.of():** Never use `Arrays.asList()` or `new ArrayList<>()` in tests
- **Test naming:** Follow `{Given}{When}{Then}` pattern (e.g., `validJobId_whenGetJobCalled_thenReturnsJob`)
  - Not: `getCurrentDspReportLevel_shouldSelectMostGranular` (too vague)
  - Yes: `campaignOnly_whenGetCurrentDspReportLevel_thenReturnsCampaignLevel` (crystal clear)
- **One behavior per test:** Each test method verifies exactly one behavior or condition
- **//given //when //then:** Structure test body with comments as mental separators, no extra blank lines between them
  ```java
  //given
  when(service.method()).thenReturn(value);
  //when
  var result = controller.call();
  //then
  assertEquals(expected, result);
  ```
- **Tight setup:** No blank lines between `@Mock`, `@MockBean`, field declarations and `@Before`/`setUp()` at class top
- **Helper methods:** Use private helper methods (e.g., `stubValidationPasses()`) for common stub setup
- **Meaningful names:** Use constant names like `VALID_JOB_ID`, `ADVERTISER_90` instead of magic values
- **No comment cruft in tests:** Remove explanatory comments like `// Campaign only → campaigns table`
  - The test name + variable names should make it obvious
  - Refactor test names to be self-documenting instead

## Why Best Practices Enforcement Matters

**Lesson Learned:** Initial implementation of DspReportLevelTest violated these standards (missing constants, verbose comments, unclear naming). Later feedback exposed the violations.

**Why This Matters:**
1. **Maintainability:** Hardcoded strings make refactoring dangerous (typos, inconsistencies)
2. **Single Source of Truth:** Constants prevent divergence between enums and test strings
3. **Readability:** Clear {Given}{When}{Then} naming makes tests self-documenting
4. **Consistency:** Enforced standards make code predictable across the codebase
5. **Prevention:** Violations caught now don't compound into future technical debt

**Prevention Strategy:**
- Review tests BEFORE approving PRs for:
  - String constants extracted (no hardcoded dimension names, table names, etc.)
  - Test names follow {Given}{When}{Then} pattern
  - No explanatory comments (naming should suffice)
  - One behavior per test method
  - All values extracted as class constants
- Use linters/IDE inspections to catch repeated strings automatically
- Document standards in local CLAUDE.md (specific to service)
- Don't assume "we'll clean it up later" — enforce from the start
