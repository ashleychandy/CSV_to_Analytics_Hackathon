from rich.progress import Progress, SpinnerColumn, TimeElapsedColumn

class TransactionProgress:
    def __init__(self):
        self.progress = Progress(
            SpinnerColumn(),
            *Progress.get_default_columns(),
            TimeElapsedColumn(),
            transient=False
        )
        
    def start_tracking(self, total: int):
        self.task = self.progress.add_task(
            "[green]Processing Transactions", 
            total=total
        )
        
    def update(self, advance: int = 1):
        self.progress.update(self.task, advance=advance) 