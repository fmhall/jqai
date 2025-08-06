"""
jqai - A tool to generate and execute jq programs using LLMs.
"""
from typing import Optional
import os
import sys
import subprocess
from dataclasses import dataclass

import typer
from openai import OpenAI
from rich import print

# Constants
DEFAULT_CHUNK_SIZE = 8192
DEFAULT_PREVIEW_LENGTH = 1024
DEFAULT_MODEL = "gpt-4.1-mini"

SYSTEM_PROMPT = """
Based on the the desired query, write a jq program

Return only the jq program to be executed as a raw string, no string delimiters
wrapping it, no yapping, no markdown, no fenced code blocks, what you return
will be passed to subprocess.check_output('jq', [...]) directly.
For example, if the user asks: extract the name of the first person
You return only: .people[0].name
""".strip()

SYSTEM_PROMPT_NO_PIPE = """
Based on the the desired outcome for the user, determine which command line execution is best suited.

For example, if the users asks to get the users who have made issues on simonw/datasette, 
and count by user.login, top 3, you should return:

curl -s https://api.github.com/repos/simonw/datasette/issues | jq 'group_by(.user.login) | map({"user": .[0].user.login, "count": length}) | sort_by(.count) | reverse | .[0:3]'

Return only the command to be executed as a raw string, no string delimiters
wrapping it, no yapping, no markdown, no fenced code blocks, what you return
will be executed as a shell command.
"""


@dataclass
class Config:
    """Configuration for jqai."""
    model_name: str = DEFAULT_MODEL
    preview_length: int = DEFAULT_PREVIEW_LENGTH
    output_only: bool = False
    silent: bool = True
    verbose: bool = True


def get_openai_client() -> OpenAI:
    """Initialize and return OpenAI client with proper error handling."""
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise ValueError(
            "OPENAI_API_KEY environment variable is not set. "
            "Please set it before running the program.\n"
            "Echo is the easiest way to get started.\n"
            "Get an API key at https://echo.merit.systems/cli-auth?appId=f6e82af0-ddda-47d9-9bb5-a82ffa41ba73"
            "and set it with `export OPENAI_API_KEY=<your-key>`"
        )
    if api_key.startswith("echo_"):
        base_url = "https://echo.router.merit.systems"
    else:
        base_url = "https://api.openai.com/v1"
    return OpenAI(api_key=api_key, base_url=base_url)

def generate_jq_program(
    intent: str,
    example_json: Optional[str],
    model: OpenAI,
    config: Config,
    system_prompt: str
) -> str:
    """Generate a jq program using the LLM.
    
    Args:
        intent: Natural language description of the desired transformation
        example_json: Optional example JSON to help guide the generation
        model: Initialized OpenAI client
        config: Configuration options for the program
        system_prompt: The system prompt to use for generation
    """
    prompt = intent
    if example_json:
        prompt += f"\n\nExample JSON snippet:\n{example_json}"

    if config.verbose:
        print(f"System:\n{system_prompt}")
        print(f"Prompt:\n{prompt}")

    response = model.chat.completions.create(
        model=config.model_name,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": prompt},
        ],
    )
    
    program = response.choices[0].message.content.strip()
    
    if config.verbose:
        print(f"Response:\n{program}")
    
    return program


def execute_jq(
    program: str,
    initial_data: Optional[bytes],
    config: Config
) -> None:
    """Execute the generated jq program with the provided input."""
    process = subprocess.Popen(
        ["jq", program],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )

    try:
        # Write initial data if we have it
        if initial_data:
            process.stdin.write(initial_data)

        # Stream remaining stdin to jq
        if not sys.stdin.isatty():
            while True:
                chunk = sys.stdin.buffer.read(DEFAULT_CHUNK_SIZE)
                if not chunk:
                    break
                process.stdin.write(chunk)
        
        # Important: Close stdin to signal we're done writing
        process.stdin.close()

        # Read and output all stdout at once
        stdout_data = process.stdout.read()
        if stdout_data:
            sys.stdout.buffer.write(stdout_data)
            sys.stdout.buffer.flush()

        # Handle stderr
        stderr_data = process.stderr.read()
        if stderr_data:
            sys.stderr.buffer.write(stderr_data)
            sys.stderr.buffer.flush()

        return_code = process.wait()

        if not config.silent and not config.verbose:
            print(f"\njq program: {program}", file=sys.stderr)

        sys.exit(return_code)

    except BrokenPipeError:
        # Handle case where output pipe is closed
        devnull = os.open(os.devnull, os.O_WRONLY)
        os.dup2(devnull, sys.stdout.fileno())
        sys.exit(1)
    except KeyboardInterrupt:
        # Handle Ctrl+C gracefully
        process.terminate()
        process.wait()
        sys.exit(130)
    finally:
        process.stdout.close()
        process.stderr.close()


