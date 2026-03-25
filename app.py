"""
app.py – OlaMedia Flask API
Exposes CRUD routes for Books, Movies, Music, and the User Ratings system.
"""
 
from flask import Flask, jsonify, request
from flask_cors import CORS
from database import get_db_connection, init_db, recalculate_avg
 
app = Flask(__name__)
CORS(app)   # Allow cross-origin requests from the frontend
 
 
# ── Validation helpers ──────────────────────────────────────────────────────
 
VALID_MEDIA_TYPES = {"book", "movie", "music"}
MEDIA_TABLE_MAP   = {"book": "books", "movie": "movies", "music": "music"}
 
 
def _validate_score(score):
    """Return (float, None) on success or (None, error_string) on failure."""
    try:
        score = float(score)
    except (TypeError, ValueError):
        return None, "score must be a number"
    if not (0 <= score <= 10):
        return None, "score must be between 0 and 10"
    return score, None
 
 
# ── Health check ────────────────────────────────────────────────────────────
 
@app.route("/api/health", methods=["GET"])
def health():
    return jsonify({"status": "ok", "message": "OlaMedia API is running"})
 
 
# ════════════════════════════════════════════════════════════════════════════
# USER RATINGS  –  shared across all media types
# ════════════════════════════════════════════════════════════════════════════
#
# POST   /api/ratings                           Submit (or update) a rating
# GET    /api/ratings/<media_type>/<media_id>   All ratings for one item
# GET    /api/ratings/<media_type>/<media_id>/summary  Avg + count only
# GET    /api/ratings/user/<user_id>            All ratings by one user
# DELETE /api/ratings/<media_type>/<media_id>/<user_id>  Remove a rating
# GET    /api/ratings/top/<media_type>          Top-rated items by avg score
#
# ════════════════════════════════════════════════════════════════════════════
 
@app.route("/api/ratings", methods=["POST"])
def submit_rating():
    """
    Submit or update a user rating.
 
    Body (JSON):
        media_type  – 'book' | 'movie' | 'music'
        media_id    – integer id of the media item
        score       – float 0-10
        user_id     – (optional) string identifier; defaults to 'anonymous'
    """
    data = request.get_json(silent=True) or {}
 
    # ── Validate input
    media_type = data.get("media_type", "").strip().lower()
    if media_type not in VALID_MEDIA_TYPES:
        return jsonify({"error": f"media_type must be one of {sorted(VALID_MEDIA_TYPES)}"}), 400
 
    try:
        media_id = int(data["media_id"])
    except (KeyError, ValueError, TypeError):
        return jsonify({"error": "media_id must be a valid integer"}), 400
 
    score, err = _validate_score(data.get("score"))
    if err:
        return jsonify({"error": err}), 400
 
    user_id = str(data.get("user_id", "anonymous")).strip() or "anonymous"
 
    # ── Verify the media item actually exists
    conn = get_db_connection()
    table = MEDIA_TABLE_MAP[media_type]
    item = conn.execute(f"SELECT id FROM {table} WHERE id = ?", (media_id,)).fetchone()
    if item is None:
        conn.close()
        return jsonify({"error": f"{media_type.capitalize()} with id {media_id} not found"}), 404
 
    # ── Upsert: INSERT or replace the user's existing score
    conn.execute(
        """
        INSERT INTO user_ratings (media_type, media_id, user_id, score, rated_at)
        VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
        ON CONFLICT(media_type, media_id, user_id)
        DO UPDATE SET score = excluded.score, rated_at = CURRENT_TIMESTAMP
        """,
        (media_type, media_id, user_id, score),
    )
    conn.commit()
 
    # ── Sync aggregate columns back to the media table
    recalculate_avg(conn, media_type, media_id)
 
    # ── Return the updated media row so the frontend can refresh immediately
    updated = conn.execute(
        f"SELECT * FROM {table} WHERE id = ?", (media_id,)
    ).fetchone()
    conn.close()
 
    return jsonify({
        "message": "Rating saved",
        "rating": {
            "media_type":  media_type,
            "media_id":    media_id,
            "user_id":     user_id,
            "score":       score,
        },
        "media_item": dict(updated),
    }), 201
 
 
