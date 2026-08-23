import os, json, secrets, sqlite3, hmac
from datetime import datetime
from pathlib import Path
from functools import wraps
from flask import Flask, render_template, request, redirect, url_for, session, abort, send_from_directory, flash
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename

BASE = Path(__file__).resolve().parent
DB = BASE / 'health_coaching.db'
UPLOADS = BASE / 'uploads'
UPLOADS.mkdir(exist_ok=True)
app = Flask(__name__)
app.config.update(
    SECRET_KEY=os.environ.get('HC_SECRET_KEY', secrets.token_hex(32)),
    MAX_CONTENT_LENGTH=50*1024*1024,
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE='Lax',
    SESSION_COOKIE_SECURE=os.environ.get('HC_HTTPS','0') == '1',
)
ADMIN_PASSWORD = os.environ.get('HC_ADMIN_PASSWORD', 'ChangeThisPassword123!')
ALLOWED = {'pdf','png','jpg','jpeg','webp','doc','docx','mp4','mov','webm'}

QUESTIONS = [
('basic','Full name','text',None,True),('basic','Phone number','tel',None,True),('basic','Email address','email',None,False),('basic','City','text',None,False),
('basic','Age','number',None,True),('basic','Gender','mcq',['Female','Male','Prefer not to say','Other'],False),
('goals','Main goals','checkbox',['Weight loss','Weight gain','Weight maintenance','Improve eating habits','Improve fitness','Improve sleep','Increase energy','Reduce cravings','Build healthy habits','Manage stress','Other'],True),
('goals','How motivated are you?','rating',['1','2','3','4','5','6','7','8','9','10'],True),
('schedule','Usual wake-up time','mcq',['Before 5 AM','5–6 AM','6–7 AM','7–8 AM','8–9 AM','9–10 AM','10–11 AM','After 11 AM'],True),
('schedule','Usual bedtime','mcq',['Before 8 PM','8–9 PM','9–10 PM','10–11 PM','11 PM–12 AM','After midnight'],True),
('schedule','Work/study schedule','checkbox',['Office/work','Work from home','Study','Household work','Childcare','Shift work','Mostly sitting','Mostly active','Other'],True),
('food','Diet pattern','mcq',['Vegetarian','Vegan','Eggetarian','Non-vegetarian','Jain','Other'],True),
('food','Favourite foods','checkbox',['Roti','Rice','Dal','Paneer','Poha','Upma','Idli','Dosa','Paratha','Thepla','Khichdi','Chole','Rajma','Sprouts','Fruits','Salads','Curd','Other'],False),
('food','Foods you dislike','checkbox',['Roti','Rice','Dal','Paneer','Poha','Upma','Idli','Dosa','Paratha','Thepla','Khichdi','Chole','Rajma','Sprouts','Fruits','Salads','Curd','Other'],False),
('food','Foods you never want in your plan','checkbox',['Roti','Rice','Dal','Paneer','Poha','Upma','Idli','Dosa','Paratha','Thepla','Khichdi','Chole','Rajma','Sprouts','Fruits','Salads','Curd','Other'],False),
('food','Foods you definitely want included','checkbox',['Roti','Rice','Dal','Paneer','Poha','Upma','Idli','Dosa','Paratha','Thepla','Khichdi','Chole','Rajma','Sprouts','Fruits','Salads','Curd','Other'],False),
('food','Preferred cuisines','checkbox',['North Indian','South Indian','Gujarati','Maharashtrian','Punjabi','Rajasthani','Bengali','Sindhi','Jain','Indo-Chinese','Chinese','Italian','Mexican','Continental','Middle Eastern','Other'],False),
('meals','Breakfast frequency','mcq',['Every day','Most days','Sometimes','Rarely','Never'],True),
('meals','Typical breakfast','checkbox',['Poha','Upma','Idli','Dosa','Uttapam','Paratha','Roti','Thepla','Bread','Sandwich','Eggs','Paneer','Cereal','Oats','Fruit','Smoothie','Sprouts','Dal','Khichdi','Leftovers','Biscuits','Nothing','Other'],False),
('meals','Typical evening snacks','checkbox',['Tea','Coffee','Fruit','Nuts','Biscuits','Namkeen','Chips','Sandwich','Samosa','Pakora/Bhajiya','Chaat','Chocolate','Sweets','Bakery items','Maggi/Noodles','Nothing','Other'],False),
('meals','Eating-out foods','checkbox',['Pizza','Burger','Sandwich','Chinese','Indian food','South Indian','Chaat','Fried food','Desserts','Bakery','Healthy meals','Other'],False),
('meals','How often do you eat outside?','mcq',['Never','Less than once/week','1–2 times/week','3–4 times/week','5–6 times/week','Daily'],True),
('lifestyle','Daily water intake','mcq',['Less than 500 ml','500 ml–1 L','1–1.5 L','1.5–2 L','2–2.5 L','2.5–3 L','More than 3 L','Don’t know'],True),
('lifestyle','Sleep duration','mcq',['Less than 4 hours','4–5','5–6','6–7','7–8','8–9','9+'],True),
('lifestyle','Sleep quality','rating',['1','2','3','4','5','6','7','8','9','10'],True),
('lifestyle','Current physical activity','checkbox',['Walking','Gym','Yoga','Pilates','Running','Cycling','Swimming','Dancing','Sports','Home workout','Household work','None','Other'],False),
('lifestyle','Exercise frequency','mcq',['Never','1 day/week','2 days','3 days','4 days','5 days','6 days','Every day'],True),
('health','Existing health conditions','checkbox',['Diabetes','Prediabetes','PCOS','Thyroid','High cholesterol','High blood pressure','Fatty liver','Kidney condition','Heart condition','Asthma','Arthritis','Migraine','Anaemia','Digestive condition','Skin condition','Hormonal condition','None','Other'],False),
('health','Allergies/intolerances','checkbox',['Milk','Gluten','Nuts','Peanuts','Soy','Eggs','Seafood','Medication allergy','None','Other'],False),
('health','Current medication categories','checkbox',['None','Diabetes medication','BP medication','Cholesterol medication','Thyroid medication','Hormonal medication','Pain medication','Other'],False),
('health','Barriers to healthy eating','checkbox',['Lack of time','Work schedule','Family','Cravings','Stress','Eating outside','Lack of planning','Lack of cooking','Cost','Travel','Social events','Low motivation','Boredom','Other'],False),
('preferences','Preferred diet-plan style','mcq',['Very simple','Quick recipes','Traditional home food','Variety every day','Repeating meals is okay','Flexible plan','Detailed plan','Other'],True),
('preferences','Preferred number of meals','mcq',['2','3','4','5','Flexible'],True),
('preferences','What matters most?','checkbox',['Taste','Convenience','Cost','Variety','Health','Weight loss','Family-friendly meals','Quick preparation','Other'],False),
('final','Anything important that was not covered?','long',None,False),
]
SECTIONS={'basic':'About you','goals':'Goals & motivation','schedule':'Daily schedule','food':'Food preferences','meals':'Meals & eating habits','lifestyle':'Water, sleep & activity','health':'Health information','preferences':'Your coaching preferences','final':'Anything else'}

