# 🗳️ SchoolVote — Web-Based School Voting System

A clean, full-stack voting system for school elections.
Stack: Python (Flask) + JSON database + HTML/CSS/JS + SheetJS for Excel imports

---

## 📁 Project Structure

```
voting-app/
├── server.py       ← Flask backend + all API routes
├── db.json         ← JSON database (students, candidates, votes)
├── index.html      ← Full frontend (login + voting + admin dashboard)
├── README.md
├── students_import_template.xlsx    ← Excel template for bulk student import
└── candidates_import_template.xlsx  ← Excel template for bulk candidate import
```

---

## 🚀 Setup & Run

### 1. Install Flask
```bash
pip install flask openpyxl
```

### 2. Start the server
```bash
cd voting-app
python server.py
```

### 3. Open in browser
```
http://localhost:5000
```

---

## 🔑 Demo Credentials

| Role    | Username/Admission | Password |
|---------|--------------------|----------|
| Admin   | `admin`            | `admin`  |
| Student | `7676`             | `kanene` |

---

## ✨ Features

### Student Side
- Login with admission number + password
- View all positions and candidates
- Select and confirm vote per position
- Cannot vote twice for same position
- Progress bar showing voting completion

### Admin Dashboard
- **Live Results** — real-time vote counts with bar charts, leading candidate highlighted
- **Voter Turnout** — overall + per-class participation stats
- **Candidate Management** — add/remove candidates per position, **bulk import via Excel/CSV**
- **Students** — view, search, add, **bulk-import via Excel/CSV**, reset passwords, delete
- **Settings** — open/close voting, export results as .txt

---

## 📥 Bulk Import Features (NEW!)

### Excel Import for Students
- Upload `.xlsx` or `.xls` files with student data
- Required columns: `admission`, `name`, `class`
- Optional column: `password` (defaults to "1234")
- Preview data before importing
- Automatic duplicate detection
- Download template: `students_import_template.xlsx`

### Excel Import for Candidates
- Upload `.xlsx` or `.xls` files with candidate data
- Required columns: `position`, `name`, `class`
- Position names must match existing positions (case-insensitive)
- Preview data before importing
- Download template: `candidates_import_template.xlsx`

### CSV Import (Alternative)
- Both students and candidates support CSV import
- Same column requirements as Excel
- Drag-and-drop or file selection
- Preview before import

### Using the Templates

#### Students Template Format:
```
| admission | name           | class   | password |
|-----------|----------------|---------|----------|
| S007      | John Kamau     | Form 4A | 1234     |
| S008      | Mary Wanjiku   | Form 4B | 1234     |
```

#### Candidates Template Format:
```
| position      | name           | class   |
|---------------|----------------|---------|
| Head Boy      | James Mwangi   | Form 4A |
| Head Girl     | Sarah Akinyi   | Form 4A |
| Games Captain | Michael Kiprop | Form 3A |
```

---

## 🗄️ Database Schema (db.json)

```json
{
  "settings": { "voting_open": true, "election_title": "...", "school_name": "..." },
  "admins":   [{ "username": "admin", "password": "<sha256>", "name": "..." }],
  "students": [{ "admission": "S001", "name": "...", "class": "...", "password": "<sha256>" }],
  "positions":[{ "id": "p1", "name": "Head Boy", "candidates": [{ "id": "c1", "name": "...", "class": "..." }] }],
  "votes":    [{ "admission": "S001", "position_id": "p1", "candidate_id": "c1", "timestamp": "..." }]
}
```

---

## 📡 API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/login/student` | Student login |
| POST | `/api/login/admin` | Admin login |
| POST | `/api/logout` | Log out |
| GET  | `/api/positions` | Get all positions + candidates |
| GET  | `/api/my-votes` | Get student's voted positions |
| POST | `/api/vote` | Cast a vote |
| GET  | `/api/admin/results` | Vote counts per candidate |
| GET  | `/api/admin/turnout` | Turnout stats |
| GET/POST | `/api/admin/settings` | Get/update settings |
| POST | `/api/admin/candidates` | Add candidate |
| DELETE | `/api/admin/candidates/:id` | Remove candidate |
| GET  | `/api/admin/students?q=` | List/search students (with voted status) |
| POST | `/api/admin/students` | Add single student or bulk import (array) |
| POST | `/api/admin/students/:adm/reset-password` | Reset student password |
| DELETE | `/api/admin/students/:adm` | Delete student + their votes |
| GET  | `/api/admin/export` | Download results .txt |

---

## 🔒 Security Notes
- Passwords stored as SHA-256 hashes
- Session tokens expire after 1 hour
- One vote per student per position enforced server-side
- Admin routes require admin session token
- Bulk import validates data and prevents duplicates

---

## 📊 Import Tips

### For Best Results:
1. **Use the provided templates** - They have the correct column headers
2. **Match position names exactly** - For candidate imports, position names must match (case-insensitive)
3. **Check for duplicates** - The system will skip duplicate admission numbers
4. **Preview before importing** - Review the preview table to catch errors
5. **Keep data clean** - Remove empty rows and ensure all required fields are filled

### Supported File Formats:
- **Excel**: `.xlsx`, `.xls` (recommended)
- **CSV**: `.csv` (comma-separated values)

### Column Name Variations:
The system recognizes multiple column name variations (case-insensitive):
- **Admission**: admission, adm, ADM
- **Name**: name, student
- **Class**: class, form
- **Password**: password (students only)
- **Position**: position (candidates only)

---

## 🎨 Technologies Used

- **Backend**: Flask (Python)
- **Frontend**: Vanilla JavaScript, HTML5, CSS3
- **Excel Processing**: SheetJS (xlsx.js)
- **Database**: JSON file-based storage
- **Fonts**: DM Sans, DM Serif Display (Google Fonts)

---

## 📝 License

Open source - feel free to use and modify for your school elections!
