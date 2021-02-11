import csv
import os
from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker

engine = create_engine(os.getenv("Heroku_books_url"))
db = scoped_session(sessionmaker(bind=engine))

def main():
    data = open("books.csv")
    reader = csv.reader(data)
    for isbn, title, author, year in reader:
        db.execute("INSERT INTO books (isbn,title,author,year) VALUES (:isbn, :title, :author, :year)",
                    {"isbn": isbn, "title": title, "author":author, "year":year})
        print(f"Added Book {title} by {author}.")
    db.commit()

if __name__ == "__main__":
    main()