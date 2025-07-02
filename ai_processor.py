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

try:
    from rich.console import Console
    from rich.markdown import Markdown
    from rich.panel import Panel
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

    def process_input(self, input_text: str, prompt: str, provider: str = "openai",
                     api_key: Optional[str] = None, model: Optional[str] = None) -> str:
        processor = self.providers.get(provider)
        if not processor:
            raise ValueError(f"Unsupported provider: {provider}. Available: {', '.join(self.providers.keys())}")

        return processor(input_text, prompt, api_key, model)

    def process_with_openai(self, input_text: str, prompt: str,
                          api_key: Optional[str] = None, model: Optional[str] = None) -> str:
        """Process with OpenAI API (v1.0.0+)"""
        try:
            client = OpenAI(api_key=api_key or os.getenv("OPENAI_API_KEY"))
            model = model or "gpt-3.5-turbo"

            response = client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": "You are a senior penetration testing specialist with a lot of experience who is ready to analyze the results of various programs, configuration files, code, and much more for serious vulnerabilities, presenting all this in a short but informative form based on the operator's prompt."},
                    {"role": "user", "content": f"{prompt}\n\nInput data:\n{input_text}"}
                ],
                temperature=0.7
            )
            return response.choices[0].message.content
        except Exception as e:
            raise Exception(f"OpenAI API error: {str(e)}")

    def process_with_ollama(self, input_text: str, prompt: str,
                          api_key: Optional[str] = None, model: Optional[str] = None) -> str:
        """Process with local Ollama server"""
        try:
            model = model or "llama2"
            url = "http://localhost:11434/v1/chat/completions"
            data = {
                "model": model,
                "messages": [
                    {"role": "system", "content": "You are a senior penetration testing specialist with a lot of experience who is ready to analyze the results of various programs, configuration files, code, and much more for serious vulnerabilities, presenting all this in a short but informative form based on the operator's prompt."},
                    {"role": "user", "content": f"{prompt}\n\n{input_text}"}
                ],
                "stream": False
            }

            response = requests.post(url, json=data)
            response.raise_for_status()
            return response.json()["choices"][0]["message"]["content"]
        except Exception as e:
            raise Exception(f"Ollama error: {str(e)}. Is Ollama running? Try 'ollama serve'")

    def process_with_deepseek(self, input_text: str, prompt: str,
                            api_key: Optional[str] = None, model: Optional[str] = None) -> str:
        """Process with DeepSeek API"""
        raise Exception(
            "DeepSeek API currently requires payment. "
            "Please use another provider like 'openai' or 'ollama'."
        )

def centered_text(text: str, width: int = OUTPUT_WIDTH) -> str:
    """Center text within given width"""
    return "\n".join(line.center(width) for line in text.splitlines())

def print_analysis_header():
    """Print beautiful header for AI analysis"""
    separator = "=" * OUTPUT_WIDTH
    title = "🛡️ AI SECURITY ANALYSIS"
    
    if rich_available:
        console = Console(width=OUTPUT_WIDTH)
        console.print(separator)
        console.print(title, justify="center", style="bold green")
        console.print(separator + "\n")
    else:
        print(separator)
        print(title.center(OUTPUT_WIDTH))
        print(separator + "\n")

def print_analysis_footer():
    """Print beautiful footer for AI analysis"""
    separator = "=" * OUTPUT_WIDTH
    title = "END OF ANALYSIS"
    
    if rich_available:
        console = Console(width=OUTPUT_WIDTH)
        console.print("\n" + separator)
        console.print(title, justify="center", style="bold green")
        console.print(separator)
    else:
        print("\n" + separator)
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

def main():
    parser = argparse.ArgumentParser(
        description="Process security tools output with AI",
        formatter_class=argparse.RawTextHelpFormatter,
        epilog="""Examples:
  # With OpenAI
  nmap scan.xml | ./ai_processor.py -ai "Analyze ports" --provider openai --api-key sk-...

  # With Ollama
  nikto report.txt | ./ai_processor.py -ai "List vulnerabilities" --provider ollama
""")

    parser.add_argument("-ai", "--ai-prompt", required=True, help="Your analysis prompt")
    parser.add_argument("--provider", choices=["openai", "ollama", "deepseek"],
                       default="openai", help="AI provider to use")
    parser.add_argument("--api-key", help="API key (or use env vars)")
    parser.add_argument("--model", help="Model name (e.g. 'gpt-4', 'llama2')")
    parser.add_argument("--no-live", action="store_true", help="Disable live output of tool results")

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
        print("Error: Pipe input data to this script".center(OUTPUT_WIDTH), file=sys.stderr)
        parser.print_help()
        sys.exit(1)

    processor = AIProcessor()

    try:
        # Start AI processing in a separate thread with spinner
        result = ""
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
            model=args.model
        )
        
        # Stop spinner and clear line
        spinner_active = False
        spinner_thread.join(timeout=0.1)
        sys.stdout.write("\r" + " " * OUTPUT_WIDTH + "\r")
        sys.stdout.flush()

        # Print AI analysis with beautiful formatting
        print_analysis_header()
        
        if rich_available:
            console = Console(width=OUTPUT_WIDTH)
            console.print(Markdown(result))
        else:
            print(format_text(result))
            
        print_analysis_footer()

    except Exception as e:
        error_msg = f"🚨 Error: {str(e)}"
        # Ensure error message fits within output width
        wrapped_error = textwrap.fill(error_msg, width=OUTPUT_WIDTH)
        
        if rich_available:
            Console(stderr=True, width=OUTPUT_WIDTH).print(f"[bold red]{wrapped_error}[/bold red]")
        else:
            print(wrapped_error, file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()
