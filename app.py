from flask import Flask, render_template, request, redirect, url_for

app = Flask(__name__)

@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
        email = request.form["email"]
        print(f"Received: {username}, {password}, {email}")
        return redirect(url_for("menu"))
    return render_template("form.html")

@app.route("/menu")
def menu():
    return render_template("menu.html")

@app.route("/search", methods=['GET', 'POST'])
def search():
    results = []
    if request.method == 'POST':
        household = request.form.get('household')
        conn = get_connection()
        cursor = conn.cursor()
        query = """
        SELECT
            hh.HSHD_NUM, hh.L, hh.AGE_RANGE, hh.MARITAL,
            hh.INCOME_RANGE, hh.HOMEOWNER, hh.HSHD_COMPOSITION,
            hh.HH_SIZE, hh.CHILDREN,

            t.BASKET_NUM, t.PURCHASE_, t.PRODUCT_NUM, t.SPEND, t.UNITS,
            t.STORE_R, t.WEEK_NUM, t.YEAR,

            p.DEPARTMENT, p.COMMODITY, p.BRAND_TY, p.NATURAL_ORGANIC_FLAG

        FROM households hh
        JOIN transactions t ON hh.HSHD_NUM = t.HSHD_NUM
        JOIN products p ON t.PRODUCT_NUM = p.PRODUCT_NUM
        WHERE hh.HSHD_NUM = ?
        ORDER BY hh.HSHD_NUM, t.BASKET_NUM, t.PURCHASE_, t.PRODUCT_NUM, p.DEPARTMENT, p.COMMODITY
        """

        cursor.execute(query, household)
        results = cursor.fetchall()
        conn.close()
    return render_template('search.html', results=results)

@app.route("/upload", methods=['GET', 'POST'])
def upload():
    if request.method == 'POST':
        dataset = request.form.get('dataset_type')
        file = request.files['file']

        reader = csv.reader(file.stream.read().decode("utf-8").splitlines())
        header = next(reader)

        conn = get_connection()
        cursor = conn.cursor()

        if dataset == 'transactions':
            cursor.execute("DELETE FROM transactions")
            for row in reader:
                cursor.execute("INSERT INTO transactions VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)", row)
        elif dataset == 'households':
            cursor.execute("DELETE FROM households")
            for row in reader:
                cursor.execute("INSERT INTO households VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)", row)
        elif dataset == 'products':
            cursor.execute("DELETE FROM products")
            for row in reader:
                cursor.execute("INSERT INTO products VALUES (?, ?, ?, ?, ?)", row)
        
        conn.commit()
        conn.close()
        return redirect(url_for('search'))
    return render_template('upload.html')

@app.route("/dashboard")
def dashboard():
    return render_template('dashboard.html')

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=8000)  