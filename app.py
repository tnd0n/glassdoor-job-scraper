#!/usr/bin/env python3
"""
Flask Web Application for Glassdoor Job Scraper
Author: TND0N
"""

from flask import Flask, render_template, request, jsonify, send_file, redirect, url_for
import glassdoor_data_cleaning as gdc
from glassdoor_scraper_api import scrape_glassdoor_api
import pandas as pd
import os
import threading
import time
from datetime import datetime
import json
import gspread
from google.oauth2.service_account import Credentials

app = Flask(__name__)
app.secret_key = os.environ.get('SESSION_SECRET', 'glassdoor-scraper-key-fallback')

# Google Sheets helper functions
def get_google_sheets_client():
    """Initialize Google Sheets client with credentials from environment"""
    try:
        credentials_json = os.environ.get('GOOGLE_SHEETS_CREDENTIALS')
        if not credentials_json:
            return None
        
        credentials_dict = json.loads(credentials_json)
        scope = ['https://www.googleapis.com/auth/spreadsheets', 'https://www.googleapis.com/auth/drive']
        credentials = Credentials.from_service_account_info(credentials_dict, scopes=scope)
        return gspread.authorize(credentials)
    except Exception as e:
        print(f"Error initializing Google Sheets client: {e}")
        return None

def get_sheets_data(spreadsheet_id, sheet_name=None):
    """Fetch data from Google Sheets and return as pandas DataFrame"""
    try:
        client = get_google_sheets_client()
        if not client:
            return None, "Google Sheets client not available"
        
        spreadsheet = client.open_by_key(spreadsheet_id)
        
        if sheet_name:
            worksheet = spreadsheet.worksheet(sheet_name)
        else:
            worksheet = spreadsheet.get_worksheet(0)  # Get first sheet
        
        data = worksheet.get_all_records()
        df = pd.DataFrame(data)
        
        return df, None
    except Exception as e:
        return None, f"Error reading Google Sheets: {str(e)}"

def save_to_google_sheets(df, spreadsheet_id, sheet_name="Analytics Data"):
    """Save DataFrame to Google Sheets"""
    try:
        client = get_google_sheets_client()
        if not client:
            return False, "Google Sheets client not available"
        
        spreadsheet = client.open_by_key(spreadsheet_id)
        
        try:
            worksheet = spreadsheet.worksheet(sheet_name)
            worksheet.clear()
        except:
            worksheet = spreadsheet.add_worksheet(title=sheet_name, rows=len(df)+1, cols=len(df.columns))
        
        # Convert DataFrame to list of lists
        data = [df.columns.tolist()] + df.values.tolist()
        worksheet.update('A1', data)
        
        return True, f"Data saved to '{sheet_name}' in Google Sheets"
    except Exception as e:
        return False, f"Error saving to Google Sheets: {str(e)}"

# Global variables to track scraping progress
scraping_progress = {
    'status': 'idle',
    'current_page': 0,
    'total_pages': 0,
    'message': 'Ready to start scraping',
    'filename': '',
    'job_count': 0
}

@app.route('/')
def index():
    """Home page with scraping form"""
    return render_template('index.html')

@app.route('/start_scraping', methods=['POST'])
def start_scraping():
    """Start the scraping process in a background thread"""
    global scraping_progress
    
    if scraping_progress['status'] == 'running':
        return jsonify({'error': 'Scraping is already in progress'})
    
    # Get form data
    keyword = request.form.get('keyword', 'data analyst').strip()
    location = request.form.get('location', 'Canada').strip()
    num_pages = int(request.form.get('num_pages', 2))
    sheet_id = request.form.get('sheet_id', '1iibXYJ5ZSFZzFIKUyM8d4u3x87FOereMESBfuFW7ZYI').strip()
    use_google_sheets = bool(sheet_id)  # Always try Google Sheets if sheet ID is provided
    
    # Validate sheet ID format if provided
    if use_google_sheets and sheet_id:
        if not sheet_id or len(sheet_id) < 20:
            return jsonify({'error': 'Invalid Google Sheet ID. Please provide a valid Sheet ID.'})
    
    # Test Google Sheets access early if requested
    if use_google_sheets:
        try:
            from google_sheets_integration import GoogleSheetsHandler
            sheets_handler = GoogleSheetsHandler()
            access_valid, access_message = sheets_handler.validate_sheet_access(sheet_id)
            if not access_valid:
                return jsonify({'error': f'Cannot access Google Sheet: {access_message}. Please check the Sheet ID and sharing permissions.'})
        except Exception as validation_error:
            return jsonify({'error': f'Google Sheets validation failed: {str(validation_error)}'})
    
    if num_pages > 10:
        num_pages = 10  # Limit to prevent excessive scraping
    
    # Reset progress
    scraping_progress = {
        'status': 'running',
        'current_page': 0,
        'total_pages': num_pages,
        'message': f'🎯 Initializing job search • Target: "{keyword}" in {location}',
        'filename': '',
        'job_count': 0,
        'start_time': datetime.now().isoformat(),
        'sheet_id': sheet_id,
        'use_google_sheets': use_google_sheets
    }
    
    # Start scraping in background thread
    thread = threading.Thread(target=scrape_jobs_thread, args=(keyword, location, num_pages, sheet_id, use_google_sheets))
    thread.daemon = True
    thread.start()
    
    return jsonify({'success': True, 'message': 'Scraping started!'})

