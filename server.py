from flask import Flask, request, jsonify, send_from_directory
import json, os, hashlib, secrets, time
from datetime import datetime

app = Flask(__name__, static_folder='.')

DB_PATH = 'db.json'

# ── helpers ──────────────────────────────────────────────────────────────────

def load_db():
    with open(DB_PATH, 'r') as f:
        return json.load(f)

def save_db(data):
    with open(DB_PATH, 'w') as f:
        json.dump(data, f, indent=2)

def hash_password(pw):
    return hashlib.sha256(pw.encode()).hexdigest()

def gen_token():
    return secrets.token_hex(24)

# In-memory session store  {token: {role, id, expires}}
sessions = {}

def create_session(role, uid):
    token = gen_token()
    sessions[token] = {'role': role, 'id': uid, 'expires': time.time() + 3600}
    return token

def get_session(req):
    token = req.headers.get('X-Token')
    if not token:
        return None
    s = sessions.get(token)
    if s and s['expires'] > time.time():
        return s
    return None

def require_admin(req):
    s = get_session(req)
    return s if (s and s['role'] == 'admin') else None

def require_student(req):
    s = get_session(req)
    return s if (s and s['role'] == 'student') else None

# ── static files ─────────────────────────────────────────────────────────────

@app.route('/')
def index():
    return send_from_directory('.', 'index.html')

@app.route('/<path:path>')
def static_files(path):
    return send_from_directory('.', path)

# ── auth ──────────────────────────────────────────────────────────────────────

@app.route('/api/login/student', methods=['POST'])
def student_login():
    body = request.json
    adm = body.get('admission', '').strip()
    pw  = body.get('password', '')
    db  = load_db()
    student = next((s for s in db['students'] if s['admission'] == adm), None)
    if not student or student['password'] != hash_password(pw):
        return jsonify({'error': 'Invalid admission number or password'}), 401
    if not student.get('active', True):
        return jsonify({'error': 'Your account has been deactivated. Please contact the administrator.'}), 403
    token = create_session('student', adm)
    return jsonify({'token': token, 'name': student['name'], 'class': student['class']})

@app.route('/api/login/admin', methods=['POST'])
def admin_login():
    body = request.json
    username = body.get('username', '')
    pw       = body.get('password', '')
    db       = load_db()
    admin = next((a for a in db['admins'] if a['username'] == username), None)
    if not admin or admin['password'] != hash_password(pw):
        return jsonify({'error': 'Invalid credentials'}), 401
    token = create_session('admin', username)
    return jsonify({'token': token, 'name': admin['name']})

@app.route('/api/logout', methods=['POST'])
def logout():
    token = request.headers.get('X-Token')
    sessions.pop(token, None)
    return jsonify({'ok': True})

# ── student endpoints ─────────────────────────────────────────────────────────

@app.route('/api/positions', methods=['GET'])
def get_positions():
    if not get_session(request):
        return jsonify({'error': 'Unauthorized'}), 401
    db = load_db()
    return jsonify(db['positions'])

@app.route('/api/my-votes', methods=['GET'])
def my_votes():
    s = require_student(request)
    if not s:
        return jsonify({'error': 'Unauthorized'}), 401
    db = load_db()
    student_votes = [v for v in db['votes'] if v['admission'] == s['id']]
    voted_positions = [v['position_id'] for v in student_votes]
    return jsonify({'voted': voted_positions})

@app.route('/api/vote', methods=['POST'])
def cast_vote():
    s = require_student(request)
    if not s:
        return jsonify({'error': 'Unauthorized'}), 401
    body = request.json
    position_id  = body.get('position_id')
    candidate_id = body.get('candidate_id')
    db = load_db()

    # Check voting is open
    if not db['settings']['voting_open']:
        return jsonify({'error': 'Voting is currently closed'}), 403

    # Check already voted for this position
    already = any(v for v in db['votes']
                  if v['admission'] == s['id'] and v['position_id'] == position_id)
    if already:
        return jsonify({'error': 'You have already voted for this position'}), 409

    # Validate position/candidate
    position = next((p for p in db['positions'] if p['id'] == position_id), None)
    if not position:
        return jsonify({'error': 'Invalid position'}), 400
    candidate = next((c for c in position['candidates'] if c['id'] == candidate_id), None)
    if not candidate:
        return jsonify({'error': 'Invalid candidate'}), 400

    db['votes'].append({
        'admission': s['id'],
        'position_id': position_id,
        'candidate_id': candidate_id,
        'timestamp': datetime.now().isoformat()
    })
    save_db(db)
    return jsonify({'ok': True})

