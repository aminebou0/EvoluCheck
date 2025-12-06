import requests

url = 'http://127.0.0.1:5000/import_csv'
files = {'file': open('test_data.csv', 'rb')}
# Need to handle session/cookies if auth is required.
# But /import_csv redirects to /audit if file missing, or /dashboard if success.
# Wait, /audit requires auth?
# @app.route('/audit', methods=['GET', 'POST'])
# def audit():
#    if 'user' not in session: return redirect(url_for('auth'))

# So I need to authenticate first.

session = requests.Session()
# Login
auth_url = 'http://127.0.0.1:5000/auth'
session.post(auth_url, data={'action': 'login', 'email': 'test@test.com'})

# Now try import
response = session.post(url, files=files)

print(f"Status Code: {response.status_code}")
print(f"URL: {response.url}")
if 'dashboard' in response.url:
    print("✅ Redirected to Dashboard (Success)")
elif 'audit' in response.url:
    print("❌ Redirected to Audit (Failure)")
else:
    print(f"❓ Redirected to: {response.url}")

print("Response Text (first 500 chars):")
print(response.text[:500])
