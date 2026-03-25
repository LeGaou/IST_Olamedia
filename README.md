# OlaMedia – Backend & Database

Python · Flask · SQLite backend for the OlaMedia AI-powered media recommendation system.

---

## Project Structure

```
olamedia/
├── app.py            # Flask application & all API routes
├── database.py       # SQLite schema, seed data, and DB helpers
├── olamedia.db       # Auto-generated SQLite database (git-ignored)
├── requirements.txt  # Python dependencies
├── static/
│   └── images/
│       ├── books/    # Book cover images go here
│       ├── movies/   # Movie poster images go here
│       └── music/    # Album art images go here
└── README.md
```

---

## Quick Start

### 1 – Create and activate a virtual environment
```bash
python -m venv venv
# macOS / Linux
source venv/bin/activate
# Windows
venv\Scripts\activate
```

### 2 – Install dependencies
```bash
pip install -r requirements.txt
```

### 3 – Run the server
```bash
python app.py
```

The API will start on **http://127.0.0.1:5000**.  
On first launch, `olamedia.db` is created automatically with 10 placeholder items in each table.

---

## Database Schema

All three tables share the same column structure:

| Column       | Type    | Description                            |
|--------------|---------|----------------------------------------|
| `id`         | INTEGER | Auto-incrementing primary key          |
| `name`       | TEXT    | Title of the media item                |
| `genre`      | TEXT    | Genre / category                       |
| `description`| TEXT    | Short descriptive blurb                |
| `rating`     | REAL    | Score 0–10                             |
| `image_dir`  | TEXT    | Relative path to the cover image       |
| `created_at` | DATETIME| Auto-set on insert                     |

Tables: **books**, **movies**, **music**

---

## API Endpoints

Base URL: `http://127.0.0.1:5000/api`

### Health
| Method | Endpoint      | Description        |
|--------|---------------|--------------------|
| GET    | `/health`     | Server health check|

### Books
| Method | Endpoint        | Description          |
|--------|-----------------|----------------------|
| GET    | `/books`        | List all books       |
| GET    | `/books/<id>`   | Get a single book    |
| POST   | `/books`        | Add a new book       |
| PUT    | `/books/<id>`   | Update a book        |
| DELETE | `/books/<id>`   | Delete a book        |

### Movies
| Method | Endpoint        | Description          |
|--------|-----------------|----------------------|
| GET    | `/movies`       | List all movies      |
| GET    | `/movies/<id>`  | Get a single movie   |
| POST   | `/movies`       | Add a new movie      |
| PUT    | `/movies/<id>`  | Update a movie       |
| DELETE | `/movies/<id>`  | Delete a movie       |

### Music
| Method | Endpoint        | Description          |
|--------|-----------------|----------------------|
| GET    | `/music`        | List all music       |
| GET    | `/music/<id>`   | Get a single item    |
| POST   | `/music`        | Add a new item       |
| PUT    | `/music/<id>`   | Update an item       |
| DELETE | `/music/<id>`   | Delete an item       |

### POST / PUT Request Body (JSON)
```json
{
  "name": "Title",
  "genre": "Genre",
  "description": "Short description.",
  "rating": 8.5,
  "image_dir": "static/images/books/cover.jpg"
}
```

---

## Connecting the Frontend

All endpoints return JSON and accept CORS requests from any origin during development.  
Point your Gemini-built frontend fetch calls at `http://127.0.0.1:5000/api/`.

Example (JavaScript):
```js
const res = await fetch("http://127.0.0.1:5000/api/books");
const books = await res.json();
```

---

## Adding Real Images

Place image files inside the matching `static/images/` sub-folder and update `image_dir` in the database (or seed data) to match the filename.

---

## Next Steps (for the team)

- **Kimi AI / Flask team** – wire Ollama recommendation calls into new `/api/recommend` routes
- **Frontend / Gemini team** – consume `/api/books`, `/api/movies`, `/api/music` to render cards
- **AI / Ollama team** – add `/api/reviews` table and sentiment-analysis endpoint
