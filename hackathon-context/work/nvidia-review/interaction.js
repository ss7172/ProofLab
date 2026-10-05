
document.getElementById('theme').addEventListener('click',()=>{const r=document.documentElement;const dark=r.dataset.theme==='dark'||(!r.dataset.theme&&matchMedia('(prefers-color-scheme: dark)').matches);r.dataset.theme=dark?'light':'dark';});
const views=[...document.querySelectorAll('[data-view]')];views.forEach(b=>b.addEventListener('click',()=>{views.forEach(x=>{const active=x===b;x.setAttribute('aria-pressed',String(active));document.getElementById('view-'+x.dataset.view).hidden=!active;});}));
