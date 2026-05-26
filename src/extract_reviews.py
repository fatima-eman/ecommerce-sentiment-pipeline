import csv
import os

def get_pending_books(queue_file):
    pending_books = []
    if not os.path.exists(queue_file):
        print(f"Error: {queue_file} not found. Run Phase 1 first!")
        return pending_books

    with open(queue_file, mode="r", encoding="utf-8") as file:
        reader = csv.DictReader(file)
        for row in reader:
            if row["Status"] == "pending":
                pending_books.append(row)
                
    return pending_books

# Quick verification test
if __name__ == "__main__":
    queue = get_pending_books("books_queue.csv")
    print(f"Loaded {len(queue)} books ready for review extraction.")