# The domain layer

`src/domain` is the part of this service that does not know it is a web
application. It has no Flask, no SQLAlchemy, no boto3, no network access and it
never reads the wall clock: anything that depends on "now" takes the moment as
an argument. That is what makes it possible to test the parts of Vokal Studio
that are actually hard — proration, restream fan-out, loudness limiting,
retention curves — without a database or a fixture server.

The Flask resources under `src/resources` stay responsible for HTTP and
persistence. They read rows, hand them to `src.domain.adapters`, ask the domain
a question, and serialise the answer back.

## Packages

| Package | What lives there |
| --- | --- |
| `core` | Errors with stable codes, argument guards, text and collection helpers, a result type, derived identifiers |
| `timeline` | UTC instants, durations, half-open intervals, drop-frame timecode, civil dates, recurring broadcast windows |
| `money` | Currencies, exact amounts in minor units, rounding modes, largest-remainder allocation, tax |
| `catalog` | Products, plans and billing cycles, feature keys, entitlement resolution, usage counters |
| `billing` | Subscription state machine, charge schedules, payments, invoices, proration, dunning, a ledger |
| `access` | Permissions, roles, authorized-user grants, invitations, token claims, the authorisation policy |
| `media` | Containers and codecs, assets, loudness normalisation, rendition ladders, render configuration, object keys |
| `episodes` | Shows and numbering, chapters, show notes, the publishing state machine, publication planning |
| `streaming` | Platform registry, RTMP parsing, stream targets, the restream plan, live sessions, encoder health |
| `servers` | Regions and latency, instance types, the provisioning state machine, the pool, the allocator |
| `distribution` | Upload destinations, OAuth credentials, retry policy, upload jobs, feed building, syndication |
| `content` | Blog posts, a small markdown block parser, the blog index query |
| `analytics` | Play events, daily rollups, retention curves, dashboard reports |
| `adapters` | Reading stored rows and writing API envelopes |

## Rules the layer keeps to

**Nothing mutates.** Every object is built once and every change returns a new
one. `subscription.cancel(day)` hands back a cancelled copy; the original is
untouched. This is why `to_dict()` is safe to hand straight to a serialiser.

**Money is an integer.** `Money(9900, "USD")` is 99.00 USD. Floats never enter,
and splitting an amount goes through `allocate_by_weights`, which is the only
place allowed to decide who gets the leftover minor unit.

**Time is an argument.** `episode.is_due(now)`, `grant.is_active(on)`,
`session.billable_minutes()` — none of them call `datetime.now()`. The Flask
layer supplies the moment.

**Failures carry codes.** Everything raised inherits from `DomainError` and has
a `code` and a `status`; `adapters.serialize.error` turns one into a response
body and an HTTP status. The codes are part of the API and are not renamed.

**Validation happens in the constructor.** If you are holding a `StreamTarget`
you are holding one with a valid ingest URL and a stream key long enough for
the platform it points at. There is no separate `is_valid()` step to forget.

## Running the tests

    python -m unittest discover -s tests -t .

The `-t .` matters: the test packages import shared fixtures from
`tests.support`. The suite has no third-party dependencies, which is why CI can
run it without installing `requirements.txt`.
