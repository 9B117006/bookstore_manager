import sqlite3
from typing import Optional


def table_exists(conn: sqlite3.Connection, table_name: str) -> bool:
    """
    檢查指定的資料表是否存在於 SQLite 資料庫中。

    參數:
        conn (sqlite3.Connection): SQLite 資料庫連線物件。
        table_name (str): 要檢查的資料表名稱。

    回傳:
        bool: 若資料表存在則回傳 True，否則回傳 False。
    """
    cursor = conn.cursor()
    cursor.execute(
        "SELECT name FROM sqlite_master "
        "WHERE type='table' AND name=?;",
        (table_name,),
    )
    return cursor.fetchone() is not None


def init_db() -> None:
    """
    初始化書店資料庫：若資料表不存在，則建立資料表並插入初始資料。

    回傳:
        None
    """
    with sqlite3.connect("bookstore.db") as conn:
        if not (
            table_exists(conn, "member")
            and table_exists(conn, "book")
            and table_exists(conn, "sale")
        ):
            print("資料表不存在，正在建立資料表並插入初始資料...")
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS member (
                    mid TEXT PRIMARY KEY,
                    mname TEXT NOT NULL,
                    mphone TEXT NOT NULL,
                    memail TEXT
                );

                CREATE TABLE IF NOT EXISTS book (
                    bid TEXT PRIMARY KEY,
                    btitle TEXT NOT NULL,
                    bprice INTEGER NOT NULL,
                    bstock INTEGER NOT NULL
                );

                CREATE TABLE IF NOT EXISTS sale (
                    sid INTEGER PRIMARY KEY AUTOINCREMENT,
                    sdate TEXT NOT NULL,
                    mid TEXT NOT NULL,
                    bid TEXT NOT NULL,
                    sqty INTEGER NOT NULL,
                    sdiscount INTEGER NOT NULL,
                    stotal INTEGER NOT NULL
                );
                """
            )
            # 插入初始會員資料
            cursor = conn.cursor()
            cursor.executemany(
                "INSERT INTO member VALUES (?, ?, ?, ?)",
                [
                    ("M001", "Alice", "0912-345678", "alice@example.com"),
                    ("M002", "Bob", "0923-456789", "bob@example.com"),
                    ("M003", "Cathy", "0934-567890", "cathy@example.com"),
                ],
            )
            # 插入初始書籍資料
            cursor.executemany(
                "INSERT INTO book VALUES (?, ?, ?, ?)",
                [
                    ("B001", "Python Programming", 600, 50),
                    ("B002", "Data Science Basics", 800, 30),
                    ("B003", "Machine Learning Guide", 1200, 20),
                ],
            )
            # 插入初始銷售資料
            cursor.executemany(
                (
                    "INSERT INTO sale (sdate, mid, bid, sqty, sdiscount, stotal) "
                    "VALUES (?, ?, ?, ?, ?, ?)"
                ),
                [
                    ("2024-01-15", "M001", "B001", 2, 100, 1100),
                    ("2024-01-16", "M002", "B002", 1, 50, 750),
                    ("2024-01-17", "M001", "B003", 3, 200, 3400),
                    ("2024-01-18", "M003", "B001", 1, 0, 600),
                ],
            )
            conn.commit()
            print("資料表建立並初始化完成！")
        else:
            print("資料庫已經存在資料表，不需要重新建立。")


def select_menu() -> None:
    """
    顯示主選單選項。

    回傳:
        None
    """
    menu = (
        "***************選單***************",
        "1. 新增銷售記錄",
        "2. 顯示銷售報表",
        "3. 更新銷售記錄",
        "4. 刪除銷售記錄",
        "5. 離開",
        "**********************************",
    )
    print("\n".join(menu))


def sales_record() -> None:
    """
    提示使用者新增銷售記錄，驗證輸入後更新銷售與書籍庫存資料表。

    回傳:
        None
    """
    with sqlite3.connect("bookstore.db") as conn:
        cursor = conn.cursor()

        while True:
            sales_date = input("請輸入銷售日期 (YYYY-MM-DD)：")
            if len(sales_date) != 10 or sales_date.count("-") != 2:
                print("錯誤：請輸入正確的日期格式 (YYYY-MM-DD)")
                continue

            member_id = input("請輸入會員編號：")
            book_id = input("請輸入書籍編號：")

            cursor.execute("SELECT 1 FROM member WHERE mid = ?", (member_id,))
            if cursor.fetchone() is None:
                print("錯誤：會員編號無效")
                continue

            cursor.execute("SELECT bstock, bprice FROM book WHERE bid = ?", (book_id,))
            book_data = cursor.fetchone()
            if book_data is None:
                print("錯誤：書籍編號無效")
                continue

            stock, price = book_data
            try:
                qty = int(input("請輸入購買數量："))
                if qty <= 0:
                    raise ValueError
            except ValueError:
                print("錯誤：數量必須為正整數，請重新輸入")
                continue

            try:
                discount = int(input("請輸入折扣金額："))
                if discount < 0:
                    raise ValueError
            except ValueError:
                print("錯誤：折扣金額必須為非負整數，請重新輸入")
                continue

            if qty > stock:
                print(f"錯誤：書籍庫存不足 (現有庫存: {stock})")
                continue

            total = price * qty - discount
            cursor.execute(
                """
                INSERT INTO sale
                    (sdate, mid, bid, sqty, sdiscount, stotal)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (sales_date, member_id, book_id, qty, discount, total),
            )
            cursor.execute(
                "UPDATE book SET bstock = bstock - ? WHERE bid = ?", (qty, book_id)
            )
            conn.commit()
            print(f"=> 銷售記錄已新增！(銷售總額: {total})")
            break


