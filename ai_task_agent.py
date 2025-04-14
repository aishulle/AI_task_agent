import os
import subprocess
import sys
import textwrap
from typing import List, Tuple, Dict, Any, Optional
import json

# For colored terminal output
try:
    from colorama import Fore, Style, init
    init()  # Initialize colorama
    COLOR_ENABLED = True
except ImportError:
    # Fallback if colorama is not installed
    class DummyColor:
        def __getattr__(self, name):
            return ""
    Fore = DummyColor()
    Style = DummyColor()
    COLOR_ENABLED = False

# Try to import different AI APIs - will use the first available one
AI_PROVIDER = None
try:
    import google.generativeai as genai
    AI_PROVIDER = "GEMINI"
except ImportError:
    try:
        import openai
        AI_PROVIDER = "OPENAI"
    except ImportError:
        try:
            import anthropic
            AI_PROVIDER = "ANTHROPIC"
        except ImportError:
            pass

# Try to load environment variables
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass  # .env file loading is optional

class AITaskAgent:
    def __init__(self):
        """Initialize the AI Task Agent with the first available AI provider."""
        self.setup_ai_provider()
        
    def setup_ai_provider(self):
        """Configure the AI provider based on available libraries and API keys."""
        if AI_PROVIDER == "GEMINI":
            api_key = os.getenv("GEMINI_API_KEY")
            if not api_key:
                print(Fore.RED + "GEMINI_API_KEY not found in environment variables" + Style.RESET_ALL)
                sys.exit(1)
            
            genai.configure(api_key=api_key)
            self.model = genai.GenerativeModel('gemini-1.5-pro-latest')
            self.ai_name = "Gemini"
            
        elif AI_PROVIDER == "OPENAI":
            api_key = os.getenv("OPENAI_API_KEY")
            if not api_key:
                print(Fore.RED + "OPENAI_API_KEY not found in environment variables" + Style.RESET_ALL)
                sys.exit(1)
                
            openai.api_key = api_key
            self.model = "gpt-4"  # Default to GPT-4
            self.ai_name = "OpenAI"
            
        elif AI_PROVIDER == "ANTHROPIC":
            api_key = os.getenv("ANTHROPIC_API_KEY")
            if not api_key:
                print(Fore.RED + "ANTHROPIC_API_KEY not found in environment variables" + Style.RESET_ALL)
                sys.exit(1)
                
            self.client = anthropic.Anthropic(api_key=api_key)
            self.model = "claude-3-opus-20240229"
            self.ai_name = "Claude"
            
        else:
            print(Fore.RED + "No AI provider available. Please install one of: google-generativeai, openai, or anthropic" + Style.RESET_ALL)
            sys.exit(1)
            
        print(Fore.GREEN + f"Using {self.ai_name} as AI provider" + Style.RESET_ALL)

    def get_ai_response(self, prompt: str) -> Optional[str]:
        """Get a response from the AI model."""
        try:
            if AI_PROVIDER == "GEMINI":
                response = self.model.generate_content(
                    prompt,
                    generation_config={
                        "temperature": 0.2,
                        "max_output_tokens": 4096,
                    }
                )
                return response.text
                
            elif AI_PROVIDER == "OPENAI":
                response = openai.ChatCompletion.create(
                    model=self.model,
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.2,
                    max_tokens=4096
                )
                return response.choices[0].message.content
                
            elif AI_PROVIDER == "ANTHROPIC":
                response = self.client.messages.create(
                    model=self.model,
                    max_tokens=4096,
                    temperature=0.2,
                    messages=[{"role": "user", "content": prompt}]
                )
                return response.content[0].text
                
        except Exception as e:
            print(Fore.RED + f"AI API Error: {str(e)}" + Style.RESET_ALL)
            return None

    def parse_plan(self, plan: str) -> List[Tuple[str, str, str]]:
        """
        Parse the AI-generated plan into a list of actions.
        
        Returns:
            List of tuples: (action_type, target, content)
              - action_type: "file" or "command"
              - target: filename or command string
              - content: file content or empty string for commands
        """
        actions = []
        lines = plan.strip().split("\n")
        
        current_type = None
        current_target = None
        current_content = []
        in_code_block = False
        
        for line in lines:
            line = line.rstrip()
            
            # Check for code block markers
            if line.startswith("```"):
                if not in_code_block:
                    in_code_block = True
                    # Check if there's a language specifier and skip it
                    if len(line) > 3:
                        continue
                else:
                    in_code_block = False
                continue
                
            # Check for action markers
            if line.startswith("FILE:"):
                # Save previous file if exists
                if current_type == "file" and current_target:
                    actions.append((current_type, current_target, "\n".join(current_content)))
                    current_content = []
                
                current_type = "file"
                current_target = line[5:].strip()
                continue
                
            if line.startswith("COMMAND:"):
                # Save previous file if exists
                if current_type == "file" and current_target:
                    actions.append((current_type, current_target, "\n".join(current_content)))
                    current_content = []
                
                command = line[8:].strip()
                actions.append(("command", command, ""))
                current_type = None
                current_target = None
                continue
                
            # Add content line if inside a file
            if current_type == "file" and current_target:
                current_content.append(line)
        
        # Add the last file if exists
        if current_type == "file" and current_target:
            actions.append((current_type, current_target, "\n".join(current_content)))
            
        return actions

    def validate_python_code(self, code: str) -> bool:
        """Validate Python code for syntax errors."""
        try:
            compile(code, '<string>', 'exec')
            return True
        except SyntaxError as e:
            print(Fore.RED + f"Python syntax error: {e}" + Style.RESET_ALL)
            print(Fore.YELLOW + "Problematic code:" + Style.RESET_ALL)
            
            # Show the problematic line with context
            lines = code.split('\n')
            start = max(0, e.lineno - 3)
            end = min(len(lines), e.lineno + 2)
            
            for i in range(start, end):
                prefix = ">> " if i == e.lineno - 1 else "   "
                print(f"{prefix}{i+1}: {lines[i]}")
                
            return False

    def execute_plan(self, actions: List[Tuple[str, str, str]]) -> Tuple[bool, str]:
        """
        Execute the parsed plan.
        
        Returns:
            Tuple[bool, str]: (success, error_message)
        """
        for i, (action_type, target, content) in enumerate(actions):
            try:
                if action_type == "command":
                    print(Fore.BLUE + f"Executing command [{i+1}/{len(actions)}]: {target}" + Style.RESET_ALL)
                    
                    # Execute the command and capture output
                    process = subprocess.Popen(
                        target, 
                        shell=True, 
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,
                        text=True
                    )
                    stdout, stderr = process.communicate()
                    
                    if process.returncode != 0:
                        error_msg = f"Command failed with exit code {process.returncode}\n{stderr}"
                        print(Fore.RED + error_msg + Style.RESET_ALL)
                        return False, error_msg
                    
                    # Print command output
                    if stdout:
                        print(Fore.CYAN + "Command output:" + Style.RESET_ALL)
                        print(stdout)
                        
                elif action_type == "file":
                    print(Fore.GREEN + f"Creating file [{i+1}/{len(actions)}]: {target}" + Style.RESET_ALL)
                    
                    # Check file content for Python files
                    if target.endswith('.py') and not self.validate_python_code(content):
                        error_msg = f"Python syntax error in file: {target}"
                        return False, error_msg
                    
                    # Create directory if it doesn't exist
                    directory = os.path.dirname(target)
                    if directory and not os.path.exists(directory):
                        os.makedirs(directory, exist_ok=True)
                        
                    # Write file content
                    with open(target, 'w', encoding='utf-8') as f:
                        f.write(content)
                        
            except Exception as e:
                error_msg = f"Error executing action {i+1}: {str(e)}"
                print(Fore.RED + error_msg + Style.RESET_ALL)
                return False, error_msg
                
        return True, ""

    def run(self):
        """Run the AI Task Agent interactive loop."""
        print(Fore.YELLOW + "=" * 60 + Style.RESET_ALL)
        print(Fore.YELLOW + f"AI Task Agent powered by {self.ai_name}" + Style.RESET_ALL)
        print(Fore.YELLOW + "Type 'exit' to quit" + Style.RESET_ALL)
        print(Fore.YELLOW + "=" * 60 + Style.RESET_ALL)
        
        # Task history for context
        task_history = []
        
        while True:
            try:
                # Get task from user
                task = input(Fore.CYAN + "\nTask: " + Style.RESET_ALL)
                if task.lower() == 'exit':
                    break
                    
                # Add task to history
                task_history.append({"role": "user", "content": task})
                
                # Get AI plan
                while True:
                    # Construct prompt with task history
                    history_context = ""
                    if len(task_history) > 1:
                        history_context = "Previous tasks and results:\n"
                        for entry in task_history[:-1]:
                            if entry["role"] == "user":
                                history_context += f"- User task: {entry['content']}\n"
                            else:
                                history_context += f"- Result: {entry['content']}\n"
                        history_context += "\n"
                    
                    prompt = f"""{history_context}
Current task: {task}

Create a detailed plan to accomplish this task. Your plan should include:
1. Files to create with their content
2. Commands to execute

Format your response strictly as follows:

FILE: <filename.ext>
```
<file content>
```

COMMAND: <command to execute>

Make sure:
- For Python files, include proper indentation and error handling
- Commands should be executable in a standard shell/terminal
- If creating directories is needed, add appropriate commands
- For programming tasks, include proper code that matches best practices
"""

                    print(Fore.YELLOW + "Generating plan..." + Style.RESET_ALL)
                    plan = self.get_ai_response(prompt)
                    
                    if not plan:
                        print(Fore.RED + "Failed to generate plan. Retrying..." + Style.RESET_ALL)
                        continue
                        
                    # Parse the plan
                    actions = self.parse_plan(plan)
                    if not actions:
                        print(Fore.RED + "No valid actions found in the plan. Retrying..." + Style.RESET_ALL)
                        continue
                    
                    # Display the plan
                    print(Fore.MAGENTA + "\n📋 Generated Plan:" + Style.RESET_ALL)
                    for i, (action_type, target, content) in enumerate(actions, 1):
                        if action_type == "command":
                            print(Fore.BLUE + f"{i}. Run: {target}" + Style.RESET_ALL)
                        else:
                            print(Fore.GREEN + f"{i}. Create file: {target}" + Style.RESET_ALL)
                            
                            # Print file content with syntax highlighting if it's not too long
                            if len(content.split('\n')) <= 20:
                                print("   Content:")
                                content_lines = content.split('\n')
                                for line in content_lines:
                                    print(f"   {line}")
                            else:
                                print(f"   ({len(content.split('\n'))} lines of content)")
                    
                    # Ask for confirmation
                    confirm = input(Fore.YELLOW + "\nExecute this plan? (y/n/r): " + Style.RESET_ALL).lower()
                    if confirm == 'n':
                        print(Fore.RED + "Plan rejected. Exiting task." + Style.RESET_ALL)
                        break
                    if confirm == 'r':
                        print(Fore.YELLOW + "Regenerating plan..." + Style.RESET_ALL)
                        continue
                    
                    # Execute the plan
                    print(Fore.YELLOW + "\n⚙️ Executing plan..." + Style.RESET_ALL)
                    success, error_message = self.execute_plan(actions)
                    
                    if success:
                        print(Fore.GREEN + "\n✅ Task completed successfully!" + Style.RESET_ALL)
                        
                        # Ask if task was successful from user's perspective
                        user_success = input(Fore.YELLOW + "Did this complete your task successfully? (y/n): " + Style.RESET_ALL).lower()
                        
                        if user_success == 'y':
                            task_history.append({"role": "assistant", "content": "Task completed successfully."})
                            break
                        else:
                            # Get feedback on what went wrong
                            feedback = input(Fore.YELLOW + "What issues did you encounter? " + Style.RESET_ALL)
                            task_history.append({"role": "assistant", "content": f"Task attempted but had issues: {feedback}"})
                            
                            # Update task with feedback
                            task = f"Fixing previous task: {task}. Issue reported: {feedback}"
                            print(Fore.YELLOW + "Refining the approach based on feedback..." + Style.RESET_ALL)
                            continue
                    else:
                        print(Fore.RED + f"\n❌ Task failed: {error_message}" + Style.RESET_ALL)
                        task_history.append({"role": "assistant", "content": f"Task failed: {error_message}"})
                        
                        # Update task with error information
                        task = f"Fixing previous task that failed with error: {error_message}"
                        print(Fore.YELLOW + "Trying alternative approach..." + Style.RESET_ALL)
                        
            except KeyboardInterrupt:
                print(Fore.YELLOW + "\nOperation cancelled by user" + Style.RESET_ALL)
                break
            except Exception as e:
                print(Fore.RED + f"\nUnexpected error: {str(e)}" + Style.RESET_ALL)

if __name__ == "__main__":
    import sys

    task = sys.argv[1] if len(sys.argv) > 1 else None

    try:
        agent = AITaskAgent()
        if task:
            # You can add a method like `run_single_task(task)` if you want smarter handling
            print(f"Received task: {task}")
            agent.run()  # Or implement a one-shot mode
        else:
            agent.run()
    except Exception as e:
        print(Fore.RED + f"Fatal error: {str(e)}" + Style.RESET_ALL)
        sys.exit(1)
       
    