import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import date, datetime, timedelta
import sqlite3
import urllib.parse
import json

st.set_page_config(
    page_title="건축설계 프로젝트 스케줄러",
    layout="wide",
    initial_sidebar_state="collapsed"
)

DB_FILE = "schedule.db"
ADMIN_PASSWORD = "1234"

# [840px 고정 폭 기준 정밀 컬럼 너비]
ROW_HEIGHT = 32
FONT_SIZE = 13
W_NO = 35
W_NAME = 250
W_TYPE = 110
W_PHASE = 110
W_STATUS = 95
W_UPDATE = 100
W_DEL = 40
TOTAL_WIDTH = W_NO + W_NAME + W_TYPE + W_PHASE + W_STATUS + W_UPDATE + W_DEL

# 상세페이지 3번 세부 공정 테이블 너비 분배
DW_NO = 35
DW_PHASE = 110
DW_TASK = 385
DW_PROG = 75
DW_STATUS = 85
DW_ACTION = 50

# 6대 표준 설계 단계
FIXED_PHASES = ["기획설계", "계획설계", "실시설계", "허가중", "착공상태", "준공대기"]

# 표준 허가 구분 목록
PERMIT_TYPES = ["신축허가", "신축신고", "증축허가", "증축신고", "대수선", "용도변경", "기재사항변경", "가설건축물", "기타"]

if "page_num" not in st.session_state:
    st.session_state.page_num = 1
if "active_permit_idx" not in st.session_state:
    st.session_state.active_permit_idx = 0
if "active_b1_tab" not in st.session_state:
    st.session_state.active_b1_tab = 0
if "contract_auth_unlocked" not in st.session_state:
    st.session_state.contract_auth_unlocked = False

# 1. CSS 스타일시트 (메인/상세 레이아웃 고정 및 하단 링크 버튼 스타일)
css_code = f"""
<style>
    @import url('https://cdn.jsdelivr.net/gh/orioncactus/pretendard/dist/web/static/pretendard.css');
    * {{
        font-family: 'Pretendard', -apple-system, BlinkMacSystemFont, system-ui, Roboto, sans-serif !important;
        box-sizing: border-box !important;
        word-break: keep-all !important;
    }}

    header[data-testid="stHeader"] {{
        display: none !important;
        height: 0px !important;
    }}
    .stAppDeployButton, [data-testid="stToolbar"], #MainMenu, footer {{
        display: none !important;
        visibility: hidden !important;
    }}

    html, body, [data-testid="stAppViewContainer"], .main {{
        overflow-x: auto !important;
        background-color: #fafbfc !important;
    }}

    .block-container {{
        padding-top: 1.8rem !important;
        padding-bottom: 3.5rem !important;
        min-width: {TOTAL_WIDTH + 40}px !important;
        width: {TOTAL_WIDTH + 40}px !important;
        max-width: {TOTAL_WIDTH + 40}px !important;
        margin: 0 auto !important;
    }}

    a.hero-title-link {{
        font-size: 2.15rem !important;
        font-weight: 750 !important;
        color: #0f172a !important;
        letter-spacing: -0.035em !important;
        line-height: 1 !important;
        margin: 0 !important;
        text-decoration: none !important;
        cursor: pointer !important;
        white-space: nowrap !important;
    }}
    a.hero-title-link:hover {{
        color: #1e293b !important;
        text-decoration: none !important;
    }}

    .hero-title-box {{
        display: inline-flex !important;
        align-items: center !important;
        gap: 6px !important;
        margin: 0 !important;
        padding: 0 !important;
        white-space: nowrap !important;
    }}

    a.title-edit-link {{
        display: inline-flex !important;
        align-items: center !important;
        justify-content: center !important;
        width: 28px !important;
        height: 28px !important;
        background: #f1f5f9 !important;
        border: 1px solid #e2e8f0 !important;
        border-radius: 6px !important;
        font-size: 0.85rem !important;
        color: #64748b !important;
        text-decoration: none !important;
        cursor: pointer !important;
        transition: all 0.15s ease !important;
        margin-left: 4px !important;
        white-space: nowrap !important;
    }}
    a.title-edit-link:hover {{
        background: #e2e8f0 !important;
        color: #0f172a !important;
    }}

    a.create-proj-link {{
        display: inline-flex !important;
        align-items: center !important;
        justify-content: center !important;
        background: #0f172a !important;
        border: 1px solid #0f172a !important;
        border-radius: 6px !important;
        padding: 0 14px !important;
        height: 32px !important;
        color: #ffffff !important;
        font-weight: 600 !important;
        font-size: 0.88rem !important;
        text-decoration: none !important;
        letter-spacing: -0.02em !important;
        box-shadow: 0 1px 2px rgba(0, 0, 0, 0.08) !important;
        transition: all 0.15s ease !important;
        white-space: nowrap !important;
    }}
    a.create-proj-link:hover {{
        background: #1e293b !important;
        border-color: #1e293b !important;
        transform: translateY(-1px);
    }}

    .kpi-grid {{
        display: flex !important;
        flex-direction: row !important;
        flex-wrap: nowrap !important;
        gap: 12px;
        width: {TOTAL_WIDTH}px !important;
        min-width: {TOTAL_WIDTH}px !important;
        margin-top: 1.2rem;
        margin-bottom: 0.7rem;
    }}
    .kpi-grid-sub {{
        display: flex !important;
        flex-direction: row !important;
        flex-wrap: nowrap !important;
        gap: 12px;
        width: {TOTAL_WIDTH}px !important;
        min-width: {TOTAL_WIDTH}px !important;
        margin-top: 0;
        margin-bottom: 1.4rem;
    }}
    
    a.kpi-card-link {{
        flex: 1;
        background: #ffffff;
        border: 1px solid #e2e8f0;
        border-radius: 10px;
        padding: 12px 18px;
        box-shadow: 0 1px 2px 0 rgba(0, 0, 0, 0.03);
        text-decoration: none !important;
        display: block;
        transition: transform 0.15s ease, box-shadow 0.15s ease;
        cursor: pointer !important;
        white-space: nowrap !important;
    }}
    a.kpi-card-link:hover {{
        transform: translateY(-2px);
        box-shadow: 0 4px 8px rgba(0, 0, 0, 0.06);
    }}
    a.kpi-card-link.active-filter {{
        outline: 2px solid #2563eb !important;
        background-color: #f8fafc !important;
    }}

    .kpi-label {{
        font-size: 0.8rem !important;
        font-weight: 550 !important;
        color: #64748b !important;
        margin-bottom: 2px !important;
    }}
    .kpi-value {{
        font-size: 1.55rem !important;
        font-weight: 750 !important;
        color: #0f172a !important;
    }}

    div[data-testid="stForm"] {{
        width: {TOTAL_WIDTH}px !important;
        min-width: {TOTAL_WIDTH}px !important;
        max-width: {TOTAL_WIDTH}px !important;
        background: #ffffff !important;
        border: 1px solid #e2e8f0 !important;
        border-radius: 0 0 10px 10px !important;
        padding: 18px 22px !important;
        box-shadow: 0 1px 3px rgba(0, 0, 0, 0.03) !important;
        overflow: hidden !important;
        margin-bottom: 1rem !important;
        margin-top: 0 !important;
    }}
    div[data-testid="stForm"] div[data-testid="stHorizontalBlock"] {{
        width: 100% !important;
        min-width: 0 !important;
        max-width: 100% !important;
        display: flex !important;
        gap: 8px !important;
        align-items: center !important;
    }}
    div[data-testid="stForm"] div[data-testid="column"] {{
        width: 100% !important;
        min-width: 0 !important;
        flex: 1 1 0% !important;
    }}

    div[data-testid="stForm"] div[data-testid="stTextInput"],
    div[data-testid="stForm"] div[data-testid="stSelectbox"],
    div[data-testid="stForm"] div[data-testid="stDateInput"],
    div[data-testid="stForm"] div[data-testid="stNumberInput"] {{
        width: 100% !important;
        min-width: 0 !important;
    }}
    div[data-testid="stForm"] input {{
        width: 100% !important;
        min-width: 0 !important;
        height: 32px !important;
        min-height: 32px !important;
        padding: 2px 10px !important;
        font-size: 13px !important;
    }}
    div[data-testid="stForm"] label {{
        font-size: 0.78rem !important;
        font-weight: 600 !important;
        color: #475569 !important;
        white-space: normal !important;
    }}

    div[data-baseweb="select"] {{
        width: 100% !important;
        min-width: 0 !important;
    }}
    div[data-baseweb="select"] * {{
        overflow: visible !important;
        text-overflow: clip !important;
        white-space: nowrap !important;
    }}
    div[data-testid="stSelectbox"] div[role="combobox"] {{
        padding-left: 8px !important;
        padding-right: 4px !important;
    }}

    hr.cad-divider {{
        margin: 10px 0 !important;
        border: none !important;
        border-top: 1px solid #e2e8f0 !important;
    }}

    a.symbol-btn {{
        display: block !important;
        text-align: center !important;
        font-size: 1.25rem !important;
        font-weight: 600 !important;
        color: #64748b !important;
        text-decoration: none !important;
        line-height: 32px !important;
        height: 32px !important;
        cursor: pointer !important;
        background: transparent !important;
        border: none !important;
        transition: all 0.12s ease !important;
    }}
    a.symbol-btn:hover {{
        color: #ef4444 !important;
        font-weight: 900 !important;
        font-size: 1.45rem !important;
        transform: scale(1.2) !important;
    }}

    .align-right-header-box {{
        width: {TOTAL_WIDTH}px !important;
        min-width: {TOTAL_WIDTH}px !important;
        max-width: {TOTAL_WIDTH}px !important;
        display: flex !important;
        justify-content: space-between !important;
        align-items: center !important;
        margin-top: 0.6rem !important;
        margin-bottom: 0.4rem !important;
        padding: 0 !important;
    }}

    a.solid-red-btn {{
        display: inline-flex !important;
        align-items: center !important;
        justify-content: center !important;
        background: #ef4444 !important;
        border: 1px solid #ef4444 !important;
        border-radius: 6px !important;
        padding: 0 16px !important;
        height: 32px !important;
        color: #ffffff !important;
        font-weight: 750 !important;
        font-size: 0.88rem !important;
        text-decoration: none !important;
        cursor: pointer !important;
        transition: all 0.15s ease !important;
        box-shadow: 0 1px 2px rgba(239, 68, 68, 0.25) !important;
    }}
    a.solid-red-btn:hover {{
        background: #dc2626 !important;
        border-color: #dc2626 !important;
        color: #ffffff !important;
        transform: translateY(-1px) !important;
        text-decoration: none !important;
    }}

    a.text-action-link {{
        display: inline-flex !important;
        align-items: center !important;
        justify-content: flex-end !important;
        font-size: 0.95rem !important;
        font-weight: 750 !important;
        color: #475569 !important;
        text-decoration: none !important;
        cursor: pointer !important;
        height: 32px !important;
        line-height: 32px !important;
        white-space: nowrap !important;
        transition: all 0.15s ease !important;
    }}
    a.text-action-link:hover {{
        color: #0f172a !important;
        font-weight: 850 !important;
        transform: scale(1.04) !important;
        text-decoration: none !important;
    }}

    .card-tabs-container {{
        display: flex !important;
        flex-direction: row !important;
        width: {TOTAL_WIDTH}px !important;
        min-width: {TOTAL_WIDTH}px !important;
        max-width: {TOTAL_WIDTH}px !important;
        gap: 6px !important;
        margin-top: 0.5rem !important;
        margin-bottom: 0 !important;
        padding: 0 !important;
        box-sizing: border-box !important;
    }}
    .card-tab-item {{
        flex: 1 1 0% !important;
        display: flex !important;
        align-items: center !important;
        justify-content: center !important;
        height: 36px !important;
        background: #ffffff !important;
        color: #475569 !important;
        border: 1px solid #cbd5e1 !important;
        border-bottom: 1px solid #e2e8f0 !important;
        border-radius: 8px 8px 0 0 !important;
        font-size: 0.88rem !important;
        font-weight: 650 !important;
        text-decoration: none !important;
        cursor: pointer !important;
        white-space: nowrap !important;
        overflow: hidden !important;
        text-overflow: ellipsis !important;
        padding: 0 12px !important;
        transition: all 0.15s ease !important;
        box-sizing: border-box !important;
    }}
    .card-tab-item:hover {{
        background: #f8fafc !important;
        color: #0f172a !important;
        border-color: #94a3b8 !important;
        text-decoration: none !important;
    }}
    .card-tab-item.active-card-tab {{
        background: #0f172a !important;
        color: #ffffff !important;
        border: 1px solid #0f172a !important;
        border-bottom: 1px solid #0f172a !important;
        font-weight: 750 !important;
    }}

    .cad-table-title {{
        font-size: 1.02rem;
        font-weight: 750;
        color: #0f172a;
        margin-top: 0.6rem;
        margin-bottom: 0.4rem;
        display: flex;
        align-items: center;
        gap: 6px;
    }}
    .cad-table-title::before {{
        content: "■";
        font-size: 0.85rem;
        color: #2563eb;
    }}
    .cad-summary-box {{
        background: #f8fafc;
        border: 1px solid #e2e8f0;
        border-radius: 6px;
        padding: 8px 14px;
        margin-top: 6px;
        margin-bottom: 12px;
        display: flex;
        justify-content: space-between;
        align-items: center;
        font-size: 0.88rem;
    }}

    .ratio-calc-preview {{
        background: #eff6ff;
        border: 1px solid #bfdbfe;
        border-radius: 6px;
        padding: 6px 12px;
        margin-top: 4px;
        margin-bottom: 8px;
        font-size: 0.82rem;
        color: #1e40af;
        display: flex;
        justify-content: space-between;
    }}

    .section-title-box {{
        font-size: 1.1rem;
        font-weight: 750;
        color: #0f172a;
        margin-top: 1.2rem;
        margin-bottom: 0.6rem;
    }}

    .badge-ing {{
        display: inline-block;
        padding: 1px 6px;
        border-radius: 4px;
        font-size: 11px;
        font-weight: 600;
        background-color: #ecfdf5;
        color: #059669;
        border: 1px solid #a7f3d0;
        line-height: 1.2;
    }}
    .badge-done {{
        display: inline-block;
        padding: 1px 6px;
        border-radius: 4px;
        font-size: 11px;
        font-weight: 600;
        background-color: #f1f5f9;
        color: #64748b;
        border: 1px solid #cbd5e1;
        line-height: 1.2;
    }}
    a.board-link {{
        color: #0f172a !important;
        text-decoration: none !important;
        font-weight: 600 !important;
        font-size: {FONT_SIZE}px !important;
        display: block !important;
        overflow: hidden !important;
        text-overflow: ellipsis !important;
        white-space: nowrap !important;
    }}
    a.board-link:hover {{
        color: #2563eb !important;
        text-decoration: underline !important;
    }}
    a.del-btn-link {{
        color: #94a3b8 !important;
        text-decoration: none !important;
        font-size: {FONT_SIZE}px !important;
        display: inline-block;
    }}
    a.del-btn-link:hover {{
        color: #ef4444 !important;
        transform: scale(1.2);
    }}

    .table-container {{
        width: {TOTAL_WIDTH}px !important;
        min-width: {TOTAL_WIDTH}px !important;
        border: 1px solid #e2e8f0;
        border-radius: 8px;
        overflow: hidden;
        background: #ffffff;
        box-shadow: 0 1px 3px 0 rgba(0, 0, 0, 0.02);
    }}
    .grid-row {{
        display: grid !important;
        grid-template-columns: {W_NO}px {W_NAME}px {W_TYPE}px {W_PHASE}px {W_STATUS}px {W_UPDATE}px {W_DEL}px !important;
        align-items: center !important;
        height: {ROW_HEIGHT}px !important;
        min-height: {ROW_HEIGHT}px !important;
        max-height: {ROW_HEIGHT}px !important;
        border-bottom: 1px solid #f1f5f9;
        font-size: {FONT_SIZE}px !important;
        white-space: nowrap !important;
    }}
    .grid-row:last-child {{
        border-bottom: none !important;
    }}
    .grid-row:hover {{
        background-color: #f8fafc !important;
    }}
    .grid-header {{
        background-color: #f8fafc !important;
        border-bottom: 1px solid #cbd5e1 !important;
        color: #475569 !important;
        font-weight: 650 !important;
        font-size: 12px !important;
    }}
    .cell {{
        padding: 0 6px !important;
        overflow: hidden !important;
        text-overflow: ellipsis !important;
        line-height: {ROW_HEIGHT}px !important;
        height: {ROW_HEIGHT}px !important;
        white-space: nowrap !important;
    }}
    .cell-center {{
        text-align: center !important;
    }}

    .table-container-detail {{
        width: {TOTAL_WIDTH}px !important;
        min-width: {TOTAL_WIDTH}px !important;
        border: 1px solid #e2e8f0;
        border-radius: 8px;
        overflow: hidden;
        background: #ffffff;
        box-shadow: 0 1px 3px 0 rgba(0, 0, 0, 0.02);
    }}
    .grid-row-detail {{
        display: grid !important;
        grid-template-columns: {DW_NO}px {DW_PHASE}px {DW_TASK}px {DW_PROG}px {DW_STATUS}px {DW_ACTION}px !important;
        align-items: center !important;
        height: {ROW_HEIGHT}px !important;
        min-height: {ROW_HEIGHT}px !important;
        max-height: {ROW_HEIGHT}px !important;
        border-bottom: 1px solid #f1f5f9;
        font-size: {FONT_SIZE}px !important;
        white-space: nowrap !important;
    }}
    .grid-row-detail:last-child {{
        border-bottom: none !important;
    }}
    .grid-row-detail:hover {{
        background-color: #f8fafc !important;
    }}

    /* 하단 외부 링크 버튼 스타일 */
    .footer-link-container {{
        display: flex !important;
        gap: 10px !important;
        width: {TOTAL_WIDTH}px !important;
        min-width: {TOTAL_WIDTH}px !important;
        margin-top: 1.8rem !important;
        margin-bottom: 1rem !important;
    }}
    a.footer-link-btn {{
        flex: 1;
        background: #ffffff;
        border: 1px solid #cbd5e1;
        border-radius: 8px;
        padding: 10px 14px;
        text-align: center;
        text-decoration: none !important;
        color: #334155 !important;
        font-weight: 650;
        font-size: 0.85rem !important;
        box-shadow: 0 1px 2px rgba(0,0,0,0.02);
        transition: all 0.15s ease;
        display: inline-flex;
        align-items: center;
        justify-content: center;
        gap: 6px;
        white-space: nowrap !important;
    }}
    a.footer-link-btn:hover {{
        background: #f1f5f9;
        border-color: #94a3b8;
        color: #0f172a !important;
        transform: translateY(-1px);
    }}
</style>
"""
st.markdown(css_code, unsafe_allow_html=True)

