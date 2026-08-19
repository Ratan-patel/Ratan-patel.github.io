/* ========================================
   ADVANCED INTERACTIVE ANIMATIONS
   ======================================== */

// 1. DANCING AVATAR ON PAGE LOAD
document.addEventListener('DOMContentLoaded', function() {
  const profileImg = document.querySelector('img[alt*="Ratan"]');
  if (profileImg) {
    profileImg.parentElement.classList.add('avatar-dancing');
  }

  // Initialize all animations
  initParticleSystem();
  initMatrixRain();
  initScrollReveal();
  initNeuralNetwork();
  initTypewriterEffect();
  enableInteractiveAnimations();
  createFloatingElements();
});

// 2. PARTICLE SYSTEM
function initParticleSystem() {
  const particleTypes = ['✦', '✧', '⚡', '◆', '●', '☆', '★'];
  const colors = ['#10b981', '#06b6d4', '#8b5cf6', '#f59e0b'];
  
  setInterval(() => {
    const particle = document.createElement('div');
    particle.className = `particle type${Math.floor(Math.random() * 3) + 1}`;
    particle.textContent = particleTypes[Math.floor(Math.random() * particleTypes.length)];
    particle.style.left = Math.random() * window.innerWidth + 'px';
    particle.style.top = window.innerHeight + 'px';
    particle.style.color = colors[Math.floor(Math.random() * colors.length)];
    particle.style.fontSize = (Math.random() * 20 + 10) + 'px';
    particle.style.animationDuration = (Math.random() * 10 + 10) + 's';
    particle.style.animationDelay = Math.random() * 2 + 's';
    
    document.body.appendChild(particle);
    
    setTimeout(() => particle.remove(), 30000);
  }, 1000);
}

// 3. MATRIX RAIN EFFECT
function initMatrixRain() {
  const characters = 'アイウエオカキクケコサシスセソタチツテトナニヌネノハヒフヘホマミムメモヤユヨラリルレロワヲン0123456789';
  
  for (let i = 0; i < 15; i++) {
    const char = document.createElement('div');
    char.className = 'matrix-char falling';
    char.textContent = characters[Math.floor(Math.random() * characters.length)];
    char.style.left = Math.random() * window.innerWidth + 'px';
    char.style.top = Math.random() * window.innerHeight + 'px';
    char.style.animationDuration = (Math.random() * 8 + 6) + 's';
    char.style.animationDelay = Math.random() * 3 + 's';
    
    document.body.appendChild(char);
  }
}

// 4. SCROLL REVEAL ANIMATION
function initScrollReveal() {
  const revealElements = document.querySelectorAll('section, .bg-slate-900\\/20');
  
  const revealOnScroll = () => {
    revealElements.forEach(element => {
      const windowHeight = window.innerHeight;
      const elementTop = element.getBoundingClientRect().top;
      const elementVisible = 150;
      
      if (elementTop < windowHeight - elementVisible) {
        element.classList.add('scroll-reveal');
      }
    });
  };
  
  window.addEventListener('scroll', revealOnScroll);
  revealOnScroll(); // Initial check
}

// 5. NEURAL NETWORK BACKGROUND
function initNeuralNetwork() {
  const container = document.querySelector('main');
  if (!container) return;
  
  const neural = document.createElement('div');
  neural.className = 'neural-network';
  
  for (let i = 0; i < 8; i++) {
    const node = document.createElement('div');
    node.className = 'neural-node';
    node.style.left = Math.random() * 90 + '%';
    node.style.top = Math.random() * 90 + '%';
    node.style.animationDelay = Math.random() * 2 + 's';
    neural.appendChild(node);
  }
  
  for (let i = 0; i < 6; i++) {
    const line = document.createElement('div');
    line.className = 'neural-line';
    line.style.left = Math.random() * 80 + '%';
    line.style.top = Math.random() * 80 + '%';
    line.style.width = (Math.random() * 150 + 50) + 'px';
    line.style.animationDelay = Math.random() * 3 + 's';
    neural.appendChild(line);
  }
  
  container.style.position = 'relative';
  container.appendChild(neural);
}

