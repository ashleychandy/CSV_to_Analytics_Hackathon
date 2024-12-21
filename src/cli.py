import asyncio
import typer
from rich.console import Console
from src.utils.system_check import verify_system

console = Console()

def main():
    """POS Revenue System CLI"""
    try:
        asyncio.run(verify_system())
    except Exception as e:
        console.print(f"[red]Error running health check: {str(e)}[/red]")
        raise SystemExit(1)

if __name__ == "__main__":
    main() 