from __future__ import annotations

import psycopg
from fastapi import APIRouter, Depends, HTTPException, Response

from ..db import Conn, get_conn
from ..schemas import (Category, CategoryIn, CategoryRule, CategoryRuleIn, Household, HouseholdDelete, HouseholdIn,
                       HouseholdPatch, Institution, Member, MemberIn, MemberPatch)
from .common import require

router = APIRouter(prefix="/api/households", tags=["가구"])
members_router = APIRouter(tags=["가구"])


@router.get("", response_model=list[Household])
def list_households(conn: Conn = Depends(get_conn)):
    return conn.execute("SELECT * FROM household ORDER BY id").fetchall()


@router.post("", response_model=Household, status_code=201)
def create_household(body: HouseholdIn, conn: Conn = Depends(get_conn)):
    return conn.execute("INSERT INTO household (name) VALUES (%s) RETURNING *", (body.name,)).fetchone()


@router.get("/{household_id}", response_model=Household)
def get_household(household_id: int, conn: Conn = Depends(get_conn)):
    return require(conn, "household", household_id, "가구")


@router.get("/{household_id}/members", response_model=list[Member])
def list_members(household_id: int, conn: Conn = Depends(get_conn)):
    require(conn, "household", household_id, "가구")
    return conn.execute("SELECT * FROM member WHERE household_id = %s ORDER BY id", (household_id,)).fetchall()


@router.post("/{household_id}/members", response_model=Member, status_code=201)
def create_member(household_id: int, body: MemberIn, conn: Conn = Depends(get_conn)):
    require(conn, "household", household_id, "가구")
    return conn.execute(
        """INSERT INTO member (household_id, name, relation, birth_date, is_dependent)
           VALUES (%s, %s, %s, %s, %s) RETURNING *""",
        (household_id, body.name, body.relation, body.birth_date, body.is_dependent)).fetchone()


@router.get("/{household_id}/categories", response_model=list[Category])
def list_categories(household_id: int, conn: Conn = Depends(get_conn)):
    require(conn, "household", household_id, "가구")
    return conn.execute(
        """SELECT id, household_id, parent_id, name, kind FROM category
            WHERE (household_id IS NULL OR household_id = %s) AND NOT is_hidden
            ORDER BY sort_order, parent_id NULLS FIRST, id""",
        (household_id,)).fetchall()


@router.patch("/{household_id}", response_model=Household)
def rename_household(household_id: int, body: HouseholdPatch, conn: Conn = Depends(get_conn)):
    require(conn, "household", household_id, "가구")
    return conn.execute("UPDATE household SET name = %s WHERE id = %s RETURNING *", (body.name, household_id)).fetchone()


# 가구 하나를 지울 때 지우는 순서 (외래키 때문에 참조하는 쪽부터)
_DELETE_HOUSEHOLD = [
    "DELETE FROM txn WHERE account_id IN (SELECT id FROM account WHERE household_id = %(h)s)",
    "DELETE FROM reported_balance WHERE account_id IN (SELECT id FROM account WHERE household_id = %(h)s)",
    "DELETE FROM reported_holding WHERE account_id IN (SELECT id FROM account WHERE household_id = %(h)s)",
    "DELETE FROM daily_value WHERE account_id IN (SELECT id FROM account WHERE household_id = %(h)s)",
    """DELETE FROM raw_record WHERE import_batch_id IN (
         SELECT b.id FROM import_batch b JOIN data_source d ON d.id = b.data_source_id WHERE d.household_id = %(h)s)""",
    "DELETE FROM import_batch WHERE data_source_id IN (SELECT id FROM data_source WHERE household_id = %(h)s)",
    "DELETE FROM category_rule WHERE household_id = %(h)s",
    "DELETE FROM account WHERE household_id = %(h)s",
    "DELETE FROM data_source WHERE household_id = %(h)s",
    "DELETE FROM app_user WHERE member_id IN (SELECT id FROM member WHERE household_id = %(h)s)",
    "DELETE FROM member WHERE household_id = %(h)s",
    "DELETE FROM category WHERE household_id = %(h)s",
    "DELETE FROM price WHERE instrument_id IN (SELECT id FROM instrument WHERE household_id = %(h)s)",
    "DELETE FROM instrument WHERE household_id = %(h)s",
    "DELETE FROM household WHERE id = %(h)s",
]


@router.delete("/{household_id}", status_code=204)
def delete_household(household_id: int, body: HouseholdDelete, conn: Conn = Depends(get_conn)):
    """가구와 그 가구의 모든 계좌·거래·구성원을 지운다 (예제 데이터 정리용). 되돌릴 수 없다."""
    h = require(conn, "household", household_id, "가구")
    if body.confirm_name != h["name"]:
        raise HTTPException(422, "확인용으로 입력한 이름이 가구 이름과 다릅니다.")
    for stmt in _DELETE_HOUSEHOLD:
        conn.execute(stmt, {"h": household_id})
    return Response(status_code=204)


