import openai
from flask import Flask, render_template, request, redirect, url_for, session
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from functools import wraps

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///adolescentes.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = '123456'
db = SQLAlchemy(app)

class PG(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100), nullable=False)
    adolescentes = db.relationship('Adolescente', backref='pg', lazy=True)

    def __init__(self, nome):
        self.nome = nome

class Adolescente(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100), nullable=False)
    idade = db.Column(db.Integer, nullable=False)
    data_nascimento = db.Column(db.Date, nullable=False)
    genero = db.Column(db.String(10), nullable=False)
    pg_id = db.Column(db.Integer, db.ForeignKey('PG.id'), nullable=False)
    imperio = db.Column(db.String(50), nullable=False)

    def __init__(self, nome, idade, data_nascimento, genero, pg_id, imperio):
        self.nome = nome
        self.idade = idade
        self.data_nascimento = data_nascimento
        self.genero = genero
        self.pg_id = pg_id
        self.imperio = imperio

class AdolescenteFactory:
    @staticmethod
    def create_adolescente(nome, idade, data_nascimento, genero, pg_id, imperio):
        return Adolescente(nome=nome, idade=idade, data_nascimento=data_nascimento, genero=genero, pg_id=pg_id, imperio=imperio)

class AdolescenteFacade:
    @staticmethod
    def add_adolescente(adolescente):
        db.session.add(adolescente)
        db.session.commit()

    @staticmethod
    def get_adolescente_by_id(id):
        return Adolescente.query.get(id)

    @staticmethod
    def update_adolescente(adolescente):
        db.session.commit()

    @staticmethod
    def delete_adolescente(adolescente):
        db.session.delete(adolescente)
        db.session.commit()

class Observer:
    def __init__(self):
        self._total_adolescentes = 0

    def update(self):
        self._total_adolescentes = Adolescente.query.count()

observer = Observer()



def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'logged_in' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

@app.route('/')
@login_required
def index():
    adolescentes = Adolescente.query.join(PG).order_by(Adolescente.nome).add_columns(
        Adolescente.id, Adolescente.nome, Adolescente.idade, Adolescente.data_nascimento, Adolescente.genero, PG.nome.label('pg_nome'), Adolescente.imperio
    ).all()
    observer.update() 
    total_adolescentes = observer._total_adolescentes  
    return render_template('index.html', adolescentes=adolescentes, total_adolescentes=total_adolescentes)



@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        if request.form['username'] == 'Equipe2024' and request.form['password'] == '123456':
            session['logged_in'] = True
            return redirect(url_for('index'))
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.pop('logged_in', None)
    return redirect(url_for('login'))

@app.route('/adolescente', methods=['GET', 'POST'])
@app.route('/adolescente/<int:id>', methods=['GET', 'POST'])
@login_required
def adolescente(id=None):
    if id:
        adolescente = AdolescenteFacade.get_adolescente_by_id(id)
    else:
        adolescente = None

    pgs = PG.query.all()

    if request.method == 'POST':
        nome = request.form['nome']
        idade = request.form['idade']
        data_nascimento = datetime.strptime(request.form['data_nascimento'], '%Y-%m-%d')
        genero = request.form['genero']
        pg_id = request.form['pg_id']
        imperio = request.form['imperio']

        if adolescente:
            adolescente.nome = nome
            adolescente.idade = idade
            adolescente.data_nascimento = data_nascimento
            adolescente.genero = genero
            adolescente.pg_id = pg_id
            adolescente.imperio = imperio
            AdolescenteFacade.update_adolescente(adolescente)
        else:
            novo_adolescente = AdolescenteFactory.create_adolescente(nome, idade, data_nascimento, genero, pg_id, imperio)
            AdolescenteFacade.add_adolescente(novo_adolescente)

        return redirect('/')

    return render_template('adolescente.html', adolescente=adolescente, pgs=pgs)

@app.route('/cadastrar_pg', methods=['POST'])
@login_required
def cadastrar_pg():
    nome = request.form['nome_pg']
    novo_pg = PG(nome=nome)
    db.session.add(novo_pg)
    db.session.commit()
    return redirect(url_for('index'))

@app.route('/excluir/<int:id>')
@login_required
def excluir(id):
    adolescente = AdolescenteFacade.get_adolescente_by_id(id)
    AdolescenteFacade.delete_adolescente(adolescente)
    return redirect('/')

openai.api_key = ""

def get_chatgpt_response(prompt):
  response = openai.ChatCompletion.create(
    model="gpt-3.5-turbo",
    messages=[
          {"role": "system", "content": "Faça um roteiro, incluindo 3 perguntas para um estudo bíblico de adolescentes de acordo com o tema apresentado"},
          {"role": "user", "content": prompt}
      ]
  )
  return response.choices[0].message['content']

@app.route('/chatgpt', methods=['POST'])
@login_required
def chatgpt():
    tema = request.form['tema']
    perguntas = get_chatgpt_response(tema)
    perguntas = perguntas.split('\n')
    return render_template('index.html', perguntas=perguntas, adolescentes=Adolescente.query.all())

if __name__ == '__main__':
    db.create_all()
    app.run(debug=True)
