# 🌿 EvoluCheck - Audit de Maturité SI (Dimension 6)

**EvoluCheck** est une plateforme d'audit de nouvelle génération conçue pour évaluer la **Dimension 6 (Évolutive)** des Systèmes d'Information, basée sur le référentiel **AuditS2I**.

Alliant expertise technique et design premium, elle permet aux organisations de mesurer leur **Adaptabilité**, leur **Innovation** et leur **Durabilité (Green IT)** à travers une interface fluide, animée et intelligente.

> Ce projet a été réalisé avec excellence dans le cadre du **Master MS2I** (Audit et Contrôle de Gestion des SI).

---

## ✨ Fonctionnalités Clés & Innovation

### 🧠 1. Intelligence Artificielle "EvoluBot"
*   **Assistant Expert** : Un chatbot intégré (basé sur OpenAI GPT-3.5) configuré avec un rôle d'expert senior en audit.
*   **Interface Moderne** : Expérience de chat style "WhatsApp" avec avatars, indicateurs de frappe et horodatage.
*   **Context-Aware** : L'IA connait vos scores d'audit en temps réel pour fournir des conseils personnalisés.

### 🎨 2. Expérience Utilisateur (UX/UI) Premium
*   **Design "Eco-Tech"** : Charte graphique moderne (Vert Émeraude & Glassmorphism) utilisant la police **Outfit** et **Inter**.
*   **Authentification Split-Screen** : Page de connexion immersive avec visuel inspirant.
*   **Animations Avancées** :
    *   **Parallax Background** : Fond animé avec orbes flottantes réagissant à la souris.
    *   **3D Tilt Effect** : Les cartes interactives s'inclinent au survol.
    *   **AI Loader** : Écran de chargement immersif simulant le calcul des scores par l'IA.

### 📊 3. Audit & Analyse Stratégique
*   **Tableau de Bord Dynamique** : Visualisation des KPIs via **Radar Charts** et **Jauges**.
*   **Gestion des Risques** : Génération automatique de la **Matrice de Farmer** (Probabilité x Impact).
*   **Recommandations Automatisées** : Le système génère un diagnostic (FRAP/FRABOP) et des actions correctives précises.
*   **Export PDF** : Rapport professionnel généré à la volée pour les comités de direction.

### 🔌 4. Connectivité & Automatisation
*   **Import CSV** : Ingestion de données en masse pour audit multi-sites.
*   **Connecteur n8n** : Webhook natif pour envoyer les alertes vers des workflows externes (Emails, Slack, Teams).

---

## 🛠️ Stack Technique

*   **Backend** : Python (Flask), SQLAlchemy (SQLite).
*   **Frontend** : HTML5, CSS3 (Variables, Flexbox/Grid), JavaScript (Vanilla).
*   **IA** : OpenAI API (GPT-3.5 Turbo).
*   **Data Viz** : Matplotlib (Génération serveur), Chart.js (Interactive).
*   **Outils** : n8n (Orchestration), FPDF (Génération de rapports).

---

## 📦 Installation & Démarrage

1.  **Prérequis** : Python 3.8+, Clé API OpenAI (Optionnel).

2.  **Installation** :
    ```bash
    git clone https://github.com/votre-repo/evolucheck.git
    cd evolucheck
    python -m venv venv
    # Windows: venv\Scripts\activate
    # Mac/Linux: source venv/bin/activate
    pip install -r requirements.txt
    ```

3.  **Configuration** :
    Créez un fichier `.env` à la racine :
    ```env
    OPENAI_API_KEY=sk-votre-cle-api
    GOOGLE_CLIENT_ID=votre-id (optionnel)
    GOOGLE_CLIENT_SECRET=votre-secret (optionnel)
    ```

4.  **Lancement** :
    ```bash
    flask run
    ```
    Accédez à `http://127.0.0.1:5000`.

---

## 👥 L'Équipe de Réalisation (Master MS2I)

*   **BOUBOU Mohammed Amine**
*   **EL-BAKKALI Aya**
*   **AMHAJJAR Hiba**
*   **FARAJI Nouhaila**
*   **ZIANI Mariyam**
*   **ZERHOUNI Amina**
*   **RAHMANI Said**
*   **LAMRHILI Imad-eddine**

**Encadrement Pédagogique :**
*   Pr. El-attar Abdelilah
*   Pr. Senhaji Zineb

---
© 2025 FSJES - Master d'Excellence Audit SII
