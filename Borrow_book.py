#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Library Manager (Borrow-Return focused) - Single File
- Binary storage: books.bin, members.bin, loans.bin (struct pack/unpack)
- Menus: Add Book, Add Member (Name/Phone/Address), Borrow, Return, Reports, View/Find
- Report (.txt) table: MemberID, Name, Phone, Address, BookID, Title, Author, Year, Loan/Return dates, Status
- Safe IO (flush/fsync), fixed-length UTF-8 strings, interactive pretty tables
- 100% Python Standard Library

"""

import os
import struct
import time
import datetime
import textwrap
import shutil
from collections import Counter

# =============================================================================
# Configuration
# =============================================================================

DATA_DIR = "data"
BOOKS_FILE   = os.path.join(DATA_DIR, "books.bin")
MEMBERS_FILE = os.path.join(DATA_DIR, "members.bin")
LOANS_FILE   = os.path.join(DATA_DIR, "loans.bin")
REPORT_FILE  = os.path.join(DATA_DIR, "report.txt")

# Fixed-length byte sizes
TITLE_LEN  = 60   # Book title
AUTHOR_LEN = 40   # Book author
NAME_LEN   = 60   # Member name
PHONE_LEN  = 20   # Member phone
ADDR_LEN   = 100  # Member address

# Structs (little-endian)
# Book: id(I), title(60s), author(40s), year(H), total(H), available(H), active(B), pad(x), last_modified(I)
BOOK_STRUCT   = struct.Struct(f"<I{TITLE_LEN}s{AUTHOR_LEN}sHHHBxI")
# Member: id(I), name(60s), phone(20s), address(100s), active(B), pad(3x), last_modified(I)
MEMBER_STRUCT = struct.Struct(f"<I{NAME_LEN}s{PHONE_LEN}s{ADDR_LEN}sB3xI")
# Loan: id(I), book_id(I), member_id(I), borrow_ts(I), return_ts(I), active(B), pad(3x), last_modified(I)
LOAN_STRUCT   = struct.Struct("<IIIIIB3xI")

BOOK_SIZE   = BOOK_STRUCT.size
MEMBER_SIZE = MEMBER_STRUCT.size
LOAN_SIZE   = LOAN_STRUCT.size

# Make data dir
os.makedirs(DATA_DIR, exist_ok=True)

# =============================================================================
# Utilities
# =============================================================================

def now_ts() -> int:
    return int(time.time())


def fmt_ts(ts: int) -> str:
    if ts == 0:
        return "-"
  
    return datetime.datetime.fromtimestamp(ts).strftime("%Y-%m-%d")

def fmt_ts_full(ts: int) -> str:
    if ts == 0:
        return "-"
    return datetime.datetime.fromtimestamp(ts).strftime("%Y-%m-%d %H:%M:%S")

def pack_fixed_str(s: str, length: int) -> bytes:
    b = s.encode("utf-8")[:length]
    return b + b"\x00" * (length - len(b))

def unpack_fixed_str(b: bytes) -> str:
    return b.split(b"\x00", 1)[0].decode("utf-8", errors="ignore")

def ensure_file(path: str) -> None:
    if not os.path.exists(path):
        with open(path, "wb") as f:
            pass

def read_all_records(path: str, struct_obj: struct.Struct):
    """Return list[(index, tuple(values))]"""
    ensure_file(path)
    out = []
    with open(path, "rb") as f:
        i = 0
        while True:
            chunk = f.read(struct_obj.size)
            if not chunk or len(chunk) < struct_obj.size:
                break
            out.append((i, struct_obj.unpack(chunk)))
            i += 1
    return out

def append_record(path: str, struct_obj: struct.Struct, packed_bytes: bytes) -> None:
    ensure_file(path)
    with open(path, "ab") as f:
        f.write(packed_bytes)
        f.flush()
        os.fsync(f.fileno())

def write_record_at(path: str, struct_obj: struct.Struct, index: int, packed_bytes: bytes) -> None:
    ensure_file(path)
    with open(path, "r+b") as f:
        f.seek(index * struct_obj.size)
        f.write(packed_bytes)
        f.flush()
        os.fsync(f.fileno())

def get_next_id(path: str, struct_obj: struct.Struct) -> int:
    ensure_file(path)
    size = os.path.getsize(path)
    if size == 0:
        return 1
    count = size // struct_obj.size
    with open(path, "rb") as f:
        f.seek((count - 1) * struct_obj.size)
        last = struct_obj.unpack(f.read(struct_obj.size))
        return int(last[0]) + 1

def safe_input(prompt, validator=None, allow_empty=False):
    while True:
        try:
            s = input(prompt).strip()
        except EOFError:
            return ""
        if s == "" and allow_empty:
            return s
        if validator is None:
            return s
        try:
            return validator(s)
        except Exception as e:
            print("Invalid input:", e)

# =============================================================================
# Pretty table
# =============================================================================

def print_table(headers, rows):
    col_widths = [len(h) for h in headers]
    for row in rows:
        for i, cell in enumerate(row):
            col_widths[i] = max(col_widths[i], len(str(cell)))
    line = "+" + "+".join("-" * (w + 2) for w in col_widths) + "+"
    print(line)
    print("|" + "|".join(f" {headers[i]:<{col_widths[i]}} " for i in range(len(headers))) + "|")
    print(line)
    for row in rows:
        print("|" + "|".join(f" {str(row[i]):<{col_widths[i]}} " for i in range(len(row))) + "|")
    print(line)

# =============================================================================
# BOOK domain
# =============================================================================

def add_book():
    print("-- Add Book --")
    title = safe_input("Title: ")
    author = safe_input("Author: ")
    year = safe_input("Year (e.g., 2024): ", int)
    total = safe_input("Total copies: ", int)
    bid = get_next_id(BOOKS_FILE, BOOK_STRUCT)

 
    print("\nPlease confirm the book information:")
    print(f"  ID     : {bid}")
    print(f"  Title  : {title}")
    print(f"  Author : {author}")
    print(f"  Year   : {year}")
    print(f"  Total  : {total}")
    print(f"  Avail. : {total}")

  
    confirm = input("Save this book? (y/n): ").strip().lower()
    if confirm not in ["y", "yes"]:
        print("Add book canceled.")
        return

    
    packed = BOOK_STRUCT.pack(
        bid,
        pack_fixed_str(title, TITLE_LEN),
        pack_fixed_str(author, AUTHOR_LEN),
        int(year),
        int(total),
        int(total), 
        1,           
        now_ts()
    )
    append_record(BOOKS_FILE, BOOK_STRUCT, packed)
    print(f"Added Book id={bid}")

def update_book():
    print("-- Update Book --")

    books = list_books()
    print("+----+---------------------------+------------------+------+-------+----------+")
    print("| ID | Title                     | Author           | Year | Total | Available|")
    print("+----+---------------------------+------------------+------+-------+----------+")
    for b in books:
        print(f"|{b['id']:<3} | {b['title'][:25]:<25} | {b['author'][:16]:<16} | {b['year']:<4} | {b['total']:<5} | {b['available']:<8}|")
    print("+----+---------------------------+------------------+------+-------+----------+")

    bid = safe_input("Enter Book ID to update: ", int)
    idx, book = find_book_by_id(bid)
    if not book:
        print("Book not found")
        return

    print("Leave blank to keep current value.")
    new_title  = safe_input(f"Title [{book['title']}]: ", allow_empty=True)
    new_author = safe_input(f"Author [{book['author']}]: ", allow_empty=True)
    new_year   = safe_input(f"Year [{book['year']}]: ", lambda s: int(s) if s else book['year'], allow_empty=True)
    new_total  = safe_input(f"Total copies [{book['total']}]: ", lambda s: int(s) if s else book['total'], allow_empty=True)

    updated_title = new_title if new_title else book['title']
    updated_author = new_author if new_author else book['author']
    updated_year = int(new_year)
    updated_total = int(new_total)

    diff = updated_total - book['total']
    updated_available = max(0, book['available'] + diff)


    print("\nPlease confirm the updated book information:")
    print(f"  ID       : {book['id']}")
    print(f"  Title    : {updated_title}")
    print(f"  Author   : {updated_author}")
    print(f"  Year     : {updated_year}")
    print(f"  Total    : {updated_total}")
    print(f"  Available: {updated_available}")
    print(f"  Status   : {'Active' if book['active'] else 'Deleted'}")

   
    confirm = input("Save changes? (y/n): ").strip().lower()
    if confirm not in ["y", "yes"]:
        print("Update canceled.")
        return

    
    packed = BOOK_STRUCT.pack(
        book['id'],
        pack_fixed_str(updated_title, TITLE_LEN),
        pack_fixed_str(updated_author, AUTHOR_LEN),
        updated_year,
        updated_total,
        updated_available,
        book['active'],
        now_ts()
    )
    write_record_at(BOOKS_FILE, BOOK_STRUCT, idx, packed)
    print("Book updated successfully.")


def list_books(show_inactive=False):
    books = []
    for idx, vals in read_all_records(BOOKS_FILE, BOOK_STRUCT):
        rid, title_b, author_b, year, total, avail, active, last_mod = vals
        if not show_inactive and active == 0:
            continue
        books.append({
            "index": idx,
            "id": rid,
            "title": unpack_fixed_str(title_b),
            "author": unpack_fixed_str(author_b),
            "year": year,
            "total": total,
            "available": avail,
            "active": active,
            "last_modified": last_mod
        })
    return books

def find_book_by_id(book_id: int):
    for idx, vals in read_all_records(BOOKS_FILE, BOOK_STRUCT):
        rid = vals[0]
        if rid == book_id:
            rid, title_b, author_b, year, total, avail, active, last_mod = vals
            return idx, {
                "id": rid,
                "title": unpack_fixed_str(title_b),
                "author": unpack_fixed_str(author_b),
                "year": year,
                "total": total,
                "available": avail,
                "active": active,
                "last_modified": last_mod
            }
    return None, None

def view_all_books():
    books = list_books()
    headers = ["ID", "Title", "Author", "Year", "Total", "Available", "Status"]
    rows = []
    for b in books:
        rows.append([
            b["id"], b["title"][:30], b["author"], b["year"], b["total"], b["available"],
            "Active" if b["active"] else "Deleted"
        ])
    print_table(headers, rows)

# =============================================================================
# MEMBER domain (with Address)
# =============================================================================

def add_member():
    print("-- Add Member --")
    name = safe_input("Full Name: ")
    phone = safe_input("Phone: ")
    addr = safe_input("Address: ")
    mid = get_next_id(MEMBERS_FILE, MEMBER_STRUCT)

    
    print("\nPlease confirm the information:")
    print(f"  ID    : {mid}")
    print(f"  Name  : {name}")
    print(f"  Phone : {phone}")
    print(f"  Addr  : {addr}")

   
    confirm = input("Save this member? (y/n): ").strip().lower()
    if confirm not in ["y", "yes"]:
        print("Add member canceled.")
        return

    
    packed = MEMBER_STRUCT.pack(
        mid,
        pack_fixed_str(name, NAME_LEN),
        pack_fixed_str(phone, PHONE_LEN),
        pack_fixed_str(addr, ADDR_LEN),
        1,         # active
        now_ts()
    )
    append_record(MEMBERS_FILE, MEMBER_STRUCT, packed)
    print(f"Added Member id={mid}")

def list_members(show_inactive=False):
    members = []
    for idx, vals in read_all_records(MEMBERS_FILE, MEMBER_STRUCT):
        rid, name_b, phone_b, addr_b, active, last_mod = vals
        if not show_inactive and active == 0:
            continue
        members.append({
            "index": idx,
            "id": rid,
            "name": unpack_fixed_str(name_b),
            "phone": unpack_fixed_str(phone_b),
            "addr": unpack_fixed_str(addr_b),
            "active": active,
            "last_modified": last_mod
        })
    return members

def find_member_by_id(member_id: int):
    for idx, vals in read_all_records(MEMBERS_FILE, MEMBER_STRUCT):
        rid = vals[0]
        if rid == member_id:
            rid, name_b, phone_b, addr_b, active, last_mod = vals
            return idx, {
                "id": rid,
                "name": unpack_fixed_str(name_b),
                "phone": unpack_fixed_str(phone_b),
                "addr": unpack_fixed_str(addr_b),
                "active": active,
                "last_modified": last_mod
            }
    return None, None

def view_all_members():
    members = list_members()
    headers = ["ID", "Name", "Phone", "Address", "Status"]
    rows = []
    for m in members:
        rows.append([
            m["id"], m["name"], m["phone"], m["addr"][:40],
            "Active" if m["active"] else "Deleted"
        ])
    print_table(headers, rows)

# =============================================================================
# LOAN domain (Borrow / Return)
# =============================================================================

def add_loan():
    print("-- Borrow Book --")
    
    books = list_books()
    if not books:
        print("ไม่มีหนังสือในระบบ")
        return
    print("\nAvailable Books:")
    print("ID | Title                          | Author         | Year | Available")
    for b in books:
        print(f"{b['id']:<2} | {b['title'][:28]:<28} | {b['author']:<12} | {b['year']:<4} | {b['available']}")

    bid = safe_input("\nBook ID ที่ต้องการยืม: ", int)
    _, book = find_book_by_id(bid)
    if not book:
        print("ไม่พบหนังสือ")
        return
    if book["available"] <= 0:
        print("หนังสือไม่เหลือให้ยืม")
        return

    members = list_members()
    if not members:
        print("ไม่มีสมาชิกในระบบ")
        return
    print("\nMembers:")
    print("ID | Name                 | Phone")
    for m in members:
        print(f"{m['id']:<2} | {m['name']:<20} | {m['phone']}")

    mid = safe_input("\nMember ID ผู้ยืม: ", int)
    _, mem = find_member_by_id(mid)
    if not mem:
        print("ไม่พบสมาชิก")
        return

    print("\nPlease confirm borrow information:")
    print(f"  LoanID  : (auto) next ID")
    print(f"  Book    : {book['title']} (ID={bid})")
    print(f"  Member  : {mem['name']} (ID={mid})")

    while True:
        confirm = input("Confirm borrow? (y/n): ").strip().lower()
        if confirm in ["y", "yes"]:
            break
        elif confirm in ["n", "no"]:
            print("Borrow canceled.")
            return
        else:
            print("Please enter 'y' or 'n'.")

    lid = get_next_id(LOANS_FILE, LOAN_STRUCT)
    packed = LOAN_STRUCT.pack(lid, bid, mid, now_ts(), 0, 1, now_ts())
    append_record(LOANS_FILE, LOAN_STRUCT, packed)

    recs = read_all_records(BOOKS_FILE, BOOK_STRUCT)
    for idx, v in recs:
        if v[0] == bid:
            packed_b = BOOK_STRUCT.pack(v[0], v[1], v[2], v[3], v[4], v[5] - 1, v[6], now_ts())
            write_record_at(BOOKS_FILE, BOOK_STRUCT, idx, packed_b)
            break

    print(f"\nBorrow success: {mem['name']} ยืม {book['title']} (LoanID={lid})")


def return_loan():
    print("-- Return Loan (คืนหนังสือ) --")

    loans = [l for l in list_loans() if l["return_date"] == 0]
    if not loans:
        print("ไม่มีรายการที่ต้องคืน")
        return

    books   = {b["id"]: b for b in list_books()}
    members = {m["id"]: m for m in list_members()}

    print("\nรายการที่ยังไม่ถูกคืน:")
    print("LoanID | BookID | Title                 | MemberID | Member Name        | Borrow Date")
    print("----------------------------------------------------------------------------------")
    for l in loans:
        b = books.get(l["book_id"], {})
        m = members.get(l["member_id"], {})
        print(f"{l['id']:<6} | {l['book_id']:<6} | {b.get('title','-')[:20]:<20} | "
              f"{l['member_id']:<8} | {m.get('name','-'):<18} | {fmt_ts(l['borrow_date'])}")

    # ให้เลือกจาก LoanID แต่ผู้ใช้ดูได้ง่ายจากชื่อหนังสือ/ชื่อสมาชิก
    lid = safe_input("\nกรอก LoanID ที่ต้องการคืน: ", int)

    # หา record ที่ตรงกับ LoanID
    recs = read_all_records(LOANS_FILE, LOAN_STRUCT)
    target_idx, target = None, None
    for idx, vals in recs:
        if vals[0] == lid:
            target_idx, target = idx, vals
            break

    if not target:
        print("ไม่พบรายการยืมนี้")
        return

    (rid, book_id, member_id, borrow_ts, return_ts, active, last_mod) = target
    if return_ts != 0:
        print("รายการนี้คืนไปแล้ว")
        return

    # ✅ แสดงข้อมูลให้ผู้ใช้ยืนยันก่อนคืน
    member_name = members.get(member_id, {}).get('name','-')
    book_title  = books.get(book_id, {}).get('title','-')
    print(f"\nคุณต้องการคืนหนังสือ '{book_title}' ของสมาชิก '{member_name}' ใช่หรือไม่?")

    # ใช้ confirm แบบบังคับ y/n
    while True:
        confirm = input("Confirm return? (y/n): ").strip().lower()
        if confirm in ["y", "yes"]:
            break
        elif confirm in ["n", "no"]:
            print("Return canceled.")
            return
        else:
            print("Please enter 'y' or 'n'.")

    # อัปเดต Loan → ใส่ return_date
    new_return = now_ts()
    packed = LOAN_STRUCT.pack(rid, book_id, member_id, borrow_ts, new_return, active, now_ts())
    write_record_at(LOANS_FILE, LOAN_STRUCT, target_idx, packed)

    # อัปเดต Book → available +1
    bidx, book = find_book_by_id(book_id)
    if book:
        recs2 = read_all_records(BOOKS_FILE, BOOK_STRUCT)
        for i, bv in recs2:
            if bv[0] == book["id"]:
                packed_b = BOOK_STRUCT.pack(bv[0], bv[1], bv[2], bv[3], bv[4],
                                            bv[5] + 1, bv[6], now_ts())
                write_record_at(BOOKS_FILE, BOOK_STRUCT, i, packed_b)
                break

    print(f"\n return book → {member_name} | {book_title}")


def list_loans(show_inactive=True):
    loans = []
    recs = read_all_records(LOANS_FILE, LOAN_STRUCT)
    for idx, vals in recs:
        rid, book_id, member_id, borrow_ts, return_ts, active, last_mod = vals
        if not show_inactive and active == 0:
            continue
        loans.append({
            "index": idx,
            "id": rid,
            "book_id": book_id,
            "member_id": member_id,
            "borrow_date": borrow_ts,
            "return_date": return_ts,
            "active": active,
            "last_modified": last_mod
        })
    return loans


# =============================================================================
# Report generation (.txt)
# =============================================================================

def generate_report(path=REPORT_FILE):
    books   = list_books(show_inactive=True)
    members = list_members(show_inactive=True)
    loans   = list_loans(show_inactive=True)

    book_map   = {b["id"]: b for b in books}
    member_map = {m["id"]: m for m in members}

    lines = []
    lines.append("Library Borrow System - Report")
    lines.append(f"Generated At : {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append("App Version  : 3.0")
    lines.append("Encoding     : UTF-8\n")

    # ---------------- BORROW HISTORY ----------------
    lines.append("Borrow History")
    lines.append("+---------+------------------------------+------------+---------------------------+------------+------------+----------+")
    lines.append("|MemberID | Member Name                  | Phone      | Title                     | Loan Date  | Return Date| Status   |")
    lines.append("+---------+------------------------------+------------+---------------------------+------------+------------+----------+")

    if loans:
        grouped = {}
        for l in loans:
            mid = l["member_id"]
            m = member_map.get(mid, {})
            b = book_map.get(l["book_id"], {})
            loan_date   = fmt_ts(l["borrow_date"])
            return_date = fmt_ts(l["return_date"])
            status = "Returned" if l["return_date"] else "Borrowed"

            if mid not in grouped:
                grouped[mid] = {
                    "member": m,
                    "titles": [b.get("title", "-")],
                    "loan_dates": [loan_date],
                    "return_dates": [return_date],
                    "status": [status]
                }
            else:
                grouped[mid]["titles"].append(b.get("title", "-"))
                grouped[mid]["loan_dates"].append(loan_date)
                grouped[mid]["return_dates"].append(return_date)
                grouped[mid]["status"].append(status)

        # แสดงผลรวมเป็น 1 แถวต่อสมาชิก
        for mid, data in grouped.items():
            m = data["member"]

            # รวมชื่อหนังสือหลายเล่มเป็น string (ตัดความยาว 27)
            titles = "; ".join(data["titles"])[:27]

            # ใช้วันยืม, วันคืน, status แค่รายการแรก (ไม่ join)
            loan_d = data["loan_dates"][0] if data["loan_dates"] else "-"
            ret_d  = data["return_dates"][0] if data["return_dates"] else "-"
            status = data["status"][0] if data["status"] else "-"

            # สร้างบรรทัดตาราง
            lines.append(
                f"|{m.get('id','-'):<9}"
                f"|{(m.get('name','-') or '-'):<30}"
                f"|{(m.get('phone','-') or '-'):<12}"
                f"|{titles:<27}"
                f"|{loan_d:<12}"
                f"|{ret_d:<12}"
                f"|{status:<10}|"
            )

    else:
        # กรณีไม่มี loan
        lines.append("|    -    | -                            | -          | -                         |     -      |     -      |   -      |")

    # ปิดท้ายตาราง Borrow History
    lines.append(
        "+---------+------------------------------+------------+---------------------------+------------+------------+----------+\n"
    )    # ---------------- SUMMARY ----------------
    active_books   = [b for b in books if b['active'] == 1]
    deleted_books  = [b for b in books if b['active'] == 0]
    borrowed_now   = len([l for l in loans if l['return_date'] == 0])
    available_now  = sum([b['available'] for b in active_books])

    lines.append("Summary (Active Books Only)")
    lines.append(f"- Total Books       : {len(books)}")
    lines.append(f"- Active Books      : {len(active_books)}")
    lines.append(f"- Deleted Books     : {len(deleted_books)}")
    lines.append(f"- Borrowed Now      : {borrowed_now}")
    lines.append(f"- Available Now     : {available_now}\n")

    # ---------------- BORROW STATISTICS ----------------
    from collections import Counter
    borrow_count = Counter([l['book_id'] for l in loans])
    most_borrowed = borrow_count.most_common(1)

    lines.append("Borrow Statistics (Active only)")
    if most_borrowed:
        book_id, times = most_borrowed[0]
        lines.append(f"- Most Borrowed Book : {book_map.get(book_id,{}).get('title','-')} ({times} times)")
    else:
        lines.append("- Most Borrowed Book : None")

    lines.append(f"- Currently Borrowed : {borrowed_now}")
    lines.append(f"- Active Members     : {len([m for m in members if m['active'] == 1])}")

    # รวมเป็น text
    report_text = "\n".join(lines)

    # ✅ print on screen
    print(report_text)

    # ✅ save file
    with open(path, "w", encoding="utf-8") as f:
        f.write(report_text)

    print(f"\n Report saved to {path}")


# =============================================================================
# Search / View helpers (bonus for grading)
# =============================================================================
def update_member():
    print("-- Update Member --")
    members = list_members()
    if not members:
        print("No members in system")
        return

    # แสดงสมาชิกทั้งหมด
    print_table(
        ["ID", "Name", "Phone", "Address", "Status"],
        [[m["id"], m["name"], m["phone"], m["addr"][:40], "Active" if m["active"] else "Deleted"] for m in members]
    )

    mid = safe_input("Enter Member ID to update: ", int)
    idx, mem = find_member_by_id(mid)
    if not mem:
        print("Member not found")
        return

    print("Leave blank to keep current value.")
    new_name  = safe_input(f"Name [{mem['name']}]: ", allow_empty=True)
    new_phone = safe_input(f"Phone [{mem['phone']}]: ", allow_empty=True)
    new_addr  = safe_input(f"Address [{mem['addr']}]: ", allow_empty=True)

    updated_name = new_name if new_name else mem["name"]
    updated_phone = new_phone if new_phone else mem["phone"]
    updated_addr = new_addr if new_addr else mem["addr"]

    print("\nPlease confirm the updated information:")
    print(f"  ID    : {mem['id']}")
    print(f"  Name  : {updated_name}")
    print(f"  Phone : {updated_phone}")
    print(f"  Addr  : {updated_addr}")
    print(f"  Status: {'Active' if mem['active'] else 'Deleted'}")


    confirm = input("Save changes? (y/n): ").strip().lower()
    if confirm not in ["y", "yes"]:
        print("Update canceled.")
        return

   
    packed = MEMBER_STRUCT.pack(
        mem["id"],
        pack_fixed_str(updated_name, NAME_LEN),
        pack_fixed_str(updated_phone, PHONE_LEN),
        pack_fixed_str(updated_addr, ADDR_LEN),
        mem["active"],
        now_ts()
    )
    write_record_at(MEMBERS_FILE, MEMBER_STRUCT, idx, packed)
    print("Member updated successfully.")


def delete_member():
    print("-- Delete Member (soft delete) --")

    # อ่านสมาชิกทั้งหมด (รวม inactive)
    members = list_members(show_inactive=True)
    if not members:
        print("No members in system")
        return

    # แสดงตารางสมาชิก
    headers = ["ID", "Name", "Phone", "Address", "Status"]
    rows = []
    for m in members:
        rows.append([
            m["id"],
            m["name"],
            m["phone"],
            m["addr"][:40],
            "Active" if m["active"] else "Deleted"
        ])
    print_table(headers, rows)  

   
    mid = safe_input("Member ID to delete: ", int)
    idx, mem = find_member_by_id(mid)
    if not mem:
        print("Member not found")
        return

    if mem["active"] == 0:
        print("Member already deleted")
        return

    # ตรวจสอบ Loan ที่ยังไม่คืน
    active_loans = [l for l in list_loans() if l["member_id"] == mid and l["return_date"] == 0]
    if active_loans:
        print("Cannot delete member: still has active loans")
        return

    # Soft delete
    packed = MEMBER_STRUCT.pack(
        mem["id"],
        pack_fixed_str(mem["name"], NAME_LEN),
        pack_fixed_str(mem["phone"], PHONE_LEN),
        pack_fixed_str(mem["addr"], ADDR_LEN),
        0,  # inactive
        now_ts()
    )
    write_record_at(MEMBERS_FILE, MEMBER_STRUCT, idx, packed)
    print(f" Member {mem['name']} soft-deleted successfully.")


def delete_book():
    print("-- Delete Book --")

    books = list_books(show_inactive=True)
    if not books:
        print("No books in system")
        return

    print("+----+---------------------------+------------------+------+-------+----------+")
    print("| ID | Title                     | Author           | Year | Total | Available|")
    print("+----+---------------------------+------------------+------+-------+----------+")
    for b in books:
        status = "Active" if b["active"] else "Deleted"
        print(f"|{b['id']:<3} | {b['title'][:25]:<25} | {b['author'][:16]:<16} | "
              f"{b['year']:<4} | {b['total']:<5} | {b['available']:<8}| {status}")
    print("+----+---------------------------+------------------+------+-------+----------+")

    bid = safe_input("Enter Book ID to delete: ", int)
    idx, book = find_book_by_id(bid)
    if not book:
        print("Book not found")
        return

    if book["active"] == 0:
        print("Book already deleted")
        return

    # ตรวจสอบว่าหนังสือยังมีการยืมอยู่หรือไม่ (ที่ยังไม่คืน)
    active_loans = [l for l in list_loans() if l["book_id"] == bid and l["return_date"] == 0]
    if active_loans:
        print("Cannot delete book: it is currently borrowed by someone.")
        return

    confirm = input(f"Are you sure you want to delete '{book['title']}' (y/n)? ").strip().lower()
    if confirm not in ["y", "yes"]:
        print("Delete canceled.")
        return

    # Soft delete (active = 0)
    packed = BOOK_STRUCT.pack(
        book["id"],
        pack_fixed_str(book["title"], TITLE_LEN),
        pack_fixed_str(book["author"], AUTHOR_LEN),
        book["year"],
        book["total"],
        book["available"],
        0,  # inactive
        now_ts()
    )
    write_record_at(BOOKS_FILE, BOOK_STRUCT, idx, packed)
    print(f"Book '{book['title']}' soft-deleted successfully.")

# =============================================================================
# Menus
# =============================================================================

def main_menu():
    while True:
        print(textwrap.dedent('''
            ===== Library Manager =====
            1) Book (Add/Update/Delete)
            2) Member (Add/Update/Delete)
            3) Borrow Book
            4) Return Book
            5) View
            6) Generate Report (.txt)      
            0) Exit
        '''))
        s = input("Select: ").strip()

        if not s.isdigit():
            print("Invalid choice.")
            continue

        choice = int(s)
        if choice == 1:
            # Book submenu
            print(textwrap.dedent('''
                --- Book Menu ---
                1) Add Book
                2) Update Book
                3) Delete Book
                0) Back
            '''))
            sub = input("Select: ").strip()
            if sub == "1":
                add_book()
            elif sub == "2":
                update_book()
            elif sub == "3":
                delete_book()
            elif sub == "0":
                continue
            else:
                print("Invalid option.")

        elif choice == 2:
            # Member submenu
            print(textwrap.dedent('''
                --- Member Menu ---
                1) Add Member
                2) Update Member
                3) Delete Member
                0) Back
            '''))
            sub = input("Select: ").strip()
            if sub == "1":
                add_member()
            elif sub == "2":
                update_member()
            elif sub == "3":
                delete_member()
            elif sub == "0":
                continue
            else:
                print("Invalid option.")

        elif choice == 3:
            add_loan()
        elif choice == 4:
            return_loan()
        elif choice == 5:
            view()
        elif choice == 6:
            generate_report()
        elif choice == 0:
            print("Exiting...")
            break
        else:
            print("Invalid option.")

def view_all_books():
    books = list_books()
    headers = ["ID", "Title", "Author", "Year", "Total", "Available", "Status"]
    rows = []
    for b in books:
        rows.append([
            b["id"], b["title"][:30], b["author"], b["year"], b["total"], b["available"],
            "Active" if b["active"] else "Deleted"
        ])
    print_table(headers, rows)

def view_all_loans():
    loans = list_loans(show_inactive=True)
    books = {b["id"]: b for b in list_books(show_inactive=True)}
    members = {m["id"]: m for m in list_members(show_inactive=True)}

    headers = ["LoanID", "BookID", "Title", "MemberID", "Name", "Borrow", "Return", "Status"]
    rows = []
    for l in loans:
        b = books.get(l["book_id"], {})
        m = members.get(l["member_id"], {})
        rows.append([
            l["id"], l["book_id"], (b.get("title","-") or "-")[:28], l["member_id"],
            m.get("name","-"), fmt_ts(l["borrow_date"]), fmt_ts(l["return_date"]),
            "Returned" if l["return_date"] else "Borrowed"
        ])
    print_table(headers, rows)


def view():
    while True:
        print("\n-- View Menu --")
        print("0) Back to Main Menu")
        t = safe_input("Type (book/member/loan): ", lambda s: s.lower())
        if t == "0":
            break
        if t not in ["book", "member", "loan"]:
            print("Unknown type")
            continue

        print("Mode:")
        print("1) View All")
        print("2) View Filter")
        print("3) View Single")
        print("0) Back")
        mode = safe_input("Select mode: ", lambda s: s.strip())
        if mode == "0":
            continue  # กลับไปเลือก Type ใหม่

        if mode == "1":  # View All
            if t == "book":
                view_all_books()
            elif t == "member":
                view_all_members()
            elif t == "loan":
                view_all_loans()

        elif mode == "2":  # Filter
            if t == "book":
                books = list_books(show_inactive=True)
                if not books:
                    print("No books found.")
                    continue
                kw_title  = input("Keyword in Title (Enter to skip): ").strip().lower()
                kw_author = input("Keyword in Author (Enter to skip): ").strip().lower()
                kw_year   = input("Year (Enter to skip): ").strip()
                kw_active = input("Status (active/deleted/Enter to skip): ").strip().lower()

                filtered_books = books
                if kw_title:
                    filtered_books = [b for b in filtered_books if kw_title in b["title"].lower()]
                if kw_author:
                    filtered_books = [b for b in filtered_books if kw_author in b["author"].lower()]
                if kw_year:
                    filtered_books = [b for b in filtered_books if str(b["year"]) == kw_year]
                if kw_active == "active":
                    filtered_books = [b for b in filtered_books if b["active"] == 1]
                elif kw_active == "deleted":
                    filtered_books = [b for b in filtered_books if b["active"] == 0]

                headers = ["ID", "Title", "Author", "Year", "Avail", "Status"]
                rows = []
                for b in filtered_books:
                    rows.append([b["id"], b["title"][:28], b["author"], b["year"], b["available"], "Active" if b["active"] else "Deleted"])
                print_table(headers, rows)
                print(f"Found {len(filtered_books)} book(s).")

            elif t == "member":
                members = list_members(show_inactive=True)
                if not members:
                    print("No members found.")
                    continue
                kw_name  = input("Keyword in Name (Enter to skip): ").strip().lower()
                kw_phone = input("Keyword in Phone (Enter to skip): ").strip().lower()
                kw_addr  = input("Keyword in Address (Enter to skip): ").strip().lower()
                kw_active = input("Status (active/deleted/Enter to skip): ").strip().lower()

                filtered_members = members
                if kw_name:
                    filtered_members = [m for m in filtered_members if kw_name in m["name"].lower()]
                if kw_phone:
                    filtered_members = [m for m in filtered_members if kw_phone in m["phone"].lower()]
                if kw_addr:
                    filtered_members = [m for m in filtered_members if kw_addr in m["addr"].lower()]
                if kw_active == "active":
                    filtered_members = [m for m in filtered_members if m["active"] == 1]
                elif kw_active == "deleted":
                    filtered_members = [m for m in filtered_members if m["active"] == 0]

                headers = ["ID", "Name", "Phone", "Address", "Status"]
                rows = []
                for m in filtered_members:
                    rows.append([m["id"], m["name"], m["phone"], m["addr"][:40], "Active" if m["active"] else "Deleted"])
                print_table(headers, rows)
                print(f"Found {len(filtered_members)} member(s).")

            else:
                print("Filter not available for loans")

        elif mode == "3":  # Single
            if t == "book":
                bid = safe_input("Book ID: ", int)
                _, b = find_book_by_id(bid)
                if not b:
                    print("Book not found")
                    continue
                headers = ["Field", "Value"]
                rows = [
                    ["ID", b["id"]],
                    ["Title", b["title"]],
                    ["Author", b["author"]],
                    ["Year", b["year"]],
                    ["Total", b["total"]],
                    ["Available", b["available"]],
                    ["Active", "Yes" if b["active"] else "No"]
                ]
                print_table(headers, rows)

            elif t == "member":
                mid = safe_input("Member ID: ", int)
                _, m = find_member_by_id(mid)
                if not m:
                    print("Member not found")
                    continue
                headers = ["Field", "Value"]
                rows = [
                    ["ID", m["id"]],
                    ["Name", m["name"]],
                    ["Phone", m["phone"]],
                    ["Address", m["addr"]],
                    ["Active", "Yes" if m["active"] else "No"]
                ]
                print_table(headers, rows)

            elif t == "loan":
                lid = safe_input("Loan ID: ", int)
                for idx, v in read_all_records(LOANS_FILE, LOAN_STRUCT):
                    if v[0] == lid:
                        rid, book_id, member_id, borrow_ts, return_ts, active, last_mod = v
                        headers = ["Field", "Value"]
                        rows = [
                            ["Loan ID", rid],
                            ["Book ID", book_id],
                            ["Member ID", member_id],
                            ["Borrow Date", fmt_ts_full(borrow_ts)],
                            ["Return Date", fmt_ts_full(return_ts)],
                            ["Active", "Yes" if active else "No"]
                        ]
                        print_table(headers, rows)
                        break
                else:
                    print("Loan not found")
        else:
            print("Invalid mode")

        # รอให้ผู้ใช้กด Enter ก่อนกลับไปเลือกเมนู
        input("\nPress Enter to continue...")

# =============================================================================
# Entrypoint
# =============================================================================

if __name__ == "__main__":
    try:
        main_menu()
    except KeyboardInterrupt:
        print("\nInterrupted. Generating final report and exiting...")
        try:
            generate_report()
        finally:
            pass

