"""
Benchmarking script for the AI Research Agent.
"""
import os
import sys
import time
import argparse
from typing import Dict, List, Any, Optional, Tuple
from pathlib import Path

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agent.model import ModelAPIWrapper
from agent.planner import Planner
from agent.executor import Executor
from agent.logger import AgentLogger

logger = AgentLogger(__name__)

class Benchmark:
    """
    A benchmark utility for the AI Research Agent.
    """
    
    def __init__(self):
        """Initialize the benchmark."""
        # Initialize components
        self.model = ModelAPIWrapper()
        self.planner = Planner()
        self.executor = Executor()
    
    def run_model_benchmark(self, iterations: int = 5) -> Dict[str, Any]:
        """
        Benchmark the model API wrapper.
        
        Args:
            iterations: Number of iterations to run
            
        Returns:
            Dictionary with benchmark results
        """
        print(f"Running model benchmark with {iterations} iterations...")
        
        test_prompt = "Explain the concept of artificial intelligence in one paragraph."
        
        # Measure generation time
        gen_times = []
        token_counts = []
        
        for i in range(iterations):
            start_time = time.time()
            
            # Generate text
            response = self.model.generate_text(test_prompt, temperature=0.7)
            
            elapsed = time.time() - start_time
            gen_times.append(elapsed)
            
            # Approximate token count (very rough)
            token_count = len(response.split()) * 1.3
            token_counts.append(token_count)
            
            print(f"  Iteration {i+1}: {elapsed:.2f}s, ~{int(token_count)} tokens")
            
            # Add a small delay between requests
            time.sleep(0.5)
        
        results = {
            "avg_generation_time": sum(gen_times) / len(gen_times),
            "min_generation_time": min(gen_times),
            "max_generation_time": max(gen_times),
            "avg_token_count": sum(token_counts) / len(token_counts),
            "total_iterations": iterations
        }
        
        return results
    
    def run_planning_benchmark(self, queries: List[str]) -> Dict[str, Any]:
        """
        Benchmark the planning component.
        
        Args:
            queries: List of test queries
            
        Returns:
            Dictionary with benchmark results
        """
        print(f"Running planning benchmark with {len(queries)} queries...")
        
        plan_times = []
        step_counts = []
        
        for i, query in enumerate(queries):
            print(f"  Query {i+1}: {query}")
            
            # Measure planning time
            start_time = time.time()
            
            # Generate plan
            plan = self.planner.create_plan(query)
            
            elapsed = time.time() - start_time
            plan_times.append(elapsed)
            
            if plan:
                step_counts.append(len(plan.steps))
                print(f"    {len(plan.steps)} steps planned in {elapsed:.2f}s")
            else:
                print("    Planning failed")
            
            # Add a delay between requests
            time.sleep(1)
        
        results = {
            "avg_planning_time": sum(plan_times) / len(plan_times) if plan_times else 0,
            "avg_step_count": sum(step_counts) / len(step_counts) if step_counts else 0,
            "min_planning_time": min(plan_times) if plan_times else 0,
            "max_planning_time": max(plan_times) if plan_times else 0,
            "total_queries": len(queries),
            "successful_plans": len(step_counts)
        }
        
        return results
    
    def run_execution_benchmark(self, queries: List[str], dry_run: bool = True) -> Dict[str, Any]:
        """
        Benchmark the execution component.
        
        Args:
            queries: List of test queries
            dry_run: Whether to perform a dry run (no actual execution)
            
        Returns:
            Dictionary with benchmark results
        """
        print(f"Running {'dry-run ' if dry_run else ''}execution benchmark with {len(queries)} queries...")
        
        plan_times = []
        execution_times = []
        total_times = []
        step_counts = []
        
        for i, query in enumerate(queries):
            print(f"  Query {i+1}: {query}")
            total_start_time = time.time()
            
            # Generate plan
            plan_start_time = time.time()
            plan = self.planner.create_plan(query)
            plan_time = time.time() - plan_start_time
            plan_times.append(plan_time)
            
            if not plan:
                print("    Planning failed")
                continue
                
            step_counts.append(len(plan.steps))
            print(f"    {len(plan.steps)} steps planned in {plan_time:.2f}s")
            
            # Execute plan
            execution_start_time = time.time()
            summary, _ = self.executor.execute_plan(plan, dry_run=dry_run)
            execution_time = time.time() - execution_start_time
            execution_times.append(execution_time)
            
            total_time = time.time() - total_start_time
            total_times.append(total_time)
            
            print(f"    Execution: {execution_time:.2f}s, Summary: {len(summary)} chars")
            print(f"    Total time: {total_time:.2f}s")
            
            # Add a delay between queries
            time.sleep(2)
        
        results = {
            "avg_planning_time": sum(plan_times) / len(plan_times) if plan_times else 0,
            "avg_execution_time": sum(execution_times) / len(execution_times) if execution_times else 0,
            "avg_total_time": sum(total_times) / len(total_times) if total_times else 0,
            "avg_step_count": sum(step_counts) / len(step_counts) if step_counts else 0,
            "max_total_time": max(total_times) if total_times else 0,
            "min_total_time": min(total_times) if total_times else 0,
            "total_queries": len(queries),
            "successful_executions": len(execution_times),
            "dry_run": dry_run
        }
        
        return results
    
    def run_all_benchmarks(self, dry_run: bool = True) -> Dict[str, Any]:
        """
        Run all benchmarks.
        
        Args:
            dry_run: Whether to perform a dry run for execution
            
        Returns:
            Dictionary with all benchmark results
        """
        print("Running all benchmarks...")
        
        # Define test queries
        test_queries = [
            "What are the latest advancements in quantum computing?",
            "Explain the differences between supervised and unsupervised learning in AI.",
            "What are the environmental impacts of renewable energy sources?",
            "How do mRNA vaccines work?",
            "What are the main challenges in implementing smart city technologies?"
        ]
        
        # Run benchmarks
        model_results = self.run_model_benchmark(iterations=3)
        planning_results = self.run_planning_benchmark(queries=test_queries)
        execution_results = self.run_execution_benchmark(
            queries=test_queries[:2],  # Use fewer queries for execution benchmark
            dry_run=dry_run
        )
        
        # Combine results
        all_results = {
            "model": model_results,
            "planning": planning_results,
            "execution": execution_results,
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "dry_run": dry_run
        }
        
        return all_results
    
    def print_results(self, results: Dict[str, Any]) -> None:
        """
        Print benchmark results.
        
        Args:
            results: Dictionary with benchmark results
        """
        print("\n===== BENCHMARK RESULTS =====")
        
        # Print model results
        if "model" in results:
            m = results["model"]
            print("\nModel Benchmark:")
            print(f"  Avg Generation Time: {m['avg_generation_time']:.2f}s")
            print(f"  Min Generation Time: {m['min_generation_time']:.2f}s")
            print(f"  Max Generation Time: {m['max_generation_time']:.2f}s")
            print(f"  Avg Token Count: {m['avg_token_count']:.1f}")
            print(f"  Total Iterations: {m['total_iterations']}")
        
        # Print planning results
        if "planning" in results:
            p = results["planning"]
            print("\nPlanning Benchmark:")
            print(f"  Avg Planning Time: {p['avg_planning_time']:.2f}s")
            print(f"  Min Planning Time: {p['min_planning_time']:.2f}s")
            print(f"  Max Planning Time: {p['max_planning_time']:.2f}s")
            print(f"  Avg Step Count: {p['avg_step_count']:.1f}")
            print(f"  Successful Plans: {p['successful_plans']}/{p['total_queries']}")
        
        # Print execution results
        if "execution" in results:
            e = results["execution"]
            print("\nExecution Benchmark:")
            print(f"  Dry Run: {e['dry_run']}")
            print(f"  Avg Planning Time: {e['avg_planning_time']:.2f}s")
            print(f"  Avg Execution Time: {e['avg_execution_time']:.2f}s")
            print(f"  Avg Total Time: {e['avg_total_time']:.2f}s")
            print(f"  Min Total Time: {e['min_total_time']:.2f}s")
            print(f"  Max Total Time: {e['max_total_time']:.2f}s")
            print(f"  Avg Step Count: {e['avg_step_count']:.1f}")
            print(f"  Successful Executions: {e['successful_executions']}/{e['total_queries']}")
        
        print("\n==============================")

