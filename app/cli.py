"""
Command-line interface for the AI Research Agent.
"""
import os
import sys
import argparse
import time
from typing import Dict, List, Any, Optional, Union

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.markdown import Markdown
from rich.progress import Progress, SpinnerColumn, TextColumn

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agent import config
from agent.planner import Planner
from agent.executor import Executor
from agent.logger import AgentLogger

logger = AgentLogger(__name__)
console = Console()

def parse_arguments():
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description=f"{config.AGENT_NAME}: {config.AGENT_OBJECTIVE}"
    )
    
    parser.add_argument(
        "query", 
        nargs="?", 
        type=str,
        help="Research query to process"
    )
    
    parser.add_argument(
        "--dry-run", 
        action="store_true",
        help="Show execution plan without performing actions"
    )
    
    parser.add_argument(
        "--verbose", 
        action="store_true",
        help="Show detailed execution information"
    )
    
    parser.add_argument(
        "-i", "--interactive",
        action="store_true",
        help="Run in interactive mode (command prompt)"
    )
    
    parser.add_argument(
        "--list-documents",
        action="store_true",
        help="List all indexed documents"
    )
    
    parser.add_argument(
        "--index-document",
        type=str,
        metavar="FILE_PATH",
        help="Index a document file"
    )
    
    parser.add_argument(
        "--index-directory",
        type=str,
        metavar="DIR_PATH",
        help="Index all documents in a directory"
    )
    
    return parser.parse_args()

def display_header():
    """Display the agent header."""
    console.print(
        Panel.fit(
            f"[bold blue]{config.AGENT_NAME}[/bold blue]\n"
            f"[italic]{config.AGENT_OBJECTIVE}[/italic]",
            border_style="blue"
        )
    )
    console.print()

def display_plan(plan):
    """Display the execution plan."""
    table = Table(title="Research Plan", show_header=True, header_style="bold")
    table.add_column("Step", style="dim")
    table.add_column("Action")
    table.add_column("Parameters")
    table.add_column("Reasoning")
    
    for i, step in enumerate(plan.steps):
        table.add_row(
            str(i+1),
            step.action,
            str(step.parameters),
            step.reasoning
        )
    
    console.print(table)
    console.print()

def display_summary(summary):
    """Display the research summary."""
    console.print(
        Panel(
            Markdown(summary),
            title="Research Summary",
            border_style="green",
            expand=False
        )
    )
    console.print()

def execute_query(query, dry_run=False, verbose=False):
    """Execute a research query."""
    try:
        with Progress(
            SpinnerColumn(),
            TextColumn("[bold blue]Planning research steps...[/bold blue]"),
            console=console,
            transient=True
        ) as progress:
            progress.start()
            
            # Create plan
            planner = Planner()
            plan = planner.create_plan(query)
            
            if not plan:
                console.print("[bold red]Failed to create a research plan.[/bold red]")
                return
        
        # Display the plan
        console.print("[bold]Generated Research Plan:[/bold]")
        display_plan(plan)
        
        # Confirm execution if not dry run
        if not dry_run and not console.input("[bold yellow]Execute this plan? (y/n): [/bold yellow]").lower().startswith('y'):
            console.print("[bold red]Execution cancelled.[/bold red]")
            return
            
        # Execute the plan
        with Progress(
            SpinnerColumn(),
            TextColumn("[bold green]Executing research plan...[/bold green]"),
            console=console,
            transient=not verbose
        ) as progress:
            progress.start()
            
            executor = Executor()
            summary, context = executor.execute_plan(plan, dry_run=dry_run)
        
        # Display the summary
        if dry_run:
            console.print("[bold]Execution Preview:[/bold]")
            console.print(Markdown(summary))
        else:
            console.print("[bold]Research Summary:[/bold]")
            display_summary(summary)
            
            # Offer to save the summary
            if console.input("[bold yellow]Save this summary to a file? (y/n): [/bold yellow]").lower().startswith('y'):
                filename = f"summary_{int(time.time())}.md"
                with open(filename, "w") as f:
                    f.write(summary)
                console.print(f"[bold green]Summary saved to {filename}[/bold green]")
                
    except KeyboardInterrupt:
        console.print("\n[bold red]Operation cancelled by user.[/bold red]")
    except Exception as e:
        console.print(f"[bold red]Error: {str(e)}[/bold red]")
        logger.error(f"Error executing query: {str(e)}")

