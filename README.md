# Native Demo

A minimal Flask webapp demonstrating a signup flow and simple homepage.

The home page shows a fake coin balance for each user and a button to
"Purchase Coins" which opens a modal displaying example coin packages.
If you are not logged in, the home page will prompt you to sign up instead
of displaying the game grid.

## Running

Install requirements for python using pip
```bash
pip install -r requirements.txt
```

Create a `.env` file with the URL and API key for Push Cash sandbox
```
PUSH_SERVICE_URL=https://sandbox.pushcash.com
PUSH_API_KEY=<your api key>
```

Then visit `http://127.0.0.1:8081/` to signup and perform test payments.

- Use `5555 5555 5555 4444` for your test-card credentials
- Use `mxuser` and `password` to complete bank authentication

## Debugging

A simple debug view is available at `http://localhost:8081/debug` which displays the current contents of the in-memory database