@app.route("/api/ratings/<media_type>/<int:media_id>", methods=["GET"])
def get_ratings_for_item(media_type, media_id):
    """Return every individual rating for a specific media item."""
    media_type = media_type.lower()
    if media_type not in VALID_MEDIA_TYPES:
        return jsonify({"error": f"Invalid media_type '{media_type}'"}), 400
 
    conn = get_db_connection()
    rows = conn.execute(
        """
        SELECT user_id, score, rated_at
        FROM   user_ratings
        WHERE  media_type = ? AND media_id = ?
        ORDER  BY rated_at DESC
        """,
        (media_type, media_id),
    ).fetchall()
    conn.close()
 
    return jsonify({
        "media_type": media_type,
        "media_id":   media_id,
        "ratings":    [dict(r) for r in rows],
        "count":      len(rows),
    })
 
 
@app.route("/api/ratings/<media_type>/<int:media_id>/summary", methods=["GET"])
def get_rating_summary(media_type, media_id):
    """Return just the aggregate average and vote count for one item."""
    media_type = media_type.lower()
    if media_type not in VALID_MEDIA_TYPES:
        return jsonify({"error": f"Invalid media_type '{media_type}'"}), 400
 
    conn = get_db_connection()
    row = conn.execute(
        """
        SELECT COUNT(*) AS cnt, AVG(score) AS avg, MIN(score) AS low, MAX(score) AS high
        FROM   user_ratings
        WHERE  media_type = ? AND media_id = ?
        """,
        (media_type, media_id),
    ).fetchone()
    conn.close()
 
    return jsonify({
        "media_type":   media_type,
        "media_id":     media_id,
        "average_score": round(row["avg"], 2) if row["avg"] else None,
        "total_votes":  row["cnt"],
        "lowest_score": row["low"],
        "highest_score": row["high"],
    })
 
 
@app.route("/api/ratings/user/<user_id>", methods=["GET"])
def get_ratings_by_user(user_id):
    """
    Return all ratings submitted by a specific user.
    Useful for personalised recommendation input.
    """
    conn = get_db_connection()
    rows = conn.execute(
        """
        SELECT ur.media_type, ur.media_id, ur.score, ur.rated_at,
               CASE ur.media_type
                   WHEN 'book'  THEN b.name
                   WHEN 'movie' THEN m.name
                   WHEN 'music' THEN mu.name
               END AS media_name,
               CASE ur.media_type
                   WHEN 'book'  THEN b.genre
                   WHEN 'movie' THEN m.genre
                   WHEN 'music' THEN mu.genre
               END AS genre
        FROM   user_ratings ur
        LEFT JOIN books  b  ON ur.media_type = 'book'  AND ur.media_id = b.id
        LEFT JOIN movies m  ON ur.media_type = 'movie' AND ur.media_id = m.id
        LEFT JOIN music  mu ON ur.media_type = 'music' AND ur.media_id = mu.id
        WHERE  ur.user_id = ?
        ORDER  BY ur.rated_at DESC
        """,
        (user_id,),
    ).fetchall()
    conn.close()
 
    return jsonify({
        "user_id": user_id,
        "total_ratings": len(rows),
        "ratings": [dict(r) for r in rows],
    })
 
 
@app.route("/api/ratings/<media_type>/<int:media_id>/<user_id>", methods=["DELETE"])
def delete_rating(media_type, media_id, user_id):
    """Remove a user's rating for a specific item and resync the average."""
    media_type = media_type.lower()
    if media_type not in VALID_MEDIA_TYPES:
        return jsonify({"error": f"Invalid media_type '{media_type}'"}), 400
 
    conn = get_db_connection()
    conn.execute(
        "DELETE FROM user_ratings WHERE media_type = ? AND media_id = ? AND user_id = ?",
        (media_type, media_id, user_id),
    )
    conn.commit()
    recalculate_avg(conn, media_type, media_id)
    conn.close()
 
    return jsonify({"message": f"Rating removed for {media_type} {media_id} by {user_id}"})
 
 
@app.route("/api/ratings/top/<media_type>", methods=["GET"])
def get_top_rated(media_type):
    """
    Return media items sorted by user_rating_avg descending.
    Accepts optional query param:  ?min_votes=5  (default 1)
    Useful as a fast recommendation signal.
    """
    media_type = media_type.lower()
    if media_type not in VALID_MEDIA_TYPES:
        return jsonify({"error": f"Invalid media_type '{media_type}'"}), 400
 
    try:
        min_votes = int(request.args.get("min_votes", 1))
    except ValueError:
        min_votes = 1
 
    table = MEDIA_TABLE_MAP[media_type]
    conn = get_db_connection()
    rows = conn.execute(
        f"""
        SELECT * FROM {table}
        WHERE  user_rating_count >= ?
        ORDER  BY user_rating_avg DESC
        """,
        (min_votes,),
    ).fetchall()
    conn.close()
 
    return jsonify({
        "media_type":  media_type,
        "min_votes":   min_votes,
        "count":       len(rows),
        "items":       [dict(r) for r in rows],
    })
 
 
