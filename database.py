"""
database.py – OlaMedia SQLite database layer
Handles schema creation, migrations, and seed data for Books, Movies, Music,
and the shared user_ratings table.
"""
 
import sqlite3
import os
 
DB_PATH = os.path.join(os.path.dirname(__file__), "olamedia.db")
 
 
def get_db_connection():
    """Return a connection with row_factory so rows behave like dicts."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn
 
 
def init_db():
    """Create / migrate tables and seed placeholder data."""
    conn = get_db_connection()
    _create_tables(conn)
    _migrate(conn)
    _seed_data(conn)
    conn.close()
 
 
# ──────────────────────────────────────────────
# Schema
# ──────────────────────────────────────────────
def _create_tables(conn):
    conn.executescript("""
        -- ── Media tables ──────────────────────────────────────────────────
        CREATE TABLE IF NOT EXISTS books (
            id                  INTEGER PRIMARY KEY AUTOINCREMENT,
            name                TEXT    NOT NULL,
            genre               TEXT    NOT NULL,
            description         TEXT    NOT NULL,
            rating              REAL    NOT NULL CHECK(rating >= 0 AND rating <= 10),
            image_dir           TEXT    NOT NULL,
            user_rating_avg     REAL    DEFAULT NULL,
            user_rating_count   INTEGER DEFAULT 0,
            created_at          DATETIME DEFAULT CURRENT_TIMESTAMP
        );
 
        CREATE TABLE IF NOT EXISTS movies (
            id                  INTEGER PRIMARY KEY AUTOINCREMENT,
            name                TEXT    NOT NULL,
            genre               TEXT    NOT NULL,
            description         TEXT    NOT NULL,
            rating              REAL    NOT NULL CHECK(rating >= 0 AND rating <= 10),
            image_dir           TEXT    NOT NULL,
            user_rating_avg     REAL    DEFAULT NULL,
            user_rating_count   INTEGER DEFAULT 0,
            created_at          DATETIME DEFAULT CURRENT_TIMESTAMP
        );
 
        CREATE TABLE IF NOT EXISTS music (
            id                  INTEGER PRIMARY KEY AUTOINCREMENT,
            name                TEXT    NOT NULL,
            genre               TEXT    NOT NULL,
            description         TEXT    NOT NULL,
            rating              REAL    NOT NULL CHECK(rating >= 0 AND rating <= 10),
            image_dir           TEXT    NOT NULL,
            user_rating_avg     REAL    DEFAULT NULL,
            user_rating_count   INTEGER DEFAULT 0,
            created_at          DATETIME DEFAULT CURRENT_TIMESTAMP
        );
 
        -- ── User ratings log ───────────────────────────────────────────────
        -- Stores every individual rating event.
        -- media_type : 'book' | 'movie' | 'music'
        -- user_id    : session token / fingerprint; defaults to 'anonymous'
        --              until a real auth system is wired in.
        -- UNIQUE constraint means a user can only rate an item once;
        -- submitting again updates (upserts) their existing score.
        CREATE TABLE IF NOT EXISTS user_ratings (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            media_type  TEXT    NOT NULL CHECK(media_type IN ('book','movie','music')),
            media_id    INTEGER NOT NULL,
            user_id     TEXT    NOT NULL DEFAULT 'anonymous',
            score       REAL    NOT NULL CHECK(score >= 0 AND score <= 10),
            rated_at    DATETIME DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(media_type, media_id, user_id)
        );
    """)
    conn.commit()
 
 
# ──────────────────────────────────────────────
# Migration  (adds new columns to existing DBs)
# ──────────────────────────────────────────────
def _migrate(conn):
    """
    Safely add user_rating_avg / user_rating_count to tables that existed
    before this version.  SQLite ALTER TABLE only supports ADD COLUMN, so
    we check the column list before attempting.
    """
    for table in ("books", "movies", "music"):
        existing_cols = {row[1] for row in conn.execute(f"PRAGMA table_info({table})")}
        if "user_rating_avg" not in existing_cols:
            conn.execute(
                f"ALTER TABLE {table} ADD COLUMN user_rating_avg REAL DEFAULT NULL"
            )
        if "user_rating_count" not in existing_cols:
            conn.execute(
                f"ALTER TABLE {table} ADD COLUMN user_rating_count INTEGER DEFAULT 0"
            )
    conn.commit()
 
 
# ──────────────────────────────────────────────
# Helper used by Flask routes
# ──────────────────────────────────────────────
def recalculate_avg(conn, media_type: str, media_id: int):
    """
    Recompute rolling average and vote count from user_ratings, then write
    the result back to the media row.  Call this after every INSERT / UPDATE
    / DELETE on user_ratings so media tables always stay in sync.
    """
    table_map = {"book": "books", "movie": "movies", "music": "music"}
    table = table_map[media_type]
 
    row = conn.execute(
        """
        SELECT COUNT(*) AS cnt, AVG(score) AS avg
        FROM   user_ratings
        WHERE  media_type = ? AND media_id = ?
        """,
        (media_type, media_id),
    ).fetchone()
 
    cnt = row["cnt"] or 0
    avg = round(row["avg"], 2) if row["avg"] is not None else None
 
    conn.execute(
        f"UPDATE {table} SET user_rating_avg = ?, user_rating_count = ? WHERE id = ?",
        (avg, cnt, media_id),
    )
    conn.commit()
 
 
# ──────────────────────────────────────────────
# Seed data  (10 placeholder items per table)
# ──────────────────────────────────────────────
BOOKS_SEED = [
    ("The Great Gatsby",                     "Classic Fiction",         "A story of wealth, obsession, and the American Dream set in the roaring 1920s, following the mysterious Jay Gatsby and his pursuit of Daisy Buchanan.",                                          8.5, "static/images/books/great_gatsby.jpg"),
    ("To Kill a Mockingbird",                "Drama",                   "Harper Lee's Pulitzer Prize-winning novel set in the American South, exploring racial injustice and moral growth through the eyes of young Scout Finch.",                                         9.2, "static/images/books/mockingbird.jpg"),
    ("1984",                                 "Dystopian Fiction",       "George Orwell's chilling vision of a totalitarian future where Big Brother watches every move and independent thought is a crime punishable by death.",                                           9.0, "static/images/books/1984.jpg"),
    ("Dune",                                 "Science Fiction",         "Frank Herbert's epic saga of desert planets, giant sandworms, and political intrigue as young Paul Atreides navigates a universe of power and prophecy.",                                         8.8, "static/images/books/dune.jpg"),
    ("Pride and Prejudice",                  "Romance",                 "Jane Austen's beloved novel following the witty Elizabeth Bennet as she navigates love, class, and society while sparring with the proud Mr. Darcy.",                                            8.7, "static/images/books/pride_prejudice.jpg"),
    ("The Hitchhiker's Guide to the Galaxy", "Comedy Sci-Fi",           "Douglas Adams' absurdist comic masterpiece in which Arthur Dent is whisked across the universe after Earth is demolished to make way for a hyperspace bypass.",                                  8.9, "static/images/books/hitchhikers_guide.jpg"),
    ("Sapiens",                              "Non-Fiction",             "Yuval Noah Harari's sweeping history of humankind, tracing the cognitive, agricultural, and scientific revolutions that shaped our species.",                                                    9.1, "static/images/books/sapiens.jpg"),
    ("The Alchemist",                        "Adventure",               "Paulo Coelho's philosophical novel about a young Andalusian shepherd who travels from Spain to Egypt following his personal legend in search of treasure.",                                       8.3, "static/images/books/alchemist.jpg"),
    ("Atomic Habits",                        "Self-Help",               "James Clear's practical guide to building good habits and breaking bad ones using small, incremental changes that compound into remarkable results over time.",                                    8.6, "static/images/books/atomic_habits.jpg"),
    ("The Name of the Wind",                 "Fantasy",                 "Patrick Rothfuss's debut novel recounts the legendary life of Kvothe — musician, arcanist, and thief — through his own captivating first-person account.",                                     9.0, "static/images/books/name_of_wind.jpg"),
]
 
MOVIES_SEED = [
    ("Inception",                            "Sci-Fi Thriller",         "Christopher Nolan's mind-bending heist film in which a thief enters people's dreams to plant an idea, blurring the line between reality and imagination.",                                      8.8, "static/images/movies/inception.jpg"),
    ("The Shawshank Redemption",             "Drama",                   "Two imprisoned men bond over years in a Maine prison, finding solace and eventual redemption through acts of common decency in an indecent time.",                                               9.3, "static/images/movies/shawshank.jpg"),
    ("Interstellar",                         "Sci-Fi Adventure",        "A team of explorers travel through a wormhole in space in an attempt to ensure humanity's survival as Earth becomes increasingly uninhabitable.",                                                8.6, "static/images/movies/interstellar.jpg"),
    ("Parasite",                             "Thriller Drama",          "Bong Joon-ho's Academy Award-winning film about class struggle and deception as the impoverished Kim family schemes their way into a wealthy household.",                                        8.5, "static/images/movies/parasite.jpg"),
    ("The Dark Knight",                      "Action Superhero",        "Batman faces the Joker, a criminal mastermind who unleashes chaos on Gotham City in this acclaimed superhero film featuring Heath Ledger's iconic performance.",                                 9.0, "static/images/movies/dark_knight.jpg"),
    ("Spirited Away",                        "Animated Fantasy",        "Studio Ghibli's masterpiece follows ten-year-old Chihiro, trapped in a mysterious spirit world, as she works to rescue her transformed parents and find a way home.",                           8.9, "static/images/movies/spirited_away.jpg"),
    ("Pulp Fiction",                         "Crime",                   "Quentin Tarantino's non-linear crime anthology weaves together the stories of two hitmen, a boxer, and a mob boss's wife through darkly comic vignettes.",                                      8.7, "static/images/movies/pulp_fiction.jpg"),
    ("The Lion King",                        "Animated Drama",          "A young lion prince flees his kingdom after the murder of his father, only to learn the true meaning of responsibility and courage when his homeland needs him most.",                           8.4, "static/images/movies/lion_king.jpg"),
    ("Schindler's List",                     "Historical Drama",        "Steven Spielberg's profound film depicting German industrialist Oskar Schindler's efforts to save Jewish refugees during the Holocaust by employing them in his factory.",                      9.1, "static/images/movies/schindlers_list.jpg"),
    ("Everything Everywhere All at Once",    "Sci-Fi Comedy",           "A Chinese-American laundromat owner must connect with parallel universe versions of herself to prevent a powerful villain from destroying the multiverse.",                                      8.0, "static/images/movies/eeaao.jpg"),
]
 
MUSIC_SEED = [
    ("Thriller – Michael Jackson",           "Pop / R&B",               "The best-selling album of all time, featuring iconic tracks produced by Quincy Jones that blended pop, rock, and funk into an unforgettable sonic experience.",                                 9.5, "static/images/music/thriller.jpg"),
    ("Dark Side of the Moon – Pink Floyd",   "Progressive Rock",        "Pink Floyd's landmark concept album exploring themes of conflict, greed, time, and mental illness through innovative studio techniques and atmospheric soundscapes.",                            9.4, "static/images/music/dark_side.jpg"),
    ("Lemonade – Beyoncé",                   "R&B / Soul",              "Beyoncé's visual album and cultural statement weaving infidelity, Black womanhood, and resilience through a genre-spanning collection of powerful tracks.",                                     9.0, "static/images/music/lemonade.jpg"),
    ("To Pimp a Butterfly – Kendrick Lamar", "Hip-Hop",                 "Kendrick Lamar's politically charged masterpiece blending jazz, funk, and spoken word to explore race, identity, and the African-American experience.",                                         9.3, "static/images/music/tpab.jpg"),
    ("21 – Adele",                           "Soul / Pop",              "Adele's Grammy-sweeping sophomore album delivers raw, heartfelt ballads about heartbreak and self-discovery, showcasing her powerhouse vocal range.",                                            8.8, "static/images/music/adele_21.jpg"),
    ("Abbey Road – The Beatles",             "Rock",                    "The Beatles' penultimate studio album featuring the legendary medley side, innovative recording techniques, and timeless songs that defined an era.",                                            9.6, "static/images/music/abbey_road.jpg"),
    ("Folklore – Taylor Swift",              "Indie Folk / Alternative", "Taylor Swift's surprise lockdown album strips back her pop sound for introspective storytelling, intimate production, and critically acclaimed songwriting.",                                   8.9, "static/images/music/folklore.jpg"),
    ("Random Access Memories – Daft Punk",   "Electronic / Disco",      "Daft Punk's love letter to 1970s Californian music, recorded live with legendary session musicians and featuring the global hit 'Get Lucky'.",                                                 9.1, "static/images/music/ram.jpg"),
    ("Afrobeats Legends – Fela Kuti",        "Afrobeat",                "A curated collection of Fela Kuti's most powerful recordings, blending jazz, funk, and West African rhythms with sharp political commentary.",                                                  9.2, "static/images/music/fela_kuti.jpg"),
    ("The Miseducation of Lauryn Hill",      "R&B / Hip-Hop",           "Lauryn Hill's debut solo album fuses hip-hop, soul, and reggae into a deeply personal narrative about love, spirituality, and empowerment.",                                                   9.4, "static/images/music/miseducation.jpg"),
]
 
 
def _seed_data(conn):
    """Insert seed rows only when tables are empty (idempotent)."""
    if conn.execute("SELECT COUNT(*) FROM books").fetchone()[0] == 0:
        conn.executemany(
            "INSERT INTO books (name, genre, description, rating, image_dir) VALUES (?, ?, ?, ?, ?)",
            BOOKS_SEED,
        )
    if conn.execute("SELECT COUNT(*) FROM movies").fetchone()[0] == 0:
        conn.executemany(
            "INSERT INTO movies (name, genre, description, rating, image_dir) VALUES (?, ?, ?, ?, ?)",
            MOVIES_SEED,
        )
    if conn.execute("SELECT COUNT(*) FROM music").fetchone()[0] == 0:
        conn.executemany(
            "INSERT INTO music (name, genre, description, rating, image_dir) VALUES (?, ?, ?, ?, ?)",
            MUSIC_SEED,
        )
    conn.commit()
 
