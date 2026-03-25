from flask import Flask, jsonify, request
from flask_cors import CORS
from database import get_db_connection, init_db

app = Flask(__name__)
CORS(app)  # Allow cross-origin requests from the frontend


# ──────────────────────────────────────────────
# Health check
# ──────────────────────────────────────────────
@app.route("/api/health", methods=["GET"])
def health():
    return jsonify({"status": "ok", "message": "OlaMedia API is running"})


# ──────────────────────────────────────────────
# BOOKS
# ──────────────────────────────────────────────
@app.route("/api/books", methods=["GET"])
def get_books():
    conn = get_db_connection()
    books = conn.execute("SELECT * FROM books").fetchall()
    conn.close()
    return jsonify([dict(b) for b in books])


@app.route("/api/books/<int:book_id>", methods=["GET"])
def get_book(book_id):
    conn = get_db_connection()
    book = conn.execute("SELECT * FROM books WHERE id = ?", (book_id,)).fetchone()
    conn.close()
    if book is None:
        return jsonify({"error": "Book not found"}), 404
    return jsonify(dict(book))


@app.route("/api/books", methods=["POST"])
def add_book():
    data = request.get_json()
    required = ["name", "genre", "description", "rating", "image_dir"]
    if not all(k in data for k in required):
        return jsonify({"error": f"Missing fields. Required: {required}"}), 400
    conn = get_db_connection()
    cursor = conn.execute(
        "INSERT INTO books (name, genre, description, rating, image_dir) VALUES (?, ?, ?, ?, ?)",
        (data["name"], data["genre"], data["description"], data["rating"], data["image_dir"]),
    )
    conn.commit()
    new_id = cursor.lastrowid
    book = conn.execute("SELECT * FROM books WHERE id = ?", (new_id,)).fetchone()
    conn.close()
    return jsonify(dict(book)), 201


@app.route("/api/books/<int:book_id>", methods=["PUT"])
def update_book(book_id):
    data = request.get_json()
    conn = get_db_connection()
    book = conn.execute("SELECT * FROM books WHERE id = ?", (book_id,)).fetchone()
    if book is None:
        conn.close()
        return jsonify({"error": "Book not found"}), 404
    updated = {**dict(book), **data}
    conn.execute(
        "UPDATE books SET name=?, genre=?, description=?, rating=?, image_dir=? WHERE id=?",
        (updated["name"], updated["genre"], updated["description"], updated["rating"], updated["image_dir"], book_id),
    )
    conn.commit()
    book = conn.execute("SELECT * FROM books WHERE id = ?", (book_id,)).fetchone()
    conn.close()
    return jsonify(dict(book))


@app.route("/api/books/<int:book_id>", methods=["DELETE"])
def delete_book(book_id):
    conn = get_db_connection()
    conn.execute("DELETE FROM books WHERE id = ?", (book_id,))
    conn.commit()
    conn.close()
    return jsonify({"message": f"Book {book_id} deleted"})


# ──────────────────────────────────────────────
# MOVIES
# ──────────────────────────────────────────────
@app.route("/api/movies", methods=["GET"])
def get_movies():
    conn = get_db_connection()
    movies = conn.execute("SELECT * FROM movies").fetchall()
    conn.close()
    return jsonify([dict(m) for m in movies])


@app.route("/api/movies/<int:movie_id>", methods=["GET"])
def get_movie(movie_id):
    conn = get_db_connection()
    movie = conn.execute("SELECT * FROM movies WHERE id = ?", (movie_id,)).fetchone()
    conn.close()
    if movie is None:
        return jsonify({"error": "Movie not found"}), 404
    return jsonify(dict(movie))


@app.route("/api/movies", methods=["POST"])
def add_movie():
    data = request.get_json()
    required = ["name", "genre", "description", "rating", "image_dir"]
    if not all(k in data for k in required):
        return jsonify({"error": f"Missing fields. Required: {required}"}), 400
    conn = get_db_connection()
    cursor = conn.execute(
        "INSERT INTO movies (name, genre, description, rating, image_dir) VALUES (?, ?, ?, ?, ?)",
        (data["name"], data["genre"], data["description"], data["rating"], data["image_dir"]),
    )
    conn.commit()
    new_id = cursor.lastrowid
    movie = conn.execute("SELECT * FROM movies WHERE id = ?", (new_id,)).fetchone()
    conn.close()
    return jsonify(dict(movie)), 201


