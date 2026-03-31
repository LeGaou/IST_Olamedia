from flask import Flask, jsonify, request
from flask_cors import CORS
from database import get_db_connection, init_db, recalculate_avg
import ollama
cache = {}
# ─── AI SERVICE ───────────────────────────────

class AIService:
    def get_recommendations(self, preferences, media_type, rated_text):

        if rated_text != "None":
            prompt = f"""
Recommend exactly 3 {media_type}.

User preference: {preferences}

User liked these:
{rated_text}

Rules:
- Recommend similar items
- DO NOT include any of the liked items above
- ONLY return a numbered list
- Each line must follow this EXACT format:

1. Movie Name - because it is similar to [rated item or preference]

No extra text.
"""
        else:
            prompt = f"""
Recommend exactly 3 {media_type}.

User preference: {preferences}

Rules:
- ONLY return a numbered list
- Each line must follow this EXACT format:

1. Movie Name - because you like {preferences}

No extra text.
"""

        response = ollama.chat(
            model="llama3:8b",
            messages=[{'role': 'user', 'content': prompt}],
            options={"num_predict": 150, "temperature": 0.2}
        )

        return response['message']['content']

ai = AIService()

# ─── APP SETUP ───────────────────────────────

app = Flask(__name__)
CORS(app)

VALID_MEDIA_TYPES = {"book", "movie", "music"}
MEDIA_TABLE_MAP = {"book": "books", "movie": "movies", "music": "music"}

def _validate_score(score):
    try:
        score = float(score)
    except:
        return None, "score must be a number"
    if not (0 <= score <= 10):
        return None, "score must be between 0 and 10"
    return score, None

# ─── HEALTH ───────────────────────────────

@app.route("/api/health")
def health():
    return jsonify({"status": "ok"})

# ─── RECOMMEND ───────────────────────────────

@app.route('/api/recommend', methods=['POST'])
def recommend():
    import re

    data = request.json
    preferences = data.get("preferences", "")
    media_type = data.get("type", "movies")
    user_id = data.get("user_id", "john")

    conn = get_db_connection()

    rows = conn.execute("""
        SELECT media_type, media_id, score
        FROM user_ratings
        WHERE user_id = ? AND score >= 7
    """, (user_id,)).fetchall()

    rated_items = []

    for r in rows:
        table = MEDIA_TABLE_MAP[r["media_type"]]
        item = conn.execute(
            f"SELECT name FROM {table} WHERE id=?",
            (r["media_id"],)
        ).fetchone()

        if item:
            rated_items.append(f"{item['name']} ({r['score']}/10)")

    conn.close()

    rated_text = "\n".join(rated_items)
    has_ratings = len(rated_items) > 0

    key = f"{preferences}-{media_type}-{rated_text}"

    # ⚡ CACHE CHECK
    if key in cache:
        return jsonify({
            "success": True,
            "data": cache[key]
        })

    # 🔥 CALL AI
    result = ai.get_recommendations(
        preferences,
        media_type,
        rated_text if has_ratings else "None"
    )


    # 🧼 CLEAN OUTPUT (ROBUST)
    lines = [l.strip() for l in result.split("\n") if l.strip()]
    cleaned = []
    seen = set()

    for line in lines:
        # remove numbering ONLY if at start (safe)
        match = re.match(r"^\d+\.\s*(.*)", line)
        if match:
            line = match.group(1)

        # ❌ skip garbage / intro lines
        if any(x in line.lower() for x in ["here are", "recommendations", "these are"]):
            continue

        # split into name + reason
        parts = line.split(" - ", 1)
        name = parts[0].strip()
        reason = parts[1].strip() if len(parts) > 1 else f"because you like {preferences}"

        if not name:
            continue

        # avoid duplicates
        if name.lower() in seen:
            continue

        seen.add(name.lower())
        cleaned.append(f"{len(cleaned)+1}. {name} - {reason}")

        if len(cleaned) == 3:
            break

    # ⚠️ fallback if AI output was trash
    if not cleaned:
        cleaned = [
            f"1. No recommendations found - try a different preference",
            f"2. No recommendations found - try a different preference",
            f"3. No recommendations found - try a different preference"
        ]

    result = "\n".join(cleaned)

    # 💾 SAVE TO CACHE
    cache[key] = result

    return jsonify({
        "success": True,
        "data": result
    })

