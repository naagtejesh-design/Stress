from flask import Flask, render_template, request, redirect, session, jsonify
import sqlite3
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = "mentalhealthsecret"

# -----------------------------------------------------------
#  CREATE DATABASE (User authentication)
# -----------------------------------------------------------
con = sqlite3.connect("users.db")
con.execute(
    "CREATE TABLE IF NOT EXISTS users(id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT, password TEXT)"
)
con.close()

# -----------------------------------------------------------
#  NUTRITION CALCULATOR FUNCTIONS
# -----------------------------------------------------------
def calculate_macros(calories, weight):
    protein_grams = int(1.5 * weight)
    protein_cals = protein_grams * 4
    fat_cals = int(0.25 * calories)
    fat_grams = fat_cals // 9
    carb_cals = max(0, calories - (protein_cals + fat_cals))
    carb_grams = carb_cals // 4

    return {
        "protein_g": protein_grams,
        "fat_g": fat_grams,
        "carb_g": carb_grams
    }

# -----------------------------------------------------------
#  AUTH + DASHBOARD ROUTES
# -----------------------------------------------------------

@app.route("/")
def home():
    return redirect("/login")

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        con = sqlite3.connect("users.db")
        cur = con.cursor()
        cur.execute("SELECT * FROM users WHERE username=?", (username,))
        user = cur.fetchone()
        con.close()

        if user and check_password_hash(user[2], password):
            session["user_id"] = user[0]
            return redirect("/dashboard")
        else:
            return render_template("login.html", error="Invalid login details")
    return render_template("login.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form["username"]
        password = generate_password_hash(request.form["password"])

        con = sqlite3.connect("users.db")
        con.execute("INSERT INTO users(username, password) VALUES (?,?)", (username, password))
        con.commit()
        con.close()
        return redirect("/login")
    return render_template("register.html")


@app.route("/dashboard")
def dashboard():
    if "user_id" not in session:
        return redirect("/login")
    return render_template("dashboard.html")


# -----------------------------------------------------------
#  QUIZ ROUTES
# -----------------------------------------------------------

@app.route("/questions")
def questions():
    if "user_id" not in session:
        return redirect("/login")
    return render_template("questions.html")


@app.route("/result", methods=["POST"])
def result():
    score = (
        int(request.form["q1"]) +
        int(request.form["q2"]) +
        int(request.form["q3"]) +
        int(request.form["q4"]) +
        int(request.form["q5"])
    )
    return render_template("result.html", score=score)


@app.route("/logout")
def logout():
    session.clear()
    return redirect("/login")


# -----------------------------------------------------------
#  BMI + TDEE + MACROS CALC API (AJAX)
# -----------------------------------------------------------

@app.route("/calculate", methods=["POST"])
def calculate():
    data = request.get_json()
    height = float(data['height'])
    weight = float(data['weight'])
    age = int(data['age'])
    gender = data['gender']
    activity = float(data['activity'])

    bmi = round(weight / ((height / 100) ** 2), 1)

    # BMR
    if gender == 'male':
        bmr = 10 * weight + 6.25 * height - 5 * age + 5
    else:
        bmr = 10 * weight + 6.25 * height - 5 * age - 161

    tdee = int(bmr * activity)

    # BMI goals
    min_bmi = 18.5
    max_bmi = 24.9
    min_weight = min_bmi * ((height / 100) ** 2)
    max_weight = max_bmi * ((height / 100) ** 2)

    if bmi < 18.5:
        category = "Underweight"
        calorie_goal = f"Gain {round(min_weight - weight, 1)} kg to reach healthy BMI"
        goal_calories = tdee + 400
    elif bmi < 25:
        category = "Normal Weight"
        calorie_goal = "Maintain Weight"
        goal_calories = tdee
    elif bmi < 30:
        category = "Overweight"
        calorie_goal = f"Lose {round(weight - max_weight, 1)} kg to reach healthy BMI"
        goal_calories = tdee - 500
    else:
        category = "Obese"
        calorie_goal = f"Lose {round(weight - max_weight, 1)} kg to reach healthy BMI"
        goal_calories = tdee - 600

    goal_calories = max(goal_calories, 1500 if gender == "male" else 1200)

    macros = calculate_macros(goal_calories, weight)

    return jsonify({
        'bmi': bmi,
        'category': category,
        'calories': tdee,
        'goal_calories': goal_calories,
        'calorie_goal': calorie_goal,
        'macros': macros
    })


# -----------------------------------------------------------
#  RUN APP
# -----------------------------------------------------------

if __name__ == "__main__":
    app.run(debug=True)