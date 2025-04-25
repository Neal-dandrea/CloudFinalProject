from flask import Flask, render_template, request

app = Flask(__name__)

@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
        email = request.form["email"]
        print(f"Received: {username}, {password}, {email}")
        return "Submitted successfully!"
    return render_template("form.html")

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=8000)  