SCHEMA='''
CREATE TABLE IF NOT EXISTS admin(id INTEGER PRIMARY KEY, username TEXT UNIQUE, password_hash TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS clients(id INTEGER PRIMARY KEY AUTOINCREMENT, client_code TEXT UNIQUE NOT NULL, name TEXT NOT NULL, phone TEXT, email TEXT, city TEXT, age INTEGER, gender TEXT, status TEXT DEFAULT 'New', created_at TEXT NOT NULL, notes TEXT);
CREATE TABLE IF NOT EXISTS submissions(id INTEGER PRIMARY KEY AUTOINCREMENT, client_id INTEGER NOT NULL, submitted_at TEXT NOT NULL, answers_json TEXT NOT NULL, FOREIGN KEY(client_id) REFERENCES clients(id) ON DELETE CASCADE);
CREATE TABLE IF NOT EXISTS measurements(id INTEGER PRIMARY KEY AUTOINCREMENT, client_id INTEGER NOT NULL, measured_at TEXT NOT NULL, weight REAL, height REAL, waist REAL, hip REAL, body_fat REAL, custom_name TEXT, custom_value TEXT, notes TEXT, FOREIGN KEY(client_id) REFERENCES clients(id) ON DELETE CASCADE);
CREATE TABLE IF NOT EXISTS files(id INTEGER PRIMARY KEY AUTOINCREMENT, client_id INTEGER NOT NULL, category TEXT NOT NULL, original_name TEXT NOT NULL, stored_name TEXT NOT NULL, uploaded_at TEXT NOT NULL, notes TEXT, FOREIGN KEY(client_id) REFERENCES clients(id) ON DELETE CASCADE);
CREATE TABLE IF NOT EXISTS payments(id INTEGER PRIMARY KEY AUTOINCREMENT, client_id INTEGER NOT NULL, amount REAL NOT NULL, paid_at TEXT NOT NULL, method TEXT, status TEXT, notes TEXT, FOREIGN KEY(client_id) REFERENCES clients(id) ON DELETE CASCADE);
CREATE TABLE IF NOT EXISTS feedback(id INTEGER PRIMARY KEY AUTOINCREMENT, client_id INTEGER NOT NULL, kind TEXT NOT NULL, text TEXT, file_id INTEGER, created_at TEXT NOT NULL, FOREIGN KEY(client_id) REFERENCES clients(id) ON DELETE CASCADE);
'''

