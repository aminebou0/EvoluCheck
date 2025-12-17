import os
import requests  # Indispensable pour n8n
from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for, session, make_response, flash
from flask_sqlalchemy import SQLAlchemy
from dotenv import load_dotenv
from openai import OpenAI
from fpdf import FPDF
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import io
import base64
import tempfile

# 1. Chargement des variables d'environnement
load_dotenv()

# 2. Configuration de l'application Flask
app = Flask(__name__)
app.config['SECRET_KEY'] = 'audit_s2i_dimension6_secret_key'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///evolucheck.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# FIX POUR PYTHONANYWHERE (HTTPS)
from werkzeug.middleware.proxy_fix import ProxyFix
app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)

# Initialisation BDD et Services
db = SQLAlchemy(app)
from authlib.integrations.flask_client import OAuth

oauth = OAuth(app)
oauth.register(
    name='google',
    client_id=os.getenv('GOOGLE_CLIENT_ID'),
    client_secret=os.getenv('GOOGLE_CLIENT_SECRET'),
    server_metadata_url='https://accounts.google.com/.well-known/openid-configuration',
    client_kwargs={'scope': 'openid email profile'}
)

api_key = os.getenv("OPENAI_API_KEY")
client = OpenAI(api_key=api_key) if api_key else None

# --- MODÈLE DE BASE DE DONNÉES ---
class Audit(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    date_audit = db.Column(db.DateTime, default=datetime.utcnow)
    user_email = db.Column(db.String(100))
    score_adaptabilite = db.Column(db.Float)
    score_innovation = db.Column(db.Float)
    score_durabilite = db.Column(db.Float)
    score_global = db.Column(db.Float)
    diagnostic_type = db.Column(db.String(20))
    recommandations = db.Column(db.Text)
    # Nouveaux KPIs Avancés
    dette_technique = db.Column(db.String(20)) # 'faible', 'moyenne', 'critique'
    taux_transformation_poc = db.Column(db.Float) # %
    part_energie_verte = db.Column(db.Float) # %

# --- LOGIQUE MÉTIER & CALCULS ---

def analyser_risques(inputs):
    """
    LOGIQUE MATRICE DE FARMER (PROBABILITÉ x IMPACT)
    Retourne des coordonnées (1-3) pour placer les points sur la grille.
    """
    risques = []

    # Risque 1 : Vendor Lock-in (Dépendance)
    if inputs['dep'] > 25:
        risques.append({
            "nom": "Vendor Lock-in Critique",
            "prob": 3, "impact": 3 # Zone Rouge (3,3)
        })
    elif inputs['dep'] > 10:
        risques.append({
            "nom": "Dépendance Fournisseur",
            "prob": 2, "impact": 2 # Zone Jaune (2,2)
        })

    # Risque 2 : Obsolescence (Temps de déploiement)
    if inputs['temps'] > 20:
        risques.append({
            "nom": "Obsolescence SI",
            "prob": 3, "impact": 2 # Zone Orange (3,2)
        })

    # Risque 3 : Non-conformité Green IT (PUE)
    if inputs['pue'] > 1.5:
        risques.append({
            "nom": "Non-conformité RSE",
            "prob": 2, "impact": 3 # Zone Orange (2,3)
        })

    # Risque 4 : Manque d'Innovation
    if inputs['rd'] < 2:
        risques.append({
            "nom": "Perte Compétitivité",
            "prob": 2, "impact": 2 # Zone Jaune (2,2)
        })

    return risques

def generer_diagnostic(global_score, s_adapt, s_innov, s_dura, inputs=None):
    """Génère le constat textuel (FRAP/FRABOP) et des recommandations détaillées"""
    diag = {}
    if global_score <= 60:
        diag['type'] = "FRAP (Problème Majeur)"
        diag['message'] = "Risque critique d'obsolescence. Le SI ne répond pas aux standards de la Dimension 6."
        diag['color'] = "danger"
    elif global_score >= 80:
        diag['type'] = "FRABOP (Bonne Pratique)"
        diag['message'] = "Excellente maturité. Le SI est résilient, innovant et durable."
        diag['color'] = "success"
    else:
        diag['type'] = "Constat d'Amélioration"
        diag['message'] = "Niveau moyen. Des optimisations sont nécessaires pour garantir l'évolution."
        diag['color'] = "warning"

    # Recommandations ciblées et étendues
    recos = []
    
    # Adaptabilité
    if s_adapt < 3: 
        recos.append({"titre": "Urgence Adaptabilité", "texte": "Réduire la dette technique et le temps de déploiement."})
    if inputs and inputs.get('arch') == 'non':
        recos.append({"titre": "Architecture Monolithique", "texte": "Migrer progressivement vers une architecture modulaire (Microservices/API) pour gagner en agilité."})
    if inputs and inputs.get('dette') == 'critique':
        recos.append({"titre": "Dette Technique Critique", "texte": "Planifier un sprint de refactoring immédiat. La dette technique freine toute évolution."})

    # Innovation
    if s_innov < 3: 
        recos.append({"titre": "Déficit Innovation", "texte": "Augmenter le budget R&D (> 5%)."})
    if inputs and inputs.get('poc', 0) < 2:
        recos.append({"titre": "Culture de l'Expérimentation", "texte": "Lancer au moins 2 PoC (Proof of Concept) par an pour tester de nouvelles technologies."})
    if inputs and inputs.get('taux_transfo', 0) < 20:
        recos.append({"titre": "Transformation des Idées", "texte": "Améliorer le processus d'industrialisation des PoC. Trop d'initiatives restent au stade de prototype."})

    # Durabilité
    if s_dura < 3: 
        recos.append({"titre": "Alerte Green IT", "texte": "PUE critique (> 1.4). Audit énergétique requis."})
    if inputs and inputs.get('rec') == 'non':
        recos.append({"titre": "Cycle de Vie Matériel", "texte": "Mettre en place une politique de recyclage et d'achat reconditionné pour le matériel IT."})
    if inputs and inputs.get('energie_verte', 0) < 30:
        recos.append({"titre": "Transition Énergétique", "texte": "Basculer une partie de l'hébergement vers des fournisseurs d'énergie renouvelable."})
    
    diag['recos'] = recos
    return diag

# --- FONCTION D'ENVOI AUTOMATISÉE N8N ---
def envoyer_alerte_n8n(data_audit):
    """
    Envoie les données de l'audit à n8n via un Webhook.
    """
    # 1. VOTRE URL N8N SPÉCIFIQUE
    N8N_WEBHOOK_URL = "https://amineboubou12.app.n8n.cloud/webhook-test/audit-alert"
    
    print(f"--- Tentative d'envoi vers n8n (URL: {N8N_WEBHOOK_URL}) ---")
    
    # 2. Préparation des données à envoyer (Payload JSON)
    # Ajout de l'email pour le coaching IA
    payload = {
        "timestamp": datetime.now().isoformat(),
        "auditeur": data_audit.get('user', 'Inconnu'),
        "email": data_audit.get('email', 'non-renseigne'), # Pour l'envoi d'email
        "score_global": data_audit['global'],
        "diagnostic_type": data_audit['diag']['type'],
        "message": data_audit['diag']['message'],
        "scores_detailles": {
            "adaptabilite": data_audit['scores_radar'][0],
            "innovation": data_audit['scores_radar'][1],
            "durabilite": data_audit['scores_radar'][2]
        },
        "recommandations": [r['titre'] for r in data_audit['diag'].get('recos', [])],
        "nombre_risques": len(data_audit.get('risques', [])),
        # Ajout des données brutes manquantes pour l'IA n8n
        "rd": data_audit.get('rd'),
        "pue": data_audit.get('pue'),
        "dette": data_audit.get('dette'),
        "dep": data_audit.get('dep'),
        "temps": data_audit.get('temps'),
        "arch": data_audit.get('arch'),
        "poc": data_audit.get('poc'),
        "rec": data_audit.get('rec'),
        "taux_transfo": data_audit.get('taux_transfo'),
        "energie_verte": data_audit.get('energie_verte')
    }
    
    try:
        # 3. Envoi réel
        response = requests.post(N8N_WEBHOOK_URL, json=payload)
        
        if response.status_code == 200:
            print("✅ SUCCÈS : n8n a bien reçu les données !")
        else:
            print(f"⚠️ AVERTISSEMENT : n8n a répondu avec le code {response.status_code}")
            # print(f"Réponse n8n : {response.text}")
            
    except Exception as e:
        print(f"❌ ERREUR DE CONNEXION N8N : {e}")

# --- GÉNÉRATION GRAPHIQUES SERVEUR (MATPLOTLIB) ---

def generer_image_radar(scores):
    """
    Génère un graphique Radar pour les 3 piliers.
    Retourne le chemin du fichier temporaire ou un objet BytesIO.
    """
    labels = ['Adaptabilité', 'Innovation', 'Durabilité']
    num_vars = len(labels)

    # Calcul des angles
    angles = [n / float(num_vars) * 2 * 3.14159 for n in range(num_vars)]
    angles += angles[:1] # Fermer la boucle

    scores_closed = scores + scores[:1] # Fermer la boucle

    fig, ax = plt.subplots(figsize=(6, 6), subplot_kw=dict(polar=True))
    
    # Couleurs personnalisées pour le PDF (Nouveau Vert Tech)
    ax.plot(angles, scores_closed, linewidth=2, linestyle='solid', color='#10B981') # Nouveau Vert
    ax.fill(angles, scores_closed, '#10B981', alpha=0.20) # Vert transparent
    
    ax.set_yticklabels([])
    ax.set_xticks(angles[:-1])
    ax.set_xticklabels(labels, size=12, color='#424242')
    
    # Sauvegarde en mémoire
    img_io = io.BytesIO()
    plt.savefig(img_io, format='png', bbox_inches='tight', transparent=True)
    img_io.seek(0)
    plt.close()
    return img_io

def generer_image_farmer(risques):
    """
    Génère la Matrice de Farmer (3x3) avec les points de risque.
    """
    fig, ax = plt.subplots(figsize=(6, 6))
    
    # Fond coloré (Zones) - Couleurs plus douces
    # Zone Verte (Faible)
    ax.add_patch(plt.Rectangle((1, 1), 1, 1, color='#E8F5E9', alpha=0.9)) # (1,1)
    ax.add_patch(plt.Rectangle((2, 1), 1, 1, color='#E8F5E9', alpha=0.9)) # (2,1)
    ax.add_patch(plt.Rectangle((1, 2), 1, 1, color='#E8F5E9', alpha=0.9)) # (1,2)
    
    # Zone Jaune (Moyen)
    ax.add_patch(plt.Rectangle((3, 1), 1, 1, color='#FFFDE7', alpha=0.9)) # (3,1)
    ax.add_patch(plt.Rectangle((2, 2), 1, 1, color='#FFFDE7', alpha=0.9)) # (2,2)
    ax.add_patch(plt.Rectangle((1, 3), 1, 1, color='#FFFDE7', alpha=0.9)) # (1,3)
    
    # Zone Rouge (Fort)
    ax.add_patch(plt.Rectangle((3, 2), 1, 1, color='#FFEBEE', alpha=0.9)) # (3,2)
    ax.add_patch(plt.Rectangle((2, 3), 1, 1, color='#FFEBEE', alpha=0.9)) # (2,3)
    ax.add_patch(plt.Rectangle((3, 3), 1, 1, color='#FFEBEE', alpha=0.9)) # (3,3)

    # Configuration des axes
    ax.set_xlim(1, 4)
    ax.set_ylim(1, 4)
    ax.set_xticks([1.5, 2.5, 3.5])
    ax.set_xticklabels(['Faible', 'Moyen', 'Fort'], color='#616161')
    ax.set_yticks([1.5, 2.5, 3.5])
    ax.set_yticklabels(['Faible', 'Moyen', 'Fort'], color='#616161')
    ax.set_xlabel('Impact', color='#424242')
    ax.set_ylabel('Probabilité', color='#424242')
    ax.set_title('Matrice de Farmer', color='#2E7D32')
    
    # Placement des points
    for r in risques:
        # On centre les points dans les cases (ex: niveau 1 -> 1.5)
        x = r['impact'] + 0.5
        y = r['prob'] + 0.5
        # Petit décalage aléatoire pour éviter la superposition si même case (optionnel, ici simple)
        ax.plot(x, y, marker='o', markersize=12, color='#C62828') # Rouge foncé
        ax.text(x, y+0.15, r['nom'], fontsize=8, ha='center', color='#424242')

    img_io = io.BytesIO()
    plt.savefig(img_io, format='png', bbox_inches='tight', transparent=True)
    img_io.seek(0)
    plt.close()
    return img_io

def get_ai_response(msg, context=None):
    """Chatbot Intelligent via OpenAI avec Contexte Audit"""
    if not client: return "Erreur : Clé API non configurée dans le fichier .env"
    try:
        system_prompt = (
            "Tu es 'EvoluBot', l'expert senior en audit informatique (SI) spécialisé dans le référentiel AuditS2I, "
            "la norme ISO 23894 (Gestion des risques IA) et le Green IT (FinOps/PUE). "
            "Ton ton est professionnel, précis, mais pédagogique. Tu vouvoies l'utilisateur. "
            "Tes réponses doivent être structurées et courtes. Ne parle QUE d'audit, de tech et de management SI."
        )
        
        if context:
            system_prompt += f"\n\nCONTEXTE DE L'AUDIT UTILISATEUR :\n{context}\n\nUtilise ces données pour personnaliser tes réponses."

        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "system", "content": system_prompt}, {"role": "user", "content": msg}],
            temperature=0.7, max_tokens=250
        )
        return response.choices[0].message.content
    except Exception as e: return f"Erreur IA : {str(e)}"

