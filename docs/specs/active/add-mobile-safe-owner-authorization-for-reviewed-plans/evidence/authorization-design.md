# Mobile owner authorization: staged design

## Now: temporary personal-use agent attestation

The owner explicitly chose a temporary model that trusts the agent's assertion of an
explicit decision in chat, to allow work to proceed. It is not independently
authenticated and is not an interactive terminal confirmation. It applies to the
specific task and reviewed content, not all tasks. The existing terminal method
remains available. A source chat reference, task identity, digest and expiry are
recorded. The agent must present the current review and obtain a specific decision;
a general instruction to proceed is not that decision.

The later authenticated implementation must have a trust anchor outside the agent-controlled task
package. It must identify the project and task, exact artifact digests and Kepler
verdict hash, the approving principal and trusted issuer, audience, decision, issue
and expiry times, and a unique challenge. It must validate the trusted signature and
user verification, expiry, audience, task and project binding, current content and
verdict, and replay policy at the gate. A failed or unavailable verifier fails closed.
The reviewed research prefix rule remains unchanged. Existing version 1 terminal
approvals remain readable; no pending task is retroactively approved. The precise
wire format and project identity scheme require review alongside the actual adapter.

## Later: passkey confirmation

Offer a review page on the owner's phone, showing the task and meaningful plan summary,
followed by an explicit approval action and passkey user verification. A trusted
service creates a fresh unpredictable challenge associated with the exact displayed
package and a short expiration. It verifies WebAuthn assertions, including signature,
registered credential, origin, relying party, challenge and user-verification flag,
and emits a decision that Fabric can verify against a separately configured trust
anchor. The page and challenge service must not allow the agent to swap the presented
package after review. Fabric rechecks current artifacts and verdict when consuming the
decision. The biometric stays on the device; passkey verification can also be fulfilled
by other device-supported user verification, so the service must not claim fingerprint
specifically unless the platform can prove that property.

Initial credential enrollment, authenticated transport, trusted origin and service
hosting, credential revocation and recovery, and configuration of the verifier remain
design and delivery prerequisites. These introduce a new credential and deployment
mechanism and are deferred until explicitly selected for the later stage. A mobile
browser's secure context and reachable endpoint must be established; localhost on the
computer is not automatically reachable as a secure origin from a phone. No current
Codex tool has been established as supplying Fabric-verifiable owner attestations.

## Acceptance matrix for the later stage

- Correct owner, project, task, reviewed hashes and advice verdict: succeeds once.
- Wrong or revoked credential, invalid signature, missing user verification, wrong
  origin or relying party, or untrusted issuer: reject.
- Altered plan, spec, reviewed research prefix or Kepler verdict; changed task/project;
  expired decision or replay outside the defined policy: reject.
- Safe runtime research append and previously issued terminal approval: preserve the
  existing behavior.
- Rejected or unavailable service, cancelled ceremony, interrupted flow, and clock
  errors: fail closed with a clear next action.
- Test actual phone-to-service-to-Fabric operation as well as local automated checks;
  a mock WebAuthn response alone is not evidence of mobile acceptance.
