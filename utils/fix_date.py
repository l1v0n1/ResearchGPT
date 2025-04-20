#!/usr/bin/env python3
"""
Utility script to check and fix the system date issues in the Research Agent.
"""
import os
import sys
import datetime
import subprocess
from pathlib import Path

def check_system_date():
    """Check if the system date is correct."""
    # Get the current system date
    system_date = datetime.datetime.now()
    
    print(f"Current system date: {system_date}")
    
    # Ask if the date is correct
    response = input("Is this date correct? (y/n): ").lower()
    
    if response == 'y':
        print("System date appears to be correct. No action needed.")
        return
    
    # If not correct, ask for the correct date
    print("\nPlease enter the correct date:")
    try:
        year = int(input("Year (YYYY): "))
        month = int(input("Month (MM): "))
        day = int(input("Day (DD): "))
        hour = int(input("Hour (24-hour format, HH): "))
        minute = int(input("Minute (MM): "))
        
        # Create the correct date
        correct_date = datetime.datetime(year, month, day, hour, minute)
        
        print(f"\nYou entered: {correct_date}")
        confirm = input("Is this correct? (y/n): ").lower()
        
        if confirm == 'y':
            # Try to set the system date (requires sudo/admin privileges)
            print("\nAttempting to set system date...")
            
            # Format for date command
            date_string = correct_date.strftime("%Y-%m-%d %H:%M:%S")
            
            if sys.platform == 'darwin' or sys.platform.startswith('linux'):
                # Mac or Linux
                print("This will require administrator privileges.")
                
                try:
                    # Using sudo date command for Unix-like systems
                    result = subprocess.run(['sudo', 'date', '-s', date_string], 
                                          capture_output=True, text=True)
                    
                    if result.returncode == 0:
                        print("System date successfully updated!")
                    else:
                        print(f"Failed to update system date: {result.stderr}")
                        print("\nManual instructions:")
                        print("1. Open a terminal")
                        print(f"2. Run: sudo date -s '{date_string}'")
                        
                except Exception as e:
                    print(f"Error executing command: {str(e)}")
                    print("\nAlternative: Please update your system date manually from system settings.")
            
            elif sys.platform == 'win32':
                # Windows
                print("This will require administrator privileges.")
                
                # Format for Windows date command
                date_str = correct_date.strftime("%m-%d-%Y")
                time_str = correct_date.strftime("%H:%M:%S")
                
                try:
                    # Set date and time separately on Windows
                    date_result = subprocess.run(['date', date_str], 
                                               capture_output=True, text=True, shell=True)
                    time_result = subprocess.run(['time', time_str], 
                                               capture_output=True, text=True, shell=True)
                    
                    if date_result.returncode == 0 and time_result.returncode == 0:
                        print("System date successfully updated!")
                    else:
                        print("Failed to update system date.")
                        print("\nManual instructions:")
                        print("1. Open Command Prompt as Administrator")
                        print(f"2. Run: date {date_str}")
                        print(f"3. Run: time {time_str}")
                        
                except Exception as e:
                    print(f"Error executing command: {str(e)}")
                    print("\nAlternative: Please update your system date manually from system settings.")
            
            else:
                print("Unsupported operating system. Please update your system date manually.")
                
        else:
            print("Operation cancelled.")
    
    except ValueError:
        print("Invalid date format. Please run the script again with correct values.")

if __name__ == "__main__":
    print("===== System Date Check and Fix Utility =====")
    check_system_date() 