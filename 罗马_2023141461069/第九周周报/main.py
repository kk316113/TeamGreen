import uvicorn
import logging
from api import app

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger("B3")

if __name__ == "__main__":
    logger.info("启动 AutoGrader B-3 沙盒安全中间件及测评API，文档: http://localhost:8000/docs")
    uvicorn.run(app, host="0.0.0.0", port=8000)