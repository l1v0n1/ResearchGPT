"""
Command-line interface for ResearchGPT.
"""
import os
import sys
import argparse
import time
from pathlib import Path
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
    """Parse command-line arguments.
    
    Returns:
        tuple: (parser, args) - The argument parser and parsed arguments
    """
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
    
    parser.add_argument(
        "--list-summaries",
        action="store_true",
        help="List all saved research summaries"
    )
    
    parser.add_argument(
        "--view-summary",
        type=str,
        metavar="FILENAME",
        help="View a specific summary file"
    )
    
    args = parser.parse_args()
    return parser, args

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

def save_summary(query: str, summary: str) -> str:
    """
    Save a summary to a file in the summaries directory.
    
    Args:
        query: The original query
        summary: The summary text to save
        
    Returns:
        Path to the saved file
    """
    timestamp = int(time.time())
    
    # Create a slug from the query for the filename
    # Remove special characters, replace spaces with underscores, and limit length
    import re
    slug = re.sub(r'[^\w\s-]', '', query.lower())
    slug = re.sub(r'[\s-]+', '_', slug)
    slug = slug[:50]  # Limit length to avoid too long filenames
    
    # Add timestamp to ensure uniqueness
    filename = f"{slug}_{timestamp}.md"
    filepath = config.SUMMARIES_DIR / filename
    
    # Format timestamp for readable date
    formatted_time = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(timestamp))
    
    # Create content with metadata header
    content = f"""---
title: Research Summary
query: "{query}"
date: {formatted_time}
---

{summary}
"""
    
    with open(filepath, "w") as f:
        f.write(content)
    
    return str(filepath)

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
                filepath = save_summary(query, summary)
                console.print(f"[bold green]Summary saved to {filepath}[/bold green]")
                
    except KeyboardInterrupt:
        console.print("\n[bold red]Operation cancelled by user.[/bold red]")
    except Exception as e:
        console.print(f"[bold red]Error: {str(e)}[/bold red]")
        logger.error(f"Error executing query: {str(e)}")

def show_help():
    """Show help information for interactive mode."""
    console.print(Panel(
        "[bold blue]Available Commands:[/bold blue]\n\n"
        "[bold]Document Management:[/bold]\n"
        "  [green]list documents[/green] - Show all indexed documents\n"
        "  [green]index document <file_path>[/green] - Index a document file\n"
        "  [green]index directory <directory_path>[/green] - Index all documents in a directory\n"
        "  [green]search documents <query>[/green] - Search indexed documents\n"
        "  [green]get document <document_id>[/green] - Get document by ID (you can use partial IDs)\n"
        "  [green]get document help[/green] - Show all available document IDs\n\n"
        "[bold]Summary Management:[/bold]\n"
        "  [green]list summaries[/green] - Show all saved research summaries\n"
        "  [green]view summary <filename>[/green] - Display a specific summary file\n\n"
        "[bold]System Commands:[/bold]\n"
        "  [green]help[/green] - Show this help information\n"
        "  [green]exit[/green] or [green]quit[/green] - End the session\n\n"
        "[bold]Research Queries:[/bold]\n"
        "  Any other input will be treated as a research query",
        title="Help",
        border_style="blue",
        expand=False
    ))

