# Feature Specification — Support Ticket Triage

**Status:** draft
**Author:** Keya Gangadharan
**Reviewers:** n/a - individual assignment
**Date:** 27 September 2026 

---

## 1. Intent

Support staff need a consistent way to triage incoming support tickets before a human reviews them. The support ticket triage feature classifies an existing ticket by category and priority, suggests the team that should handle it, and generates a draft first reply. Because model classifications may be uncertain or incorrect, the response must expose enough information for a human reviewer to recognize uncertain results rather than presenting every classification as equally reliable. This feature assists human review; it does not replace it.

## 2. User stories

- As a support agent, I want a ticket assigned a category so that I can understand the type of issue being reported.
- As a support agent, I want a ticket assigned a priority so that urgent issues can be identified.
- As a support agent, I want a suggested team so that I know where the ticket should be routed.
- As a support agent, I want a draft first reply so that I have a starting point for responding to the customer.
- As a support agent, I want to see the model confidence and model version so that I can recognize uncertain or model-dependent results.
- As a support agent, I want uncertain classifications clearly identified so that I know when additional human judgment is required.

## 3. Acceptance criteria

1. Given an existing support ticket with a subject and body, when the caller requests triage for that ticket, then the API returns HTTP 200 with the original ticket, category, priority, suggested team, draft first reply, model confidence, model version, and model latency.
2. Given a successful triage request, when a triage result is returned, then `category` is one of `billing`, `access`, `data`, `outage`, or `general`, and `priority` is one of `high`, `normal`, or `low`.
3. Given a ticket for which the model returns confidence below `0.50`, when the caller requests triage, then the API still returns HTTP 200 and includes the model result and confidence, but marks the result as requiring human review.
4. Given a ticket for which the model returns confidence greater than or equal to `0.50`, when the caller requests triage, then the API returns HTTP 200 and does not mark the result as requiring human review solely because of model confidence.
5. Given an existing ticket with no subject but with a non-empty body, when the caller requests triage, then the API classifies the ticket using the available body and returns HTTP 200.
6. Given an existing ticket with a subject but no body, when the caller requests triage, then the API classifies the ticket using the available subject and returns HTTP 200.
7. Given a ticket ID that does not exist in the ticket fixture data, when the caller requests triage, then the API returns HTTP 404 using the repository `ErrorBody` error contract.
8. Given an existing ticket and a model client that raises `ModelUnavailable`, when the caller requests triage, then the API returns HTTP 503 using the repository `ErrorBody` error contract with code `model_unavailable`.
9. Given an existing ticket and a model client that raises `ModelTimeout`, when the caller requests triage, then the API returns HTTP 504 using the repository `ErrorBody` error contract with code `model_timeout`.
10. Given any successful model-backed triage response, when the response is returned, then it contains the model confidence, model version, latency, and raw model result in a `ModelPayload` in addition to the typed triage fields.
11. Given the same ticket is triaged using model version `v1` and later using model version `v2`, when the returned classifications differ, then each response reports the model version that produced its result rather than hiding the difference.
12. Given any successful triage result, when a draft first reply is returned, then it is returned only as a draft for human review and the feature does not automatically send it to the customer.
13. Given two tickets that describe the same or a near-duplicate problem but have different ticket IDs, when each ticket is triaged, then each remains a separate ticket and receives its own triage result; this feature does not merge or delete either ticket.
14. Given two triage requests for the same ticket arrive concurrently, when both requests complete successfully, then each returns a valid triage response and neither request modifies or deletes the source ticket.

## 4. Scope and non-goals

**In scope:**
- Triage an existing ticket from the provided ticket fixture data.
- Classify the ticket into a supported category.
- Assign a priority.
- Suggest a team.
- Generate a draft first reply.
- Return model confidence, version, latency, and raw result.
- Indicate when low model confidence requires human review.
- Handle tickets containing only a subject or only a body.
- Handle model unavailability and timeouts using the existing API error contract.


**Explicitly out of scope:** 
- Automatically sending the draft reply to a customer.
- Automatically merging duplicate or near-duplicate tickets.
- Automatically closing or deleting tickets.
- Persisting triage results to a database.
- Learning from human overrides.
- Implementing a user interface or approval screen.
- Automatically re-routing tickets after human review.
- Authentication and authorization changes.
- Changing or retraining the stub model.
- Guaranteeing that a high-confidence model classification is factually correct.

