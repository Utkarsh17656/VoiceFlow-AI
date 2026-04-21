import sys
import os

# Add the project root to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from voxreach_ai.services.data_processor import data_processor_service

def test_data_processor():
    csv_path = "voxreach_ai/sample_customers.csv"
    with open(csv_path, "rb") as f:
        content = f.read()
    
    customers = data_processor_service.parse_csv(content)
    print(f"Successfully parsed {len(customers)} customers.")
    for c in customers:
        print(f"Name: {c.name}, Phone: {c.phone}")

if __name__ == "__main__":
    test_data_processor()
