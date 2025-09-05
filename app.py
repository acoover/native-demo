import os
import uuid

import requests
from dotenv import load_dotenv
from flask import Flask, render_template, request, redirect, url_for, session, jsonify


load_dotenv()

app = Flask(__name__)
app.secret_key = 'dev-secret-key'

# configuration for external push user service
PUSH_SERVICE_URL = os.getenv('PUSH_SERVICE_URL', 'http://localhost:8080')
PUSH_API_KEY = os.getenv('PUSH_API_KEY', '')

# conversion rate of gold coins to USD
GOLD_TO_USD = 1.0

# in-memory storage of users
# each user record stores first name, last name, password
# and coin balances for gold and sweep coins
users = {}
# store purchases waiting on auth intent completion
pending_intents = {}

@app.route('/')
def home():
    user = session.get('user')
    if user and user not in users:
        session.pop('user', None)
        user = None
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
            app.logger.debug(f"Registering user with Push service: {payload}")
            res = requests.post(
                f"{PUSH_SERVICE_URL}/user",
                headers={
                    "Authorization": f"Bearer {PUSH_API_KEY}",
                    "X-Idempotency-Key": str(uuid.uuid4()),
                },
                json=payload,
                timeout=5,
            )
            app.logger.debug(f"Push registration response status: {res.status_code}")
            app.logger.debug(f"Push registration response content: {res.content}")
            res.raise_for_status()
            data = res.json()
            app.logger.debug(f"Push registration response data: {data}")
            push_user_id = data.get("id")
            if push_user_id:
                app.logger.info("Registered user with Push %s", push_user_id)
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

@app.route('/widget_url', methods=['POST'])
def widget_url():
    """Generate a PushCash widget URL for the logged in user."""
    user_email = session.get('user')
    if not user_email:
        return jsonify({'error': 'not logged in'}), 401

    user = users.get(user_email)
    push_user_id = user.get('push_user_id') if user else None
    if not push_user_id:
        return jsonify({'error': 'missing push user id'}), 400

    data = request.get_json(force=True)
    direction = data.get('direction')
    if not direction or direction not in ['cash_in', 'cash_out']:
        return jsonify({'error': 'missing or invalid direction parameter'}), 400

    payload = {
        'direction': direction
    }
    
    widget_type = data.get('type')
    if widget_type:
        payload['type'] = widget_type

    try:
        app.logger.debug(f"Requesting widget URL for user {push_user_id} with direction {direction}")
        res = requests.post(
            f"{PUSH_SERVICE_URL}/user/{push_user_id}/url",
            headers={"Authorization": f"Bearer {PUSH_API_KEY}"},
            json=payload,
            timeout=5,
        )
        app.logger.debug(f"Widget URL response status: {res.status_code}")
        app.logger.debug(f"Widget URL response content: {res.content}")
        res.raise_for_status()
        data = res.json()
        app.logger.debug(f"Widget URL response data: {data}")
        app.logger.info("Generated widget URL from Push API")
        return jsonify({'url': data.get('url')})
    except requests.RequestException as e:
        app.logger.error(f"Failed to generate widget URL: {str(e)}")
        return jsonify({'error': 'failed to generate widget url'}), 502


@app.route('/purchase', methods=['POST'])
def purchase():
    """Authorize payment token and update user balance."""
    user_email = session.get('user')
    if not user_email:
        return jsonify({'error': 'not logged in'}), 401

    user = users.get(user_email)
    if not user:
        return jsonify({'error': 'user not found'}), 404

    data = request.get_json(force=True)
    token = data.get('token')
    amount = data.get('amount')  # dollars
    sweeps = data.get('sweeps')
    gold = data.get('gold')
    if not token or amount is None:
        return jsonify({'error': 'missing params'}), 400

    payload = {
        'amount': int(round(float(amount) * 100)),
        'currency': 'USD',
        'direction': 'cash_in',
        'token': token,
    }

    try:
        app.logger.info("Authorizing payment")
        app.logger.debug(f"Payment payload: {payload}")
        res = requests.post(
            f"{PUSH_SERVICE_URL}/authorize",
            headers={"Authorization": f"Bearer {PUSH_API_KEY}"},
            json=payload,
            timeout=5,
        )
        app.logger.debug(f"Payment response status: {res.status_code}")
        app.logger.debug(f"Payment response content: {res.content}")
        resp_data = res.json() if res.content else {}
        app.logger.debug(f"Payment response data: {resp_data}")
    except requests.RequestException as e:
        app.logger.error(f"Payment authorization failed: {str(e)}")
        return jsonify({'error': 'authorization request failed'}), 502

    if res.status_code == 200:
        if sweeps:
            user['sweep_coins'] += int(sweeps)
        if gold:
            user['gold_coins'] += int(gold)
        return jsonify({
            'id': resp_data.get('id'),
            'gold_coins': user['gold_coins'],
            'sweep_coins': user['sweep_coins'],
        })
    elif res.status_code == 202:
        intent_id = resp_data.get('id')
        if intent_id:
            pending_intents[intent_id] = {
                'user': user_email,
                'sweeps': int(sweeps or 0),
                'gold': int(gold or 0),
            }
        else:
            return jsonify({'error': 'missing intent id'}), 400
        return jsonify({'url': resp_data.get('url'), 'intent_id': intent_id}), 202
    else:
        return jsonify({'status': 'declined'}), 401


