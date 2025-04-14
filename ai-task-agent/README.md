#  AI Task Agent — VS Code Extension

This VS Code extension allows you to **run AI-powered automation tasks** using natural language.

### Example Task
You describe a task like:

> "Create a Python script that prints Fibonacci numbers."

The agent will:
- Use an AI API to generate a step-by-step plan.
- Show the proposed file + command actions.
- Ask for your approval.
- Execute the files and commands locally.
- Ask if the task was successful, and refine if needed.

---

## How It Works

- Written in **TypeScript**.
- Sends tasks to a backend **Python agent**.
- Uses `child_process` to run local commands.
- Supports OpenAI, Gemini, or Claude APIs (whichever is configured).

---

## Getting Started

### 1. Open the Extension in VS Code

```bash
cd ai-task-agent
code .
```

### 2. Install & Compile

```bash
npm install
npm run compile
```

This compiles `src/extension.ts` into `dist/extension.js`.

### 3. Launch the Extension
Press `F5` (or click the ▶️ Run button at the top).  
This opens a new Extension Development Host.

### 4. Run the Agent
Press `Ctrl + Shift + P` (or `Cmd + Shift + P`)  
Type:

```bash
Run AI Task Agent
```

Enter any task, for example:

```bash
Create