# 2. 데이터베이스 초기화
def init_db():
    conn = sqlite3.connect(DB_FILE, check_same_thread=False)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            project_name TEXT NOT NULL,
            work_type TEXT NOT NULL DEFAULT '신축허가',
            phase TEXT NOT NULL DEFAULT '기획설계',
            task_name TEXT,
            start_date TEXT NOT NULL,
            end_date TEXT NOT NULL,
            assignee TEXT,
            status TEXT,
            progress INTEGER,
            updated_at TEXT,
            client_name TEXT,
            site_address TEXT
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL
        )
    """)
    cursor.execute("INSERT OR IGNORE INTO settings (key, value) VALUES (?, ?)", 
                   ("main_title", "대문건축 업무대장"))

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS project_permits (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            project_name TEXT NOT NULL,
            client_name TEXT NOT NULL DEFAULT '',
            permit_type TEXT NOT NULL DEFAULT '신축허가',
            lots_json TEXT,
            zone_district TEXT,
            road_condition TEXT,
            main_use TEXT,
            structure TEXT,
            floors_up TEXT,
            height TEXT,
            building_area TEXT,
            total_floor_area TEXT,
            far_area TEXT,
            bc_ratio TEXT,
            fa_ratio TEXT,
            parking_calc TEXT,
            parking_plan TEXT,
            septic_tank TEXT,
            landscaping TEXT,
            assignee TEXT,
            status TEXT DEFAULT '진행중'
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS project_permit_milestones (
            permit_id INTEGER PRIMARY KEY,
            project_name TEXT NOT NULL,
            permit_no TEXT,
            permit_date TEXT,
            start_work_date TEXT,
            complete_work_date TEXT
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS project_contracts (
            project_name TEXT PRIMARY KEY,
            contract_date TEXT,
            contract_amount TEXT,
            vat_included TEXT DEFAULT '포함',
            contractor_name TEXT,
            deposit_terms TEXT,
            mid_terms TEXT,
            balance_terms TEXT,
            notes TEXT
        )
    """)
    
    cursor.execute("PRAGMA table_info(project_permits)")
    p_cols = [col[1] for col in cursor.fetchall()]
    needed_cols = {
        "client_name": "TEXT NOT NULL DEFAULT ''",
        "permit_type": "TEXT NOT NULL DEFAULT '신축허가'",
        "lots_json": "TEXT",
        "zone_district": "TEXT",
        "road_condition": "TEXT",
        "main_use": "TEXT",
        "structure": "TEXT",
        "floors_up": "TEXT",
        "height": "TEXT",
        "building_area": "TEXT",
        "total_floor_area": "TEXT",
        "far_area": "TEXT",
        "bc_ratio": "TEXT",
        "fa_ratio": "TEXT",
        "parking_calc": "TEXT",
        "parking_plan": "TEXT",
        "septic_tank": "TEXT",
        "landscaping": "TEXT",
        "assignee": "TEXT",
        "status": "TEXT DEFAULT '진행중'"
    }
    for c_name, c_type in needed_cols.items():
        if c_name not in p_cols:
            cursor.execute(f"ALTER TABLE project_permits ADD COLUMN {c_name} {c_type}")

    cursor.execute("PRAGMA table_info(tasks)")
    columns = [col[1] for col in cursor.fetchall()]
    if "updated_at" not in columns:
        cursor.execute("ALTER TABLE tasks ADD COLUMN updated_at TEXT")
    if "client_name" not in columns:
        cursor.execute("ALTER TABLE tasks ADD COLUMN client_name TEXT")
    if "site_address" not in columns:
        cursor.execute("ALTER TABLE tasks ADD COLUMN site_address TEXT")

    cursor.execute("UPDATE tasks SET phase = '기획설계' WHERE phase IN ('기획', '심의/사전결정', '사전심의', '기획단계')")
    cursor.execute("UPDATE tasks SET phase = '계획설계' WHERE phase IN ('계획', '계획단계')")
    cursor.execute("UPDATE tasks SET phase = '실시설계' WHERE phase IN ('실시', '실시단계', '도면작성')")
    cursor.execute("UPDATE tasks SET phase = '허가중' WHERE phase IN ('인허가', '허가접수', '세움터', '협력업체 조율', '심의')")
    cursor.execute("UPDATE tasks SET phase = '착공상태' WHERE phase IN ('착공/감리', '착공', '감리', '착공준비')")
    cursor.execute("UPDATE tasks SET phase = '준공대기' WHERE phase IN ('준공', '사용승인', '준공/사용승인')")

    cursor.execute("SELECT COUNT(*) FROM tasks")
    if cursor.fetchone()[0] == 0:
        now = datetime.now()
        samples = [
            ("화성 안석리 단독주택", "신축허가", "계획설계", "배치 및 평면 확정 (건축주 협의)", str(now.date() - timedelta(days=7)), str(now.date() + timedelta(days=3)), "김건축", "진행중", 80, (now - timedelta(minutes=15)).strftime("%Y-%m-%d %H:%M:%S"), "홍길동", "화성시 남양읍 안석리"),
            ("화성 안석리 단독주택", "신축허가", "허가중", "건축허가 접수 (세움터)", str(now.date() + timedelta(days=4)), str(now.date() + timedelta(days=18)), "이팀장", "대기", 0, (now - timedelta(minutes=15)).strftime("%Y-%m-%d %H:%M:%S"), "홍길동", "화성시 남양읍 안석리"),
            ("남양읍 근린생활시설", "신축허가", "실시설계", "구조안전확인서 및 구조도 납품", str(now.date() - timedelta(days=3)), str(now.date() + timedelta(days=5)), "구조협력", "진행중", 50, (now - timedelta(hours=2)).strftime("%Y-%m-%d %H:%M:%S"), "이영희", "화성시 남양읍 남양리"),
            ("온석리 제2종근생 증축", "증축허가", "기획설계", "개발행위허가 사전심의 도서 제출", str(now.date() - timedelta(days=1)), str(now.date() + timedelta(days=14)), "박소장", "진행중", 30, (now - timedelta(days=1)).strftime("%Y-%m-%d %H:%M:%S"), "김철수", "화성시 남양읍 온석리"),
            ("송산면 창고시설", "신축신고", "착공상태", "배치도 및 신고도서 납품", str(now.date() - timedelta(days=2)), str(now.date() + timedelta(days=8)), "이팀장", "진행중", 60, (now - timedelta(days=2)).strftime("%Y-%m-%d %H:%M:%S"), "박대표", "화성시 송산면 사강리")
        ]
        cursor.executemany("""
            INSERT INTO tasks (project_name, work_type, phase, task_name, start_date, end_date, assignee, status, progress, updated_at, client_name, site_address)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, samples)

    cursor.execute("UPDATE tasks SET updated_at = ? WHERE updated_at IS NULL OR updated_at = ''", (datetime.now().strftime("%Y-%m-%d %H:%M:%S"),))
    conn.commit()
    conn.close()

init_db()

def get_connection():
    return sqlite3.connect(DB_FILE, check_same_thread=False)

def get_main_title():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT value FROM settings WHERE key = 'main_title'")
    row = cursor.fetchone()
    conn.close()
    return row[0] if row else "대문건축 업무대장"

def update_main_title(new_title):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE settings SET value = ? WHERE key = 'main_title'", (new_title,))
    conn.commit()
    conn.close()

def delete_project_from_db(project_name):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM tasks WHERE project_name = ?", (project_name,))
    cursor.execute("DELETE FROM project_permits WHERE project_name = ?", (project_name,))
    cursor.execute("DELETE FROM project_permit_milestones WHERE project_name = ?", (project_name,))
    cursor.execute("DELETE FROM project_contracts WHERE project_name = ?", (project_name,))
    conn.commit()
    conn.close()

def update_project_base_info(old_name, new_name, base_address):
    conn = get_connection()
    cursor = conn.cursor()
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cursor.execute("""
        UPDATE tasks 
        SET project_name = ?, site_address = ?, updated_at = ?
        WHERE project_name = ?
    """, (new_name, base_address, now_str, old_name))
    cursor.execute("""
        UPDATE project_permits
        SET project_name = ?
        WHERE project_name = ?
    """, (new_name, old_name))
    cursor.execute("""
        UPDATE project_permit_milestones
        SET project_name = ?
        WHERE project_name = ?
    """, (new_name, old_name))
    cursor.execute("""
        UPDATE project_contracts
        SET project_name = ?
        WHERE project_name = ?
    """, (new_name, old_name))
    conn.commit()
    conn.close()

def get_permit_milestone(permit_id, project_name):
    conn = get_connection()
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM project_permit_milestones WHERE permit_id = ?", (permit_id,))
    row = cursor.fetchone()
    conn.close()
    if row:
        return dict(row)
    return {"permit_no": "", "permit_date": "", "start_work_date": "", "complete_work_date": ""}

def save_permit_milestone(permit_id, project_name, p_no, p_date, s_date, c_date):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO project_permit_milestones (permit_id, project_name, permit_no, permit_date, start_work_date, complete_work_date)
        VALUES (?, ?, ?, ?, ?, ?)
        ON CONFLICT(permit_id) DO UPDATE SET
            permit_no = excluded.permit_no,
            permit_date = excluded.permit_date,
            start_work_date = excluded.start_work_date,
            complete_work_date = excluded.complete_work_date
    """, (permit_id, project_name, p_no, p_date, s_date, c_date))
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cursor.execute("UPDATE tasks SET updated_at = ? WHERE project_name = ?", (now_str, project_name))
    conn.commit()
    conn.close()