def scrape_jobs_thread(keyword, location, num_pages, sheet_id=None, use_google_sheets=False):
    """Background thread function to run the scraper"""
    global scraping_progress
    
    try:
        scraping_progress['message'] = '🔧 Setting up scraping environment...'
        
        # Create a modified version of fetch_jobs that updates progress
        filename = f"{keyword.replace(' ', '_')}_jobs.csv"
        scraping_progress['filename'] = filename
        
        # Run the API scraper (most reliable method)
        scraping_progress['message'] = f'🚀 Using Glassdoor GraphQL API • Most reliable method'
        
        scraping_progress['message'] = f'🎯 API method active • Fetching "{keyword}" jobs in {location}...'
        
        # Calculate max_results based on num_pages (roughly 30 jobs per page)
        max_results = num_pages * 30
        df = scrape_glassdoor_api(keyword, location, max_results)
        
        if df.empty:
            raise Exception("No jobs found with the specified criteria")
            
        # Handle Google Sheets upload or CSV save
        if use_google_sheets and sheet_id:
            try:
                scraping_progress['message'] = '📊 Saving data to Google Sheets...'
                from google_sheets_integration import GoogleSheetsHandler
                sheets_handler = GoogleSheetsHandler()
                worksheet_name = f"{keyword.replace(' ', '_')}_jobs_{datetime.now().strftime('%Y%m%d_%H%M')}"
                result_info = sheets_handler.save_jobs_to_sheet(df, sheet_id, worksheet_name)
                success = bool(result_info)
                if success:
                    sheets_result = {
                        'url': f'https://docs.google.com/spreadsheets/d/{sheet_id}',
                        'worksheet_name': worksheet_name
                    }
                    result = (df, sheets_result)
                else:
                    # This shouldn't happen as save_jobs_to_sheet raises exception on failure
                    raise Exception("Google Sheets upload returned no result")
            except Exception as sheets_error:
                print(f"Google Sheets upload failed: {sheets_error}")
                # Re-raise the exception so user gets proper error message
                raise Exception(f"Failed to save data to Google Sheets: {str(sheets_error)}")
        else:
            # Save to CSV
            filename = f"{keyword.replace(' ', '_')}_jobs.csv"
            df.to_csv(filename, index=False)
            result = (df, None)
        
        # Handle both single DataFrame return and tuple return
        if isinstance(result, tuple):
            df, sheets_result = result
        else:
            df = result
            sheets_result = None
        
        job_count = len(df)
        scraping_progress['job_count'] = job_count
        scraping_progress['status'] = 'completed'
        
        if sheets_result:
            scraping_progress['message'] = f'✅ Mission accomplished! Found {job_count} jobs • Saved to Google Sheets with professional formatting'
            scraping_progress['sheets_url'] = sheets_result['url']
            scraping_progress['worksheet_name'] = sheets_result['worksheet_name']
        else:
            scraping_progress['message'] = f'✅ Scraping complete! Successfully extracted {job_count} jobs • Ready for download'
            
        scraping_progress['end_time'] = datetime.now().isoformat()
        
    except Exception as e:
        scraping_progress['status'] = 'error'
        scraping_progress['message'] = f'❌ Scraping interrupted • {str(e)} • Please try again'

@app.route('/progress')
def get_progress():
    """Get current scraping progress"""
    return jsonify(scraping_progress)

@app.route('/download/<filename>')
def download_file(filename):
    """Download CSV file"""
    if filename.endswith('.csv') and os.path.exists(filename):
        return send_file(filename, as_attachment=True)
    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)