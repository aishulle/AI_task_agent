import * as vscode from 'vscode';
import * as cp from 'child_process';
import * as path from 'path';

export function activate(context: vscode.ExtensionContext) {
    let disposable = vscode.commands.registerCommand('ai-task-agent.run', async () => {
        const task = await vscode.window.showInputBox({
            prompt: 'Enter your task for the AI agent',
            placeHolder: 'e.g. Create a Python file that prints Fibonacci series'
        });

        if (!task) return;

        const pythonPath = 'python'; // or 'python3' depending on your system
        const scriptPath = path.join(context.extensionPath, '..', 'ai_task_agent.py');

        const terminal = vscode.window.createTerminal('AI Task Agent');
        terminal.show();
		terminal.sendText(`${pythonPath} "${scriptPath}" "${task.replace(/"/g, '\\"')}"`);

    });

    context.subscriptions.push(disposable);
}
