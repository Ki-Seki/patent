import numpy as np
import torch

from fastapi import FastAPI
from pydantic import BaseModel
from transformers import AutoModel  # type: ignore


# 初始化模型
model = AutoModel.from_pretrained("/mnt/public/model/huggingface/jina-embeddings-v3", trust_remote_code=True).cuda()
model.eval()

# 创建 FastAPI 应用
app = FastAPI(title="Sentence Similarity API")


# 请求体
class SimilarityRequest(BaseModel):
    sentence1: str
    sentence2: str


# 计算相似度
def cosine_similarity(vec1, vec2):
    return float(np.dot(vec1, vec2) / (np.linalg.norm(vec1) * np.linalg.norm(vec2)))


@app.post("/similarity")
def get_similarity(req: SimilarityRequest):
    sentences = [req.sentence1, req.sentence2]
    with torch.no_grad():
        embeddings = model.encode(sentences, task="text-matching")
        score = cosine_similarity(embeddings[0], embeddings[1])
    return {"similarity": score}


# 运行命令：
# uvicorn serve_jina_cos:app --host 0.0.0.0 --port 8000
