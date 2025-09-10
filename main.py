#!/usr/bin/env python3
"""
Main entry point for the Glassdoor Job Scraper project
Author: TND0N
"""

import sys
import os

def print_menu():
    """Display the main menu options"""
    print("\n" + "="*50)
    print("       GLASSDOOR JOB SCRAPER")
    print("="*50)
    print("1. Run Job Scraper (Interactive)")
    print("2. Run Job Scraper (Quick Demo)")
    print("3. Clean and Analyze Existing Data")
    print("4. View Project Information")
    print("5. Exit")
    print("="*50)

def run_interactive_scraper():
    """Run the interactive job scraper"""
    try:
        import glassdoor_jobs
        glassdoor_jobs.main()
    except Exception as e:
        print(f"Error running interactive scraper: {e}")

def run_demo_scraper():
    """Run a quick demo scraper with predefined parameters"""
    try:
        from glassdoor_scraper_api import scrape_glassdoor_api
        print("Running demo scraper...")
        print("Searching for 'data analyst' jobs in Canada (first 2 pages)")
        results = scrape_glassdoor_api('data analyst', 'Canada', 2)
        print(f"Demo completed! Found {len(results)} job listings")
    except Exception as e:
        print(f"Error running demo scraper: {e}")

def run_data_cleaning():
    """Run the data cleaning and analysis script"""
    try:
        import glassdoor_data_cleaning
        glassdoor_data_cleaning.main()
    except Exception as e:
        print(f"Error running data cleaning: {e}")

def show_project_info():
    """Display project information"""
    print("\n" + "="*60)
    print("GLASSDOOR JOB SCRAPER - PROJECT INFORMATION")
    print("="*60)
    print("This project uses Selenium to scrape job listings from Glassdoor.")
    print("It extracts key job information including:")
    print("- Company names and details")
    print("- Job titles and descriptions")
    print("- Salary estimates")
    print("- Location information")
    print("- Company size, industry, and other details")
    print("")
    print("Files in this project:")
    print("- glassdoor_scraper_api.py: Core GraphQL API scraping functionality")
    print("- glassdoor_jobs.py: Interactive job scraper")
    print("- glassdoor_data_cleaning.py: Data cleaning and analysis")
    print("- main.py: This main menu system")
    print("")
    print("Features:")
    print("- Web scraping with dynamic page navigation")
    print("- Data extraction using XPath selectors")
    print("- CSV export functionality")
    print("- Data cleaning and preprocessing")
    print("- Skills and tools analysis")
    print("- Salary data processing")
    print("="*60)

def main():
    """Main function with menu system"""
    while True:
        print_menu()
        
        try:
            choice = input("\nEnter your choice (1-5): ").strip()
            
            if choice == '1':
                run_interactive_scraper()
            elif choice == '2':
                run_demo_scraper()
            elif choice == '3':
                run_data_cleaning()
            elif choice == '4':
                show_project_info()
            elif choice == '5':
                print("Thank you for using Glassdoor Job Scraper!")
                sys.exit(0)
            else:
                print("Invalid choice. Please enter a number between 1-5.")
                
        except KeyboardInterrupt:
            print("\n\nExiting...")
            sys.exit(0)
        except EOFError:
            print("\n\nExiting...")
            sys.exit(0)

if __name__ == "__main__":
    main()