def get_db():
    c=sqlite3.connect(DB); c.row_factory=sqlite3.Row; c.execute('PRAGMA foreign_keys=ON'); return c

def init_db():
    c=get_db(); c.executescript(SCHEMA)
    if not c.execute('SELECT 1 FROM admin LIMIT 1').fetchone(): c.execute('INSERT INTO admin(username,password_hash) VALUES(?,?)',('admin',generate_password_hash(ADMIN_PASSWORD)))
    c.commit(); c.close()

def csrf():
    session.setdefault('csrf',secrets.token_urlsafe(24)); return session['csrf']
def csrf_valid(): return hmac.compare_digest(request.form.get('_csrf',''),session.get('csrf',''))
def auth(f):
    @wraps(f)
    def w(*a,**k):
        if not session.get('admin'): return redirect(url_for('login'))
        return f(*a,**k)
    return w

def now(): return datetime.now().strftime('%Y-%m-%d %H:%M')

def save_file(client_id, category, f, notes=''):
    if not f or not f.filename: return None
    ext=f.filename.rsplit('.',1)[-1].lower() if '.' in f.filename else ''
    if ext not in ALLOWED: return None
    stored=secrets.token_hex(20)+'.'+ext
    f.save(UPLOADS/stored)
    c=get_db(); c.execute('INSERT INTO files(client_id,category,original_name,stored_name,uploaded_at,notes) VALUES(?,?,?,?,?,?)',(client_id,category,secure_filename(f.filename),stored,now(),notes)); fid=c.execute('SELECT last_insert_rowid()').fetchone()[0]; c.commit(); c.close(); return fid

@app.context_processor
def inject(): return {'csrf':csrf(),'sections':SECTIONS}

@app.after_request
def security_headers(r):
    r.headers['X-Content-Type-Options']='nosniff'; r.headers['X-Frame-Options']='DENY'; r.headers['Referrer-Policy']='no-referrer'; r.headers['Cache-Control']='no-store'; return r

@app.route('/login',methods=['GET','POST'])
def login():
    if request.method=='POST':
        c=get_db(); a=c.execute('SELECT * FROM admin WHERE username=?',('admin',)).fetchone(); c.close()
        if a and check_password_hash(a['password_hash'],request.form.get('password','')):
            session.clear(); session['admin']=True; session['csrf']=secrets.token_urlsafe(24); return redirect(url_for('dashboard'))
        flash('Incorrect password.')
    return render_template('login.html')
@app.route('/logout')
def logout(): session.clear(); return redirect(url_for('login'))
@app.route('/')
def root(): return redirect(url_for('dashboard') if session.get('admin') else url_for('login'))

