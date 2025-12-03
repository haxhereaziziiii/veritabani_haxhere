
import psycopg2
from psycopg2.extras import RealDictCursor
import sys

# -------------------------
# DB connection settings
# -------------------------
DB_CONFIG = {
    "host": "localhost",
    "port": 5432,
    "database": "ODEV_1",
    "user": "postgres",
    "password": "110205"
}

# -------------------------
# DB helpers
# -------------------------
def get_conn():
    return psycopg2.connect(cursor_factory=RealDictCursor, **DB_CONFIG)

def get_connection():
    return psycopg2.connect(
        host="localhost",
        database="ODEV_1",
        user="postgres",
        password="110205"
    )

def fetchall(query, params=None):
    conn = get_conn()
    try:
        with conn:
            with conn.cursor() as cur:
                cur.execute(query, params)
                return cur.fetchall()
    finally:
        conn.close()

def fetchone(query, params=None):
    conn = get_conn()
    try:
        with conn:
            with conn.cursor() as cur:
                cur.execute(query, params)
                return cur.fetchone()
    finally:
        conn.close()

def execute(query, params=None):
    conn = get_conn()
    try:
        with conn:
            with conn.cursor() as cur:
                cur.execute(query, params)
    finally:
        conn.close()

def call_function_single_value(sql_call, params=None):
    """
    Helper to call stored functions that return a single scalar value.
    Example usage: SELECT sp_purchase_ticket(%s,%s,%s,%s,%s);
    """
    conn = get_conn()
    try:
        with conn:
            with conn.cursor() as cur:
                cur.execute(sql_call, params)
                row = cur.fetchone()
                if row is None:
                    return None
                # row is RealDictRow or tuple depending on function; handle both
                if isinstance(row, dict):
                    # fetchone returned dict when named columns, but scalar functions usually return tuple-like
                    return next(iter(row.values()))
                if isinstance(row, (list, tuple)):
                    return row[0]
                return row
    finally:
        conn.close()

# -------------------------
# Utility validation functions
# -------------------------
def person_exists(person_id):
    r = fetchone("SELECT person_id FROM persons WHERE person_id = %s;", (person_id,))
    return bool(r)

def get_int_input(prompt):
    while True:
        s = input(prompt).strip()
        if s == "":
            return None
        try:
            return int(s)
        except ValueError:
            print("Please enter a valid integer (or empty to cancel).")

# -------------------------
# Person operations
# -------------------------
def add_person():
    print("\n-- Add Person --")
    first = input("First name: ").strip()
    last = input("Last name: ").strip()
    email = input("Email (optional): ").strip() or None
    phone = input("Phone (optional): ").strip() or None

    sql = """
    INSERT INTO persons (first_name, last_name, email, phone)
    VALUES (%s, %s, %s, %s)
    RETURNING person_id;
    """
    try:
        new = call_function_single_value(sql, (first, last, email, phone))
        print(f"Person created with person_id = {new}")
        print("If you have the auto_create_attendee trigger enabled, an attendees row should be created automatically.")
    except Exception as e:
        print("Error creating person:", e)

def list_persons():
    con = get_connection()      # <— now it is defined
    cur = con.cursor()
    cur.execute("""
        SELECT person_id, first_name, last_name, email, phone, created_at
        FROM persons
        ORDER BY person_id;
    """)
    rows = cur.fetchall()

    print("\n--- PERSONS LIST ---")
    for r in rows:
        print(f"ID: {r[0]} | {r[1]} {r[2]} | Email: {r[3]} | Phone: {r[4]} | Created at: {r[5]}")
    
    cur.close()
    con.close()


def search_person():
    print("\n-- Search Person --")
    print("1) Search by ID")
    print("2) Search by Name")
    choice = input("Select: ").strip()

    try:
        if choice == "1":
            pid = get_int_input("Person ID: ")
            if pid is None:
                print("Cancelled.")
                return
            rows = call_query("SELECT * FROM persons WHERE person_id = %s;", (pid,))
        
        elif choice == "2":
            name = input("Enter name (first or last or both): ").strip()
            like = f"%{name}%"
            rows = call_query("""
                SELECT * FROM persons
                WHERE first_name ILIKE %s OR last_name ILIKE %s;
            """, (like, like))

        else:
            print("Invalid choice.")
            return

        if not rows:
            print("No persons found.")
            return

        print("\n-- Results --")
        for r in rows:
            print(r)

    except Exception as e:
        print("Error searching person:", e)







def add_staff():
    print("\n-- Promote Person to Staff --")
    pid = get_int_input("Person ID to make staff: ")
    if not pid:
        print("Cancelled.")
        return
    if not person_exists(pid):
        print("Person not found.")
        return
    role = input("Role: ").strip()
    hire_date = input("Hire start date (YYYY-MM-DD, optional): ").strip() or None
    try:
        execute("INSERT INTO staff(person_id, role, hire_start_date) VALUES (%s, %s, %s);", (pid, role, hire_date))
        print("Staff record created.")
    except Exception as e:
        print("Error:", e)