# ── admin endpoints ───────────────────────────────────────────────────────────

@app.route('/api/admin/results', methods=['GET'])
def admin_results():
    if not require_admin(request):
        return jsonify({'error': 'Unauthorized'}), 401
    db = load_db()
    results = []
    for pos in db['positions']:
        candidates = []
        for cand in pos['candidates']:
            count = sum(1 for v in db['votes']
                        if v['position_id'] == pos['id'] and v['candidate_id'] == cand['id'])
            candidates.append({**cand, 'votes': count})
        candidates.sort(key=lambda x: x['votes'], reverse=True)
        # Fix: use a copy of pos without 'candidates', then add sorted candidates
        pos_copy = {k: v for k, v in pos.items() if k != 'candidates'}
        results.append({**pos_copy, 'candidates': candidates})
    return jsonify(results)

@app.route('/api/admin/turnout', methods=['GET'])
def admin_turnout():
    if not require_admin(request):
        return jsonify({'error': 'Unauthorized'}), 401
    db = load_db()
    total_students = len(db['students'])
    voted_students = len(set(v['admission'] for v in db['votes']))
    by_class = {}
    for st in db['students']:
        cls = st['class']
        by_class.setdefault(cls, {'total': 0, 'voted': 0})
        by_class[cls]['total'] += 1
    for v in db['votes']:
        st = next((s for s in db['students'] if s['admission'] == v['admission']), None)
        if st:
            by_class[st['class']]['voted'] = by_class[st['class']].get('voted', 0)
            # count unique voters per class
    # recalculate unique voters per class properly
    by_class_voters = {}
    for v in db['votes']:
        st = next((s for s in db['students'] if s['admission'] == v['admission']), None)
        if st:
            by_class_voters.setdefault(st['class'], set()).add(st['admission'])
    for cls in by_class:
        by_class[cls]['voted'] = len(by_class_voters.get(cls, set()))
    return jsonify({
        'total': total_students,
        'voted': voted_students,
        'by_class': by_class
    })

@app.route('/api/admin/settings', methods=['GET', 'POST'])
def admin_settings():
    if not require_admin(request):
        return jsonify({'error': 'Unauthorized'}), 401
    db = load_db()
    if request.method == 'POST':
        body = request.json
        db['settings'].update(body)
        save_db(db)
    return jsonify(db['settings'])

@app.route('/api/admin/account', methods=['POST'])
def update_admin_account():
    s = require_admin(request)
    if not s:
        return jsonify({'error': 'Unauthorized'}), 401
    body = request.json
    db = load_db()
    admin = next((a for a in db['admins'] if a['username'] == s['id']), None)
    if not admin:
        return jsonify({'error': 'Admin not found'}), 404
    # Verify current password
    current_pw = body.get('current_password', '')
    if admin['password'] != hash_password(current_pw):
        return jsonify({'error': 'Current password is incorrect'}), 403
    # Update fields
    if body.get('name', '').strip():
        admin['name'] = body['name'].strip()
    if body.get('username', '').strip():
        new_username = body['username'].strip()
        if new_username != admin['username'] and any(a['username'] == new_username for a in db['admins']):
            return jsonify({'error': 'Username already taken'}), 409
        admin['username'] = new_username
        # Update session id too
        sessions[request.headers.get('X-Token')]['id'] = new_username
    if body.get('new_password', ''):
        admin['password'] = hash_password(body['new_password'])
    save_db(db)
    return jsonify({'ok': True, 'name': admin['name'], 'username': admin['username']})

