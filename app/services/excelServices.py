import os
import pandas as pd
from flask import current_app
import re
import datetime
from datetime import date, timedelta
import calendar
import numpy as np


class ProductionPlanningProcessor:
    def __init__(self, file_path=None):
        """Initialize Excel processor with the production planning file."""
        # If file path not provided, try multiple locations
        if file_path is None:
            # Try various common locations for the Excel file
            possible_paths = [
                # Root project directory
                os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                             'Production planning 2025.xlsx'),
                # In static/data folder
                os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                             'static', 'data', 'Production planning 2025.xlsx'),
                # In static/uploads folder
                os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                             'static', 'uploads', 'Production planning 2025.xlsx'),
                # In the current directory
                os.path.join(os.path.abspath(os.path.dirname(__file__)),
                             'Production planning 2025.xlsx')
            ]

            # Find the first path that exists
            for path in possible_paths:
                if os.path.exists(path):
                    self.file_path = path
                    break
            else:
                # If none of the paths exist, use the default path but log a warning
                self.file_path = possible_paths[0]
                print(f'WARNING: Excel file not found in any of the expected locations. Will try: {self.file_path}')
        else:
            self.file_path = file_path

        print(f'Initializing Excel processor with file: {self.file_path}')
        print(f'File exists: {os.path.exists(self.file_path)}')

        if not os.path.exists(self.file_path):
            print(f'⚠️ File does not exist: {self.file_path}')
            # List all xlsx files in the project directory to help diagnose
            project_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            print(f'Searching for Excel files in {project_dir}')
            for root, dirs, files in os.walk(project_dir):
                for file in files:
                    if file.endswith('.xlsx'):
                        print(f'Found Excel file: {os.path.join(root, file)}')
        print(f'Initializing Excel processor with file: {self.file_path}')

        # Ensure the data directory exists
        os.makedirs(os.path.dirname(self.file_path), exist_ok=True)

        # Key Bulgarian keywords for intent detection
        self.bulgarian_keywords = {
            'summary': ['обобщение', 'резюме', 'справка', 'информация', 'статистика', 'данни'],
            'client': ['клиент', 'фирма', 'компания', 'марка'],
            'product': ['продукт', 'артикул', 'модел', 'изделие', 'стока'],
            'production': ['производство', 'изработка', 'изплетено', 'изработено', 'конфекционирано'],
            'machine_type': ['файн', 'машини', 'машина', 'гейдж', 'гейч'],
            'planning': ['планиране', 'план', 'график', 'прогноза', 'очаквано'],
            'date': ['дата', 'ден', 'днес', 'утре', 'завчера', 'седмица', 'месец'],
            'quantity': ['количество', 'бройки', 'брой', 'бр'],
            'color': ['цвят', 'цветове'],
            'type': ['вид', 'тип', 'видове'],
            'factory': ['цех', 'работилница', 'фабрика', 'етаж']
        }

        # Common translation mappings (product types, month names)
        self.product_type_mappings = {
            'пуловер': 'пуловер',
            'жилетка': 'жилетка',
            'жилетка с копчета': 'жил с коп',
            'жилетка с цип': 'жил с цип',
            'риза': 'риза',
            'риза с копчета': 'риза с к-та',
            'троер': 'троер',
            'елек': 'елек',
            'рокля': 'рокля',
            'пола': 'пола',
            'шал': 'шал',
            'шапка': 'шапка'
        }

        self.month_mappings = {
            'януари': 1,
            'февруари': 2,
            'март': 3,
            'април': 4,
            'май': 5,
            'юни': 6,
            'юли': 7,
            'август': 8,
            'септември': 9,
            'октомври': 10,
            'ноември': 11,
            'декември': 12
        }

        # Bulgarian ordinal number words to digits (1-31)
        self.ordinal_word_to_num = {
            'първи': 1, 'втори': 2, 'трети': 3, 'четвърти': 4, 'пети': 5,
            'шести': 6, 'седми': 7, 'осми': 8, 'девети': 9, 'десети': 10,
            'единадесети': 11, 'единайсти': 11, 'дванадесети': 12, 'дванайсти': 12, 'тринадесети': 13,
            'тринайсти': 13, 'четиринадесети': 14, 'четиринайсти': 14,
            'петнайсти': 15, 'петнадесети': 15, 'шестнадесети': 16,
            'шестнайсти': 16, 'седемнадесети': 17, 'седемнайсти': 17,
            'осемнайсти': 18, 'осемнадесети': 18, 'деветнадесети': 19,
            'деветнайсти': 19, 'двадесети': 20, 'двайсти': 20, 'двадесет и първи': 21,
            'двайсет и първи': 21, 'двайспърви': 21, 'двадесет и втори': 22, 'двайсет и втори': 22,
            'двайсвтори': 22, 'двайстрети': 23, 'двайсет и трети': 23, 'двадесет и трети': 23,
            'двайсет и четвърти': 24, 'двадесет и четвърти': 24, 'двайсчетвърти': 24,
            'двадесет и пети': 25, 'двайсет и пети': 25, 'двайспети': 25,
            'двадесет и шести': 26, 'двайсет и шести': 26, 'двайсшести': 26,
            'двадесет и седми': 27, 'двайсет и седми': 27, 'двайсседми': 27,
            'двадесет и осми': 28, 'двайсет и осми': 28, 'двайсосми': 28,
            'двадесет и девети': 29, 'двайсет и девети': 29, 'двайсдевети': 29,
            'тридесети': 30, 'трийсти': 30,
            'тридесет и първи': 31, 'трийсет и първи': 31, 'трийспърви': 31,
        }

        # Cache for loaded data
        self.cached_data = {}

    def load_workbook(self):
        """Load the Excel workbook with all sheets."""
        if not os.path.exists(self.file_path):
            raise FileNotFoundError(f"File not found: {self.file_path}")
        print(f'Loading Excel workbook from: {self.file_path}')
        try:
            return pd.ExcelFile(self.file_path)
        except Exception as e:
            current_app.logger.error(f"Error loading Excel file: {str(e)}")
            raise Exception(f"Грешка при зареждане на файла: {str(e)}")

    def get_sheet_data(self, sheet_name):
        """Get data from a specific sheet, with caching."""
        # Check if data is in cache
        if sheet_name in self.cached_data:
            return self.cached_data[sheet_name]

        # Load the data if not cached
        try:
            excel_file = self.load_workbook()

            # Check if this is a MockExcelFile
            if hasattr(excel_file, 'parse'):
                df = excel_file.parse(sheet_name)
            else:
                df = pd.read_excel(excel_file, sheet_name=sheet_name)

            # Cache the data
            self.cached_data[sheet_name] = df
            return df
        except Exception as e:
            current_app.logger.error(f"Error loading sheet '{sheet_name}': {str(e)}")
            raise Exception(f"Грешка при зареждане на данните от лист '{sheet_name}': {str(e)}")

    def get_all_sheet_names(self):
        """Get all sheet names in the workbook."""
        try:
            excel_file = self.load_workbook()
            return excel_file.sheet_names
        except Exception as e:
            current_app.logger.error(f"Error getting sheet names: {str(e)}")
            raise Exception(f"Грешка при извличане на имената на листовете: {str(e)}")

    def clean_dataframe(self, df):
        """Clean the dataframe by removing header rows and fixing column names."""
        try:
            # Check if this is likely a header row by looking for common header terms
            if isinstance(df.iloc[0, 0], str) and any(
                    term in df.iloc[0, 0].lower() for term in ['фирма', 'company', 'производство']):
                # This is a header row, let's set it as column names if possible
                # First, preserve the original column names as they might be important
                original_columns = df.columns.tolist()

                # Extract the header row and skip it
                header_row = df.iloc[0].tolist()
                df = df.iloc[1:].reset_index(drop=True)

                # Set meaningful column names where available
                for i, header in enumerate(header_row):
                    if i < len(original_columns) and isinstance(header, str) and header.strip():
                        df.rename(columns={original_columns[i]: header.strip()}, inplace=True)

            # Replace empty strings with NaN for better processing
            df.replace('', np.nan, inplace=True)

            return df
        except Exception as e:
            current_app.logger.error(f"Error cleaning dataframe: {str(e)}")
            return df  # Return original if cleaning fails

    def detect_query_intent(self, user_message):
        """
        Detect intent from Bulgarian language user message.

        Args:
            user_message: string with user's query in Bulgarian

        Returns:
            tuple (intent_type, params) with the detected intent and parameters
        """
        message = user_message.lower()

        # Initialize results
        intent_type = "summary"  # Default intent
        params = {}

        # Check for each intent type based on keyword presence
        intent_scores = {}
        for intent, keywords in self.bulgarian_keywords.items():
            score = sum(1 for keyword in keywords if keyword in message)
            intent_scores[intent] = score

        # Get the intent with the highest score
        primary_intent = max(intent_scores, key=intent_scores.get)
        if intent_scores[primary_intent] > 0:
            intent_type = primary_intent

        # Extract client name if present
        client_match = re.search(r'(?:клиент|фирма|марка)\s+(\w+)', message)
        if client_match:
            params['client'] = client_match.group(1)
        elif 'клиент' in message or 'фирма' in message or 'марка' in message:
            # If client intent but no specific client, check for client names in the message
            common_clients = ['matinique', 'lebek', 'матеник', 'лебек', 'robert tod', 'робърт тод', 'zerbi', 'зерби']
            for client in common_clients:
                if client in message.lower():
                    params['client'] = client
                    break

        # Extract product type if present
        for product_type, db_match in self.product_type_mappings.items():
            if product_type in message:
                params['product_type'] = db_match
                break
        # print(user_message)
        # Extract products if client name and products is present
        products_match = re.search(r'(всички)\s+(\w+)', message)
        if products_match:
            params['all_products'] = True

        specific_products_match = re.search(r'(?:номер|модел|модели|поръчка|поръчки)\s+(.*)', message)
        if specific_products_match and client_match and not products_match:
            params['specific_products'] = specific_products_match.group(1).split()
            for char in [' ', ',', '-', ';', '.', ':', 'и']:
                params['specific_products'] = [product.replace(char, '') for product in params['specific_products']]

        today = date.today()

        # Check for "този месец" (this month)
        is_this_month = bool(re.search(r'(?:този|текущия|настоящия|сегашния)\s+месец', message))
        if is_this_month:
            params['month'] = today.month
            params['month_name'] = calendar.month_name[params['month']]

        # Extract month if present
        for month_name, month_num in self.month_mappings.items():
            if month_name in message:
                params['month'] = month_num
                params['month_name'] = month_name
                break


        # Extract date references
        if 'днес' in message:
            params['date'] = today.strftime('%Y-%m-%d')
        elif 'утре' in message:
            params['date'] = (today + timedelta(days=1)).strftime('%Y-%m-%d')
        elif 'вчера' in message:
            params['date'] = (today - timedelta(days=1)).strftime('%Y-%m-%d')
        elif 'завчера' in message:
            params['date'] = (today - timedelta(days=2)).strftime('%Y-%m-%d')

        # Extract day if present
        day_num = None

        # First check for written ordinal numbers
        for word, num in self.ordinal_word_to_num.items():
            if word in message:
                day_num = num
                break

        # If no written ordinal found, look for numeric patterns
        # if day_num is None:
        #     # Match patterns like "10-ти", "10ти", "10 ти", "10-и", "10и", etc.
        #     day_match = re.search(r'(\d{1,2})(?:-?[ти][ия][и])?', message)
        #     if day_match:
        #         try:
        #             day_num = int(day_match.group(1))
        #             # Validate day number
        #             if day_num < 1 or day_num > 31:
        #                 day_num = None
        #         except ValueError:
        #             day_num = None

        # If we have a day number, construct the date
        if day_num:
            try:
                # Check if the day is valid for the given month and year
                if not params['month']:
                    params['month'] = today.month
                max_days = calendar.monthrange(today.year, params['month'])[1]
                if day_num <= max_days:
                    params['date'] = f'{today.year}-{params['month']}-{day_num}'
            except ValueError:
                pass  # Invalid date, return None

        # Extract factory/workshop if mentioned
        factory_match = re.search(r'(?:цех|етаж)\s+(\w+|\d+(?:-ти)?)', message)
        if factory_match:
            params['factory'] = factory_match.group(1)

        return intent_type, params

    def get_client_list(self):
        """Get a list of all clients from the Excel file."""
        try:
            # Get data from both main sheets
            # knitting_df = self.clean_dataframe(self.get_sheet_data('pletene'))
            # confection_df = self.clean_dataframe(self.get_sheet_data('confekcia'))
            clients_df = self.clean_dataframe(self.get_sheet_data('za pletene po fainove'))

            # Get all client names from first column, usually "Фирма" or similar
            # clients_knitting = set()
            # clients_confection = set()
            allClients = set()

            if not clients_df.empty:
                allClients = set(clients_df.iloc[:, 0].dropna().unique())

            # if not knitting_df.empty:
            #     clients_knitting = set(knitting_df.iloc[:, 0].dropna().unique())
            #
            # if not confection_df.empty:
            #     clients_confection = set(confection_df.iloc[:, 0].dropna().unique())

            # Combine and filter out non-client entries (often headers or empty)
            # all_clients = clients_knitting.union(clients_confection)
            valid_clients = [client for client in allClients
                             if isinstance(client, str)
                             and client.strip()
                             and client.lower() not in ['фирма', 'company', 'производство']]

            return sorted(valid_clients)
        except Exception as e:
            current_app.logger.error(f"Error getting client list: {str(e)}")
            return []

    def match_client_name(self, client_query):
        """Find the best matching client name from the available clients."""
        if not client_query:
            return None

        client_query = client_query.lower()
        client_list = self.get_client_list()

        # Direct match
        for client in client_list:
            if client.lower() == client_query:
                return client

        # Partial match
        matches = []
        for client in client_list:
            if client_query in client.lower() or client.lower() in client_query:
                matches.append((client, len(client) / len(client_query) if len(client_query) > 0 else 0))
            print(matches)

        if matches:
            # Sort by score (closest length ratio)
            matches.sort(key=lambda x: abs(1 - x[1]))
            return matches[0][0]

        return None

    def get_product_types(self):
        """Get all product types from the Excel file."""
        try:
            # Try to get product type data from both sheets
            knitting_df = self.clean_dataframe(self.get_sheet_data('pletene'))
            confection_df = self.clean_dataframe(self.get_sheet_data('confekcia'))

            product_types = set()

            # Look for a column that might contain product types (usually "вид" or similar)
            for df in [knitting_df, confection_df]:
                if df.empty:
                    continue

                # Try to find the product type column
                type_col = None
                for i, col in enumerate(df.columns):
                    if isinstance(col, str) and 'вид' in col.lower():
                        type_col = col
                        break

                # If not found by name, try column 5 which often contains product types
                if type_col is None and len(df.columns) > 5:
                    type_col = df.columns[5]

                if type_col is not None:
                    types = df[type_col].dropna().unique()
                    product_types.update([t for t in types if isinstance(t, str) and t.strip()])

            return sorted(product_types)
        except Exception as e:
            current_app.logger.error(f"Error getting product types: {str(e)}")
            return []

    def match_product_name(self, product_query, db_client):
        """Find the best matching product name from the available products."""
        # print(product_query, db_client)
        if not product_query or db_client.empty:
            return None

        score_treshreshold = 0.1

        product_list = db_client.get('Модел')  # Assuming products collection has a 'name' field

        selected_products = []

        for query in product_query:
            # Direct match
            for product in product_list:
                clean_product = str(product).lower()
                for char in [' ', ',', '-', ';', '.', ':', 'и']:
                    clean_product = clean_product.replace(char, '')
                if clean_product == query:
                    selected_products.append(product)

            # print(selected_products)

            # Partial match
            matches = []
            for product in product_list:
                cleaned_product = str(product).lower()
                for char in [' ', ',', '-', ';', '.', ':', 'и']:
                    cleaned_product = cleaned_product.replace(char, '').lower()
                if query in cleaned_product or cleaned_product in query:
                    matches.append(
                        (product, len(query) / len(cleaned_product) if len(query) > 0 else 0))

            print(matches)
            if matches:
                filtered_matches = [match for match in matches if match[1] > score_treshreshold]

                for match in filtered_matches:
                    selected_products.append(match[0])
                # Sort by score (closest length ratio)
                # matches.sort(key=lambda x: abs(1 - x[1]))
                # selected_products.append(matches[0][0])

        return selected_products if selected_products else None


    def match_product_type(self, product_query):
        """Find the best matching product type from the available types."""
        if not product_query:
            return None

        product_query = product_query.lower()
        product_types = self.get_product_types()

        # Direct match
        for product_type in product_types:
            if product_type.lower() == product_query:
                return product_type

        # Partial match
        matches = []
        for product_type in product_types:
            if product_query in product_type.lower() or product_type.lower() in product_query:
                matches.append((product_type, len(product_type) / len(product_query) if len(product_query) > 0 else 0))

        if matches:
            # Sort by score (closest length ratio)
            matches.sort(key=lambda x: abs(1 - x[1]))
            return matches[0][0]

        return None

    def get_factory_list(self):
        """Get a list of all factories/workshops from the Excel file."""
        try:
            # Get data from both main sheets
            knitting_df = self.clean_dataframe(self.get_sheet_data('pletene'))
            confection_df = self.clean_dataframe(self.get_sheet_data('confekcia'))

            factories = set()

            # Try to find the factory/workshop column (usually "цех" or similar)
            for df in [knitting_df, confection_df]:
                if df.empty:
                    continue

                factory_col = None
                for i, col in enumerate(df.columns):
                    if isinstance(col, str) and 'цех' in col.lower():
                        factory_col = col
                        break

                # If not found by name, try column 3 which often contains factory info
                if factory_col is None and len(df.columns) > 3:
                    factory_col = df.columns[3]

                if factory_col is not None:
                    factory_list = df[factory_col].dropna().unique()
                    factories.update([f for f in factory_list if isinstance(f, str) and f.strip()])

            return sorted(factories)
        except Exception as e:
            current_app.logger.error(f"Error getting factory list: {str(e)}")
            return []

    def get_client_info(self, client_query, all_products, specific_products):
        """Get detailed information about a specific client."""
        results = {}

        try:
            client_name = self.match_client_name(client_query)

            if not client_name:
                return {
                    'client_found': False,
                    'message': f"Не намерих клиент, съответстващ на '{client_query}'. Опитайте с друго име."
                }

            # Load and clean the data from both sheets
            knitting_df = self.clean_dataframe(self.get_sheet_data('pletene'))
            confection_df = self.clean_dataframe(self.get_sheet_data('confekcia'))
            summary_df = self.clean_dataframe(self.get_sheet_data('za pletene po fainove'))

            # Filter by client name
            client_knitting = knitting_df[
                (knitting_df.iloc[:, 0] == client_name) &
                (knitting_df.iloc[:, 1])] if not knitting_df.empty else pd.DataFrame()
            client_confection = confection_df[
                (confection_df.iloc[:, 0] == client_name) &
                (confection_df.iloc[:, 1])] if not confection_df.empty else pd.DataFrame()
            client_summary = summary_df[
                summary_df.iloc[:, 0] == client_name] if not summary_df.empty else pd.DataFrame()

            # Check if we found any data
            if client_knitting.empty and client_confection.empty:
                return {
                    'client_found': False,
                    'client_name': client_name,
                    'message': f"Намерих клиент '{client_name}', но нямам данни за него."
                }

            # Initialize results dictionary
            results = {
                'client_found': True,
                'client_name': client_name,
                'knitting_data': {},
                'confection_data': {},
                'product_types': set(),
                'all_products': {},
                'specific_product': {},
                'monthly_data': {},
                'total_ordered': 0,
                'total_knitted': 0,
                'total_confectioned': 0,
                'for_knitting': 0,
                'for_confection': 0,
            }

            # Extract product types
            # First find the column with product types (usually "вид" or column 5)
            knitting_type_col = None
            confection_type_col = None

            for df in [knitting_df, confection_df]:
                if df.empty:
                    continue

                for i, col in enumerate(df.columns):
                    if isinstance(col, str) and 'вид' in col.lower():
                        knitting_type_col = col
                        confection_type_col = col
                        break

                # # If not found by name, try column 5
                # if locals()[col_var] is None and len(df.columns) > 5:
                #     locals()[col_var] = df.columns[5]

            # Get all products if True
            if all_products:
                for col, row in client_confection.iterrows():
                    # if isinstance(col, str) and 'модел' in col.lower():
                    #     for row in client_confection[col]:
                    #         results['all_products'][row] = 0
                    results['all_products'][str(row['Модел'])] = {
                        'файн': row['файн'],
                        'вид': row['вид'],
                        'поръчка': row['Поръчка'],
                        'изплетено': row['изплетено до момента в бр.'],
                        'за плетене': row['остава за плетене в бр'],
                        'конфекционирано': row['конфекционирано до момента в бр.'],
                        'за конфекциониране': row['остава за конфекция в бр']
                    }

            # Extract specific product details
            match_specific_product = None
            if specific_products:
                match_specific_product = self.match_product_name(specific_products, client_confection)

                if match_specific_product:
                    results['specific_product'] = match_specific_product
            print(match_specific_product)

            # Extract monthly data
            # Look for specific columns with production data

            # Try to find columns with specific keywords


            # Get product types
            if knitting_type_col and not client_knitting.empty:
                types = client_knitting[knitting_type_col].dropna().unique()
                results['product_types'].update([t for t in types if isinstance(t, str) and t.strip()])

            if confection_type_col and not client_confection.empty:
                types = client_confection[confection_type_col].dropna().unique()
                results['product_types'].update([t for t in types if isinstance(t, str) and t.strip()])

            # Get order quantities
            # Try to find order quantity column (usually "Поръчка" or column 2)
            order_col = None
            for i, col in enumerate(summary_df.columns):
                if isinstance(col, str) and 'поръчки в бр.' in col.lower():
                    order_col = col
                    break

            if order_col is None and len(summary_df.columns) > 1:
                order_col = knitting_df.columns[1]

            if order_col and not client_summary.empty:
                client_orders = client_summary[order_col].sum()
                if not pd.isna(client_orders):
                    results['total_ordered'] = client_orders

            # Get knitting and confection quantities
            # Look for specific columns with production data

            knittingCol = None
            confectionCol = None
            forKnittingCol = None
            forConfectionCol = None
            order_product_type_col = None

            # Try to find columns with specific keywords
            # for df, keywords in [
            #     (knitting_df, ['изплетено до момента', 'конфекционирано до момента', 'остава за конфекция в бр', 'остава за плетене в бр']),
            #     (confection_df, ['конфекционирано до момента', 'конфекционирано'])
            # ]:
            #     print(df)
            #     if df.empty:
            #         continue
            #
            for col in confection_df.columns:
                if isinstance(col, str) and col == 'изплетено до момента в бр.':
                    knittingCol = col
                elif isinstance(col, str) and col == 'конфекционирано до момента в бр.':
                    confectionCol = col
                elif isinstance(col, str) and col == 'остава за конфекция в бр':
                    forConfectionCol = col
                elif isinstance(col, str) and col == 'остава за плетене в бр':
                    forKnittingCol = col
                elif isinstance(col, str) and col == 'Поръчка':
                    order_product_type_col = col


            # Get the knitting quantity
            # if knittingCol and not client_knitting.empty:
            #     knitting_qty = client_knitting[knittingCol].sum()
            #     if not pd.isna(knitting_qty):
            #         results['total_knitted'] = knitting_qty

            # Get the confection quantity
            if not client_confection.empty:
                knitting_qty = client_confection[knittingCol].sum()
                if not pd.isna(knitting_qty):
                    results['total_knitted'] = knitting_qty

                confection_qty = client_confection[confectionCol].sum()
                if not pd.isna(confection_qty):
                    results['total_confectioned'] = confection_qty

                for_knitting_qty = client_confection[forKnittingCol].sum()
                if not pd.isna(knitting_qty):
                    results['for_knitting'] = for_knitting_qty

                for_confection_qty = client_confection[forConfectionCol].sum()
                if not pd.isna(confection_qty):
                    results['for_confection'] = for_confection_qty

            # print(results)

            # Get monthly data
            month_cols = ['януари', 'февруари', 'март', 'април', 'май', 'юни',
                          'юли', 'август', 'септември', 'октомври', 'ноември', 'декември']

            for df, data_type in [(client_knitting, 'плетене'), (client_confection, 'конфекция')]:
                if df.empty:
                    continue

                for month in month_cols:
                    # Try to find the month column
                    month_col = None
                    for col in df.columns:
                        if isinstance(col, str) and month.lower() in col.lower():
                            month_col = col
                            break

                    if month_col:
                        monthly_qty = df[month_col].sum()
                        if not pd.isna(monthly_qty) and monthly_qty > 0:
                            if month not in results['monthly_data']:
                                results['monthly_data'][month] = {}
                            results['monthly_data'][month][data_type] = monthly_qty

            # Get details for each product type
            if knitting_type_col and not client_knitting.empty:
                results['product_details'] = {}

                for product_type in results['product_types']:
                    product_knitting = client_knitting[client_knitting[knitting_type_col] == product_type]
                    product_confection = pd.DataFrame()

                    if confection_type_col and not client_confection.empty:
                        product_confection = client_confection[client_confection[confection_type_col] == product_type]

                    if not product_knitting.empty or not product_confection.empty:
                        prod_details = {
                            'ordered': 0,
                            'knitted': 0,
                            'confectioned': 0,
                            'monthly_data': {}
                        }

                        # Get order quantity for this product
                        if order_product_type_col and not product_confection.empty:
                            prod_orders = product_confection[order_product_type_col].sum()
                            if not pd.isna(prod_orders):
                                prod_details['ordered'] = prod_orders

                        # Get knitting quantity for this product
                        if knittingCol and not product_knitting.empty:
                            prod_knitting = product_knitting[knittingCol].sum()
                            if not pd.isna(prod_knitting):
                                prod_details['knitted'] = prod_knitting

                        # Get confection quantity for this product
                        if confectionCol and not product_confection.empty:
                            prod_confection = product_confection[confectionCol].sum()
                            if not pd.isna(prod_confection):
                                prod_details['confectioned'] = prod_confection

                        # Get monthly data for this product
                        for df, data_type in [(product_knitting, 'плетене'), (product_confection, 'конфекция')]:
                            if df.empty:
                                continue

                            for month in month_cols:
                                # Try to find the month column
                                month_col = None
                                for col in df.columns:
                                    if isinstance(col, str) and month.lower() in col.lower():
                                        month_col = col
                                        break

                                if month_col:
                                    monthly_qty = df[month_col].sum()
                                    if not pd.isna(monthly_qty) and monthly_qty > 0:
                                        if month not in prod_details['monthly_data']:
                                            prod_details['monthly_data'][month] = {}
                                        prod_details['monthly_data'][month][data_type] = monthly_qty

                        results['product_details'][product_type] = prod_details

            return results

        except Exception as e:
            # current_app.logger.error(f"Error getting client info: {str(e)}")
            print(e)
            return {
                'client_found': False,
                'error': str(e),
                'message': f"Възникна грешка при извличане на информация за клиент: {str(e)}"
            }

    def get_product_info(self, product_type_query):
        """Get detailed information about a specific product type."""
        results = {}

        try:
            product_type = self.match_product_type(product_type_query)

            if not product_type:
                return {
                    'product_found': False,
                    'message': f"Не намерих продукт, съответстващ на '{product_type_query}'. Опитайте с друг тип продукт."
                }

            # Load and clean the data from both sheets
            knitting_df = self.clean_dataframe(self.get_sheet_data('pletene'))
            confection_df = self.clean_dataframe(self.get_sheet_data('confekcia'))

            # Find product type column
            knitting_type_col = None
            confection_type_col = None

            for df, col_var in [(knitting_df, 'knitting_type_col'), (confection_df, 'confection_type_col')]:
                if df.empty:
                    continue

                for i, col in enumerate(df.columns):
                    if isinstance(col, str) and 'вид' in col.lower():
                        locals()[col_var] = col
                        break

                # If not found by name, try column 5
                if locals()[col_var] is None and len(df.columns) > 5:
                    locals()[col_var] = df.columns[5]

            # Filter by product type
            product_knitting = knitting_df[knitting_df[
                                               knitting_type_col] == product_type]\
                                                if knitting_type_col and not knitting_df.empty else pd.DataFrame()
            product_confection = confection_df[confection_df[
                                                   confection_type_col] == product_type]\
                                                if confection_type_col and not confection_df.empty else pd.DataFrame()

            # Check if we found any data
            if product_knitting.empty and product_confection.empty:
                return {
                    'product_found': False,
                    'product_type': product_type,
                    'message': f"Намерих продукт '{product_type}', но нямам данни за него."
                }

            # Initialize results dictionary
            results = {
                'product_found': True,
                'product_type': product_type,
                'clients': set(),
                'knitting_data': {},
                'confection_data': {},
                'monthly_data': {},
                'total_ordered': 0,
                'total_knitted': 0,
                'total_confectioned': 0
            }

            # Get clients for this product
            if not product_knitting.empty:
                clients = product_knitting.iloc[:, 0].dropna().unique()
                results['clients'].update([c for c in clients if isinstance(c, str) and c.strip()])

            if not product_confection.empty:
                clients = product_confection.iloc[:, 0].dropna().unique()
                results['clients'].update([c for c in clients if isinstance(c, str) and c.strip()])

            # Get order quantities
            # Try to find order quantity column (usually "Поръчка" or column 2)
            order_col = None
            for i, col in enumerate(knitting_df.columns):
                if isinstance(col, str) and 'поръчка' in col.lower():
                    order_col = col
                    break

            if order_col is None and len(knitting_df.columns) > 2:
                order_col = knitting_df.columns[2]

            if order_col and not product_knitting.empty:
                product_orders = product_knitting[order_col].sum()
                if not pd.isna(product_orders):
                    results['total_ordered'] = product_orders

            # Get knitting and confection quantities
            # Look for specific columns with production data
            knittingCol = None
            confectionCol = None

            # Try to find columns with specific keywords
            for df, col_name, keywords in [
                (knitting_df, 'knittingCol', ['изплетено до момента', 'изплетено', 'изработено']),
                (confection_df, 'confectionCol', ['конфекционирано до момента', 'конфекционирано'])
            ]:
                if df.empty:
                    continue

                for col in df.columns:
                    if isinstance(col, str) and any(keyword in col.lower() for keyword in keywords):
                        locals()[col_name] = col
                        break

            # Get the knitting quantity
            if knittingCol and not product_knitting.empty:
                knitting_qty = product_knitting[knittingCol].sum()
                if not pd.isna(knitting_qty):
                    results['total_knitted'] = knitting_qty

            # Get the confection quantity
            if confectionCol and not product_confection.empty:
                confection_qty = product_confection[confectionCol].sum()
                if not pd.isna(confection_qty):
                    results['total_confectioned'] = confection_qty

            # Get monthly data
            month_cols = ['януари', 'февруари', 'март', 'април', 'май', 'юни',
                          'юли', 'август', 'септември', 'октомври', 'ноември', 'декември']

            for df, data_type in [(product_knitting, 'knitting'), (product_confection, 'confection')]:
                if df.empty:
                    continue

                for month in month_cols:
                    # Try to find the month column
                    month_col = None
                    for col in df.columns:
                        if isinstance(col, str) and month.lower() in col.lower():
                            month_col = col
                            break

                    if month_col:
                        monthly_qty = df[month_col].sum()
                        if not pd.isna(monthly_qty) and monthly_qty > 0:
                            if month not in results['monthly_data']:
                                results['monthly_data'][month] = {}
                            results['monthly_data'][month][data_type] = monthly_qty

            # Get details for each client
            results['client_details'] = {}

            for client in results['clients']:
                client_knitting = product_knitting[
                    product_knitting.iloc[:, 0] == client] if not product_knitting.empty else pd.DataFrame()
                client_confection = product_confection[
                    product_confection.iloc[:, 0] == client] if not product_confection.empty else pd.DataFrame()

                if not client_knitting.empty or not client_confection.empty:
                    client_details = {
                        'ordered': 0,
                        'knitted': 0,
                        'confectioned': 0,
                        'monthly_data': {}
                    }

                    # Get order quantity for this client
                    if order_col and not client_knitting.empty:
                        client_orders = client_knitting[order_col].sum()
                        if not pd.isna(client_orders):
                            client_details['ordered'] = client_orders

                    # Get knitting quantity for this client
                    if knittingCol and not client_knitting.empty:
                        client_knitting_qty = client_knitting[knittingCol].sum()
                        if not pd.isna(client_knitting_qty):
                            client_details['knitted'] = client_knitting_qty

                    # Get confection quantity for this client
                    if confectionCol and not client_confection.empty:
                        client_confection_qty = client_confection[confectionCol].sum()
                        if not pd.isna(client_confection_qty):
                            client_details['confectioned'] = client_confection_qty

                    # Get monthly data for this client
                    for df, data_type in [(client_knitting, 'knitting'), (client_confection, 'confection')]:
                        if df.empty:
                            continue

                        for month in month_cols:
                            # Try to find the month column
                            month_col = None
                            for col in df.columns:
                                if isinstance(col, str) and month.lower() in col.lower():
                                    month_col = col
                                    break

                            if month_col:
                                monthly_qty = df[month_col].sum()
                                if not pd.isna(monthly_qty) and monthly_qty > 0:
                                    if month not in client_details['monthly_data']:
                                        client_details['monthly_data'][month] = {}
                                    client_details['monthly_data'][month][data_type] = monthly_qty

                    results['client_details'][client] = client_details

            return results

        except Exception as e:
            current_app.logger.error(f"Error getting product info: {str(e)}")
            return {
                'product_found': False,
                'error': str(e),
                'message': f"Възникна грешка при извличане на информация за продукт: {str(e)}"
            }

    def generate_response_message(self, intent_type, params, results):
        """Generate a human-readable response in Bulgarian based on analysis results."""
        if 'error' in results:
            return f"Възникна грешка при анализа: {results['error']}"

        messages = []
        # print(results)
        # Generate message based on intent type
        try:
            is_all_products = results['all_products']
        except KeyError:
            is_all_products = False
        if is_all_products:
            messages.append(f"Информация за всички продукти за {results['client_name']}:")
            for product_name in results['all_products']:
                message_string = f'- {product_name} - '
                product_details = results['all_products'][product_name]
                for detail_type, quantity in product_details.items():
                    message_string += f"{detail_type}: {quantity}; "
                messages.append(f'\n{message_string}')

        elif intent_type == 'client':
            # Client information
            if not results.get('client_found', False):
                return results.get('message', 'Не успях да намеря информация за този клиент.')

            client_name = results['client_name']
            messages.append(f"Информация за клиент {client_name}:")

            total_ordered = results.get('total_ordered', 0)
            total_knitted = results.get('total_knitted', 0)
            total_confectioned = results.get('total_confectioned', 0)

            if total_ordered > 0:
                messages.append(f"- Общо поръчани: {total_ordered} бр.")

            messages.append(f"- Общо изплетени: {total_knitted} бр.")
            messages.append(f"- Общо конфекционирани: {total_confectioned} бр.")

            if 'product_types' in results and results['product_types']:
                product_types_str = ', '.join(results['product_types'])
                messages.append(f"- Видове изделия: {product_types_str}")

            # Add monthly data if available
            if 'monthly_data' in results and results['monthly_data']:
                messages.append("\nМесечно разпределение:")

                for month, data in results['monthly_data'].items():
                    month_total = sum(data.values())
                    if month_total > 0:
                        month_details = []
                        if 'knitting' in data and data['knitting'] > 0:
                            month_details.append(f"плетене: {data['knitting']} бр.")
                        if 'confection' in data and data['confection'] > 0:
                            month_details.append(f"конфекция: {data['confection']} бр.")

                        month_info = ", ".join(month_details)
                        messages.append(f"- {month}: {month_info}")

            # Add product details if available
            if 'product_details' in results and results['product_details']:
                messages.append("\nИнформация по видове изделия:")

                for product_type, details in results['product_details'].items():
                    product_total = details.get('ordered', 0)
                    if product_total > 0:
                        messages.append(f"- {product_type}: общо {product_total} бр. "
                                        f"(изплетени: {details.get('knitted', 0)}, "
                                        f"конфекционирани: {details.get('confectioned', 0)})")

        elif intent_type == 'product':
            # Product information
            if not results.get('product_found', False):
                return results.get('message', 'Не успях да намеря информация за този продукт.')

            product_type = results['product_type']
            messages.append(f"Информация за продукт '{product_type}':")

            total_ordered = results.get('total_ordered', 0)
            total_knitted = results.get('total_knitted', 0)
            total_confectioned = results.get('total_confectioned', 0)

            if total_ordered > 0:
                messages.append(f"- Общо поръчани: {total_ordered} бр.")

            messages.append(f"- Общо изплетени: {total_knitted} бр.")
            messages.append(f"- Общо конфекционирани: {total_confectioned} бр.")

            if 'clients' in results and results['clients']:
                num_clients = len(results['clients'])
                clients_str = ', '.join(list(results['clients'])[:5])
                if num_clients > 5:
                    clients_str += f" и още {num_clients - 5}"

                messages.append(f"- Клиенти: {clients_str}")

            # Add monthly data if available
            if 'monthly_data' in results and results['monthly_data']:
                messages.append("\nМесечно разпределение:")

                for month, data in results['monthly_data'].items():
                    month_total = sum(data.values())
                    if month_total > 0:
                        month_details = []
                        if 'knitting' in data and data['knitting'] > 0:
                            month_details.append(f"плетене: {data['knitting']} бр.")
                        if 'confection' in data and data['confection'] > 0:
                            month_details.append(f"конфекция: {data['confection']} бр.")

                        month_info = ", ".join(month_details)
                        messages.append(f"- {month}: {month_info}")

            # Add client details if available
            if 'client_details' in results and results['client_details']:
                messages.append("\nИнформация по клиенти:")

                # Sort clients by total production
                sorted_clients = sorted(
                    results['client_details'].items(),
                    key=lambda x: x[1].get('knitted', 0) + x[1].get('confectioned', 0),
                    reverse=True
                )

                # Show top 5 clients
                for client, details in sorted_clients[:5]:
                    client_total = details.get('knitted', 0) + details.get('confectioned', 0)
                    if client_total > 0:
                        messages.append(f"- {client}: общо {client_total} бр. "
                                        f"(изплетени: {details.get('knitted', 0)}, "
                                        f"конфекционирани: {details.get('confectioned', 0)})")

                if len(sorted_clients) > 5:
                    messages.append(f"...и още {len(sorted_clients) - 5} клиенти")

        elif intent_type == 'summary' or 'date' in params:
            # Daily summary
            date_display = results.get('date_display', 'днес')
            month_name = results.get('month_name', '')

            messages.append(f"Производствена справка за {date_display} (месец {month_name}):")

            knitting_total = results.get('knitting_total', 0)
            confection_total = results.get('confection_total', 0)

            messages.append(f"- Прогнозно дневно количество за плетене: {knitting_total} бр.")
            messages.append(f"- Прогнозно дневно количество за конфекция: {confection_total} бр.")
            messages.append(f"- Общо дневно производство: {knitting_total + confection_total} бр.")

            # Add client information
            if 'clients' in results and results['clients']:
                messages.append("\nАктивни клиенти:")

                # Display top 5 clients
                for i, client in enumerate(results['clients'][:5], 1):
                    client_total = client['total']
                    client_info = []

                    if client['knitting'] > 0:
                        client_info.append(f"плетене: {client['knitting']} бр.")
                    if client['confection'] > 0:
                        client_info.append(f"конфекция: {client['confection']} бр.")

                    client_details = ", ".join(client_info)
                    messages.append(f"{i}. {client['name']}: общо {client_total} бр. ({client_details})")

                if len(results['clients']) > 5:
                    messages.append(f"...и още {len(results['clients']) - 5} клиенти")

            # Add product type information
            if 'product_types' in results and results['product_types']:
                messages.append("\nПродукти в производство:")

                # Display top 5 product types
                for i, product in enumerate(results['product_types'][:5], 1):
                    product_total = product['total']
                    product_info = []

                    if product['knitting'] > 0:
                        product_info.append(f"плетене: {product['knitting']} бр.")
                    if product['confection'] > 0:
                        product_info.append(f"конфекция: {product['confection']} бр.")

                    product_details = ", ".join(product_info)
                    messages.append(f"{i}. {product['type']}: общо {product_total} бр. ({product_details})")

                if len(results['product_types']) > 5:
                    messages.append(f"...и още {len(results['product_types']) - 5} вида продукти")

        # # Add disclaimer about data approximation for daily summary
        # if intent_type == 'summary' or 'date' in params:
        #     messages.append("\nЗабележка: Тъй като данните в таблицата са организирани по месеци, "
        #                     "дневните данни са приблизителни стойности, базирани на месечните данни.")

        # If no messages were generated, return a default message
        if not messages:
            return "Не успях да намеря подходяща информация по вашата заявка. Моля, опитайте с по-конкретен въпрос."

        return "\n".join(messages)

    def get_monthly_data(self, month=None):
        """Get production data for a specific month or all months."""
        try:
            # Start of editing
            # If no month is specified, use the current month
            if month is None:
                current_month = datetime.datetime.now().month
                month = current_month

            # Convert month name to number if needed
            if isinstance(month, str):
                month = self.month_mappings.get(month.lower(), datetime.datetime.now().month)

            # Get the month name for display
            month_name = next((name for name, num in self.month_mappings.items() if num == month), "unknown")

            # Load data from both sheets
            knitting_df = self.clean_dataframe(self.get_sheet_data('pletene'))
            confection_df = self.clean_dataframe(self.get_sheet_data('confekcia'))

            # Find the month column
            month_col_knitting = None
            month_col_confection = None

            for month_name_key in self.month_mappings.keys():
                if self.month_mappings[month_name_key] == month:
                    # Try to find this month in the column names
                    for col in knitting_df.columns:
                        if isinstance(col, str) and month_name_key.lower() in col.lower():
                            month_col_knitting = col
                            break

                    for col in confection_df.columns:
                        if isinstance(col, str) and month_name_key.lower() in col.lower():
                            month_col_confection = col
                            break

            if not month_col_knitting and not month_col_confection:
                # If we couldn't find the month column, use sample data
                return {
                    'date_display': f"{month_name}",
                    'month_name': month_name,
                    'knitting_total': 500,  # Sample value
                    'confection_total': 450,  # Sample value
                    'clients': [
                        {'name': 'Matinique', 'knitting': 200, 'confection': 180, 'total': 380},
                        {'name': 'Lebek', 'knitting': 300, 'confection': 270, 'total': 570}
                    ],
                    'product_types': [
                        {'type': 'пуловер', 'knitting': 250, 'confection': 220, 'total': 470},
                        {'type': 'жилетка', 'knitting': 150, 'confection': 130, 'total': 280},
                        {'type': 'риза', 'knitting': 100, 'confection': 100, 'total': 200}
                    ]
                }

            # Calculate totals for the month
            knitting_total = knitting_df[month_col_knitting].sum() if month_col_knitting else 0
            confection_total = confection_df[month_col_confection].sum() if month_col_confection else 0

            # Get client information
            clients = []
            if month_col_knitting:
                client_col = knitting_df.columns[0]  # Usually the first column is the client name
                for client in knitting_df[client_col].unique():
                    if isinstance(client, str) and client.strip():
                        client_knitting = knitting_df[knitting_df[client_col] == client][month_col_knitting].sum()
                        client_confection = 0

                        if month_col_confection:
                            client_confection_df = confection_df[confection_df[client_col] == client]
                            if not client_confection_df.empty:
                                client_confection = client_confection_df[month_col_confection].sum()

                        clients.append({
                            'name': client,
                            'knitting': client_knitting,
                            'confection': client_confection,
                            'total': client_knitting + client_confection
                        })

            # Get product type information
            product_types = []
            product_col = None

            # Find the product type column (usually with "Вид" in the name or column index 5)
            for col in knitting_df.columns:
                if isinstance(col, str) and 'вид' in col.lower():
                    product_col = col
                    break

            if not product_col and len(knitting_df.columns) > 5:
                product_col = knitting_df.columns[5]

            if product_col and month_col_knitting:
                for product in knitting_df[product_col].unique():
                    if isinstance(product, str) and product.strip():
                        product_knitting = knitting_df[knitting_df[product_col] == product][month_col_knitting].sum()
                        product_confection = 0

                        if month_col_confection:
                            product_confection_df = confection_df[confection_df[product_col] == product]
                            if not product_confection_df.empty:
                                product_confection = product_confection_df[month_col_confection].sum()

                        product_types.append({
                            'type': product,
                            'knitting': product_knitting,
                            'confection': product_confection,
                            'total': product_knitting + product_confection
                        })

            # Sort clients and product types by total
            clients.sort(key=lambda x: x['total'], reverse=True)
            product_types.sort(key=lambda x: x['total'], reverse=True)

            return {
                'date_display': f"{month_name}",
                'month_name': month_name,
                'knitting_total': knitting_total,
                'confection_total': confection_total,
                'clients': clients,
                'product_types': product_types
            }
            # End of editing

        except Exception as e:
            current_app.logger.error(f"Error getting monthly data: {str(e)}")
            return {
                'error': str(e),
                'message': f"Грешка при извличане на месечни данни: {str(e)}"
            }

    def process_query(self, query):
        """
        Process a user query in Bulgarian and return production planning information.

        Args:
            query (str): The user's query in Bulgarian

        Returns:
            dict: A dictionary containing the processing results with the following keys:
                - success (bool): Whether the query was successfully processed
                - intent_type (str): The detected intent type (if successful)
                - params (dict): Extracted parameters from the query (if successful)
                - message (str): A human-readable response message in Bulgarian
        """
        try:
            # Detect the intent and extract parameters
            intent_type, params = self.detect_query_intent(query)

            # Log the detected intent and parameters
            print(f"Detected intent: {intent_type}, params: {params}")

            # Process based on intent type
            results = {}

            if intent_type == 'client':
                # Get client information
                client_query = params.get('client')
                if client_query:
                    results = self.get_client_info(client_query,
                                                   params.get('all_products'),
                                                   params.get('specific_products'))
                else:
                    results = {
                        'client_found': False,
                        'message': "Не разпознах за кой клиент искате информация. Моля уточнете."
                    }

            elif intent_type == 'product':
                # Get product information
                product_query = params.get('product_type')
                if product_query:
                    results = self.get_product_info(product_query)
                else:
                    results = {
                        'product_found': False,
                        'message': "Не разпознах за кой продукт искате информация. Моля уточнете."
                    }

            elif intent_type == 'planning':
                # Get planning information (monthly or yearly)
                month = params.get('month')
                if month:
                    # Monthly planning
                    # This would call a method to get monthly planning data
                    # For now, we'll use a placeholder
                    results = self.get_monthly_data(month)
                    # results = {
                    #     'month_name': list(self.month_mappings.keys())[month - 1] if 1 <= month <= 12 else 'неизвестен',
                    #     'knitting_total': 0,
                    #     'confection_total': 0,
                    #     'clients': [],
                    #     'product_types': [],
                    #     'factories': []
                    # }
                else:
                    # Yearly planning
                    # This would call a method to get yearly planning data
                    # For now, we'll use a placeholder
                    results = {
                        'yearly_knitting': 0,
                        'yearly_confection': 0,
                        'yearly_total': 0,
                        'monthly_totals': {},
                        'clients': [],
                        'product_types': []
                    }

            elif intent_type == 'summary':
                # Get daily summary
                # This would call a method to get daily summary data
                # For now, we'll use a placeholder with the date
                today = params.get('date', 'unknown date')
                current_month = datetime.datetime.now().month
                month_name = list(self.month_mappings.keys())[
                    current_month - 1] if 1 <= current_month <= 12 else 'неизвестен'

                results = {
                    'date_display': 'днес' if today == datetime.date.today().strftime('%Y-%m-%d') else today,
                    'month_name': month_name,
                    'knitting_total': 0,
                    'confection_total': 0,
                    'clients': [],
                    'product_types': []
                }

            # Generate a human-readable response
            response_message = self.generate_response_message(intent_type, params, results)

            return {
                'success': True,
                'intent_type': intent_type,
                'params': params,
                'message': response_message
            }

        except Exception as e:
            import traceback
            print(f"Error processing query: {str(e)}")
            print(traceback.format_exc())
            return {
                'success': False,
                'message': f"Възникна грешка при обработката: {str(e)}"
            }
