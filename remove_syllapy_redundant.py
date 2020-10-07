import os
import csv
import syllapy

syllable_file_path = os.path.join(os.path.dirname(__file__), 'nyt_haiku', 'data', 'syllable_counts.csv')
with open(syllable_file_path, newline='') as file:
    reader = csv.reader(file)
    for row in reader:
        if len(row) == 2:
            word = row[0].lower()
            count = int(row[1])
            if count != syllapy.count(word):
                print(f"{word},{count}")
