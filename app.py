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
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///evolucheck_v2.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

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
    N8N_WEBHOOK_URL = "https://magana12.app.n8n.cloud/webhook-test/audit-alert"
    
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

def get_ai_response(msg):
    """Chatbot Intelligent via OpenAI"""
    if not client: return "Erreur : Clé API non configurée dans le fichier .env"
    
    # Construction du contexte (Récupération du dernier audit s'il existe)
    last_audit = session.get('last_audit')
    context_str = ""
    if last_audit:
        recos_titres = [r['titre'] for r in last_audit['diag'].get('recos', [])]
        context_str = f"""
        [CONTEXTE AUDIT UTILISATEUR]
        Score Global : {last_audit.get('global')}/100
        - Adaptabilité : {last_audit['scores_radar'][0]}/5
        - Innovation : {last_audit['scores_radar'][1]}/5
        - Durabilité : {last_audit['scores_radar'][2]}/5
        - Points d'attention : {', '.join(recos_titres)}
        Réponds en tenant compte de ces résultats pour conseiller l'utilisateur.
        """

    try:
        completion = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "Tu es un expert en audit de maturité des Systèmes d'Information (Dimension 6). Tes réponses sont professionnelles, concises et orientées action. " + context_str},
                {"role": "user", "content": msg}
            ],
            max_tokens=250
        )
        return completion.choices[0].message.content
    except Exception as e:
        return f"Erreur OpenAI : {str(e)}"

# --- INTERFACE FLASK (ROUTES) ---
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/login/google')
def google_login():
    redirect_uri = url_for('google_callback', _external=True)
    return oauth.google.authorize_redirect(redirect_uri)

@app.route('/auth/google/callback')
def google_callback():
    token = oauth.google.authorize_access_token()
    user_info = oauth.google.parse_id_token(token, nonce=None)
    
    session['user'] = user_info['name']
    session['email'] = user_info['email']
    
    flash(f"Bienvenue, {user_info['name']} !", "success")
    return redirect(url_for('audit'))

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
            'email': session.get('email', 'non-renseigne'),
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

# --- ROUTE SAUVEGARDE MANUELLE ---
@app.route('/save_audit', methods=['POST'])
def save_audit():
    if 'user' not in session: return redirect(url_for('auth'))
    if 'last_audit' not in session: 
        flash("Aucun audit à sauvegarder.", "warning")
        return redirect(url_for('audit'))
    
    data = session['last_audit']
    user_email = session.get('email')
    
    if user_email:
        try:
            # Vérifier si cet audit a déjà été sauvegardé récemment (optionnel, pour éviter doublons)
            # Ici on sauvegarde direct
            # Adaptation pour les KPIs manquants si nécessaire
            new_audit = Audit(
                user_email=user_email,
                score_adaptabilite=data['scores_radar'][0],
                score_innovation=data['scores_radar'][1],
                score_durabilite=data['scores_radar'][2],
                score_global=data['global'],
                diagnostic_type=data['diag']['type'],
                recommandations=str([r['titre'] for r in data['diag'].get('recos', [])]),
                dette_technique=data.get('dette', '-'),
                taux_transformation_poc=data.get('taux_transfo', 0),
                part_energie_verte=data.get('energie_verte', 0)
            )
            db.session.add(new_audit)
            db.session.commit()
            flash("Audit sauvegardé avec succès dans l'historique !", "success")
        except Exception as e:
            flash("Erreur lors de la sauvegarde.", "error")
            print(f"Erreur DB Save: {e}")
    else:
        flash("Utilisateur non identifié pour la sauvegarde.", "warning")

    return redirect(url_for('dashboard'))