# ════════════════════════════════════════════════════════════════════════════
# BOOKS  –  full CRUD
# ════════════════════════════════════════════════════════════════════════════
 
@app.route("/api/books", methods=["GET"])
def get_books():
    conn = get_db_connection()
    rows = conn.execute("SELECT * FROM books").fetchall()
    conn.close()
    return jsonify([dict(r) for r in rows])
 
 
@app.route("/api/books/<int:book_id>", methods=["GET"])
def get_book(book_id):
    conn = get_db_connection()
    row = conn.execute("SELECT * FROM books WHERE id = ?", (book_id,)).fetchone()
    conn.close()
    if row is None:
        return jsonify({"error": "Book not found"}), 404
    return jsonify(dict(row))
 
 
@app.route("/api/books", methods=["POST"])
def add_book():
    data = request.get_json(silent=True) or {}
    required = ["name", "genre", "description", "rating", "image_dir"]
    missing = [k for k in required if k not in data]
    if missing:
        return jsonify({"error": f"Missing fields: {missing}"}), 400
    conn = get_db_connection()
    cur = conn.execute(
        "INSERT INTO books (name, genre, description, rating, image_dir) VALUES (?, ?, ?, ?, ?)",
        (data["name"], data["genre"], data["description"], data["rating"], data["image_dir"]),
    )
    conn.commit()
    row = conn.execute("SELECT * FROM books WHERE id = ?", (cur.lastrowid,)).fetchone()
    conn.close()
    return jsonify(dict(row)), 201
 
 
@app.route("/api/books/<int:book_id>", methods=["PUT"])
def update_book(book_id):
    data = request.get_json(silent=True) or {}
    conn = get_db_connection()
    row = conn.execute("SELECT * FROM books WHERE id = ?", (book_id,)).fetchone()
    if row is None:
        conn.close()
        return jsonify({"error": "Book not found"}), 404
    updated = {**dict(row), **data}
    conn.execute(
        "UPDATE books SET name=?, genre=?, description=?, rating=?, image_dir=? WHERE id=?",
        (updated["name"], updated["genre"], updated["description"],
         updated["rating"], updated["image_dir"], book_id),
    )
    conn.commit()
    row = conn.execute("SELECT * FROM books WHERE id = ?", (book_id,)).fetchone()
    conn.close()
    return jsonify(dict(row))
 
 
@app.route("/api/books/<int:book_id>", methods=["DELETE"])
def delete_book(book_id):
    conn = get_db_connection()
    conn.execute("DELETE FROM books WHERE id = ?", (book_id,))
    conn.commit()
    conn.close()
    return jsonify({"message": f"Book {book_id} deleted"})
 
 
# ════════════════════════════════════════════════════════════════════════════
# MOVIES  –  full CRUD
# ════════════════════════════════════════════════════════════════════════════
 
@app.route("/api/movies", methods=["GET"])
def get_movies():
    conn = get_db_connection()
    rows = conn.execute("SELECT * FROM movies").fetchall()
    conn.close()
    return jsonify([dict(r) for r in rows])
 
 
@app.route("/api/movies/<int:movie_id>", methods=["GET"])
def get_movie(movie_id):
    conn = get_db_connection()
    row = conn.execute("SELECT * FROM movies WHERE id = ?", (movie_id,)).fetchone()
    conn.close()
    if row is None:
        return jsonify({"error": "Movie not found"}), 404
    return jsonify(dict(row))
 
 
@app.route("/api/movies", methods=["POST"])
def add_movie():
    data = request.get_json(silent=True) or {}
    required = ["name", "genre", "description", "rating", "image_dir"]
    missing = [k for k in required if k not in data]
    if missing:
        return jsonify({"error": f"Missing fields: {missing}"}), 400
    conn = get_db_connection()
    cur = conn.execute(
        "INSERT INTO movies (name, genre, description, rating, image_dir) VALUES (?, ?, ?, ?, ?)",
        (data["name"], data["genre"], data["description"], data["rating"], data["image_dir"]),
    )
    conn.commit()
    row = conn.execute("SELECT * FROM movies WHERE id = ?", (cur.lastrowid,)).fetchone()
    conn.close()
    return jsonify(dict(row)), 201
 
 