@app.route('/dashboard')
@auth
def dashboard():
    c=get_db(); stats=[c.execute('SELECT COUNT(*) FROM clients').fetchone()[0],c.execute('SELECT COUNT(*) FROM submissions').fetchone()[0],c.execute("SELECT COUNT(*) FROM clients WHERE status='Active'").fetchone()[0],c.execute("SELECT COALESCE(SUM(amount),0) FROM payments WHERE status='Pending'").fetchone()[0]]; recent=c.execute('SELECT * FROM clients ORDER BY id DESC LIMIT 8').fetchall(); c.close(); return render_template('dashboard.html',stats=stats,recent=recent)

@app.route('/clients')
@auth
def clients():
    q=request.args.get('q','').strip(); c=get_db(); rows=c.execute('SELECT * FROM clients WHERE name LIKE ? OR client_code LIKE ? ORDER BY id DESC',(f'%{q}%',f'%{q}%')).fetchall() if q else c.execute('SELECT * FROM clients ORDER BY id DESC').fetchall(); c.close(); return render_template('clients.html',clients=rows,q=q)

@app.route('/client/new',methods=['GET','POST'])
@auth
def client_new():
    if request.method=='POST':
        if not csrf_valid(): abort(400)
        code='HC-'+secrets.token_hex(4).upper(); c=get_db(); c.execute('INSERT INTO clients(client_code,name,phone,email,city,age,gender,status,created_at,notes) VALUES(?,?,?,?,?,?,?,?,?,?)',(code,request.form['name'],request.form.get('phone'),request.form.get('email'),request.form.get('city'),request.form.get('age') or None,request.form.get('gender'),request.form.get('status','Active'),now(),request.form.get('notes'))); cid=c.execute('SELECT last_insert_rowid()').fetchone()[0]; c.commit(); c.close(); return redirect(url_for('client',cid=cid))
    return render_template('client_new.html')

@app.route('/client/<int:cid>')
@auth
def client(cid):
    c=get_db(); cl=c.execute('SELECT * FROM clients WHERE id=?',(cid,)).fetchone();
    if not cl: abort(404)
    data={k:c.execute(q,(cid,)).fetchall() for k,q in {'measurements':'SELECT * FROM measurements WHERE client_id=? ORDER BY id DESC','files':'SELECT * FROM files WHERE client_id=? ORDER BY id DESC','payments':'SELECT * FROM payments WHERE client_id=? ORDER BY id DESC','feedback':'SELECT * FROM feedback WHERE client_id=? ORDER BY id DESC','submissions':'SELECT * FROM submissions WHERE client_id=? ORDER BY id DESC'}.items()}; c.close(); return render_template('client.html',client=cl,**data)

@app.route('/form')
def form(): return render_template('form.html',questions=QUESTIONS)
@app.route('/form/submit',methods=['POST'])
def form_submit():
    if not request.form.get('full_name','').strip() or not request.form.get('phone_number','').strip(): return render_template('thanks.html',error='Please go back and enter your name and phone number.')
    answers={}
    for sec,q,typ,opts,req in QUESTIONS:
        key=q.lower().replace(' ','_').replace('/','_')
        vals=request.form.getlist(key)
        if vals: answers[q]=vals if len(vals)>1 else vals[0]
        other=request.form.get(key+'_other','').strip()
        if other: answers[q+' — Other']=other
    c=get_db(); code='HC-'+secrets.token_hex(4).upper(); c.execute('INSERT INTO clients(client_code,name,phone,email,city,age,gender,status,created_at) VALUES(?,?,?,?,?,?,?,?,?)',(code,request.form.get('full_name'),request.form.get('phone_number'),request.form.get('email'),request.form.get('city'),request.form.get('age') or None,request.form.get('gender'),'New Intake',now())); cid=c.execute('SELECT last_insert_rowid()').fetchone()[0]; c.execute('INSERT INTO submissions(client_id,submitted_at,answers_json) VALUES(?,?,?)',(cid,now(),json.dumps(answers,ensure_ascii=False))); c.commit(); c.close(); return render_template('thanks.html')

@app.route('/submission/<int:sid>')
@auth
def submission(sid):
    c=get_db(); s=c.execute('SELECT s.*,cl.name,cl.client_code,cl.id cid FROM submissions s JOIN clients cl ON cl.id=s.client_id WHERE s.id=?',(sid,)).fetchone(); c.close();
    if not s: abort(404)
    return render_template('submission.html',s=s,answers=json.loads(s['answers_json']))

