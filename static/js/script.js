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
/* =========================================
   3. LOGIQUE D'ENVOI MESSAGE (INTERFACE MODERNE)
   ========================================= */

function getCurrentTime() {
    const now = new Date();
    return now.getHours().toString().padStart(2, '0') + ':' + now.getMinutes().toString().padStart(2, '0');
}

function createChatRow(text, isUser, isTyping = false) {
    // 1. Conteneur Ligne
    const row = document.createElement('div');
    row.className = isUser ? 'chat-row user-row' : 'chat-row bot-row';

    // 2. Avatar
    const avatar = document.createElement('div');
    avatar.className = isUser ? 'chat-avatar user-avatar-img' : 'chat-avatar bot-avatar-img';

    // 3. Bulle de message
    const bubble = document.createElement('div');
    bubble.className = isUser ? 'chat-bubble user-bubble' : 'chat-bubble bot-bubble';

    if (isTyping) {
        bubble.innerHTML = `
            <div class="typing-indicator">
                <div class="typing-dot"></div>
                <div class="typing-dot"></div>
                <div class="typing-dot"></div>
            </div>`;
    } else {
        bubble.textContent = text;
        // Ajout de l'heure
        const timeSpan = document.createElement('span');
        timeSpan.className = 'chat-time';
        timeSpan.textContent = getCurrentTime();
        bubble.appendChild(timeSpan);
    }

    // Assemblage (Attention à l'ordre visuel géré par CSS flex-direction)
    if (isUser) {
        row.appendChild(bubble); // Bulle d'abord (visuellement inversé par row-reverse)
        row.appendChild(avatar); // Avatar ensuite
    } else {
        row.appendChild(avatar);
        row.appendChild(bubble);
    }

    return row;
}

async function sendMessage() {
    const input = document.getElementById('chat-input');
    const messagesDiv = document.getElementById('chat-messages');

    if (!input || !messagesDiv) return;

    const userText = input.value.trim();
    if (!userText) return;

    // --- 1. AFFICHER MESSAGE UTILISATEUR ---
    const userRow = createChatRow(userText, true);
    messagesDiv.appendChild(userRow);

    // Reset Input & Scroll
    input.value = '';
    messagesDiv.scrollTop = messagesDiv.scrollHeight;

    // --- 2. AFFICHER INDICATEUR DE FRAPPE (TYPING) ---
    const loadingRow = createChatRow("", false, true);
    loadingRow.id = 'loading-row';
    messagesDiv.appendChild(loadingRow);
    messagesDiv.scrollTop = messagesDiv.scrollHeight;

    try {
        // --- 3. APPEL API ---
        const response = await fetch('/api/chat', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ message: userText })
        });
        const data = await response.json();

        // --- 4. RÉPONSE DU BOT ---
        // Supprimer le loading
        const loader = document.getElementById('loading-row');
        if (loader) loader.remove();

        const botText = data.error ? "Erreur : " + data.error : (data.response || "Je n'ai pas compris.");
        const botRow = createChatRow(botText, false);

        // Si erreur, on peut changer la couleur du texte si on veut, mais restons simple pour l'instant
        if (data.error) botRow.querySelector('.chat-bubble').style.color = '#DC2626';

        messagesDiv.appendChild(botRow);

    } catch (error) {
        console.error('Erreur Chatbot:', error);

        const loader = document.getElementById('loading-row');
        if (loader) loader.remove();

        const errorRow = createChatRow("Erreur de connexion au serveur IA.", false);
        errorRow.querySelector('.chat-bubble').style.color = '#DC2626';
        messagesDiv.appendChild(errorRow);
    }

    messagesDiv.scrollTop = messagesDiv.scrollHeight;
}