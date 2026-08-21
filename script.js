document.addEventListener('DOMContentLoaded', () => {
    // Theme toggle functionality
    const themeToggleBtn = document.getElementById('theme-toggle');
    console.log('Theme toggle button loaded:', themeToggleBtn);
    
    let savedTheme = null;
    try {
        savedTheme = localStorage.getItem('theme');
    } catch (e) {
        console.warn('Storage is not accessible', e);
    }
    const isLightMode = savedTheme === 'light';
    
    if (isLightMode) {
        document.body.classList.add('light-mode');
        updateThemeIcon(true);
    }
    
    if (themeToggleBtn) {
        themeToggleBtn.addEventListener('click', () => {
            console.log('Theme toggle clicked');
            const currentlyLight = document.body.classList.contains('light-mode');
            if (currentlyLight) {
                document.body.classList.remove('light-mode');
                try {
                    localStorage.setItem('theme', 'dark');
                } catch (e) {
                    console.warn('Storage is not accessible', e);
                }
                updateThemeIcon(false);
            } else {
                document.body.classList.add('light-mode');
                try {
                    localStorage.setItem('theme', 'light');
                } catch (e) {
                    console.warn('Storage is not accessible', e);
                }
                updateThemeIcon(true);
            }
        });
    }
    
    function updateThemeIcon(light) {
        if (!themeToggleBtn) return;
        const icon = themeToggleBtn.querySelector('i');
        if (icon) {
            if (light) {
                icon.className = 'fa-solid fa-moon';
            } else {
                icon.className = 'fa-solid fa-sun';
            }
        }
    }

    // Smooth scrolling for navigation links
    document.querySelectorAll('a[href^="#"]').forEach(anchor => {
        anchor.addEventListener('click', function (e) {
            e.preventDefault();
            const targetId = this.getAttribute('href');
            if (targetId === '#') return;
            
            try {
                const targetElement = document.querySelector(targetId);
                if (targetElement) {
                    targetElement.scrollIntoView({
                        behavior: 'smooth'
                    });
                }
            } catch (err) {
                console.error('Smooth scroll target selector error:', err);
            }
        });
    });
});
