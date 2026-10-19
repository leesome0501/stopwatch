from __future__ import annotations

from fastapi import APIRouter, Depends

from ..db import Conn, get_conn
from ..schemas import Category, Household, HouseholdIn, Member, MemberIn
from .common import require

router = APIRouter(prefix="/api/households", tags=["가구"])


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
