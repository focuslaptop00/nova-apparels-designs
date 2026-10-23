import urllib.request
import urllib.parse
import json
import io

# Let's test the database and endpoints directly
from server import init_db, MeeshoReviewHandler
import sqlite3

print("Running internal server test...")
init_db()

conn = sqlite3.connect("reviews.db")
c = conn.cursor()
c.execute("INSERT INTO designs (title, filename, status) VALUES ('Sample Saree Design 01', 'sample1.jpg', 'pending')")
d_id = c.lastrowid
c.execute("INSERT INTO comments (design_id, author, text) VALUES (?, 'Harsh (Owner)', 'Iska border print thoda dull hai')", (d_id,))
c_id = c.lastrowid
c.execute("INSERT INTO replies (comment_id, author, text) VALUES (?, 'Partner 2', 'Haan harsh, mujhe bhi lagging lag raha hai')", (c_id,))
conn.commit()
conn.close()

print(f"Sample data inserted: design_id={d_id}, comment_id={c_id}")