def list_staff():
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT 
            s.staff_id,
            p.person_id,
            p.first_name,
            p.last_name,
            p.email,
            p.phone,
            p.created_at,
            s.role,
            s.hire_start_date
        FROM staff s
        JOIN persons p ON s.person_id = p.person_id
        ORDER BY s.staff_id;
    """)

    rows = cur.fetchall()

    if not rows:
        print("\nNo staff found.\n")
    else:
        print("\n=== STAFF LIST ===")
        for r in rows:
            print(f"""
Staff ID: {r[0]}
Person ID: {r[1]}
Name: {r[2]} {r[3]}
Email: {r[4]}
Phone: {r[5]}
Created At: {r[6]}
Role: {r[7]}
Hire Start Date: {r[8]}
------------------------------
""")

    cur.close()
    conn.close()

def search_staff():
    con = get_connection()
    cur = con.cursor()

    print("\n--- Search Staff ---")
    keyword = input("Enter name, surname or person_id to search: ")

    try:
        query = """
        SELECT s.person_id, p.first_name, p.last_name, p.email, p.phone,
               s.role, s.hire_start_date, p.created_at
        FROM staff s
        JOIN persons p ON p.person_id = s.person_id
        WHERE p.first_name ILIKE %s
           OR p.last_name ILIKE %s
           OR CAST(s.person_id AS TEXT) = %s;
        """

        cur.execute(query, (f"%{keyword}%", f"%{keyword}%", keyword))
        rows = cur.fetchall()

        if not rows:
            print("No staff found.")
        else:
            print("\nResults:")
            for r in rows:
                print(f"""
Staff ID: {r[0]}
Name: {r[1]} {r[2]}
Email: {r[3]}
Phone: {r[4]}
Role: {r[5]}
Hire Date: {r[6]}
Created At: {r[7]}
-------------------------------------
""")

    except Exception as e:
        print("Error searching staff:", e)

    cur.close()
    con.close()
def delete_staff():
    con = get_connection()
    cur = con.cursor()

    print("\n--- Delete Staff Member ---")
    staff_id = input("Enter staff's person_id to delete: ")

    try:
        cur.execute("SELECT person_id FROM staff WHERE person_id = %s", (staff_id,))
        if cur.fetchone() is None:
            print("Staff member does not exist!")
        else:
            cur.execute("DELETE FROM staff WHERE person_id = %s", (staff_id,))
            con.commit()
            print("Staff member removed from staff table.")

    except Exception as e:
        print("Error deleting staff:", e)

    cur.close()
    con.close()
# -------------------------
# Jury Members
# -------------------------
def add_jury_member():
    print("\n-- Add Jury Member --")
    pid = get_int_input("Person ID to be jury member: ")
    if not pid:
        print("Cancelled.")
        return
    if not person_exists(pid):
        print("Person not found.")
        return
    affiliation = input("Affiliation: ").strip()
    notes = input("Expertise notes (optional): ").strip() or None
    try:
        execute("INSERT INTO jury_members(person_id, affiliation, expertise_notes) VALUES (%s, %s, %s);", (pid, affiliation, notes))
        print("Jury member record created.")
    except Exception as e:
        print("Error:", e)


def list_jury_members():
    con = get_connection()
    cur = con.cursor()

    try:
        cur.execute("""
            SELECT 
                j.jury_id,
                p.person_id,
                p.first_name,
                p.last_name,
                p.email,
                j.affiliation,
                j.expertise_notes,
                p.created_at
            FROM jury_members j
            JOIN persons p ON j.person_id = p.person_id
            ORDER BY j.jury_id;
        """)

        rows = cur.fetchall()

        if not rows:
            print("\n❗ No jury members found.\n")
            return

        print("\n==== JURY MEMBERS ====\n")
        for row in rows:
            print(f"Jury ID: {row[0]}")
            print(f"Person ID: {row[1]}")
            print(f"Name: {row[2]} {row[3]}")
            print(f"Email: {row[4]}")
            print(f"Affiliation: {row[5]}")
            print(f"Expertise Notes: {row[6]}")
            print(f"Created At: {row[7]}")
            print("---------------------------")

    except Exception as e:
        print("Error listing jury members:", e)

    finally:
        cur.close()
        con.close()



def search_jury_members():
    con = get_connection()
    cur = con.cursor()

    key = input("\nSearch keyword: ")

    cur.execute("""
        SELECT p.person_id, p.first_name, p.last_name, p.email, 
               j.affiliation, j.expertise_notes, p.created_at
        FROM jury_members j
        JOIN persons p ON p.person_id = j.person_id
        WHERE p.first_name ILIKE %s
           OR p.last_name ILIKE %s
           OR p.email ILIKE %s
           OR j.affiliation ILIKE %s;
    """, (f"%{key}%", f"%{key}%", f"%{key}%", f"%{key}%"))

    rows = cur.fetchall()

    if not rows:
        print("No jury members found.")
    else:
        print("\n--- Jury Members ---")
        for r in rows:
            print(f"""
    ID: {r[0]}
    Name: {r[1]} {r[2]}
    Email: {r[3]}
    Affiliation: {r[4]}
    Expertise: {r[5]}
    Created At: {r[6]}
            """)

    cur.close()
    con.close()
def update_jury_member():
    con = get_connection()
    cur = con.cursor()

    jid = input("Enter Jury Member person_id to update: ")

    print("\nLeave field empty to keep the current value.")

    new_email = input("New Email: ")
    new_phone = input("New Phone: ")
    new_aff = input("New Affiliation: ")
    new_notes = input("New Expertise Notes: ")

    try:
        # Update persons
        cur.execute("""
            UPDATE persons 
            SET email = COALESCE(NULLIF(%s,''), email),
                phone = COALESCE(NULLIF(%s,''), phone)
            WHERE person_id = %s;
        """, (new_email, new_phone, jid))

        # Update jury
        cur.execute("""
            UPDATE jury_members
            SET affiliation = COALESCE(NULLIF(%s,''), affiliation),
                expertise_notes = COALESCE(NULLIF(%s,''), expertise_notes)
            WHERE person_id = %s;
        """, (new_aff, new_notes, jid))

        con.commit()
        print("Jury member updated successfully!")

    except Exception as e:
        con.rollback()
        print("Error:", e)

    cur.close()
    con.close()

def delete_jury_member():
    con = get_connection()
    cur = con.cursor()

    jid = input("Enter Jury Member person_id to delete: ")

    try:
        cur.execute("DELETE FROM persons WHERE person_id = %s;", (jid,))
        con.commit()

        print("Jury member deleted successfully!")

    except Exception as e:
        con.rollback()
        print("Error:", e)

    cur.close()
    con.close()


# -------------------------
# Venues / Halls / Festival
# -------------------------
def add_venue():
    print("\n-- Add Venue --")
    name = input("Venue name: ").strip()
    address = input("Address (optional): ").strip() or None
    city = input("City (optional): ").strip() or None
    capacity = get_int_input("Total capacity (optional): ")
    try:
        execute("INSERT INTO venues (name, address, city, capacity_total) VALUES (%s,%s,%s,%s);", (name, address, city, capacity))
        print("Venue added.")
    except Exception as e:
        print("Error:", e)
def list_venues():
    try:
        con = get_connection()
        cur = con.cursor()

        cur.execute("""
            SELECT venue_id, name, address, city, capacity_total
            FROM venues
            ORDER BY venue_id;
        """)

        rows = cur.fetchall()
        print("\n--- VENUES ---")
        if not rows:
            print("No venues found.")
        else:
            for r in rows:
                print(f"""
