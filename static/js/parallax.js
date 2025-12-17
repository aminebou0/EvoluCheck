/* =========================================
   PARALLAX BACKGROUND EFFECT
   ========================================= */
document.addEventListener('mousemove', (e) => {
    const orbsContainer = document.querySelector('.background-orbs');
    if (!orbsContainer) return;

    const x = (window.innerWidth - e.pageX * 2) / 100;
    const y = (window.innerHeight - e.pageY * 2) / 100;

    // Déplacement subtil inversé
    // On utilise translate3d pour forcer l'accélération matérielle (GPU)
    orbsContainer.style.transform = `translate3d(${x}px, ${y}px, 0)`;
});
