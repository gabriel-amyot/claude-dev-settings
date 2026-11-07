# SSE through a proxy: buffering checklist

Use this checklist when an SSE response in a HAR shows the right events but the user says they
"arrive all at once" or no progress shows. The parser prints header-based buffering hypotheses.
They are not proof. A HAR stores the stream as one body and has no per-event arrival times.

## 1. Confirm the events are correct first

Read the parser's event table. Check step names, types and content shapes. If the events are
wrong or missing, the problem is the backend, not buffering. Stop here and debug the producer.

## 2. Map every hop

Write the path down, one line per hop: backend, then each proxy (for example a Next.js API route),
then the load balancer or CDN, then the browser. For each hop, note who owns it and whether it can
compress or buffer.

## 3. Get timing evidence per hop

Header signals only make a hop a suspect. Prove the hop with arrival times:

- Call the hop directly with `curl -N` and print a timestamp per line, for example
  `curl -sN <url> | while IFS= read -r l; do printf '%s %s\n' "$(date +%T)" "$l"; done`.
- Start at the backend and move one hop closer to the browser each time. The first hop where
  events arrive together is the buffering hop.
- In the browser, the EventStream tab of the request shows the arrival time of each event.

## 4. Check the deployed code, not the local checkout

Run `/deploy-identity` before you cite proxy or backend code as the deployed behavior.

## 5. Check load balancer logs in the correct project

Find the project that owns the load balancer from the infrastructure code, not from an alias or
a guess. A log query on the wrong project returns nothing and looks like "no errors".

## 6. Check the client render path

When the network delivers events incrementally but the UI still updates once, the cause is in the
client. In React, state updates from one tick batch together. Check how the stream reader yields
between events (for example `flushSync` or a `setTimeout(0)` per event).

## Report

State each hop as: proven buffering, proven streaming, or not measured. Never report a hop as the
cause on header signals alone.
