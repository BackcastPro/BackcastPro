"""Data reader for fetching stock price data from API."""

import os
import requests
import pandas as pd
from datetime import datetime, timedelta
from typing import Union
from dotenv import load_dotenv

# Load environment variables from .env file in project root
load_dotenv()

BACKCASTPRO_API_URL= 'http://backcastpro.i234.me'

def DataReader(code: str, 
        start_date: Union[str, datetime, None] = None, 
        end_date: Union[str, datetime, None] = None) -> pd.DataFrame:
    """
    Fetch stock price data from API.
    
    Args:
        code (str): Stock code (e.g., '7203' for Toyota)
        start_date (Union[str, datetime, None], optional): Start date for data retrieval. 
                                                          If None, defaults to 1 year ago.
        end_date (Union[str, datetime, None], optional): End date for data retrieval. 
                                                        If None, defaults to today.
        
    Returns:
        pd.DataFrame: Stock price data with columns like 'Open', 'High', 'Low', 'Close', 'Volume'
        
    Raises:
        requests.RequestException: If API request fails
        ValueError: If dates are invalid or API returns error
    """
    # Set default dates if not provided
    if end_date is None:
        end_date = datetime.now()
    if start_date is None:
        start_date = end_date - timedelta(days=365)
    
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
        base_url = BACKCASTPRO_API_URL
        
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
            df['Date'] = pd.to_datetime(df['date'])
            df.set_index('Date', inplace=True)
        elif df.index.name is None or df.index.name == 'index':
            # If no date column, try to parse index as datetime
            try:
                df.index = pd.to_datetime(df.index)
            except:
                pass
        
        # Ensure numeric columns are properly typed
        numeric_columns = ['Open', 'High', 'Low', 'Close', 'Volume']
        for col in numeric_columns:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce')
        
        # Add code column to the DataFrame
        df['code'] = code
        
        return df
        
    except requests.exceptions.RequestException as e:
        raise requests.RequestException(f"Failed to fetch data from API: {e}")
    except Exception as e:
        raise ValueError(f"Error processing API response: {e}")

def JapanStocks() -> pd.DataFrame:
    """
    日本株の銘柄リストを取得
    
    Returns:
        pd.DataFrame: 日本株の銘柄リスト（コード、名前、市場、セクター等）
        
    Raises:
        requests.RequestException: If API request fails
        ValueError: If API returns error
    """
    # Construct API URL
    base_url = os.getenv('BACKCASTPRO_API_URL')
    if not base_url:
        base_url = BACKCASTPRO_API_URL
        
    # Ensure base_url doesn't end with slash and path starts with slash
    base_url = base_url.rstrip('/')
    url = f"{base_url}/api/stocks"
    
    try:
        # Make API request
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        
        # Parse JSON response
        data = response.json()
        
        # Convert to DataFrame
        if isinstance(data, dict) and 'data' in data:
            df = pd.DataFrame(data['data'])
        elif isinstance(data, list):
            df = pd.DataFrame(data)
        else:
            raise ValueError(f"Unexpected response format: {type(data)}")
        
        # Ensure proper column names and types
        if 'code' in df.columns:
            df['code'] = df['code'].astype(str)
        if 'name' in df.columns:
            df['name'] = df['name'].astype(str)
        if 'market' in df.columns:
            df['market'] = df['market'].astype(str)
        if 'sector' in df.columns:
            df['sector'] = df['sector'].astype(str)
        if 'currency' in df.columns:
            df['currency'] = df['currency'].astype(str)
        
        return df
        
    except requests.exceptions.RequestException as e:
        raise requests.RequestException(f"Failed to fetch data from API: {e}")
    except Exception as e:
        raise ValueError(f"Error processing API response: {e}")