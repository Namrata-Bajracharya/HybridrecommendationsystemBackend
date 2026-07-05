import sys, os
sys.path.insert(0, os.path.dirname(__file__))
import uvicorn
uvicorn.run("app.main:socket_app", host="0.0.0.0", port=8000, reload=False)