@app.route('/api/admin/candidates', methods=['POST'])
def add_candidate():
    if not require_admin(request):
        return jsonify({'error': 'Unauthorized'}), 401
    body = request.json
    position_id = body.get('position_id')
    name = body.get('name', '').strip()
    if not name:
        return jsonify({'error': 'Name required'}), 400
    db = load_db()
    pos = next((p for p in db['positions'] if p['id'] == position_id), None)
    if not pos:
        return jsonify({'error': 'Position not found'}), 404
    new_id = f"c{int(time.time()*1000)}"
    pos['candidates'].append({'id': new_id, 'name': name, 'class': body.get('class','')})
    save_db(db)
    return jsonify({'ok': True, 'id': new_id})

@app.route('/api/admin/candidates/<cand_id>', methods=['DELETE'])
def delete_candidate(cand_id):
    if not require_admin(request):
        return jsonify({'error': 'Unauthorized'}), 401
    db = load_db()
    for pos in db['positions']:
        pos['candidates'] = [c for c in pos['candidates'] if c['id'] != cand_id]
    save_db(db)
    return jsonify({'ok': True})

@app.route('/api/admin/candidates/bulk-delete', methods=['POST'])
def bulk_delete_candidates():
    if not require_admin(request):
        return jsonify({'error': 'Unauthorized'}), 401
    db = load_db()
    deleted = 0
    # Clear all candidates from all positions
    for pos in db['positions']:
        deleted += len(pos['candidates'])
        pos['candidates'] = []
    save_db(db)
    return jsonify({'ok': True, 'deleted': deleted})

@app.route('/api/admin/positions', methods=['POST'])
def add_position():
    if not require_admin(request):
        return jsonify({'error': 'Unauthorized'}), 401
    body = request.json
    name = body.get('name', '').strip()
    if not name:
        return jsonify({'error': 'Name required'}), 400
    db = load_db()
    new_id = f"p{int(time.time()*1000)}"
    db['positions'].append({'id': new_id, 'name': name, 'candidates': []})
    save_db(db)
    return jsonify({'ok': True, 'id': new_id})

@app.route('/api/admin/positions/<pos_id>', methods=['DELETE'])
def delete_position(pos_id):
    if not require_admin(request):
        return jsonify({'error': 'Unauthorized'}), 401
    db = load_db()
    before = len(db['positions'])
    db['positions'] = [p for p in db['positions'] if p['id'] != pos_id]
    if len(db['positions']) == before:
        return jsonify({'error': 'Position not found'}), 404
    # Remove votes for this position too
    db['votes'] = [v for v in db['votes'] if v['position_id'] != pos_id]
    save_db(db)
    return jsonify({'ok': True})

@app.route('/api/admin/reset-election', methods=['POST'])
def reset_election():
    if not require_admin(request):
        return jsonify({'error': 'Unauthorized'}), 401
    db = load_db()
    db['positions'] = []
    db['votes'] = []
    db['settings']['voting_open'] = False
    save_db(db)
    return jsonify({'ok': True})

@app.route('/api/admin/students', methods=['GET', 'POST'])
def admin_students():
    if not require_admin(request):
        return jsonify({'error': 'Unauthorized'}), 401
    db = load_db()
    if request.method == 'POST':
        body = request.json
        # Bulk import: accept array
        if isinstance(body, list):
            added, skipped = 0, 0
            for item in body:
                adm = item.get('admission', '').strip()
                if not adm or any(s['admission'] == adm for s in db['students']):
                    skipped += 1
                    continue
                db['students'].append({
                    'admission': adm,
                    'name': item.get('name', '').strip(),
                    'class': item.get('class', '').strip(),
                    'password': hash_password(item.get('password', '1234')),
                    'active': True
                })
                added += 1
            save_db(db)
            return jsonify({'ok': True, 'added': added, 'skipped': skipped})
        # Single student add
        adm = body.get('admission', '').strip()
        if any(s['admission'] == adm for s in db['students']):
            return jsonify({'error': 'Admission number already exists'}), 409
        db['students'].append({
            'admission': adm,
            'name': body.get('name', '').strip(),
            'class': body.get('class', '').strip(),
            'password': hash_password(body.get('password', '1234')),
            'active': True
        })
        save_db(db)
        return jsonify({'ok': True})
    # GET with optional search
    q = request.args.get('q', '').lower().strip()
    voted_admissions = set(v['admission'] for v in db['votes'])
    students = []
    for s in db['students']:
        if q and q not in s['admission'].lower() and q not in s['name'].lower() and q not in s['class'].lower():
            continue
        students.append({
            'admission': s['admission'],
            'name': s['name'],
            'class': s['class'],
            'has_voted': s['admission'] in voted_admissions,
            'active': s.get('active', True)
        })
    return jsonify(students)

