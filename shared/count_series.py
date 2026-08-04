import pandas as pd

df = pd.read_csv("/data/alessia.gerbasi/AI4Quality/_00_Preprocessing/OUTPUTS/retained_series_unified_filtered.csv")  
# count unique patients names
unique_patients_count = df['ct_name'].nunique()
# count all series
total_series_count = len(df)

# Print the counts
print(f"Unique patients count: {unique_patients_count}")
print(f"Total series count: {total_series_count}")