def get_project_contract(project_name):
    conn = get_connection()
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM project_contracts WHERE project_name = ?", (project_name,))
    row = cursor.fetchone()
    conn.close()
    if row:
        return dict(row)
    return {
        "contract_date": "",
        "contract_amount": "",
        "vat_included": "포함",
        "contractor_name": "",
        "deposit_terms": "",
        "mid_terms": "",
        "balance_terms": "",
        "notes": ""
    }

def save_project_contract(project_name, payload):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO project_contracts (
            project_name, contract_date, contract_amount, vat_included,
            contractor_name, deposit_terms, mid_terms, balance_terms, notes
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(project_name) DO UPDATE SET
            contract_date = excluded.contract_date,
            contract_amount = excluded.contract_amount,
            vat_included = excluded.vat_included,
            contractor_name = excluded.contractor_name,
            deposit_terms = excluded.deposit_terms,
            mid_terms = excluded.mid_terms,
            balance_terms = excluded.balance_terms,
            notes = excluded.notes
    """, (
        project_name,
        payload.get("contract_date", ""),
        payload.get("contract_amount", ""),
        payload.get("vat_included", "포함"),
        payload.get("contractor_name", ""),
        payload.get("deposit_terms", ""),
        payload.get("mid_terms", ""),
        payload.get("balance_terms", ""),
        payload.get("notes", "")
    ))
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cursor.execute("UPDATE tasks SET updated_at = ? WHERE project_name = ?", (now_str, project_name))
    conn.commit()
    conn.close()

def get_project_permits_list(project_name, default_client="", default_type="신축허가"):
    conn = get_connection()
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM project_permits WHERE project_name = ? ORDER BY id ASC", (project_name,))
    rows = cursor.fetchall()
    
    if not rows:
        empty_lots = json.dumps([
            {"lot": "", "category": "대", "doc_area": "", "act_area": "", "road_area": "", "excl_area": "", "note": ""}
        ], ensure_ascii=False)
        
        cursor.execute("""
            INSERT INTO project_permits (
                project_name, client_name, permit_type, lots_json, zone_district, road_condition,
                main_use, structure, floors_up, height, building_area, total_floor_area,
                far_area, bc_ratio, fa_ratio, parking_calc, parking_plan, septic_tank, landscaping, assignee, status
            ) VALUES (
                ?, ?, ?, ?, '', '',
                '', '', '', '', '', '',
                '', '', '', '', '',
                '', '', '', '진행중'
            )
        """, (project_name, default_client, default_type or "신축허가", empty_lots))
        conn.commit()
        cursor.execute("SELECT * FROM project_permits WHERE project_name = ? ORDER BY id ASC", (project_name,))
        rows = cursor.fetchall()
        
    conn.close()
    result = []
    for r in rows:
        d = dict(r)
        if "client_name" not in d:
            d["client_name"] = ""
        if not d.get("permit_type"):
            d["permit_type"] = "신축허가"
        result.append(d)
    return result

def add_new_permit_tab(project_name, client_name, permit_type):
    conn = get_connection()
    cursor = conn.cursor()
    empty_lots = json.dumps([
        {"lot": "", "category": "대", "doc_area": "", "act_area": "", "road_area": "", "excl_area": "", "note": ""}
    ], ensure_ascii=False)
    cursor.execute("""
        INSERT INTO project_permits (
            project_name, client_name, permit_type, lots_json, zone_district, road_condition,
            main_use, structure, floors_up, height, building_area, total_floor_area,
            far_area, bc_ratio, fa_ratio, parking_calc, parking_plan, septic_tank, landscaping, assignee, status
        ) VALUES (
            ?, ?, ?, ?, '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '진행중'
        )
    """, (project_name, client_name, permit_type, empty_lots))
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cursor.execute("UPDATE tasks SET updated_at = ? WHERE project_name = ?", (now_str, project_name))
    conn.commit()
    conn.close()

def save_cad_permit_overview(permit_id, project_name, payload):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE project_permits SET
            client_name = :client_name,
            permit_type = :permit_type,
            lots_json = :lots_json,
            zone_district = :zone_district,
            road_condition = :road_condition,
            main_use = :main_use,
            structure = :structure,
            floors_up = :floors_up,
            height = :height,
            building_area = :building_area,
            total_floor_area = :total_floor_area,
            far_area = :far_area,
            bc_ratio = :bc_ratio,
            fa_ratio = :fa_ratio,
            parking_calc = :parking_calc,
            parking_plan = :parking_plan,
            septic_tank = :septic_tank,
            landscaping = :landscaping,
            assignee = :assignee
        WHERE id = :id
    """, {
        "id": permit_id,
        "client_name": payload.get("client_name", ""),
        "permit_type": payload.get("permit_type", "신축허가"),
        "lots_json": payload.get("lots_json", "[]"),
        "zone_district": payload.get("zone_district", ""),
        "road_condition": payload.get("road_condition", ""),
        "main_use": payload.get("main_use", ""),
        "structure": payload.get("structure", ""),
        "floors_up": payload.get("floors_up", ""),
        "height": payload.get("height", ""),
        "building_area": payload.get("building_area", ""),
        "total_floor_area": payload.get("total_floor_area", ""),
        "far_area": payload.get("far_area", ""),
        "bc_ratio": payload.get("bc_ratio", ""),
        "fa_ratio": payload.get("fa_ratio", ""),
        "parking_calc": payload.get("parking_calc", ""),
        "parking_plan": payload.get("parking_plan", ""),
        "septic_tank": payload.get("septic_tank", ""),
        "landscaping": payload.get("landscaping", ""),
        "assignee": payload.get("assignee", "")
    })
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cursor.execute("UPDATE tasks SET updated_at = ? WHERE project_name = ?", (now_str, project_name))
    conn.commit()
    conn.close()