def parse_arguments():
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(description="AI Research Agent Benchmark")
    
    parser.add_argument(
        "--model-only",
        action="store_true",
        help="Run only the model benchmark"
    )
    
    parser.add_argument(
        "--planning-only",
        action="store_true",
        help="Run only the planning benchmark"
    )
    
    parser.add_argument(
        "--execution-only",
        action="store_true",
        help="Run only the execution benchmark"
    )
    
    parser.add_argument(
        "--full-execution",
        action="store_true",
        help="Run execution benchmark with actual tool calls (not dry run)"
    )
    
    parser.add_argument(
        "--iterations",
        type=int,
        default=3,
        help="Number of iterations for model benchmark"
    )
    
    parser.add_argument(
        "--save",
        action="store_true",
        help="Save benchmark results to file"
    )
    
    return parser.parse_args()

def main():
    """Main entry point."""
    args = parse_arguments()
    benchmark = Benchmark()
    
    results = {}
    
    # Run specific benchmarks based on arguments
    if args.model_only:
        results["model"] = benchmark.run_model_benchmark(iterations=args.iterations)
    elif args.planning_only:
        test_queries = [
            "What are the latest advancements in quantum computing?",
            "Explain the differences between supervised and unsupervised learning in AI.",
            "What are the environmental impacts of renewable energy sources?",
            "How do mRNA vaccines work?",
            "What are the main challenges in implementing smart city technologies?"
        ]
        results["planning"] = benchmark.run_planning_benchmark(queries=test_queries)
    elif args.execution_only:
        test_queries = [
            "What are the latest advancements in quantum computing?",
            "Explain the differences between supervised and unsupervised learning in AI."
        ]
        results["execution"] = benchmark.run_execution_benchmark(
            queries=test_queries,
            dry_run=not args.full_execution
        )
    else:
        # Run all benchmarks
        results = benchmark.run_all_benchmarks(dry_run=not args.full_execution)
    
    # Print results
    benchmark.print_results(results)
    
    # Save results if requested
    if args.save:
        import json
        output_file = f"benchmark_results_{int(time.time())}.json"
        with open(output_file, "w") as f:
            json.dump(results, f, indent=2)
        print(f"\nResults saved to {output_file}")

if __name__ == "__main__":
    main() 