def interactive_mode():
    """Run the agent in interactive mode."""
    display_header()
    console.print("[bold]Interactive Mode:[/bold] Type 'help' for available commands or 'exit' to end session\n")
    
    while True:
        try:
            query = console.input("[bold blue]> [/bold blue]")
            
            if query.lower() in ('exit', 'quit'):
                break
                
            if not query.strip():
                continue
            
            # Show help
            if query.lower() == 'help':
                show_help()
                continue
            
            # Handle document-related commands directly
            if query.lower() == 'list documents':
                list_documents()
                continue
            
            # Handle summary-related commands
            if query.lower() == 'list summaries':
                list_summaries()
                continue
                
            # Handle 'view summary' command
            if query.lower().startswith('view summary '):
                filename = query[len('view summary '):].strip()
                view_summary(filename)
                continue
            
            # Handle incomplete 'view summary' command
            if query.lower() == 'view summary' or query.lower().startswith('view summary') and len(query) <= 12:
                console.print("[bold yellow]Missing summary filename. Usage: view summary <filename>[/bold yellow]")
                filename = console.input("[bold yellow]Enter summary filename: [/bold yellow]")
                if filename.strip():
                    view_summary(filename.strip())
                continue
            
            # Handle incomplete 'index document' command    
            if query.lower() == 'index document' or query.lower().startswith('index document') and len(query) <= 14:
                console.print("[bold yellow]Missing document path. Usage: index document <file_path>[/bold yellow]")
                file_path = console.input("[bold yellow]Enter document path: [/bold yellow]")
                if file_path.strip():
                    index_document(file_path.strip())
                continue
                
            # Handle complete 'index document' command
            if query.lower().startswith('index document '):
                file_path = query[len('index document '):].strip()
                index_document(file_path)
                continue
            
            # Handle incomplete 'index directory' command
            if query.lower() == 'index directory' or query.lower().startswith('index directory') and len(query) <= 15:
                console.print("[bold yellow]Missing directory path. Usage: index directory <directory_path>[/bold yellow]")
                dir_path = console.input("[bold yellow]Enter directory path: [/bold yellow]")
                if dir_path.strip():
                    index_directory(dir_path.strip())
                continue
                
            # Handle complete 'index directory' command
            if query.lower().startswith('index directory '):
                dir_path = query[len('index directory '):].strip()
                index_directory(dir_path)
                continue
            
            # Handle incomplete 'search documents' command
            if query.lower() == 'search documents' or query.lower().startswith('search documents') and len(query) <= 16:
                console.print("[bold yellow]Missing search query. Usage: search documents <query>[/bold yellow]")
                search_query = console.input("[bold yellow]Enter search query: [/bold yellow]")
                if search_query.strip():
                    search_documents(search_query.strip())
                continue
                
            # Handle complete 'search documents' command
            if query.lower().startswith('search documents '):
                search_query = query[len('search documents '):].strip()
                search_documents(search_query)
                continue
            
            # Handle incomplete 'get document' command
            if query.lower() == 'get document' or query.lower().startswith('get document') and len(query) <= 12:
                console.print("[bold yellow]Missing document ID. Usage: get document <document_id>[/bold yellow]")
                doc_id = console.input("[bold yellow]Enter document ID: [/bold yellow]")
                if doc_id.strip():
                    get_document(doc_id.strip())
                continue
                
            # Handle complete 'get document' command
            if query.lower().startswith('get document '):
                doc_id = query[len('get document '):].strip()
                get_document(doc_id)
                continue
            
            # If not a special command, execute as a research query
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
        table.add_column("ID", style="dim")
        table.add_column("Filename")
        table.add_column("Type")
        table.add_column("Size")
        table.add_column("Created")
        
        for doc in documents:
            # Create nicely formatted ID (first 8 chars)
            short_id = doc.id[:8]
            
            table.add_row(
                short_id + "...",  # Show truncated ID
                doc.filename,
                doc.type,
                f"{doc.metadata.get('size_bytes', 0) / 1024:.1f} KB",
                doc.created_at or "Unknown"
            )
        
        console.print(table)
        console.print("[bold yellow]Tip: Use 'get document <id>' with just the first few characters of the ID.[/bold yellow]")
        
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
            doc_id = doc_tool.index_document(file_path)
        
        if doc_id:
            console.print(f"[bold green]Successfully indexed: {file_path}[/bold green]")
            console.print(f"[bold green]Document ID: {doc_id}[/bold green]")
        else:
            console.print(f"[bold red]Failed to index: {file_path}[/bold red]")
            
    except Exception as e:
        console.print(f"[bold red]Error indexing document: {str(e)}[/bold red]")
        logger.error(f"Error indexing document: {str(e)}")

