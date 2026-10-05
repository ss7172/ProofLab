
const themeButton=document.getElementById('theme');
themeButton.addEventListener('click',()=>{const root=document.documentElement;const dark=root.dataset.theme==='dark'||(!root.dataset.theme&&matchMedia('(prefers-color-scheme: dark)').matches);root.dataset.theme=dark?'light':'dark';});
const controlButtons=[...document.querySelectorAll('[data-control]')];
controlButtons.forEach(button=>button.addEventListener('click',()=>{controlButtons.forEach(other=>{const active=other===button;other.setAttribute('aria-pressed',String(active));document.getElementById('control-'+other.dataset.control).hidden=!active;});}));
