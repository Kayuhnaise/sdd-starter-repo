# Gap Analysis — Support Ticket Triage

## 1. Round 1 Results

The first blind handoff used `specs/spec-v1.md` with the prompt:

> Implement the feature specified in `specs/spec-v1.md`. Follow the conventions already in the repository.

The implementation agent successfully implemented the ticket triage endpoint without receiving additional clarification. All 14 acceptance tests for the V1 specification passed, and the complete repository test suite ultimately passed with 67 tests.

Although the implementation satisfied the V1 acceptance criteria, the handoff exposed an ambiguity involving tickets with no usable content. In the Open Questions section, V1 asked:

> "What should happen if a ticket has neither a subject nor a body?"

Because V1 did not answer this question, the implementation agent had to make its own assumption. The agent chose to pass empty strings for both fields to the classifier and return the resulting classification. This behavior was not necessarily incorrect under V1 because the specification had deliberately left the case unresolved, but it demonstrated that two independent implementers could reasonably choose different behaviors.

This was the most significant specification gap identified during the first blind handoff. The successful V1 tests also showed that passing tests alone did not mean every important edge case had been specified.

## 2. Specification Refinement from V1 to V2

The main refinement in V2 was to resolve the empty-ticket ambiguity identified during the first blind handoff.

In V1, the behavior appeared only as an unresolved open question:

> "What should happen if a ticket has neither a subject nor a body?"

V2 removed this question and added a new acceptance criterion:

> "Given an existing ticket with both an empty subject and an empty body, when the caller requests triage, then the API returns HTTP `422` using the repository `ErrorBody` error contract rather than sending an empty ticket to the model."

The V2 scope was also updated to explicitly include rejecting a ticket containing neither a subject nor a body. The interface contract was updated to state that the model must not be called for this case.

A new acceptance test, `test_ac15_empty_ticket_returns_422`, was added to verify the revised requirement. When the V2 tests were run against the Round 1 implementation, 14 tests passed and AC15 failed because the endpoint returned HTTP `200` instead of the newly specified `422`. This confirmed that the V2 change represented a real behavioral distinction rather than only a documentation change.

Two existing criteria were also clarified for testability. AC12 was revised to describe the observable responsibility of the triage endpoint: it returns `draft_first_reply` but performs no customer-contact or message-sending operation. AC14 was revised from describing concurrent requests to repeated requests because the original acceptance test did not actually exercise concurrency. The revised criterion accurately reflects the behavior being verified: repeated triage requests must not modify or delete the source ticket.

These changes made V2 more precise without substantially expanding the feature's scope.

## 3. Round 2 Results

The second blind handoff used `specs/spec-v2.md` with the prompt:

> Implement the feature specified in `specs/spec-v2.md`. Follow the conventions already in the repository.

The second implementation agent independently identified the newly specified empty-ticket behavior. It updated the endpoint to reject a ticket when both the subject and body are empty before calling the model. It also ensured that HTTP `422` uses the repository's existing error contract.

The agent did not require clarification about the new requirement. After the implementation, all 15 V2 ticket-triage acceptance tests passed. The complete repository test suite also passed with 68 tests.

This result showed that the V2 specification resolved the ambiguity found during Round 1. Under V1, an implementer had to decide independently what to do with an empty ticket. Under V2, the expected behavior was explicit enough for a fresh implementation agent to make the required change without additional guidance.

The progression of the acceptance tests also provided evidence of the refinement:

- Before the feature was implemented: **14 of 14 V1 tests failed** because the endpoint did not yet exist.
- After Blind Handoff 1: **14 of 14 V1 acceptance tests passed**.
- After adding the V2 empty-ticket criterion but before changing the implementation: **14 tests passed and 1 failed**. AC15 returned HTTP `200` instead of the specified `422`.
- After Blind Handoff 2: **15 of 15 V2 acceptance tests passed**, and **68 of 68 total repository tests passed**.

The failing AC15 between the two handoffs was particularly useful because it demonstrated that the specification revision resulted in a concrete, testable change in system behavior.

## 4. Remaining Gaps and Over-Specification

The refinement process also highlighted the importance of balancing precision with implementation freedom. The specification needed enough detail for an independent agent to produce consistent observable behavior, but it did not need to prescribe every internal implementation decision.

For example, the specification defines the endpoint, response fields, supported category and priority values, confidence threshold, error behavior, and model metadata because these are observable parts of the feature contract. It also incorporates repository conventions such as using `ModelPayload`, `ErrorBody`, and the existing model client. These constraints help ensure compatibility with the rest of the application.

At the same time, the specification avoids prescribing private helper functions, internal control flow, or a particular algorithm for constructing the response. The blind implementation agent was therefore able to choose its own implementation structure while still satisfying the acceptance criteria.

There were places where V1 was slightly over-specified or insufficiently testable. AC14 originally required concurrent requests even though concurrency was not central to the ticket-triage problem and the corresponding test did not actually create concurrent requests. V2 changed this to repeated requests and focused on the important observable requirement that triage must not mutate the source ticket. AC12 also originally stated that the draft reply must not be automatically sent, even though the repository does not provide a customer-message delivery mechanism that the acceptance test could directly observe. V2 clarified that the triage endpoint itself performs no customer-contact or message-sending operation.

Some questions intentionally remain open, including whether certain sensitive ticket types should always require human review, whether agents should be able to override triage decisions, whether corrections should be persisted, and whether duplicate tickets should eventually be linked. These behaviors are outside the current proof-of-concept scope and do not need to be decided to implement the present feature.

Overall, the two handoffs showed that the most useful specification details were those that affected observable behavior. The V1 specification was sufficient to produce a working implementation, but the blind handoff exposed an unresolved edge case. V2 converted that ambiguity into a specific, testable requirement while also making two existing criteria more accurately reflect what the tests could verify.