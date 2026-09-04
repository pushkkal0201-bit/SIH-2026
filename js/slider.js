(() => {
  const slider = document.querySelector('[data-slider]');
  const slides = slider ? [...slider.querySelectorAll('.drone-slide')] : [];
  const dots = slider ? [...slider.querySelectorAll('[data-slide]')] : [];
  const previous = slider?.querySelector('[data-prev]');
  const next = slider?.querySelector('[data-next]');
  const pauseButton = slider?.querySelector('[data-pause]');
  const intervalMs = 6000;
  let activeIndex = 0;
  let timer = null;
  let paused = false;
  let touchStartX = 0;

  const setSlide = (index, restart = true) => {
    if (!slides.length) return;
    activeIndex = (index + slides.length) % slides.length;
    slides.forEach((slide, slideIndex) => {
      const active = slideIndex === activeIndex;
      slide.classList.toggle('is-active', active);
      slide.setAttribute('aria-hidden', String(!active));
    });
    dots.forEach((dot, dotIndex) => {
      const active = dotIndex === activeIndex;
      dot.classList.toggle('is-active', active);
      dot.setAttribute('aria-selected', String(active));
      dot.tabIndex = active ? 0 : -1;
    });
    if (restart && !paused) startTimer();
  };

  const startTimer = () => {
    window.clearInterval(timer);
    if (!paused && slides.length > 1) {
      timer = window.setInterval(() => setSlide(activeIndex + 1, false), intervalMs);
    }
  };

  const togglePause = () => {
    paused = !paused;
    slider?.classList.toggle('is-paused', paused);
    if (pauseButton) {
      pauseButton.textContent = paused ? 'Resume' : 'Pause';
      pauseButton.setAttribute('aria-label', paused ? 'Resume automatic slideshow' : 'Pause automatic slideshow');
    }
    paused ? window.clearInterval(timer) : startTimer();
  };

  previous?.addEventListener('click', () => setSlide(activeIndex - 1));
  next?.addEventListener('click', () => setSlide(activeIndex + 1));
  pauseButton?.addEventListener('click', togglePause);
  dots.forEach((dot, index) => dot.addEventListener('click', () => setSlide(index)));

  slider?.addEventListener('keydown', (event) => {
    if (event.key === 'ArrowLeft') setSlide(activeIndex - 1);
    if (event.key === 'ArrowRight') setSlide(activeIndex + 1);
    if (event.key === ' ') {
      event.preventDefault();
      togglePause();
    }
  });

  slider?.addEventListener('touchstart', (event) => {
    touchStartX = event.changedTouches[0].clientX;
  }, { passive: true });
  slider?.addEventListener('touchend', (event) => {
    const distance = event.changedTouches[0].clientX - touchStartX;
    if (Math.abs(distance) > 55) setSlide(activeIndex + (distance < 0 ? 1 : -1));
  }, { passive: true });

  document.addEventListener('visibilitychange', () => {
    if (document.hidden) window.clearInterval(timer);
    else if (!paused) startTimer();
  });

  setSlide(0, false);
  if (!window.matchMedia('(prefers-reduced-motion: reduce)').matches) startTimer();
  else {
    paused = true;
    slider?.classList.add('is-paused');
    if (pauseButton) pauseButton.textContent = 'Resume';
  }

  const header = document.querySelector('.site-header');
  const menuButton = document.querySelector('[data-menu-toggle]');
  const backToTop = document.querySelector('[data-back-to-top]');
  const navLinks = [...document.querySelectorAll('.primary-nav a')];

  const closeMenu = () => {
    header?.classList.remove('nav-open');
    document.body.classList.remove('menu-open');
    menuButton?.setAttribute('aria-expanded', 'false');
    menuButton?.setAttribute('aria-label', 'Open navigation');
  };

  menuButton?.addEventListener('click', () => {
    const open = !header?.classList.contains('nav-open');
    header?.classList.toggle('nav-open', open);
    document.body.classList.toggle('menu-open', open);
    menuButton.setAttribute('aria-expanded', String(open));
    menuButton.setAttribute('aria-label', open ? 'Close navigation' : 'Open navigation');
  });
  navLinks.forEach(link => link.addEventListener('click', closeMenu));
  document.addEventListener('keydown', event => {
    if (event.key === 'Escape') closeMenu();
  });

  const updateScrollUI = () => {
    const scrollTop = window.scrollY;
    const scrollRange = document.documentElement.scrollHeight - window.innerHeight;
    const progress = scrollRange > 0 ? Math.min(100, (scrollTop / scrollRange) * 100) : 0;
    document.body.style.setProperty('--scroll-progress', `${progress}%`);
    header?.classList.toggle('is-scrolled', scrollTop > 90);
    backToTop?.classList.toggle('is-visible', scrollTop > 700);
  };
  window.addEventListener('scroll', updateScrollUI, { passive: true });
  updateScrollUI();

  backToTop?.addEventListener('click', () => {
    window.scrollTo({ top: 0, behavior: 'smooth' });
  });

  if ('IntersectionObserver' in window) {
    const linkedSections = navLinks
      .map(link => document.querySelector(link.getAttribute('href')))
      .filter(Boolean);
    const sectionObserver = new IntersectionObserver(entries => {
      const visible = entries
        .filter(entry => entry.isIntersecting)
        .sort((a, b) => b.intersectionRatio - a.intersectionRatio)[0];
      if (!visible) return;
      navLinks.forEach(link => {
        const current = link.getAttribute('href') === `#${visible.target.id}`;
        link.classList.toggle('is-current', current);
        if (current) link.setAttribute('aria-current', 'page');
        else link.removeAttribute('aria-current');
      });
    }, { rootMargin: '-32% 0px -58%', threshold: [0, .15, .4] });
    linkedSections.forEach(section => sectionObserver.observe(section));
  }

  let textSize = 16;
  const setTextSize = value => {
    textSize = Math.max(14, Math.min(20, value));
    document.documentElement.style.fontSize = `${textSize}px`;
  };
  document.querySelector('[data-font-down]')?.addEventListener('click', () => setTextSize(textSize - 1));
  document.querySelector('[data-font-reset]')?.addEventListener('click', () => setTextSize(16));
  document.querySelector('[data-font-up]')?.addEventListener('click', () => setTextSize(textSize + 1));
  document.querySelector('[data-contrast]')?.addEventListener('click', event => {
    const enabled = document.body.classList.toggle('high-contrast');
    event.currentTarget.setAttribute('aria-pressed', String(enabled));
  });

  const revealTargets = document.querySelectorAll(
    '.section-intro, .compare-shell, .three-layer-grid, .twin-showcase, .capability-grid, .architecture-layout, .mission-gallery, .use-case-grid'
  );
  revealTargets.forEach(target => target.classList.add('reveal'));
  if ('IntersectionObserver' in window && !window.matchMedia('(prefers-reduced-motion: reduce)').matches) {
    const observer = new IntersectionObserver(entries => {
      entries.forEach(entry => {
        if (entry.isIntersecting) {
          entry.target.classList.add('is-visible');
          observer.unobserve(entry.target);
        }
      });
    }, { threshold: .12 });
    revealTargets.forEach(target => observer.observe(target));
  } else {
    revealTargets.forEach(target => target.classList.add('is-visible'));
  }
})();
