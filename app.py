"""
Star Cinema - Online Ticket Booking System
Python (OOP) + Streamlit -- no external database, all data kept in memory
for the lifetime of the app session.

Run locally with following command:
    python -m streamlit run app.py
"""

import streamlit as st

from database import DatabaseConfigurationError, SupabaseHall, get_supabase_client

ADMIN_PASSWORD = "admin123"  # change this before submitting / deploying


# ---------------------------------------------------------------------------
# CORE LOGIC (OOP) — StarCinema (base) -> Hall (child)
# ---------------------------------------------------------------------------

# ---------------------------------------------------------------------------
# PAGE CONFIG + STYLING
# ---------------------------------------------------------------------------

st.set_page_config(page_title="Star Cinema", page_icon="🎬", layout="wide")

st.markdown("""
<style>
    .stApp { background: linear-gradient(180deg, #0E1117 0%, #14161c 100%); }

    .cinema-header { text-align: center; padding: 1.4rem 0 0.6rem 0; }
    .cinema-header h1 {
        font-size: 2.4rem;
        font-weight: 800;
        letter-spacing: 2px;
        background: linear-gradient(90deg, #E50914, #ff6a6a);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 0;
    }
    .cinema-header p { color: #9aa0a6; font-size: 0.92rem; margin-top: 0.2rem; }

    @media (max-width: 480px) {
        .cinema-header h1 { font-size: 1.7rem; }
        .cinema-header p { font-size: 0.8rem; }
    }

    .movie-card {
        border-radius: 14px;
        padding: 1.1rem 1.2rem;
        margin-bottom: 0.9rem;
        color: white;
        box-shadow: 0 4px 14px rgba(0,0,0,0.35);
    }
    .movie-card h3 { margin: 0 0 0.3rem 0; }
    .movie-card .meta { opacity: 0.9; font-size: 0.88rem; }
    .movie-card .price {
        display: inline-block; margin-top: 0.5rem;
        background: rgba(255,255,255,0.18);
        padding: 0.15rem 0.6rem; border-radius: 20px;
        font-weight: 700; font-size: 0.85rem;
    }

    .screen-bar {
        width: 100%; height: 10px;
        background: linear-gradient(90deg, transparent, #E50914, transparent);
        border-radius: 50%;
        margin: 0.5rem 0 1.4rem 0;
        opacity: 0.8;
    }
    .screen-label {
        text-align: center; color: #9aa0a6;
        letter-spacing: 6px; font-size: 0.75rem; margin-bottom: 0.2rem;
    }

    .legend-box {
        display: inline-block; width: 14px; height: 14px;
        border-radius: 3px; margin-right: 6px; vertical-align: middle;
    }

    div.stButton > button { border-radius: 8px; font-weight: 600; }

    .role-card {
        border-radius: 16px;
        padding: 2rem 1.5rem;
        text-align: center;
        background: #1c1f26;
        box-shadow: 0 4px 14px rgba(0,0,0,0.35);
    }
</style>
""", unsafe_allow_html=True)


