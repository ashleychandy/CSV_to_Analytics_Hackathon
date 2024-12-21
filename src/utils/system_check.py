from rich.console import Console
from rich.table import Table
from datetime import datetime
import httpx
from src.tests.test_processor import test_process_transaction

async def verify_system():
    console = Console()
    table = Table(title="System Health Check")
    
    table.add_column("Component", style="cyan")
    table.add_column("Status", style="magenta")
    table.add_column("Details", style="green")
    
    # Check API Health
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get("http://localhost:8000/health")
            health_data = response.json()
            table.add_row(
                "API Health",
                "✅ Online" if health_data["status"] == "healthy" else "❌ Offline",
                str(health_data)
            )
    except Exception as e:
        table.add_row("API Health", "❌ Offline", str(e))
    
    # Test Transaction Processing
    test_result = await test_process_transaction()
    table.add_row(
        "Transaction Processing",
        "✅ Working" if test_result else "❌ Failed",
        "All tests passed" if test_result else "Check logs for details"
    )
    
    console.print(table) 