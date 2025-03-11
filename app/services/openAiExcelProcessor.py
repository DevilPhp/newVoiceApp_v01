import os
import pandas as pd
import numpy as np
from flask import current_app
import json
import openai
from typing import Dict, List, Any, Union
import datetime


class OpenAIExcelProcessor:
    def __init__(self, file_path=None, api_key=None):
        """Initialize the Excel processor with OpenAI integration."""
        # Set the OpenAI API key
        openai.api_key = api_key or os.environ.get('OPENAI_API_KEY')

        # Find the Excel file
        if file_path is None:
            possible_paths = [
                os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                             'Production planning 2025.xlsx'),
                os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                             'static', 'data', 'Production planning 2025.xlsx'),
                os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                             'static', 'uploads', 'Production planning 2025.xlsx'),
            ]

            for path in possible_paths:
                if os.path.exists(path):
                    self.file_path = path
                    break
            else:
                self.file_path = possible_paths[0]
                print(f'WARNING: Excel file not found. Will try: {self.file_path}')
        else:
            self.file_path = file_path

        # Cache for loaded data
        self.dataframes = {}

        # Load all Excel data on initialization
        self._load_all_data()

    def _load_all_data(self):
        """Load all sheets from the Excel file."""
        if not os.path.exists(self.file_path):
            print(f"File not found: {self.file_path}")
            return

        try:

            # Define which sheets you want to load
            target_sheets = ['pletene', 'confekcia', 'za pletene po fainove']

            # Load all sheets into dataframes
            excel_file = pd.ExcelFile(self.file_path)

            # Check which sheets actually exist in the file
            available_sheets = excel_file.sheet_names
            print(f"Available sheets in Excel file: {available_sheets}")

            # Load only the target sheets that exist
            for sheet_name in target_sheets:
                if sheet_name in available_sheets:
                    print(f"Loading sheet: {sheet_name}")
                    df = pd.read_excel(excel_file, sheet_name=sheet_name, header=1)
                    # Clean the dataframe
                    df = self._clean_dataframe(df)

                    # Make sure column names are unique
                    if not df.columns.is_unique:
                        print(f"Warning: Sheet '{sheet_name}' has duplicate column names")
                        # Rename duplicate columns
                        df.columns = pd.io.parsers.base_parser.ParserBase({'names': df.columns})._maybe_dedup_names(
                            df.columns)

                    self.dataframes[sheet_name] = df
                else:
                    print(f"Warning: Sheet '{sheet_name}' not found in Excel file")

            print(f"Loaded {len(self.dataframes)} sheets from Excel file")
        except Exception as e:
            print(f"Error loading Excel data: {str(e)}")
            import traceback
            traceback.print_exc()

    def _clean_dataframe(self, df):
        """Clean the dataframe by removing empty rows, fixing column names, etc."""
        try:
            # Convert header row to column names if it looks like a header
            if isinstance(df.iloc[0, 0], str) and any(
                    term in df.iloc[0, 0].lower() for term in ['фирма', 'company', 'производство']):
                original_columns = df.columns.tolist()
                header_row = df.iloc[1].tolist()

                df = df.iloc[1:].reset_index(drop=True)

                # Set meaningful column names where available
                for i, header in enumerate(header_row):
                    if i < len(original_columns) and isinstance(header, str) and header.strip():
                        df.rename(columns={original_columns[i]: header.strip()}, inplace=True)

            # Replace empty strings with NaN
            df.replace('', np.nan, inplace=True)

            print(df.info())
            return df
        except Exception as e:
            print(f"Error cleaning dataframe: {str(e)}")
            return df

    def _json_serializable(self, obj):
        """Convert DataFrame to JSON-serializable format, handling NaT and other non-serializable types."""
        if isinstance(obj, dict):
            # Convert keys and values that might not be serializable
            result = {}
            for k, v in obj.items():
                # Convert datetime keys to strings
                if isinstance(k, (pd.Timestamp, datetime.datetime, datetime.date)):
                    k = str(k)
                # Convert other unserializable keys to strings too
                elif not isinstance(k, (str, int, float, bool)) and k is not None:
                    k = str(k)

                # Convert the value recursively
                result[k] = self._json_serializable(v)
            return result
        elif isinstance(obj, list):
            return [self._json_serializable(item) for item in obj]
        elif isinstance(obj, (pd.Timestamp, pd._libs.tslibs.nattype.NaTType, datetime.datetime, datetime.date)):
            return str(obj)
        elif pd.isna(obj):
            return None
        elif isinstance(obj, (np.int64, np.int32, np.float64, np.float32)):
            return float(obj) if isinstance(obj, (np.float64, np.float32)) else int(obj)
        else:
            return obj

    def _extract_sheet_summaries(self):
        """Extract summaries of each sheet for context."""
        summaries = {}

        for sheet_name, df in self.dataframes.items():
            if df.empty:
                continue

            # Get column names
            columns = df.columns.tolist()

            # Get data shape
            rows, cols = df.shape

            # Get sample of unique values for key columns
            sample_data = {}
            for col in columns[:min(5, len(columns))]:
                unique_values = df[col].dropna().unique()
                sample_values = unique_values[:min(5, len(unique_values))].tolist()
                # Convert numpy values to native Python types
                sample_data[str(col)] = self._json_serializable(sample_values)

            summaries[sheet_name] = {
                "columns": [str(col) for col in columns],
                "rows": rows,
                "sample_data": sample_data
            }

        return summaries

    def _prepare_data_context(self, query):
        """
        Prepare the relevant data from Excel for the query context.
        Analyzes the query to determine which sheets/data are relevant.
        """
        context_data = {}
        query_lower = query.lower()

        # Include sheet summaries for overall context
        context_data["sheet_summaries"] = self._extract_sheet_summaries()

        # Extract specific data based on the query
        # If query mentions a client, include client data
        if any(word in query_lower for word in ['клиент', 'фирма', 'компания']):
            for sheet_name, df in self.dataframes.items():
                if df.empty or len(df.columns) < 1:
                    continue

                # Get client column (usually first column)
                client_col = df.columns[0]

                # Include a sample of client data (only first 10 rows to limit size)
                client_sample = df.head(10)
                # Convert to native Python types for JSON serialization
                context_data[f"client_data_{sheet_name}"] = self._json_serializable(
                    client_sample.to_dict(orient='records'))

        # If query mentions a specific model or product type
        if any(word in query_lower for word in ['модел', 'продукт', 'изделие', 'артикул']):
            for sheet_name, df in self.dataframes.items():
                # Look for product/model columns
                for col in df.columns:
                    if isinstance(col, str) and any(term in str(col).lower() for term in ['модел', 'вид', 'артикул']):
                        product_sample = df.head(10)
                        context_data[f"product_data_{sheet_name}"] = self._json_serializable(
                            product_sample.to_dict(orient='records'))
                        break

        # If query mentions monthly data or planning
        if any(word in query_lower for word in ['месец', 'план', 'седмица', 'дата']):
            # Try to find monthly columns
            for sheet_name, df in self.dataframes.items():
                month_cols = []
                month_names = ['януари', 'февруари', 'март', 'април', 'май', 'юни',
                               'юли', 'август', 'септември', 'октомври', 'ноември', 'декември']

                for col in df.columns:
                    if isinstance(col, str) and any(month in str(col).lower() for month in month_names):
                        month_cols.append(col)

                if month_cols:
                    # Only select month columns
                    monthly_sample = df[month_cols].head(10)
                    context_data[f"monthly_data_{sheet_name}"] = self._json_serializable(
                        monthly_sample.to_dict(orient='records'))

        # If no specific data was included, add samples from all sheets
        if len(context_data) <= 1:  # Only has sheet_summaries
            for sheet_name, df in self.dataframes.items():
                if not df.empty:
                    sample_df = df.head(5)  # Just 5 rows to limit size
                    context_data[f"sample_data_{sheet_name}"] = self._json_serializable(
                        sample_df.to_dict(orient='records'))

        return context_data

    def process_query(self, query):
        """
        Process a Bulgarian language query about production planning data.

        Args:
            query (str): The user query in Bulgarian

        Returns:
            dict: A dictionary with the response and success status
        """
        if not openai.api_key:
            return {
                'success': False,
                'message': "OpenAI API ключът не е конфигуриран. Моля, проверете настройките."
            }

        try:
            # Prepare relevant data context based on the query
            context_data = self._prepare_data_context(query)

            # Convert context data to a JSON string (safely handled for serialization)
            try:
                context_str = json.dumps(context_data, ensure_ascii=False)

                # Truncate if too large to avoid token limits
                if len(context_str) > 8000:  # Lower limit to ensure we stay within token constraints
                    context_str = context_str[:8000] + "... [truncated]"
            except TypeError as e:
                print(f"JSON serialization error: {str(e)}")
                # Fallback to simpler context if JSON serialization fails
                context_str = json.dumps({"error": "Could not serialize full data context"}, ensure_ascii=False)

            # Prepare the system message
            system_message = """Ти си експертен асистент за анализ на данни за производство. 
            Твоята задача е да анализираш данни от Excel таблица за планиране на производството 
            и да отговориш на въпроси на български език. Бъди точен, професионален и ясен в отговорите си."""

            # Prepare the user message with context and query
            user_message = f"""Разполагаш със следните данни от Excel файл с информация за планиране на производството:

            {context_str}

            Въпрос на потребителя: "{query}"

            Моля, анализирай данните и отговори на въпроса на български език. Включи релевантни числа и статистики 
            от данните, където е възможно."""

            # Generate the response using OpenAI's API
            response = openai.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": system_message},
                    {"role": "user", "content": user_message}
                ],
                temperature=0.5,
                max_tokens=500
            )

            # Extract the response text
            response_text = response.choices[0].message.content

            return {
                'success': True,
                'message': response_text
            }

        except Exception as e:
            print(f"Error processing query: {str(e)}")
            import traceback
            traceback.print_exc()
            return {
                'success': False,
                'message': f"Възникна грешка при обработката: {str(e)}"
            }