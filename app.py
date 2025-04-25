import os
import pandas as pd
from flask import Flask, render_template, request, redirect, url_for, flash
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
app.secret_key = os.urandom(24)

login_manager = LoginManager()
login_manager.login_view = "login"
login_manager.init_app(app)

class User(UserMixin):
    def __init__(self, username, email):
        self.id = username
        self.email = email

@login_manager.user_loader
def load_user(user_id):
    return User(user_id, email=None)

server   = os.getenv("AZURE_SQL_SERVER")
database = os.getenv("AZURE_SQL_DB")
username = os.getenv("AZURE_SQL_USER")
password = os.getenv("AZURE_SQL_PASS")
conn_str = (
    f"mssql+pyodbc://{username}:{password}@{server}:1433/{database}"
    "?driver=ODBC+Driver+17+for+SQL+Server"
)
engine = create_engine(conn_str)

def ensure_tables():
    with engine.begin() as conn:
        conn.execute(text("""
        IF NOT EXISTS (SELECT * FROM sys.objects 
                       WHERE object_id=OBJECT_ID(N'[dbo].[Households]') AND type='U')
        BEGIN
          CREATE TABLE dbo.Households (
            HSHD_NUM INT PRIMARY KEY,
            AGE_RANGE VARCHAR(20), INCOME_RANGE VARCHAR(20),
            MARITAL VARCHAR(20), HOMEOWNER VARCHAR(10),
            HH_SIZE INT, CHILDREN INT
          );
        END
        """))
        conn.execute(text("""
        IF NOT EXISTS (SELECT * FROM sys.objects 
                       WHERE object_id=OBJECT_ID(N'[dbo].[Products]') AND type='U')
        BEGIN
          CREATE TABLE dbo.Products (
            PRODUCT_NUM INT PRIMARY KEY,
            DEPARTMENT VARCHAR(50), COMMODITY VARCHAR(50)
          );
        END
        """))
        conn.execute(text("""
        IF NOT EXISTS (SELECT * FROM sys.objects 
                       WHERE object_id=OBJECT_ID(N'[dbo].[Transactions]') AND type='U')
        BEGIN
          CREATE TABLE dbo.Transactions (
            ID INT IDENTITY PRIMARY KEY,
            HSHD_NUM INT, BASKET_NUM INT,
            [PURCHASE_] DATE, PRODUCT_NUM INT,
            SPEND FLOAT, UNITS INT,
            CONSTRAINT FK_Trans_Households FOREIGN KEY(HSHD_NUM) 
              REFERENCES dbo.Households(HSHD_NUM),
            CONSTRAINT FK_Trans_Products FOREIGN KEY(PRODUCT_NUM) 
              REFERENCES dbo.Products(PRODUCT_NUM)
          );
        END
        """))
ensure_tables()

@app.route("/login", methods=["GET","POST"])
def login():
    if request.method == "POST":
        u = request.form.get("username")
        p = request.form.get("password")
        e = request.form.get("email")
        # This will accept any credentials—no check
        print(f"Logging in user={u}, password={p}, email={e}")
        login_user(User(u, e))
        return redirect(url_for("home"))
    return render_template("login.html")

@app.route("/home")
@login_required
def home():
    return render_template("home.html")

@app.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("login"))

@app.route("/")
@login_required
def sample10():
    hshd = 10
    sql = text("""
      SELECT t.HSHD_NUM, t.BASKET_NUM, t.[PURCHASE_] AS PURCHASE_DATE,
             t.PRODUCT_NUM, p.DEPARTMENT, p.COMMODITY
      FROM Transactions t
      JOIN Products p ON t.PRODUCT_NUM = p.PRODUCT_NUM
      WHERE t.HSHD_NUM = :h
      ORDER BY t.HSHD_NUM, t.BASKET_NUM, t.[PURCHASE_], t.PRODUCT_NUM;
    """)
    df = pd.read_sql(sql, engine, params={"h": hshd})
    return render_template("table.html", df=df, title=f"Sample Data Pull for Household {hshd}")

@app.route("/search", methods=["GET","POST"])
@login_required
def search():
    df = None
    if request.method == "POST":
        h = int(request.form.get("hshd_num", 0))
        sql = text("""
          SELECT t.HSHD_NUM, t.BASKET_NUM, t.[PURCHASE_] AS PURCHASE_DATE,
                 t.PRODUCT_NUM, p.DEPARTMENT, p.COMMODITY
          FROM Transactions t
          JOIN Products p ON t.PRODUCT_NUM = p.PRODUCT_NUM
          WHERE t.HSHD_NUM = :h
          ORDER BY t.HSHD_NUM, t.BASKET_NUM, t.[PURCHASE_], t.PRODUCT_NUM;
        """)
        df = pd.read_sql(sql, engine, params={"h": h})
    return render_template("search.html", df=df)

@app.route("/upload", methods=["GET","POST"])
@login_required
def upload():
    if request.method=="POST":
        for filekey, table in [
            ("households","Households"),
            ("products","Products"),
            ("transactions","Transactions")
        ]:
            f = request.files.get(filekey)
            if not f:
                continue

            # read and clean
            df = pd.read_csv(f)
            # drop any stray index column
            if "Unnamed: 0" in df.columns:
                df = df.drop(columns=["Unnamed: 0"])
            # strip whitespace from column names
            df.columns = [c.strip() for c in df.columns]

            # ensure transaction date column matches the table
            if table == "Transactions" and "PURCHASE_" in df.columns:
                df = df.rename(columns={"PURCHASE_": "PURCHASE_"})

            # append into the existing table
            df.to_sql(table, engine, if_exists="append", index=False)

        flash("Data loaded successfully!")
        return redirect(url_for("upload"))

    return render_template("upload.html")

@app.route("/dashboard")
@login_required
def dashboard():
    return render_template("dashboard.html")

if __name__=="__main__":
    app.run(host="0.0.0.0", port=8000, debug=True)
