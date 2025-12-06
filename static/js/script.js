/* =========================================
   1. GESTION DES ONGLETS (TABS)
   ========================================= */
function openTab(evt, tabName) {
    // Déclaration des variables
    var i, tabcontent, tablinks;
    
    // 1. Cacher tous les contenus d'onglets
    tabcontent = document.getElementsByClassName("tab-content");
    for (i = 0; i < tabcontent.length; i++) {
        tabcontent[i].style.display = "none";
        tabcontent[i].classList.remove("active");
    }
    
    // 2. Désactiver l'état "active" de tous les boutons
    tablinks = document.getElementsByClassName("tab-btn");
    for (i = 0; i < tablinks.length; i++) {
        tablinks[i].className = tablinks[i].className.replace(" active", "");
    }
    
    // 3. Afficher l'onglet actuel
    const targetTab = document.getElementById(tabName);
    if (targetTab) {
        targetTab.style.display = "block";
        // Petit délai pour permettre l'animation CSS (fadeIn)
        setTimeout(() => {
            targetTab.classList.add("active");
        }, 10);
    }
    
    // 4. Ajouter la classe active au bouton cliqué
    if (evt) {
        evt.currentTarget.className += " active";
    }
}

/* =========================================
   2. GESTION DU CHATBOT (Interface)
   ========================================= */

// Ouvrir / Fermer la fenêtre de chat
function toggleChatbot() {
    const chatWindow = document.getElementById('chatbot-window');
    
    // Vérifie le style calculé pour être sûr de l'état actuel
    const currentDisplay = window.getComputedStyle(chatWindow).display;

    if (currentDisplay === 'none') {
        chatWindow.style.display = 'flex';
        // Focus automatique sur l'input quand on ouvre
        setTimeout(() => {
            const input = document.getElementById('chat-input');
            if (input) input.focus();
        }, 100);
    } else {
        chatWindow.style.display = 'none';
    }
}

// Gérer l'appui sur la touche "Entrée"
function handleEnter(e) {
    if (e.key === 'Enter') {
        sendMessage();
    }
}

/* =========================================
   3. LOGIQUE D'ENVOI MESSAGE (API FETCH)
   ========================================= */
async function sendMessage() {
    const input = document.getElementById('chat-input');
    const messagesDiv = document.getElementById('chat-messages');
    
    if (!input || !messagesDiv) return; // Sécurité

    const userText = input.value.trim();

    // Ne rien faire si le message est vide
    if (!userText) return;

    // --- 1. Afficher le message de l'utilisateur ---
    const userMsgDiv = document.createElement('div');
    userMsgDiv.className = 'message user-msg';
    userMsgDiv.textContent = userText;
    messagesDiv.appendChild(userMsgDiv);
    
    // Vider l'input et scroller vers le bas
    input.value = '';
    messagesDiv.scrollTop = messagesDiv.scrollHeight;

    // --- 2. Afficher l'indicateur de chargement "..." ---
    const loadingDiv = document.createElement('div');
    loadingDiv.className = 'message bot-msg';
    loadingDiv.innerHTML = '<i class="fa-solid fa-circle-notch fa-spin"></i> Analyse en cours...';
    loadingDiv.id = 'loading-msg';
    messagesDiv.appendChild(loadingDiv);
    messagesDiv.scrollTop = messagesDiv.scrollHeight;

    try {
        // --- 3. Appel à l'API Backend (Python) ---
        const response = await fetch('/api/chat', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ message: userText })
        });
        
        const data = await response.json();
        
        // --- 4. Remplacer le chargement par la réponse de l'IA ---
        const loader = document.getElementById('loading-msg');
        if (loader) messagesDiv.removeChild(loader);
        
        const botMsgDiv = document.createElement('div');
        botMsgDiv.className = 'message bot-msg';
        
        // Gestion simple des erreurs renvoyées par le serveur
        if (data.error) {
            botMsgDiv.style.color = '#DC2626';
            botMsgDiv.textContent = "Erreur : " + data.error;
        } else {
            // Affichage de la réponse
            botMsgDiv.textContent = data.response || "Je n'ai pas compris, pouvez-vous reformuler ?";
        }
        
        messagesDiv.appendChild(botMsgDiv);
        
    } catch (error) {
        console.error('Erreur Chatbot:', error);
        
        // Gestion des erreurs réseau
        const loader = document.getElementById('loading-msg');
        if (loader) messagesDiv.removeChild(loader);
        
        const errorDiv = document.createElement('div');
        errorDiv.className = 'message bot-msg';
        errorDiv.style.color = '#DC2626';
        errorDiv.innerHTML = '<i class="fa-solid fa-wifi"></i> Erreur de connexion au serveur IA.';
        messagesDiv.appendChild(errorDiv);
    }
    
    // Toujours scroller vers le bas pour voir le dernier message
    messagesDiv.scrollTop = messagesDiv.scrollHeight;
}