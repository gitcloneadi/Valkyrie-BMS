import pandas as pd
import os
import re
from tqdm import tqdm 

# --- CONFIG ---
DATA_FOLDER = "./data"  # Path where 00001.csv to 07565.csv live
OUTPUT_FILE = 'nasa_battery_master_cleaned.csv'

def natural_sort_key(s):
    """Ensures 1.csv comes before 10.csv."""
    return [int(text) if text.isdigit() else text.lower() for text in re.split('([0-9]+)', s)]

def consolidate_datasets():
    # 1. Get and sort all CSV files
    all_files = [f for f in os.listdir(DATA_FOLDER) if f.endswith('.csv')]
    all_files.sort(key=natural_sort_key)
    
    combined_data = []
    print(f"Refining {len(all_files)} files...")

    for file_name in tqdm(all_files):
        file_path = os.path.join(DATA_FOLDER, file_name)
        
        try:
            df = pd.read_csv(file_path)
            
            # Skip empty files or Impedance files (like 00002.csv) if they don't have Time
            if 'Time' not in df.columns:
                continue
                
            # 2. SCHEMA ALIGNMENT
            # Create a universal 'External_Current' and 'External_Voltage' 
            # by merging Charge and Load columns
            if 'Current_load' in df.columns:
                df['external_current'] = df['Current_load']
                df['external_voltage'] = df['Voltage_load']
                df['mode'] = 'discharge'
            elif 'Current_charge' in df.columns:
                df['external_current'] = df['Current_charge']
                df['external_voltage'] = df['Voltage_charge']
                df['mode'] = 'charge'
            else:
                df['mode'] = 'unknown'

            # 3. ADD METADATA
            # Extract the number from the filename as the unique cycle ID
            df['cycle_id'] = int(re.findall(r'\d+', file_name)[0])
            
            # Keep only the essential columns for the Digital Twin
            essential_cols = [
                'cycle_id', 'Time', 'mode', 
                'Voltage_measured', 'Current_measured', 'Temperature_measured',
                'external_current', 'external_voltage'
            ]
            
            # Filter and append
            combined_data.append(df[essential_cols])
            
        except Exception as e:
            print(f"Skipping {file_name} due to error: {e}")

    # 4. CONCATENATE & EXPORT
    print("Finalizing master dataset...")
    master_df = pd.concat(combined_data, ignore_index=True)
    
    # Optional: Cast types to save space (float32 is enough for battery HIL)
    float_cols = master_df.select_dtypes(include=['float64']).columns
    master_df[float_cols] = master_df[float_cols].astype('float32')

    master_df.to_csv(OUTPUT_FILE, index=False)
    print(f"Success! Cleaned dataset saved as: {OUTPUT_FILE}")
    print(f"Total Rows: {len(master_df)}")

if __name__ == "__main__":
    consolidate_datasets()