# Native Demo

A minimal Flask webapp demonstrating the Push Native [integration](https://docs.pushcash.com/integration) on a demo Social Sweeps application.

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
