# 0007 — Place names are geocoded by OpenStreetMap, from the server, behind a button

Date: 2026-08-21

## Context

The registry's distance filter needs a latitude and longitude. Asking a person to
type coordinates is not a product, so the interface offered six hard-coded cities.
Honest for a skeleton; useless to anybody in Tucson, which is `D-4`.

## Decisions

**Nominatim, the OpenStreetMap Foundation's geocoder.**

It needs no key and no account, so nothing about this project depends on a
credential the build environment might not have — the same property that let the
whole search path be built while the model steps stayed blocked. The data is open
under the ODbL. The alternatives all wanted either a paid key or a signed-up
account tied to an identity.

Their usage policy is not a formality: the service runs on donated servers with,
in their words, "very limited capacity". Everything below is that policy, obeyed.

**The server geocodes, not the browser.**

The browser could call Nominatim directly and save a hop. It would also hand a
third party the user's IP address alongside the name of the town they are looking
for — a service the user never chose to talk to, learning where they are and what
they are looking for near it. Going through this server means OpenStreetMap sees
*this server* asking about a town, and nothing about who wanted to know.

It also puts the rate limit and the User-Agent somewhere they can be enforced,
rather than trusting every browser tab to behave.

**One request per second, enforced in code.**

The policy says "an absolute maximum of 1 request per second". A limit that is
documented and not implemented is a limit exceeded by the first impatient user.
`Geocoder._wait_for_turn` holds callers behind a lock and a clock; a test drives
it with a fake clock and asserts the waits happen. The lock is process-wide
because the promise is about this server, not about one browser.

**No auto-complete, ever.**

"Auto-complete search" is on the policy's forbidden list. So the lookup is
something the person asks for — a text box and a **Find** button — and nothing is
wired to a keystroke. Verified by typing "Tucson" one letter at a time in a real
browser with `fetch` instrumented: **zero requests while typing, one when the
button is pressed.**

This is also the reason the *chip* for the place offers only places already
known: editing a chip is a keystroke-driven interaction, and a lookup does not
belong there.

**The cache is in memory and stays there.**

The policy asks that results be cached and warns that repeating identical queries
can get a client classified as faulty. But `docs/decisions/0005` turned off the
registry response cache because a file of queries with timestamps is a record of
what people searched for. A file of *place names* with timestamps is a record of
where they were looking, which is worse.

So the cache lives in the process and dies with it. A repeated search does not
produce a repeated request, and nothing is written down. A test runs two identical
searches in an empty directory and asserts one request and no files.

**Attribution is displayed**, next to the results it produced, as the ODbL
requires.

**The preset cities and "Anywhere" both survive.** The cities are the fallback
when the lookup is down — and the error message says so explicitly rather than
leaving the person stuck. "Anywhere" is not a placeholder: searching with no
location is a real query that returns trials with no distance claim attached.

## Consequences

**Rule 4's wording had to change**, and this is the part most likely to be
forgotten next time. There is now a second place a typed location goes, so the
on-screen statement names OpenStreetMap as well as ClinicalTrials.gov. A rule-4
statement that mentioned only one of them would have become exactly the kind of
half-true claim `docs/decisions/0005` exists to prevent. There is a test pinning
it.

**The profile stopped holding an index.** It used to store a position in the
six-item city list. The moment that list could grow, an index meant nothing on its
own: search for Tucson, get index 7, and every reader still consulting the
constant fell back to "Anywhere" and searched the whole world without saying so.
The profile now holds the place itself. That is a class of bug removed rather than
an instance fixed, and it is the kind of thing to watch for whenever a fixed list
becomes a growing one.
