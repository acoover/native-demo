import os
import uuid

import requests
from flask import Flask, render_template, request, redirect, url_for, session

app = Flask(__name__)
app.secret_key = 'dev-secret-key'

# configuration for external push user service
PUSH_SERVICE_URL = os.getenv('PUSH_SERVICE_URL', 'http://localhost:8080')
PUSH_API_KEY = os.getenv('PUSH_API_KEY', '')

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

        # register user with external push service
        push_user_id = None
        payload = {
            "name": {"first": first, "last": last},
            "email": email,
            "address": {
                "address_line_1": "1609 10th Ave",
                "locality": "Bodega Bay",
                "administrative_area": "CA",
                "postal_code": "94923",
                "country": "US",
            },
            "date_of_birth": "1899-08-13",
            "government_id": {"type": "passport", "last4": "7349"},
            "phone_number": "(555) 681-3485",
            "tag": str(uuid.uuid4())[:8],
            "identity_verified": True,
        }

        try:
            res = requests.post(
                f"{PUSH_SERVICE_URL}/user",
                headers={
                    "Authorization": f"Bearer {PUSH_API_KEY}",
                    "X-Idempotency-Key": str(uuid.uuid4()),
                },
                json=payload,
                timeout=5,
            )
            res.raise_for_status()
            data = res.json()
            push_user_id = data.get("id")
            if push_user_id:
                app.logger.info("Created user with Push %s", push_user_id)
        except requests.RequestException:
            return (
                render_template(
                    "error.html",
                    message="Failed to register user with push service.",
                ),
                502,
            )

        users[email] = {
            'first': first,
            'last': last,
            'password': password,
            'gold_coins': 0,
            'sweep_coins': 0,
            'push_user_id': push_user_id,
        }
        session['user'] = email
        return redirect(url_for('home'))
    return render_template('signup.html')

if __name__ == '__main__':
    app.run(debug=True, port=8081)

