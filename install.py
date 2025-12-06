import os

# L'architecture exacte requise pour le projet
structure = {
    "dossiers": [
        "static",
        "static/css",
        "static/js",
        "static/img",
        "templates"
    ],
    "fichiers": [
        "app.py",
        ".env",
        "requirements.txt",
        "static/css/style.css",
        "static/js/script.js",
        "templates/base.html",
        "templates/index.html",
        "templates/auth.html",
        "templates/audit.html",
        "templates/dashboard.html",
        "templates/about.html",
        "templates/contact.html"
    ]
}

def installer():
    print("🔧 Démarrage de la réparation de l'architecture...")
    
    # 1. Création des dossiers
    for dossier in structure["dossiers"]:
        os.makedirs(dossier, exist_ok=True)
        print(f"   [Dossier] {dossier} ... OK")

    # 2. Création des fichiers vides
    for fichier in structure["fichiers"]:
        if not os.path.exists(fichier):
            with open(fichier, 'w', encoding='utf-8') as f:
                f.write("") # On crée un fichier vide
            print(f"   [Fichier] {fichier} ... CRÉÉ")
        else:
            print(f"   [Fichier] {fichier} ... EXISTE DÉJÀ")

    print("\n✅ Architecture réparée avec succès !")
    print("Vous pouvez maintenant supprimer ce fichier 'install.py'.")

if __name__ == "__main__":
    installer()