from flask import Flask, render_template, request, redirect, url_for, session

app = Flask(__name__)
app.secret_key = 'dev-secret-key'

# in-memory storage of users
# each user record stores first name, last name, password
# and coin balances for gold and sweep coins
users = {}

@app.route('/')
def home():
    user = session.get('user')
    return render_template('home.html', user=user, users=users)

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        first = request.form['first_name']
        last = request.form['last_name']
        email = request.form['email']
        password = request.form['password']
        users[email] = {
            'first': first,
            'last': last,
            'password': password,
            'gold_coins': 0,
            'sweep_coins': 0,
        }
        session['user'] = email
        return redirect(url_for('home'))
    return render_template('signup.html')

if __name__ == '__main__':
    app.run(debug=True)

