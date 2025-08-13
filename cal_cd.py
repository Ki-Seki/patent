import argparse

from functools import lru_cache

import requests

from sqlalchemy.orm import Session
from tenacity import retry, stop_after_attempt
from tqdm import tqdm

from db import SessionLocal, engine
from db.log import get_logger
from db.models import Base, CDIndex, ExtendedInfo, Patent


logger = get_logger(__name__)


def count(patents: str) -> int:
    return len([p for p in patents.split(",") if p.strip()]) if patents else 0

@lru_cache(maxsize=10240)
@retry(stop=stop_after_attempt(5))
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


def cal_cd_t(db: Session, info: ExtendedInfo) -> float | None:
    def sub_formula(b: int, f: int, w: int = 1) -> float:
        return (-2 * f * b + f) / w

    len_b1f0, len_b1f1, len_b0f1 = count(info.b1f0_patents), count(info.b1f1_patents), count(info.b0f1_patents)  # type: ignore
    cd = len_b1f0 * sub_formula(1, 0) + len_b1f1 * sub_formula(1, 1) + len_b0f1 * sub_formula(0, 1)
    if len_b1f0 + len_b1f1 + len_b0f1 != 0:
        return cd / (len_b1f0 + len_b1f1 + len_b0f1)
    else:
        return None


def cal_cd_f_t(db: Session, info: ExtendedInfo) -> float | None:
    def sub_formula(b: int, f: int, w: int = 1) -> float:
        return (f * (-f * b + 2 * f) - 1) / w

    len_b1f0, len_b1f1, len_b0f1 = count(info.b1f0_patents), count(info.b1f1_patents), count(info.b0f1_patents)  # type: ignore
    cd = len_b1f0 * sub_formula(1, 0) + len_b1f1 * sub_formula(1, 1) + len_b0f1 * sub_formula(0, 1)
    if len_b1f0 + len_b1f1 + len_b0f1 != 0:
        return cd / (len_b1f0 + len_b1f1 + len_b0f1)
    else:
        return None


def cal_cd_f2_t(db: Session, info: ExtendedInfo) -> float | None:
    def sub_formula(b: int, f: int, w: int = 1) -> float:
        return (f * (-f * b + 2 * f) - 1) / w

    len_b1f0, len_b1f1, len_b0f1 = count(info.b1f0_patents), count(info.b1f1_patents), count(info.b0f1_patents)  # type: ignore
    cd = len_b1f0 * sub_formula(1, 0) + len_b1f1 * sub_formula(1, 1) + len_b0f1 * sub_formula(0, 1)
    if len_b1f0 + len_b1f1 + len_b0f1 != 0:
        return cd / (len_b1f0 + len_b1f1 + len_b0f1) * (len_b1f1 + len_b0f1)
    else:
        return None


def cal_cd_f3_t(db: Session, info: ExtendedInfo) -> float | None:
    def get_abstract(patent: str) -> str:
        return db.query(Patent.abstract).filter(Patent.publication_number == patent).scalar() or ""

    focus_patent = info.publication_number
    forward_patents = {
        p.strip() for group in (info.b1f1_patents, info.b0f1_patents) if group for p in group.split(",") if p.strip()
    }

    cos_similarity = []
    for forward_patent in forward_patents:
        small_patent, big_patent = sorted([focus_patent, forward_patent])

        small_patent_abs = get_abstract(small_patent)
        if small_patent_abs == "":
            continue

        big_patent_abs = get_abstract(big_patent)
        if big_patent_abs == "":
            continue

        cos_similarity.append(get_similarity(small_patent_abs, big_patent_abs))

    if cos_similarity == []:
        return None

    cd_f2_t = cal_cd_f2_t(db, info)

    if cd_f2_t is None:
        return None

    mean_cos_similarity = sum(cos_similarity) / len(cos_similarity)
    return mean_cos_similarity * cd_f2_t


CAL_CD_MAPPING = {"cd_t": cal_cd_t, "cd_f_t": cal_cd_f_t, "cd_f2_t": cal_cd_f2_t, "cd_f3_t": cal_cd_f3_t}


def cal_cd(db: Session, index_names: str, batch_size: int):
    p_bar: tqdm = tqdm(desc=f"计算{index_names}中")
    offset = 0
    while True:
        info_batch = db.query(ExtendedInfo).offset(offset).limit(batch_size).all()
        if not info_batch:
            break

        for info in info_batch:
            p_bar.update(1)
            cd_index = db.query(CDIndex).filter(
                CDIndex.publication_number == info.publication_number
            ).first() or CDIndex(publication_number=info.publication_number)
            for index_name in index_names.split(","):
                try:
                    current_val = getattr(cd_index, index_name, None)
                    if current_val is not None:
                        continue
                    cd_value = CAL_CD_MAPPING[index_name](db, info)
                    setattr(cd_index, index_name, cd_value)
                except Exception as e:
                    logger.error(f"计算专利 {info.publication_number} 的 {index_name} 时出错: {e}")
            cd_index = db.merge(cd_index)
        db.commit()
        offset += batch_size
    p_bar.close()


if __name__ == "__main__":
    Base.metadata.create_all(bind=engine)
    arg_parser = argparse.ArgumentParser()
    arg_parser.add_argument("--index-names", required=True)
    arg_parser.add_argument("--batch-size", type=int, default=10000)
    args = arg_parser.parse_args()
    if not all(index_name in CAL_CD_MAPPING for index_name in args.index_names.split(",")):
        raise ValueError(f"包含不支持的指数名称 {args.index_names}，支持的名称有 {list(CAL_CD_MAPPING.keys())}")
    logger.info(f"开始计算CD指数，运行参数：{args}")
    db: Session = SessionLocal()
    cal_cd(db, args.index_names, args.batch_size)
    db.close()
    logger.info("计算完成")