def execute_command(command: str, config: Config) -> None:
    """Execute a shell command and handle its output."""
    try:
        process = subprocess.Popen(
            command,
            shell=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )

        stdout_data, stderr_data = process.communicate()

        if stdout_data:
            sys.stdout.buffer.write(stdout_data)
            sys.stdout.buffer.flush()

        if stderr_data:
            sys.stderr.buffer.write(stderr_data)
            sys.stderr.buffer.flush()

        if not config.silent and not config.verbose:
            print(f"\ncommand: {command}", file=sys.stderr)

        sys.exit(process.returncode)

    except KeyboardInterrupt:
        process.terminate()
        process.wait()
        sys.exit(130)


def jq(
    intent: str,
    model: OpenAI,
    config: Config
) -> None:
    """
    Process JSON data with a jq program generated from a natural language description.

    Args:
        intent: Natural language description of the desired jq transformation
        model: Initialized OpenAI client
        config: Configuration options for the program
    """
    is_pipe = not sys.stdin.isatty()
    initial_data = None

    if is_pipe:
        initial_data = sys.stdin.buffer.read(config.preview_length)
        example_json = initial_data.decode() if initial_data else None
        system_prompt = SYSTEM_PROMPT
    else:
        example_json = None
        system_prompt = SYSTEM_PROMPT_NO_PIPE

    program = generate_jq_program(intent, example_json, model, config, system_prompt)

    if config.output_only:
        print(program)
        return

    if not is_pipe:
        execute_command(program, config)
        return

    execute_jq(program, initial_data, config)


def main(
    intent: str,
    model_name: str = typer.Option(
        DEFAULT_MODEL,
        "--model", "-m",
        help="The OpenAI model to use for generating jq programs"
    ),
    preview_length: int = typer.Option(
        DEFAULT_PREVIEW_LENGTH,
        "--preview-length", "-p",
        help="Number of bytes to read from input for preview in LLM context"
    ),
    output_only: bool = typer.Option(
        False,
        "--output-only", "-o",
        help="Only output the generated program without executing it"
    ),
    silent: bool = typer.Option(
        True,
        "--silent/--verbose", "-s/-v",
        help="Control output verbosity. Verbose mode shows prompts and responses"
    ),
) -> None:
    """
    Generate and execute jq programs using natural language.

    Args:
        intent: Natural language description of what you want to do with the JSON
        model_name: OpenAI model to use (default: gpt-4)
        preview_length: Bytes of input to include in LLM context (default: 1024)
        output_only: Only show the generated program without running it
        silent: Reduce output verbosity (use --verbose for more details)

    Examples:
        # Pipe JSON and transform it
        cat data.json | jqai "get all user names and emails"

        # Direct command that fetches and processes data
        jqai "show the latest 5 issues from simonw/datasette repo"

        # Only output the generated jq program
        cat data.json | jqai "count items by type" --output-only

        # Use a different model with verbose output
        cat data.json | jqai "complex analysis" --model gpt-4-turbo-preview --verbose
    """
    try:
        model = get_openai_client()
        config = Config(
            model_name=model_name,
            preview_length=preview_length,
            output_only=output_only,
            silent=silent,
            verbose=not silent
        )
        jq(intent, model, config)
    except Exception as e:
        print(f"Error: {str(e)}", file=sys.stderr)
        sys.exit(1)


def run() -> None:
    """CLI entry point."""
    typer.run(main)
