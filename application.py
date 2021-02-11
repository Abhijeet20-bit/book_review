import os
import json,requests
from flask import Flask, session, render_template, request, redirect, jsonify
from flask_session import Session
from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker

app = Flask(__name__)
#creating a key to be stored in browser cookies as well as in the server
app.secret_key = os.urandom(24)
# Check for environment variable
if not os.getenv("Heroku_books_url"):
    raise RuntimeError("DATABASE_URL is not set")

# Configure session to use filesystem
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)


# Set up database
engine = create_engine(os.getenv("Heroku_books_url"))
db = scoped_session(sessionmaker(bind=engine))


@app.route("/")
def login():
    if session.get("username") is None:
        return render_template("login.html")
    else:
        return redirect("/home")
        
@app.route("/registration")
def register():
    return render_template("register.html")

@app.route("/home",methods=["POST","GET"])
def home():
    if request.method == "GET":
        if session.get("username") is None:
            return redirect("/")
        else:
            books = db.execute("SELECT isbn, title, author, year FROM books").fetchall()
            #print(books)
            return render_template("home.html",books=books)
    elif request.method == "POST":
        return render_template("home.html")
       

@app.route("/login-verification",methods=["post"])
def verify():
    username = request.form.get("username")
    password = request.form.get("password")
    session["username"] = []
    #checking if user exist or not
    if db.execute("SELECT * FROM users WHERE username = :user",{"user": username}).rowcount == 1:
        if db.execute("SELECT * FROM users WHERE username = :user AND password = :pass",{"user": username, "pass": password}).rowcount==1:
            session["username"].append(username)
            return redirect("/home")
        else:
            return render_template("log-error.html",message="Wrong password")
    else:
        return render_template("log-error.html",message="Username doesnot exist")

@app.route("/user-added",methods=["POST"])
def addeduser():
    username = request.form.get("user_name")
    firstname = request.form.get("firstname")
    lastname = request.form.get("lastname")
    password = request.form.get("password1")
    confirm_password = request.form.get("confirmpassword")
    #checking if password = confirm password
    if password == confirm_password:
        #checking if username already exist or not
        if db.execute("SELECT * FROM users WHERE username = :user",{"user": username}).rowcount != 0:
            return render_template("reg-error.html",message="Username already exist!!!")
        db.execute("INSERT INTO users (username,firstname,lastname,password) VALUES (:user,:fn,:ln,:pass)",
                {"user": username, "fn": firstname, "ln": lastname, "pass": password})
        db.commit()
        return render_template("useradded.html")
    else:
        return render_template("reg-error.html",message="Confirm Password doesn't matched Password!!")

@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")

@app.route("/search",methods=["GET"])
def search():
    if request.method == "GET":
        if session.get("username") is None:
            return render_template("log-error.html",message="You Need to login to access this page!!!")
        data = request.args.get("text")
        if not data:
            return redirect("/home")
        query = "%" + data + "%"
        rows = db.execute("SELECT isbn, title, author, year FROM books WHERE isbn LIKE :query OR title LIKE :query OR author LIKE :query LIMIT 15",{"query": query})
        output = rows.fetchall()
        length = rows.rowcount
        return render_template("search-none.html",books=output,length=length,data=data)

@app.route("/book/<isbn>",methods=["POST","GET"])
def final(isbn):
    user = session["username"]
    session["review"] = []

    #checking if user loged in or not
    if user is None:
        return render_template("log-error.html",message="Please Login to continue!!!")
    #taking user feedback
    rows = db.execute("SELECT * from reviews WHERE isbn=:isbn AND username=:username", {"isbn" :isbn,"username" :user[0]}).fetchall()
    if not rows and request.method == "POST":
        feedback=request.form.get('feedback')
        rating=request.form.get('rating')
        username=session["username"]
        db.execute("INSERT INTO reviews (isbn,feedback,rating,username) VALUES (:isbn,:feedback,:rating,:username)",
                {"isbn": isbn,"feedback": feedback,"rating": rating, "username": user[0]})
        db.commit()
    elif rows and request.method == "POST":
        return render_template("error.html", message="you have already submitted a review")

    #making api request to goodreads
    res = requests.get("https://www.goodreads.com/book/review_counts.json", params={"key": "XjytnMTBuDsGMM2lWu33w", "isbns": isbn})
    res = res.json()
    avg_rating= res['books'][0]['average_rating']
    rate_count = res['books'][0]['work_ratings_count']

    reviews = db.execute("SELECT * from reviews WHERE isbn=:isbn", {"isbn" :isbn}).fetchall()
    for comment in reviews:
        session["review"].append(comment)

    data = db.execute("SELECT * FROM books WHERE isbn = :isbn",{"isbn": isbn})
    data = data.fetchone()

    
    length=len(session["review"])
    return render_template("final.html",data=data,avg_rating=avg_rating,rate_count=rate_count,reviews=session["review"],size=length)

@app.route("/api/<isbn>")
def api(isbn):
    data = db.execute("SELECT * from books WHERE isbn=:isbn",{"isbn":isbn}).fetchone()
    if not data:
	    return jsonify({"Error": "Invalid ISBN"}),422
    result = dict(data.items())
    return jsonify(result)