# --- ROUTES DE NAVIGATION ---

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/about')
def about():
    team = [
        {
            "name": "BOUBOU Mohammed Amine",
            "role": "Étudiant en Master d'Excellence MS2I",
            "image": url_for('static', filename='img/team/amine.png'),
            "socials": {
                "linkedin": "https://www.linkedin.com/in/mohammed-amine-boubou-32a249223/",
                "github": "https://github.com/aminebou0",
                "email": "amineboubou02@gmail.com"
            }
        },
        {
            "name": "EL-BAKKALI Aya",
            "role": "Étudiante en Master d'Excellence MS2I",
            "image": url_for('static', filename='img/team/aya.png'),
            "socials": {
                "linkedin": "https://www.linkedin.com/in/aya-el-bakkali-b2692630a/",
                "email": "eaya78726@gmail.com"
            }
        },
        {
            "name": "AMHAJJAR Hiba",
            "role": "Étudiante en Master d'Excellence MS2I",
            "image": url_for('static', filename='img/team/hiba.jpeg'),
            "socials": {
                "linkedin": "https://www.linkedin.com/in/hiba-amhajjar-21946a361/",
                "email": "hibaamh59@gmail.com"
            }
        },
        {
            "name": "FARAJI Nouhaila",
            "role": "Étudiante en Master d'Excellence MS2I",
            "image": url_for('static', filename='img/team/nouhaila.png'),
            "socials": {
                "linkedin": "https://www.linkedin.com/in/nouhaila-faraji-635943352/",
                "email": "nouhailafaraji7@gmail.com"
            }
        },
        {
            "name": "ZIANI Mariyam",
            "role": "Étudiante en Master d'Excellence MS2I",
            "image": url_for('static', filename='img/team/mariyam.png'),
            "socials": {
                "linkedin": "https://www.linkedin.com/in/mariyam-ziani-7321442b8/",
                "email": "mariyam8ziani@gmail.com"
            }
        },
        {
            "name": "ZERHOUNI Amina",
            "role": "Étudiante en Master d'Excellence MS2I",
            "image": url_for('static', filename='img/team/amina.png'),
            "socials": {
                "linkedin": "https://www.linkedin.com/in/amina-zerhouni-8b1077204/",
                "email": "aminazerhouni78@gmail.com"
            }
        },
        {
            "name": "RAHMANI Said",
            "role": "Étudiant en Master d'Excellence MS2I",
            "image": url_for('static', filename='img/team/said.png'),
            "socials": {
                "linkedin": "https://www.linkedin.com/in/saiid-rahmanii/"
            }
        },
        {
            "name": "LAMRHILI Imad-eddine",
            "role": "Étudiant en Master d'Excellence MS2I",
            "image": url_for('static', filename='img/team/imad.png'),
            "socials": {
                "email": "imadlamrhili71@gmail.com"
            }
        }
    ]
    return render_template('about.html', team=team)