@app.route("/api/movies/<int:movie_id>", methods=["PUT"])
def update_movie(movie_id):
    data = request.get_json(silent=True) or {}
    conn = get_db_connection()
    row = conn.execute("SELECT * FROM movies WHERE id = ?", (movie_id,)).fetchone()
    if row is None:
        conn.close()
        return jsonify({"error": "Movie not found"}), 404
    updated = {**dict(row), **data}
    conn.execute(
        "UPDATE movies SET name=?, genre=?, description=?, rating=?, image_dir=? WHERE id=?",
        (updated["name"], updated["genre"], updated["description"],
         updated["rating"], updated["image_dir"], movie_id),
    )
    conn.commit()
    row = conn.execute("SELECT * FROM movies WHERE id = ?", (movie_id,)).fetchone()
    conn.close()
    return jsonify(dict(row))
 
 
@app.route("/api/movies/<int:movie_id>", methods=["DELETE"])
def delete_movie(movie_id):
    conn = get_db_connection()
    conn.execute("DELETE FROM movies WHERE id = ?", (movie_id,))
    conn.commit()
    conn.close()
    return jsonify({"message": f"Movie {movie_id} deleted"})
 
 
# ════════════════════════════════════════════════════════════════════════════
# MUSIC  –  full CRUD
# ════════════════════════════════════════════════════════════════════════════
 
@app.route("/api/music", methods=["GET"])
def get_music():
    conn = get_db_connection()
    rows = conn.execute("SELECT * FROM music").fetchall()
    conn.close()
    return jsonify([dict(r) for r in rows])
 
 
@app.route("/api/music/<int:music_id>", methods=["GET"])
def get_music_item(music_id):
    conn = get_db_connection()
    row = conn.execute("SELECT * FROM music WHERE id = ?", (music_id,)).fetchone()
    conn.close()
    if row is None:
        return jsonify({"error": "Music not found"}), 404
    return jsonify(dict(row))
 
 
@app.route("/api/music", methods=["POST"])
def add_music():
    data = request.get_json(silent=True) or {}
    required = ["name", "genre", "description", "rating", "image_dir"]
    missing = [k for k in required if k not in data]
    if missing:
        return jsonify({"error": f"Missing fields: {missing}"}), 400
    conn = get_db_connection()
    cur = conn.execute(
        "INSERT INTO music (name, genre, description, rating, image_dir) VALUES (?, ?, ?, ?, ?)",
        (data["name"], data["genre"], data["description"], data["rating"], data["image_dir"]),
    )
    conn.commit()
    row = conn.execute("SELECT * FROM music WHERE id = ?", (cur.lastrowid,)).fetchone()
    conn.close()
    return jsonify(dict(row)), 201
 
 
@app.route("/api/music/<int:music_id>", methods=["PUT"])
def update_music(music_id):
    data = request.get_json(silent=True) or {}
    conn = get_db_connection()
    row = conn.execute("SELECT * FROM music WHERE id = ?", (music_id,)).fetchone()
    if row is None:
        conn.close()
        return jsonify({"error": "Music not found"}), 404
    updated = {**dict(row), **data}
    conn.execute(
        "UPDATE music SET name=?, genre=?, description=?, rating=?, image_dir=? WHERE id=?",
        (updated["name"], updated["genre"], updated["description"],
         updated["rating"], updated["image_dir"], music_id),
    )
    conn.commit()
    row = conn.execute("SELECT * FROM music WHERE id = ?", (music_id,)).fetchone()
    conn.close()
    return jsonify(dict(row))
 
 
@app.route("/api/music/<int:music_id>", methods=["DELETE"])
def delete_music(music_id):
    conn = get_db_connection()
    conn.execute("DELETE FROM music WHERE id = ?", (music_id,))
    conn.commit()
    conn.close()
    return jsonify({"message": f"Music {music_id} deleted"})
 
 
# ── Entry point ─────────────────────────────────────────────────────────────
if __name__ == "__main__":
    init_db()
    print("✅  Database initialised.  Starting OlaMedia API on http://127.0.0.1:5000")
    app.run(debug=True, port=5000)