# ─── RATINGS ───────────────────────────────

@app.route("/api/ratings", methods=["POST"])
def submit_rating():
    data = request.get_json() or {}

    media_type = data.get("media_type", "").lower()
    if media_type not in VALID_MEDIA_TYPES:
        return jsonify({"error": "invalid media_type"}), 400

    media_id = int(data.get("media_id"))
    score, err = _validate_score(data.get("score"))
    if err:
        return jsonify({"error": err}), 400

    user_id = data.get("user_id", "anonymous")

    conn = get_db_connection()
    table = MEDIA_TABLE_MAP[media_type]

    item = conn.execute(f"SELECT id FROM {table} WHERE id=?", (media_id,)).fetchone()
    if not item:
        conn.close()
        return jsonify({"error": "not found"}), 404

    conn.execute("""
    INSERT INTO user_ratings (media_type, media_id, user_id, score, rated_at)
    VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
    ON CONFLICT(media_type, media_id, user_id)
    DO UPDATE SET score=excluded.score
    """, (media_type, media_id, user_id, score))

    conn.commit()
    recalculate_avg(conn, media_type, media_id)

    updated = conn.execute(f"SELECT * FROM {table} WHERE id=?", (media_id,)).fetchone()
    conn.close()

    return jsonify({
        "message": "Rating saved",
        "media_item": dict(updated)
    })

@app.route("/api/ratings/<media_type>/<int:media_id>/<user_id>", methods=["DELETE"])
def delete_rating(media_type, media_id, user_id):
    if media_type not in VALID_MEDIA_TYPES:
        return jsonify({"error": "invalid media_type"}), 400

    conn = get_db_connection()

    conn.execute("""
        DELETE FROM user_ratings
        WHERE media_type = ? AND media_id = ? AND user_id = ?
    """, (media_type, media_id, user_id))

    conn.commit()
    conn.close()

    return jsonify({"success": True})

# ─── BASIC CRUD (SHORT VERSION) ───────────────────────────────

@app.route("/api/movies")
def get_movies():
    conn = get_db_connection()
    rows = conn.execute("SELECT * FROM movies").fetchall()
    conn.close()

    print("MOVIES:", rows)  # 👈 ADD THIS

    return jsonify([dict(r) for r in rows])
    
@app.route("/api/books")
def get_books():
    conn = get_db_connection()
    rows = conn.execute("SELECT * FROM books").fetchall()
    conn.close()
    return jsonify([dict(r) for r in rows])

@app.route("/api/music")
def get_music():
    conn = get_db_connection()
    rows = conn.execute("SELECT * FROM music").fetchall()
    conn.close()
    return jsonify([dict(r) for r in rows])

@app.route("/api/user_ratings")
def get_user_ratings():
    user_id = request.args.get("user_id", "john")

    conn = get_db_connection()

    rows = conn.execute("""
        SELECT media_type, media_id, score
        FROM user_ratings
        WHERE user_id = ?
    """, (user_id,)).fetchall()

    results = []

    for r in rows:
        table = {
            "movie": "movies",
            "book": "books",
            "music": "music"
        }[r["media_type"]]

        item = conn.execute(
            f"SELECT name FROM {table} WHERE id=?",
            (r["media_id"],)
        ).fetchone()

        results.append({
            "name": item["name"] if item else "Unknown",
            "type": r["media_type"],
            "score": r["score"],
            "media_id": r["media_id"]
        })

    conn.close()

    return jsonify(results)

# ─── ENTRY ───────────────────────────────

if __name__ == "__main__":
    init_db()
    print("✅ Server running on http://127.0.0.1:5000")
    app.run(debug=True)