#!/usr/bin/env python3
"""
Meesho Product Review Hub for 3 Partners: Harsh, Kiran, Anurag
Zero external dependencies - Uses Python standard library (http.server, sqlite3, json)
"""

import os
import sys
import json
import sqlite3
import mimetypes
import cgi
import re
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse
from datetime import datetime

PORT = int(os.environ.get("PORT", 8080))
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
UPLOADS_DIR = os.path.join(BASE_DIR, "uploads")
DB_PATH = os.path.join(BASE_DIR, "reviews.db")

PARTNERS = ["Harsh", "Kiran", "Anurag"]

os.makedirs(UPLOADS_DIR, exist_ok=True)

def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS designs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL,
        filename TEXT NOT NULL,
        status TEXT DEFAULT 'pending',
        status_by TEXT DEFAULT '',
        status_note TEXT DEFAULT '',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)
    
    # Track each partner's vote separately (Harsh, Kiran, Anurag)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS partner_reviews (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        design_id INTEGER NOT NULL,
        partner_name TEXT NOT NULL,
        status TEXT NOT NULL, -- 'approved', 'rejected', 'complaint'
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(design_id, partner_name) ON CONFLICT REPLACE,
        FOREIGN KEY (design_id) REFERENCES designs(id) ON DELETE CASCADE
    )
    """)
    
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS comments (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        design_id INTEGER NOT NULL,
        author TEXT NOT NULL,
        text TEXT NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (design_id) REFERENCES designs(id) ON DELETE CASCADE
    )
    """)
    
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS replies (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        comment_id INTEGER NOT NULL,
        author TEXT NOT NULL,
        text TEXT NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (comment_id) REFERENCES comments(id) ON DELETE CASCADE
    )
    """)
    
    conn.commit()
    conn.close()

init_db()

class MeeshoReviewHandler(BaseHTTPRequestHandler):
    def get_db(self):
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        return conn

    def send_json(self, data, status=200):
        response = json.dumps(data).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS, DELETE")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.send_header("Content-Length", str(len(response)))
        self.end_headers()
        self.wfile.write(response)

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS, DELETE")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path

        if path == "/":
            index_path = os.path.join(BASE_DIR, "index.html")
            if os.path.exists(index_path):
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                with open(index_path, "rb") as f:
                    content = f.read()
                self.send_header("Content-Length", str(len(content)))
                self.end_headers()
                self.wfile.write(content)
                return
            else:
                self.send_error(404, "index.html not found")
                return

        elif path.startswith("/uploads/"):
            filename = os.path.basename(path)
            file_path = os.path.join(UPLOADS_DIR, filename)
            if os.path.exists(file_path) and os.path.isfile(file_path):
                mime, _ = mimetypes.guess_type(file_path)
                self.send_response(200)
                self.send_header("Content-Type", mime or "application/octet-stream")
                with open(file_path, "rb") as f:
                    content = f.read()
                self.send_header("Content-Length", str(len(content)))
                self.end_headers()
                self.wfile.write(content)
                return
            else:
                self.send_error(404, "File not found")
                return

        elif path == "/api/designs":
            conn = self.get_db()
            cursor = conn.cursor()
            
            cursor.execute("SELECT * FROM designs ORDER BY id DESC")
            designs_rows = cursor.fetchall()
            
            results = []
            for d in designs_rows:
                d_dict = dict(d)
                
                # Fetch individual partner reviews
                cursor.execute("SELECT partner_name, status, updated_at FROM partner_reviews WHERE design_id = ?", (d['id'],))
                p_reviews = {r['partner_name']: r['status'] for r in cursor.fetchall()}
                
                # Ensure all 3 partners exist in dict
                d_dict['partner_reviews'] = {
                    p: p_reviews.get(p, 'pending') for p in PARTNERS
                }
                
                # Fetch comments
                cursor.execute("SELECT * FROM comments WHERE design_id = ? ORDER BY id ASC", (d['id'],))
                comments_rows = cursor.fetchall()
                
                comments_list = []
                for c in comments_rows:
                    c_dict = dict(c)
                    # Fetch replies
                    cursor.execute("SELECT * FROM replies WHERE comment_id = ? ORDER BY id ASC", (c['id'],))
                    replies_rows = cursor.fetchall()
                    c_dict['replies'] = [dict(r) for r in replies_rows]
                    comments_list.append(c_dict)
                
                d_dict['comments'] = comments_list
                results.append(d_dict)
                
            conn.close()
            self.send_json({"designs": results, "partners": PARTNERS})
            return

        self.send_error(404, "Endpoint not found")

    def do_POST(self):
        parsed = urlparse(self.path)
        path = parsed.path

        # Bulk Image Upload
        if path == "/api/upload":
            content_type = self.headers.get('Content-Type', '')
            if not content_type.startswith('multipart/form-data'):
                self.send_json({"error": "Expected multipart/form-data"}, 400)
                return

            try:
                content_len = self.headers.get('Content-Length')
                environ = {
                    'REQUEST_METHOD': 'POST',
                    'CONTENT_TYPE': content_type,
                }
                if content_len:
                    environ['CONTENT_LENGTH'] = content_len

                form = cgi.FieldStorage(
                    fp=self.rfile,
                    headers=self.headers,
                    environ=environ
                )

                if 'files' not in form:
                    self.send_json({"error": "No files provided"}, 400)
                    return

                file_fields = form['files']
                if not isinstance(file_fields, list):
                    file_fields = [file_fields]

                saved_count = 0
                conn = self.get_db()
                cursor = conn.cursor()

                for item in file_fields:
                    if item.filename:
                        orig_filename = item.filename
                        clean_name = re.sub(r'[^a-zA-Z0-9_\.-]', '_', orig_filename)
                        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
                        stored_filename = f"{timestamp}_{clean_name}"
                        dest_path = os.path.join(UPLOADS_DIR, stored_filename)

                        with open(dest_path, "wb") as f:
                            f.write(item.file.read())

                        title = os.path.splitext(orig_filename)[0].replace('_', ' ').replace('-', ' ').title()
                        cursor.execute(
                            "INSERT INTO designs (title, filename, status) VALUES (?, ?, 'pending')",
                            (title, stored_filename)
                        )
                        saved_count += 1

                conn.commit()
                conn.close()
                self.send_json({"success": True, "count": saved_count})
                return

            except Exception as e:
                self.send_json({"error": str(e)}, 500)
                return

        # Parse JSON Body
        content_len = int(self.headers.get('Content-Length', 0))
        post_data = self.rfile.read(content_len) if content_len > 0 else b'{}'
        try:
            body = json.loads(post_data.decode('utf-8'))
        except Exception:
            body = {}

        # Set Partner Specific Status (Harsh / Kiran / Anurag)
        # Match /api/designs/<id>/partner-status
        m_partner_status = re.match(r"^/api/designs/(\d+)/partner-status$", path)
        if m_partner_status:
            design_id = int(m_partner_status.group(1))
            partner = body.get('partner', '').strip()
            status = body.get('status', 'pending') # 'approved', 'rejected', 'complaint'

            if partner not in PARTNERS:
                self.send_json({"error": f"Invalid partner. Must be one of {PARTNERS}"}, 400)
                return

            conn = self.get_db()
            cursor = conn.cursor()
            
            # Upsert into partner_reviews
            cursor.execute("""
                INSERT INTO partner_reviews (design_id, partner_name, status, updated_at)
                VALUES (?, ?, ?, CURRENT_TIMESTAMP)
                ON CONFLICT(design_id, partner_name) 
                DO UPDATE SET status = excluded.status, updated_at = CURRENT_TIMESTAMP
            """, (design_id, partner, status))

            # Also update design updated_at
            cursor.execute("UPDATE designs SET updated_at = CURRENT_TIMESTAMP WHERE id = ?", (design_id,))
            conn.commit()
            conn.close()
            self.send_json({"success": True})
            return

        # Add Comment
        m_comment = re.match(r"^/api/designs/(\d+)/comments$", path)
        if m_comment:
            design_id = int(m_comment.group(1))
            author = body.get('author', '').strip()
            text = body.get('text', '').strip()
            if not text:
                self.send_json({"error": "Comment cannot be empty"}, 400)
                return

            conn = self.get_db()
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO comments (design_id, author, text) VALUES (?, ?, ?)",
                (design_id, author, text)
            )
            comment_id = cursor.lastrowid
            conn.commit()
            conn.close()
            self.send_json({"success": True, "comment_id": comment_id})
            return

        # Reply to Comment
        m_reply = re.match(r"^/api/comments/(\d+)/reply$", path)
        if m_reply:
            comment_id = int(m_reply.group(1))
            author = body.get('author', '').strip()
            text = body.get('text', '').strip()
            if not text:
                self.send_json({"error": "Reply cannot be empty"}, 400)
                return

            conn = self.get_db()
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO replies (comment_id, author, text) VALUES (?, ?, ?)",
                (comment_id, author, text)
            )
            reply_id = cursor.lastrowid
            conn.commit()
            conn.close()
            self.send_json({"success": True, "reply_id": reply_id})
            return

        # Delete Design
        m_del = re.match(r"^/api/designs/(\d+)/delete$", path)
        if m_del:
            design_id = int(m_del.group(1))
            conn = self.get_db()
            cursor = conn.cursor()
            cursor.execute("SELECT filename FROM designs WHERE id = ?", (design_id,))
            row = cursor.fetchone()
            if row:
                img_path = os.path.join(UPLOADS_DIR, row['filename'])
                if os.path.exists(img_path):
                    try:
                        os.remove(img_path)
                    except Exception:
                        pass
                cursor.execute("DELETE FROM designs WHERE id = ?", (design_id,))
                conn.commit()
            conn.close()
            self.send_json({"success": True})
            return

        self.send_error(404, "Endpoint not found")

def run():
    server_address = ('', PORT)
    httpd = HTTPServer(server_address, MeeshoReviewHandler)
    print(f"🚀 Meesho Review App running at: http://localhost:{PORT}")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping server...")
        httpd.server_close()

if __name__ == "__main__":
    run()
