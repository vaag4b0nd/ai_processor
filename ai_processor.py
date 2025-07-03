#!/usr/bin/env python3
import sys
import argparse
import os
from openai import OpenAI
import requests
from typing import Optional
import threading
import time
import textwrap
import re
from datetime import datetime

try:
    from rich.console import Console
    from rich.markdown import Markdown
    from rich.panel import Panel
    from rich.live import Live
    from rich.text import Text
    rich_available = True
except ImportError:
    rich_available = False

OUTPUT_WIDTH = 80

class AIProcessor:
    def __init__(self):
        self.providers = {
            "openai": self.process_with_openai,
            "ollama": self.process_with_ollama,
            "deepseek": self.process_with_deepseek
        }
        self.chat_history = []

    def process_input(self, input_text: str, prompt: str, provider: str = "openai",
                     api_key: Optional[str] = None, model: Optional[str] = None,
                     chat_mode: bool = False) -> str:
        # Build messages based on chat history or initial prompt
        if chat_mode and self.chat_history:
            messages = self.chat_history
        else:
            messages = [
                {"role": "system", "content": "You are a senior penetration testing specialist with a lot of experience who is ready to analyze the results of various programs, configuration files, code, and much more for serious vulnerabilities, presenting all this in a short but informative form based on the operator's prompt."},
                {"role": "user", "content": f"{prompt}\n\nInput data:\n{input_text}"}
            ]

        processor = self.providers.get(provider)
        if not processor:
            raise ValueError(f"Unsupported provider: {provider}. Available: {', '.join(self.providers.keys())}")

        result = processor(messages, api_key, model)
        
        # Update chat history for follow-up questions
        if chat_mode:
            self.chat_history.append({"role": "assistant", "content": result})
        return result

    def process_with_openai(self, messages: list, api_key: Optional[str] = None, model: Optional[str] = None) -> str:
        """Process with OpenAI API (v1.0.0+)"""
        try:
            client = OpenAI(api_key=api_key or os.getenv("OPENAI_API_KEY"))
            model = model or "gpt-3.5-turbo"

            response = client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=0.7
            )
            return response.choices[0].message.content
        except Exception as e:
            raise Exception(f"OpenAI API error: {str(e)}")

    def process_with_ollama(self, messages: list, api_key: Optional[str] = None, model: Optional[str] = None) -> str:
        """Process with local Ollama server"""
        try:
            model = model or "llama2"
            url = "http://localhost:11434/v1/chat/completions"
            data = {
                "model": model,
                "messages": messages,
                "stream": False
            }

            response = requests.post(url, json=data)
            response.raise_for_status()
            return response.json()["choices"][0]["message"]["content"]
        except Exception as e:
            raise Exception(f"Ollama error: {str(e)}. Is Ollama running? Try 'ollama serve'")

    def process_with_deepseek(self, messages: list, api_key: Optional[str] = None, model: Optional[str] = None) -> str:
        """Process with DeepSeek API"""
        raise Exception(
            "DeepSeek API currently requires payment. "
            "Please use another provider like 'openai' or 'ollama'."
        )
    
    def add_user_message(self, message: str):
        """Add user message to chat history"""
        self.chat_history.append({"role": "user", "content": message})

def print_analysis_header():
    """Print beautiful header for AI analysis"""
    separator = "=" * OUTPUT_WIDTH
    title = "🛡️ AI SECURITY ANALYSIS"
    
    if rich_available:
        console = Console(width=OUTPUT_WIDTH)
        console.print(separator)
        console.print(title, justify="center", style="bold")
        console.print(separator)
        console.print()  # Empty line
    else:
        print(separator)
        print(title.center(OUTPUT_WIDTH))
        print(separator)

def print_analysis_footer():
    """Print beautiful footer for AI analysis"""
    separator = "=" * OUTPUT_WIDTH
    title = "END OF ANALYSIS"
    
    if rich_available:
        console = Console(width=OUTPUT_WIDTH)
        console.print()
        console.print(separator)
        console.print(title, justify="center", style="bold")
        console.print(separator)
    else:
        print()
        print(separator)
        print(title.center(OUTPUT_WIDTH))
        print(separator)

def format_text(text: str) -> str:
    """Format text to fixed width output"""
    if rich_available:
        return text  # Rich will handle formatting
        
    # Format without rich: wrap text and preserve newlines
    formatted_lines = []
    for paragraph in text.split('\n\n'):
        wrapped = textwrap.fill(
            paragraph, 
            width=OUTPUT_WIDTH,
            replace_whitespace=False,
            drop_whitespace=False
        )
        formatted_lines.append(wrapped)
    
    return "\n\n".join(formatted_lines)

def save_to_markdown(content: str, filename: str, mode: str = 'w'):
    """Save content to markdown file with proper formatting"""
    try:
        with open(filename, mode, encoding='utf-8') as f:
            # Add timestamp and header for chat interactions
            if mode == 'a':
                timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                f.write(f"\n\n## 🔄 Follow-up ({timestamp})\n\n")
            f.write(content + "\n")
    except Exception as e:
        print(f"⚠️ Error saving to file: {str(e)}", file=sys.stderr)

