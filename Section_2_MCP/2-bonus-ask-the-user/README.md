# Bonus 2: When a tool needs your input

Sometimes, a tool needs a little more information before it can complete a task.

For example, imagine asking a tool to create a table of research papers. Before starting, it might need to know:

- How far back should the search go?
- How many papers should be included?
- Should it include only open-access papers?

Instead of making these decisions for you, the tool can **ask you to confirm your preferences first**.

In this bonus exercise, you'll see how that works with MCP.

## 1. How does it work?

The process is quite simple:

1. **You request something:** For example, an evidence table about a research topic.
2. **The server asks a question:** It needs you to confirm a few details before continuing.
3. **You provide your answers:** The client sends your choices back to the server.
4. **The tool completes the task:** The server uses your answers to create the evidence table.

Behind the scenes, this involves two requests to the server instead of one. This is called a *multi round-trip request* (MRTR).

You don't need to understand the technical details to follow this exercise.

## 2. What are we testing?

We've already prepared a tool called `build_evidence_table` in `server.py`.

The tool searches scientific literature and creates an evidence table. But before searching, it asks you to confirm:

- **Earliest publication year:** How old can the papers be?
- **Number of papers:** How many results do you want?
- **Open access:** Do you only want papers that are freely available?

The example code is provided, so you don't need to write anything yourself.

## 3. Try it yourself

First, make sure the reference server is running.

If it isn't, open a terminal and run:

```bash
python server.py
```

Keep the server running. Open another terminal in the project folder and run:

```bash
python 2-bonus-ask-the-user/ask_the_user.py
```

You should see a few questions appear in the terminal.

**Your task:**

1. Read the questions.
2. Enter your preferred values, or press **Enter** to keep the suggested defaults.
3. Look at the evidence table generated using your choices.

That's it! You've now seen how an MCP tool can ask for your input before completing a task.

## 4. Want to see what happens behind the scenes? (Optional)

You can also run:

```bash
python 2-bonus-ask-the-user/ask_the_user.py --wire
```

This shows the actual messages exchanged between the client and server.

You may notice a few unfamiliar terms:

| What you'll see | What it means |
|---|---|
| `input_required` | The server needs an answer before it can continue |
| `inputRequests` | The questions the server wants to ask |
| `requestState` | Information that allows the server to safely continue the request |
| `inputResponses` | The answers provided by the user |
| `complete` | The tool has finished its task |

The example also shows what happens when something goes wrong, such as changing the saved request information or calling a tool without supporting user questions.

**Don't worry about understanding every message.** The important thing is to see how the server asks for information, receives an answer, and continues.

## 5. A few things to keep in mind

- **Not every application can ask questions.** The client must support this feature. Otherwise, the server will return an error for tools that require it.
- **The server checks that requests are valid.** If someone changes the information needed to continue a request (`requestState`), the server rejects it.
- **Sensitive information needs extra care.** Passwords and other secrets should not be collected through these ordinary questions.

For those interested in the implementation, the example uses the MCP SDK's `Elicit` and `Resolve` helpers. The client uses an `elicitation_callback` to handle questions from the server. If you deploy multiple copies of the server, they also need to share the same `MCP_STATE_KEY` so requests can continue reliably.

These details are optional for this workshop.

## 6. What should you take away?

**An MCP tool doesn't always have to do everything immediately.**

Sometimes, the best approach is to ask the user for a little more information before continuing.

This is particularly useful in research, where decisions such as publication dates, search limits, and inclusion criteria should often be made by the researcher rather than automatically.

**For now, focus on running the example and observing what happens.** You can always come back to the code and technical details later.