def interactive_mode():
    """Run the agent in interactive mode."""
    display_header()
    console.print("[bold]Interactive Mode:[/bold] Type 'exit' or 'quit' to end session\n")
    
    while True:
        try:
            query = console.input("[bold blue]> [/bold blue]")
            
            if query.lower() in ('exit', 'quit'):
                break
                
            if not query.strip():
                continue
                
            execute_query(query)
            
        except KeyboardInterrupt:
            console.print("\n[bold red]Session terminated.[/bold red]")
            break
            
    console.print("[bold]Session ended.[/bold]")

def list_documents():
    """List all indexed documents."""
    from agent.tools.documents import DocumentRetrievalTool
    
    try:
        doc_tool = DocumentRetrievalTool()
        documents = doc_tool.list_documents()
        
        if not documents:
            console.print("[bold yellow]No documents found in the index.[/bold yellow]")
            return
        
        table = Table(title="Indexed Documents", show_header=True, header_style="bold")
        table.add_column("Filename")
        table.add_column("Type")
        table.add_column("Path")
        table.add_column("Size")
        table.add_column("Modified")
        
        for doc in documents:
            table.add_row(
                doc["filename"],
                doc["type"],
                doc["path"],
                f"{doc['size_bytes'] / 1024:.1f} KB",
                doc["modified"]
            )
        
        console.print(table)
        
    except Exception as e:
        console.print(f"[bold red]Error listing documents: {str(e)}[/bold red]")
        logger.error(f"Error listing documents: {str(e)}")

def index_document(file_path):
    """Index a document file."""
    from agent.tools.documents import DocumentRetrievalTool
    
    try:
        doc_tool = DocumentRetrievalTool()
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[bold blue]Indexing document...[/bold blue]"),
            console=console,
            transient=True
        ) as progress:
            progress.start()
            success = doc_tool.index_document(file_path)
        
        if success:
            console.print(f"[bold green]Successfully indexed: {file_path}[/bold green]")
        else:
            console.print(f"[bold red]Failed to index: {file_path}[/bold red]")
            
    except Exception as e:
        console.print(f"[bold red]Error indexing document: {str(e)}[/bold red]")
        logger.error(f"Error indexing document: {str(e)}")

def index_directory(directory_path):
    """Index all documents in a directory."""
    from agent.tools.documents import DocumentRetrievalTool
    
    try:
        doc_tool = DocumentRetrievalTool()
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[bold blue]Indexing directory...[/bold blue]"),
            console=console,
            transient=True
        ) as progress:
            progress.start()
            count = doc_tool.index_directory(directory_path)
        
        if count > 0:
            console.print(f"[bold green]Successfully indexed {count} documents from: {directory_path}[/bold green]")
        else:
            console.print(f"[bold yellow]No documents indexed from: {directory_path}[/bold yellow]")
            
    except Exception as e:
        console.print(f"[bold red]Error indexing directory: {str(e)}[/bold red]")
        logger.error(f"Error indexing directory: {str(e)}")

def main():
    """Main entry point for the CLI."""
    args = parse_arguments()
    
    # Handle document operations
    if args.list_documents:
        display_header()
        list_documents()
        return
        
    if args.index_document:
        display_header()
        index_document(args.index_document)
        return
        
    if args.index_directory:
        display_header()
        index_directory(args.index_directory)
        return
    
    # Interactive mode
    if args.interactive:
        interactive_mode()
        return
    
    # Query mode
    if args.query:
        display_header()
        execute_query(args.query, dry_run=args.dry_run, verbose=args.verbose)
    else:
        # If no query and no special commands, show help
        parse_arguments().print_help()

if __name__ == "__main__":
    main() 