@app.route('/contact')
def contact():
    return render_template('contact.html')

# --- AUTHENTIFICATION ---

@app.route('/login/google')
def login_google():
    redirect_uri = url_for('auth_google_callback', _external=True)
    return oauth.google.authorize_redirect(redirect_uri)

@app.route('/auth/google/callback')
def auth_google_callback():
    token = oauth.google.authorize_access_token()
    user_info = token.get('userinfo')
    if not user_info:
        # Fallback si userinfo n'est pas dans le token
        user_info = oauth.google.userinfo()
        
    session['user'] = user_info.get('name')
    session['email'] = user_info.get('email')
    return redirect(url_for('audit'))

# --- ANCIENNE AUTHENTIFICATION (EMAIL/PASS) ---

@app.route('/auth', methods=['GET', 'POST'])
def auth():
    if request.method == 'POST':
        action = request.form.get('action')
        email = request.form.get('email')
        
        if action == 'register':
            session['user'] = request.form.get('fullname') # Stockage du nom
            session['email'] = email # Stockage de l'email pour n8n
        else:
            session['user'] = email.split('@')[0] # Stockage d'un pseudo
            session['email'] = email # Stockage de l'email pour n8n
            
        return redirect(url_for('audit'))
    return render_template('auth.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))

# --- CŒUR DE L'APPLICATION : AUDIT & DASHBOARD ---

@app.route('/audit', methods=['GET', 'POST'])
def audit():
    if 'user' not in session: return redirect(url_for('auth'))
    
    if request.method == 'POST':
        # 1. Récupération des données du formulaire
        dep = float(request.form.get('dep_fournisseur', 0))
        temps = int(request.form.get('temps_deploy', 30))
        arch = request.form.get('arch_modulaire')
        
        rd = float(request.form.get('budget_rd', 0))
        poc = int(request.form.get('nb_poc', 0))
        
        pue = float(request.form.get('pue', 2.0))
        rec = request.form.get('recyclage')

        # Nouveaux KPIs
        dette = request.form.get('dette_technique', 'moyenne')
        taux_transfo = float(request.form.get('taux_transformation_poc', 0))
        energie_verte = float(request.form.get('part_energie_verte', 0))

        # 2. Calcul des Scores (Logique métier)
        # Adaptabilité (Inversé pour le temps : moins c'est mieux)
        score_a = (2 if dep < 10 else 1) + (2 if temps <= 7 else (1 if temps <= 15 else 0)) + (1 if arch == 'oui' else 0)
        if dette == 'critique': score_a -= 1 # Pénalité Dette Technique

        # Innovation (Plafonné pour PoC)
        score_i = (3 if rd >= 5 else (1 if rd >= 2 else 0)) + min(poc, 2)
        if taux_transfo > 40: score_i = min(score_i + 1, 5) # Bonus Transformation

        # Durabilité (Green IT)
        score_d = (3 if pue <= 1.4 else (1 if pue <= 1.6 else 0)) + (2 if rec == 'oui' else 0)
        if energie_verte > 50: score_d = min(score_d + 1, 5) # Bonus Énergie Verte

        # Score Global sur 100
        global_score = round(((score_a + score_i + score_d) / 15) * 100, 1)
        
        # 3. Génération des analyses
        inputs = {'dep': dep, 'temps': temps, 'arch': arch, 'rd': rd, 'poc': poc, 'pue': pue, 'rec': rec, 'dette': dette, 'taux_transfo': taux_transfo, 'energie_verte': energie_verte}
        diag = generer_diagnostic(global_score, score_a, score_i, score_d, inputs)
        
        risques = analyser_risques(inputs) # Appel à la nouvelle fonction Farmer

        # 4. Stockage en session
        session['last_audit'] = {
            'scores_radar': [score_a, score_i, score_d],
            'global': global_score,
            'diag': diag,
            'risques': risques,
            'date': datetime.now().strftime("%d/%m/%Y"),
            'user': session.get('user', 'Anonyme'),
            'email': session.get('email', 'non-renseigne'), # Ajout Email
            # Données Brutes pour le Rapport
            'dep': dep, 'temps': temps, 'arch': arch,
            'rd': rd, 'poc': poc,
            'pue': pue, 'rec': rec,
            'dette': dette, 'taux_transfo': taux_transfo, 'energie_verte': energie_verte
        }
        
        # 5. DÉCLENCHEMENT DE L'AUTOMATISATION N8N
        envoyer_alerte_n8n(session['last_audit'])
        
        return redirect(url_for('dashboard'))

    return render_template('audit.html')

@app.route('/import_csv', methods=['POST'])
def import_csv():
    if 'file' not in request.files:
        flash("Aucun fichier sélectionné.", "error")
        return redirect(url_for('audit'))
    
    file = request.files['file']
    if file.filename == '':
        flash("Nom de fichier vide.", "error")
        return redirect(url_for('audit'))

    if file:
        try:
            # Lecture du CSV
            df = pd.read_csv(file)
            
            last_audit_data = None
            
            # Itération sur chaque ligne
            for index, row in df.iterrows():
                try:
                    # Extraction des données (avec valeurs par défaut si manquant)
                    dep = float(row.get('dep_fournisseur', 0))
                    temps = int(row.get('temps_deploy', 30))
                    arch = str(row.get('arch_modulaire', 'non')).lower()
                    
                    rd = float(row.get('budget_rd', 0))
                    poc = int(row.get('nb_poc', 0))
                    
                    pue = float(row.get('pue', 2.0))
                    rec = str(row.get('recyclage', 'non')).lower()

                    # Nouveaux KPIs Import
                    dette = str(row.get('dette_technique', 'moyenne')).lower()
                    taux_transfo = float(row.get('taux_transformation', 0))
                    energie_verte = float(row.get('energie_verte', 0))

                    # --- MÊME LOGIQUE DE CALCUL QUE /audit ---
                    # Adaptabilité
                    score_a = (2 if dep < 10 else 1) + (2 if temps <= 7 else (1 if temps <= 15 else 0)) + (1 if arch == 'oui' else 0)
                    if dette == 'critique': score_a -= 1

                    # Innovation
                    score_i = (3 if rd >= 5 else (1 if rd >= 2 else 0)) + min(poc, 2)
                    if taux_transfo > 40: score_i = min(score_i + 1, 5)

                    # Durabilité
                    score_d = (3 if pue <= 1.4 else (1 if pue <= 1.6 else 0)) + (2 if rec == 'oui' else 0)
                    if energie_verte > 50: score_d = min(score_d + 1, 5)

                    global_score = round(((score_a + score_i + score_d) / 15) * 100, 1)
                    
                    inputs = {'dep': dep, 'temps': temps, 'arch': arch, 'rd': rd, 'poc': poc, 'pue': pue, 'rec': rec, 'dette': dette, 'taux_transfo': taux_transfo, 'energie_verte': energie_verte}
                    diag = generer_diagnostic(global_score, score_a, score_i, score_d, inputs)
                    
                    # Création de l'objet Audit pour la BDD
                    new_audit = Audit(
                        user_email=session.get('user', 'Anonyme'),
                        score_adaptabilite=score_a,
                        score_innovation=score_i,
                        score_durabilite=score_d,
                        score_global=global_score,
                        diagnostic_type=diag['type'],
                        recommandations=str(diag['recos']),
                        dette_technique=dette,
                        taux_transformation_poc=taux_transfo,
                        part_energie_verte=energie_verte
                    )
                    db.session.add(new_audit)

                    # Préparation des données pour la session (on gardera la dernière ligne pour le dashboard)
                    risques = analyser_risques(inputs)

                    last_audit_data = {
                        'scores_radar': [score_a, score_i, score_d],
                        'global': global_score,
                        'diag': diag,
                        'risques': risques,
                        'date': datetime.now().strftime("%d/%m/%Y"),
                        'user': session.get('user', 'Anonyme'),
                        'email': session.get('email', 'non-renseigne'), # Ajout Email
                        # Données Brutes
                        'dep': dep, 'temps': temps, 'arch': arch,
                        'rd': rd, 'poc': poc,
                        'pue': pue, 'rec': rec,
                        'dette': dette, 'taux_transfo': taux_transfo, 'energie_verte': energie_verte
                    }
                
                except Exception as e:
                    print(f"Erreur traitement ligne {index}: {e}")
                    continue # On passe à la ligne suivante en cas d'erreur
            
            # Commit unique à la fin pour valider tous les enregistrements
            db.session.commit()
            print(f"✅ Import terminé. {index + 1 if 'index' in locals() else 0} lignes traitées.")
            
            # Mise à jour de la session avec le dernier audit traité
            if last_audit_data:
                session['last_audit'] = last_audit_data
                envoyer_alerte_n8n(session['last_audit'])
                flash("Import CSV réussi ! Redirection vers le tableau de bord.", "success")
                return redirect(url_for('dashboard'))
            else:
                flash("Aucune donnée valide trouvée dans le CSV.", "error")
                return redirect(url_for('audit'))

        except Exception as e:
            print(f"❌ Erreur Import CSV Global : {e}")
            flash(f"Erreur lors de l'import : {str(e)}", "error")
            return redirect(url_for('audit'))

@app.route('/dashboard')
def dashboard():
    if 'last_audit' not in session: return redirect(url_for('audit'))
    return render_template('dashboard.html', data=session['last_audit'])

@app.route('/api/chat', methods=['POST'])
def chat_api():
    data = request.get_json()
    user_msg = data.get('message')
    
    # Construction du contexte si un audit existe
    context_str = None
    if 'last_audit' in session:
        audit = session['last_audit']
        context_str = (
            f"Score Global: {audit['global']}/100. "
            f"Scores Dimensions: Adaptabilité {audit['scores_radar'][0]}/5, "
            f"Innovation {audit['scores_radar'][1]}/5, Durabilité {audit['scores_radar'][2]}/5. "
        )
        # Ajout des risques majeurs
        if audit.get('risques'):
            risques_noms = [r['nom'] for r in audit['risques'] if r['impact'] == 3]
            if risques_noms:
                context_str += f"Risques Critiques identifiés: {', '.join(risques_noms)}."
        
        # Ajout des recommendations (titres seulement)
        if audit['diag'].get('recos'):
             recos_titres = [r['titre'] for r in audit['diag']['recos']]
             context_str += f" Recommandations proposées: {', '.join(recos_titres)}."

    return {"response": get_ai_response(user_msg, context=context_str)}

# --- EXPORT PDF (DESIGN MINIMALISTE) ---

@app.route('/export_pdf')
def export_pdf():
    if 'last_audit' not in session: return redirect(url_for('audit'))
    data = session['last_audit']
    
    # Chemins des ressources (Logo)
    logo_path = os.path.join(app.root_path, 'static', 'img', 'logo.png')
    
    # Génération des images (Graphiques Matplotlib)
    radar_img = generer_image_radar(data['scores_radar'])
    
    class PDF(FPDF):
        def header(self):
            # En-tête discret (sauf page 1)
            if self.page_no() > 1:
                self.set_font('Arial', '', 9)
                self.set_text_color(150, 150, 150)
                self.set_xy(15, 10)
                self.cell(0, 10, 'EvoluCheck - Audit de Maturité SI 2025', 0, 0, 'L')
                self.set_xy(15, 18)
                self.set_draw_color(16, 185, 129) # Bordure Verte
                self.line(15, 18, 195, 18)
                self.ln(15)

        def footer(self):
            if self.page_no() > 1:
                self.set_y(-15)
                self.set_font('Arial', 'I', 8)
                self.set_text_color(180, 180, 180)
                self.cell(0, 10, f'Page {self.page_no()} | Confidentiel - {datetime.now().year}', 0, 0, 'R')

        # --- COMPOSANTS UI ---
        
        def consulting_title(self, label):
            self.set_font('Arial', 'B', 18)
            self.set_text_color(4, 120, 87) # Vert Foncé (#047857)
            self.cell(0, 10, label.upper(), 0, 1, 'L')
            # Ligne Verte sous le titre
            self.set_fill_color(16, 185, 129) # Vert Primaire (#10B981)
            self.rect(self.get_x(), self.get_y(), 15, 1.5, 'F')
            self.ln(10)

        def consulting_card(self, x, y, w, title, value, icon):
            # Fond blanc avec ombre/bordure légère
            self.set_draw_color(220, 220, 220)
            self.set_fill_color(255, 255, 255)
            self.rect(x, y, w, 40, 'FD')
            
            # Bande supérieure colorée
            self.set_fill_color(16, 185, 129) # Vert Primaire
            self.rect(x, y, w, 2, 'F')
            
            # Titre
            self.set_xy(x, y + 6)
            self.set_font('Arial', 'B', 9)
            self.set_text_color(100, 100, 100)
            self.cell(w, 5, title.upper(), 0, 1, 'C')
            
            # Valeur
            self.set_xy(x, y + 16)
            self.set_font('Arial', 'B', 22)
            self.set_text_color(4, 120, 87) # Vert Foncé
            self.cell(w, 10, str(value) + "/5", 0, 1, 'C')
            
            # Icône (Lettre)
            self.set_xy(x + w - 12, y + 4)
            self.set_font('Arial', 'B', 8)
            self.set_text_color(16, 185, 129)
            self.cell(8, 8, icon, 0, 0, 'C')

    pdf = PDF()
    pdf.set_margins(15, 15, 15)
    
    # ==========================
    # PAGE 1 : COUVERTURE
    # ==========================
    pdf.add_page()
    
    # Bande Latérale Gauche
    pdf.set_fill_color(4, 120, 87) # Vert Foncé
    pdf.rect(0, 0, 60, 297, 'F') 
    
    # Ligne de séparation
    pdf.set_fill_color(16, 185, 129) # Vert Clair
    pdf.rect(60, 0, 2, 297, 'F') 
    
    # LOGO (Si présent)
    if os.path.exists(logo_path):
        # Affiche le logo en haut à droite sur la partie blanche
        # Ou centré dans la bande verte si c'est un logo blanc (mais ici on suppose logo couleur)
        # On va le mettre bien en évidence à droite
        try:
            pdf.image(logo_path, x=80, y=20, w=40)
        except:
            pass

    # Titre du Rapport
    pdf.set_xy(75, 80)
    pdf.set_font('Arial', 'B', 32)
    pdf.set_text_color(30, 30, 30)
    pdf.multi_cell(120, 14, "RAPPORT D'AUDIT\nDE MATURITÉ SI")
    
    pdf.set_xy(75, 120)
    pdf.set_font('Arial', '', 14)
    pdf.set_text_color(100, 100, 100)
    pdf.cell(0, 10, "EvoluCheck Edition 2025", 0, 1)
    
    # Auteur / Date (Alignement corrigé)
    pdf.set_xy(75, 220)
    pdf.set_font('Arial', 'B', 10)
    pdf.set_text_color(16, 185, 129) # Vert
    pdf.cell(0, 6, "RÉALISÉ PAR", 0, 1)
    
    pdf.set_x(75) # Alignement forcé
    pdf.set_font('Arial', '', 12)
    pdf.set_text_color(50, 50, 50)
    pdf.cell(0, 8, data.get('user', 'Utilisateur'), 0, 1) # Nom dynamique
    
    pdf.set_x(75) # Alignement forcé
    pdf.set_font('Arial', '', 10)
    pdf.set_text_color(150, 150, 150)
    pdf.cell(0, 6, datetime.now().strftime("%d %B %Y"), 0, 1)

    # ==========================
    # PAGE 2 : SYNTHÈSE
    # ==========================
    pdf.add_page()
    pdf.ln(10)
    pdf.consulting_title("Synthèse Exécutive")
    
    # Score Global
    pdf.ln(5)
    pdf.set_fill_color(245, 245, 245)
    # Centrage du cercle : Page largeur 210. Milieu = 105. Cercle rayon 20 (diam 40). X = 85.
    pdf.ellipse(85, 55, 40, 40, 'F')
    
    pdf.set_xy(85, 68)
    pdf.set_font('Arial', 'B', 28)
    pdf.set_text_color(4, 120, 87) # Vert Foncé
    pdf.cell(40, 10, str(int(data['global'])), 0, 1, 'C')
    
    pdf.set_xy(85, 78)
    pdf.set_font('Arial', '', 9)
    pdf.set_text_color(100, 100, 100)
    pdf.cell(40, 5, "/ 100", 0, 1, 'C')
    
    # Mention TOP
    if data['global'] > 80:
        pdf.set_xy(75, 100)
        pdf.set_fill_color(236, 253, 245) # Vert très pâle
        pdf.set_text_color(4, 120, 87)
        pdf.set_font('Arial', 'B', 8)
        pdf.cell(60, 6, "EXCELLENT NIVEAU DE MATURITÉ", 0, 1, 'C', True)

    pdf.ln(30) 

    # Cards des 3 Piliers
    # Largeur dispo = 180. 3 cartes de 55 = 165. Reste 15 pour 2 espaces = 7.5 chacun.
    card_w = 55
    space = 7.5
    start_x = 15 + (180 - (3 * card_w + 2 * space)) / 2 # Centrage exact
    y_pos = pdf.get_y()
    
    pdf.consulting_card(start_x, y_pos, card_w, "Adaptabilité", data['scores_radar'][0], "A")
    pdf.consulting_card(start_x + card_w + space, y_pos, card_w, "Innovation", data['scores_radar'][1], "I")
    pdf.consulting_card(start_x + 2*card_w + 2*space, y_pos, card_w, "Durabilité", data['scores_radar'][2], "D")
    
    pdf.ln(50)

    # Points Forts
    pdf.set_fill_color(240, 253, 244) # Vert très très pâle background
    pdf.rect(15, pdf.get_y(), 180, 40, 'F')
    
    pdf.set_xy(20, pdf.get_y() + 5)
    pdf.set_font('Arial', 'B', 12)
    pdf.set_text_color(16, 185, 129)
    pdf.cell(0, 8, "Points Forts Identifiés", 0, 1)
    
    pdf.set_font('Arial', '', 10)
    pdf.set_text_color(60, 60, 60)
    points_forts = ["Architecture SI alignée sur les standards", "Bonne gestion de la dette technique", "Politique Green IT en place"]
    for pf in points_forts:
        pdf.set_x(25)
        pdf.cell(5, 6, "+", 0, 0)
        pdf.cell(0, 6, pf, 0, 1)

    # ==========================
    # PAGE 3 : KPIs & PLAN
    # ==========================
    pdf.add_page()
    pdf.consulting_title("Indicateurs Clés de Performance")
    
    # Tableau
    headers = [("Indicateur", 60), ("Valeur", 30), ("Statut", 30), ("Analyse", 60)]
    pdf.set_fill_color(240, 240, 240)
    pdf.set_font('Arial', 'B', 9)
    pdf.set_text_color(50, 50, 50)
    
    for label, w in headers:
        pdf.cell(w, 10, label.upper(), 0, 0, 'L', True)
    pdf.ln()
    
    # Données KPI
    kpis = [
        ("Dette Technique", data.get('dette', '-').capitalize(), "Maîtrisée", "Impact limité"),
        ("Temps Déploiement", f"{data.get('temps', '-')} j", "Optimisé" if data.get('temps',0) <= 15 else "Lent", "Processus CI/CD"),
        ("Budget R&D", f"{data.get('rd', '-')} %", "Correct", "Investissement continu"),
        ("PUE (Efficience)", str(data.get('pue', '-')), "Critique" if data.get('pue', 0) > 1.5 else "Optimal", "Green IT"),
    ]

    pdf.set_font('Arial', '', 9)
    for i, (col1, col2, col3, col4) in enumerate(kpis):
        pdf.set_draw_color(230, 230, 230)
        pdf.line(15, pdf.get_y(), 195, pdf.get_y()) # Ligne séparation avant
        
        pdf.cell(60, 12, col1, 0, 0, 'L')
        pdf.set_font('Arial', 'B', 9)
        pdf.cell(30, 12, col2, 0, 0, 'L')
        
        # Statut Coloré
        pdf.set_font('Arial', '', 9)
        if "Critique" in col3 or "Lent" in col3:
            pdf.set_text_color(220, 38, 38) # Rouge
        else:
            pdf.set_text_color(16, 185, 129) # Vert
            
        pdf.cell(30, 12, col3, 0, 0, 'L')
        pdf.set_text_color(80, 80, 80)
        pdf.cell(60, 12, col4, 0, 1, 'L')
        pdf.ln(12) # Saut de ligne après la ligne du tableau

    pdf.ln(10)
    
    # Recommandations
    pdf.consulting_title("Feuille de Route")
    
    if not data['diag'].get('recos'):
        pdf.set_fill_color(236, 253, 245)
        pdf.rect(15, pdf.get_y(), 180, 20, 'F')
        pdf.set_xy(20, pdf.get_y() + 5)
        pdf.set_text_color(4, 120, 87)
        pdf.cell(0, 10, "Aucune recommandation critique.", 0, 1)
    else:
        for reco in data['diag']['recos']:
            titre = reco['titre'].encode('latin-1', 'replace').decode('latin-1')
            texte = reco['texte'].encode('latin-1', 'replace').decode('latin-1')
            
            pdf.set_fill_color(4, 120, 87) # Carré vert
            pdf.rect(15, pdf.get_y() + 2, 4, 4, 'F')
            
            pdf.set_x(25)
            pdf.set_font('Arial', 'B', 10)
            pdf.set_text_color(4, 120, 87)
            pdf.cell(0, 6, titre, 0, 1)
            
            pdf.set_x(25)
            pdf.set_font('Arial', '', 10)
            pdf.set_text_color(80, 80, 80)
            pdf.multi_cell(0, 5, texte)
            pdf.ln(5)
            
    # PAGE FIN
    pdf.add_page()
    
    # Logo Centré
    if os.path.exists(logo_path):
        try:
            # Centrage horizontal : Page 210mm, Logo 40mm -> X = (210-40)/2 = 85
            pdf.image(logo_path, x=85, y=100, w=40)
        except: pass
    
    # Titre & Message
    pdf.set_y(145)
    pdf.set_font('Arial', 'B', 22)
    pdf.set_text_color(4, 120, 87) # Vert Foncé
    pdf.cell(0, 10, "EvoluCheck", 0, 1, 'C')
    
    pdf.ln(5)
    pdf.set_font('Arial', '', 11)
    pdf.set_text_color(100, 100, 100) # Gris Moyen
    # Texte de résumé
    summary_text = (
        "Votre partenaire pour une transformation numérique durable.\n"
        "EvoluCheck analyse vos dimensions clés (Adaptabilité, Innovation, Durabilité)\n"
        "pour vous offrir un diagnostic précis et un plan d'action concret."
    )
    pdf.multi_cell(0, 6, summary_text, 0, 'C')
    
    # Ligne finale décorative
    pdf.ln(10)
    pdf.set_draw_color(200, 200, 200)
    x_line = (210 - 50) / 2
    pdf.line(x_line, pdf.get_y(), x_line + 50, pdf.get_y())
    
    # Output
    response = make_response(pdf.output(dest='S').encode('latin-1'))
    response.headers['Content-Type'] = 'application/pdf'
    response.headers['Content-Disposition'] = 'attachment; filename=rapport_audit_evolucheck_final.pdf'
    return response

# Initialisation DB au lancement
with app.app_context():
    db.create_all()

if __name__ == '__main__':
    app.run(debug=True)