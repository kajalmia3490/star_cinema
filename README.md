# Star Cinema Seat Booking

Streamlit-based movie ticket booking system using Supabase for persistent shows,
bookings, and seat reservations.

## Supabase API setup

1. Create a project at [Supabase](https://supabase.com/dashboard).
2. Open **SQL Editor**, paste and run the full contents of `supabase_schema.sql`.
	It creates the tables, an atomic booking function, and the initial three shows.
3. In **Project Settings > API Keys**, create or copy a server-side secret key.
4. For local development create `.streamlit/secrets.toml` (do not commit it):

	```toml
	SUPABASE_URL = "https://bkxkmehxtibzwhhmojsf.supabase.co"
	SUPABASE_SECRET_KEY = "your-server-side-secret-key"
	```

5. In Streamlit Community Cloud, open the app dashboard, choose **Settings > Secrets**,
	and paste the same values. Then redeploy the app.

`SUPABASE_SECRET_KEY` is used only by the Streamlit server and must never be committed or sent
to a browser. Do not use the publishable key for this setting. Rotate any secret key that was
shared outside the Supabase or Streamlit secret managers.

## Run locally

```bash
pip install -r requirements.txt
python -m streamlit run app.py
```

## Current database operations

- Users can create bookings and view live seat availability.
- Admins can create, read, update, and delete shows.
- Admins can list and cancel bookings; cancelling releases the booked seats.
- `create_booking` performs booking and seat reservation in one database transaction,
  so concurrent customers cannot successfully reserve the same seat.