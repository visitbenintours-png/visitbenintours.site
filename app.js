
function openWhatsapp() {
  const msg = encodeURIComponent("Hello! I'm interested in booking a tour with Visit Bénin Tours. Could you tell me more about your available tours and prices?");
  window.open('https://wa.me/2290159255518?text=' + msg, '_blank');
}

function openCall() {
  window.location.href = 'tel:+2290159255518';
}

function toggleMenu() {
  document.getElementById('mobileMenu').classList.toggle('open');
}

// Scroll reveal on load
window.addEventListener('load', () => {
  const observer = new IntersectionObserver(entries => {
    entries.forEach(e => {
      if (e.isIntersecting) { e.target.classList.add('visible'); observer.unobserve(e.target); }
    });
  }, { threshold: 0.1 });
  document.querySelectorAll('.reveal').forEach(el => observer.observe(el));
});

// Transparent-over-hero nav, glass on scroll (home page only — detected by presence of .hero)
(() => {
  const heroEl = document.querySelector('.hero');
  const navEl = document.querySelector('nav');
  if (!heroEl || !navEl) return;
  navEl.classList.add('transparent');
  const onScroll = () => {
    if (window.scrollY > 40) navEl.classList.remove('transparent');
    else navEl.classList.add('transparent');
  };
  onScroll();
  window.addEventListener('scroll', onScroll, { passive: true });
})();