@app.route('/api/admin/students/<adm>/set-active', methods=['POST'])
def set_student_active(adm):
    if not require_admin(request):
        return jsonify({'error': 'Unauthorized'}), 401
    body = request.json or {}
    active = body.get('active', True)
    db = load_db()
    student = next((s for s in db['students'] if s['admission'] == adm), None)
    if not student:
        return jsonify({'error': 'Student not found'}), 404
    student['active'] = bool(active)
    save_db(db)
    return jsonify({'ok': True, 'active': student['active']})

@app.route('/api/admin/students/<adm>/reset-password', methods=['POST'])
def reset_student_password(adm):
    if not require_admin(request):
        return jsonify({'error': 'Unauthorized'}), 401
    body = request.json or {}
    new_pw = body.get('password', '1234')
    db = load_db()
    student = next((s for s in db['students'] if s['admission'] == adm), None)
    if not student:
        return jsonify({'error': 'Student not found'}), 404
    student['password'] = hash_password(new_pw)
    save_db(db)
    return jsonify({'ok': True})

@app.route('/api/admin/students/<adm>', methods=['DELETE'])
def delete_student(adm):
    if not require_admin(request):
        return jsonify({'error': 'Unauthorized'}), 401
    db = load_db()
    before = len(db['students'])
    db['students'] = [s for s in db['students'] if s['admission'] != adm]
    if len(db['students']) == before:
        return jsonify({'error': 'Student not found'}), 404
    # Also remove their votes
    db['votes'] = [v for v in db['votes'] if v['admission'] != adm]
    save_db(db)
    return jsonify({'ok': True})

@app.route('/api/admin/students/bulk-delete', methods=['POST'])
def bulk_delete_students():
    if not require_admin(request):
        return jsonify({'error': 'Unauthorized'}), 401
    db = load_db()
    before = len(db['students'])
    # Clear all students
    db['students'] = []
    # Clear all votes since there are no students
    db['votes'] = []
    save_db(db)
    deleted = before
    return jsonify({'ok': True, 'deleted': deleted})

@app.route('/api/admin/export', methods=['GET'])
def export_results():
    if not require_admin(request):
        return jsonify({'error': 'Unauthorized'}), 401
    db = load_db()
    lines = ['SCHOOL VOTING SYSTEM - RESULTS EXPORT', '='*50,
             f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", '']
    for pos in db['positions']:
        lines.append(f"POSITION: {pos['name']}")
        lines.append('-'*30)
        for cand in pos['candidates']:
            count = sum(1 for v in db['votes']
                        if v['position_id'] == pos['id'] and v['candidate_id'] == cand['id'])
            lines.append(f"  {cand['name']} ({cand.get('class','')}) — {count} vote(s)")
        lines.append('')
    total = len(db['students'])
    voted = len(set(v['admission'] for v in db['votes']))
    lines += [f"TURNOUT: {voted}/{total} students ({round(voted/total*100 if total else 0,1)}%)"]
    return '\n'.join(lines), 200, {
        'Content-Type': 'text/plain',
        'Content-Disposition': 'attachment; filename="results.txt"'
    }

if __name__ == '__main__':
    app.run(host='127.0.0.1', port=8000, debug=True)