Venue ID: {r[0]}
Name: {r[1]}
Address: {r[2]}
City: {r[3]}
Total Capacity: {r[4]}
---------------------------""")

        cur.close()
        con.close()

    except Exception as e:
        print("Error listing venues:", e)

def add_hall():
    print("\n-- Add Hall --")
    venue_id = get_int_input("Venue ID: ")
    if venue_id is None:
        print("Cancelled.")
        return
    name = input("Hall name: ").strip()
    seating = get_int_input("Seating capacity: ")
    has_assigned = input("Has assigned seats? (y/N): ").strip().lower() == "y"
    try:
        execute("INSERT INTO hall (venue_id, name, seating_capacity, has_assigned_seats) VALUES (%s,%s,%s,%s);", (venue_id, name, seating, has_assigned))
        print("Hall created.")
    except Exception as e:
        print("Error:", e)

def add_festival_edition():
    print("\n-- Add Festival Edition --")
    year = get_int_input("Year (e.g. 2025): ")
    if not year:
        print("Cancelled.")
        return
    name = input("Edition name (optional): ").strip() or None
    start_date = input("Start date (YYYY-MM-DD): ").strip() or None
    end_date = input("End date (YYYY-MM-DD): ").strip() or None
    try:
        execute("INSERT INTO festival_edition (year, name, start_date, end_date) VALUES (%s,%s,%s,%s);", (year, name, start_date, end_date))
        print("Festival edition added.")
    except Exception as e:
        print("Error:", e)

def list_halls():
    try:
        con = get_connection()
        cur = con.cursor()

        cur.execute("""
            SELECT h.hall_id, h.name, h.seating_capacity, h.has_assigned_seats,
                   v.venue_id, v.name AS venue_name
            FROM hall h
            JOIN venues v ON h.venue_id = v.venue_id
            ORDER BY h.hall_id;
        """)

        rows = cur.fetchall()
        print("\n--- HALLS ---")
        if not rows:
            print("No halls found.")
        else:
            for r in rows:
                print(f"""
