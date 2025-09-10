#!/usr/bin/env python3
"""
Google Sheets Integration for Glassdoor Job Scraper
Handles saving job data to Google Sheets instead of CSV files
"""

import gspread
from google.oauth2.service_account import Credentials
import pandas as pd
import json
import os
from datetime import datetime

class GoogleSheetsHandler:
    def __init__(self, credentials_file=None):
        """
        Initialize Google Sheets handler with service account credentials
        """
        self.credentials_file = credentials_file
        self.client = None
        self._authenticate()
    
    def _authenticate(self):
        """
        Authenticate with Google Sheets API using service account
        """
        try:
            # Define the scope
            scopes = [
                'https://www.googleapis.com/auth/spreadsheets',
                'https://www.googleapis.com/auth/drive'
            ]
            
            # Try to load from environment variable first
            credentials_json = os.environ.get('GOOGLE_SHEETS_CREDENTIALS')
            if credentials_json:
                try:
                    # Clean up credentials JSON - handle various formats
                    credentials_json = credentials_json.strip()
                    
                    # Remove any outer quotes that might have been added
                    while credentials_json.startswith('"') and credentials_json.endswith('"'):
                        credentials_json = credentials_json[1:-1]
                    
                    # Handle escaped quotes
                    credentials_json = credentials_json.replace('\\"', '"')
                    
                    # If it doesn't start with { but we see JSON-like content, try to find it
                    if not credentials_json.startswith('{'):
                        # Look for JSON content starting with {
                        start_idx = credentials_json.find('{')
                        if start_idx > 0:
                            credentials_json = credentials_json[start_idx:]
                        elif credentials_json.startswith('"type":'):
                            # Missing opening brace - add it
                            credentials_json = '{' + credentials_json
                    
                    # Ensure it ends properly - find the last complete }
                    if not credentials_json.endswith('}'):
                        # Find the last } and truncate there
                        last_brace = credentials_json.rfind('}')
                        if last_brace > 0:
                            credentials_json = credentials_json[:last_brace + 1]
                    
                    # Remove any trailing comma before }
                    credentials_json = credentials_json.replace(',}', '}').replace(', }', '}')
                    
                    # Try to parse as JSON
                    credentials_dict = json.loads(credentials_json)
                    
                    # Validate it's a proper service account key
                    required_fields = ['type', 'project_id', 'private_key_id', 'private_key', 'client_email']
                    if not all(field in credentials_dict for field in required_fields):
                        raise ValueError("Invalid service account credentials format")
                    
                    creds = Credentials.from_service_account_info(credentials_dict, scopes=scopes)
                    self.client = gspread.authorize(creds)
                    print("✅ Google Sheets authentication successful (from environment)")
                    return
                    
                except (json.JSONDecodeError, ValueError) as parse_error:
                    print(f"❌ Failed to parse Google Sheets credentials: {parse_error}")
                    print(f"📝 Credentials first 100 chars: {credentials_json[:100]}...")
                    print(f"📝 Credentials last 100 chars: {credentials_json[-100:]}")
                    # Fall through to file-based credentials instead of raising
                    pass
            
            # Fallback to credentials file if environment variable not found
            if self.credentials_file and os.path.exists(self.credentials_file):
                creds = Credentials.from_service_account_file(
                    self.credentials_file, 
                    scopes=scopes
                )
                self.client = gspread.authorize(creds)
                print("✅ Google Sheets authentication successful (from file)")
            else:
                raise FileNotFoundError("No Google Sheets credentials found in environment or file")
                
        except Exception as e:
            print(f"❌ Google Sheets authentication failed: {e}")
            raise
    
    def create_new_sheet(self, title, folder_id=None):
        """
        Create a new Google Sheet
        """
        try:
            if folder_id:
                # Create in specific folder
                sheet = self.client.create(title, folder_id=folder_id)
            else:
                # Create in root
                sheet = self.client.create(title)
            
            print(f"✅ Created new sheet: {title}")
            print(f"📋 Sheet ID: {sheet.id}")
            print(f"🔗 Sheet URL: https://docs.google.com/spreadsheets/d/{sheet.id}")
            
            return sheet
            
        except Exception as e:
            print(f"❌ Failed to create sheet: {e}")
            raise
    
    def open_sheet_by_id(self, sheet_id):
        """
        Open an existing Google Sheet by ID
        """
        try:
            sheet = self.client.open_by_key(sheet_id)
            print(f"✅ Opened sheet: {sheet.title}")
            return sheet
        except Exception as e:
            print(f"❌ Failed to open sheet with ID {sheet_id}: {e}")
            raise
    
    def save_jobs_to_sheet(self, dataframe, sheet_id, worksheet_name=None):
        """
        Save job data DataFrame to Google Sheet
        """
        try:
            # Clean DataFrame for Google Sheets compatibility
            import numpy as np
            df = dataframe.copy()
            
            # Replace NaN and infinite values  
            df = df.replace([np.inf, -np.inf], None)
            df = df.fillna('')
            
            # Convert any remaining problematic numeric columns to strings
            for col in df.columns:
                if df[col].dtype in ['float64', 'int64']:
                    df[col] = df[col].astype(str).replace('nan', '').replace('None', '')
            
            # Open the sheet
            sheet = self.open_sheet_by_id(sheet_id)
            
            # Create worksheet name with timestamp if not provided
            if not worksheet_name:
                timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
                worksheet_name = f"Jobs {timestamp}"
            
            # Try to select existing worksheet or create new one
            try:
                worksheet = sheet.worksheet(worksheet_name)
                print(f"📝 Using existing worksheet: {worksheet_name}")
            except gspread.WorksheetNotFound:
                worksheet = sheet.add_worksheet(
                    title=worksheet_name, 
                    rows=len(df) + 10, 
                    cols=len(df.columns)
                )
                print(f"📝 Created new worksheet: {worksheet_name}")
            
            # Clear existing data
            worksheet.clear()
            
            # Convert DataFrame to list of lists for gspread
            data_to_upload = [df.columns.tolist()] + df.values.tolist()
            
            # Upload data to sheet
            worksheet.update('A1', data_to_upload, value_input_option='RAW')
            
            # Format headers
            header_format = {
                "backgroundColor": {"red": 0.2, "green": 0.6, "blue": 0.9},
                "textFormat": {"bold": True, "foregroundColor": {"red": 1, "green": 1, "blue": 1}}
            }
            
            worksheet.format('A1:Z1', header_format)
            
            print(f"✅ Successfully saved {len(df)} jobs to Google Sheet")
            print(f"📊 Worksheet: {worksheet_name}")
            print(f"🔗 Direct link: https://docs.google.com/spreadsheets/d/{sheet_id}")
            
            return {
                'sheet_id': sheet_id,
                'worksheet_name': worksheet_name,
                'job_count': len(df),
                'url': f"https://docs.google.com/spreadsheets/d/{sheet_id}"
            }
            
        except Exception as e:
            print(f"❌ Failed to save data to Google Sheet: {e}")
            raise
    
    def get_sheet_info(self, sheet_id):
        """
        Get information about a Google Sheet
        """
        try:
            sheet = self.open_sheet_by_id(sheet_id)
            worksheets = sheet.worksheets()
            
            info = {
                'title': sheet.title,
                'id': sheet.id,
                'url': f"https://docs.google.com/spreadsheets/d/{sheet.id}",
                'worksheets': [{'title': ws.title, 'rows': ws.row_count, 'cols': ws.col_count} for ws in worksheets]
            }
            
            return info
            
        except Exception as e:
            print(f"❌ Failed to get sheet info: {e}")
            raise
    
    def validate_sheet_access(self, sheet_id):
        """
        Validate that we can access the sheet
        """
        try:
            sheet = self.open_sheet_by_id(sheet_id)
            # Try to read first cell to test access
            worksheet = sheet.sheet1
            worksheet.acell('A1')
            return True, f"✅ Access confirmed for sheet: {sheet.title}"
        except Exception as e:
            return False, f"❌ Cannot access sheet: {e}"

def test_sheets_integration():
    """
    Test the Google Sheets integration
    """
    print("🧪 Testing Google Sheets Integration...")
    
    try:
        # Initialize handler
        sheets = GoogleSheetsHandler()
        
        # Create test data
        test_data = pd.DataFrame({
            'Company': ['Google', 'Microsoft', 'Amazon'],
            'Job Title': ['Software Engineer', 'Data Scientist', 'Product Manager'],
            'Location': ['San Francisco', 'Seattle', 'New York'],
            'Salary': ['$150K-$200K', '$120K-$180K', '$130K-$190K']
        })
        
        # Test creating a new sheet
        test_sheet = sheets.create_new_sheet("Test Glassdoor Jobs")
        
        # Test saving data
        result = sheets.save_jobs_to_sheet(test_data, test_sheet.id, "Test Data")
        
        print("🎉 Google Sheets integration test successful!")
        return result
        
    except Exception as e:
        print(f"❌ Google Sheets integration test failed: {e}")
        return None

if __name__ == "__main__":
    test_sheets_integration()