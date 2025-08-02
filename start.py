import webbrowser
import time
from app import app

time.sleep(1)
webbrowser.open("http://127.0.0.1:5000")
app.run(debug=False)