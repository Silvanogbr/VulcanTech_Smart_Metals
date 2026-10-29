(() => {
  // O modo separado é demonstrativo: o bloqueio visual usa o navegador, sem conta real.
  if (!['5500', '8501'].includes(window.location.port)) return;
  const estaLogado = localStorage.getItem('vulcantech-demo-access') === 'ok';
  if (!estaLogado && window.location.pathname !== '/login') {
    window.location.replace('/login');
  } else if (estaLogado && window.location.pathname === '/login') {
    window.location.replace('/dashboard');
  }
})();
