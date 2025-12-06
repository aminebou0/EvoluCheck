# EvoluCheck

**EvoluCheck** est une application web d'audit conçue pour évaluer la **Dimension 6 (Évolutive)** des Systèmes d'Information (SI), conformément au référentiel **AuditS2I**. Elle permet aux auditeurs d'analyser la résilience, l'adaptabilité, l'innovation et la durabilité (Green IT) d'une organisation.

Ce projet a été réalisé dans le cadre du **Master d'Excellence Audit et Contrôle de Gestion des SI (MS2I)**.

---

## 🚀 Fonctionnalités Principales

*   **Audit Assisté** : Formulaire interactif pour saisir les indicateurs clés (KPIs) des 3 piliers de la dimension évolutive :
    *   **Adaptabilité** (Architecture, Dette Technique, Dépendance Fournisseur).
    *   **Innovation** (Budget R&D, PoC, Taux de Transformation).
    *   **Durabilité** (Green IT, PUE, Recyclage).
*   **Tableau de Bord (Dashboard)** : Visualisation graphique des résultats via :
    *   Un **Radar Chart** pour positionner l'entreprise sur les 3 axes.
    *   La **Matrice de Farmer** pour cartographier les risques (Probabilité x Impact).
*   **Diagnostic Expert & IA** : Génération automatique d'un rapport textuel avec des recommandations ciblées, enrichies par une **Intelligence Artificielle (OpenAI GPT)** via un chatbot intégré.
*   **Export PDF** : Génération d'un rapport d'audit professionnel téléchargeable au format PDF.
*   **Intégration n8n** : Connexion possible avec n8n pour l'automatisation de workflows (alertes, emails, CRM).
*   **Import CSV** : Possibilité d'importer des données d'audit en masse depuis un fichier CSV.

---

## 🛠️ Prérequis Techniques

*   **Python** 3.8 ou supérieur.
*   Un compte **OpenAI** (pour la clé API) si vous souhaitez activer le Chatbot IA.
*   Un navigateur web moderne.

---

## 📦 Installation

1.  **Cloner le projet** (ou extraire l'archive) dans votre répertoire local.

2.  **Créer un environnement virtuel** (recommandé) :
    ```bash
    python -m venv venv
    # Activation sur Windows :
    venv\Scripts\activate
    # Activation sur Mac/Linux :
    source venv/bin/activate
    ```

3.  **Installer les dépendances** :
    ```bash
    pip install -r requirements.txt
    ```

4.  **Configuration** :
    *   Renommez ou créez un fichier `.env` à la racine du projet.
    *   Ajoutez votre clé API OpenAI :
        ```env
        OPENAI_API_KEY=votre_clé_api_ici
        ```

---

## ▶️ Démarrage

1.  Lancez l'application Flask :
    ```bash
    flask run
    ```
2.  Ouvrez votre navigateur et accédez à :
    `http://127.0.0.1:5000`

---

## 📂 Structure du Projet

*   `app.py` : Le cœur de l'application (Backend Flask, Routes, Logique Métier).
*   `templates/` : Fichiers HTML (Jinja2) pour l'interface utilisateur.
*   `static/` : Feuilles de style CSS (`style.css`), Scripts JS (`script.js`) et Images.
*   `instance/` : Base de données SQLite (`evolucheck.db`).
*   `requirements.txt` : Liste des librairies Python requises.

---

## 👥 Auteurs & Crédits

**Encadrement :**
*   Pr. El-attar Abdelilah
*   Pr. Senhaji Zineb

**Équipe Projet (Master MS2I) :**
*   BOUBOU Mohammed Amine
*   EL-BAKKALI Aya
*   AMHAJJAR Hiba
*   FARAJI Nouhaila
*   ZIANI Mariyam
*   ZERHOUNI Amina
*   RAHMANI Said
*   LAMRHILI Imad-eddine

---
© 2025 FSJES - Master d'Excellence Audit SII