@app.route('/load_audit/<int:audit_id>')
def load_audit(audit_id):
    if 'user' not in session: return redirect(url_for('auth'))
    user_email = session.get('email')
    
    audit = Audit.query.get_or_404(audit_id)
    
    # Sécurité : Un utilisateur ne peut charger que ses audits
    if audit.user_email != user_email:
        flash("Accès non autorisé à cet audit.", "error")
        return redirect(url_for('historique'))
    
    # Reconstruction des données pour la session
    # Note: On n'a pas tout stocké en DB (inputs bruts), donc on approxime ou on laisse vide ce qui n'est pas critique
    # Pour Farmer (Risques), on doit reconstruire une liste approximative ou stocker les risques en JSON string en DB
    # Solution rapide : on réanalyse les risques basés sur les scores si possible, sinon on laisse vide
    
    # Pour afficher la matrice de risques, il nous faut les inputs 'inputs'. 
    # Or, on ne stocke pas 'dep', 'temps', 'pue', etc. en DB dans ce modèle v2 simplifié pour l'instant.
    # Amélioration : On va créer des inputs fictifs cohérents avec les scores pour reconstituer l'affichage
    # C'est une limite actuelle, pour l'instant on met des risques vides ou on améliore le modèle DB plus tard.
    
    inputs_fictifs = {
        'dep': 0, 'temps': 0, 'pue': 0, 'rd': 0 # Valeurs par défaut
    }
    
    # On reconstitue les risques (Réellement il faudrait stocker le JSON complet des risques en DB)
    risques_reconstitues = analyser_risques(inputs_fictifs)

    session['last_audit'] = {
        'scores_radar': [audit.score_adaptabilite, audit.score_innovation, audit.score_durabilite],
        'global': audit.score_global,
        'diag': {
            'type': audit.diagnostic_type,
            'message': 'Audit historique chargé.',
            'color': 'success' if audit.score_global >= 80 else ('danger' if audit.score_global <= 60 else 'warning'),
            'recos': [{'titre': r, 'texte': ''} for r in eval(audit.recommandations)] if audit.recommandations else []
        },
        'risques': risques_reconstitues, # Sera vide ou basique
        'date': audit.date_audit.strftime("%d/%m/%Y"),
        'user': session.get('user'),
        'email': user_email,
        # KPIs stockés
        'dette': audit.dette_technique,
        'taux_transfo': audit.taux_transformation_poc,
        'energie_verte': audit.part_energie_verte,
        # Valeurs par défaut pour éviter erreurs template
        'dep': 0, 'temps': 0, 'pue': 0, 'rd': 0, 'poc': 0, 'rec': 'non', 'arch': 'non'
    }
    
    flash(f"Audit du {audit.date_audit.strftime('%d/%m/%Y')} chargé dans le tableau de bord.", "info")
    return redirect(url_for('dashboard'))

@app.route('/historique')
def historique():
    if 'user' not in session: return redirect(url_for('auth'))
    user_email = session.get('email')
    
    # Récupérer les audits de l'utilisateur
    audits = Audit.query.filter_by(user_email=user_email).order_by(Audit.date_audit.desc()).all()
    
    # Préparer les données pour le graphique d'évolution
    dates = [a.date_audit.strftime("%d/%m") for a in audits][::-1] # Ordre chronologique
    scores = [a.score_global for a in audits][::-1]
    
    return render_template('history.html', audits=audits, dates=dates, scores=scores)

@app.route('/dashboard')
def dashboard():
    if 'last_audit' not in session: return redirect(url_for('audit'))
    return render_template('dashboard.html', data=session['last_audit'])

@app.route('/api/chat', methods=['POST'])
def chat_api():
    data = request.get_json()
    return {"response": get_ai_response(data.get('message'))}