@app.route('/measurement/new',methods=['GET','POST'])
@auth
def measurement_new():
    cid=request.args.get('client',request.form.get('client_id'))
    if request.method=='POST':
        if not csrf_valid(): abort(400)
        c=get_db(); c.execute('INSERT INTO measurements(client_id,measured_at,weight,height,waist,hip,body_fat,custom_name,custom_value,notes) VALUES(?,?,?,?,?,?,?,?,?,?)',(cid,request.form['measured_at'],request.form.get('weight') or None,request.form.get('height') or None,request.form.get('waist') or None,request.form.get('hip') or None,request.form.get('body_fat') or None,request.form.get('custom_name'),request.form.get('custom_value'),request.form.get('notes'))); c.commit(); c.close(); return redirect(url_for('client',cid=cid))
    return render_template('measurement.html',cid=cid)

@app.route('/upload',methods=['GET','POST'])
@auth
def upload():
    cid=request.args.get('client',request.form.get('client_id'))
    if request.method=='POST':
        if not csrf_valid(): abort(400)
        for f in request.files.getlist('files'): save_file(cid,request.form.get('category','Other'),f,request.form.get('notes',''))
        return redirect(url_for('client',cid=cid))
    return render_template('upload.html',cid=cid)
@app.route('/file/<int:fid>')
@auth
def file_view(fid):
    c=get_db(); f=c.execute('SELECT * FROM files WHERE id=?',(fid,)).fetchone(); c.close();
    if not f: abort(404)
    return send_from_directory(UPLOADS,f['stored_name'],as_attachment=False,download_name=f['original_name'])

@app.route('/payment/new',methods=['GET','POST'])
@auth
def payment_new():
    cid=request.args.get('client',request.form.get('client_id'))
    if request.method=='POST':
        if not csrf_valid(): abort(400)
        c=get_db(); c.execute('INSERT INTO payments(client_id,amount,paid_at,method,status,notes) VALUES(?,?,?,?,?,?)',(cid,request.form['amount'],request.form['paid_at'],request.form.get('method'),request.form.get('status'),request.form.get('notes'))); c.commit(); c.close(); return redirect(url_for('client',cid=cid))
    return render_template('payment.html',cid=cid)

@app.route('/feedback/new',methods=['GET','POST'])
@auth
def feedback_new():
    cid=request.args.get('client',request.form.get('client_id'))
    if request.method=='POST':
        if not csrf_valid(): abort(400)
        fid=None
        if request.files.get('video') and request.files['video'].filename: fid=save_file(cid,'Video feedback',request.files['video'])
        c=get_db(); c.execute('INSERT INTO feedback(client_id,kind,text,file_id,created_at) VALUES(?,?,?,?,?)',(cid,request.form['kind'],request.form.get('text'),fid,now())); c.commit(); c.close(); return redirect(url_for('client',cid=cid))
    return render_template('feedback.html',cid=cid)

@app.route('/reports')
@auth
def reports():
    c=get_db(); rows=c.execute('SELECT f.*,cl.name FROM files f JOIN clients cl ON cl.id=f.client_id ORDER BY f.id DESC').fetchall(); c.close(); return render_template('reports.html',files=rows)
@app.route('/measurements')
@auth
def measurements():
    c=get_db(); rows=c.execute('SELECT m.*,cl.name FROM measurements m JOIN clients cl ON cl.id=m.client_id ORDER BY m.id DESC').fetchall(); c.close(); return render_template('measurements.html',rows=rows)
@app.route('/payments')
@auth
def payments():
    c=get_db(); rows=c.execute('SELECT p.*,cl.name FROM payments p JOIN clients cl ON cl.id=p.client_id ORDER BY p.id DESC').fetchall(); c.close(); return render_template('payments.html',rows=rows)
@app.route('/feedback')
@auth
def feedback():
    c=get_db(); rows=c.execute('SELECT f.*,cl.name FROM feedback f JOIN clients cl ON cl.id=f.client_id ORDER BY f.id DESC').fetchall(); c.close(); return render_template('feedback.html',rows=rows)

init_db()
if __name__=='__main__': app.run(host='127.0.0.1',port=int(os.environ.get('PORT',5000)),debug=False)
