(() => {
  const progress = document.querySelector('.reading-progress');
  const links = [...document.querySelectorAll('.section-nav a')];
  const update = () => {
    const available = document.documentElement.scrollHeight - window.innerHeight;
    progress.style.width = `${available > 0 ? Math.min(100, 100 * window.scrollY / available) : 0}%`;
    if (window.scrollY < document.querySelector('#quick').offsetTop - 150) {
      links.forEach(link => link.removeAttribute('aria-current'));
    }
  };
  window.addEventListener('scroll', update, {passive: true});
  window.addEventListener('resize', update);
  if ('IntersectionObserver' in window) {
    const observer = new IntersectionObserver(entries => {
      for (const entry of entries) {
        if (!entry.isIntersecting) continue;
        for (const link of links) {
          if (link.hash === `#${entry.target.id}`) link.setAttribute('aria-current', 'true');
          else link.removeAttribute('aria-current');
        }
      }
    }, {rootMargin: '-10% 0px -65% 0px'});
    links.forEach(link => { const target = document.querySelector(link.hash); if (target) observer.observe(target); });
  }
  update();
})();