// 6. TYPEWRITER EFFECT
function initTypewriterEffect() {
  const heading = document.querySelector('h1');
  if (heading) {
    const text = heading.textContent;
    heading.textContent = '';
    
    let i = 0;
    const typeInterval = setInterval(() => {
      if (i < text.length) {
        heading.textContent += text[i];
        i++;
      } else {
        clearInterval(typeInterval);
      }
    }, 100);
  }
}

// 7. INTERACTIVE CARD ANIMATIONS
function enableInteractiveAnimations() {
  const cards = document.querySelectorAll('.bg-slate-900\\/20, .bg-slate-900\\/30');
  
  cards.forEach(card => {
    card.classList.add('card-3d-flip');
    
    card.addEventListener('mouseenter', function() {
      this.style.transform = 'perspective(1000px) rotateY(10deg) rotateX(-5deg)';
      this.style.boxShadow = '0 20px 60px rgba(16, 185, 129, 0.3)';
    });
    
    card.addEventListener('mouseleave', function() {
      this.style.transform = 'perspective(1000px) rotateY(0deg) rotateX(0deg)';
      this.style.boxShadow = '';
    });
  });
}

// 8. FLOATING ELEMENTS
function createFloatingElements() {
  const floatingElements = document.querySelectorAll('.text-slate-300, h4.font-bold');
  
  floatingElements.forEach((el, index) => {
    if (index % 3 === 0) {
      el.classList.add('float-text');
      el.style.animationDelay = (index * 0.2) + 's';
    }
  });
}

// 9. DANCING AVATAR TOGGLE
let isDancing = false;

function toggleAvatarDance() {
  const profileImg = document.querySelector('img[alt*="Ratan"]');
  if (!profileImg) return;
  
  isDancing = !isDancing;
  
  if (isDancing) {
    profileImg.parentElement.classList.add('avatar-dancing');
  } else {
    profileImg.parentElement.classList.remove('avatar-dancing');
  }
}

// 10. GLITCH TEXT EFFECT ON HOVER
function enableGlitchEffect() {
  const glossyText = document.querySelectorAll('.text-emerald-400, .text-cyan-400');
  
  glossyText.forEach(el => {
    el.addEventListener('mouseenter', function() {
      this.classList.add('glitch');
    });
    
    el.addEventListener('mouseleave', function() {
      this.classList.remove('glitch');
    });
  });
}

// 11. ENHANCED GLOW ON INTERACTIVE ELEMENTS
function enableEnhancedGlow() {
  const buttons = document.querySelectorAll('button, a[href*="contact"]');
  
  buttons.forEach(btn => {
    btn.classList.add('enhanced-glow');
  });
}

// 12. SCROLL-BASED PARALLAX
function initParallax() {
  window.addEventListener('scroll', () => {
    const scrolled = window.pageYOffset;
    const parallaxElements = document.querySelectorAll('.bg-[radial-gradient');
    
    parallaxElements.forEach(el => {
      el.style.transform = `translateY(${scrolled * 0.5}px)`;
    });
  });
}

// 13. CURSOR TRACKING EFFECT
function initCursorTracking() {
  const cards = document.querySelectorAll('.bg-slate-900\\/20');
  
  document.addEventListener('mousemove', (e) => {
    cards.forEach(card => {
      const rect = card.getBoundingClientRect();
      const x = e.clientX - rect.left;
      const y = e.clientY - rect.top;
      
      const xPercent = (x / rect.width) * 100;
      const yPercent = (y / rect.height) * 100;
      
      const rotX = (yPercent - 50) / 5;
      const rotY = (xPercent - 50) / 5;
      
      card.style.transform = `perspective(1000px) rotateX(${rotX}deg) rotateY(${rotY}deg)`;
    });
  });
}

