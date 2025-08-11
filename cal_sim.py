
from functools import lru_cache

import requests

from sqlalchemy.orm import Session
from tqdm import tqdm

from db import SessionLocal, engine
from db.log import get_logger
from db.models import Base, ExtendedInfo, Patent, PatentMatrix


logger = get_logger(__name__)


def get_similarity(sentence1: str, sentence2: str, url: str = "http://wjuru36-service:80/similarity") -> float | None:
    payload = {
        "sentence1": sentence1,
        "sentence2": sentence2,
    }
    headers = {"Content-Type": "application/json"}

    try:
        resp = requests.post(url, json=payload, headers=headers, timeout=5)
        if resp.status_code == 200:
            data = resp.json()
            return float(data.get("similarity", 0.0))
        else:
            logger.error(f"请求失败，状态码: {resp.status_code}, 响应内容: {resp.text}")
            return None
    except requests.RequestException as e:
        logger.error(f"请求异常: {e}")
        return None


def cal_sim(db: Session, batch_size: int):
    @lru_cache(maxsize=204800)
    def get_abstract(patent: str) -> str:
        return db.query(Patent.abstract).filter(Patent.number == patent).scalar() or ""

    p_bar: tqdm = tqdm(desc="计算相似性中")
    offset = 0
    while True:
        info_batch = db.query(ExtendedInfo).offset(offset).limit(batch_size).all()
        if not info_batch:
            break

        for info in info_batch:
            p_bar.update(1)
            # 找到small patent和big patent
            # 先在patentmatrix中找下是否有
            patent_matrix = db.query(PatentMatrix).filter(PatentMatrix.focus_patent == info.publication_number).first()
            focus_patent = info.publication_number
            focus_patent_abs = get_abstract(focus_patent)
            related_patents = set(
                info.b1f0_patents.split(",") + info.b1f1_patents.split(",") + info.b0f1_patents.split(",")
            )
            sim_score = 0

        db.commit()
        offset += batch_size
    p_bar.close()


if __name__ == "__main__":
    Base.metadata.create_all(bind=engine)
    logger.info("开始计算extended_info中每一对关系之间的余弦相似度")
    db: Session = SessionLocal()
    cal_sim(db, batch_size=10000)
    db.close()
    logger.info("计算完成")