Hall ID: {r[0]}
Hall Name: {r[1]}
Seating Capacity: {r[2]}
Assigned Seats: {r[3]}
Venue ID: {r[4]}
Venue Name: {r[5]}
---------------------------""")

        cur.close()
        con.close()

    except Exception as e:
        print("Error listing halls:", e)


# -------------------------
# Genres / Films / Submissions / Actors
# -------------------------
def add_genre():
    print("\n-- Add Genre --")
    name = input("Genre name: ").strip()
    try:
        execute("INSERT INTO genres (name) VALUES (%s);", (name,))
        print("Genre added.")
    except Exception as e:
        print("Error:", e)

def list_genres():
    rows = fetchall("SELECT genre_id, name FROM genres ORDER BY name;")
    print("\n-- Genres --")
    for r in rows:
        print(f"{r['genre_id']}: {r['name']}")

#################################################################
def add_submission_and_film():
    print("\n-- Add Submission + Film (calls stored procedure) --")
    pid = get_int_input("Submitting Person ID: ")
    if pid is None:
        print("Cancelled.")
        return
    if not person_exists(pid):
        print("Person not found. Create person first.")
        return

    title = input("Film title: ").strip()
    year = get_int_input("Production year: ")
    country = input("Country (optional): ").strip() or None
    lang = input("Language (optional): ").strip() or None

    try:
        film_id = call_function_single_value(
            "SELECT sp_add_submission_and_film(%s,%s,%s,%s,%s);",
            (pid, title, year, country, lang)
        )
        print(f"Film inserted. film_id = {film_id}")
    except Exception as e:
        print("Error calling sp_add_submission_and_film:", e)

def list_submissions():
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT 
            s.submission_id, 
            s.submission_date, 
            s.status,
            p.person_id, 
            (p.first_name || ' ' || p.last_name) AS full_name,
            f.film_id, 
            f.title, 
            f.production_year
        FROM submissions s
        JOIN persons p ON s.submitting_person_id = p.person_id
        JOIN films f ON f.submission_id = s.submission_id
        ORDER BY s.submission_id;
    """)

    rows = cur.fetchall()

    for r in rows:
        print(f"""
Submission ID: {r[0]}
Date: {r[1]}
Status: {r[2]}
Person: {r[4]} (ID {r[3]})
Film: {r[6]} ({r[7]})
Film ID: {r[5]}
-----------------------------
        """)

    cur.close()
    conn.close()

def search_submission():
    conn = get_connection()
    cur = conn.cursor()

    sid = int(input("Enter submission ID: "))

    cur.execute("""
        SELECT 
            s.submission_id, 
            s.status, 
            s.submission_date,
            (p.first_name || ' ' || p.last_name) AS full_name,
            f.title, 
            f.production_year
        FROM submissions s
        JOIN persons p ON s.submitting_person_id = p.person_id
        JOIN films f ON f.submission_id = s.submission_id
        WHERE s.submission_id = %s;
    """, (sid,))

    row = cur.fetchone()

    if row:
        print(f"""
Submission ID: {row[0]}
Status: {row[1]}
Date: {row[2]}
Submitted by: {row[3]}
Film: {row[4]} ({row[5]})
        """)
    else:
        print("Submission not found.")

    cur.close()
    conn.close()

def update_submission_status():
    conn = get_connection()
    cur = conn.cursor()

    sid = int(input("Submission ID: "))
    new_status = input("New status (pending/approved/rejected): ").lower()

    cur.execute("""
        UPDATE submissions
        SET status = %s
        WHERE submission_id = %s;
    """, (new_status, sid))

    conn.commit()

    if cur.rowcount > 0:
        print("Status updated.")
    else:
        print("Submission not found.")

    cur.close()
    conn.close()
def delete_submission():
    conn = get_connection()
    cur = conn.cursor()

    sid = int(input("Submission ID to delete: "))

    cur.execute("DELETE FROM submissions WHERE submission_id = %s;", (sid,))
    conn.commit()

    if cur.rowcount > 0:
        print("Submission deleted.")
    else:
        print("Submission not found.")

    cur.close()
    conn.close()

def add_film_actor():
    print("\n-- Add Film Actor --")
    film_id = get_int_input("Film ID: ")
    actor_pid = get_int_input("Actor Person ID: ")
    role_name = input("Role name (optional): ").strip() or None
    if film_id is None or actor_pid is None:
        print("Cancelled.")
        return
    try:
        execute("INSERT INTO film_actor (film_id, actor_person_id, role_name) VALUES (%s,%s,%s);", (film_id, actor_pid, role_name))
        print("Actor linked to film.")
    except Exception as e:
        print("Error:", e)

def add_film_genre():
    print("\n-- Add Film Genre --")
    film_id = get_int_input("Film ID: ")
    genre_id = get_int_input("Genre ID: ")
    if film_id is None or genre_id is None:
        print("Cancelled.")
        return
    try:
        execute("INSERT INTO film_genres (film_id, genre_id) VALUES (%s,%s);", (film_id, genre_id))
        print("Genre added to film.")
    except Exception as e:
        print("Error:", e)
        
def print_film_details(cur, film_row):
    film_id, title, year, country, sub_id, person_id, submitter = film_row

    print("\n---------------------------")
    print(f"Film ID: {film_id}")
    print(f"Title: {title}")
    print(f"Year: {year}")
    print(f"Country: {country}")
    print(f"Submitted by: {submitter} (ID:{person_id})" if submitter else "Submitted by: Unknown")
    print(f"Submission ID: {sub_id}")

    # ---- GENRES ----
    cur.execute("""
        SELECT g.name
        FROM genres g
        JOIN film_genres fg ON g.genre_id = fg.genre_id
        WHERE fg.film_id = %s;
    """, (film_id,))
    genres = [g[0] for g in cur.fetchall()]
    print("Genres:", ", ".join(genres) if genres else "None")

    # ---- ACTORS ----
    cur.execute("""
        SELECT p.first_name || ' ' || p.last_name AS actor_name, fa.role_name
        FROM film_actor fa
        JOIN persons p ON fa.actor_person_id = p.person_id
        WHERE fa.film_id = %s;
    """, (film_id,))
    actors = cur.fetchall()
    if actors:
        print("Actors:")
        for a in actors:
            print(f"  - {a[0]} as {a[1]}")
    else:
        print("Actors: None")
    print("---------------------------")

