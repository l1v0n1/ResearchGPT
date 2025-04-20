#!/usr/bin/env python3
"""
Script to fix the date issue in the AI Research Assistant.

This script sets the date offset to correct the time discrepancy where 
the system shows 2025-04-20 but it should actually be 2024-04-26.
"""
import os
import sys

# Add the project root to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from agent.logger import set_global_date_offset

def main():
    print("==== AI Research Assistant Date Fix ====")
    print("The logs currently show dates from 2025-04-20,")
    print("but the research mentions April 26, 2024.")
    
    # Calculate the difference:
    # If system shows 2025-04-20 and correct date is 2024-04-26
    # Year diff: 1, Month diff: 0, Day diff: -6 (26-20)
    corrected_date = set_global_date_offset(year_diff=1, month_diff=0, day_diff=-6)
    
    print("\nDate correction applied!")
    print(f"All future operations will use corrected date: {corrected_date.strftime('%Y-%m-%d')}")
    print("\nRun your application now with:")
    print("  python -m app.cli -i")

if __name__ == "__main__":
    main() 