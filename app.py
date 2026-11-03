import os
import random
import sqlite3
from flask import Flask, request, session, redirect, url_for, jsonify, render_template_string, g

app = Flask(__name__)
app.secret_key = "music_trainer_secret_key_change_me"
DB_PATH = os.path.join(os.path.dirname(__file__), "music.db")

# ============================================================
# БАЗА ДАННЫХ
# ============================================================
def get_db():
    if "db" not in g:
        g.db = sqlite3.connect(DB_PATH)
        g.db.row_factory = sqlite3.Row
    return g.db

@app.teardown_appcontext
def close_db(exc):
    db = g.pop("db", None)
    if db is not None:
        db.close()

def init_db():
    db = sqlite3.connect(DB_PATH)
    db.executescript("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL
    );
    CREATE TABLE IF NOT EXISTS stats (
        user_id INTEGER PRIMARY KEY,
        correct INTEGER DEFAULT 0,
        wrong INTEGER DEFAULT 0
    );
    CREATE TABLE IF NOT EXISTS wrong_tasks (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        task_key TEXT,
        category TEXT,
        question TEXT,
        answer TEXT,
        UNIQUE(user_id, task_key)
    );
    CREATE TABLE IF NOT EXISTS favorites (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        task_key TEXT,
        category TEXT,
        question TEXT,
        answer TEXT,
        UNIQUE(user_id, task_key)
    );
    """)
    db.commit()
    db.close()

init_db()

# ============================================================
# МУЗЫКАЛЬНЫЕ ДАННЫЕ
# ============================================================
NOTES = ["до", "до#", "ре", "ре#", "ми", "фа", "фа#", "соль", "соль#", "ля", "ля#", "си"]
NOTES_FLAT = ["до", "ре♭", "ре", "ми♭", "ми", "фа", "соль♭", "соль", "ля♭", "ля", "си♭", "си"]
ALL_NOTES = ["до","до#","ре♭","ре","ре#","ми♭","ми","фа","фа#","соль♭","соль","соль#","ля♭","ля","ля#","си♭","си"]

# Интервалы (полутоны и названия)
INTERVALS = [
    ("ч1", 0, "чистая прима"),
    ("м2", 1, "малая секунда"),
    ("б2", 2, "большая секунда"),
    ("м3", 3, "малая терция"),
    ("б3", 4, "большая терция"),
    ("ч4", 5, "чистая кварта"),
    ("ум4", 6, "увеличенная кварта / тритон"),
    ("ч5", 7, "чистая квинта"),
    ("м6", 8, "малая секста"),
    ("б6", 9, "большая секста"),
    ("м7", 10, "малая септима"),
    ("б7", 11, "большая септима"),
    ("ч8", 12, "чистая октава"),
]

# Тональности: (название, знаков, тип, параллельная)
KEYS = [
    # мажор
    ("до мажор", 0, "мажор", "ля минор"),
    ("соль мажор", 1, "мажор", "ми минор"),
    ("ре мажор", 2, "мажор", "си минор"),
    ("ля мажор", 3, "мажор", "фа# минор"),
    ("ми мажор", 4, "мажор", "до# минор"),
    ("си мажор", 5, "мажор", "соль# минор"),
    ("фа# мажор", 6, "мажор", "ре# минор"),
    ("до# мажор", 7, "мажор", "ля# минор"),
    ("фа мажор", -1, "мажор", "ре минор"),
    ("си♭ мажор", -2, "мажор", "соль минор"),
    ("ми♭ мажор", -3, "мажор", "до минор"),
    ("ля♭ мажор", -4, "мажор", "фа минор"),
    ("ре♭ мажор", -5, "мажор", "си♭ минор"),
    ("соль♭ мажор", -6, "мажор", "ми♭ минор"),
    # минор
    ("ля минор", 0, "минор", "до мажор"),
    ("ми минор", 1, "минор", "соль мажор"),
    ("си минор", 2, "минор", "ре мажор"),
    ("фа# минор", 3, "минор", "ля мажор"),
    ("до# минор", 4, "минор", "ми мажор"),
    ("соль# минор", 5, "минор", "си мажор"),
    ("ре# минор", 6, "минор", "фа# мажор"),
    ("ля# минор", 7, "минор", "до# мажор"),
    ("ре минор", -1, "минор", "фа мажор"),
    ("соль минор", -2, "минор", "си♭ мажор"),
    ("до минор", -3, "минор", "ми♭ мажор"),
    ("фа минор", -4, "минор", "ля♭ мажор"),
    ("си♭ минор", -5, "минор", "ре♭ мажор"),
    ("ми♭ минор", -6, "минор", "соль♭ мажор"),
]

SHARP_ORDER = ["фа", "до", "соль", "ре", "ля", "ми", "си"]
FLAT_ORDER = ["си", "ми", "ля", "ре", "соль", "до", "фа"]

CHORDS_TRIADS = [
    ("до мажор", ["до", "ми", "соль"], "трезвучие мажор"),
    ("ре мажор", ["ре", "фа#", "ля"], "трезвучие мажор"),
    ("ми мажор", ["ми", "соль#", "си"], "трезвучие мажор"),
    ("фа мажор", ["фа", "ля", "до"], "трезвучие мажор"),
    ("соль мажор", ["соль", "си", "ре"], "трезвучие мажор"),
    ("ля мажор", ["ля", "до#", "ми"], "трезвучие мажор"),
    ("си♭ мажор", ["си♭", "ре", "фа"], "трезвучие мажор"),
    ("ля минор", ["ля", "до", "ми"], "трезвучие минор"),
    ("ми минор", ["ми", "соль", "си"], "трезвучие минор"),
    ("си минор", ["си", "ре", "фа#"], "трезвучие минор"),
    ("ре минор", ["ре", "фа", "ля"], "трезвучие минор"),
    ("соль минор", ["соль", "си♭", "ре"], "трезвучие минор"),
    ("до минор", ["до", "ми♭", "соль"], "трезвучие минор"),
    ("фа минор", ["фа", "ля♭", "до"], "трезвучие минор"),
    ("до увеличенный", ["до", "ми", "соль#"], "трезвучие увеличенный"),
    ("ре увеличенный", ["ре", "фа#", "ля#"], "трезвучие увеличенный"),
    ("ми увеличенный", ["ми", "соль#", "си#"], "трезвучие увеличенный"),
    ("до уменьшенный", ["до", "ми♭", "соль♭"], "трезвучие уменьшенный"),
    ("ре уменьшенный", ["ре", "фа", "ля♭"], "трезвучие уменьшенный"),
    ("си уменьшенный", ["си", "ре", "фа"], "трезвучие уменьшенный"),
]

# ============================================================
# ГЕНЕРАТОРЫ ЗАДАНИЙ
# ============================================================
def note_index(n):
    # приведение к хроматическому индексу
    mapping = {
        "до":0,"до#":1,"ре♭":1,"ре":2,"ре#":3,"ми♭":3,"ми":4,"фа":5,
        "фа#":6,"соль♭":6,"соль":7,"соль#":8,"ля♭":8,"ля":9,"ля#":10,
        "си♭":10,"си":11,"си#":0,"ми#":5,"фа♭":4,"до♭":11
    }
    return mapping.get(n, 0)

def transpose(n, semitones):
    idx = (note_index(n) + semitones) % 12
    sharp_names = ["до","до#","ре","ре#","ми","фа","фа#","соль","соль#","ля","ля#","си"]
    return sharp_names[idx]

def gen_interval(level):
    code, semis, name = random.choice(INTERVALS)
    base = random.choice(["до","ре","ми","фа","соль","ля","си","до#","ре#","фа#","соль#","ля#"])
    top = transpose(base, semis)
    question = f"Постройте интервал: <b>{name} ({code})</b> от ноты <b>{base}</b>"
    answer = f"<b>{base} — {top}</b> ({name}, {code}, {semis} полутонов)"
    return {
        "key": f"interval_{code}_{base}",
        "category": "Интервалы",
        "question": question,
        "answer": answer,
    }

def gen_key_signs(level):
    # уровень 1: без двойных знаков
    if level == 1:
        pool = [k for k in KEYS if abs(k[1]) <= 4]
    elif level == 2:
        pool = [k for k in KEYS if abs(k[1]) <= 5]
    else:
        pool = KEYS
    name, signs, typ, parallel = random.choice(pool)
    if signs == 0:
        ans = f"<b>0 знаков</b> (нет диезов и бемолей)"
    elif signs > 0:
        ans = f"<b>{signs} диез(а/ов)</b>: {', '.join(SHARP_ORDER[:signs])}"
    else:
        ans = f"<b>{abs(signs)} бемол(я/ей)</b>: {', '.join(FLAT_ORDER[:abs(signs)])}"
    question = f"Сколько знаков при ключе в тональности <b>{name}</b> и какие?"
    return {
        "key": f"keysign_{name}",
        "category": "Тональности",
        "question": question,
        "answer": ans + f"<br>Параллельная: <b>{parallel}</b>",
    }

def gen_which_notes_raised(level):
    count = random.randint(0, 4 if level == 1 else 7)
    if count == 0:
        question = "В какой тональности нет знаков при ключе?"
        answer = "<b>до мажор</b> и <b>ля минор</b> — 0 знаков."
        return {"key":"which_notes_0","category":"Тональности","question":question,"answer":answer}
    if random.random() < 0.5:
        notes = SHARP_ORDER[:count]
        question = f"Какие ноты повышаются, если при ключе <b>{count} диез(а/ов)</b>?"
        answer = f"<b>{', '.join(notes)}</b><br><i>Скороговорка: фа, до, соль, ре, ля, ми, си — отсчитываем {count} нот.</i>"
    else:
        notes = FLAT_ORDER[:count]
        question = f"Какие ноты понижаются, если при ключе <b>{count} бемол(я/ей)</b>?"
        answer = f"<b>{', '.join(notes)}</b><br><i>Скороговорка: си, ми, ля, ре, соль, до, фа — отсчитываем {count} нот.</i>"
    return {"key": f"which_notes_{question[-10:]}", "category": "Тональности", "question": question, "answer": answer}

def gen_parallel(level):
    name, signs, typ, parallel = random.choice(KEYS)
    question = f"Назовите параллельную тональность для <b>{name}</b>"
    answer = f"<b>{parallel}</b>"
    return {"key": f"parallel_{name}", "category": "Тональности", "question": question, "answer": answer}

def gen_triad(level):
    name, notes, kind = random.choice(CHORDS_TRIADS)
    if level == 1:
        # только мажор/минор/ув/ум без обращений
        pass
    question = f"Постройте {kind}: <b>{name}</b>"
    answer = f"<b>{' — '.join(notes)}</b>"
    return {"key": f"triad_{name}", "category": "Аккорды", "question": question, "answer": answer}

def gen_triad_inversion(level):
    name, notes, kind = random.choice([c for c in CHORDS_TRIADS if "мажор" in c[2] or "минор" in c[2]])
    inv = random.choice(["секстаккорд (6)", "квартсекстаккорд (64)"])
    if "6" in inv and "64" not in inv:
        inv_notes = [notes[1], notes[2], notes[0]]
    else:
        inv_notes = [notes[2], notes[0], notes[1]]
    question = f"Постройте {inv} от трезвучия <b>{name}</b>"
    answer = f"<b>{' — '.join(inv_notes)}</b> (обращение {kind} {name})"
    return {"key": f"triad_inv_{name}_{inv}", "category": "Аккорды", "question": question, "answer": answer}

def gen_septachord(level):
    roots = ["до","ре","ми","фа","соль","ля","си"]
    root = random.choice(roots)
    kinds = {
        "малый мажорный (доминантсептаккорд)": [0,4,7,10],
        "малый минорный": [0,3,7,10],
        "большой мажорный": [0,4,7,11],
        "уменьшенный": [0,3,6,9],
        "малый уменьшенный (полууменьшенный)": [0,3,6,10],
    }
    kind = random.choice(list(kinds.keys()))
    notes = [transpose(root, s) for s in kinds[kind]]
    question = f"Постройте {kind} септаккорд от ноты <b>{root}</b>"
    answer = f"<b>{' — '.join(notes)}</b>"
    return {"key": f"sept_{root}_{kind}", "category": "Аккорды", "question": question, "answer": answer}

# Гаммы
SCALES = {
    "натуральный мажор": [0,2,4,5,7,9,11],
    "натуральный минор": [0,2,3,5,7,8,10],
    "гармонический минор": [0,2,3,5,7,8,11],
    "мелодический минор (вверх)": [0,2,3,5,7,9,11],
    "хроматическая": [0,1,2,3,4,5,6,7,8,9,10,11,12],
    "целотонная": [0,2,4,6,8,10,12],
    "уменьшенная (тон-полутон)": [0,1,3,4,6,7,9,10,12],
}
def gen_scale(level):
    root = random.choice(["до","ре","ми","фа","соль","ля","си"])
    if level == 2:
        kinds = ["натуральный мажор","натуральный минор","хроматическая","целотонная","уменьшенная (тон-полутон)"]
    else:
        kinds = list(SCALES.keys())
    kind = random.choice(kinds)
    steps = SCALES[kind]
    notes = [transpose(root, s) for s in steps]
    question = f"Постройте гамму: <b>{root} {kind}</b>"
    answer = f"<b>{' — '.join(notes)}</b>"
    return {"key": f"scale_{root}_{kind}", "category": "Гаммы", "question": question, "answer": answer}

def gen_arpeggio(level):
    root = random.choice(["до","ре","ми","фа","соль","ля","си"])
    kind = random.choice(["мажорное трезвучие","минорное трезвучие","доминантсептаккорд","уменьшенный септаккорд"])
    if kind == "мажорное трезвучие":
        notes = [transpose(root,s) for s in [0,4,7,12]]
    elif kind == "минорное трезвучие":
        notes = [transpose(root,s) for s in [0,3,7,12]]
    elif kind == "доминантсептаккорд":
        notes = [transpose(root,s) for s in [0,4,7,10,12]]
    else:
        notes = [transpose(root,s) for s in [0,3,6,9,12]]
    question = f"Постройте арпеджио: <b>{kind} от {root}</b>"
    answer = f"<b>{' — '.join(notes)}</b>"
    return {"key": f"arp_{root}_{kind}", "category": "Арпеджио", "question": question, "answer": answer}

def gen_hard_task(level):
    # продвинутые — комбинированные
    return random.choice([
        gen_parallel(level),
        gen_septachord(level),
        gen_scale(level),
        gen_arpeggio(level),
        gen_triad_inversion(level),
    ])

# ============================================================
# ВЫБОР ЗАДАНИЯ ПО УРОВНЮ
# ============================================================
def generate_task(level):
    """Возвращает задание, гарантированно из случайной категории."""
    if level == 1:
        pool = [gen_interval, gen_key_signs, gen_which_notes_raised, gen_triad]
    elif level == 2:
        pool = [gen_interval, gen_key_signs, gen_which_notes_raised,
                gen_triad, gen_triad_inversion, gen_scale, gen_parallel]
    elif level == 3:
        pool = [gen_interval, gen_key_signs, gen_which_notes_raised,
                gen_triad, gen_triad_inversion, gen_septachord,
                gen_scale, gen_parallel, gen_arpeggio]
    else:
        pool = [gen_interval, gen_key_signs, gen_which_notes_raised,
                gen_triad, gen_triad_inversion, gen_septachord,
                gen_scale, gen_parallel, gen_arpeggio, gen_hard_task]
    return random.choice(pool)(level)

# ============================================================
# HTML ШАБЛОНЫ
# ============================================================
BASE_HTML = """
<!DOCTYPE html>
<html lang="ru">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Music Trainer</title>
<style>
  * { box-sizing: border-box; }
  body {
    margin: 0; font-family: 'Segoe UI', Roboto, sans-serif;
    background: linear-gradient(135deg, #1e3c72 0%, #2a5298 100%);
    color: #f0f0f0; min-height: 100vh;
  }
  .topbar {
    display: flex; align-items: center; padding: 12px 20px;
    background: rgba(0,0,0,0.3); position: sticky; top: 0; z-index: 100;
  }
  .burger { font-size: 26px; cursor: pointer; padding: 4px 12px; user-select: none; }
  .burger:hover { background: rgba(255,255,255,0.1); border-radius: 6px; }
  .title { margin-left: 12px; font-weight: 600; font-size: 18px; }
  .menu {
    position: fixed; top: 0; left: -280px; width: 260px; height: 100%;
    background: #122240; padding: 20px; transition: left 0.3s;
    z-index: 200; overflow-y: auto;
  }
  .menu.open { left: 0; }
  .menu h3 { color: #7fd3ff; border-bottom: 1px solid #2a5298; padding-bottom: 10px; }
  .menu a {
    display: block; color: #e0e0e0; text-decoration: none;
    padding: 10px 12px; border-radius: 8px; margin: 6px 0;
  }
  .menu a:hover { background: #2a5298; }
  .container { max-width: 900px; margin: 40px auto; padding: 0 20px; }
  .card {
    background: rgba(255,255,255,0.08); border-radius: 16px;
    padding: 28px; margin-bottom: 20px;
    box-shadow: 0 8px 32px rgba(0,0,0,0.3);
  }
  .levels { display: grid; grid-template-columns: repeat(auto-fit, minmax(180px,1fr)); gap: 16px; }
  .level-card {
    background: linear-gradient(145deg,#2a5298,#1e3c72); border-radius: 14px;
    padding: 24px; text-align: center; cursor: pointer; transition: transform 0.2s;
  }
  .level-card:hover { transform: translateY(-4px); box-shadow: 0 8px 24px rgba(127,211,255,0.3); }
  .level-card h4 { margin: 0 0 8px; font-size: 20px; }
  .level-card p { margin: 0; color: #b0c8e8; font-size: 13px; }
  h2 { color: #7fd3ff; }
  .question-box {
    font-size: 20px; line-height: 1.6; padding: 24px;
    background: rgba(0,0,0,0.25); border-radius: 12px; margin-bottom: 20px;
    min-height: 80px;
  }
  .btn {
    display: inline-block; padding: 12px 22px; border-radius: 10px;
    border: none; cursor: pointer; font-size: 15px; font-weight: 600;
    margin: 6px 6px 6px 0; transition: 0.2s; text-decoration: none; color: #fff;
  }
  .btn-primary { background: #2a5298; }
  .btn-primary:hover { background: #3a6ac8; }
  .btn-success { background: #28a745; }
  .btn-success:hover { background: #34c759; }
  .btn-danger { background: #c0392b; }
  .btn-danger:hover { background: #e74c3c; }
  .btn-star { background: #f39c12; }
  .btn-star:hover { background: #f1c40f; }
  .answer-box {
    background: rgba(40,167,69,0.15); border-left: 4px solid #28a745;
    padding: 20px; border-radius: 10px; margin: 16px 0; font-size: 18px;
    line-height: 1.6;
  }
  .hint { color: #b0c8e8; font-size: 14px; margin-top: 8px; }
  .folder {
    background: rgba(255,255,255,0.06); border-radius: 12px;
    padding: 16px; margin-bottom: 12px; cursor: pointer;
  }
  .folder summary { cursor: pointer; font-weight: 600; color: #7fd3ff; font-size: 16px; }
  .task-item {
    background: rgba(0,0,0,0.2); border-radius: 8px;
    padding: 12px; margin: 8px 0; font-size: 14px;
  }
  .task-item .q { color: #e0e0e0; }
  .task-item .a { color: #7fd3ff; margin-top: 6px; display: none; }
  .task-item.open .a { display: block; }
  .back-link { color: #7fd3ff; text-decoration: none; }
  input[type=text], input[type=password] {
    width: 100%; padding: 12px; margin: 8px 0; border-radius: 8px;
    border: 1px solid #2a5298; background: rgba(0,0,0,0.3); color: #fff; font-size: 15px;
  }
  .error { color: #ff6b6b; margin: 8px 0; }
  .stat-num { font-size: 40px; font-weight: 700; color: #7fd3ff; }
  .stat-label { color: #b0c8e8; font-size: 14px; }
  .stats-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 20px; }
  .empty { color: #888; font-style: italic; padding: 12px; }
  .overlay { position: fixed; inset: 0; background: rgba(0,0,0,0.5); display: none; z-index: 150; }
  .overlay.open { display: block; }
  @media (max-width: 600px) { .stats-grid { grid-template-columns: 1fr; } }
</style>
</head>
<body>
<div class="overlay" id="overlay" onclick="toggleMenu()"></div>
<div class="menu" id="menu">
  <h3>🎵 {{ username }}</h3>
  <a href="/home">🏠 Главная</a>
  <a href="/stats">📊 Статистика</a>
  <a href="/favorites">⭐ Избранное</a>
  <a href="/learn">📚 Обучение</a>
  <a href="/logout">🚪 Выйти</a>
</div>
<div class="topbar">
  <span class="burger" onclick="toggleMenu()">☰</span>
  <span class="title">🎹 Music Trainer</span>
</div>
<div class="container">
{{ content|safe }}
</div>
<script>
function toggleMenu() {
  document.getElementById('menu').classList.toggle('open');
  document.getElementById('overlay').classList.toggle('open');
}
</script>
</body>
</html>
"""

def render_page(content, username):
    return render_template_string(BASE_HTML, content=content, username=username)

# ============================================================
# МАРШРУТЫ
# ============================================================
@app.route("/")
def index():
    if "user_id" in session:
        return redirect(url_for("home"))
    return render_page("""
    <div class="card" style="text-align:center;">
      <h2>Добро пожаловать!</h2>
      <p>Тренируйте интервалы, аккорды, гаммы, арпеджио и тональности в случайном порядке.</p>
      <a href="/login" class="btn btn-primary">Войти</a>
      <a href="/register" class="btn btn-success">Регистрация</a>
    </div>
    """, "Гость")

@app.route("/register", methods=["GET","POST"])
def register():
    error = ""
    if request.method == "POST":
        u = request.form.get("username","").strip()
        p = request.form.get("password","").strip()
        if not u or not p:
            error = "Заполните все поля"
        else:
            db = get_db()
            try:
                cur = db.execute("INSERT INTO users(username,password) VALUES(?,?)",(u,p))
                db.execute("INSERT INTO stats(user_id) VALUES(?)",(cur.lastrowid,))
                db.commit()
                session["user_id"] = cur.lastrowid
                session["username"] = u
                return redirect(url_for("home"))
            except sqlite3.IntegrityError:
                error = "Такое имя пользователя уже занято"
    content = f"""
    <div class="card" style="max-width:420px;margin:auto;">
      <h2>Регистрация</h2>
      {f'<div class="error">{error}</div>' if error else ''}
      <form method="post">
        <input type="text" name="username" placeholder="Имя пользователя" required>
        <input type="password" name="password" placeholder="Пароль" required>
        <button class="btn btn-success" type="submit">Создать аккаунт</button>
      </form>
      <p class="hint">Уже есть аккаунт? <a href="/login" class="back-link">Войти</a></p>
    </div>
    """
    return render_page(content, "Гость")

@app.route("/login", methods=["GET","POST"])
def login():
    error = ""
    if request.method == "POST":
        u = request.form.get("username","").strip()
        p = request.form.get("password","").strip()
        db = get_db()
        row = db.execute("SELECT * FROM users WHERE username=? AND password=?",(u,p)).fetchone()
        if row:
            session["user_id"] = row["id"]
            session["username"] = row["username"]
            return redirect(url_for("home"))
        error = "Неверное имя или пароль"
    content = f"""
    <div class="card" style="max-width:420px;margin:auto;">
      <h2>Вход</h2>
      {f'<div class="error">{error}</div>' if error else ''}
      <form method="post">
        <input type="text" name="username" placeholder="Имя пользователя" required>
        <input type="password" name="password" placeholder="Пароль" required>
        <button class="btn btn-primary" type="submit">Войти</button>
      </form>
      <p class="hint">Нет аккаунта? <a href="/register" class="back-link">Зарегистрироваться</a></p>
    </div>
    """
    return render_page(content, "Гость")

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("index"))

@app.route("/home")
def home():
    if "user_id" not in session:
        return redirect(url_for("login"))
    content = """
    <div class="card">
      <h2>Выберите уровень</h2>
      <p class="hint">Задания выдаются случайно из всех категорий — эффект неожиданности помогает запоминать лучше!</p>
      <div class="levels">
        <a href="/train/1" style="text-decoration:none;color:inherit;">
          <div class="level-card"><h4>🌱 Новичок</h4><p>Трезвучия • все интервалы • базовые тональности • знаки при ключе</p></div>
        </a>
        <a href="/train/2" style="text-decoration:none;color:inherit;">
          <div class="level-card"><h4>📗 Средний</h4><p>Обращения • натуральные гаммы • параллельные тональности</p></div>
        </a>
        <a href="/train/3" style="text-decoration:none;color:inherit;">
          <div class="level-card"><h4>🎓 Умеющий</h4><p>Септаккорды • арпеджио • все виды гамм и тональностей</p></div>
        </a>
        <a href="/train/4" style="text-decoration:none;color:inherit;">
          <div class="level-card"><h4>🏆 Продвинутый</h4><p>Комбинированные задания • знаки + параллельная • сложные септаккорды</p></div>
        </a>
      </div>
    </div>
    """
    return render_page(content, session["username"])

@app.route("/train/<
