# Writing adapters

Training Gate's engine depends only on the protocols in
[`training_gate/ports.py`](../training_gate/ports.py). To connect it to real
systems, implement those six interfaces and return them from a *wiring*
function. [`examples/custom_wiring.py`](../examples/custom_wiring.py) is a
starting skeleton.

| Port | Responsibility | Typical backing system |
| --- | --- | --- |
| `CaseTracker` | List cases with their training-expiration date and last-trained date | Project-management / kanban board |
| `DocumentPortal` | Return the latest plan document, download it, and upload the signed-off record | External partner portal or document-management system |
| `TeamRoster` | Return the current team and supervisor for a case | Data warehouse, HR system, or CRM |
| `Mailer` | Send the training email and list replies in that thread | Work email API |
| `ChatNotifier` | Send the follow-up reminder | Team chat API |
| `DeckStorage` | Store the generated deck and return a shareable link | Shared drive / object storage |

## Contract notes

- **`Mailer.send` must return an id that `replies_to` understands.** The
  engine matches replies by thread *and* by sender address, so a supervisor
  replying on someone else's behalf does not count.
- **`DocumentPortal.latest_plan` decides what "new" means.** The engine treats a
  document as new when `published_on` is after the case's `last_trained_on`
  and it has not already sent that version.
- **`upload_attestation` should be safe to retry.** If an upload fails, the
  assignment stays `acknowledged` and filing is retried on the next run.
- **Adapters raise; the engine isolates.** An exception while processing
  one case is logged as an `error` event and the run continues with the rest.

## Handling sensitive data in your private deployment

- Request only the fields the engine needs (ids, display names, work email,
  chat handle, and dates). Don't pull anything else into the process.
- Use a pseudonymous `display_name` for cases wherever the downstream
  channel allows it. It is shown in email subjects and chat messages.
- Store `state.json` (or your database replacement) with the same access
  controls as the source systems. It contains names and work emails.
- Keep the deck link access-controlled. `DeckStorage.publish` should
  return a link that requires sign-in, not an anonymous public URL.
- Add your organization's real names and system names to `.pii-denylist` so
  `scripts/pii_scan.py` blocks them from any public fork.