def get_terminal_input():
    """Get input from terminal even when stdin is piped"""
    try:
        # Try to use /dev/tty on Unix systems
        if os.name == 'posix':
            tty = open('/dev/tty', 'r')
            return tty.readline().strip()
        # Try to use CONIN$ on Windows
        elif os.name == 'nt':
            con = open('CONIN$', 'r')
            return con.readline().strip()
    except Exception:
        pass
    
    # Fallback to sys.stdin if terminal input fails
    return sys.stdin.readline().strip()

def print_chat_header():
    """Print beautiful chat header"""
    separator = "━" * OUTPUT_WIDTH
    title = "💬 CHAT MODE ACTIVATED"
    subtitle = "Type your questions (or 'exit' to quit)"
    
    if rich_available:
        console = Console(width=OUTPUT_WIDTH)
        console.print(separator)
        console.print(title, justify="center", style="bold")
        console.print(subtitle, justify="center", style="dim")
        console.print(separator)
    else:
        print(separator)
        print(title.center(OUTPUT_WIDTH))
        print(subtitle.center(OUTPUT_WIDTH))
        print(separator)

def print_user_message(message: str):
    """Print user message with clean formatting"""
    timestamp = datetime.now().strftime("%H:%M:%S")
    
    if rich_available:
        console = Console(width=OUTPUT_WIDTH)
        panel = Panel(
            Markdown(message),
            title=f"YOU [{timestamp}]",
            title_align="right",
            width=OUTPUT_WIDTH-4,
            padding=(0, 1, 0, 1),
            style="dim"
        )
        console.print(panel, justify="right")
    else:
        # Simple formatting without rich
        print(f"\n┌─[YOU @ {timestamp}]")
        print(format_text(message))
        print("└" + "─" * (OUTPUT_WIDTH - 1))

def print_ai_message(message: str, live: Live = None):
    """Print AI message with clean formatting"""
    timestamp = datetime.now().strftime("%H:%M:%S")
    
    if rich_available:
        console = Console(width=OUTPUT_WIDTH)
        
        if live:
            # Update live display with final message
            panel = Panel(
                Markdown(message),
                title=f"AI ASSISTANT [{timestamp}]",
                width=OUTPUT_WIDTH-4,
                padding=(0, 1, 0, 1)
            )
            live.update(panel)
        else:
            # Print static message
            panel = Panel(
                Markdown(message),
                title=f"AI ASSISTANT [{timestamp}]",
                width=OUTPUT_WIDTH-4,
                padding=(0, 1, 0, 1)
            )
            console.print(panel, justify="left")
    else:
        # Simple formatting without rich
        print(f"\n┌─[AI ASSISTANT @ {timestamp}]")
        print(format_text(message))
        print("└" + "─" * (OUTPUT_WIDTH - 1))

def print_ai_analysis(message: str):
    """Print AI analysis with clean formatting"""
    if rich_available:
        console = Console(width=OUTPUT_WIDTH)
        panel = Panel(
            Markdown(message),
            width=OUTPUT_WIDTH-4,
            padding=(1, 2, 1, 2),
            subtitle="AI ANALYSIS",
            subtitle_align="right",
            style="dim"
        )
        console.print(panel)
    else:
        print("\n" + "─" * OUTPUT_WIDTH)
        print("AI ANALYSIS:")
        print("─" * OUTPUT_WIDTH)
        print(format_text(message))

def animated_ai_response(processor, args, message: str):
    """Display animated AI response with typing effect"""
    if not rich_available:
        return print_ai_message(message)
    
    console = Console(width=OUTPUT_WIDTH)
    timestamp = datetime.now().strftime("%H:%M:%S")
    
    # Create a panel for the animated response
    with Live(console=console, refresh_per_second=10) as live:
        # Initial empty message
        partial_response = ""
        panel = Panel(
            Text("Thinking...", style="dim"),
            title=f"AI ASSISTANT [{timestamp}]",
            width=OUTPUT_WIDTH-4,
            padding=(0, 1, 0, 1)
        )
        live.update(panel)
        
        # Process the AI response
        spinner_active = True
        
        def spinner():
            """Show loading spinner while processing"""
            symbols = ['⣾', '⣽', '⣻', '⢿', '⡿', '⣟', '⣯', '⣷']
            i = 0
            while spinner_active:
                title = f"AI ASSISTANT [{timestamp}] {symbols[i % len(symbols)]}"
                panel.title = title
                live.update(panel)
                time.sleep(0.1)
                i += 1
        
        # Start spinner in background
        spinner_thread = threading.Thread(target=spinner)
        spinner_thread.daemon = True
        spinner_thread.start()
        
        # Get AI response
        response = processor.process_input(
            "",
            "",
            provider=args.provider,
            api_key=args.api_key,
            model=args.model,
            chat_mode=True
        )
        
        # Stop spinner
        spinner_active = False
        spinner_thread.join(timeout=0.1)
        
        # Animate the typing effect
        words = response.split()
        current_text = ""
        
        for word in words:
            current_text += word + " "
            panel.renderable = Markdown(current_text)
            live.update(panel)
            time.sleep(0.03)  # Adjust typing speed
            
        # Add final panel with full message
        print_ai_message(response, live)
    
    return response

