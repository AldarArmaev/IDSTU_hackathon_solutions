import json
import pandas as pd

# Читаем JSON
with open("test_1/01.in", "r", encoding="utf-8") as file:
    data = json.load(file)

# Получаем dataset
dataset = data["dataset"]

# Создаём DataFrame
df = pd.DataFrame(dataset["values"])

# Добавляем timestamps
df.insert(0, "timestamp", pd.to_datetime(dataset["timestamps"]))

print(df)

print()