@app.route('/redeem', methods=['POST'])
def redeem():
    """Redeem gold coins for cash_out using Push"""
    user_email = session.get('user')
    if not user_email:
        return jsonify({'error': 'not logged in'}), 401

    user = users.get(user_email)
    if not user:
        return jsonify({'error': 'user not found'}), 404

    data = request.get_json(force=True)
    token = data.get('token')
    gold = data.get('gold')
    if not token or gold is None:
        return jsonify({'error': 'missing params'}), 400

    gold = int(gold)
    if gold <= 0 or gold > user['gold_coins']:
        return jsonify({'error': 'invalid amount'}), 400

    payload = {
        'amount': int(round(gold * GOLD_TO_USD * 100)),
        'currency': 'USD',
        'direction': 'cash_out',
        'token': token,
    }

    try:
        app.logger.info("Authorizing redemption")
        app.logger.debug(f"Redemption payload: {payload}")
        res = requests.post(
            f"{PUSH_SERVICE_URL}/authorize",
            headers={"Authorization": f"Bearer {PUSH_API_KEY}"},
            json=payload,
            timeout=5,
        )
        app.logger.debug(f"Redemption response status: {res.status_code}")
        app.logger.debug(f"Redemption response content: {res.content}")
        resp_data = res.json() if res.content else {}
        app.logger.debug(f"Redemption response data: {resp_data}")
    except requests.RequestException as e:
        app.logger.error(f"Redemption request failed: {str(e)}")
        return jsonify({'error': 'authorization request failed'}), 502

    if res.status_code == 200:
        user['gold_coins'] -= gold
        return jsonify({
            'id': resp_data.get('id'),
            'gold_coins': user['gold_coins'],
            'sweep_coins': user['sweep_coins'],
        })
    elif res.status_code == 202:
        intent_id = resp_data.get('id')
        if intent_id:
            pending_intents[intent_id] = {
                'user': user_email,
                'sweeps': 0,
                'gold': -gold,
            }
        else:
            return jsonify({'error': 'missing intent id'}), 400
        return jsonify({'url': resp_data.get('url'), 'intent_id': intent_id}), 202
    else:
        return jsonify({'status': 'declined'}), 401


@app.route('/intent/<intent_id>')
def intent_status(intent_id):
    """Check status of an authorization intent and update balance if approved."""
    info = pending_intents.get(intent_id)
    if not info:
        return jsonify({'error': 'unknown intent'}), 404
    try:
        app.logger.info(f"Fetching status for intent {intent_id}")
        res = requests.get(
            f"{PUSH_SERVICE_URL}/intent/{intent_id}",
            headers={"Authorization": f"Bearer {PUSH_API_KEY}"},
            timeout=5,
        )
        app.logger.debug(f"Intent status response: {res.status_code}")
        res.raise_for_status()
        data = res.json()
        app.logger.debug(f"Intent status data: {data}")
    except requests.RequestException as e:
        app.logger.error(f"Failed to fetch intent status: {str(e)}")
        return jsonify({'error': 'failed to fetch intent status'}), 502

    status = data.get('status')
    user = users.get(info['user'])
    if status == 'approved' and user:
        user['sweep_coins'] += info['sweeps']
        user['gold_coins'] += info['gold']
        pending_intents.pop(intent_id, None)
        return jsonify({
            'status': 'approved',
            'gold_coins': user['gold_coins'],
            'sweep_coins': user['sweep_coins'],
        })

    if status in ['declined', 'canceled']:
        pending_intents.pop(intent_id, None)
        return jsonify({'status': 'declined'})

    # pending
    return jsonify({'status': 'pending'})


@app.route('/debug')
def debug_view():
    """Display current in-memory database contents for debugging."""
    return render_template('debug.html', users=users, pending_intents=pending_intents)

if __name__ == '__main__':
    app.run(debug=True, port=8081)