def list_films():
    conn = get_connection()
    cur = conn.cursor()

    print("\n=== List Films ===")
    print("1) List ALL films")
    print("2) List films BY genre")
    print("3) List film BY ID")
    choice = input("Choice: ").strip()

    if choice == "1":
        query = """
            SELECT f.film_id, f.title, f.production_year, f.country,
                   s.submission_id, p.person_id,
                   p.first_name || ' ' || p.last_name AS submitter_name
            FROM films f
            LEFT JOIN submissions s ON f.submission_id = s.submission_id
            LEFT JOIN persons p ON s.submitting_person_id = p.person_id
            ORDER BY f.film_id;
        """
        cur.execute(query)
        films = cur.fetchall()
        for f in films:
            print_film_details(cur, f)

    elif choice == "2":
        genre = input("Enter genre name: ").strip()

        query = """
            SELECT f.film_id, f.title, f.production_year, f.country,
                   s.submission_id, p.person_id,
                   p.first_name || ' ' || p.last_name AS submitter_name
            FROM films f
            JOIN film_genres fg ON f.film_id = fg.film_id
            JOIN genres g ON g.genre_id = fg.genre_id
            LEFT JOIN submissions s ON f.submission_id = s.submission_id
            LEFT JOIN persons p ON s.submitting_person_id = p.person_id
            WHERE LOWER(g.name) = LOWER(%s)
            ORDER BY f.film_id;
        """
        cur.execute(query, (genre,))
        films = cur.fetchall()
        for f in films:
            print_film_details(cur, f)

    elif choice == "3":
        fid = int(input("Film ID: "))

        query = """
            SELECT f.film_id, f.title, f.production_year, f.country,
                   s.submission_id, p.person_id,
                   p.first_name || ' ' || p.last_name AS submitter_name
            FROM films f
            LEFT JOIN submissions s ON f.submission_id = s.submission_id
            LEFT JOIN persons p ON s.submitting_person_id = p.person_id
            WHERE f.film_id = %s;
        """
        cur.execute(query, (fid,))
        film = cur.fetchone()
        if film:
            print_film_details(cur, film)
        else:
            print("Film not found.")
    else:
        print("Invalid choice.")

    cur.close()
    conn.close()


# -------------------------
# Screenings
# -------------------------
def schedule_screening():
    print("\n-- Schedule Screening --")
    film_id = get_int_input("Film ID: ")
    hall_id = get_int_input("Hall ID (or empty): ")
    festival_id = get_int_input("Festival ID (or empty): ")
    start = input("Start timestamp (YYYY-MM-DD HH:MM:SS): ").strip() or None
    end = input("End timestamp (YYYY-MM-DD HH:MM:SS): ").strip() or None
    lang = input("Language version (optional): ").strip() or None
    capacity = get_int_input("Capacity limit (optional): ")
    try:
        execute("""
            INSERT INTO screenings (film_id, hall_id, festival_id, screening_start, screening_end, language_version, capacity_limit)
            VALUES (%s,%s,%s,%s,%s,%s,%s);
        """, (film_id, hall_id, festival_id, start, end, lang, capacity))
        print("Screening scheduled. If overlapping in same hall exists, DB trigger will raise an error and rollback.")
    except Exception as e:
        print("Error scheduling screening (possible overlap):", e)

def list_screenings(limit=50):
    print("\n-- Screenings --")
    rows = fetchall("""
        SELECT s.screening_id, f.title, s.screening_start, s.screening_end, h.name AS hall_name, fe.name AS festival_name
        FROM screenings s
        LEFT JOIN films f ON f.film_id = s.film_id
        LEFT JOIN hall h ON h.hall_id = s.hall_id
        LEFT JOIN festival_edition fe ON fe.festival_id = s.festival_id
        ORDER BY s.screening_start NULLS LAST
        LIMIT %s;
    """, (limit,))
    for r in rows:
        print(f"{r['screening_id']}: {r.get('title')} @ {r.get('screening_start')} - {r.get('screening_end')} hall={r.get('hall_name')} festival={r.get('festival_name')}")

# -------------------------
# Tickets & Payments (use stored procedures)
# -------------------------
def purchase_ticket():
    print("\n-- Purchase Ticket (calls stored procedure sp_purchase_ticket) --")
    screening_id = get_int_input("Screening ID: ")
    person_id = get_int_input("Buyer Person ID: ")
    seat = input("Seat label (optional): ").strip() or None
    price_str = input("Price (numeric): ").strip()
    try:
        price = float(price_str)
    except:
        print("Invalid price.")
        return
    currency = input("Currency (default TRY): ").strip() or "TRY"
    payment_method = input("Payment method (card/cash): ").strip() or "card"

    # call stored proc
    try:
        ticket_id = call_function_single_value("SELECT sp_purchase_ticket(%s,%s,%s,%s,%s);", (screening_id, person_id, seat, price, currency))
        print(f"Ticket purchased: ticket_id = {ticket_id}")
    except Exception as e:
        print("Error purchasing ticket (proc may raise exception):", e)

