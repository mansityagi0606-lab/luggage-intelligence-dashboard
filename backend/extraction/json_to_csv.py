import pandas as pd
import json
import glob
import os

# 📌 Get current file directory
current_dir = os.path.dirname(os.path.abspath(__file__))

# 📌 Navigate to project root → then to data/raw
project_root = os.path.abspath(os.path.join(current_dir, "../../"))
json_folder = os.path.join(project_root, "data", "raw")

# Get all JSON files
files = glob.glob(os.path.join(json_folder, "*.json"))

all_products = []

for file in files:
    with open(file, "r", encoding="utf-8") as f:
        data = json.load(f)

        brand = data.get("brand")

        for product in data.get("products", []):
            product["brand"] = brand
            all_products.append(product)

# Convert to DataFrame
df = pd.DataFrame(all_products)

# Optional: drop unwanted column
if "reviews" in df.columns:
    df = df.drop(columns=["reviews"])

# 📌 Save CSV inside data/cleaned folder
output_folder = os.path.join(project_root, "data", "cleaned")

# Create folder if not exists
os.makedirs(output_folder, exist_ok=True)

output_path = os.path.join(output_folder, "combined_products.csv")

df.to_csv(output_path, index=False)

print("✅ All JSON files converted and merged into CSV!")
print(f"📁 File saved at: {output_path}")