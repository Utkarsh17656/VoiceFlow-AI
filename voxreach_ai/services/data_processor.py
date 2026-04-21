import pandas as pd
from typing import List
from voxreach_ai.models.customer import Customer
from voxreach_ai.utils.logger import logger
import io

class DataProcessorService:
    @staticmethod
    def parse_csv(file_content: bytes) -> List[Customer]:
        """
        Parses CSV content using Pandas and validates required columns.
        """
        try:
            # Read CSV from bytes
            df = pd.read_csv(io.BytesIO(file_content))
            
            # Normalize column names (lowercase, strip whitespace)
            df.columns = [col.lower().strip() for col in df.columns]
            
            required_columns = ["name", "phone", "interaction_history"]
            missing_columns = [col for col in required_columns if col not in df.columns]
            
            if missing_columns:
                logger.error(f"Missing columns in CSV: {missing_columns}")
                raise ValueError(f"CSV is missing required columns: {', '.join(missing_columns)}")
            
            customers = []
            for _, row in df.iterrows():
                customer = Customer(
                    name=str(row["name"]),
                    phone=str(row["phone"]),
                    interaction_history=str(row["interaction_history"])
                )
                customers.append(customer)
            
            logger.info(f"Successfully parsed {len(customers)} customers from CSV.")
            return customers
            
        except Exception as e:
            logger.error(f"Error parsing CSV: {str(e)}")
            raise ValueError(f"Failed to process CSV file: {str(e)}")

data_processor_service = DataProcessorService()
