
/* =========================================
   12. JS TILT EFFECT (Injected Snippet)
   ========================================= */
document.addEventListener('DOMContentLoaded', () => {
    const cards = document.querySelectorAll('.feature-card');
    const container = document.querySelector('.features-grid');

    if (container) {
        container.addEventListener('mousemove', (e) => {
            cards.forEach(card => {
                const rect = card.getBoundingClientRect();
                const x = e.clientX - rect.left;
                const y = e.clientY - rect.top;

                // Calcul de la rotation en fonction de la position de la souris
                // Seulement si la souris est PROCHE de la carte (pour éviter que tout bouge en même temps trop fort)
                // Ou alors on fait un effet global subtil

                // Simplification : effet tilt uniquement sur la carte survolée
            });
        });
    }

    // Gestion individuelle par carte
    cards.forEach(card => {
        card.addEventListener('mousemove', (e) => {
            const rect = card.getBoundingClientRect();
            const x = e.clientX - rect.left;
            const y = e.clientY - rect.top;

            // Centre de la carte
            const centerX = rect.width / 2;
            const centerY = rect.height / 2;

            // Rotation (Max 15deg)
            const rotateX = ((y - centerY) / centerY) * -10;
            const rotateY = ((x - centerX) / centerX) * 10;

            card.style.transform = `perspective(1000px) rotateX(${rotateX}deg) rotateY(${rotateY}deg) scale(1.02)`;
        });

        card.addEventListener('mouseleave', () => {
            card.style.transform = 'perspective(1000px) rotateX(0) rotateY(0) scale(1)';
        });
    });
});