def refund_ticket():
    print("\n-- Refund Ticket (calls stored procedure sp_refund_ticket) --")

    ticket_id = get_int_input("Ticket ID to refund: ")
    if ticket_id is None:
        print("Cancelled.")
        return

    reason = input("Reason (optional): ").strip() or None

    try:
        result = call_function_single_value(
            "SELECT sp_refund_ticket(%s, %s);",
            (ticket_id, reason)
        )

        if result:
            print(" Ticket refunded successfully.")
        else:
            print(" Refund function returned FALSE (unexpected).")

    except Exception as e:
        # This catches exceptions thrown by PL/pgSQL, such as:
        #   RAISE EXCEPTION 'Ticket % not found'
        print("\n Error calling sp_refund_ticket:")
        print(e)


def list_tickets():
    print("\n-- List Tickets --")
    print("1) List ALL tickets")
    print("2) List by Film ID")
    print("3) List by Film Title")
    choice = input("Choice: ").strip()

    conn = get_connection()
    cur = conn.cursor()

    if choice == "1":
        cur.execute("""
            SELECT 
                t.ticket_id,
                f.film_id,
                f.title,
                t.screening_id,
                p.first_name || ' ' || p.last_name AS attendee_name,
                t.seat_label,
                t.price,
                t.status,
                t.purchased_at
            FROM tickets t
            LEFT JOIN attendees a ON t.attendee_person_id = a.person_id
            LEFT JOIN persons p ON a.person_id = p.person_id
            JOIN screenings s ON t.screening_id = s.screening_id
            JOIN films f ON s.film_id = f.film_id
            ORDER BY t.ticket_id;
        """)
    
    elif choice == "2":
        film_id = input("Enter Film ID: ").strip()
        cur.execute("""
            SELECT 
                t.ticket_id,
                f.film_id,
                f.title,
                t.screening_id,
                p.first_name || ' ' || p.last_name AS attendee_name,
                t.seat_label,
                t.price,
                t.status,
                t.purchased_at
            FROM tickets t
            LEFT JOIN attendees a ON t.attendee_person_id = a.person_id
            LEFT JOIN persons p ON a.person_id = p.person_id
            JOIN screenings s ON t.screening_id = s.screening_id
            JOIN films f ON s.film_id = f.film_id
            WHERE f.film_id = %s
            ORDER BY t.ticket_id;
        """, (film_id,))
    
    elif choice == "3":
        title = input("Enter Film Title (partial OK): ").strip()
        cur.execute("""
            SELECT 
                t.ticket_id,
                f.film_id,
                f.title,
                t.screening_id,
                p.first_name || ' ' || p.last_name AS attendee_name,
                t.seat_label,
                t.price,
                t.status,
                t.purchased_at
            FROM tickets t
            LEFT JOIN attendees a ON t.attendee_person_id = a.person_id
            LEFT JOIN persons p ON a.person_id = p.person_id
            JOIN screenings s ON t.screening_id = s.screening_id
            JOIN films f ON s.film_id = f.film_id
            WHERE LOWER(f.title) LIKE LOWER(%s)
            ORDER BY t.ticket_id;
        """, (f"%{title}%",))

    else:
        print("Invalid choice.")
        cur.close()
        conn.close()
        return

    rows = cur.fetchall()
    if not rows:
        print("No tickets found.")
    else:
        for r in rows:
            print(f"""
Ticket ID: {r[0]}
Film: {r[2]} (ID {r[1]})
Screening ID: {r[3]}
Attendee: {r[4]}
Seat: {r[5]}
Price: {r[6]}
Status: {r[7]}
Purchased at: {r[8]}
----------------------------------------
""")

    cur.close()
    conn.close()


# -------------------------
# Awards & Sponsors
# -------------------------

def fetch_all(query, params=None):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(query, params or ())
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return rows


def fetch_one(query, params=None):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(query, params or ())
    row = cur.fetchone()
    cur.close()
    conn.close()
    return row


def call_query(query, params=None):
    """Runs a SELECT query and returns fetchall() results."""
    return fetch_all(query, params)


def add_award_category():
    print("\n-- Add Award Category --")
    name = input("Category name: ").strip()
    desc = input("Description (optional): ").strip() or None
    try:
        execute("INSERT INTO award_categories (name, description) VALUES (%s,%s);", (name, desc))
        print("Award category added.")
    except Exception as e:
        print("Error:", e)

def add_award():
    print("\n-- Add Award to Film --")
    edition_year = get_int_input("Edition year: ")
    name = input("Award name: ").strip()
    award_type = input("Award type (optional): ").strip() or None
    film_id = get_int_input("Film ID (optional): ")
    cat_id = get_int_input("Category ID (optional): ")
    try:
        execute("INSERT INTO awards (edition_year, name, award_type, film_id, category_id) VALUES (%s,%s,%s,%s,%s);",
                (edition_year, name, award_type, film_id, cat_id))
        print("Award inserted.")
    except Exception as e:
        print("Error:", e)