def index_directory(directory_path):
    """Index all documents in a directory."""
    from agent.tools.documents import DocumentRetrievalTool
    import os
    from pathlib import Path
    
    try:
        doc_tool = DocumentRetrievalTool()
        dir_path = Path(directory_path)
        
        if not dir_path.exists() or not dir_path.is_dir():
            console.print(f"[bold red]Directory not found: {directory_path}[/bold red]")
            return
            
        # Get all supported file types
        supported_extensions = list(doc_tool.SUPPORTED_FILE_TYPES.keys())
        
        # Find all files with supported extensions
        document_files = []
        for ext in supported_extensions:
            document_files.extend(dir_path.glob(f"*{ext}"))
            
        if not document_files:
            console.print(f"[bold yellow]No supported documents found in: {directory_path}[/bold yellow]")
            return
            
        console.print(f"[bold blue]Found {len(document_files)} documents to index...[/bold blue]")
        
        # Index each file
        success_count = 0
        for file_path in document_files:
            if file_path.is_file():
                with Progress(
                    SpinnerColumn(),
                    TextColumn(f"[bold blue]Indexing {file_path.name}...[/bold blue]"),
                    console=console,
                    transient=True
                ) as progress:
                    progress.start()
                    doc_id = doc_tool.index_document(str(file_path))
                    
                if doc_id:
                    success_count += 1
                    
        if success_count > 0:
            console.print(f"[bold green]Successfully indexed {success_count} out of {len(document_files)} documents from: {directory_path}[/bold green]")
        else:
            console.print(f"[bold yellow]Failed to index any documents from: {directory_path}[/bold yellow]")
            
    except Exception as e:
        console.print(f"[bold red]Error indexing directory: {str(e)}[/bold red]")
        logger.error(f"Error indexing directory: {str(e)}")

def search_documents(query, num_results=5):
    """Search for documents using semantic search."""
    from agent.tools.documents import DocumentRetrievalTool
    
    try:
        doc_tool = DocumentRetrievalTool()
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[bold blue]Searching documents...[/bold blue]"),
            console=console,
            transient=True
        ) as progress:
            progress.start()
            results = doc_tool.search(query, num_results=num_results)
        
        if not results:
            console.print("[bold yellow]No matching documents found.[/bold yellow]")
            return
        
        console.print("[bold green]Search Results:[/bold green]")
        
        for i, result in enumerate(results):
            # Format document ID nicely
            doc_id = result.document_id
            formatted_id = f"{doc_id[:8]}...{doc_id[-8:]}" if len(doc_id) > 20 else doc_id
            
            # Check if this is a code file
            is_code = result.metadata.get("content_type") == "code"
            language = result.metadata.get("language", "")
            
            # Prepare the panel content
            if is_code:
                from pygments.lexers import get_lexer_by_name
                from pygments.formatters import TerminalFormatter
                from pygments import highlight
                
                # Try to get a lexer for syntax highlighting
                try:
                    lexer = get_lexer_by_name(language, stripall=True)
                    # Limit content length for preview
                    preview_content = result.content[:500] + ("..." if len(result.content) > 500 else "")
                    highlighted_code = highlight(preview_content, lexer, TerminalFormatter())
                    
                    panel_content = (
                        f"[bold blue]File:[/bold blue] {result.filename}\n"
                        f"[bold]Document ID:[/bold] {formatted_id}\n"
                        f"[bold]Language:[/bold] {language}\n"
                        f"[bold]Lines:[/bold] {result.metadata.get('line_count', 'Unknown')}\n"
                        f"[bold]Score:[/bold] {1.0 - result.score:.4f}\n"
                        f"[bold]Content:[/bold]\n{highlighted_code}"
                    )
                except Exception:
                    # Fallback if syntax highlighting fails
                    panel_content = (
                        f"[bold blue]File:[/bold blue] {result.filename}\n"
                        f"[bold]Document ID:[/bold] {formatted_id}\n"
                        f"[bold]Language:[/bold] {language}\n"
                        f"[bold]Score:[/bold] {1.0 - result.score:.4f}\n"
                        f"[bold]Content:[/bold]\n{result.content[:300]}..." if len(result.content) > 300 else result.content
                    )
            else:
                panel_content = (
                    f"[bold blue]Document:[/bold blue] {result.filename}\n"
                    f"[bold]Document ID:[/bold] {formatted_id}\n"
                    f"[bold]Score:[/bold] {1.0 - result.score:.4f}\n"
                    f"[bold]Content:[/bold]\n{result.content[:300]}..." if len(result.content) > 300 else result.content
                )
            
            console.print(
                Panel(
                    panel_content,
                    title=f"Result {i+1}",
                    border_style="green"
                )
            )
            console.print()
            
        console.print("[bold yellow]Tip: Use 'get document <id>' with the ID shown above to view the full document.[/bold yellow]")
            
    except Exception as e:
        console.print(f"[bold red]Error searching documents: {str(e)}[/bold red]")
        logger.error(f"Error searching documents: {str(e)}")