def delete_permit_tab(permit_id, project_name):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM project_permits WHERE id = ?", (permit_id,))
    cursor.execute("DELETE FROM project_permit_milestones WHERE permit_id = ?", (permit_id,))
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cursor.execute("UPDATE tasks SET updated_at = ? WHERE project_name = ?", (now_str, project_name))
    conn.commit()
    conn.close()

def get_or_create_fixed_phases(project_name, work_type="신축허가"):
    conn = get_connection()
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM tasks WHERE project_name = ?", (project_name,))
    existing_tasks = {r["phase"]: dict(r) for r in cursor.fetchall()}
    
    now_date_str = str(date.today())
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    for phase_name in FIXED_PHASES:
        if phase_name not in existing_tasks:
            cursor.execute("""
                INSERT INTO tasks (project_name, work_type, phase, task_name, start_date, end_date, assignee, status, progress, updated_at, client_name, site_address)
                VALUES (?, ?, ?, '', ?, ?, '', '대기', 0, ?, ?, '')
            """, (project_name, work_type, phase_name, now_date_str, now_date_str, now_str))
    conn.commit()

    cursor.execute("SELECT * FROM tasks WHERE project_name = ?", (project_name,))
    all_rows = {r["phase"]: dict(r) for r in cursor.fetchall()}
    conn.close()
    return [all_rows[p] for p in FIXED_PHASES if p in all_rows]

def update_task_simple(task_id, project_name, task_name, status, prog, assignee):
    conn = get_connection()
    cursor = conn.cursor()
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cursor.execute("""
        UPDATE tasks SET
            task_name = ?,
            status = ?,
            progress = ?,
            assignee = ?,
            updated_at = ?
        WHERE id = ?
    """, (task_name, status, prog, assignee, now_str, task_id))
    cursor.execute("UPDATE tasks SET updated_at = ? WHERE project_name = ?", (now_str, project_name))
    conn.commit()
    conn.close()

def load_data():
    conn = get_connection()
    df = pd.read_sql_query("SELECT * FROM tasks", conn)
    conn.close()
    return df

current_page = st.query_params.get("page", "main")
current_proj = st.query_params.get("project", None)
del_target = st.query_params.get("del_proj", None)
edit_phase_id = st.query_params.get("edit_phase", None)
edit_title_flag = st.query_params.get("edit_title", None)
active_filter = st.query_params.get("filter", None)

edit_proj_modal = st.query_params.get("edit_proj_modal", None)
add_card_modal = st.query_params.get("add_card_modal", None)

set_b1_tab = st.query_params.get("set_b1_tab", None)
set_permit_param = st.query_params.get("set_permit", None)

action_lot_add = st.query_params.get("action_lot_add", None)
action_lot_del = st.query_params.get("action_lot_del", None)

if set_b1_tab is not None and current_proj:
    try:
        st.session_state.active_b1_tab = int(set_b1_tab)
    except:
        pass
    st.query_params.clear()
    st.query_params["page"] = "detail"
    st.query_params["project"] = current_proj
    st.rerun()

if set_permit_param is not None and current_proj:
    try:
        st.session_state.active_permit_idx = int(set_permit_param)
    except:
        pass
    st.query_params.clear()
    st.query_params["page"] = "detail"
    st.query_params["project"] = current_proj
    st.rerun()

if action_lot_add and current_proj:
    perm_list_tmp = get_project_permits_list(current_proj)
    if st.session_state.active_permit_idx < len(perm_list_tmp):
        cur_p = perm_list_tmp[st.session_state.active_permit_idx]
        try: l_list = json.loads(cur_p.get("lots_json") or "[]")
        except: l_list = []
        l_list.append({"lot": "", "category": "대", "doc_area": "", "act_area": "", "road_area": "", "excl_area": "", "note": ""})
        cur_p["lots_json"] = json.dumps(l_list, ensure_ascii=False)
        save_cad_permit_overview(cur_p["id"], current_proj, cur_p)
    st.query_params.clear()
    st.query_params["page"] = "detail"
    st.query_params["project"] = current_proj
    st.rerun()

if action_lot_del and current_proj:
    perm_list_tmp = get_project_permits_list(current_proj)
    if st.session_state.active_permit_idx < len(perm_list_tmp):
        cur_p = perm_list_tmp[st.session_state.active_permit_idx]
        try: l_list = json.loads(cur_p.get("lots_json") or "[]")
        except: l_list = []
        del_idx = int(action_lot_del)
        if 0 <= del_idx < len(l_list) and len(l_list) > 1:
            l_list.pop(del_idx)
        elif len(l_list) <= 1:
            l_list = [{"lot": "", "category": "대", "doc_area": "", "act_area": "", "road_area": "", "excl_area": "", "note": ""}]
        cur_p["lots_json"] = json.dumps(l_list, ensure_ascii=False)
        save_cad_permit_overview(cur_p["id"], current_proj, cur_p)
    st.query_params.clear()
    st.query_params["page"] = "detail"
    st.query_params["project"] = current_proj
    st.rerun()

df = load_data()

@st.dialog("대시보드 제목 변경")
def edit_main_title_dialog(current_title):
    st.write("메인 화면에 표시할 대제목을 입력하세요.")
    new_t = st.text_input("대제목 명칭", value=current_title)
    col1, col2 = st.columns(2)
    with col1:
        if st.button("저장", type="primary", use_container_width=True):
            if new_t.strip():
                update_main_title(new_t.strip())
                st.query_params.clear()
                st.rerun()
    with col2:
        if st.button("취소", use_container_width=True):
            st.query_params.clear()
            st.rerun()

@st.dialog("프로젝트 삭제")
def confirm_delete_dialog(project_name):
    st.write(f"**'{project_name}'** 프로젝트를 삭제하시겠습니까?")
    st.caption("등록된 모든 세부 공정 및 허가개요 데이터가 영구 삭제됩니다.")
    input_pw = st.text_input("관리자 비밀번호", type="password", placeholder="비밀번호 입력")
    col1, col2 = st.columns(2)
    with col1:
        if st.button("삭제", type="primary", use_container_width=True):
            if input_pw == ADMIN_PASSWORD:
                delete_project_from_db(project_name)
                st.query_params.clear()
                st.rerun()
            else:
                st.error("비밀번호가 일치하지 않습니다.")
    with col2:
        if st.button("취소", use_container_width=True):
            st.query_params.clear()
            st.rerun()

@st.dialog("프로젝트 기본정보 수정")
def edit_project_base_dialog(project_name, current_addr):
    st.write(f"**'{project_name}'** 기본정보 수정")
    new_pname = st.text_input("프로젝트명 *", value=project_name).strip()
    new_addr = st.text_input("대지위치 (00리까지 기본 주소)", value=current_addr, placeholder="예: 경기도 화성시 남양읍 안석리").strip()
    
    c_ok, c_cancel = st.columns(2)
    with c_ok:
        if st.button("수정 저장", type="primary", use_container_width=True):
            if new_pname:
                update_project_base_info(project_name, new_pname, new_addr)
                st.query_params.clear()
                st.query_params["page"] = "detail"
                st.query_params["project"] = new_pname
                st.success("프로젝트 정보가 수정되었습니다.")
                st.rerun()
            else:
                st.error("프로젝트명을 입력해 주세요.")
    with c_cancel:
        if st.button("취소", use_container_width=True):
            st.query_params.clear()
            st.query_params["page"] = "detail"
            st.query_params["project"] = project_name
            st.rerun()

@st.dialog("설계 단계 세부 내용 수정")
def edit_phase_dialog(task_id, project_name):
    conn = get_connection()
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    cur.execute("SELECT * FROM tasks WHERE id = ?", (task_id,))
    t_row = cur.fetchone()
    conn.close()

    if not t_row:
        st.error("공정 정보를 찾을 수 없습니다.")
        return

    cur_phase = t_row["phase"]
    st.write(f"**[{cur_phase}]** 단계 업무 내용 수정")
    edit_tname = st.text_input("세부 업무 내용 *", value=t_row["task_name"] or "").strip()
    
    c1, c2 = st.columns(2)
    with c1:
        statuses = ["진행중", "대기", "완료"]
        st_idx = statuses.index(t_row["status"]) if t_row["status"] in statuses else 0
        edit_status = st.selectbox("진행 상태", statuses, index=st_idx)
    with c2:
        edit_prog = st.number_input("진행률 (%)", min_value=0, max_value=100, value=int(t_row["progress"] or 0), step=10)

    edit_assignee = st.text_input("담당자 / PM", value=t_row["assignee"] or "").strip()

    st.markdown("<div style='height: 8px;'></div>", unsafe_allow_html=True)
    b_ok, b_cancel = st.columns(2)
    with b_ok:
        if st.button("단계 정보 저장", type="primary", use_container_width=True):
            update_task_simple(task_id, project_name, edit_tname, edit_status, edit_prog, edit_assignee)
            st.query_params.clear()
            st.query_params["page"] = "detail"
            st.query_params["project"] = project_name
            st.rerun()
    with b_cancel:
        if st.button("취소", use_container_width=True):
            st.query_params.clear()
            st.query_params["page"] = "detail"
            st.query_params["project"] = project_name
            st.rerun()

