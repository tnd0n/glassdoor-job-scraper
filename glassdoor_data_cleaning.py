#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Data cleaning and analysis script for Glassdoor job data
"""

import pandas as pd
import numpy as np
import os

def clean_salary_data(jobs):
    """Clean and process salary estimate data"""
    # Remove duplicates based on job description
    jobs = jobs.drop_duplicates(subset='job_description', keep='first')
    
    # Filter jobs with salary information
    jobs = jobs[jobs['salary_estimate'] != 'N/A']
    jobs = jobs[jobs['salary_estimate'].notna()]
    
    # Create hourly and employer estimate indicators
    jobs['per_hour'] = jobs['salary_estimate'].apply(lambda x: 1 if 'per hour' in str(x).lower() else 0)
    jobs['employer_est'] = jobs['salary_estimate'].apply(lambda x: 1 if 'employer est.' in str(x).lower() else 0)
    
    # Clean salary strings
    salaries = jobs['salary_estimate'].apply(lambda x: str(x).lower()
                                           .replace('ca$', '')
                                           .replace('$', '')
                                           .replace('k', '')
                                           .replace('per hour', '')
                                           .replace('(glassdoor est.)', '')
                                           .replace('(employer est.)', '')
                                           .strip())
    
    try:
        # Extract min and max wages
        jobs['min_wage'] = salaries.apply(lambda x: float(x.split('-')[0]) if '-' in x else float(x))
        jobs['max_wage'] = salaries.apply(lambda x: float(x.split('-')[-1]) if '-' in x else float(x))
        
        # Convert hourly to annual (assuming 2080 hours per year)
        jobs['min_wage'] = jobs.apply(lambda x: round(x.min_wage * 2080) if x.per_hour == 1 else x.min_wage, axis=1)
        jobs['max_wage'] = jobs.apply(lambda x: round(x.max_wage * 2080) if x.per_hour == 1 else x.max_wage, axis=1)
        
        # Calculate average salary
        jobs['average_salary'] = round((jobs.min_wage + jobs.max_wage) / 2)
        
    except (ValueError, AttributeError) as e:
        print(f"Warning: Error processing salary data: {e}")
        jobs['min_wage'] = np.nan
        jobs['max_wage'] = np.nan
        jobs['average_salary'] = np.nan
    
    return jobs

def clean_company_data(jobs):
    """Clean and process company-related data"""
    # Extract ratings from company names
    jobs['ratings'] = jobs['company'].apply(lambda x: x[-3:] if any(chr.isdigit() for chr in str(x)) else '')
    jobs['company'] = jobs['company'].apply(lambda x: x[:-3].strip() if any(chr.isdigit() for chr in str(x)) else str(x).strip())
    
    # Calculate company age
    try:
        jobs['company_founded'] = pd.to_numeric(jobs['company_founded'], errors='coerce')
        jobs['company_age'] = jobs['company_founded'].apply(lambda x: 2024 - x if pd.notna(x) and x > 1800 else np.nan)
    except:
        jobs['company_age'] = np.nan
    
    return jobs

def extract_job_features(jobs):
    """Extract additional features from job data"""
    
    def title_simplifier(title):
        """Simplify job titles into categories"""
        title = str(title).lower()
        if 'business analyst' in title:
            return 'business analyst'
        elif 'analyst' in title and 'business analyst' not in title:
            return 'analyst'
        elif 'scientist' in title:
            return 'scientist'
        elif 'engineer' in title:
            return 'engineer'
        elif 'manager' in title:
            return 'manager'
        else:
            return 'other'

    def seniority_level(title):
        """Determine seniority level from job title"""
        title = str(title).lower()
        if any(word in title for word in ['senior', 'sr', 'lead', 'principal']):
            return 'senior'
        elif any(word in title for word in ['junior', 'jr', 'entry', 'intern']):
            return 'junior'
        elif 'manager' in title:
            return 'manager'
        elif any(word in title for word in ['expert', 'specialist']):
            return 'expert'
        else:
            return 'mid-level'

    def work_environment(description):
        """Determine work environment from job description"""
        description = str(description).lower()
        if 'remote' in description:
            return 'remote'
        elif 'hybrid' in description:
            return 'hybrid'
        elif any(phrase in description for phrase in ['on site', 'on-site', 'onsite']):
            return 'on-site'
        else:
            return 'not specified'

    # Apply feature extraction functions
    jobs['simple_title'] = jobs['job_title'].apply(title_simplifier)
    jobs['seniority'] = jobs['job_title'].apply(seniority_level)
    jobs['work_environment'] = jobs['job_description'].apply(work_environment)
    
    return jobs

def analyze_tools_and_skills(jobs, keywords=None):
    """Analyze tools and skills mentioned in job descriptions"""
    if keywords is None:
        keywords = ['excel', 'python', 'r-studio', 'r studio', 'jupyter', 'spark', 'sql', 
                   'qlikview', 'power bi', 'tableau', 'knime', 'sas', 'matlab', 'java',
                   'javascript', 'aws', 'azure', 'docker', 'kubernetes']
    
    tools_data = {}
    for keyword in keywords:
        jobs[keyword] = jobs['job_description'].apply(lambda x: 1 if keyword.lower() in str(x).lower() else 0)
        tools_data[keyword] = jobs[keyword].sum()
    
    # Create tools summary DataFrame
    tools_df = pd.DataFrame(list(tools_data.items()), columns=['Tool', 'Count'])
    tools_df = tools_df.sort_values('Count', ascending=False)
    
    return jobs, tools_df

def main():
    """Main function to clean and analyze job data"""
    print("=== Glassdoor Data Cleaning and Analysis ===")
    
    # Look for CSV files in the current directory
    csv_files = [f for f in os.listdir('.') if f.endswith('.csv') and 'jobs' in f]
    
    if not csv_files:
        print("No job data CSV files found. Please run the scraper first.")
        return
    
    print(f"Found CSV files: {csv_files}")
    
    for csv_file in csv_files:
        print(f"\nProcessing {csv_file}...")
        
        try:
            # Load the data
            jobs = pd.read_csv(csv_file)
            print(f"Loaded {len(jobs)} job records")
            
            # Clean the data
            jobs = clean_salary_data(jobs)
            print(f"After cleaning: {len(jobs)} job records with salary data")
            
            jobs = clean_company_data(jobs)
            jobs = extract_job_features(jobs)
            
            # Analyze tools and skills
            jobs, tools_df = analyze_tools_and_skills(jobs)
            
            # Generate summary statistics
            print("\n=== Summary Statistics ===")
            if 'average_salary' in jobs.columns and jobs['average_salary'].notna().any():
                print(f"Average salary: ${jobs['average_salary'].mean():,.0f}")
                print(f"Median salary: ${jobs['average_salary'].median():,.0f}")
                print(f"Salary range: ${jobs['average_salary'].min():,.0f} - ${jobs['average_salary'].max():,.0f}")
            
            print(f"\nTop job titles:")
            print(jobs['simple_title'].value_counts().head())
            
            print(f"\nSeniority levels:")
            print(jobs['seniority'].value_counts())
            
            print(f"\nWork environments:")
            print(jobs['work_environment'].value_counts())
            
            print(f"\nTop companies:")
            print(jobs['company'].value_counts().head())
            
            print(f"\nTop skills/tools:")
            print(tools_df.head(10))
            
            # Save cleaned data
            base_name = csv_file.replace('.csv', '')
            cleaned_filename = f"{base_name}_cleaned.csv"
            tools_filename = f"{base_name}_tools_analysis.csv"
            
            jobs.to_csv(cleaned_filename, index=False)
            tools_df.to_csv(tools_filename, index=False)
            
            print(f"\nCleaned data saved to: {cleaned_filename}")
            print(f"Tools analysis saved to: {tools_filename}")
            
        except Exception as e:
            print(f"Error processing {csv_file}: {str(e)}")
            continue

if __name__ == "__main__":
    main()