## 5. Interfaces and contracts

**Endpoint**
`GET /tickets/{ticket_id}/triage`
`ticket_id` identifies an existing ticket in the provided ticket fixture data.
No request body is required.

**Successful response**
HTTP `200`
The response contains:
- `ticket`
  - `id`
  - `subject`
  - `body`
- `triage`
  - `category`
  - `priority`
  - `suggested_team`
  - `draft_first_reply`
  - `requires_human_review`
- `model`
  - `value`
  - `confidence`
  - `model_version`
  - `latency_ms`

The exact category, priority, suggested team, draft text, confidence, and latency depend on the stub model result. The API contract requires these fields and their valid shapes rather than any particular example values.

**Low-confidence response**
A model confidence below `0.50` does not cause an HTTP error. The API returns the model output and sets `requires_human_review` to `true`.
A model confidence greater than or equal to `0.50` sets `requires_human_review` to `false` unless another future rule requires human review.

**Error responses**
For an unknown ticket ID, the API returns HTTP `404` using `ErrorBody` with code `not_found`.
If the model is unavailable, the API returns HTTP `503` using `ErrorBody` with code `model_unavailable`.
If the model times out, the API returns HTTP `504` using `ErrorBody` with code `model_timeout`.
All request and response shapes must be declared in `app/models.py`. Nothing crosses the API boundary as a bare dictionary.

## 6. Constraints

- **Security**: No authentication or authorization changes are included in this feature. The endpoint operates only on the provided ticket fixture data and must not introduce external data storage or transmit ticket data to an external AI service.
- **Performance:** One request processes exactly one ticket and makes at most one model call. The feature does not provide bulk triage. The application must not retry automatically after a model timeout or unavailable error.
- **Compatibility:** Existing API endpoints and the existing test suite must continue to work. Request and response models must be declared in `app/models.py`. Errors must use the existing `ErrorBody` contract and existing status codes. The model must be accessed through `app.model_client.get_client()`, and successful model-backed responses must expose confidence, model version, latency, and the raw result through `ModelPayload`.
- **Other:** The route must live under `app/routes/` and be registered with the existing FastAPI application. The existing ticket fixture loader must be used rather than introducing a new persistence system. No ORM or new database layer may be added. Business logic must not be placed in `app/main.py`. The endpoint must not modify the ticket fixture data. The feature must work with the provided stub model and must not require an external AI API, GPU, or additional dataset.

## 7. Test plan

Tests will use the repository `client` fixture for HTTP behavior and the stub-model controls when model behavior must be varied. Each test is mapped to an acceptance criterion by number.

| Acceptance criterion | Test |
|---|---|
| AC1 | `test_ac1_successful_triage` |
| AC2 | `test_ac2_supported_category_and_priority` |
| AC3 | `test_ac3_low_confidence_requires_human_review` |
| AC4 | `test_ac4_normal_confidence_does_not_require_review` |
| AC5 | `test_ac5_missing_subject_uses_body` |
| AC6 | `test_ac6_missing_body_uses_subject` |
| AC7 | `test_ac7_unknown_ticket_returns_404` |
| AC8 | `test_ac8_model_unavailable_returns_503` |
| AC9 | `test_ac9_model_timeout_returns_504` |
| AC10 | `test_ac10_response_contains_model_payload` |
| AC11 | `test_ac11_model_version_is_reported` |
| AC12 | `test_ac12_draft_reply_is_not_sent` |
| AC13 | `test_ac13_duplicate_tickets_remain_independent` |
| AC14 | `test_ac14_concurrent_requests_do_not_modify_ticket` |


Tests will assert observable behavior such as HTTP status codes, response shapes, returned fields, and error codes rather than private implementation details.
The complete existing test suite must also continue to pass.

## 8. Open questions

- What should happen if a ticket has neither a subject nor a body?
- Should high-confidence classifications ever require human review for reasons other than model confidence?
- Should specific ticket types, such as account deletion or accessibility requests, always require human review regardless of confidence?
- Should support agents eventually be able to override the category, priority, or suggested team through the API?
- Should accepted or corrected triage decisions be persisted for later analysis or model improvement?
- Should near-duplicate tickets eventually be linked or grouped while remaining separate tickets?
- Should the system enforce a response-time clock based on the assigned priority?
- Should draft replies ever be eligible for automatic sending in a future version?
---