@st.dialog("신규 허가건(인덱스 카드) 추가")
def add_permit_dialog(project_name):
    st.write("새 허가건의 건축주명을 입력하세요.")
    new_cname = st.text_input("건축주 성명", placeholder="건축주 성명 입력").strip()
    new_ptype = st.selectbox("허가 구분 *", PERMIT_TYPES)
    
    col_ok, col_no = st.columns(2)
    with col_ok:
        if st.button("인덱스 카드 생성", type="primary", use_container_width=True):
            add_new_permit_tab(project_name, new_cname, new_ptype)
            st.query_params.clear()
            st.query_params["page"] = "detail"
            st.query_params["project"] = project_name
            st.rerun()
    with col_no:
        if st.button("취소", use_container_width=True):
            st.query_params.clear()
            st.query_params["page"] = "detail"
            st.query_params["project"] = project_name
            st.rerun()

if del_target:
    confirm_delete_dialog(del_target)

if edit_proj_modal and current_proj:
    p_addr_for_m = df[df["project_name"] == current_proj]["site_address"].dropna().values
    cur_a_str = p_addr_for_m[0] if len(p_addr_for_m) > 0 else ""
    edit_project_base_dialog(current_proj, cur_a_str)

if add_card_modal and current_proj:
    add_permit_dialog(current_proj)

if edit_phase_id and current_proj:
    edit_phase_dialog(int(edit_phase_id), current_proj)

if edit_title_flag:
    edit_main_title_dialog(get_main_title())

def render_top_header(title, show_create_btn=True):
    create_btn_html = ""
    if show_create_btn:
        create_btn_html = '<div><a href="?page=create" target="_self" class="create-proj-link">+ 새 프로젝트</a></div>'

    top_header_html = f"""
    <div style="display: flex; justify-content: space-between; align-items: center; width: {TOTAL_WIDTH}px;">
      <div class="hero-title-box">
        <a href="?" target="_self" class="hero-title-link" title="메인 대시보드로 이동">{title}</a>
        <a href="?edit_title=1" target="_self" class="title-edit-link" title="대제목 수정">✏️</a>
      </div>
      {create_btn_html}
    </div>
    """
    st.markdown(top_header_html, unsafe_allow_html=True)