// 14. STATS COUNTER ANIMATION
function animateCounters() {
  const counters = document.querySelectorAll('[id^="stat-"]');
  
  const startCounting = (counter) => {
    const target = parseInt(counter.getAttribute('data-target') || counter.textContent);
    let current = 0;
    
    const increment = target / 50;
    
    const updateCounter = () => {
      current += increment;
      if (current < target) {
        counter.textContent = Math.floor(current) + '+';
        requestAnimationFrame(updateCounter);
      } else {
        counter.textContent = target + '+';
      }
    };
    
    updateCounter();
  };
  
  const observer = new IntersectionObserver((entries) => {
    entries.forEach(entry => {
      if (entry.isIntersecting) {
        startCounting(entry.target);
        observer.unobserve(entry.target);
      }
    });
  });
  
  counters.forEach(counter => observer.observe(counter));
}

// 15. RAINBOWS TEXT ON DEMAND
function enableRainbowText() {
  const headings = document.querySelectorAll('h1, h2, h3');
  
  headings.forEach(heading => {
    heading.addEventListener('click', function() {
      this.classList.toggle('rainbow-text');
      setTimeout(() => this.classList.remove('rainbow-text'), 3000);
    });
  });
}

// 16. KEYBOARD SHORTCUTS FOR ANIMATIONS
document.addEventListener('keydown', function(e) {
  // Alt + D = Dance
  if (e.altKey && e.key.toLowerCase() === 'd') {
    toggleAvatarDance();
  }
  
  // Alt + G = Glitch
  if (e.altKey && e.key.toLowerCase() === 'g') {
    enableGlitchEffect();
  }
  
  // Alt + R = Rainbow
  if (e.altKey && e.key.toLowerCase() === 'r') {
    enableRainbowText();
  }
});

// 17. MORPHING BLOB BACKGROUND
function createMorphingBlob() {
  const hero = document.querySelector('section#home');
  if (!hero) return;
  
  const blob = document.createElement('div');
  blob.style.position = 'absolute';
  blob.style.width = '300px';
  blob.style.height = '300px';
  blob.style.background = 'linear-gradient(135deg, rgba(16, 185, 129, 0.1), rgba(6, 182, 212, 0.1))';
  blob.style.borderRadius = '40% 60% 70% 30% / 40% 50% 60% 50%';
  blob.style.filter = 'blur(40px)';
  blob.style.animation = 'morphBlob 8s ease-in-out infinite';
  blob.style.top = '10%';
  blob.style.right = '-10%';
  blob.style.zIndex = '0';
  blob.style.pointerEvents = 'none';
  
  hero.style.position = 'relative';
  hero.appendChild(blob);
}

// 18. SIGNAL PULSE
function initSignalPulse() {
  const statusIndicator = document.querySelector('[class*="animate-pulse"]');
  if (statusIndicator) {
    statusIndicator.classList.add('electric-pulse');
  }
}

// 19. SMOOTH SCROLL
function initSmoothScroll() {
  document.querySelectorAll('a[href^="#"]').forEach(anchor => {
    anchor.addEventListener('click', function (e) {
      e.preventDefault();
      const target = document.querySelector(this.getAttribute('href'));
      if (target) {
        target.scrollIntoView({
          behavior: 'smooth',
          block: 'start'
        });
      }
    });
  });
}

// 20. BACKGROUND WAVE ANIMATION
function createWaveBackground() {
  const style = document.createElement('style');
  style.textContent = `
    @keyframes wave {
      0%, 100% { transform: translateY(0); }
      50% { transform: translateY(-10px); }
    }
    
    .wave-bg {
      position: fixed;
      bottom: 0;
      left: 0;
      width: 200%;
      height: 100px;
      background: url('data:image/svg+xml;utf8,<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1200 120"><path d="M0,50 Q300,0 600,50 T1200,50 L1200,120 L0,120 Z" fill="rgba(16,185,129,0.05)"/></svg>');
      background-size: 600px 100px;
      animation: wave 10s linear infinite;
      pointer-events: none;
      z-index: 1;
    }
  `;
  document.head.appendChild(style);
  
  const wave = document.createElement('div');
  wave.className = 'wave-bg';
  document.body.appendChild(wave);
}