def create_pdf_object(data):
    # Génération des images
    radar_img = generer_image_radar(data['scores_radar'])
    farmer_img = generer_image_farmer(data['risques'])
    
    logo_path = os.path.join(app.root_path, 'static', 'img', 'logo.png')
    
    class PDF(FPDF):
        def header(self):
            # En-tête discret (sauf page 1)
            if self.page_no() > 1:
                self.set_font('Arial', '', 9)
                self.set_text_color(150, 150, 150)
                self.set_xy(10, 10)
                self.cell(0, 10, 'EvoluCheck - Audit de Maturité 2025', 0, 0, 'L')
                self.set_xy(10, 18)
                self.set_draw_color(220, 220, 220)
                self.line(10, 18, 200, 18)
                self.ln(15)

        def footer(self):
            if self.page_no() > 1:
                self.set_y(-15)
                self.set_font('Arial', '', 8)
                self.set_text_color(180, 180, 180)
                self.cell(0, 10, f'Page {self.page_no()} | Document Confidentiel', 0, 0, 'R')

        # --- COMPOSANTS UI ---
        
        def consulting_title(self, label):
            self.set_font('Arial', 'B', 18)
            self.set_text_color(16, 185, 129) # Vert Logo (#10B981)
            self.cell(0, 10, label.upper(), 0, 1, 'L')
            # Ligne de soulignement
            self.set_fill_color(5, 150, 105) # Vert Foncé
            self.rect(self.get_x(), self.get_y(), 20, 1.5, 'F')
            self.ln(10)

        def consulting_card(self, x, y, w, title, value, icon):
            # Fond blanc + Bordure
            self.set_draw_color(229, 231, 235) # Gris clair
            self.set_fill_color(255, 255, 255)
            self.rect(x, y, w, 45, 'FD')
            
            # Bande supérieure verte
            self.set_fill_color(16, 185, 129) # Vert Logo
            self.rect(x, y, w, 2, 'F')
            
            # Titre
            self.set_xy(x, y + 8)
            self.set_font('Arial', 'B', 10)
            self.set_text_color(107, 114, 128) # Gris moyen
            self.cell(w, 5, title.upper(), 0, 1, 'C')
            
            # Valeur
            self.set_xy(x, y + 18)
            self.set_font('Arial', 'B', 22)
            self.set_text_color(6, 95, 70) # Vert très foncé
            self.cell(w, 10, str(value) + "/5", 0, 1, 'C')
            
            # Lettre icône fond rond
            self.set_fill_color(236, 253, 245) # Vert très pâle
            self.rect(x + w/2 - 5, y + 33, 10, 10, 'F') # "Cercle" carré
            
            self.set_xy(x, y + 35)
            self.set_font('Arial', 'B', 9)
            self.set_text_color(16, 185, 129)
            self.cell(w, 6, icon, 0, 0, 'C')

    pdf = PDF()
    pdf.set_margins(20, 20, 20) # Marges standardisées
    
    # ==========================
    # PAGE 1 : COUVERTURE AVEC LOGO
    # ==========================
    pdf.add_page()
    
    # Bande Latérale Verte
    pdf.set_fill_color(6, 78, 59) # Vert Forêt Profond
    pdf.rect(0, 0, 70, 297, 'F') 
    
    # Ligne Accent
    pdf.set_fill_color(16, 185, 129) # Vert Logo
    pdf.rect(70, 0, 2, 297, 'F')
    
    # Logo (si dispo)
    if os.path.exists(logo_path):
        try:
            # On place le logo sur la partie blanche
            pdf.image(logo_path, x=90, y=40, w=50) 
        except: pass
    
    # Titre Principal
    pdf.set_xy(90, 100)
    pdf.set_font('Arial', 'B', 30)
    pdf.set_text_color(31, 41, 55) # Gris Anthracite
    pdf.multi_cell(100, 14, "RAPPORT D'AUDIT\nDE MATURITÉ SI")
    
    # Sous-titre
    pdf.set_xy(90, 140)
    pdf.set_font('Arial', '', 14)
    pdf.set_text_color(107, 114, 128)
    pdf.cell(0, 10, "EvoluCheck Edition 2025", 0, 1)
    
    # Bloc Auteur Alignement corrigé
    pdf.set_xy(90, 220)
    pdf.set_font('Arial', 'B', 10)
    pdf.set_text_color(16, 185, 129) # Vert
    pdf.cell(0, 6, "CONFIDENTIEL", 0, 1)
    
    pdf.set_x(90)
    pdf.set_font('Arial', '', 12)
    pdf.set_text_color(55, 65, 81)
    pdf.cell(0, 8, "Réalisé par Hiba Amhajjar", 0, 1)
    
    pdf.set_x(90)
    pdf.set_font('Arial', '', 10)
    pdf.set_text_color(156, 163, 175)
    pdf.cell(0, 6, datetime.now().strftime("%d %B %Y"), 0, 1)

    # ==========================
    # PAGE 2 : SYNTHÈSE
    # ==========================
    pdf.add_page()
    pdf.ln(10)
    pdf.consulting_title("Synthèse Exécutive")
    
    # Jauge Score Global
    pdf.ln(5)
    # Fond jauge
    pdf.set_fill_color(243, 244, 246)
    pdf.rect(85, 55, 40, 40, 'F')
    # Score
    pdf.set_xy(85, 65)
    pdf.set_font('Arial', 'B', 26)
    pdf.set_text_color(16, 185, 129) # Vert
    pdf.cell(40, 10, str(int(data['global'])), 0, 1, 'C')
    # Label
    pdf.set_xy(85, 75)
    pdf.set_font('Arial', '', 9)
    pdf.set_text_color(107, 114, 128)
    pdf.cell(40, 10, "/ 100", 0, 1, 'C')
    
    pdf.ln(40) # Espace

    # Cards Alignées
    # Calcul largeur: (210 - 20 - 20 - 2*space) / 3
    # 170 / 3 ≈ 52
    card_w = 52
    space = 6
    start_x = 22 # Marge gauche un peu décalée pour centrer visuellement
    y_pos = pdf.get_y()
    
    pdf.consulting_card(start_x, y_pos, card_w, "Adaptabilité", data['scores_radar'][0], "A")
    pdf.consulting_card(start_x + card_w + space, y_pos, card_w, "Innovation", data['scores_radar'][1], "I")
    pdf.consulting_card(start_x + 2*card_w + 2*space, y_pos, card_w, "Durabilité", data['scores_radar'][2], "D")
    
    pdf.ln(60)

    # Section Points Forts
    pdf.set_fill_color(236, 253, 245) # Fond Vert très clair
    pdf.rect(20, pdf.get_y(), 170, 45, 'F')
    
    pdf.set_xy(25, pdf.get_y() + 5)
    pdf.set_font('Arial', 'B', 12)
    pdf.set_text_color(6, 95, 70) # Vert Foncé
    pdf.cell(0, 8, "Points Forts Identifiés", 0, 1)
    
    pdf.set_font('Arial', '', 10)
    pdf.set_text_color(55, 65, 81)
    
    # Génération dynamique des points forts
    points_forts = []
    if data['global'] >= 70:
        points_forts.append(f"Score Global performant ({data['global']}%)")
    
    if data['scores_radar'][0] >= 3.5:
        points_forts.append("Forte Adaptabilité et Agilité du SI")
    elif data['scores_radar'][0] >= 2.5:
        points_forts.append("Socle technologique stable")
        
    if data['scores_radar'][1] >= 3.5:
        points_forts.append("Culture de l'Innovation active")
    
    if data['scores_radar'][2] >= 3.5:
        points_forts.append("Démarche Green IT mature")
    
    # Fallback si aucun point fort marquant
    if not points_forts:
        points_forts.append("Potentiel d'amélioration identifié")
        points_forts.append("Démarche d'audit volontaire")

    for pf in points_forts:
        pdf.set_x(30)
        pdf.cell(5, 6, "+", 0, 0)
        pdf.cell(0, 6, pf, 0, 1)

    # ==========================
    # PAGE 3 : DIAGNOSTIC & KPIs
    # ==========================
    pdf.add_page()
    pdf.consulting_title("Détails de la Performance")
    
    # En-têtes Tableau
    # Largeurs: 170 total (page 210 - 20 - 20)
    headers = [("Indicateur", 60), ("Valeur", 25), ("Statut", 30), ("Analyse", 55)]
    
    pdf.set_fill_color(249, 250, 251) # Gris très clair
    pdf.set_font('Arial', 'B', 9)
    pdf.set_text_color(55, 65, 81)
    
    for label, w in headers:
        pdf.cell(w, 10, label.upper(), 0, 0, 'L', True)
    pdf.ln()
    
    # Données
    kpis = [
        ("Dette Technique", data.get('dette', '-').capitalize(), "Maîtrisée", "Impact faible"),
        ("Temps Déploiement", f"{data.get('temps', '-')} j", "Conforme", "Processus optimisé"),
        ("Budget R&D", f"{data.get('rd', '-')} %", "À surveiller", "Sous cible 5%"),
        ("PUE (Efficience)", str(data.get('pue', '-')), "Critique" if data.get('pue', 0) > 1.5 else "Optimal", "Indicateur clé"),
        ("Taux Transfo POC", f"{data.get('taux_transfo', 0)}%", "Orange" if data.get('taux_transfo',0)<20 else "Vert", "Passage à l'échelle")
    ]

    pdf.set_font('Arial', '', 9)
    for col1, col2, col3, col4 in kpis:
        pdf.set_draw_color(243, 244, 246)
        pdf.line(20, pdf.get_y(), 190, pdf.get_y()) # Ligne séparation
        
        pdf.cell(60, 12, col1, 0, 0, 'L')
        pdf.set_font('Arial', 'B', 9)
        pdf.cell(25, 12, col2, 0, 0, 'L')
        
        # Couleur Statut
        pdf.set_font('Arial', '', 9)
        if col3 == "Critique": pdf.set_text_color(220, 38, 38) # Rouge
        elif col3 == "À surveiller": pdf.set_text_color(217, 119, 6) # Orange
        else: pdf.set_text_color(5, 150, 105) # Vert
            
        pdf.cell(30, 12, col3, 0, 0, 'L')
        
        pdf.set_text_color(107, 114, 128) # Gris
        pdf.cell(55, 12, col4, 0, 1, 'L')
        pdf.set_text_color(55, 65, 81) # Reset Noir

    pdf.ln(10)
    
    # Risques
    pdf.set_font('Arial', 'B', 11)
    pdf.set_text_color(6, 78, 59)
    pdf.cell(0, 10, "Points de Vigilance", 0, 1)
    pdf.set_font('Arial', '', 10)
    pdf.set_text_color(75, 85, 99)
    pdf.multi_cell(0, 5, "Surveillance recommandée de l'évolution du PUE et de la dette technique sur les modules legacy.")

    # ==========================
    # PAGE 4 : PLANS D'ACTION
    # ==========================
    pdf.add_page()
    pdf.consulting_title("Feuille de Route")
    
    if not data['diag'].get('recos'):
        # Carte Aucune Action (Vert)
        pdf.set_fill_color(236, 253, 245)
        pdf.set_draw_color(16, 185, 129)
        pdf.rect(20, pdf.get_y()+5, 170, 30, 'FD')
        
        pdf.set_xy(20, pdf.get_y()+15)
        pdf.set_font('Arial', 'B', 11)
        pdf.set_text_color(6, 95, 70)
        pdf.cell(170, 10, "Aucune action prioritaire requise pour le moment.", 0, 0, 'C')
    else:
        for reco in data['diag']['recos']:
            titre = reco['titre'].encode('latin-1', 'replace').decode('latin-1')
            texte = reco['texte'].encode('latin-1', 'replace').decode('latin-1')
            
            # Puce Carrée Verte
            pdf.set_fill_color(16, 185, 129)
            pdf.rect(20, pdf.get_y() + 2, 4, 4, 'F')
            
            pdf.set_x(30)
            pdf.set_font('Arial', 'B', 11)
            pdf.set_text_color(6, 78, 59)
            pdf.cell(0, 8, titre, 0, 1)
            
            pdf.set_x(30)
            pdf.set_font('Arial', '', 10)
            pdf.set_text_color(75, 85, 99)
            pdf.multi_cell(0, 5, texte)
            pdf.ln(6)

    # PAGE FIN
    pdf.add_page()
    pdf.set_y(130)
    pdf.set_font('Arial', 'B', 20)
    pdf.set_text_color(16, 185, 129)
    pdf.cell(0, 10, "EvoluCheck", 0, 1, 'C')
    
    return pdf

# --- EXPORT PDF (DESIGN MINIMALISTE) ---

@app.route('/export_pdf')
def export_pdf():
    if 'last_audit' not in session: return redirect(url_for('audit'))
    data = session['last_audit']
    
    pdf = create_pdf_object(data)
    
    response = make_response(pdf.output(dest='S').encode('latin-1'))
    response.headers['Content-Type'] = 'application/pdf'
    response.headers['Content-Disposition'] = f'attachment; filename=Audit_EvoluCheck_{datetime.now().strftime("%Y%m%d")}.pdf'
    return response

# Initialisation DB au lancement
with app.app_context():
    db.create_all()

if __name__ == '__main__':
    app.run(debug=True)