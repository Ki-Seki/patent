from functools import lru_cache

import requests

from sqlalchemy import tuple_
from sqlalchemy.orm import Session
from tenacity import retry, stop_after_attempt
from tqdm import tqdm

from db import SessionLocal, engine
from db.log import get_logger
from db.models import Base, ExtendedInfo, Patent, PatentMatrix


logger = get_logger(__name__)


@retry(stop=stop_after_attempt(3))
def get_similarity(
    sentence1: str, sentence2: str, url: str = "http://if-dbepe3l7zwjuru36-service:80/similarity"
) -> float:
    payload = {
        "sentence1": sentence1,
        "sentence2": sentence2,
    }
    headers = {"Content-Type": "application/json"}

    resp = requests.post(url, json=payload, headers=headers, timeout=5)
    if resp.status_code == 200:
        data = resp.json()
        return data["similarity"]
    else:
        raise ValueError(f"请求失败，状态码: {resp.status_code}, 响应内容: {resp.text}")


def cal_sim(db: Session, batch_size: int):
    @lru_cache(maxsize=204800)
    def get_abstract(patent: str) -> str:
        return db.query(Patent.abstract).filter(Patent.publication_number == patent).scalar() or ""

    p_bar: tqdm = tqdm(desc="计算相似性中")
    offset = 0
    while True:
        # 1. 得到当前批次的patents的扩展信息
        info_batch = db.query(ExtendedInfo).offset(offset).limit(batch_size).all()
        if not info_batch:
            break

        # 2. 收集本批次所有的专利 pairs
        pairs_to_check = set()
        for info in info_batch:
            focus_patent = info.publication_number
            related_patents = {
                p.strip()
                for group in (info.b1f0_patents, info.b1f1_patents, info.b0f1_patents)
                if group
                for p in group.split(",")
                if p.strip()
            }
            for related_patent in related_patents:
                # 找到small patent和big patent
                small_patent, big_patent = sorted([focus_patent, related_patent])
                pairs_to_check.add((small_patent, big_patent))

        # 3. 批量查出已存在数据库中的 pairs
        existing_pairs = set(
            db.query(PatentMatrix.small_patent, PatentMatrix.big_patent)
            .filter(tuple_(PatentMatrix.small_patent, PatentMatrix.big_patent).in_(pairs_to_check))
            .all()
        )

        # 4. 只保留不存在的 pairs
        new_pairs = pairs_to_check - existing_pairs  # type: ignore

        # 5. 计算相似度并插入
        for small_patent, big_patent in new_pairs:
            try:
                sim_score = get_similarity(get_abstract(small_patent), get_abstract(big_patent))
                db.add(PatentMatrix(small_patent=small_patent, big_patent=big_patent, similarity=sim_score))
            except Exception as e:
                logger.error(f"计算相似度失败: {small_patent} - {big_patent}, 错误信息: {e}")
            p_bar.update(1)

        # 6. 提交到数据库并记录日志
        db.commit()
        offset += batch_size
        logger.info(f"已处理 {offset} 条记录，当前批次大小: {len(info_batch)}，当前批次新建配对数量: {len(new_pairs)}")
    p_bar.close()


if __name__ == "__main__":
    Base.metadata.create_all(bind=engine)
    logger.info("开始计算extended_info中每一对关系之间的余弦相似度")
    db: Session = SessionLocal()
    cal_sim(db, batch_size=1000)
    db.close()
    logger.info("计算完成")
