"""
Convenience entrypoint: `python -m src.main`
(Equivalent to `uvicorn src.api:app --host 0.0.0.0 --port 8000`.)
"""

import uvicorn

from src.config import API_HOST, API_PORT

if __name__ == "__main__":
    uvicorn.run("src.api:app", host=API_HOST, port=API_PORT, reload=True)