@app.route("/api/movies/<int:movie_id>", methods=["PUT"])
def update_movie(movie_id):
    data = request.get_json()
    conn = get_db_connection()
    movie = conn.execute("SELECT * FROM movies WHERE id = ?", (movie_id,)).fetchone()
    if movie is None:
        conn.close()
        return jsonify({"error": "Movie not found"}), 404
    updated = {**dict(movie), **data}
    conn.execute(
        "UPDATE movies SET name=?, genre=?, description=?, rating=?, image_dir=? WHERE id=?",
        (updated["name"], updated["genre"], updated["description"], updated["rating"], updated["image_dir"], movie_id),
    )
    conn.commit()
    movie = conn.execute("SELECT * FROM movies WHERE id = ?", (movie_id,)).fetchone()
    conn.close()
    return jsonify(dict(movie))


@app.route("/api/movies/<int:movie_id>", methods=["DELETE"])
def delete_movie(movie_id):
    conn = get_db_connection()
    conn.execute("DELETE FROM movies WHERE id = ?", (movie_id,))
    conn.commit()
    conn.close()
    return jsonify({"message": f"Movie {movie_id} deleted"})


# ──────────────────────────────────────────────
# MUSIC
# ──────────────────────────────────────────────
@app.route("/api/music", methods=["GET"])
def get_music():
    conn = get_db_connection()
    music = conn.execute("SELECT * FROM music").fetchall()
    conn.close()
    return jsonify([dict(m) for m in music])


@app.route("/api/music/<int:music_id>", methods=["GET"])
def get_music_item(music_id):
    conn = get_db_connection()
    item = conn.execute("SELECT * FROM music WHERE id = ?", (music_id,)).fetchone()
    conn.close()
    if item is None:
        return jsonify({"error": "Music not found"}), 404
    return jsonify(dict(item))


@app.route("/api/music", methods=["POST"])
def add_music():
    data = request.get_json()
    required = ["name", "genre", "description", "rating", "image_dir"]
    if not all(k in data for k in required):
        return jsonify({"error": f"Missing fields. Required: {required}"}), 400
    conn = get_db_connection()
    cursor = conn.execute(
        "INSERT INTO music (name, genre, description, rating, image_dir) VALUES (?, ?, ?, ?, ?)",
        (data["name"], data["genre"], data["description"], data["rating"], data["image_dir"]),
    )
    conn.commit()
    new_id = cursor.lastrowid
    item = conn.execute("SELECT * FROM music WHERE id = ?", (new_id,)).fetchone()
    conn.close()
    return jsonify(dict(item)), 201


@app.route("/api/music/<int:music_id>", methods=["PUT"])
def update_music(music_id):
    data = request.get_json()
    conn = get_db_connection()
    item = conn.execute("SELECT * FROM music WHERE id = ?", (music_id,)).fetchone()
    if item is None:
        conn.close()
        return jsonify({"error": "Music not found"}), 404
    updated = {**dict(item), **data}
    conn.execute(
        "UPDATE music SET name=?, genre=?, description=?, rating=?, image_dir=? WHERE id=?",
        (updated["name"], updated["genre"], updated["description"], updated["rating"], updated["image_dir"], music_id),
    )
    conn.commit()
    item = conn.execute("SELECT * FROM music WHERE id = ?", (music_id,)).fetchone()
    conn.close()
    return jsonify(dict(item))


@app.route("/api/music/<int:music_id>", methods=["DELETE"])
def delete_music(music_id):
    conn = get_db_connection()
    conn.execute("DELETE FROM music WHERE id = ?", (music_id,))
    conn.commit()
    conn.close()
    return jsonify({"message": f"Music {music_id} deleted"})


# ──────────────────────────────────────────────
# Entry point
# ──────────────────────────────────────────────
if __name__ == "__main__":
    init_db()
    print("✅ Database initialised. Starting OlaMedia API…")
    app.run(debug=True, port=5000)
