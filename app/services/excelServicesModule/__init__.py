import os
import pandas as pd
from flask import current_app
import re
import datetime
from datetime import date, timedelta
import calendar
import numpy as np


class DataProcessor:
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
            'summary': ['обобщение', 'резюме', 'справка', 'информация', 'статистика', 'данни', 'покажи'],
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
