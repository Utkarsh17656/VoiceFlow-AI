import os
from twilio.rest import Client

sid = os.getenv("TWILIO_ACCOUNT_SID")
auth = os.getenv("TWILIO_AUTH_TOKEN")

try:
    client = Client(sid, auth)
    # verify auth by hitting the api
    account = client.api.accounts(sid).fetch()
    print("SUCCESS: Credentials are valid. Status:", account.status)
except Exception as e:
    print("FAILED: Error validating credentials.")
    print(str(e))
