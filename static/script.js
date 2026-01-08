function setLanguage(lang) {
    localStorage.setItem('lang', lang);
    document.querySelectorAll('[data-en]').forEach(el => {
        const text = el.getAttribute(`data-${lang}`);
        if (text) el.textContent = text;
    });
}

window.onload = () => {
    const savedLang = localStorage.getItem('lang') || 'en';
    document.querySelector('.language-switcher select').value = savedLang;
    setLanguage(savedLang);
};

function changeLanguage(lang) {
    const elements = document.querySelectorAll('[data-en]');
    
    elements.forEach(el => {
        const translation = el.getAttribute(`data-${lang}`);
        
        if (translation) {
            el.innerHTML = translation;
        }
    });
}