def list_awards():
    print("\n-- List Awards --")
    conn = get_connection()
    cur = conn.cursor()

    try:
        cur.execute("""
            SELECT a.award_id,
                   a.name AS award_name,
                   a.award_type,
                   ac.name AS category_name,
                   f.title AS film_title,
                   a.edition_year
            FROM awards a
            LEFT JOIN award_categories ac ON a.category_id = ac.category_id
            LEFT JOIN films f ON a.film_id = f.film_id
            ORDER BY a.award_id;
        """)

        rows = cur.fetchall()

        if not rows:
            print("No awards found.")
        else:
            for r in rows:
                print(f"""
Award ID: {r[0]}
Award Name: {r[1]}
Award Type: {r[2]}
Category: {r[3]}
Film (Winner): {r[4]}
Edition Year: {r[5]}
--------------------------------
                """)

    except Exception as e:
        print("Error listing awards:", e)

    cur.close()
    conn.close()


def search_award():
    print("\n-- Search Award --")
    aid = get_int_input("Award ID: ")
    if aid is None:
        print("Cancelled.")
        return

    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT a.award_id, a.name, a.award_type, a.edition_year,
               f.film_id, f.title,
               c.category_id, c.name
        FROM awards a
        LEFT JOIN films f ON a.film_id = f.film_id
        LEFT JOIN award_categories c ON a.category_id = c.category_id
        WHERE a.award_id = %s;
    """, (aid,))

    row = cur.fetchone()

    if row:
        print(f"""
