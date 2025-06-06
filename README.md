# Native Demo

A minimal Flask webapp demonstrating a signup flow and simple homepage.

The home page shows a fake coin balance for each user and a button to
"Purchase Coins" which opens a modal displaying example coin packages.
If you are not logged in, the home page will prompt you to sign up instead
of displaying the game grid.

## Running

```bash
pip install -r requirements.txt
python app.py
```

Set the following environment variables to configure the push user service:

```
export PUSH_SERVICE_URL=http://localhost:8080  # default if unset
export PUSH_API_KEY=<your api key>
```

If the push service request fails during signup, an error page will be
displayed.

Then visit `http://localhost:5000/signup` to create a user profile.