# ==========================================
# PAGE 1: 신규 등록 (영구 고정)
# ==========================================
if current_page == "create":
    render_top_header(get_main_title(), show_create_btn=False)
    
    st.markdown(
        f"<div style='font-size: 1.25rem; font-weight: 750; color: #0f172a; margin-top: 1.5rem; margin-bottom: 0.8rem;'>"
        f"신규 프로젝트 등록"
        f"</div>", 
        unsafe_allow_html=True
    )

    with st.form("create_project_form"):
        p_name = st.text_input("프로젝트명 *", placeholder="예: 화성 안석리 단독주택").strip()
        site_address = st.text_input("대지위치 (00리까지 기본 주소)", placeholder="예: 경기도 화성시 남양읍 안석리").strip()

        c1, c2 = st.columns(2)
        with c1:
            client_name = st.text_input("건축주", placeholder="예: 홍길동").strip()
        with c2:
            p_work_type = st.selectbox("업무 구분 *", PERMIT_TYPES)

        d1, d2 = st.columns(2)
        with d1:
            assignee = st.text_input("담당자", placeholder="예: 김건축 소장").strip()
        with d2:
            reg_date = st.date_input("등록일", date.today())

        st.markdown("<div style='height: 14px;'></div>", unsafe_allow_html=True)

        btn_col1, btn_col2 = st.columns(2)
        with btn_col1:
            submitted = st.form_submit_button("등록 완료", type="primary", use_container_width=True)
        with btn_col2:
            cancel_clicked = st.form_submit_button("취소", use_container_width=True)

        if submitted:
            if p_name:
                now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                conn = get_connection()
                for ph in FIXED_PHASES:
                    st_val = "진행중" if ph == "기획설계" else "대기"
                    conn.execute("""
                        INSERT INTO tasks (project_name, work_type, phase, task_name, start_date, end_date, assignee, status, progress, updated_at, client_name, site_address)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (p_name, p_work_type, ph, assignee, st_val, now_str, client_name, site_address))
                
                empty_lots = json.dumps([{"lot": "", "category": "대", "doc_area": "", "act_area": "", "road_area": "", "excl_area": "", "note": ""}], ensure_ascii=False)
                conn.execute("""
                    INSERT INTO project_permits (
                        project_name, client_name, permit_type, lots_json, zone_district, road_condition,
                        main_use, structure, floors_up, height, building_area, total_floor_area,
                        far_area, bc_ratio, fa_ratio, parking_calc, parking_plan, septic_tank, landscaping, assignee, status
                    ) VALUES (
                        ?, ?, ?, ?, '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', ?, '진행중'
                    )
                """, (p_name, client_name, p_work_type, empty_lots, assignee))
                conn.commit()
                conn.close()
                st.query_params.clear()
                st.rerun()
            else:
                st.error("프로젝트명을 입력해 주세요.")
                
        if cancel_clicked:
            st.query_params.clear()
            st.rerun()

# ==========================================
# PAGE 2: 진행상세 페이지
# ==========================================
elif current_page == "detail" and current_proj:
    proj_name = current_proj

    render_top_header(get_main_title(), show_create_btn=False)

    proj_df = df[df["project_name"] == proj_name]
    first_row = proj_df.iloc[0] if not proj_df.empty else {}
    
    meta_addr_db = first_row.get("site_address") or ""
    meta_client = first_row.get("client_name") or ""
    meta_type = first_row.get("work_type") or "신축허가"
    encoded_proj_url = urllib.parse.quote(proj_name)

    contract_data = get_project_contract(proj_name)
    permits_list = get_project_permits_list(proj_name, default_client=meta_client, default_type=meta_type)

    if st.session_state.active_permit_idx >= len(permits_list):
        st.session_state.active_permit_idx = 0

    top_bar_html = f"""
    <div class="align-right-header-box">
      <div style="font-size: 1.45rem; font-weight: 750; color: #0f172a; line-height: 32px;">
        {proj_name} <span style="font-size: 0.85rem; font-weight: 500; color: #64748b; margin-left: 6px;">상세 관리</span>
      </div>
      <div>
        <a href="?page=detail&project={encoded_proj_url}&edit_proj_modal=1" target="_self" class="solid-red-btn">수정</a>
      </div>
    </div>
    """
    st.markdown(top_bar_html, unsafe_allow_html=True)

    # -------------------------------------------------------------
    # [1번 박스] 인덱스 탭 (기본정보 / 허가별연동일정 / 계약정보)
    # -------------------------------------------------------------
    st.markdown(
        f"<div class='section-title-box' style='margin-top: 0.8rem; margin-bottom: 0.35rem;'>"
        f"1. 프로젝트 기본정보 및 계약관리"
        f"</div>", 
        unsafe_allow_html=True
    )

    b1_tab_titles = ["📁 기본정보", "📁 인허가 및 공사 일정", "🔒 계약 정보 (보안)"]
    b1_tabs_html = ['<div class="card-tabs-container">']
    for idx, t_title in enumerate(b1_tab_titles):
        is_active = (idx == st.session_state.active_b1_tab)
        active_cls = " active-card-tab" if is_active else ""
        b1_tabs_html.append(
            f'<a href="?page=detail&project={encoded_proj_url}&set_b1_tab={idx}" target="_self" class="card-tab-item{active_cls}">{t_title}</a>'
        )
    b1_tabs_html.append('</div>')
    st.markdown("".join(b1_tabs_html), unsafe_allow_html=True)

    # [1번 박스 탭 0] 기본 정보 즉시 수정
    if st.session_state.active_b1_tab == 0:
        with st.form("inline_base_info_form"):
            ib_c1, ib_c2 = st.columns([1, 1])
            with ib_c1:
                in_pname = st.text_input("프로젝트명 *", value=proj_name).strip()
            with ib_c2:
                in_base_addr = st.text_input("대지위치 (00리 기본주소)", value=meta_addr_db, placeholder="예: 경기도 화성시 남양읍 안석리").strip()

            st.markdown("<div style='height: 4px;'></div>", unsafe_allow_html=True)
            if st.form_submit_button("기본정보 변경사항 저장", type="primary", use_container_width=True):
                if in_pname:
                    update_project_base_info(proj_name, in_pname, in_base_addr)
                    st.query_params.clear()
                    st.query_params["page"] = "detail"
                    st.query_params["project"] = in_pname
                    st.success("기본정보가 수정되었습니다.")
                    st.rerun()
                else:
                    st.error("프로젝트명을 입력해 주세요.")

    # [1번 박스 탭 1] 인허가 공사 일정 목록
    elif st.session_state.active_b1_tab == 1:
        with st.form("milestone_schedule_list_form"):
            st.markdown("<div style='font-size:0.92rem; font-weight:750; color:#0f172a; margin-bottom:8px;'>허가건별 주요 인허가 및 공정 일정 목록</div>", unsafe_allow_html=True)
            
            m_h1, m_h2, m_h3, m_h4, m_h5 = st.columns([1.6, 2.3, 1.8, 1.8, 1.8])
            with m_h1: st.caption("**건축주**")
            with m_h2: st.caption("**허가(신고)번호**")
            with m_h3: st.caption("**허가(신고)일**")
            with m_h4: st.caption("**착공(착수)일**")
            with m_h5: st.caption("**준공(사용승인)일**")

            milestone_inputs = {}
            for p_idx, p_item in enumerate(permits_list, start=1):
                cur_pid = p_item["id"]
                c_name = p_item.get("client_name") or f"건축주{p_idx}"
                m_info = get_permit_milestone(cur_pid, proj_name)

                mc1, mc2, mc3, mc4, mc5 = st.columns([1.6, 2.3, 1.8, 1.8, 1.8])
                with mc1:
                    st.markdown(f"<div style='font-size:0.88rem; font-weight:700; color:#1e293b; line-height:32px;'>{p_idx}. {c_name}</div>", unsafe_allow_html=True)
                with mc2:
                    v_no = st.text_input("허가번호", value=m_info.get("permit_no") or "", key=f"ms_no_{cur_pid}", label_visibility="collapsed", placeholder="예: 2026-건축과-123").strip()
                with mc3:
                    v_pdate = st.text_input("허가일", value=m_info.get("permit_date") or "", key=f"ms_pdate_{cur_pid}", label_visibility="collapsed", placeholder="예: 2026-03-15").strip()
                with mc4:
                    v_sdate = st.text_input("착공일", value=m_info.get("start_work_date") or "", key=f"ms_sdate_{cur_pid}", label_visibility="collapsed", placeholder="예: 2026-04-01").strip()
                with mc5:
                    v_cdate = st.text_input("준공일", value=m_info.get("complete_work_date") or "", key=f"ms_cdate_{cur_pid}", label_visibility="collapsed", placeholder="예: 2026-11-30").strip()

                milestone_inputs[cur_pid] = {
                    "no": v_no, "pdate": v_pdate, "sdate": v_sdate, "cdate": v_cdate
                }

            st.markdown("<div style='height: 6px;'></div>", unsafe_allow_html=True)
            if st.form_submit_button("모든 허가건 일정 저장", type="primary", use_container_width=True):
                for pid_key, vals in milestone_inputs.items():
                    save_permit_milestone(pid_key, proj_name, vals["no"], vals["pdate"], vals["sdate"], vals["cdate"])
                st.success("모든 허가건의 일정이 성공적으로 저장되었습니다.")
                st.rerun()

    # [1번 박스 탭 2] 비밀번호 인증 기반 보안 계약 정보
    elif st.session_state.active_b1_tab == 2:
        if not st.session_state.contract_auth_unlocked:
            with st.form("contract_auth_form"):
                st.markdown("<div style='font-size:0.95rem; font-weight:700; color:#0f172a;'>🔒 계약정보 열람 인증</div>", unsafe_allow_html=True)
                st.caption("민감한 금융 및 계약 정보 보호를 위해 비밀번호를 입력해 주세요.")
                in_auth_pw = st.text_input("관리자 비밀번호", type="password", placeholder="비밀번호 입력")
                if st.form_submit_button("인증 확인", type="primary", use_container_width=True):
                    if in_auth_pw == ADMIN_PASSWORD:
                        st.session_state.contract_auth_unlocked = True
                        st.rerun()
                    else:
                        st.error("비밀번호가 일치하지 않습니다.")
        else:
            with st.form("contract_detail_form"):
                c_top1, c_top2 = st.columns([TOTAL_WIDTH - 90, 90])
                with c_top1:
                    st.markdown("<div style='font-size:0.95rem; font-weight:750; color:#0f172a;'>📄 용역 계약 상세 내역</div>", unsafe_allow_html=True)
                with c_top2:
                    if st.form_submit_button("🔒 잠금", use_container_width=True):
                        st.session_state.contract_auth_unlocked = False
                        st.rerun()

                ct_c1, ct_c2, ct_c3 = st.columns([2, 2.5, 1.5])
                with ct_c1:
                    in_ct_date = st.text_input("계약 체결일", value=contract_data.get("contract_date") or "", placeholder="예: 2026-02-10").strip()
                with ct_c2:
                    in_ct_amount = st.text_input("총 계약금액 (원)", value=contract_data.get("contract_amount") or "", placeholder="예: 35,000,000").strip()
                with ct_c3:
                    vat_opts = ["포함", "별도", "면세"]
                    cur_vat = contract_data.get("vat_included") or "포함"
                    vat_idx = vat_opts.index(cur_vat) if cur_vat in vat_opts else 0
                    in_vat = st.selectbox("부가세", vat_opts, index=vat_idx)

                in_contractor = st.text_input("계약 상대방 (발주처/건축주)", value=contract_data.get("contractor_name") or meta_client, placeholder="예: 홍길동 (주식회사 대문)").strip()

                st.markdown("<div style='font-size:0.8rem; font-weight:700; color:#475569; margin:6px 0 2px 0;'>대금 분할 지급 조건</div>", unsafe_allow_html=True)
                pay_c1, pay_c2, pay_c3 = st.columns(3)
                with pay_c1:
                    in_deposit = st.text_input("계약금 조건", value=contract_data.get("deposit_terms") or "", placeholder="예: 계약시 30%").strip()
                with pay_c2:
                    in_mid = st.text_input("중도금 조건", value=contract_data.get("mid_terms") or "", placeholder="예: 허가접수시 40%").strip()
                with pay_c3:
                    in_balance = st.text_input("잔금 조건", value=contract_data.get("balance_terms") or "", placeholder="예: 허가완료시 30%").strip()

                in_notes = st.text_input("계약 특약사항 / 비고", value=contract_data.get("notes") or "", placeholder="예: 인허가 외 토목 및 구조설계비 포함 여부").strip()

                st.markdown("<div style='height: 4px;'></div>", unsafe_allow_html=True)
                if st.form_submit_button("계약정보 저장", type="primary", use_container_width=True):
                    save_project_contract(proj_name, {
                        "contract_date": in_ct_date,
                        "contract_amount": in_ct_amount,
                        "vat_included": in_vat,
                        "contractor_name": in_contractor,
                        "deposit_terms": in_deposit,
                        "mid_terms": in_mid,
                        "balance_terms": in_balance,
                        "notes": in_notes
                    })
                    st.success("계약 정보가 안전하게 저장되었습니다.")
                    st.rerun()

    # -------------------------------------------------------------
    # 2번 박스: 허가별 대지/건축개요 타이틀 & 우측 '+ 카드 추가'
    # -------------------------------------------------------------
    b2_header_html = f"""
    <div class="align-right-header-box" style="margin-top: 1.1rem; margin-bottom: 0.35rem;">
      <div class="section-title-box" style="margin: 0;">
        2. 허가별 대지 및 건축개요 (도면 양식)
      </div>
      <div>
        <a href="?page=detail&project={encoded_proj_url}&add_card_modal=1" target="_self" class="text-action-link">＋ 카드 추가</a>
      </div>
    </div>
    """
    st.markdown(b2_header_html, unsafe_allow_html=True)

    tabs_html = ['<div class="card-tabs-container">']
    for idx, p_item in enumerate(permits_list, start=1):
        c_raw = p_item.get("client_name")
        c_label = f"📁 {c_raw}" if c_raw else f"📁 허가건 {idx}"
        is_active = ((idx - 1) == st.session_state.active_permit_idx)
        active_cls = " active-card-tab" if is_active else ""
        tabs_html.append(
            f'<a href="?page=detail&project={encoded_proj_url}&set_permit={idx-1}" target="_self" class="card-tab-item{active_cls}" title="{c_label}">{c_label}</a>'
        )
    tabs_html.append('</div>')
    st.markdown("".join(tabs_html), unsafe_allow_html=True)

    active_permit = permits_list[st.session_state.active_permit_idx]
    pid = active_permit["id"]

    raw_lots_json = active_permit.get("lots_json") or "[]"
    try:
        lots_data = json.loads(raw_lots_json)
        if not lots_data:
            lots_data = [{"lot": "", "category": "대", "doc_area": "", "act_area": "", "road_area": "", "excl_area": "", "note": ""}]
    except Exception:
        lots_data = [{"lot": "", "category": "대", "doc_area": "", "act_area": "", "road_area": "", "excl_area": "", "note": ""}]

    with st.form(f"cad_overview_form_{pid}"):
        t_c1, t_c2, t_c3 = st.columns([2.4, 2.6, 2.0])
        with t_c1:
            in_client = st.text_input("건축주 성명", value=active_permit.get("client_name") or "", key=f"cname_{pid}", placeholder="건축주 성명 입력").strip()
        with t_c2:
            current_ptype = active_permit.get("permit_type") or "신축허가"
            idx_ptype = PERMIT_TYPES.index(current_ptype) if current_ptype in PERMIT_TYPES else 0
            in_ptype = st.selectbox("허가 구분 *", PERMIT_TYPES, index=idx_ptype, key=f"ptype_{pid}")
        with t_c3:
            in_pm = st.text_input("담당자 / PM", value=active_permit.get("assignee") or "", placeholder="예: 김건축", key=f"pm_{pid}").strip()

        st.markdown("<hr style='margin: 10px 0; border: none; border-top: 1px solid #e2e8f0;'>", unsafe_allow_html=True)

        st.markdown('<div class="cad-table-title">대 지 개 요</div>', unsafe_allow_html=True)
        
        d_r1_c1, d_r1_c2 = st.columns(2)
        with d_r1_c1:
            in_zone = st.text_input("지역 / 지구", value=active_permit.get("zone_district") or "", placeholder="예: 생산관리지역, 성장관리계획구역", key=f"zone_{pid}").strip()
        with d_r1_c2:
            in_road = st.text_input("도로 관계", value=active_permit.get("road_condition") or "", placeholder="예: 너비 3m 이상 도로, 12.3m 접함", key=f"road_{pid}").strip()

        st.markdown("<div style='font-size:0.82rem; font-weight:700; color:#475569; margin: 8px 0 4px 0;'>구분별 대지개요 (지번별 면적 산출표)</div>", unsafe_allow_html=True)
        
        lh_c1, lh_c2, lh_c3, lh_c4, lh_c5, lh_c6, lh_c7, lh_c8 = st.columns([1.5, 0.9, 1.3, 1.3, 1.2, 1.2, 1.6, 0.5])
        with lh_c1: st.caption("**지번**")
        with lh_c2: st.caption("**지목**")
        with lh_c3: st.caption("**공부면적**")
        with lh_c4: st.caption("**실사면적**")
        with lh_c5: st.caption("**도로화**")
        with lh_c6: st.caption("**제외지**")
        with lh_c7: st.caption("**비고**")
        with lh_c8: st.caption("")

        curr_lot_rows = []
        tot_doc = 0.0
        tot_act = 0.0
        tot_road = 0.0
        tot_excl = 0.0

        for l_idx, l_val in enumerate(lots_data):
            lc1, lc2, lc3, lc4, lc5, lc6, lc7, lc8 = st.columns([1.5, 0.9, 1.3, 1.3, 1.2, 1.2, 1.6, 0.5])
            with lc1:
                v_lot = st.text_input("지번", value=l_val.get("lot", ""), key=f"l_lot_{pid}_{l_idx}", label_visibility="collapsed", placeholder="지번").strip()
            with lc2:
                v_cat = st.text_input("지목", value=l_val.get("category", ""), key=f"l_cat_{pid}_{l_idx}", label_visibility="collapsed", placeholder="대").strip()
            with lc3:
                v_doc = st.text_input("공부면적", value=l_val.get("doc_area", ""), key=f"l_doc_{pid}_{l_idx}", label_visibility="collapsed", placeholder="0.00").strip()
            with lc4:
                v_act = st.text_input("실사면적", value=l_val.get("act_area", ""), key=f"l_act_{pid}_{l_idx}", label_visibility="collapsed", placeholder="0.00").strip()
            with lc5:
                v_road = st.text_input("도로화", value=l_val.get("road_area", ""), key=f"l_road_{pid}_{l_idx}", label_visibility="collapsed", placeholder="-").strip()
            with lc6:
                v_excl = st.text_input("제외지", value=l_val.get("excl_area", ""), key=f"l_excl_{pid}_{l_idx}", label_visibility="collapsed", placeholder="-").strip()
            with lc7:
                v_note = st.text_input("비고", value=l_val.get("note", ""), key=f"l_note_{pid}_{l_idx}", label_visibility="collapsed", placeholder="비고").strip()
            
            with lc8:
                if l_idx == 0:
                    btn_html = f'<a href="?page=detail&project={encoded_proj_url}&action_lot_add=1" target="_self" class="symbol-btn" title="필지 행 추가">＋</a>'
                else:
                    btn_html = f'<a href="?page=detail&project={encoded_proj_url}&action_lot_del={l_idx}" target="_self" class="symbol-btn" title="해당 행 삭제">－</a>'
                st.markdown(btn_html, unsafe_allow_html=True)

            curr_lot_rows.append({
                "lot": v_lot, "category": v_cat, "doc_area": v_doc,
                "act_area": v_act, "road_area": v_road, "excl_area": v_excl, "note": v_note
            })

            try: tot_doc += float(v_doc.replace(",", "")) if v_doc and v_doc != "-" else 0.0
            except Exception: pass
            try: tot_act += float(v_act.replace(",", "")) if v_act and v_act != "-" else 0.0
            except Exception: pass
            try: tot_road += float(v_road.replace(",", "")) if v_road and v_road != "-" else 0.0
            except Exception: pass
            try: tot_excl += float(v_excl.replace(",", "")) if v_excl and v_excl != "-" else 0.0
            except Exception: pass

        st.markdown(
            f"""
            <div class="cad-summary-box">
                <span style="font-weight:750; color:#1e293b;">합 계 (계)</span>
                <span>공부상: <b>{tot_doc:,.2f} ㎡</b></span>
                <span style="color:#2563eb;">실사(대지면적): <b>{tot_act:,.2f} ㎡</b></span>
                <span>도로화: <b>{tot_road:,.2f} ㎡</b></span>
                <span>제외지: <b>{tot_excl:,.2f} ㎡</b></span>
            </div>
            """, 
            unsafe_allow_html=True
        )

        st.markdown("<hr style='margin: 10px 0; border: none; border-top: 1px solid #e2e8f0;'>", unsafe_allow_html=True)

        st.markdown('<div class="cad-table-title">건 축 개 요</div>', unsafe_allow_html=True)

        b_r1_c1, b_r1_c2 = st.columns([3, 1])
        with b_r1_c1:
            in_use = st.text_input("공사명 / 주용도", value=active_permit.get("main_use") or "", placeholder="예: 단독주택 / 제1종 근린생활시설", key=f"use_{pid}").strip()
        with b_r1_c2:
            in_h = st.text_input("최고 높이", value=active_permit.get("height") or "", placeholder="예: 8.5 m", key=f"h_{pid}").strip()

        b_r2_c1, b_r2_c2, b_r2_c3 = st.columns(3)
        with b_r2_c1:
            in_b_area = st.text_input("건축면적 (㎡)", value=active_permit.get("building_area") or "", placeholder="예: 120.00", key=f"ba_{pid}").strip()
        with b_r2_c2:
            in_t_area = st.text_input("연면적 (㎡)", value=active_permit.get("total_floor_area") or "", placeholder="예: 200.00", key=f"ta_{pid}").strip()
        with b_r2_c3:
            in_far_area = st.text_input("용적률 산정용 연면적 (㎡)", value=active_permit.get("far_area") or "", placeholder="예: 200.00", key=f"far_{pid}").strip()

        calc_site_area = tot_act if tot_act > 0 else 0.0
        
        auto_bc_str = ""
        auto_bc_val = ""
        try:
            val_bldg = float(in_b_area.replace(",", ""))
            if calc_site_area > 0:
                num_bc = round((val_bldg / calc_site_area) * 100, 2)
                auto_bc_val = f"{num_bc:.2f}"
                auto_bc_str = f"{val_bldg:,.2f} / {calc_site_area:,.2f} = {auto_bc_val}%"
        except Exception:
            pass

        auto_fa_str = ""
        auto_fa_val = ""
        try:
            val_far = float(in_far_area.replace(",", "")) if in_far_area else float(in_t_area.replace(",", ""))
            if calc_site_area > 0:
                num_fa = round((val_far / calc_site_area) * 100, 2)
                auto_fa_val = f"{num_fa:.2f}"
                auto_fa_str = f"{val_far:,.2f} / {calc_site_area:,.2f} = {auto_fa_val}%"
        except Exception:
            pass

        if auto_bc_str or auto_fa_str:
            st.markdown(
                f"""
                <div class="ratio-calc-preview">
                    <span>📐 <b>건폐율 자동계산식:</b> {auto_bc_str if auto_bc_str else '-'}</span>
                    <span>🏢 <b>용적률 자동계산식:</b> {auto_fa_str if auto_fa_str else '-'}</span>
                </div>
                """,
                unsafe_allow_html=True
            )

        bc_key = f"bc_{pid}"
        fa_key = f"fa_{pid}"
        if auto_bc_val:
            st.session_state[bc_key] = auto_bc_val
        elif bc_key not in st.session_state:
            st.session_state[bc_key] = active_permit.get("bc_ratio") or ""

        if auto_fa_val:
            st.session_state[fa_key] = auto_fa_val
        elif fa_key not in st.session_state:
            st.session_state[fa_key] = active_permit.get("fa_ratio") or ""

        b_r3_c1, b_r3_c2 = st.columns(2)
        with b_r3_c1:
            in_bc = st.text_input("건폐율 (%)", key=bc_key, placeholder="자동 계산값 기입됨").strip()
        with b_r3_c2:
            in_fa = st.text_input("용적률 (%)", key=fa_key, placeholder="자동 계산값 기입됨").strip()

        b_r4_c1, b_r4_c2 = st.columns(2)
        with b_r4_c1:
            in_floors = st.text_input("규 모 (층수)", value=active_permit.get("floors_up") or "", placeholder="예: 지상 2층 / 지하 -층", key=f"fl_{pid}").strip()
        with b_r4_c2:
            in_struct = st.text_input("구 조 (주구조)", value=active_permit.get("structure") or "", placeholder="예: 철근콘크리트구조", key=f"struct_{pid}").strip()

        b_r5_c1, b_r5_c2 = st.columns(2)
        with b_r5_c1:
            in_p_calc = st.text_input("주차 산정식 (법정)", value=active_permit.get("parking_calc") or "", placeholder="예: 200㎡ 당 1대 = 법정 2대", key=f"pcalc_{pid}").strip()
        with b_r5_c2:
            in_p_plan = st.text_input("시설 계획 주차대수", value=active_permit.get("parking_plan") or "", placeholder="예: 옥외 자주식 2대", key=f"pplan_{pid}").strip()

        b_r6_c1, b_r6_c2 = st.columns(2)
        with b_r6_c1:
            in_septic = st.text_input("정화조 / 오수처리시설", value=active_permit.get("septic_tank") or "", placeholder="예: 오수처리시설 (5Ton)", key=f"septic_{pid}").strip()
        with b_r6_c2:
            in_land = st.text_input("조 경 (면적 및 식재)", value=active_permit.get("landscaping") or "", placeholder="예: 조경면적 제외 대상", key=f"land_{pid}").strip()

        st.markdown("<div style='height: 8px;'></div>", unsafe_allow_html=True)
        save_card_clicked = st.form_submit_button("도면 대지·건축개요 저장", type="primary", use_container_width=True)

        if save_card_clicked:
            payload = {
                "client_name": in_client,
                "permit_type": in_ptype,
                "lots_json": json.dumps(curr_lot_rows, ensure_ascii=False),
                "zone_district": in_zone,
                "road_condition": in_road,
                "main_use": in_use,
                "structure": in_struct,
                "floors_up": in_floors,
                "height": in_h,
                "building_area": in_b_area,
                "total_floor_area": in_t_area,
                "far_area": in_far_area,
                "bc_ratio": in_bc,
                "fa_ratio": in_fa,
                "parking_calc": in_p_calc,
                "parking_plan": in_p_plan,
                "septic_tank": in_septic,
                "landscaping": in_land,
                "assignee": in_pm
            }
            save_cad_permit_overview(pid, proj_name, payload)
            st.success("도면 대지 및 건축개요가 저장되었습니다.")
            st.rerun()

    # 3번 박스: 세부 공정 목록
    st.markdown(
        f"<div class='section-title-box' style='margin-top: 1.4rem; margin-bottom: 0.5rem;'>"
        f"3. 세부 공정 목록 <span style='font-size: 0.82rem; font-weight: 500; color: #64748b;'>표준 6대 설계단계</span>"
        f"</div>", 
        unsafe_allow_html=True
    )

    fixed_tasks = get_or_create_fixed_phases(proj_name, work_type=meta_type)

    t_header = (
        '<div class="grid-row-detail grid-header">'
        '<div class="cell cell-center">No</div>'
        '<div class="cell">설계 단계</div>'
        '<div class="cell">세부 업무 내용</div>'
        '<div class="cell cell-center">진행률</div>'
        '<div class="cell cell-center">상태</div>'
        '<div class="cell cell-center">수정</div>'
        '</div>'
    )

    t_rows = []
    for idx, r in enumerate(fixed_tasks, start=1):
        task_id = r["id"]
        phase_str = r.get("phase", "-")
        t_name = r.get("task_name") or "-"
        prog = r.get("progress", 0)
        status_str = r.get("status", "대기")

        if status_str == "진행중":
            st_badge = '<span class="badge-ing">진행중</span>'
        elif status_str == "완료":
            st_badge = '<span class="badge-done">완료</span>'
        else:
            st_badge = '<span style="font-size:11px; color:#94a3b8; font-weight:600;">대기</span>'

        row_h = (
            '<div class="grid-row-detail">'
            f'<div class="cell cell-center" style="color:#94a3b8; font-size:11px;">{idx}</div>'
            f'<div class="cell" style="font-weight:700; color:#1e293b;">{phase_str}</div>'
            f'<div class="cell" style="color:#334155;" title="{t_name}">{t_name}</div>'
            f'<div class="cell cell-center" style="font-weight:600; color:#2563eb; font-size:11.5px;">{prog}%</div>'
            f'<div class="cell cell-center">{st_badge}</div>'
            f'<div class="cell cell-center">'
            f'<a href="?page=detail&project={encoded_proj_url}&edit_phase={task_id}" target="_self" class="icon-action-link" title="내용 수정">✏️</a>'
            f'</div>'
            '</div>'
        )
        t_rows.append(row_h)

    st.markdown(f'<div class="table-container-detail">{t_header}{"".join(t_rows)}</div>', unsafe_allow_html=True)

    # 대시보드 하단 외부 링크 버튼 (법제처, 토지이음, 세움터)
    footer_links_html = f"""
    <div class="footer-link-container">
      <a href="https://www.law.go.kr" target="_blank" class="footer-link-btn">🏛️ 법제처 (국가법령정보)</a>
      <a href="https://www.eum.go.kr" target="_blank" class="footer-link-btn">🗺️ 토지이음 (토지이용계획)</a>
      <a href="https://www.eais.go.kr" target="_blank" class="footer-link-btn">🏢 세움터 (건축행정시스템)</a>
    </div>
    """
    st.markdown(footer_links_html, unsafe_allow_html=True)

# ==========================================
# PAGE 3: 메인 대시보드 (영구 고정)
# ==========================================
else:
    main_title = get_main_title()
    render_top_header(main_title, show_create_btn=True)

    total_proj = df["project_name"].nunique() if not df.empty else 0
    ongoing_tasks = len(df[df["status"] == "진행중"]) if not df.empty else 0

    pre_permit_projects = set()
    permit_exec_projects = set()
    construction_projects = set()
    ongoing_task_projects = set()

    if not df.empty:
        for p in df["project_name"].unique():
            p_sub = df[df["project_name"] == p]
            if any(p_sub["status"] == "진행중"):
                ongoing_task_projects.add(p)

            pending_sub = p_sub[p_sub["status"] == "진행중"]
            if not pending_sub.empty:
                curr_phase = pending_sub.iloc[0]["phase"]
            else:
                waiting_sub = p_sub[p_sub["status"] != "완료"]
                curr_phase = waiting_sub.iloc[0]["phase"] if not waiting_sub.empty else p_sub.iloc[-1]["phase"]

            if curr_phase in ["기획설계", "계획설계"]:
                pre_permit_projects.add(p)
            elif curr_phase in ["실시설계", "허가중"]:
                permit_exec_projects.add(p)
            else:
                construction_projects.add(p)

    pre_permit_cnt = len(pre_permit_projects)
    permit_exec_cnt = len(permit_exec_projects)
    construction_cnt = len(construction_projects)

    c_all_active = " active-filter" if active_filter is None or active_filter == "all" else ""
    c_ongoing_active = " active-filter" if active_filter == "ongoing" else ""
    c_permit_active = " active-filter" if active_filter == "permit" else ""
    c_start_active = " active-filter" if active_filter == "start" else ""
    c_complete_active = " active-filter" if active_filter == "complete" else ""

    kpi_html = f"""
    <div class="kpi-grid">
        <a href="?filter=all" target="_self" class="kpi-card-link{c_all_active}" title="전체 진행 프로젝트 보기">
            <div class="kpi-label">진행 중 프로젝트</div>
            <div class="kpi-value">{total_proj} <span style="font-size:0.95rem; color:#64748b;">개</span></div>
        </a>
        <a href="?filter=ongoing" target="_self" class="kpi-card-link{c_ongoing_active}" title="진행중 업무가 있는 프로젝트만 보기">
            <div class="kpi-label">활성 공정 프로젝트</div>
            <div class="kpi-value">{len(ongoing_task_projects)} <span style="font-size:0.95rem; color:#64748b;">개</span></div>
        </a>
        <a href="?filter=permit" target="_self" class="kpi-card-link{c_permit_active}" style="border-left: 3px solid #3b82f6;" title="기획/계획설계 현장">
            <div class="kpi-label" style="color: #2563eb;">기획 / 계획설계</div>
            <div class="kpi-value" style="color: #1d4ed8;">{pre_permit_cnt} <span style="font-size:0.95rem; color:#64748b;">개</span></div>
        </a>
    </div>
    """
    st.markdown(kpi_html, unsafe_allow_html=True)

    progress_kpi_html = f"""
    <div class="kpi-grid-sub">
        <a href="?filter=start" target="_self" class="kpi-card-link{c_start_active}" style="border-left: 3px solid #f59e0b;" title="실시설계/허가중 현장">
            <div class="kpi-label" style="color: #d97706;">실시설계 / 허가중</div>
            <div class="kpi-value" style="color: #b45309;">{permit_exec_cnt} <span style="font-size:0.95rem; color:#64748b;">개</span></div>
        </a>
        <a href="?filter=complete" target="_self" class="kpi-card-link{c_complete_active}" style="border-left: 3px solid #10b981;" title="착공상태/준공대기 현장">
            <div class="kpi-label" style="color: #059669;">착공상태 / 준공대기</div>
            <div class="kpi-value" style="color: #047857;">{construction_cnt} <span style="font-size:0.95rem; color:#64748b;">개</span></div>
        </a>
    </div>
    """
    st.markdown(progress_kpi_html, unsafe_allow_html=True)

    filter_label_map = {
        "ongoing": "활성 공정 진행 현장",
        "permit": "기획 / 계획설계",
        "start": "실시설계 / 허가중",
        "complete": "착공상태 / 준공대기"
    }
    cur_filter_text = filter_label_map.get(active_filter, None)

    t_col, s_col = st.columns([TOTAL_WIDTH - 220, 220])
    with t_col:
        filter_badge = ""
        if cur_filter_text:
            filter_badge = f"<span style='font-size:0.75rem; background:#eff6ff; color:#2563eb; border:1px solid #bfdbfe; border-radius:4px; padding:2px 6px; margin-left:6px; font-weight:600;'>필터: {cur_filter_text}</span> <a href='?' target='_self' style='font-size:0.75rem; color:#94a3b8; text-decoration:none; margin-left:4px;'>[해제 ✕]</a>"
        
        st.markdown(
            f"<div style='font-size:1.15rem; font-weight:750; color:#0f172a; line-height:32px;'>"
            f"프로젝트 진행 현황 "
            f"<span style='font-size:0.85rem; font-weight:500; color:#64748b; margin-left:4px;'>총 {total_proj}건</span>"
            f"{filter_badge}"
            f"</div>", 
            unsafe_allow_html=True
        )
    with s_col:
        search_kw = st.text_input("검색", placeholder="🔍 프로젝트명 검색...", label_visibility="collapsed").strip()

    if not df.empty:
        latest_updates = df.groupby("project_name")["updated_at"].max().to_dict()
        
        sorted_projects_by_update = sorted(
            latest_updates.keys(), 
            key=lambda p: str(latest_updates.get(p, "")), 
            reverse=True
        )

        if active_filter == "ongoing":
            base_projects = [p for p in sorted_projects_by_update if p in ongoing_task_projects]
        elif active_filter == "permit":
            base_projects = [p for p in sorted_projects_by_update if p in pre_permit_projects]
        elif active_filter == "start":
            base_projects = [p for p in sorted_projects_by_update if p in permit_exec_projects]
        elif active_filter == "complete":
            base_projects = [p for p in sorted_projects_by_update if p in construction_projects]
        else:
            base_projects = sorted_projects_by_update

        if search_kw:
            filtered_projects = [p for p in base_projects if search_kw.lower() in p.lower()]
        else:
            filtered_projects = base_projects

        PAGE_SIZE = 10
        total_filtered = len(filtered_projects)
        max_page = max(1, (total_filtered + PAGE_SIZE - 1) // PAGE_SIZE)
        
        if st.session_state.page_num > max_page:
            st.session_state.page_num = max_page
            
        start_idx = (st.session_state.page_num - 1) * PAGE_SIZE
        end_idx = start_idx + PAGE_SIZE
        page_projects = filtered_projects[start_idx:end_idx]

        header_row = (
            '<div class="grid-row grid-header">'
            '<div class="cell cell-center">No</div>'
            '<div class="cell">프로젝트명</div>'
            '<div class="cell">업무 구분</div>'
            '<div class="cell">설계 단계</div>'
            '<div class="cell">상태</div>'
            '<div class="cell cell-center">최종수정</div>'
            '<div class="cell cell-center"></div>'
            '</div>'
        )

        body_rows = []
        for offset, p_name in enumerate(page_projects, start=1):
            row_no = start_idx + offset
            p_df = df[df["project_name"] == p_name]
            w_type = p_df.iloc[0].get("work_type", "신축허가")
            if pd.isna(w_type) or not w_type:
                w_type = "신축허가"
            
            p_ing = p_df[p_df["status"] == "진행중"]
            if not p_ing.empty:
                curr_phase = p_ing.iloc[0]["phase"]
                badge_html = '<span class="badge-ing">진행중</span>'
            else:
                p_wait = p_df[p_df["status"] != "완료"]
                curr_phase = p_wait.iloc[0]["phase"] if not p_wait.empty else p_df.iloc[-1]["phase"]
                badge_html = '<span class="badge-done">완료</span>' if p_wait.empty else '<span class="badge-ing">진행중</span>'
            
            encoded_proj = urllib.parse.quote(p_name)

            raw_update = str(latest_updates.get(p_name, ""))
            if len(raw_update) >= 16:
                yy = raw_update[2:4]
                mm = raw_update[5:7]
                dd = raw_update[8:10]
                hhmm = raw_update[11:16]
                display_time = f"{yy}.{mm}.{dd} {hhmm}"
            else:
                display_time = "-"

            row_item = (
                '<div class="grid-row">'
                f'<div class="cell cell-center" style="color: #94a3b8; font-size: 11px;">{row_no}</div>'
                f'<div class="cell"><a href="?page=detail&project={encoded_proj}" target="_self" class="board-link" title="{p_name}">{p_name}</a></div>'
                f'<div class="cell" style="color: #334155;">{w_type}</div>'
                f'<div class="cell" style="font-weight: 700; color: #1e293b;">{curr_phase}</div>'
                f'<div class="cell">{badge_html}</div>'
                f'<div class="cell cell-center" style="color: #64748b; font-size: 11.5px;">{display_time}</div>'
                f'<div class="cell cell-center"><a href="?del_proj={encoded_proj}" target="_self" class="del-btn-link" title="프로젝트 삭제">🗑️</a></div>'
                '</div>'
            )
            body_rows.append(row_item)

        full_table_html = f'<div class="table-container">{header_row}{"".join(body_rows)}</div>'
        st.markdown(full_table_html, unsafe_allow_html=True)

        if max_page > 1:
            p_col1, p_col2, p_col3 = st.columns([4, 2, 4])
            with p_col2:
                btn_prev, info_col, btn_next = st.columns([1, 2, 1])
                with btn_prev:
                    if st.session_state.page_num > 1:
                        if st.button("◀", key="page_prev"):
                            st.session_state.page_num -= 1
                            st.rerun()
                with info_col:
                    st.markdown(f"<div style='text-align:center; font-size:0.85rem; color:#64748b; line-height:30px;'>{st.session_state.page_num} / {max_page}</div>", unsafe_allow_html=True)
                with btn_next:
                    if st.session_state.page_num < max_page:
                        if st.button("▶", key="page_next"):
                            st.session_state.page_num += 1
                            st.rerun()
    else:
        st.info("등록된 프로젝트가 없습니다.")

    # 메인 대시보드 하단 외부 링크 버튼 (법제처, 토지이음, 세움터)
    footer_links_html = f"""
    <div class="footer-link-container">
      <a href="https://www.law.go.kr" target="_blank" class="footer-link-btn">🏛️ 법제처 (국가법령정보)</a>
      <a href="https://www.eum.go.kr" target="_blank" class="footer-link-btn">🗺️ 토지이음 (토지이용계획)</a>
      <a href="https://www.eais.go.kr" target="_blank" class="footer-link-btn">🏢 세움터 (건축행정시스템)</a>
    </div>
    """
    st.markdown(footer_links_html, unsafe_allow_html=True)