#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Updated Glassdoor Job Scraper 2024 - API-Based Approach
Based on JobSpy's proven GraphQL API implementation
Author: TND0N

This scraper uses Glassdoor's internal GraphQL API instead of HTML scraping,
which is much more reliable and bypasses the compression issues we encountered.
"""

import re
import json
import time
import random
import requests
from typing import List, Dict, Tuple, Optional
from datetime import datetime, timedelta
import pandas as pd
import requests

class GlassdoorAPIScraper:
    """
    Modern Glassdoor API scraper using GraphQL endpoints
    Based on the successful JobSpy implementation
    """
    
    def __init__(self):
        self.base_url = "https://www.glassdoor.com"
        self.session: Optional[requests.Session] = None
        self.csrf_token: Optional[str] = None
        self.seen_urls = set()
        
        # Headers based on JobSpy's successful configuration
        self.headers = {
            "authority": "www.glassdoor.com",
            "accept": "*/*",
            "accept-language": "en-US,en;q=0.9",
            "apollographql-client-name": "job-search-next",
            "apollographql-client-version": "4.65.5",
            "content-type": "application/json",
            "origin": "https://www.glassdoor.com",
            "referer": "https://www.glassdoor.com/",
            "sec-ch-ua": '"Chromium";v="118", "Google Chrome";v="118", "Not=A?Brand";v="99"',
            "sec-ch-ua-mobile": "?0",
            "sec-ch-ua-platform": '"Windows"',
            "sec-fetch-dest": "empty",
            "sec-fetch-mode": "cors",
            "sec-fetch-site": "same-origin",
            "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36",
        }
        
        # Fallback CSRF token from JobSpy
        self.fallback_token = "Ft6oHEWlRZrxDww95Cpazw:0pGUrkb2y3TyOpAIqF2vbPmUXoXVkD3oEGDVkvfeCerceQ5-n8mBg3BovySUIjmCPHCaW0H2nQVdqzbtsYqf4Q:wcqRqeegRUa9MVLJGyujVXB7vWFPjdaS1CtrrzJq-ok"
        
        # GraphQL query template from JobSpy
        self.query_template = """
        query JobSearchResultsQuery(
            $excludeJobListingIds: [Long!],
            $keyword: String,
            $locationId: Int,
            $locationType: LocationTypeEnum,
            $numJobsToShow: Int!,
            $pageCursor: String,
            $pageNumber: Int,
            $filterParams: [FilterParams],
            $originalPageUrl: String,
            $seoFriendlyUrlInput: String,
            $parameterUrlInput: String,
            $seoUrl: Boolean
        ) {
            jobListings(
                contextHolder: {
                    searchParams: {
                        excludeJobListingIds: $excludeJobListingIds,
                        keyword: $keyword,
                        locationId: $locationId,
                        locationType: $locationType,
                        numPerPage: $numJobsToShow,
                        pageCursor: $pageCursor,
                        pageNumber: $pageNumber,
                        filterParams: $filterParams,
                        originalPageUrl: $originalPageUrl,
                        seoFriendlyUrlInput: $seoFriendlyUrlInput,
                        parameterUrlInput: $parameterUrlInput,
                        seoUrl: $seoUrl,
                        searchType: SR
                    }
                }
            ) {
                jobListings {
                    jobview {
                        header {
                            adOrderId
                            advertiserType
                            adOrderSponsorshipLevel
                            ageInDays
                            divisionEmployerName
                            easyApply
                            employer {
                                id
                                name
                                shortName
                                __typename
                            }
                            employerNameFromSearch
                            jobLink
                            jobResultTrackingKey
                            jobTitleText
                            locationName
                            locationType
                            locId
                            payPeriod
                            payPeriodAdjustedPay {
                                p10
                                p50
                                p90
                                __typename
                            }
                            payCurrency
                            rating
                            __typename
                        }
                        job {
                            description
                            listingId
                            jobTitleText
                            __typename
                        }
                        overview {
                            shortName
                            squareLogoUrl
                            __typename
                        }
                        __typename
                    }
                    __typename
                }
                paginationCursors {
                    cursor
                    pageNumber
                    __typename
                }
                totalJobsCount
                __typename
            }
        }
        """

    def initialize_session(self) -> None:
        """Initialize session and get CSRF token"""
        if self.session is None:
            self.session = requests.Session()
            self.session.headers.update(self.headers)
        
        # Get CSRF token
        try:
            response = self.session.get(f"{self.base_url}/Job/computer-science-jobs.htm")
            pattern = r'"token":\s*"([^"]+)"'
            matches = re.findall(pattern, response.text)
            if matches:
                self.csrf_token = matches[0]
                print(f"✅ Retrieved CSRF token: {self.csrf_token[:20]}...")
            else:
                self.csrf_token = self.fallback_token
                print(f"⚠️  Using fallback CSRF token")
        except Exception as e:
            print(f"⚠️  Error getting CSRF token, using fallback: {e}")
            self.csrf_token = self.fallback_token
        
        # Add CSRF token to headers
        self.session.headers["gd-csrf-token"] = self.csrf_token

    def get_location_id(self, location: str) -> Tuple[Optional[int], Optional[str]]:
        """Get location ID and type for API requests"""
        if not location:
            return 11047, "STATE"  # Default to remote/nationwide
            
        # Initialize session if not already done
        if not self.session:
            self.initialize_session()
            
        try:
            url = f"{self.base_url}/findPopularLocationAjax.htm"
            params = {"maxLocationsToReturn": 10, "term": location}
            response = self.session.get(url, params=params, timeout=10)
            
            if response.status_code != 200:
                print(f"⚠️  Location lookup failed with status {response.status_code}")
                return 11047, "STATE"
                
            locations = response.json()
            if not locations:
                print(f"⚠️  No locations found for '{location}', using default")
                return 11047, "STATE"
                
            location_data = locations[0]
            location_id = int(location_data["locationId"])
            location_type = location_data["locationType"]
            
            # Convert location type
            if location_type == "C":
                location_type = "CITY"
            elif location_type == "S":
                location_type = "STATE"  
            elif location_type == "N":
                location_type = "COUNTRY"
                
            print(f"✅ Found location: {location} -> ID {location_id}, Type {location_type}")
            return location_id, location_type
            
        except Exception as e:
            print(f"⚠️  Error in location lookup: {e}")
            return 11047, "STATE"

    def search_jobs(self, search_term: str, location: str = "", max_results: int = 100) -> List[Dict]:
        """
        Search for jobs using Glassdoor's GraphQL API
        """
        print(f"🔍 Searching Glassdoor API for: '{search_term}' in '{location}'")
        
        # Initialize session
        if not self.session:
            self.initialize_session()
            
        # Get location information
        location_id, location_type = self.get_location_id(location)
        if not location_id:
            print("❌ Could not resolve location")
            return []
            
        all_jobs = []
        page = 1
        cursor = None
        max_pages = min(30, (max_results // 30) + 2)
        
        while page <= max_pages and len(all_jobs) < max_results:
            print(f"📄 Fetching page {page}/{max_pages}")
            
            try:
                # Build GraphQL payload
                payload = [{
                    "operationName": "JobSearchResultsQuery",
                    "variables": {
                        "excludeJobListingIds": [],
                        "filterParams": [],
                        "keyword": search_term,
                        "numJobsToShow": 30,
                        "locationType": location_type,
                        "locationId": location_id,
                        "parameterUrlInput": f"IL.0,12_I{location_type}{location_id}",
                        "pageNumber": page,
                        "pageCursor": cursor,
                        "sort": "date",
                    },
                    "query": self.query_template,
                }]
                
                # Make API request
                response = self.session.post(
                    f"{self.base_url}/graph",
                    json=payload,
                    timeout=15
                )
                
                if response.status_code != 200:
                    print(f"❌ API request failed with status {response.status_code}")
                    break
                    
                data = response.json()
                if not data or "data" not in data[0]:
                    print("❌ No data in API response")
                    break
                    
                jobs_data = data[0]["data"]["jobListings"]["jobListings"]
                
                if not jobs_data:
                    print(f"✅ No more jobs found on page {page}")
                    break
                    
                # Process jobs from this page
                page_jobs = []
                processed_count = 0
                for i, job_data in enumerate(jobs_data):
                    processed_job = self.process_job(job_data)
                    if processed_job:
                        page_jobs.append(processed_job)
                        processed_count += 1
                        print(f"✅ Job {i+1}: {processed_job.get('title', 'N/A')} at {processed_job.get('company', 'N/A')}")
                    else:
                        print(f"❌ Job {i+1}: Failed to process (check logs above)")
                        
                all_jobs.extend(page_jobs)
                print(f"✅ Found {len(page_jobs)} jobs on page {page} (processed {processed_count}/{len(jobs_data)}, total: {len(all_jobs)})")
                
                # Get cursor for next page
                pagination_cursors = data[0]["data"]["jobListings"].get("paginationCursors", [])
                cursor = None
                for cursor_data in pagination_cursors:
                    if cursor_data["pageNumber"] == page + 1:
                        cursor = cursor_data["cursor"]
                        break
                        
                if not cursor:
                    print("✅ No more pages available")
                    break
                    
                page += 1
                time.sleep(random.uniform(1, 2))  # Respectful delay
                
            except Exception as e:
                print(f"❌ Error on page {page}: {e}")
                break
                
        print(f"🎯 Total jobs found: {len(all_jobs)}")
        return all_jobs[:max_results]

    def process_job(self, job_data: Dict) -> Optional[Dict]:
        """Process individual job data from API response"""
        try:
            if "jobview" not in job_data:
                print(f"❌ Missing jobview in job_data: {list(job_data.keys())}")
                return None
                
            jobview = job_data["jobview"]
            if "header" not in jobview or "job" not in jobview:
                print(f"❌ Missing header/job in jobview: {list(jobview.keys())}")
                return None
                
            header = jobview["header"]
            job_info = jobview["job"]
            
            # Basic job information
            job_id = job_info.get("listingId")
            if not job_id:
                print(f"❌ Missing listingId in job_info")
                return None
                
            job_url = f"{self.base_url}/job-listing/j?jl={job_id}"
            
            # Skip if we've seen this job before (comment out to debug)
            # if job_url in self.seen_urls:
            #     print(f"🔄 Skipping duplicate job: {job_url}")
            #     return None
            # self.seen_urls.add(job_url)
            
            # Extract job details
            title = job_info["jobTitleText"] or header.get("jobTitleText", "")
            company_name = header.get("employerNameFromSearch", "")
            location_name = header.get("locationName", "")
            age_in_days = header.get("ageInDays")
            
            # Calculate posting date
            date_posted = None
            if age_in_days is not None:
                date_posted = (datetime.now() - timedelta(days=age_in_days)).strftime("%Y-%m-%d")
            
            # Parse location
            city, state = "", ""
            if location_name and location_name != "Remote":
                parts = location_name.split(", ")
                city = parts[0] if len(parts) > 0 else ""
                state = parts[1] if len(parts) > 1 else ""
            
            # Parse salary information
            salary_min, salary_max, currency = None, None, "USD"
            pay_info = header.get("payPeriodAdjustedPay")
            if pay_info:
                salary_min = int(pay_info.get("p10", 0)) if pay_info.get("p10") else None
                salary_max = int(pay_info.get("p90", 0)) if pay_info.get("p90") else None
                currency = header.get("payCurrency", "USD")
            
            # Company information
            employer = header.get("employer", {})
            company_id = employer.get("id") if employer else None
            company_url = f"{self.base_url}/Overview/W-EI_IE{company_id}.htm" if company_id else None
            
            # Overview info
            overview = jobview.get("overview", {})
            company_logo = overview.get("squareLogoUrl")
            
            return {
                "id": f"glassdoor_{job_id}",
                "title": title,
                "company": company_name,
                "location": location_name,
                "city": city,
                "state": state,
                "job_url": job_url,
                "company_url": company_url,
                "company_logo": company_logo,
                "salary_min": salary_min,
                "salary_max": salary_max,
                "currency": currency,
                "date_posted": date_posted,
                "source": "glassdoor",
                "description": job_info.get("description", ""),
                "age_days": age_in_days,
                "easy_apply": header.get("easyApply", False),
                "remote": location_name == "Remote" or header.get("locationType") == "S"
            }
            
        except Exception as e:
            print(f"⚠️  Error processing job: {e}")
            return None

def scrape_glassdoor_api(search_term: str, location: str = "United States", max_results: int = 100) -> pd.DataFrame:
    """
    Main function to scrape Glassdoor using the API approach
    """
    scraper = GlassdoorAPIScraper()
    
    try:
        jobs = scraper.search_jobs(search_term, location, max_results)
        
        if not jobs:
            print("❌ No jobs found")
            return pd.DataFrame()
        
        df = pd.DataFrame(jobs)
        
        # Clean and organize data
        print(f"📊 Before deduplication: {len(df)} jobs")
        initial_count = len(df)
        df = df.drop_duplicates(subset=['job_url'], keep='first')
        print(f"📊 After deduplication: {len(df)} jobs (removed {initial_count - len(df)} duplicates)")
        df = df.sort_values('date_posted', ascending=False).reset_index(drop=True)
        
        print(f"✅ Successfully scraped {len(df)} unique jobs from Glassdoor API")
        return df
        
    except Exception as e:
        print(f"❌ Error in scraping: {e}")
        return pd.DataFrame()

# Test function
def test_api_scraper():
    """Test the API scraper with a simple search"""
    print("🧪 Testing Glassdoor API Scraper")
    df = scrape_glassdoor_api("data analyst", "San Francisco, CA", max_results=20)
    
    if not df.empty:
        print(f"✅ Test successful! Found {len(df)} jobs")
        print("\nSample results:")
        for idx, job in df.head(3).iterrows():
            print(f"  {idx+1}. {job['title']} at {job['company']} - {job['location']}")
    else:
        print("❌ Test failed - no jobs found")
    
    return df

if __name__ == "__main__":
    # Run test
    test_df = test_api_scraper()