Award ID: {row[0]}
Award Name: {row[1]}
Type: {row[2]}
Edition Year: {row[3]}
Film: {row[5]} (Film ID: {row[4]})
Category: {row[7]} (Category ID: {row[6]})
        """)
    else:
        print("Award not found.")

    cur.close()
    conn.close()

def delete_award():
    print("\n-- Delete Award --")
    aid = get_int_input("Award ID to delete: ")
    if aid is None:
        print("Cancelled.")
        return

    conn = get_connection()
    cur = conn.cursor()

    cur.execute("DELETE FROM awards WHERE award_id = %s;", (aid,))
    conn.commit()

    if cur.rowcount > 0:
        print("Award deleted.")
    else:
        print("Award not found.")

    cur.close()
    conn.close()

def add_sponsor_tier():
    print("\n-- Add Sponsor Tier --")
    name = input("Tier name: ").strip()
    benefits = input("Benefits description: ").strip() or None
    try:
        execute("INSERT INTO sponsor_tiers (name, benefits_desc) VALUES (%s,%s);", (name, benefits))
        print("Sponsor tier added.")
    except Exception as e:
        print("Error:", e)

def add_sponsor():
    print("\n-- Add Sponsor --")
    name = input("Sponsor name: ").strip()
    start = input("Contract start date (YYYY-MM-DD, optional): ").strip() or None
    end = input("Contract end date (YYYY-MM-DD, optional): ").strip() or None
    festival_id = get_int_input("Festival ID (optional): ")
    amount = input("Amount committed (numeric, optional): ").strip() or None
    tier_id = get_int_input("Tier ID (optional): ")
    try:
        execute("INSERT INTO sponsors (name, contract_start, contract_end, festival_id, amount_committed, tier_id) VALUES (%s,%s,%s,%s,%s,%s);",
                (name, start, end, festival_id, amount, tier_id))
        print("Sponsor added.")
    except Exception as e:
        print("Error:", e)

def list_sponsors():
    print("\n-- Sponsors --")
    try:
        rows = call_query("""
            SELECT sponsor_id, name, contract_start, contract_end, festival_id, amount_committed, tier_id
            FROM sponsors
            ORDER BY sponsor_id;
        """)
        if not rows:
            print("No sponsors found.")
            return
        for r in rows:
            print(f"ID: {r[0]} | Name: {r[1]} | Start: {r[2]} | End: {r[3]} | "
                  f"Festival: {r[4]} | Amount: {r[5]} | Tier: {r[6]}")
    except Exception as e:
        print("Error listing sponsors:", e)

def delete_sponsor():
    print("\n-- Delete Sponsor --")
    sponsor_id = get_int_input("Sponsor ID to delete: ")
    if sponsor_id is None:
        print("Cancelled.")
        return
    try:
        execute("DELETE FROM sponsors WHERE sponsor_id = %s;", (sponsor_id,))
        print("Sponsor deleted.")
    except Exception as e:
        print("Error deleting sponsor:", e)


# -------------------------
# Small helpers / diagnostics
# -------------------------


# -------------------------
# Main menu
# -------------------------
# ============================
# MAIN MENU SYSTEM (CLEAN)
# ============================

def menu_persons():
    while True:
        print("\n=== PERSONS MENU ===")
        print("1. Add Person")
        print("2. List Persons")
        print("3. Search Person")
        print("4. Promote to Staff")
        print("5. Back")
        choice = input("Choice: ")

        if choice == "1": add_person()
        elif choice == "2": list_persons()
        elif choice == "3": search_person()
        elif choice == "4": add_staff()
        elif choice == "5": return
        else: print("Invalid choice.")


def menu_staff():
    while True:
        print("\n=== STAFF MENU ===")
        print("1. List Staff")
        print("2. Search Staff")
        print("3. Delete Staff")
        print("4. Back")
        c = input("Choice: ")

        if c == "1": list_staff()
        elif c == "2": search_staff()
        elif c == "3": delete_staff()
        elif c == "4": return
        else: print("Invalid choice.")


def menu_jury():
    while True:
        print("\n=== JURY MENU ===")
        print("1. Add Jury Member")
        print("2. List Jury Members")
        print("3. Search Jury Members")
        print("4. Update Jury Member")
        print("5. Delete Jury Member")
        print("6. Back")
        c = input("Choice: ")

        if c == "1": add_jury_member()
        elif c == "2": list_jury_members()
        elif c == "3": search_jury_members()
        elif c == "4": update_jury_member()
        elif c == "5": delete_jury_member()
        elif c == "6": return
        else: print("Invalid choice.")


def menu_venues():
    while True:
        print("\n=== VENUES / HALLS / FESTIVAL ===")
        print("1. Add Venue")
        print("2. List Venues")
        print("3. Add Hall")
        print("4. List Halls")
        print("5. Add Festival Edition")
        print("6. Back")
        c = input("Choice: ")

        if c == "1": add_venue()
        elif c == "2": list_venues()
        elif c == "3": add_hall()
        elif c == "4": list_halls()
        elif c == "5": add_festival_edition()
        elif c == "6": return
        else: print("Invalid choice.")


def menu_films():
    while True:
        print("\n=== FILMS / SUBMISSIONS / GENRES / ACTORS ===")
        print("1. Add Submission + Film")
        print("2. List Submissions")
        print("3. Search Submission")
        print("4. Update Submission Status")
        print("5. Delete Submission")
        print("6. List Films")
        print("7. Add Film Actor")
        print("8. Add Film Genre")
        print("9. Add Genre")
        print("10. List Genres")
        print("11. Back")
        c = input("Choice: ")

        if c == "1": add_submission_and_film()
        elif c == "2": list_submissions()
        elif c == "3": search_submission()
        elif c == "4": update_submission_status()
        elif c == "5": delete_submission()
        elif c == "6": list_films()
        elif c == "7": add_film_actor()
        elif c == "8": add_film_genre()
        elif c == "9": add_genre()
        elif c == "10": list_genres()
        elif c == "11": return
        else: print("Invalid choice.")


def menu_screenings():
    while True:
        print("\n=== SCREENINGS ===")
        print("1. Schedule Screening")
        print("2. List Screenings")
        print("3. Back")
        c = input("Choice: ")

        if c == "1": schedule_screening()
        elif c == "2": list_screenings()
        elif c == "3": return
        else: print("Invalid choice.")


def menu_tickets():
    while True:
        print("\n=== TICKETS ===")
        print("1. Purchase Ticket")
        print("2. Refund Ticket")
        print("3. List Tickets")
        print("4. Back")
        c = input("Choice: ")

        if c == "1": purchase_ticket()
        elif c == "2": refund_ticket()
        elif c == "3": list_tickets()
        elif c == "4": return
        else: print("Invalid choice.")


def menu_awards():
    while True:
        print("\n=== AWARDS ===")
        print("1. Add Award Category")
        print("2. Add Award")
        print("3. List Awards")
        print("4. Back")
        c = input("Choice: ")

        if c == "1": add_award_category()
        elif c == "2": add_award()
        elif c == "3": list_awards()
        elif c == "4": return
        else: print("Invalid choice.")

def menu_sponsors():
    while True:
        print("\n=== SPONSORS ===")
        print("1. Add Sponsor Tier")
        print("2. Add Sponsor")
        print("3. Delete Sponsor")
        print("4. List Sponsors")
        print("5. Back")
        c = input("Choice: ")

        if c == "1": add_sponsor_tier()
        elif c == "2": add_sponsor()
        elif c == "3": delete_sponsor()
        elif c == "4": list_sponsors()
        elif c == "5": return
        else: print("Invalid choice.")


# ============================
# MAIN MENU LOOP
# ============================

def main_menu():
    while True:
        print("\n==== MAIN MENU ====")
        print("1. Persons")
        print("2. Staff")
        print("3. Jury")
        print("4. Venues / Halls / Festival")
        print("5. Films / Submissions")
        print("6. Screenings")
        print("7. Tickets")
        print("8. Awards")
        print("9. Sponsors")
        print("10. Exit")

        choice = input("Choice: ")

        if choice == "1": menu_persons()
        elif choice == "2": menu_staff()
        elif choice == "3": menu_jury()
        elif choice == "4": menu_venues()
        elif choice == "5": menu_films()
        elif choice == "6": menu_screenings()
        elif choice == "7": menu_tickets()
        elif choice == "8": menu_awards()
        elif choice == "9": menu_sponsors ()
        elif choice == "10":
            print("Goodbye!")
            sys.exit()
        else:
            print("Invalid choice.")
            

# RUN PROGRAM
if __name__ == "__main__":
    main_menu()
