# Bonus 2: the server asks the user (multi round-trip requests)

Since protocol revision 2026-07-28, an MCP server can no longer send requests to the client in the middle of a call. When a tool needs input from the user, the server **returns the question** instead:

1. The client calls the tool.
2. The server answers with `resultType: "input_required"`, the question in `inputRequests`, and a signed `requestState`.
3. The client asks the user, then sends the **same request again** with the answers in `inputResponses` and the `requestState` copied byte for byte.
4. The server checks the signature, runs the tool, and returns `resultType: "complete"`.

This is called a multi round-trip request (MRTR). It replaces the old server-initiated `elicitation/create`, and it works behind load balancers because no connection has to stay open.

## The example

`build_evidence_table` in `server.py` asks you to confirm the scope of an evidence table (earliest year, number of papers, open access only) before it searches. The question is declared with the SDK's `Resolve` and `Elicit` helpers:

```python
async def ask_review_scope(research_question: str = config.DEFAULT_QUESTION) -> Elicit[ReviewScope]:
    return Elicit(f'Build an evidence table for: "{research_question}". Confirm the scope.', ReviewScope)

@mcp.tool()
async def build_evidence_table(scope: Annotated[ReviewScope, Resolve(ask_review_scope)], query: str = ..., ...):
    ...
```

The `scope` parameter never appears in the tool's input schema. The SDK fills it from the user's answer.

## Run it

Start the reference server first (`python server.py`, or set `MCP_URL` to a deployed server).

```bash
python 2-bonus-ask-the-user/ask_the_user.py          # answer in the terminal; Enter keeps a default
python 2-bonus-ask-the-user/ask_the_user.py --wire   # the same exchange as raw HTTP
```

## What to look for

| You do | You should see |
|---|---|
| Call with the SDK client and a callback | The question in the terminal, then a numbered evidence table |
| `--wire`, round 1 | `resultType: input_required`, the question under `inputRequests`, a long `requestState` |
| Retry with a tampered `requestState` | Error `-32602`, "Invalid or expired requestState" |
| Call without declaring elicitation | Error `-32021`: the client did not declare the capability this tool needs |
| Retry with the original `requestState` | `resultType: complete` and the table |

## Things worth discussing

- **Capabilities are declared, not assumed.** Registering `elicitation_callback` is how a client says it can ask the user. Hosts that cannot ask (most plain agent loops) get `-32021` for this tool only; the other tools still work. That is why the workshop agent is not given this tool.
- **Anything that passed through the client is attacker-controlled.** The SDK signs `requestState`, so a modified copy is refused.
- **Several replicas.** By default the signing key is random per process, so a retry that lands on another replica, or arrives after a restart, fails. Set the same `MCP_STATE_KEY` on every replica.
- **Credentials never travel through a form.** Use URL-mode elicitation (a browser flow) for anything secret.
