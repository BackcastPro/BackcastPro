"""Data reader for fetching stock price data from API."""

import os
import requests
import pandas as pd
from datetime import datetime
from typing import Union
from dotenv import load_dotenv

# Load environment variables from .env file in project root
load_dotenv()


def DataReader(code: str, 
        start_date: Union[str, datetime], 
        end_date: Union[str, datetime]) -> pd.DataFrame:
    """
    Fetch stock price data from API.
    
    Args:
        code (str): Stock code (e.g., '72030' for Toyota)
        start_date (Union[str, datetime]): Start date for data retrieval
        end_date (Union[str, datetime]): End date for data retrieval
        
    Returns:
        pd.DataFrame: Stock price data with columns like 'Open', 'High', 'Low', 'Close', 'Volume'
        
    Raises:
        requests.RequestException: If API request fails
        ValueError: If dates are invalid or API returns error
    """
    # Convert datetime objects to string format if needed
    if isinstance(start_date, datetime):
        start_date_str = start_date.strftime('%Y-%m-%d')
    else:
        start_date_str = str(start_date)
        
    if isinstance(end_date, datetime):
        end_date_str = end_date.strftime('%Y-%m-%d')
    else:
        end_date_str = str(end_date)
    
    # Construct API URL
    base_url = os.getenv('BACKCASTPRO_API_URL')
    if not base_url:
        base_url = 'http://backcastpro.i234.me'
        
    # Ensure base_url doesn't end with slash and path starts with slash
    base_url = base_url.rstrip('/')
    url = f"{base_url}/api/stocks/price?code={code}&start_date={start_date_str}&end_date={end_date_str}"
    
    try:
        # Make API request
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        
        # Parse JSON response
        data = response.json()
        
        # Convert to DataFrame
        if isinstance(data, dict):
            if 'price_data' in data:
                df = pd.DataFrame(data['price_data'])
            elif 'data' in data:
                df = pd.DataFrame(data['data'])
            elif 'prices' in data:
                df = pd.DataFrame(data['prices'])
            elif 'results' in data:
                df = pd.DataFrame(data['results'])
            else:
                # If it's a single dict, wrap it in a list
                df = pd.DataFrame([data])
        elif isinstance(data, list):
            # If response is directly a list
            df = pd.DataFrame(data)
        else:
            raise ValueError(f"Unexpected response format: {type(data)}")
        
        # Ensure proper datetime index
        if 'Date' in df.columns:
            df['Date'] = pd.to_datetime(df['Date'])
            df.set_index('Date', inplace=True)
        elif 'date' in df.columns:
            df['date'] = pd.to_datetime(df['date'])
            df.set_index('date', inplace=True)
        elif df.index.name is None or df.index.name == 'index':
            # If no date column, try to parse index as datetime
            try:
                df.index = pd.to_datetime(df.index)
            except:
                pass
        
        # Ensure numeric columns are properly typed
        numeric_columns = ['Open', 'High', 'Low', 'Close', 'Volume', 'open', 'high', 'low', 'close', 'volume']
        for col in numeric_columns:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce')
        
        return df
        
    except requests.exceptions.RequestException as e:
        raise requests.RequestException(f"Failed to fetch data from API: {e}")
    except Exception as e:
        raise ValueError(f"Error processing API response: {e}")