def get_document(document_id):
    """Get and display document summary by ID."""
    from agent.tools.documents import DocumentRetrievalTool
    
    try:
        doc_tool = DocumentRetrievalTool()
        
        # First, check if we need to list document IDs to help the user
        if document_id.lower() in ('list', 'help', '?'):
            console.print("[bold yellow]Available document IDs:[/bold yellow]")
            for doc in doc_tool.list_documents():
                console.print(f"[green]{doc.id}[/green] - {doc.filename}")
            return
            
        with Progress(
            SpinnerColumn(),
            TextColumn("[bold blue]Retrieving document...[/bold blue]"),
            console=console,
            transient=True
        ) as progress:
            progress.start()
            doc_summary = doc_tool.get_document(document_id)
        
        if not doc_summary:
            console.print(f"[bold red]Document not found with ID: {document_id}[/bold red]")
            console.print("[bold yellow]Tip: Use 'list documents' to see all available documents.[/bold yellow]")
            console.print("[bold yellow]Tip: You can use just the first few characters of the ID.[/bold yellow]")
            return
        
        # Format the full document ID nicely
        full_id = doc_summary.document_id
        formatted_id = f"{full_id[:8]}...{full_id[-8:]}" if len(full_id) > 20 else full_id
        
        # Check if this is a code file
        is_code = doc_summary.metadata.get("content_type") == "code"
        
        if is_code:
            # Try to add syntax highlighting if it's a code file
            language = doc_summary.metadata.get("language", "")
            imports = doc_summary.metadata.get("imports", [])
            line_count = doc_summary.metadata.get("line_count", "Unknown")
            
            try:
                from pygments.lexers import get_lexer_by_name
                from pygments.formatters import TerminalFormatter
                from pygments import highlight
                
                lexer = get_lexer_by_name(language, stripall=True)
                highlighted_code = highlight(doc_summary.content, lexer, TerminalFormatter())
                
                # Create imports section if available
                imports_section = ""
                if imports:
                    imports_section = "\n[bold]Imports/Dependencies:[/bold]\n"
                    for imp in imports:
                        imports_section += f"  • {imp}\n"
                
                # Display code file with syntax highlighting
                console.print(
                    Panel(
                        f"[bold blue]Filename:[/bold blue] {doc_summary.filename}\n"
                        f"[bold]Document ID:[/bold] {formatted_id}\n"
                        f"[bold]Language:[/bold] {language}\n"
                        f"[bold]Lines:[/bold] {line_count}\n"
                        f"[bold]Full ID:[/bold] {full_id}\n"
                        f"{imports_section}\n"
                        f"[bold]Content:[/bold]\n{highlighted_code}",
                        title=f"Code File: {doc_summary.filename}",
                        border_style="blue"
                    )
                )
            except Exception:
                # Fallback if syntax highlighting fails
                console.print(
                    Panel(
                        f"[bold blue]Filename:[/bold blue] {doc_summary.filename}\n"
                        f"[bold]Document ID:[/bold] {formatted_id}\n"
                        f"[bold]Language:[/bold] {language}\n"
                        f"[bold]Lines:[/bold] {line_count}\n"
                        f"[bold]Full ID:[/bold] {full_id}\n"
                        f"[bold]Content:[/bold]\n{doc_summary.content}",
                        title=f"Code File: {doc_summary.filename}",
                        border_style="blue"
                    )
                )
        else:
            # Regular document display
            console.print(
                Panel(
                    f"[bold blue]Filename:[/bold blue] {doc_summary.filename}\n"
                    f"[bold]Document ID:[/bold] {formatted_id}\n"
                    f"[bold]Full ID:[/bold] {full_id}\n"
                    f"[bold]Content:[/bold]\n{doc_summary.content}",
                    title="Document Summary",
                    border_style="blue"
                )
            )
            
    except Exception as e:
        console.print(f"[bold red]Error retrieving document: {str(e)}[/bold red]")
        logger.error(f"Error retrieving document: {str(e)}")

