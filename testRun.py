#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Test script for the Production Planning Processor.
"""

import os
import sys
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

# Ensure the script can find the application modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

try:
    # Import the processor
    from app.services.excelServices import ProductionPlanningProcessor

    # Create a processor instance
    processor = ProductionPlanningProcessor()

    # Define test queries in Bulgarian
    test_queries = [
        # Daily summary
        "Покажи ми обобщение на производството за днес",

        # Client information
        "клиент Robert Todd",

        # Client information
        "клиент Rue De Tokio",

        # Product information
        "Покажи данни за жилетки",

        # Monthly planning
        "Какъв е планът за производство за месец февруари",

        # Yearly planning
        "Направи годишна справка за производството"
    ]

    # Process each test query
    for i, query in enumerate(test_queries, 1):
        logger.info(f"\n--- Test Query {i}: {query} ---")

        # Process the query
        result = processor.process_query(query)

        # Display the results
        if result['success']:
            logger.info(f"Detected intent: {result['intent_type']}")
            logger.info(f"Parameters: {result['params']}")
            logger.info("Response message:")
            print("\n" + result['message'] + "\n")
        else:
            logger.error(f"Error: {result['message']}")

    logger.info("All tests completed!")

except Exception as e:
    logger.error(f"Error running tests: {str(e)}")

if __name__ == "__main__":
    # Script was run directly
    pass