@members_router.patch("/api/members/{member_id}", response_model=Member)
def patch_member(member_id: int, body: MemberPatch, conn: Conn = Depends(get_conn)):
    require(conn, "member", member_id, "구성원")
    # 생년월일만 비울 수 있다 (나머지는 NOT NULL)
    changes = {k: v for k, v in body.model_dump(exclude_unset=True).items() if v is not None or k == "birth_date"}
    if changes:
        sets = ", ".join(f"{k} = %s" for k in changes)
        conn.execute(f"UPDATE member SET {sets} WHERE id = %s", (*changes.values(), member_id))
    return conn.execute("SELECT * FROM member WHERE id = %s", (member_id,)).fetchone()


@members_router.delete("/api/members/{member_id}", status_code=204)
def delete_member(member_id: int, conn: Conn = Depends(get_conn)):
    require(conn, "member", member_id, "구성원")
    owned = conn.execute("""SELECT string_agg(a.name, ', ') AS names FROM account_owner o
                              JOIN account a ON a.id = o.account_id WHERE o.member_id = %s""", (member_id,)).fetchone()
    if owned["names"]:
        raise HTTPException(409, f"명의로 된 계좌가 있어 지울 수 없습니다: {owned['names']}. 계좌 명의를 먼저 바꿔 주세요.")
    conn.execute("DELETE FROM app_user WHERE member_id = %s", (member_id,))
    conn.execute("DELETE FROM member WHERE id = %s", (member_id,))
    return Response(status_code=204)


@members_router.get("/api/institutions", response_model=list[Institution], tags=["계좌"])
def list_institutions(conn: Conn = Depends(get_conn)):
    return conn.execute("SELECT id, code, name, kind FROM institution ORDER BY kind, name").fetchall()


@router.post("/{household_id}/categories", response_model=Category, status_code=201)
def create_category(household_id: int, body: CategoryIn, conn: Conn = Depends(get_conn)):
    """가구 전용 카테고리. 하위 카테고리는 상위의 수입/지출/이체 구분을 따른다."""
    require(conn, "household", household_id, "가구")
    if body.parent_id is not None:
        parent = conn.execute("""SELECT id, kind, parent_id FROM category WHERE id = %s
                                   AND (household_id IS NULL OR household_id = %s)""",
                              (body.parent_id, household_id)).fetchone()
        if parent is None:
            raise HTTPException(422, "상위 카테고리를 찾을 수 없습니다.")
        if parent["parent_id"] is not None:
            raise HTTPException(422, "카테고리는 2단계까지만 만들 수 있습니다.")
        kind = parent["kind"]
    else:
        if body.kind is None:
            raise HTTPException(422, "상위 카테고리를 새로 만들 때는 수입/지출/이체 구분(kind)이 필요합니다.")
        kind = body.kind
    try:
        with conn.transaction():
            return conn.execute(
                """INSERT INTO category (household_id, parent_id, name, kind, sort_order)
                   VALUES (%s, %s, %s, %s, 500) RETURNING id, household_id, parent_id, name, kind""",
                (household_id, body.parent_id, body.name, kind)).fetchone()
    except psycopg.errors.UniqueViolation:
        raise HTTPException(409, "같은 이름의 카테고리가 이미 있습니다.") from None


_RULE_SELECT = """SELECT r.id, r.match_field, r.match_type, r.pattern, r.category_id, c.name AS category_name,
                         r.account_id, r.priority, r.enabled
                    FROM category_rule r JOIN category c ON c.id = r.category_id"""


@router.get("/{household_id}/category-rules", response_model=list[CategoryRule])
def list_rules(household_id: int, conn: Conn = Depends(get_conn)):
    require(conn, "household", household_id, "가구")
    return conn.execute(_RULE_SELECT + " WHERE r.household_id = %s ORDER BY r.priority, r.id", (household_id,)).fetchall()


@router.post("/{household_id}/category-rules", response_model=CategoryRule, status_code=201)
def create_rule(household_id: int, body: CategoryRuleIn, conn: Conn = Depends(get_conn)):
    require(conn, "household", household_id, "가구")
    ok = conn.execute("SELECT 1 FROM category WHERE id = %s AND (household_id IS NULL OR household_id = %s)",
                      (body.category_id, household_id)).fetchone()
    if not ok:
        raise HTTPException(422, "이 가구에서 쓸 수 없는 카테고리입니다.")
    if body.match_type == "regex":
        import re
        try:
            re.compile(body.pattern)
        except re.error as e:
            raise HTTPException(422, f"정규식이 올바르지 않습니다: {e}") from None
    rid = conn.execute(
        """INSERT INTO category_rule (household_id, priority, account_id, match_field, match_type, pattern, category_id)
           VALUES (%s, %s, %s, %s, %s, %s, %s) RETURNING id""",
        (household_id, body.priority, body.account_id, body.match_field, body.match_type, body.pattern,
         body.category_id)).fetchone()["id"]
    return conn.execute(_RULE_SELECT + " WHERE r.id = %s", (rid,)).fetchone()


@router.delete("/{household_id}/category-rules/{rule_id}", status_code=204)
def delete_rule(household_id: int, rule_id: int, conn: Conn = Depends(get_conn)):
    if conn.execute("DELETE FROM category_rule WHERE id = %s AND household_id = %s", (rule_id, household_id)).rowcount == 0:
        raise HTTPException(404, "규칙을 찾을 수 없습니다.")
    return Response(status_code=204)