def header(subtitle):
    st.markdown(f"""
    <div class="cinema-header">
        <h1>🎬 STAR CINEMA</h1>
        <p>{subtitle}</p>
    </div>
    """, unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# SESSION STATE
# ---------------------------------------------------------------------------

def init_state():
    if "hall" not in st.session_state:
        st.session_state.hall = SupabaseHall(get_supabase_client())
    if "role" not in st.session_state:
        st.session_state.role = None
    if "admin_ok" not in st.session_state:
        st.session_state.admin_ok = False
    if "selected_seats" not in st.session_state:
        st.session_state.selected_seats = set()
    if "last_show" not in st.session_state:
        st.session_state.last_show = None


try:
    init_state()
except DatabaseConfigurationError as error:
    st.error("Database connection is not configured.")
    st.code(str(error))
    st.stop()
hall = st.session_state.hall


# ---------------------------------------------------------------------------
# SHARED TAB RENDER FUNCTIONS (used by both User and Admin)
# ---------------------------------------------------------------------------

def safe_render(func, *args, **kwargs):
    """Run a render_* function, showing a friendly message instead of crashing on DB errors."""
    try:
        return func(*args, **kwargs)
    except DatabaseConfigurationError as error:
        st.error("Supabase connection failed.")
        st.info(str(error))


def render_available_shows(hall, key_prefix):
    st.subheader("Now Showing")
    shows = hall.get_shows()
    if not shows:
        st.info("No shows available right now.")
        return

    cols = st.columns(min(3, len(shows)))
    for i, show in enumerate(shows):
        free = hall.available_seat_count(show["show_id"])
        total = show["total_rows"] * show["total_cols"]
        with cols[i % len(cols)]:
            st.markdown(f"""
            <div class="movie-card" style="background:{show['poster_color']};">
                <h3>{show['movie_name']}</h3>
                <div class="meta">🎫 Show ID: {show['show_id']}</div>
                <div class="meta">🕐 {show['show_time']}</div>
                <div class="meta">💺 {free}/{total} seats free</div>
                <div class="price">৳{show['ticket_price']} / seat</div>
            </div>
            """, unsafe_allow_html=True)
            st.progress(free / total if total else 0)


def render_available_seats(hall, key_prefix):
    st.subheader("Check Available Seats")
    shows = hall.get_shows()
    if not shows:
        st.info("No shows available right now.")
        return

    options = {f"{s['movie_name']} — {s['show_time']} ({s['show_id']})": s for s in shows}
    label = st.selectbox("Select a show to preview seats", list(options.keys()), key=f"{key_prefix}_preview_select")
    show = options[label]
    grid = hall.get_seat_grid(show["show_id"])

    st.markdown('<div class="screen-label">S C R E E N</div>', unsafe_allow_html=True)
    st.markdown('<div class="screen-bar"></div>', unsafe_allow_html=True)

    c1, c2 = st.columns(2)
    c1.markdown('<span class="legend-box" style="background:#2a2f3a;border:1px solid #555;"></span> Available', unsafe_allow_html=True)
    c2.markdown('<span class="legend-box" style="background:#444;"></span> Booked', unsafe_allow_html=True)
    st.write("")

    for r in range(show["total_rows"]):
        row_cols = st.columns([0.4] + [1] * show["total_cols"])
        row_cols[0].markdown(f"**{chr(65 + r)}**")
        for c in range(show["total_cols"]):
            symbol = str(c) if grid[r][c] else "✕"
            row_cols[c + 1].button(symbol, key=f"{key_prefix}_prev_{show['show_id']}_{r}_{c}",
                                    disabled=True, use_container_width=True)

    st.caption("This is a read-only preview. Go to 'Ticket Booking' to select and book seats.")


def render_ticket_booking(hall, key_prefix):
    st.subheader("Book Tickets")
    shows = hall.get_shows()
    if not shows:
        st.info("No shows available right now.")
        return

    options = {f"{s['movie_name']} — {s['show_time']} ({s['show_id']})": s for s in shows}
    label = st.selectbox("Choose a show", list(options.keys()), key=f"{key_prefix}_book_select")
    show = options[label]
    show_id = show["show_id"]

    if st.session_state.last_show != f"{key_prefix}_{show_id}":
        st.session_state.selected_seats = set()
        st.session_state.last_show = f"{key_prefix}_{show_id}"

    grid = hall.get_seat_grid(show_id)

    st.markdown('<div class="screen-label">S C R E E N</div>', unsafe_allow_html=True)
    st.markdown('<div class="screen-bar"></div>', unsafe_allow_html=True)

    c1, c2, c3 = st.columns(3)
    c1.markdown('<span class="legend-box" style="background:#2a2f3a;border:1px solid #555;"></span> Available', unsafe_allow_html=True)
    c2.markdown('<span class="legend-box" style="background:#E50914;"></span> Selected', unsafe_allow_html=True)
    c3.markdown('<span class="legend-box" style="background:#444;"></span> Booked', unsafe_allow_html=True)
    st.write("")

    for r in range(show["total_rows"]):
        row_cols = st.columns([0.4] + [1] * show["total_cols"])
        row_cols[0].markdown(f"**{chr(65 + r)}**")
        for c in range(show["total_cols"]):
            is_booked = not grid[r][c]
            is_selected = (r, c) in st.session_state.selected_seats
            key = f"{key_prefix}_seat_{show_id}_{r}_{c}"

            if is_booked:
                row_cols[c + 1].button("✕", key=key, disabled=True, use_container_width=True)
            else:
                btn_label = "●" if is_selected else str(c)
                if row_cols[c + 1].button(btn_label, key=key, use_container_width=True):
                    if is_selected:
                        st.session_state.selected_seats.discard((r, c))
                    else:
                        st.session_state.selected_seats.add((r, c))
                    st.rerun()

    st.markdown("---")
    selected = sorted(st.session_state.selected_seats)
    seat_names = ", ".join(f"{chr(65 + r)}{c}" for r, c in selected) or "None"
    total_price = len(selected) * show["ticket_price"]
    st.markdown(f"**Selected seats:** {seat_names}")
    if selected:
        st.info(f"{len(selected)} seat(s) × ৳{show['ticket_price']} = **৳{total_price}**")

    with st.form(f"{key_prefix}_booking_form"):
        fc1, fc2 = st.columns(2)
        name = fc1.text_input("Your name")
        phone = fc2.text_input("Phone number")
        submitted = st.form_submit_button("🎟️ Confirm Booking", use_container_width=True)

        if submitted:
            if not name.strip() or not phone.strip():
                st.error("Please enter your name and phone number.")
            elif not selected:
                st.error("Please select at least one seat.")
            else:
                ok, msg, booking = hall.book_seats(
                    show_id, name.strip(), phone.strip(), selected, show["ticket_price"]
                )
                if ok:
                    st.success(f"✅ Ticket booked successfully! Ticket No: #{booking['ticket_no']}")
                    st.write(f"**Movie:** {show['movie_name']}  |  **Time:** {show['show_time']}")
                    st.write(f"**Seats:** {booking['seat_labels']}")
                    st.write(f"**Total paid:** ৳{booking['total_price']}")
                    st.session_state.selected_seats = set()
                    st.balloons()
                else:
                    st.error(msg)


def render_add_show(hall):
    st.subheader("Add a New Show")
    with st.form("add_show_form"):
        c1, c2 = st.columns(2)
        show_id = c1.text_input("Show ID (unique, e.g. xyz1)")
        movie_name = c2.text_input("Movie name")

        c3, c4 = st.columns(2)
        show_time = c3.text_input("Show time (e.g. 07:00 PM)")
        price = c4.number_input("Ticket price (৳)", min_value=1, value=150, step=10)

        c5, c6 = st.columns(2)
        rows = c5.number_input("Rows", min_value=1, max_value=15, value=5)
        cols = c6.number_input("Seats per row", min_value=1, max_value=15, value=8)

        color = st.color_picker("Card color", "#1f6fb2")
        submitted = st.form_submit_button("Add Show", use_container_width=True)

        if submitted:
            if not show_id.strip() or not movie_name.strip() or not show_time.strip():
                st.error("Please fill in all fields.")
            else:
                ok, msg = hall.add_show(
                    show_id.strip(), movie_name.strip(), show_time.strip(),
                    int(rows), int(cols), int(price), color
                )
                if ok:
                    st.success(msg)
                    st.rerun()
                else:
                    st.error(msg)


def render_manage_shows(hall):
    st.subheader("Manage Shows")
    shows = hall.get_shows()
    if not shows:
        st.info("No shows available right now.")
        return

    options = {f"{show['movie_name']} ({show['show_id']})": show for show in shows}
    selected_label = st.selectbox("Select a show", list(options), key="manage_show_select")
    show = options[selected_label]

    with st.form("edit_show_form"):
        movie_name = st.text_input("Movie name", value=show["movie_name"])
        show_time = st.text_input("Show time", value=show["show_time"])
        price = st.number_input("Ticket price (৳)", min_value=1, value=int(show["ticket_price"]), step=10)
        color = st.color_picker("Card color", value=show["poster_color"])
        submitted = st.form_submit_button("Save Changes", use_container_width=True)
        if submitted:
            if not movie_name.strip() or not show_time.strip():
                st.error("Movie name and show time are required.")
            else:
                ok, message = hall.update_show(
                    show["show_id"], movie_name.strip(), show_time.strip(), int(price), color
                )
                if ok:
                    st.success(message)
                    st.rerun()
                else:
                    st.error(message)

    st.warning("Deleting a show is permanent. Shows with bookings must be cleared first.")
    if st.button("Delete Selected Show", key=f"delete_show_{show['show_id']}", type="secondary"):
        ok, message = hall.delete_show(show["show_id"])
        if ok:
            st.success(message)
            st.rerun()
        else:
            st.error(message)


def render_booked_list(hall):
    st.subheader("All Booked Tickets")
    bookings = hall.get_all_bookings()
    if not bookings:
        st.info("No tickets have been booked yet.")
        return

    st.caption(f"Total bookings: {len(bookings)}")
    for b in bookings:
        with st.container(border=True):
            col1, col2 = st.columns([3, 1])
            with col1:
                st.markdown(f"**Ticket #{b['ticket_no']} — {b['movie_name']}**")
                st.caption(f"{b['show_time']}  •  Seats: {b['seat_labels']}")
                st.caption(f"Booked by: {b['customer_name']}  •  Phone: {b['phone']}  •  Paid: ৳{b['total_price']}")
            with col2:
                if st.button("Cancel", key=f"cancel_{b['ticket_no']}", use_container_width=True):
                    ok, msg = hall.cancel_booking(b["ticket_no"])
                    if ok:
                        st.success(msg)
                        st.rerun()
                    else:
                        st.error(msg)


# ---------------------------------------------------------------------------
# LANDING PAGE: choose User or Admin
# ---------------------------------------------------------------------------
if st.session_state.role is None:
    header("Choose how you'd like to continue")
    st.write("")
    col1, col2 = st.columns(2)

    with col1:
        st.markdown('<div class="role-card"><h2>👤</h2><h3>User</h3>'
                     '<p style="color:#9aa0a6;">View shows, check seats, and book tickets</p></div>',
                     unsafe_allow_html=True)
        st.write("")
        if st.button("Continue as User", use_container_width=True):
            st.session_state.role = "user"
            st.rerun()

    with col2:
        st.markdown('<div class="role-card"><h2>🔑</h2><h3>Admin</h3>'
                     '<p style="color:#9aa0a6;">Manage shows and view all booked tickets</p></div>',
                     unsafe_allow_html=True)
        st.write("")
        if st.button("Continue as Admin", use_container_width=True):
            st.session_state.role = "admin"
            st.rerun()

    st.stop()

# ---------------------------------------------------------------------------
# SIDEBAR: switch role
# ---------------------------------------------------------------------------
with st.sidebar:
    st.markdown(f"### {'👤 User Mode' if st.session_state.role == 'user' else '🔑 Admin Mode'}")
    if st.button("⬅ Switch Role"):
        st.session_state.role = None
        st.session_state.admin_ok = False
        st.session_state.selected_seats = set()
        st.rerun()
    st.markdown("---")
    st.caption("Star Cinema • Python + Streamlit")

# ---------------------------------------------------------------------------
# ADMIN LOGIN GATE
# ---------------------------------------------------------------------------
if st.session_state.role == "admin" and not st.session_state.admin_ok:
    header("Admin Login")
    with st.form("admin_login"):
        pwd = st.text_input("Admin password", type="password")
        submitted = st.form_submit_button("Login", use_container_width=True)
        if submitted:
            if pwd == ADMIN_PASSWORD:
                st.session_state.admin_ok = True
                st.rerun()
            else:
                st.error("Incorrect password.")
    st.stop()

# ---------------------------------------------------------------------------
# USER SIDE
# ---------------------------------------------------------------------------
if st.session_state.role == "user":
    header("Book your movie ticket in a few clicks")

    tab_shows, tab_seats, tab_book = st.tabs(
        ["🎬 Available Shows", "💺 Available Seats", "🎟️ Ticket Booking"]
    )
    with tab_shows:
        safe_render(render_available_shows, hall, "user")
    with tab_seats:
        safe_render(render_available_seats, hall, "user")
    with tab_book:
        safe_render(render_ticket_booking, hall, "user")

# ---------------------------------------------------------------------------
# ADMIN SIDE
# ---------------------------------------------------------------------------
elif st.session_state.role == "admin" and st.session_state.admin_ok:
    header("Admin Dashboard")

    tab_shows, tab_seats, tab_book, tab_add, tab_manage, tab_list = st.tabs(
        ["🎬 Available Shows", "💺 Available Seats", "🎟️ Ticket Booking",
         "➕ Add Show", "⚙️ Manage Shows", "📋 Booked Tickets List"]
    )
    with tab_shows:
        safe_render(render_available_shows, hall, "admin")
    with tab_seats:
        safe_render(render_available_seats, hall, "admin")
    with tab_book:
        safe_render(render_ticket_booking, hall, "admin")
    with tab_add:
        safe_render(render_add_show, hall)
    with tab_manage:
        safe_render(render_manage_shows, hall)
    with tab_list:
        safe_render(render_booked_list, hall)
