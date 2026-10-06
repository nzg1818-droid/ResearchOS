import os
import uvicorn
from app.main import create_app

if __name__ == '__main__':
    if not os.getenv('RESEARCHOS_TOKEN'):
        raise SystemExit('Set RESEARCHOS_TOKEN to a random session secret, or launch through Electron.')
    uvicorn.run(create_app(), host='127.0.0.1', port=int(os.getenv('RESEARCHOS_PORT', '8765')), access_log=False)