def main():
    parser = argparse.ArgumentParser(
        description="Process security tools output with AI",
        formatter_class=argparse.RawTextHelpFormatter,
        epilog="""Examples:
  # With OpenAI
  nmap scan.xml | ./ai_processor.py -ai "Analyze ports" --provider openai --api-key sk-...

  # With Ollama
  nikto report.txt | ./ai_processor.py -ai "List vulnerabilities" --provider ollama

  # Interactive chat mode
  cat report.txt | ./ai_processor.py -ai "Analyze this" --chat

  # Save to file
  ./ai_processor.py -ai "Check config" < config.txt --file analysis.md
""")

    parser.add_argument("-ai", "--ai-prompt", required=True, help="Your analysis prompt")
    parser.add_argument("--provider", choices=["openai", "ollama", "deepseek"],
                       default="openai", help="AI provider to use")
    parser.add_argument("--api-key", help="API key (or use env vars)")
    parser.add_argument("--model", help="Model name (e.g. 'gpt-4', 'llama2')")
    parser.add_argument("--no-live", action="store_true", help="Disable live output of tool results")
    parser.add_argument("--chat", action="store_true", help="Enable interactive chat for follow-up questions")
    parser.add_argument("--file", help="Save AI responses to a Markdown file")

    args = parser.parse_args()

    # Read input data from stdin
    input_data = ""
    if not sys.stdin.isatty():
        if args.no_live:
            # Read all input at once without live output
            input_data = sys.stdin.read()
        else:
            # Read input line by line with live output
            print("\n[+] Running security tool...\n")
            for line in sys.stdin:
                sys.stdout.write(line)
                sys.stdout.flush()
                input_data += line
            print("\n[+] Security tool completed. Starting AI analysis...\n")
    else:
        # Allow running without stdin in chat mode
        if not args.chat:
            print("Error: Pipe input data to this script or use --chat mode".center(OUTPUT_WIDTH), file=sys.stderr)
            parser.print_help()
            sys.exit(1)

    processor = AIProcessor()
    output_file = args.file

    try:
        # Start AI processing with spinner
        spinner_active = True
        
        def spinner():
            """Show loading spinner while processing"""
            symbols = ['⣾', '⣽', '⣻', '⢿', '⡿', '⣟', '⣯', '⣷']
            i = 0
            while spinner_active:
                sys.stdout.write(f"\r[+] AI processing {symbols[i % len(symbols)]}".ljust(OUTPUT_WIDTH))
                sys.stdout.flush()
                time.sleep(0.1)
                i += 1
        
        # Start spinner in background
        spinner_thread = threading.Thread(target=spinner)
        spinner_thread.daemon = True
        spinner_thread.start()
        
        # Process with AI
        result = processor.process_input(
            input_data,
            args.ai_prompt,
            provider=args.provider,
            api_key=args.api_key,
            model=args.model,
            chat_mode=args.chat
        )
        
        # Stop spinner and clear line
        spinner_active = False
        spinner_thread.join(timeout=0.1)
        sys.stdout.write("\r" + " " * OUTPUT_WIDTH + "\r")
        sys.stdout.flush()

        # Print AI analysis with beautiful formatting
        print_analysis_header()
        print_ai_analysis(result)
        print_analysis_footer()

        # Save initial response to file if requested
        if output_file:
            save_to_markdown(f"# Security Analysis Report\n\n**Prompt**: {args.ai_prompt}\n\n## Initial Analysis\n\n{result}", output_file)

        # Interactive chat mode
        if args.chat:
            print_chat_header()
            
            while True:
                try:
                    # Print input prompt
                    if rich_available:
                        console = Console(width=OUTPUT_WIDTH)
                        console.print("\n> ", end="", style="dim")
                    else:
                        print("\n> ", end="", flush=True)
                    
                    # Get user input
                    user_input = get_terminal_input()
                    if not user_input:
                        continue
                        
                    if user_input.lower() in ['exit', 'quit']:
                        print("Exiting chat mode")
                        break
                    
                    # Print user message
                    print_user_message(user_input)
                    
                    # Add user question to history
                    processor.add_user_message(user_input)
                    
                    # Get and display AI response
                    response = animated_ai_response(processor, args, user_input)
                    
                    # Save to file
                    if output_file:
                        save_to_markdown(response, output_file, mode='a')
                        
                except EOFError:
                    print("\nEnd of input. Exiting chat mode.")
                    break
                except KeyboardInterrupt:
                    print("\nExiting chat mode")
                    break
                except Exception as e:
                    print(f"🚨 Error: {str(e)}")

    except Exception as e:
        error_msg = f"🚨 Error: {str(e)}"
        # Ensure error message fits within output width
        wrapped_error = textwrap.fill(error_msg, width=OUTPUT_WIDTH)
        
        if rich_available:
            Console(stderr=True, width=OUTPUT_WIDTH).print(wrapped_error)
        else:
            print(wrapped_error, file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()