// Initialize everything on document ready
document.addEventListener('DOMContentLoaded', function() {
  enableGlitchEffect();
  enableEnhancedGlow();
  initParallax();
  initCursorTracking();
  animateCounters();
  createMorphingBlob();
  initSignalPulse();
  initSmoothScroll();
  createWaveBackground();
  
  // Add stagger animation to lists
  const listItems = document.querySelectorAll('li[class*="flex"]');
  listItems.forEach((item, index) => {
    item.classList.add('stagger-item');
  });
});

// Bonus: Easter egg - Konami code for special effects
const konamiCode = ['ArrowUp', 'ArrowUp', 'ArrowDown', 'ArrowDown', 'ArrowLeft', 'ArrowRight', 'ArrowLeft', 'ArrowRight', 'b', 'a'];
let konamiIndex = 0;

document.addEventListener('keydown', function(e) {
  if (e.key === konamiCode[konamiIndex]) {
    konamiIndex++;
    if (konamiIndex === konamiCode.length) {
      activateMatrixMode();
      konamiIndex = 0;
    }
  } else {
    konamiIndex = 0;
  }
});

function activateMatrixMode() {
  document.body.style.filter = 'hue-rotate(90deg) saturate(2)';
  setTimeout(() => {
    document.body.style.filter = '';
  }, 3000);
  
  alert('🎮 MATRIX MODE ACTIVATED! Watch the transformation! 🎮');
}

// Export for use
window.animationController = {
  toggleAvatarDance,
  enableGlitchEffect,
  enableRainbowText,
  activateMatrixMode
};

/* ========================================
   ENHANCED 3D TRACKING AND INTERACTIVE EFFECTS
   ======================================== */

// 21. ADVANCED 3D TILT EFFECT FOR CARDS
function initAdvanced3DTilt() {
  const tiltElements = document.querySelectorAll('.card-3d-float, .bg-slate-900\\/30');
  
  tiltElements.forEach(el => {
    el.addEventListener('mousemove', (e) => {
      const rect = el.getBoundingClientRect();
      const x = e.clientX - rect.left;
      const y = e.clientY - rect.top;
      
      const centerX = rect.width / 2;
      const centerY = rect.height / 2;
      
      const rotateX = ((y - centerY) / centerY) * -10; // Max 10 degrees
      const rotateY = ((x - centerX) / centerX) * 10; // Max 10 degrees
      
      el.style.transform = `perspective(1000px) rotateX(${rotateX}deg) rotateY(${rotateY}deg) scale3d(1.02, 1.02, 1.02)`;
    });
    
    el.addEventListener('mouseleave', () => {
      el.style.transform = 'perspective(1000px) rotateX(0deg) rotateY(0deg) scale3d(1, 1, 1)';
    });
  });
}

// 22. FLOATING CYBER ASSETS
function initFloatingCyberAssets() {
  const container = document.body;
  const icons = ['fa-shield-halved', 'fa-lock', 'fa-terminal', 'fa-code', 'fa-user-secret'];
  
  for (let i = 0; i < 10; i++) {
    const icon = document.createElement('i');
    icon.className = `fa-solid ${icons[Math.floor(Math.random() * icons.length)]} floating-bg-element`;
    icon.style.position = 'fixed';
    icon.style.left = Math.random() * 100 + 'vw';
    icon.style.top = Math.random() * 100 + 'vh';
    icon.style.fontSize = (Math.random() * 20 + 10) + 'px';
    icon.style.color = 'rgba(16, 185, 129, 0.05)';
    icon.style.zIndex = '-1';
    icon.style.pointerEvents = 'none';
    icon.style.animationDelay = (Math.random() * 5) + 's';
    
    container.appendChild(icon);
  }
}

// Update initialization
document.addEventListener('DOMContentLoaded', function() {
  initAdvanced3DTilt();
  initFloatingCyberAssets();
});
