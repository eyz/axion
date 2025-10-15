#!/usr/bin/env python3
"""View discussion.log with Rich formatting/colors."""

import sys
from pathlib import Path
from rich.console import Console

def main():
    console = Console()
    log_file = Path("discussion.log")
    
    if not log_file.exists():
        console.print("[red]discussion.log not found[/red]")
        return
    
    # Read and display with markup
    with open(log_file, 'r', encoding='utf-8') as f:
        for line in f:
            console.print(line.rstrip())

if __name__ == "__main__":
    main()