def show_sales_report() -> None:
    """
    取得並顯示所有銷售記錄，包含會員與書籍資訊。

    回傳:
        None
    """
    with sqlite3.connect("bookstore.db") as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT
                sale.sid, sale.sdate, member.mname, book.btitle,
                book.bprice, sale.sqty, sale.sdiscount, sale.stotal
            FROM sale
            JOIN member ON sale.mid = member.mid
            JOIN book ON sale.bid = book.bid
            ORDER BY sale.sid;
            """
        )
        rows = cursor.fetchall()

        if not rows:
            print("目前沒有銷售紀錄。")
            return

        print("==================== 銷售報表 ====================")
        for sid, sdate, mname, title, price, qty, disc, total in rows:
            print(f"銷售 #{sid}")
            print(f"日期: {sdate} 會員: {mname} 書籍: {title}")
            print("-" * 50)
            print("單價\t數量\t折扣\t小計")
            print("-" * 50)
            subtotal = price * qty - disc
            print(f"{price:,}\t{qty}\t{disc:,}\t{subtotal:,}")
            print("-" * 50)
            print(f"銷售總額: {total:,}")
            print("=" * 50)


def update_sales_record() -> None:
    """
    允許使用者更新既有銷售記錄的折扣，並重新計算總額。

    回傳:
        None
    """
    with sqlite3.connect("bookstore.db") as conn:
        cursor = conn.cursor()

        # 顯示銷售記錄列表
        cursor.execute("""
            SELECT sale.sid, sale.sdate, member.mname
            FROM sale
            JOIN member ON sale.mid = member.mid
            ORDER BY sale.sid;
        """)

        sales = cursor.fetchall()

        if not sales:
            print("目前沒有銷售記錄。")
            return

        print("======== 銷售記錄列表 ========")
        for i, sale in enumerate(sales, 1):
            sid, sdate, mname = sale
            print(f"{i}. 銷售編號: {sid} - 會員: {mname} - 日期: {sdate}")
        print("================================")

        # 讓使用者選擇銷售編號
        while True:
            choice = input("請選擇要更新的銷售編號 (輸入數字或按 Enter 取消): ")
            if choice == "":
                print("取消更新操作。")
                conn.close()
                return

            try:
                sale_index = int(choice) - 1  # 將選擇的編號轉為索引
                if sale_index < 0 or sale_index >= len(sales):  # 檢查選擇的編號是否有效
                    print("錯誤：無效的選擇！請選擇有效的銷售編號")
                    continue
                sid = sales[sale_index][0]  # 獲取選中的銷售編號
                break

            except ValueError:
                print("錯誤：請選擇有效的數字或按 Enter 取消")  # 捕獲無效數字錯誤

        # 取得當前銷售記錄的詳細資料（包括折扣和小計）
        cursor.execute("""
            SELECT bprice, sqty, sdiscount FROM sale
            JOIN book ON sale.bid = book.bid
            WHERE sale.sid = ?;
        """, (sid,))
        book_data = cursor.fetchone()

        if not book_data:
            print("錯誤：找不到該銷售記錄的書籍資料！")
            conn.close()
            return

        bprice, sqty, old_discount = book_data

        # 顯示當前折扣並讓使用者輸入新的折扣
        print(f"目前的折扣金額是: {old_discount}")
        while True:
            try:
                new_discount = int(input("請輸入新的折扣金額："))
                if new_discount < 0:
                    print("錯誤：折扣金額不能為負數，請重新輸入")
                    continue  # 如果折扣為負數，繼續要求輸入
                break  # 如果折扣金額有效，退出循環
            except ValueError:
                print("錯誤：請輸入有效的折扣金額")

        # 計算新的銷售總額
        new_stotal = bprice * sqty - new_discount

        # 更新資料庫中的折扣金額和銷售總額
        cursor.execute("""
            UPDATE sale
            SET sdiscount = ?, stotal = ?
            WHERE sid = ?;
        """, (new_discount, new_stotal, sid))
        conn.commit()

        print(f"=> 銷售編號 {sid} 已更新！(銷售總額: {new_stotal:,})")


def delete_sales_record() -> None:
    """
    提示使用者刪除指定的銷售記錄。

    回傳:
        None
    """
    with sqlite3.connect("bookstore.db") as conn:
        cursor = conn.cursor()

        # 顯示銷售記錄列表
        cursor.execute("""
            SELECT sale.sid, sale.sdate, member.mname
            FROM sale
            JOIN member ON sale.mid = member.mid
            ORDER BY sale.sid;
        """)

        sales = cursor.fetchall()

        if not sales:
            print("目前沒有銷售記錄。")
            return

        print("======== 銷售記錄列表 ========")
        for i, sale in enumerate(sales, 1):
            sid, sdate, mname = sale
            print(f"{i}. 銷售編號: {sid} - 會員: {mname} - 日期: {sdate}")
        print("================================")

        # 讓使用者選擇銷售編號
        while True:
            choice = input("請選擇要刪除的銷售編號 (輸入數字或按 Enter 取消): ")

            if choice == "":
                print("取消刪除操作。")
                conn.close()
                return

            try:
                choice = int(choice)
                if choice < 1 or choice > len(sales):
                    print("錯誤：請輸入有效的數字")
                    continue

                # 確定要刪除的銷售編號
                sid_to_delete = sales[choice - 1][0]

                # 刪除該銷售記錄
                cursor.execute("DELETE FROM sale WHERE sid = ?", (sid_to_delete,))
                conn.commit()

                print(f"=> 銷售編號 {sid_to_delete} 已刪除")
                break

            except ValueError:
                print("錯誤：請輸入有效的數字")


def main() -> None:
    """
    主程式入口，顯示選單並處理使用者輸入。

    回傳:
        None
    """
    init_db()
    while True:
        select_menu()
        choice = input("請選擇操作項目 (1-5, Enter離開)：")
        if choice == "1":
            sales_record()
        elif choice == "2":
            show_sales_report()
        elif choice == "3":
            update_sales_record()
        elif choice == "4":
            delete_sales_record()
        elif choice == "5" or choice == "":
            print("程式結束！")
            break
        else:
            print("請輸入有效的選項（1-5）")


if __name__ == "__main__":
    main()