def list_summaries():
    """List all saved summaries."""
    try:
        # Get all markdown files in the summaries directory
        summary_files = list(config.SUMMARIES_DIR.glob("*.md"))
        
        if not summary_files:
            console.print("[bold yellow]No summary files found.[/bold yellow]")
            return
        
        # Sort files by modification time (newest first)
        summary_files.sort(key=lambda x: x.stat().st_mtime, reverse=True)
        
        table = Table(title="Saved Summaries", show_header=True, header_style="bold")
        table.add_column("Filename", style="dim")
        table.add_column("Date")
        table.add_column("Query")
        
        for file_path in summary_files:
            # Extract metadata from file
            with open(file_path, 'r') as f:
                content = f.read()
            
            # Parse metadata from frontmatter
            query = "Unknown"
            date = "Unknown"
            
            if content.startswith("---"):
                _, frontmatter, _ = content.split("---", 2)
                for line in frontmatter.strip().split("\n"):
                    if line.startswith("query:"):
                        query = line[6:].strip().strip('"')
                    elif line.startswith("date:"):
                        date = line[5:].strip()
            
            table.add_row(
                file_path.name,
                date,
                query[:50] + "..." if len(query) > 50 else query
            )
        
        console.print(table)
        console.print("[bold yellow]Tip: To view a summary, use 'view summary <filename>'[/bold yellow]")
        
    except Exception as e:
        console.print(f"[bold red]Error listing summaries: {str(e)}[/bold red]")
        logger.error(f"Error listing summaries: {str(e)}")

def view_summary(filename):
    """View a specific summary file."""
    try:
        # Check if filename includes path
        if "/" in filename or "\\" in filename:
            filepath = Path(filename)
        else:
            filepath = config.SUMMARIES_DIR / filename
        
        if not filepath.exists():
            console.print(f"[bold red]Summary file not found: {filepath}[/bold red]")
            return
        
        with open(filepath, 'r') as f:
            content = f.read()
        
        # Parse frontmatter
        if content.startswith("---"):
            _, frontmatter, markdown_content = content.split("---", 2)
        else:
            frontmatter = ""
            markdown_content = content
        
        # Extract metadata
        metadata = {}
        for line in frontmatter.strip().split("\n"):
            if ":" in line:
                key, value = line.split(":", 1)
                metadata[key.strip()] = value.strip().strip('"')
        
        # Display metadata and content
        metadata_text = "\n".join([f"[bold]{k}:[/bold] {v}" for k, v in metadata.items()])
        
        # Create the panel with markdown content
        panel_content = f"{metadata_text}\n\n"
        
        # Render the panel first
        console.print(
            Panel(
                panel_content,
                title=f"Summary: {filepath.name}",
                border_style="green",
                expand=False
            )
        )
        
        # Then render the markdown content separately
        console.print(Markdown(markdown_content.strip()))
        
    except Exception as e:
        console.print(f"[bold red]Error viewing summary: {str(e)}[/bold red]")
        logger.error(f"Error viewing summary: {str(e)}")

def main():
    """Main entry point for the CLI."""
    parser, args = parse_arguments()
    
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
    
    # Handle summary operations
    if args.list_summaries:
        display_header()
        list_summaries()
        return
        
    if args.view_summary:
        display_header()
        view_summary(args.view_summary)
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
        parser.print_help()

if __name__ == "__main__":
    main() 